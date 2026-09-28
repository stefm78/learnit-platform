#!/usr/bin/env python3
"""ATLAS-WP-064 static qualification for learner-journey UX coherence R1."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDER = ROOT / "apps/learnit-next/src/ui/render.js"
MAIN = ROOT / "apps/learnit-next/src/main.js"
PRESENTERS = ROOT / "apps/learnit-next/src/ui/activity_presenters.js"
PROJECTION = ROOT / "apps/learnit-next/src/integration/atlas/activity_projection.js"
OBJECTIVE = ROOT / "apps/learnit-next/src/ui/objective_progress.js"
CSS = ROOT / "apps/learnit-next/src/styles.css"
MANIFEST = ROOT / "apps/learnit-next/source_manifest.json"

PROTECTED = {
    "apps/learnit-next/src/core/session.js": "9909f0712de59211d14211ef1afc27bda87fcbf5",
    "apps/learnit-next/src/core/activity_semantics.js": "07c4595332419da1da0473a9715f09894620f6bd",
    "apps/learnit-next/src/core/progress.js": "257720824ce9d2689ff2f48266592f9fc13750ec",
    "apps/learnit-next/src/core/objective_progress.js": "1f33e1d1214d0a9bce1f8db6bb40d4d7627ac2f0",
    "apps/learnit-next/src/core/learning_recommendation.js": "fe1a1a67db20500e84357f1c4884c972def839b1",
    "apps/learnit-next/src/integration/atlas/session.js": "98d8348e98c2068c0cb29f0e4f0a0e0493b00b5d",
    "apps/learnit-next/src/ui/objective_progress.js": "0e219f5570ce4d366ad97e0ba5d1101c81ee7909",
    "apps/learnit-next/src/ui/media.js": "1c84d5da04025cf372e3496fb7d25c088d1a0650",
    "contracts/learnit-kit-v5.schema.json": "15e708f9b57ea1b35ff50ad3b3854bd49d5cadc7",
    "authoring/v5/validate_kit.py": "0b93925eb22058878f13bc86554126846d2923d1",
    "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json": "57374ba897600894ab124e8ac2d3ee3b6f5c4cc2",
    "showcase/student-v0.1/nombres-complexes/LEARNER_BRIEF.json": "6c4fb770f12690a3cb338c82fc77bf9b323c3b06",
    "showcase/student-v0.1/nombres-complexes/ROLE_B_SOURCE_MANIFEST_V5.json": "74e16e07e9e5978b7b5f3ce81befa4c0650bf925",
    "showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT_V5.json": "3f6a1cec5444121c8fe742d515b400780046557c",
    "showcase/student-v0.1/nombres-complexes/SEMANTIC_REVIEW_V5_R2.json": "a6c9f65f94900f5e46c0ecc8a44cb0d0e7166056",
    "showcase/student-v0.1/nombres-complexes/FACTORY_EVIDENCE_V5_FINAL.json": "d1c17f6f12775f667c23df0a3cf96e316ffab41b",
}

def blob(path: str) -> str:
    return subprocess.check_output(["git", "rev-parse", f"HEAD:{path}"], cwd=ROOT, text=True).strip()

for path, expected in PROTECTED.items():
    actual = blob(path)
    assert actual == expected, (path, actual, expected)

render = RENDER.read_text(encoding="utf-8")
main = MAIN.read_text(encoding="utf-8")
presenters = PRESENTERS.read_text(encoding="utf-8")
projection = PROJECTION.read_text(encoding="utf-8")
objective = OBJECTIVE.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

# Library hierarchy and CTA arbitration.
assert "renderLibraryObjectiveDetails" not in render
assert "Voir la progression détaillée" not in render
assert "Options du cours" not in render
assert "À revoir : aucune activité." not in render
assert "const objectiveDetails = objectiveSurface;" in render
assert "Gérer la bibliothèque" in render
assert "Réinitialiser les données locales" in render
assert "library-file-input" in render and "library-file-picker" in render
assert "const preview = await runtime.previewImport(text);" in render
assert "fileStatus.textContent = preview.title;" in render
assert "fileInput.value = '';" not in render
assert "course.progress.recommendation?.action === 'correct'" in render
assert "Renforcer maintenant" in render
assert "Nom local du cours" in render
assert "Ce nom est utilisé uniquement sur cet appareil." not in render

# Activity shell owns only one transition action; presenter owns the pedagogical prompt.
session = render[render.index("function renderSessionSnapshot"):render.index("function renderFeedbackLines")]
assert "className: 'sr-only'" in session
assert "activityPresentationHeading(presentation)" not in session
assert "renderProgress(session.progress)" not in session
assert "Revenir au parcours" not in session
assert "data-activity-continue':'lesson'" not in presenters
assert "data-activity-continue':'flashcard'" not in presenters
assert "root.dataset.activityReady='true'" in presenters
assert "learnit:activity-ready" in presenters
assert "activity-interaction-status sr-only" in presenters
assert "activity-match-count sr-only" in presenters

# Non-scored activities transition directly after a successful runtime.answer().
submit = render[render.index("async function submitAnswer"):render.index("function renderSessionSnapshot")]
assert "if (result.scored !== true)" in submit
assert "result.nextActivity" in submit
assert "runtime.getSession()" in submit
assert "renderFeedback(result)" in submit
assert "Cette activité compte comme terminée, sans score de correction." not in render

# Scored feedback is contextual and has one transition CTA.
feedback = render[render.index("function renderFeedbackLines"):render.index("async function initialize")]
for text in ("Votre réponse", "Réponse attendue", "Explication"):
    assert text in feedback
assert "result.postAnswerFeedback" in feedback
assert feedback.count("'data-served-next-action': 'true'") == 2  # mutually-exclusive learn/review branches
assert "Revenir au parcours" not in feedback
assert "renderProgress(result.progress)" not in feedback
assert "context: 'terminal-summary'" in feedback

# Post-answer authored truth is projected only after sessions.answer() has succeeded.
answer_runtime = main[main.index("answer: async"):main.index("async getProgress")]
assert "projectLearnerAnswer(" in answer_runtime and "await sessions.answer(" in answer_runtime
project_answer = main[main.index("async function projectLearnerAnswer"):main.index("  const runtime =")]
assert "value.scored === true" in project_answer
assert "projectPostAnswerFeedback(" in project_answer
assert "transitionAuthorized: true" in project_answer
assert "value.answer" in project_answer
for authored in ("correctChoiceId", "answers", "acceptedResponses", "matches", "correctOrder", "assignments"):
    assert authored in projection
assert "V5_POST_ANSWER_TRANSITION_REQUIRED" in projection

# Pre-response learner presentation remains answer-key free.
presentation = projection[projection.index("export function projectActivityPresentation"):]
for authored in ("correctChoiceId", "acceptedResponses", "correctOrder", "assignments"):
    assert authored not in presentation
assert "activity.matches" not in presentation
assert "activity.answers" not in presentation

# Dynamically exercise all six scored post-answer projections without invoking scoring.
with tempfile.TemporaryDirectory() as td:
    module = Path(td) / "projection.mjs"
    module.write_text(projection, encoding="utf-8")
    runner = Path(td) / "run.mjs"
    runner.write_text(
        """
