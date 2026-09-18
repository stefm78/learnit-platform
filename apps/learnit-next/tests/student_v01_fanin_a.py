#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.v2.atlas import pedagogical_quality
from authoring.v4.tests.test_validate_v4 import make_valid_v4, validate

FAMILIES = (
    "qcm",
    "fill",
    "constructed",
    "lesson",
    "flashcard",
    "matching",
    "order",
    "classify",
)
SECRETS = (
    "correctChoiceId",
    "answers",
    "acceptedResponses",
    "matches",
    "correctOrder",
    "assignments",
)

PROJECT = r"""
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=process.env.FANIN_ROOT;
const kit=JSON.parse(fs.readFileSync(process.env.FANIN_KIT,'utf8'));
const mod=async p=>import(pathToFileURL(path.join(root,p)).href);
const C=await mod('apps/learnit-next/src/core/contract.js');
const X=await mod('apps/learnit-next/src/integration/atlas/activity_projection.js');
const admitted=await C.validatePackageObject(kit);
assert.ok(admitted.ok,JSON.stringify(admitted.errors));
const activities=kit.courses[0].activities;
const presentations=activities.map(activity=>X.projectActivityPresentation(activity,{assets:kit.assets}));
assert.equal(presentations.length,8);
console.log(JSON.stringify({presentations}));
"""

EVALUATE = r"""
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=process.env.FANIN_ROOT;
const kit=JSON.parse(fs.readFileSync(process.env.FANIN_KIT,'utf8'));
const responses=JSON.parse(fs.readFileSync(process.env.FANIN_RESPONSES,'utf8'));
const A=await import(pathToFileURL(path.join(root,'apps/learnit-next/src/core/activity_semantics.js')).href);
const byType=Object.fromEntries(kit.courses[0].activities.map(a=>[a.type,a]));
const results={};
for(const [type,response] of Object.entries(responses)){
  const result=A.evaluateActivityResponse(byType[type],response);
  results[type]=result;
  if(type==='lesson'||type==='flashcard'){
    assert.equal(result.scored,false,type);
    assert.ok(!Object.hasOwn(result,'correct'),type);
  }else{
    assert.equal(result.correct,true,type+': '+JSON.stringify(result));
  }
}
console.log(JSON.stringify(results));
"""


def run_node(script: str, *, kit_path: Path, responses_path: Path | None = None) -> dict:
    env = os.environ.copy()
    env["FANIN_ROOT"] = str(ROOT)
    env["FANIN_KIT"] = str(kit_path)
    if responses_path is not None:
        env["FANIN_RESPONSES"] = str(responses_path)
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            "Node integration probe failed "
            f"(exit={completed.returncode})\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return json.loads(completed.stdout)


