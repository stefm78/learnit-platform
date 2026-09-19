#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps" / "learnit-next"
MAIN = APP / "src" / "main.js"
RENDER = APP / "src" / "ui" / "render.js"
SURFACE = APP / "src" / "integration" / "atlas" / "surface.js"
PROJECTION = APP / "src" / "integration" / "atlas" / "activity_projection.js"
FIXTURE = APP / "tests" / "fixtures" / "student_v01_v4_runtime.json"
ATLAS_FIXTURE = ROOT / "authoring" / "v2" / "atlas" / "nombres_complexes_atlas.json"
ARTIFACT = APP / "dist" / "learnit-next.html"
FORBIDDEN_ACTIVITY_KEYS = {
    "correctChoiceId",
    "answers",
    "acceptedResponses",
    "matches",
    "correctOrder",
    "assignments",
}
SCORED_FAMILIES = {"qcm", "fill", "constructed", "matching", "order", "classify"}
FAMILIES = ["qcm", "fill", "constructed", "lesson", "flashcard", "matching", "order", "classify"]

main = MAIN.read_text(encoding="utf-8")
render = RENDER.read_text(encoding="utf-8")
surface = SURFACE.read_text(encoding="utf-8")
projection = PROJECTION.read_text(encoding="utf-8")
fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
atlas_fixture = json.loads(ATLAS_FIXTURE.read_text(encoding="utf-8"))

for source in (MAIN, RENDER, SURFACE):
    subprocess.run(["node", "--check", str(source)], cwd=ROOT, check=True)

assert "projectActivityPresentation" in main
assert "projectLearnerActivity" in main
assert "packageAssets ?? []" in main
assert "activityRevisionId: activity.activityRevisionId" in main
assert "presentation: projectActivityPresentation" in main
assert "projectLearnerSession(await sessions.startCourse" in main
assert "projectLearnerSession(await sessions.startReviewQueue" in main
assert "projectLearnerAnswer(await sessions.answer" in main
assert "projectLearnerSession(await sessions.resumeActiveCourse" in main
assert "projectLearnerSession(await sessions.getSession" in main
for field in FORBIDDEN_ACTIVITY_KEYS:
    assert f"activity.{field}" not in main, field

assert "renderActivityPresentation" in render
assert "readActivityResponse" in render
assert "renderServedActivityForm" in render
assert "data-served-activity-submit" in render
session_slice = render[render.index("function renderSessionSnapshot"):render.index("function renderFeedback")]
assert "renderQcmForm(" not in session_slice
assert "renderFillForm(" not in session_slice
assert "renderServedActivityForm(" in session_slice
assert "result.scored === true" in render
assert "Activité terminée" in render
assert "data-served-feedback" in render

assert "ATLAS_SUPPORTED_ACTIVITY_TYPES = new Set(['qcm', 'fill'])" in surface
compat = surface[surface.index("function compatibleAtlasCourse"):surface.index("function learnerObjectiveLabels")]
assert "ATLAS_SUPPORTED_ACTIVITY_TYPES.has(activity.type)" in compat
assert "typeof activity.assessmentRole === 'string'" in compat

families = [item["type"] for item in fixture["courses"][0]["activities"]]
assert families == FAMILIES
for family in families:
    assert f"case '{family}'" in projection


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return


@contextmanager
def artifact_server():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(QuietHandler, directory=str(ARTIFACT.parent)),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/{ARTIFACT.name}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def forbidden_hits(value: Any) -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_ACTIVITY_KEYS:
                hits.append(key)
            hits.extend(forbidden_hits(child))
    elif isinstance(value, list):
        for child in value:
            hits.extend(forbidden_hits(child))
    return hits


def assert_safe_activity(activity: dict[str, Any] | None, expected_type: str) -> None:
    assert activity is not None
    assert sorted(activity) == ["activityRevisionId", "presentation"], activity
    assert activity["presentation"]["type"] == expected_type, activity
    assert forbidden_hits(activity) == [], activity
    serialized = json.dumps(activity, ensure_ascii=False, sort_keys=True)
    for field in FORBIDDEN_ACTIVITY_KEYS:
        assert f'"{field}"' not in serialized, (field, serialized)


