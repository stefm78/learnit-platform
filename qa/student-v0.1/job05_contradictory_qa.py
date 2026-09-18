#!/usr/bin/env python3
"""JOB05 deterministic repro for the served Student V0.1 rich-V4 product gap.

QA-only: validates the independent fixture, proves exact build identity, then opens
that built artifact through the real import/start controls at desktop/mobile sizes.
A zero exit means the expected HOLD was reproduced without touching product code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name("JOB05_CANONICAL_V4_FIXTURE.json")
EXPECTED_BYTES = 474861
EXPECTED_SHA256 = "0b1e21038bc8f17521ecd604460781377a850b174907723a7d6af6174511310f"
FAMILIES = ["lesson", "flashcard", "matching", "order", "classify", "qcm", "fill", "constructed"]


def command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)


def canonical_fixture_check() -> dict:
    proc = command(sys.executable, "-B", "authoring/v4/validate_kit.py", str(FIXTURE), "--format=json")
    if proc.returncode != 0:
        raise RuntimeError(f"canonical V4 validation failed: {proc.stderr or proc.stdout}")
    report = json.loads(proc.stdout)
    if report.get("ok") is not True:
        raise RuntimeError(f"canonical V4 validation returned non-PASS: {report}")
    kit = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if len(kit.get("courses", [])) != 1:
        raise RuntimeError("fixture must contain exactly one course")
    actual = [a.get("type") for a in kit["courses"][0].get("activities", [])]
    if actual != FAMILIES:
        raise RuntimeError(f"fixture family order mismatch: {actual}")
    for item in kit["courses"][0]["activities"][:2]:
        if "assessmentRole" in item:
            raise RuntimeError(f"non-scored family contaminated by assessmentRole: {item['type']}")
    svg = kit.get("assets", [{}])[0].get("data", "")
    if 'xmlns="http://www.w3.org/2000/svg"' not in svg:
        raise RuntimeError("fixture lacks canonical safe SVG namespace")
    return {"validator": "PASS", "families": actual, "packageDigest": kit["packageRevisionDigest"]}


def exact_build_check(directory: Path) -> dict:
    outputs = [directory / "build-a.html", directory / "build-b.html"]
    evidence = []
    for output in outputs:
        proc = command(sys.executable, "-B", "apps/learnit-next/build.py", "--output", str(output))
        if proc.returncode != 0:
            raise RuntimeError(f"Learn-it Next build failed: {proc.stderr or proc.stdout}")
        data = output.read_bytes()
        evidence.append({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    if evidence[0] != evidence[1]:
        raise RuntimeError(f"two builds differ: {evidence}")
    if evidence[0] != {"bytes": EXPECTED_BYTES, "sha256": EXPECTED_SHA256}:
        raise RuntimeError(f"QA-only branch drifted from R3 artifact: {evidence[0]}")
    return {"builds": evidence, "artifact": outputs[0]}


def static_boundary_check() -> dict:
    render = (ROOT / "apps/learnit-next/src/ui/render.js").read_text(encoding="utf-8")
    atlas_session = (ROOT / "apps/learnit-next/src/integration/atlas/session.js").read_text(encoding="utf-8")
    atlas_surface = (ROOT / "apps/learnit-next/src/integration/atlas/surface.js").read_text(encoding="utf-8")
    presenters = (ROOT / "apps/learnit-next/src/ui/activity_presenters.js").read_text(encoding="utf-8")
    projection = (ROOT / "apps/learnit-next/src/integration/atlas/activity_projection.js").read_text(encoding="utf-8")

    supported_presenters = [family for family in FAMILIES if f"case '{family}'" in presenters]
    supported_projection = [family for family in FAMILIES if f"case '{family}'" in projection]
    if supported_presenters != FAMILIES or supported_projection != FAMILIES:
        raise RuntimeError("qualified eight-family seams are not present; this is not the intended JOB05 contradiction")

    classic_two_family = bool(re.search(
        r"activity\.type\s*===\s*'qcm'\s*\?\s*renderQcmForm\([\s\S]*?:\s*renderFillForm\(",
        render,
    ))
    atlas_two_family = (
        "if (activity.type === 'qcm')" in atlas_session
        and "if (activity.type === 'fill')" in atlas_session
        and "ATLAS_ACTIVITY_TYPE_UNSUPPORTED" in atlas_session
    )
    atlas_requires_assessment_role = "typeof activity.assessmentRole === 'string'" in atlas_surface
    if not (classic_two_family and atlas_two_family and atlas_requires_assessment_role):
        raise RuntimeError("expected served-path contradiction was not found at the frozen R3 boundaries")
    return {
        "presenterFamilies": supported_presenters,
        "projectionFamilies": supported_projection,
        "classicRoute": "qcm-or-fill-only",
        "atlasRoute": "qcm-fill-only",
        "atlasCompatibilityRequiresAssessmentRoleOnEveryActivity": True,
    }


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        pass


@contextmanager
def serve(directory: Path):
    handler = partial(QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def browser_probe(artifact: Path, width: int, height: int) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is required for the real served/browser JOB05 probe") from exc

    unexpected_network: list[str] = []
    with sync_playwright() as p:
        launch = {"headless": True}
        chromium_path = os.environ.get("CHROMIUM_EXECUTABLE")
        if chromium_path:
            launch["executable_path"] = chromium_path
        browser = p.chromium.launch(**launch)
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        page.on("request", lambda req: unexpected_network.append(req.url) if not req.url.startswith(("http://127.0.0.1:", "blob:", "data:")) else None)
        base_url = os.environ["JOB05_BASE_URL"]
        page.goto(f"{base_url}/{artifact.name}", wait_until="domcontentloaded")
        page.locator("#kit-file").set_input_files(str(FIXTURE))
        page.locator("button[type=submit]", has_text="Importer").click()
        page.locator('[data-learnit-next-app][aria-busy="false"]').wait_for()
        course = page.locator(".course-card", has_text="QA Student V0.1 — cycle de l’eau").first
        course.wait_for()
        import_ok = course.is_visible()
        start = course.locator('button[data-course-learning-action="learn"]')
        start.click()
        page.locator('[data-learnit-next-app][aria-busy="false"]').wait_for()
        lesson = page.locator('[data-activity-presentation="lesson"]')
        notice = page.locator(".notice-error").first
        evidence = {
            "viewport": [width, height],
            "import": import_ok,
            "lessonPresenterVisible": lesson.count() > 0 and lesson.first.is_visible(),
            "errorVisible": notice.count() > 0 and notice.is_visible(),
            "errorText": notice.inner_text().strip() if notice.count() else "",
            "unexpectedNetwork": unexpected_network,
        }
        context.close()
        browser.close()
        return evidence


def run() -> dict:
    fixture = canonical_fixture_check()
    static = static_boundary_check()
    with tempfile.TemporaryDirectory(prefix="learnit-job05-") as tmp_name:
        tmp = Path(tmp_name)
        build = exact_build_check(tmp)
        artifact: Path = build.pop("artifact")
        with serve(tmp) as base_url:
            previous = os.environ.get("JOB05_BASE_URL")
            os.environ["JOB05_BASE_URL"] = base_url
            try:
                desktop = browser_probe(artifact, 1365, 768)
                mobile = browser_probe(artifact, 390, 844)
            finally:
                if previous is None:
                    os.environ.pop("JOB05_BASE_URL", None)
                else:
                    os.environ["JOB05_BASE_URL"] = previous

    reproduced = all([
        desktop["import"], mobile["import"],
        not desktop["lessonPresenterVisible"], not mobile["lessonPresenterVisible"],
        desktop["errorVisible"], mobile["errorVisible"],
        not desktop["unexpectedNetwork"], not mobile["unexpectedNetwork"],
    ])
    return {
        "job": "STUDENT_V01_JOB05_CONTRADICTORY_QA",
        "qualifiedProductBase": "8fa25844cf9ddf7c2429f730d818b3518c46de04",
        "fixture": fixture,
        "buildIdentity": build,
        "staticBoundary": static,
        "desktop": desktop,
        "mobile": mobile,
        "productGapReproduced": reproduced,
        "defectOwner": "PRESENTATION_UI" if reproduced else "UNKNOWN_NEEDS_CONTROL_ROOM",
        "finalVerdict": "HOLD_STUDENT_V01_JOB05_PRODUCT_GAP" if reproduced else "HOLD_STUDENT_V01_JOB05_QA_NEEDS_REWORK",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    try:
        result = run()
    except Exception as exc:
        print(json.dumps({"qaHarness": "ERROR", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["productGapReproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