def main() -> int:
    # JOB03 -> authoring authority and quality layer.
    kit = make_valid_v4()
    canonical_before = json.dumps(kit, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    report = validate(copy.deepcopy(kit))
    assert report.ok, report.errors
    assert sum(report.activities.values()) == 8
    quality = pedagogical_quality.analyze_package(copy.deepcopy(kit))
    assert quality["canonicalValid"], quality
    assert quality["verdict"] == "PASS_ATLAS_PEDAGOGICAL_PROFILE_V1", quality

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        kit_path = work / "candidate-v4.json"
        response_path = work / "responses.json"
        kit_path.write_text(json.dumps(kit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # JOB01 -> explicit runtime admission and learner-safe projection.
        projected = run_node(PROJECT, kit_path=kit_path)
        presentations = projected["presentations"]
        source_types = [a["type"] for a in kit["courses"][0]["activities"]]
        assert len(FAMILIES) == len(set(FAMILIES)), "expected family list must not contain duplicates"
        assert len(source_types) == len(FAMILIES), (source_types, FAMILIES)
        assert len(source_types) == len(set(source_types)), f"duplicate source families: {source_types}"
        assert set(source_types) == set(FAMILIES), (source_types, FAMILIES)
        assert [p["type"] for p in presentations] == source_types
        presentation_by_type = {p["type"]: p for p in presentations}
        activity_by_type = {a["type"]: a for a in kit["courses"][0]["activities"]}
        for family, presentation in presentation_by_type.items():
            serialized = json.dumps(presentation, ensure_ascii=False, sort_keys=True)
            for secret in SECRETS:
                assert f'"{secret}"' not in serialized, f"{family} leaked {secret}"

        lesson = presentation_by_type["lesson"]
        assert lesson["media"][0]["alt"] == kit["assets"][0]["alt"]
        assert not any(
            str(asset.get("data", "")).startswith(("http://", "https://"))
            for asset in kit.get("assets", [])
        )

        # JOB02 -> render the actual learner-safe projections and read the actual
        # UI response grammar in Chromium. The UI never receives the canonical kit.
        media = (ROOT / "apps/learnit-next/src/ui/media.js").read_text(encoding="utf-8")
        presenters = (ROOT / "apps/learnit-next/src/ui/activity_presenters.js").read_text(encoding="utf-8")
        css = (ROOT / "apps/learnit-next/src/atlas.css").read_text(encoding="utf-8")
        bundle = media.replace("export function ", "function ")
        bundle += "\n" + presenters.replace(
            "import { renderEmbeddedMediaSet } from './media.js';\n", ""
        ).replace("export function ", "function ")
        bundle += "\nwindow.Fanin={renderActivityPresentation,readActivityResponse};"

        responses: dict[str, object] = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
            page = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True)
            page_errors: list[str] = []
            remote_requests: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on(
                "request",
                lambda request: remote_requests.append(request.url)
                if request.url.startswith(("http://", "https://"))
                else None,
            )
            page.set_content('<main class="atlas-m1"><div id="mount"></div></main>')
            page.add_style_tag(content=css)
            page.add_script_tag(content=bundle)
            page.wait_for_function("() => Boolean(window.Fanin)")

            def render(family: str) -> dict:
                p = presentation_by_type[family]
                page.evaluate(
                    "p => document.getElementById('mount').replaceChildren(Fanin.renderActivityPresentation(p))",
                    p,
                )
                return p

            def read(presentation: dict) -> object:
                return page.evaluate(
                    "p => Fanin.readActivityResponse(document.getElementById('mount'), p)",
                    presentation,
                )

            p = render("qcm")
            qcm = activity_by_type["qcm"]
            page.locator(
                f'[data-activity-choice="true"][value="{qcm["correctChoiceId"]}"]'
            ).check()
            responses["qcm"] = read(p)

            p = render("fill")
            fill = activity_by_type["fill"]
            for answer in fill["answers"]:
                page.locator(f'[data-activity-slot="{answer["slotId"]}"]').select_option(
                    answer["tokenId"]
                )
            responses["fill"] = read(p)

            p = render("constructed")
            constructed = activity_by_type["constructed"]
            page.locator("[data-constructed-response]").fill(constructed["acceptedResponses"][0])
            responses["constructed"] = read(p)

            p = render("lesson")
            assert page.get_by_alt_text(kit["assets"][0]["alt"]).count() == 1
            page.locator('[data-activity-continue="lesson"]').click()
            responses["lesson"] = read(p)

            p = render("flashcard")
            page.locator('[data-flashcard-reveal="true"]').click()
            page.locator('[data-activity-continue="flashcard"]').click()
            responses["flashcard"] = read(p)

            p = render("matching")
            matching = activity_by_type["matching"]
            for pair in matching["matches"]:
                page.locator(f'[data-matching-left="{pair["leftItemId"]}"]').click()
                page.locator(f'[data-matching-right="{pair["rightItemId"]}"]').click()
            responses["matching"] = read(p)

            p = render("order")
            order = activity_by_type["order"]
            current = list(read(p)["orderedItemIds"])
            for target_index, item_id in enumerate(order["correctOrder"]):
                while current.index(item_id) > target_index:
                    page.locator(
                        f'[data-order-item="{item_id}"] [data-order-move="up"]'
                    ).click()
                    current = list(read(p)["orderedItemIds"])
            responses["order"] = read(p)

            p = render("classify")
            classify = activity_by_type["classify"]
            for assignment in classify["assignments"]:
                page.locator(
                    f'[data-classify-select="{assignment["itemId"]}"]'
                ).select_option(assignment["bucketId"])
            responses["classify"] = read(p)

            assert page_errors == [], page_errors
            assert remote_requests == [], remote_requests
            browser.close()

        # JOB01 again -> the exact UI response shapes are consumed by Learning.
        response_path.write_text(
            json.dumps(responses, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        results = run_node(EVALUATE, kit_path=kit_path, responses_path=response_path)
        assert set(results) == set(FAMILIES)
        assert results["lesson"]["scored"] is False and "correct" not in results["lesson"]
        assert results["flashcard"]["scored"] is False and "correct" not in results["flashcard"]

        canonical_after = json.dumps(kit, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        assert canonical_after == canonical_before, "cross-role qualification mutated the canonical kit"

    print("STUDENT_V01_FANIN_A_AUTHORING_TO_LEARNER_PASS")
    print("STUDENT_V01_FANIN_A_ALL_FAMILIES_END_TO_END_PASS")
    print("STUDENT_V01_FANIN_A_SECRET_BOUNDARY_PASS")
    print("STUDENT_V01_FANIN_A_MEDIA_PASS")
    print("STUDENT_V01_FANIN_A_NON_SCORED_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
