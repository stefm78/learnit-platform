#!/usr/bin/env python3
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
SURFACE = APP / "src/integration/atlas/surface.js"
SESSION = APP / "src/integration/atlas/session.js"


def run_node(source: str):
    proc = subprocess.run(
        ["node", "-e", source],
        cwd=APP,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout)


class IndependentAtlasM2UxClarityQa(unittest.TestCase):
    def test_two_same_action_items_cannot_look_identical(self):
        result = run_node(r"""
const assert=require('node:assert/strict');
const T=require('./src/ui/atlas_today.js');
const courseRef={packageLineageId:'p',courseLineageId:'c'};
const rev={packageLineageId:'p',packageRevisionId:'r',packageDigest:'sha256:'+'a'.repeat(64)};
function obj(id){return {courseRef,objectiveId:id};}
function act(id){return {courseRef,activityLineageId:id};}
const items=[
 {position:0,objectiveRef:obj('opaque-111'),activityRef:act('a1'),action:'start-practice',executionClass:'practice',estimatedMinutes:4},
 {position:1,objectiveRef:obj('opaque-222'),activityRef:act('a2'),action:'start-practice',executionClass:'practice',estimatedMinutes:4},
];
const payload={schemaVersion:'atlas.session-plan.v1',engineVersion:'qa',courseRef,contentRevisionRef:rev,durationMinutes:15,items,totalEstimatedMinutes:8,unusedMinutes:7};
const hex=T.hashHex('learnit.atlas.m1.v0.3/plan-digest',payload);
const plan={planId:'atlas-plan-sha256:'+hex,planDigest:'sha256:'+hex,payload};
const recommendation={recommendationVersion:'atlas.recommendation.v1',objectiveRef:items[0].objectiveRef,action:'start-practice',eligibleActivityRefs:[items[0].activityRef],preferredActivityRef:items[0].activityRef,estimatedMinutes:4,reasonCodes:['NEW_OBJECTIVE']};
const html=T.renderToday({recommendation,plan,objectiveLabels:{'opaque-111':'Objectif Alpha','opaque-222':'Objectif Bêta'}});
assert.equal((html.match(/Entraînement — je m’exerce/g)||[]).length,2);
assert.match(html,/Objectif : Objectif Alpha/);
assert.match(html,/Objectif : Objectif Bêta/);
assert.doesNotMatch(html,/opaque-111|opaque-222/);
console.log(JSON.stringify({ok:true}));
""")
        self.assertTrue(result["ok"])

    def test_equal_summary_states_remain_distinguishable(self):
        result = run_node(r"""
const assert=require('node:assert/strict');
const S=require('./src/ui/atlas_summary.js');
const courseRef={packageLineageId:'p',courseLineageId:'c'};
function evidence(id, stamp){
 return {evidenceVersion:'atlas.objective-evidence.v1',objectiveRef:{courseRef,objectiveId:id},practiceAttempts:3,correctionsCompleted:1,validationAttempts:2,latestPracticeCorrect:true,latestValidationCorrect:true,lastValidationAt:stamp,lastEvidenceAt:stamp,state:'validated-recently'};
}
const stamp='2026-08-29T15:24:48.965Z';
const html=S.renderSummary({completed:true,evidence:[evidence('secret-a',stamp),evidence('secret-b',stamp)],objectiveLabels:{'secret-a':'Conjugué','secret-b':'Module'}});
assert.equal((html.match(/Validation autonome récente/g)||[]).length,2);
assert.match(html,/Objectif : Conjugué/);
assert.match(html,/Objectif : Module/);
assert.doesNotMatch(html,/secret-a|secret-b/);
assert.doesNotMatch(html,/2026-08-29T15:24:48\.965Z/);
assert.match(html,/ni une certification ni une promesse de rétention durable/);
console.log(JSON.stringify({ok:true}));
""")
        self.assertTrue(result["ok"])

    def test_classic_surface_is_not_default_atlas_continuation(self):
        source = SURFACE.read_text(encoding="utf-8")
        required = [
            "data-atlas-library-toggle",
            "appMain.style.display = 'none'",
            "appMain.setAttribute('inert', '')",
            "Afficher la bibliothèque",
            "Masquer la bibliothèque",
            "if (!atlasCourses.length)",
            "appMain.style.display = classicDisplay",
        ]
        for token in required:
            self.assertIn(token, source)
        self.assertLess(
            source.index("setClassicVisible(libraryVisible)"),
            source.index("const cards = []"),
        )

    def test_learner_copy_does_not_expose_internal_time_or_planner_language(self):
        source = SURFACE.read_text(encoding="utf-8")
        self.assertNotIn("Plan Atlas calculé localement", source)
        self.assertNotIn("Reconfirmation due selon", source)
        self.assertNotIn("Prochaine reconfirmation au plus tôt le", source)
        self.assertIn("Une reconfirmation est disponible.", source)
        self.assertIn("Prochaine reconfirmation à partir du", source)
        self.assertIn("Intl.DateTimeFormat('fr-FR'", source)

    def test_session_summary_receives_canonical_learner_labels(self):
        source = SESSION.read_text(encoding="utf-8")
        self.assertIn("learnerObjectiveLabels(context)", source)
        self.assertIn("objectiveLabels:", source)
        self.assertIn("modules.summary.renderSummary", source)
        self.assertIn("classicMain.style.display = 'none'", source)
        self.assertNotIn("transfer-completed", source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
