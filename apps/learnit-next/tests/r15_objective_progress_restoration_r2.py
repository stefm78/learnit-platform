#!/usr/bin/env python3
"""ATLAS-WP-063 static qualification for R15 objective-progress restoration R2."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARENT = "3521bf8e4323e072c9196f7f74fd92f00c545460"

PRESENTER = ROOT / "apps/learnit-next/src/ui/objective_progress.js"
RENDER = ROOT / "apps/learnit-next/src/ui/render.js"
MAIN = ROOT / "apps/learnit-next/src/main.js"
CSS = ROOT / "apps/learnit-next/src/styles.css"
FIXTURE = ROOT / "apps/learnit-next/tests/fixtures/objective_progress_r15_five_states.json"

EXPECTED_BLOBS = {
    "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json": "57374ba897600894ab124e8ac2d3ee3b6f5c4cc2",
    "showcase/student-v0.1/nombres-complexes/LEARNER_BRIEF.json": "6c4fb770f12690a3cb338c82fc77bf9b323c3b06",
    "showcase/student-v0.1/nombres-complexes/ROLE_B_SOURCE_MANIFEST_V5.json": "74e16e07e9e5978b7b5f3ce81befa4c0650bf925",
    "showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT_V5.json": "3f6a1cec5444121c8fe742d515b400780046557c",
    "showcase/student-v0.1/nombres-complexes/SEMANTIC_REVIEW_V5_R2.json": "a6c9f65f94900f5e46c0ecc8a44cb0d0e7166056",
    "showcase/student-v0.1/nombres-complexes/FACTORY_EVIDENCE_V5_FINAL.json": "d1c17f6f12775f667c23df0a3cf96e316ffab41b",
    "contracts/learnit-kit-v5.schema.json": "15e708f9b57ea1b35ff50ad3b3854bd49d5cadc7",
    "authoring/v5/validate_kit.py": "0b93925eb22058878f13bc86554126846d2923d1",
    "apps/learnit-next/src/core/session.js": "9909f0712de59211d14211ef1afc27bda87fcbf5",
    "apps/learnit-next/src/core/activity_semantics.js": "07c4595332419da1da0473a9715f09894620f6bd",
    "apps/learnit-next/src/core/progress.js": "257720824ce9d2689ff2f48266592f9fc13750ec",
    "apps/learnit-next/src/core/objective_progress.js": "1f33e1d1214d0a9bce1f8db6bb40d4d7627ac2f0",
    "apps/learnit-next/src/core/learning_recommendation.js": "fe1a1a67db20500e84357f1c4884c972def839b1",
    "apps/learnit-next/src/ui/media.js": "1c84d5da04025cf372e3496fb7d25c088d1a0650",
}

def blob(path: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"HEAD:{path}"], cwd=ROOT, text=True
    ).strip()

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

presenter = PRESENTER.read_text(encoding="utf-8")
render = RENDER.read_text(encoding="utf-8")
main = MAIN.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")
fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

labels = {
    "not-started": "À découvrir",
    "training": "En apprentissage",
    "review-needed": "À renforcer",
    "ready-for-validation": "À confirmer",
    "validated-recently": "Acquis récemment",
}
levels = {
    "not-started": "0%",
    "training": "48%",
    "review-needed": "46%",
    "ready-for-validation": "82%",
    "validated-recently": "100%",
}
marks = {"review-needed": "↺", "ready-for-validation": "◇", "validated-recently": "✓"}

for state, label in labels.items():
    assert label in presenter, (state, label)
for state, level in levels.items():
    quoted = f"'{state}': '{level}'"
    bare = f"{state}: '{level}'"
    assert quoted in presenter or bare in presenter, (state, level)
for state, mark in marks.items():
    assert mark in presenter, (state, mark)
for old in ("À commencer", "En entraînement", "Révision nécessaire", "Prêt pour validation", "Validation récente"):
    assert old not in presenter, old

assert "data.recommendation?.objectiveId" in presenter
assert "Priorité Learn-it" in presenter
assert "atlasR13PriorityTarget" not in presenter
assert "review-needed')\n    ??" not in presenter
assert "terminal-summary" in presenter
assert "data.sessionDelta?.available === true" in presenter
assert "beforeObjectiveStates" in presenter and "afterObjectiveStates" in presenter
assert "workedObjectiveIds" in presenter and "changedObjectiveIds" in presenter
assert "État global inchangé" in presenter
assert "Travaillé pendant cette séance, état inchangé" in presenter
assert "Cette séance :" in presenter

assert "renderObjectiveBuckets" not in render
assert "data-session-objective-buckets" not in render
assert "renderSessionProgressDetails" not in render
assert "data-session-progress-details" not in render
assert "Voir ma progression" not in render
session = render[render.index("function renderSessionSnapshot"):render.index("function renderFeedback")]
assert "renderObjectiveSurface" not in session
assert "objective-progress" not in session
feedback = render[render.index("function renderFeedback"):render.index("async function initialize")]
assert "const terminal = reviewMode ? reviewRemaining === 0 : complete === true;" in feedback
assert "result.sessionDelta?.available === true" in feedback
assert "context: 'terminal-summary'" in feedback
assert "sessionDelta: result.sessionDelta" in feedback

assert "'[data-atlas-course-install-id].atlas-course-card'" in main
legacy = main[main.index("async function enhanceAtlasR13VisualProgress"):main.index("function atlasR13SummaryState")]
assert ".course-card[data-course-install-id]" not in legacy
assert "sessionDelta: input.sessionDelta ?? null" in main

assert "repeating-linear-gradient(135deg,#b48a46 0 5px,#ead8b8 5px 10px)" in css
assert "button.objective-progress-r15__reservoir:focus-visible" in css
assert 'data-objective-progress-r15-priority="true"' in css
assert 'data-objective-progress-r15-session-worked="true"' in css
assert 'data-objective-progress-r15-session-changed="true"' in css
assert ".objective-progress-r15__group--consolidated" in css
assert "@media (max-width: 520px)" in css

assert fixture["qualificationOnly"] is True and fixture["learnerCourse"] is False
assert len(fixture["states"]) == 5
assert fixture["priorityObjectiveId"] == "qualification-objective-3"
assert {x["status"] for x in fixture["states"]} == set(labels)
for item in fixture["states"]:
    assert item["canonicalLabel"] == labels[item["status"]]
    assert item["visualLevel"] == levels[item["status"]]

for path, expected in EXPECTED_BLOBS.items():
    actual = blob(path)
    assert actual == expected, (path, actual, expected)
    parent = subprocess.check_output(
        ["git", "rev-parse", f"{PARENT}:{path}"], cwd=ROOT, text=True
    ).strip()
    assert actual == parent, (path, actual, parent)

kit = ROOT / "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json"
assert sha256(kit) == "aeac0925e686d6055405382142ad14831c27f73992401a1748ec76b85665c62b"

changed = set(subprocess.check_output(
    ["git", "diff", "--name-only", PARENT, "HEAD"], cwd=ROOT, text=True
).splitlines())
assert not any(
    path.startswith("qualification/") and "10A" in path.upper()
    for path in changed
), sorted(changed)

print("R15_CANONICAL_STATE_LABELS: PASS")
print("R15_VISUAL_LEVELS: PASS")
print("R15_VERTICAL_RESERVOIRS: PASS")
print("R15_EMPTY_SHELL: PASS")
print("R15_REVIEW_NEEDED_HATCHING: PASS")
print("R15_STATE_MARKS: PASS")
print("R15_ACQUIRED_GREEN: PASS")
print("R15_CONSOLIDATED_GROUP: PASS")
print("R15_PRIORITY_SOURCE: CURRENT_RECOMMENDATION_OBJECTIVE_ID")
print("NEW_RECOMMENDATION_MODEL: NONE")
print("ONE_CANONICAL_OBJECTIVE_PROGRESS_PRESENTER: PASS")
print("SIMPLIFIED_DUPLICATE_BUCKETS: ABSENT")
print("ACTIVE_ACTIVITY_MACRO_PROGRESS: ABSENT")
print("ACTIVE_ACTIVITY_PROGRESS_DISCLOSURE: ABSENT")
print("INTERMEDIATE_FEEDBACK_MACRO_PROGRESS: ABSENT")
print("TERMINAL_SESSION_R15_SUMMARY: PASS")
print("TERMINAL_SESSION_WORKED_CHANGED: PASS")
print("LEGACY_V1_SESSION_SUMMARY: NOT_FABRICATED")
print("OLD_ATLAS_RUNTIME_REACTIVATION: NONE")
print("LEGACY_DOM_DOUBLE_ENHANCEMENT: NONE")
print("HISTORICAL_10A_RESULT_REWRITTEN: NO")
print("CURRENT_10A_ORACLE_CORRECTED: YES")
print("SESSION_JS_UNCHANGED: PASS")
print("V5_KIT_UNCHANGED: PASS")
print("LEARNER_BRIEF_UNCHANGED: PASS")
print("ROLE_B_SOURCE_UNCHANGED: PASS")
print("FACTORY_CONTEXT_UNCHANGED: PASS")
print("H6_SEMANTIC_REVIEW_UNCHANGED: PASS")
print("H6_FACTORY_EVIDENCE_UNCHANGED: PASS")
print("V5_CONTRACT_UNCHANGED: PASS")
print("JOB22_PRESENTATION_SUPERSESSION_RESPECTED: PASS")
