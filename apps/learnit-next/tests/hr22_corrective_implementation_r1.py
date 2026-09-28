#!/usr/bin/env python3
"""Bounded static contract for JOB_23_HR22_CORRECTIVE_IMPLEMENTATION_R1."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps" / "learnit-next"
BASE = "c5f82d27b67c680cf18f07a79f390391a83d7a68"

render = (APP / "src/ui/render.js").read_text(encoding="utf-8")
css = (APP / "src/styles.css").read_text(encoding="utf-8")
objective = (APP / "src/ui/objective_progress.js").read_text(encoding="utf-8")
projection = (APP / "src/integration/atlas/activity_projection.js").read_text(encoding="utf-8")
manifest = json.loads((APP / "source_manifest.json").read_text(encoding="utf-8"))
schema = json.loads((ROOT / "contracts/learnit-kit-v5.schema.json").read_text(encoding="utf-8"))
kit = json.loads((ROOT / "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json").read_text(encoding="utf-8"))

def blob(path: str) -> str:
    return subprocess.check_output(["git", "rev-parse", f"HEAD:{path}"], cwd=ROOT, text=True).strip()

# Protected semantic authorities and exact content remain parent-identical.
protected = [
    "apps/learnit-next/src/core/session.js",
    "apps/learnit-next/src/core/activity_semantics.js",
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/core/objective_progress.js",
    "apps/learnit-next/src/core/learning_recommendation.js",
    "apps/learnit-next/src/main.js",
    "apps/learnit-next/src/integration/atlas/session.js",
    "apps/learnit-next/src/ui/activity_presenters.js",
    "contracts/learnit-kit-v5.schema.json",
    "authoring/v5/validate_kit.py",
    "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json",
]
for path in protected:
    assert blob(path) == subprocess.check_output(["git", "rev-parse", f"{BASE}:{path}"], cwd=ROOT, text=True).strip(), path
assert blob("apps/learnit-next/src/core/session.js") == "9909f0712de59211d14211ef1afc27bda87fcbf5"

# A — compact, learner-first Library and secondary management.
assert "node('p', { className: 'eyebrow', text: 'Bibliothèque' })" not in render
assert "text: 'Vos cours'" in render
assert "node('summary', { text: 'Gérer' })" in render
assert "node('summary', { text: 'Renommer' })" not in render
for token in (
    "ATLAS-WP-065 — HR22 bounded corrective implementation",
    ".learner-course-card .objective-progress-r15",
    ".learner-course-card .learner-course-actions",
    "@media (max-width: 600px)",
):
    assert token in css

# B — activity exhaustion is not presented as learning mastery.
assert "Cours terminé" not in render
assert "Parcours d’activités terminé" in render
assert "renderCourseCompletionGuidance" in render
assert "course.progress.recommendation?.action === 'correct'\n          && reviewQueue.total > 0;" in render
assert "&& !course.progress.isComplete" not in render
for action in ("correct", "validate", "revisit-later", "continue-training", "start-training"):
    assert f"recommendation?.action === '{action}'" in render
assert "ne propose pas encore de nouvelle validation" in render.lower()
assert "n’indique pas encore de moment précis" in render

# C — correct feedback does not echo an identical expected answer; comparisons use no list bullets/arrows.
assert "feedbackProjection && !result.correct" in render
feedback_start = render.index("function renderFeedbackLines")
feedback_lines = render[feedback_start:render.index("function renderFeedback(", feedback_start)]
assert "node('ul'" not in feedback_lines and "node('li'" not in feedback_lines
assert "feedback-lines" in feedback_lines and "feedback-line" in feedback_lines
post = projection[projection.index("export function projectPostAnswerFeedback"):projection.index("export function projectActivityPresentation")]
assert " → " not in post
for phrase in ("Élément :", "votre choix :", "réponse attendue :"):
    assert phrase in post

# D — no hierarchy is invented. V5 and the exact authored kit expose course -> objectives/activities only.
course_schema = schema["$defs"]["course"]
course_props = set(course_schema["properties"])
assert {"objectives", "activities"} <= course_props
assert not ({"chapters", "chapter", "phases", "groups", "objectiveGroups"} & course_props)
course = kit["courses"][0]
assert set(course).isdisjoint({"chapters", "chapter", "phases", "groups", "objectiveGroups"})
assert len(course["activities"]) == 10
assert sum(int(a["estimatedMinutes"]) for a in course["activities"]) == 39

# E — preserve reservoir interaction and add explicit selected-state semantics.
assert "reservoir.addEventListener('click'" in objective
assert "reservoir.addEventListener('focus'" in objective
for token in ("aria-pressed", "aria-controls", "data-objective-progress-r15-selected"):
    assert token in objective
assert '[data-objective-progress-r15-selected="true"]' in css

# Dynamic post-answer projection: matching/classify retain authored truth but no mathematical-looking arrows.
with tempfile.TemporaryDirectory() as td:
    module = Path(td) / "projection.mjs"
    module.write_text(projection, encoding="utf-8")
    runner = Path(td) / "run.mjs"
    runner.write_text(
        """
import { projectPostAnswerFeedback as p } from './projection.mjs';
const opts={contract:'learnit.kit.v5',transitionAuthorized:true};
const matching={type:'matching',prompt:'M',leftItems:[{itemId:'l1',label:'z'},{itemId:'l2',label:'w'}],rightItems:[{itemId:'r1',label:'1+i'},{itemId:'r2',label:'2-i'}],matches:[{leftItemId:'l1',rightItemId:'r1'},{leftItemId:'l2',rightItemId:'r2'}]};
const out=p(matching,{associations:[{leftItemId:'l1',rightItemId:'r2'},{leftItemId:'l2',rightItemId:'r1'}]},opts);
if(out.learnerAnswer.some(x=>x.includes('→'))||out.expectedAnswer.some(x=>x.includes('→'))) throw new Error('ambiguous arrow');
if(!out.learnerAnswer.every(x=>x.includes('Élément :')&&x.includes('votre choix :'))) throw new Error('learner structure');
if(!out.expectedAnswer.every(x=>x.includes('Élément :')&&x.includes('réponse attendue :'))) throw new Error('expected structure');
console.log('POST_ANSWER_COMPARISON_TEXT=PASS');
""",
        encoding="utf-8",
    )
    subprocess.run(["node", str(runner)], cwd=td, check=True)

# Manifest is bound to the new presentation blobs only.
owned = {item["path"]: item for item in manifest["workingFiles"] if item.get("owner") == "ATLAS-WP-065"}
expected_owned = {
    "apps/learnit-next/src/styles.css",
    "apps/learnit-next/src/ui/render.js",
    "apps/learnit-next/src/ui/objective_progress.js",
    "apps/learnit-next/src/integration/atlas/activity_projection.js",
    "apps/learnit-next/source_manifest.json",
}
assert expected_owned <= set(owned)
assert manifest["artifact"]["finalized"] is False

print("HR22_A_LIBRARY_DENSITY=PASS")
print("HR22_B_TERMINAL_TRUTHFULNESS=PASS")
print("HR22_C_FEEDBACK_CLARITY=PASS")
print("HR22_D_HIERARCHY=NO_CHANGE_AFTER_AUDIT")
print("HR22_E_SELECTED_OBJECTIVE=PASS")
print("SESSION_JS_UNCHANGED=PASS")
print("SCORING_AUTHORITY_UNCHANGED=PASS")
print("OBJECTIVE_STATE_SEMANTICS_UNCHANGED=PASS")
print("RECOMMENDATION_SEMANTICS_UNCHANGED=PASS")
print("V5_EXACT_SHOWCASE_UNCHANGED=PASS")
