#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps" / "learnit-next"
MAIN = APP / "src" / "main.js"
RENDER = APP / "src" / "ui" / "render.js"
SURFACE = APP / "src" / "integration" / "atlas" / "surface.js"
PROJECTION = APP / "src" / "integration" / "atlas" / "activity_projection.js"
FIXTURE = APP / "tests" / "fixtures" / "student_v01_v4_runtime.json"

main = MAIN.read_text(encoding="utf-8")
render = RENDER.read_text(encoding="utf-8")
surface = SURFACE.read_text(encoding="utf-8")
projection = PROJECTION.read_text(encoding="utf-8")
fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

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
for field in ("correctChoiceId", "acceptedResponses", "correctOrder"):
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
assert families == ["qcm", "fill", "constructed", "lesson", "flashcard", "matching", "order", "classify"]
for family in families:
    assert f"case '{family}'" in projection

print("STUDENT_V01_SERVED_V4_STATIC_PASS")
print("SERVED_RUNTIME_PROJECTION_BOUNDARY=PASS")
print("SERVED_GENERIC_PRESENTER_WIRING=PASS")
print("ATLAS_EXPLICIT_QCM_FILL_GATE=PASS")