def response_for(activity: dict[str, Any]) -> dict[str, Any]:
    family = activity["type"]
    if family == "qcm":
        return {"choiceId": activity["correctChoiceId"]}
    if family == "fill":
        return {entry["slotId"]: entry["tokenId"] for entry in activity["answers"]}
    if family == "constructed":
        return {"text": activity["acceptedResponses"][0]}
    if family == "lesson":
        return {"acknowledged": True}
    if family == "flashcard":
        return {"revealed": True}
    if family == "matching":
        return {"associations": [dict(item) for item in activity["matches"]]}
    if family == "order":
        return {"orderedItemIds": list(activity["correctOrder"])}
    if family == "classify":
        return {"assignments": [dict(item) for item in activity["assignments"]]}
    raise AssertionError(family)


assert ARTIFACT.is_file(), "built Learn-it Next artifact is required for runtime integration proof"
with artifact_server() as url, sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
    context = browser.new_context(viewport={"width": 1024, "height": 768})
    page = context.new_page()
    page.goto(url)
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

    page.evaluate("async () => window.__LEARNIT_NEXT_TEST__.resetNextData()")
    imported = page.evaluate(
        "async payload => await window.__LEARNIT_NEXT_TEST__.importPackage(payload)",
        fixture,
    )
    course_install_id = imported["courses"][0]["courseInstallId"]
    session = page.evaluate(
        "async courseInstallId => await window.__LEARNIT_NEXT_TEST__.startCourse(courseInstallId)",
        course_install_id,
    )
    assert_safe_activity(session["currentActivity"], FAMILIES[0])

    source_activities = fixture["courses"][0]["activities"]
    for index, source in enumerate(source_activities):
        family = source["type"]
        assert_safe_activity(session["currentActivity"], family)

        if family == "constructed":
            media = session["currentActivity"]["presentation"]["media"]
            assert len(media) == 1, media
            assert media[0]["assetId"] == fixture["assets"][0]["assetId"]
            assert media[0]["data"] == fixture["assets"][0]["data"]
            assert media[0]["alt"] == fixture["assets"][0]["alt"]

        response = response_for(source)
        result = page.evaluate(
            """async args => await window.__LEARNIT_NEXT_TEST__.answer(
              args.activityRevisionId,
              args.response,
            )""",
            {
                "activityRevisionId": source["activityRevisionId"],
                "response": response,
            },
        )
        assert result["answer"] == response, (family, result["answer"], response)

        if family in SCORED_FAMILIES:
            assert result["scored"] is True, result
            assert result["correct"] is True, result
        else:
            assert result["scored"] is False, result
            assert "correct" not in result, result

        if index < len(source_activities) - 1:
            assert_safe_activity(result["nextActivity"], FAMILIES[index + 1])
        else:
            assert result["nextActivity"] is None, result

        session = page.evaluate("async () => await window.__LEARNIT_NEXT_TEST__.getSession()")
        if index < len(source_activities) - 1:
            assert_safe_activity(session["currentActivity"], FAMILIES[index + 1])
        else:
            assert session["currentActivity"] is None, session
            assert session["progress"]["isComplete"] is True, session["progress"]

    page.reload()
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    assert page.locator("[data-atlas-course-install-id]").count() == 0

    page.evaluate("async () => window.__LEARNIT_NEXT_TEST__.resetNextData()")
    atlas_imported = page.evaluate(
        "async payload => await window.__LEARNIT_NEXT_TEST__.importPackage(payload)",
        atlas_fixture,
    )
    assert atlas_imported["courses"], atlas_imported
    page.reload()
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    page.locator("[data-atlas-course-install-id]").first.wait_for()
    assert page.locator("[data-atlas-course-install-id]").count() >= 1

    context.close()
    browser.close()

print("STUDENT_V01_SERVED_V4_STATIC_PASS")
print("SERVED_RUNTIME_PROJECTION_BOUNDARY=PASS")
print("CURRENT_NEXT_LEARNER_SAFE=PASS")
print("FORBIDDEN_SECRET_KEYS_RECURSIVE=PASS")
print("ALL_EIGHT_RESPONSE_SHAPES=PASS")
print("SCORED_FAMILIES_RUNTIME=PASS")
print("NON_SCORED_RESULT_SHAPE=PASS")
print("TRUSTED_MEDIA_PROJECTION=PASS")
print("SERVED_GENERIC_PRESENTER_WIRING=PASS")
print("ATLAS_EXPLICIT_QCM_FILL_GATE=PASS")
print("ATLAS_RICH_REJECTED=PASS")
print("ATLAS_QCM_FILL_ACCEPTED=PASS")