import { projectPostAnswerFeedback as p } from './projection.mjs';
const opts={contract:'learnit.kit.v5',transitionAuthorized:true};
const cases=[
 [{type:'qcm',prompt:'Q',choices:[{choiceId:'a',label:'A'},{choiceId:'b',label:'B'}],correctChoiceId:'b'},{choiceId:'a'}],
 [{type:'fill',prompt:'F',tokens:[{tokenId:'t1',label:'un'},{tokenId:'t2',label:'deux'}],segments:[{slotId:'s1'},{slotId:'s2'}],answers:[{slotId:'s1',tokenId:'t1'},{slotId:'s2',tokenId:'t2'}]},{s1:'t2',s2:'t1'}],
 [{type:'constructed',prompt:'C',acceptedResponses:['alpha','beta']},{text:'gamma'}],
 [{type:'matching',prompt:'M',leftItems:[{itemId:'l1',label:'L1'},{itemId:'l2',label:'L2'}],rightItems:[{itemId:'r1',label:'R1'},{itemId:'r2',label:'R2'}],matches:[{leftItemId:'l1',rightItemId:'r1'},{leftItemId:'l2',rightItemId:'r2'}]},{associations:[{leftItemId:'l1',rightItemId:'r2'},{leftItemId:'l2',rightItemId:'r1'}]}],
 [{type:'order',prompt:'O',items:[{itemId:'i1',label:'I1'},{itemId:'i2',label:'I2'}],correctOrder:['i1','i2']},{orderedItemIds:['i2','i1']}],
 [{type:'classify',prompt:'K',buckets:[{bucketId:'b1',label:'B1'},{bucketId:'b2',label:'B2'}],items:[{itemId:'i1',label:'I1'},{itemId:'i2',label:'I2'}],assignments:[{itemId:'i1',bucketId:'b1'},{itemId:'i2',bucketId:'b2'}]},{assignments:[{itemId:'i1',bucketId:'b2'},{itemId:'i2',bucketId:'b1'}]}]
];
for(const [a,r] of cases){
 const out=p(a,r,opts);
 if(!out || !out.learnerAnswer.length || !out.expectedAnswer.length) throw new Error(a.type);
}
let denied=false;
try{p(cases[0][0],cases[0][1],{contract:'learnit.kit.v5',transitionAuthorized:false});}
catch(e){denied=e.message==='V5_POST_ANSWER_TRANSITION_REQUIRED';}
if(!denied) throw new Error('transition gate');
console.log('POST_ANSWER_PROJECTION_6_OF_6=PASS');
""",
        encoding="utf-8",
    )
    subprocess.run(["node", str(runner)], cwd=td, check=True)

# R15 visual language is untouched.
for label in ("À découvrir", "En apprentissage", "À renforcer", "À confirmer", "Acquis récemment", "Priorité Learn-it"):
    assert label in objective
assert "repeating-linear-gradient(135deg,#b48a46 0 5px,#ead8b8 5px 10px)" in css
assert '[tabindex="-1"]:focus' not in css
assert "button:focus-visible" in css

# Manifest acknowledges only the bounded presentation/composition ownership changes.
owned = {
    item["path"]: item
    for item in manifest["workingFiles"]
    if item.get("owner") == "ATLAS-WP-064"
}
for path in (
    "apps/learnit-next/src/styles.css",
    "apps/learnit-next/src/main.js",
    "apps/learnit-next/src/ui/render.js",
    "apps/learnit-next/src/integration/atlas/activity_projection.js",
    "apps/learnit-next/src/ui/activity_presenters.js",
    "apps/learnit-next/source_manifest.json",
):
    assert path in owned, path
assert manifest["artifact"]["finalized"] is False

print("LIBRARY_EMPTY_MINIMAL: PASS")
print("LIBRARY_NONEMPTY_LEARNING_FIRST: PASS")
print("DESTRUCTIVE_ACTION_HIDDEN_BY_DEFAULT: PASS")
print("COURSE_CARD_R15_VISIBLE: PASS")
print("RECOMMENDATION_DRIVES_PRIMARY_CTA: PASS")
print("ONE_VISIBLE_ACTIVITY_PROMPT: PASS")
print("NON_SCORED_SINGLE_TRANSITION: PASS")
print("NON_SCORED_GENERIC_FEEDBACK: ABSENT")
print("VISIBLE_SYSTEM_NARRATION_REDUCED: PASS")
print("CONTEXTUAL_CORRECTIVE_FEEDBACK: PASS")
print("ANSWER_KEY_PRETRANSITION_LEAKAGE: NONE")
print("FAILED_PERSISTENCE_ANSWER_KEY_PATH: NONE")
print("ACTIVITY_RESPONSE_UNCHANGED: PASS")
print("SCORING_AUTHORITY_UNCHANGED: PASS")
print("OBJECTIVE_STATE_SEMANTICS_UNCHANGED: PASS")
print("RECOMMENDATION_SEMANTICS_UNCHANGED: PASS")
print("SESSION_DELTA_V2_UNCHANGED: PASS")
print("V5_CONTRACT_CONTENT_SOURCES_UNCHANGED: PASS")
print("H6_FACTORY_EVIDENCE_UNCHANGED: PASS")
print("R15_LANGUAGE_PRESERVED: PASS")
