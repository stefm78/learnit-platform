#!/usr/bin/env python3
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
SURFACE = APP / "src/integration/atlas/surface.js"
SESSION = APP / "src/integration/atlas/session.js"


def run_node(script: str):
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=APP,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout)


class AtlasM2UxClarity(unittest.TestCase):
    def test_plan_rows_expose_learner_objective_labels(self):
        result = run_node(r"""
const assert = require('node:assert/strict');
const T = require('./src/ui/atlas_today.js');

const courseRef = {packageLineageId:'pkg',courseLineageId:'course'};
const contentRevisionRef = {packageLineageId:'pkg',packageRevisionId:'rev',packageDigest:'sha256:'+'1'.repeat(64)};
const objectiveA = {courseRef,objectiveId:'objective-a'};
const objectiveB = {courseRef,objectiveId:'objective-b'};
const activityA = {courseRef,activityLineageId:'activity-a'};
const activityB = {courseRef,activityLineageId:'activity-b'};
const items = [
  {position:0,objectiveRef:objectiveA,activityRef:activityA,action:'continue-practice',executionClass:'practice',estimatedMinutes:4},
  {position:1,objectiveRef:objectiveB,activityRef:activityB,action:'continue-practice',executionClass:'practice',estimatedMinutes:4},
];
const payload = {
  schemaVersion:'atlas.session-plan.v1',
  engineVersion:'atlas.m2.transfer.v1',
  courseRef,
  contentRevisionRef,
  durationMinutes:15,
  items,
  totalEstimatedMinutes:8,
  unusedMinutes:7,
};
const hex = T.hashHex('learnit.atlas.m1.v0.3/plan-digest', payload);
const plan = {planId:'atlas-plan-sha256:'+hex,planDigest:'sha256:'+hex,payload};
const recommendation = {
  recommendationVersion:'atlas.recommendation.v1',
  objectiveRef:objectiveA,
  action:'continue-practice',
  eligibleActivityRefs:[activityA],
  preferredActivityRef:activityA,
  estimatedMinutes:4,
  reasonCodes:['PRACTICE_IN_PROGRESS'],
};
const html = T.renderToday({
  recommendation,
  plan,
  objectiveLabels:{
    'objective-a':'Conjugué',
    'objective-b':'Module',
  },
});
assert.match(html,/Objectif : Conjugué/);
assert.match(html,/Objectif : Module/);
assert.match(html,/<br><small class="atlas-plan-objective">Objectif : Conjugué<\/small>/);
assert.doesNotMatch(html,/objective-a|objective-b/);
console.log(JSON.stringify({ok:true}));
""")
        self.assertTrue(result["ok"])

    def test_summary_identifies_objectives_hides_raw_iso_and_exposes_next_step(self):
        result = run_node(r"""
const assert = require('node:assert/strict');
const S = require('./src/ui/atlas_summary.js');
const courseRef = {packageLineageId:'pkg',courseLineageId:'course'};
function evidence(objectiveId, at, state='validated-recently') {
  return {
    evidenceVersion:'atlas.objective-evidence.v1',
    objectiveRef:{courseRef,objectiveId},
    practiceAttempts:2,
    correctionsCompleted:0,
    validationAttempts:state === 'validated-recently' ? 1 : 0,
    latestPracticeCorrect:true,
    latestValidationCorrect:state === 'validated-recently' ? true : null,
    lastValidationAt:state === 'validated-recently' ? at : null,
    lastEvidenceAt:at,
    state,
  };
}
const stamp = '2026-08-29T15:24:48.965Z';
const html = S.renderSummary({
  completed:true,
  evidence:[evidence('objective-a', stamp), evidence('objective-b', stamp, 'review-needed')],
  objectiveLabels:{
    'objective-a':'Conjugué',
    'objective-b':'Module',
  },
});
assert.match(html,/Objectif : Conjugué/);
assert.match(html,/Objectif : Module/);
assert.doesNotMatch(html,/2026-08-29T15:24:48\.965Z/);
assert.match(html,/Voici votre bilan par objectif/);
assert.match(html,/Prochaine étape :/);
assert.match(html,/À renforcer :/);
assert.match(html,/Reprendre Module avec une activité ciblée/);
assert.match(html,/class="atlas-objective-details"/);
assert.match(html,/<summary>Voir le détail<\/summary>/);
assert.match(html,/Dernière activité/);
assert.doesNotMatch(html,/Dernière preuve|preuves enregistrées|certification|rétention durable/i);
const readable = S.formatLearnerTimestamp(stamp, new Date('2026-08-29T16:00:00.000Z'));
assert.ok(!readable.includes('T15:24:48.965Z'));
console.log(JSON.stringify({ok:true,readable}));
""")
        self.assertTrue(result["ok"])

    def test_atlas_owns_default_continuation_but_library_is_intentional(self):
        surface = SURFACE.read_text(encoding="utf-8")
        self.assertIn("data-atlas-library-toggle", surface)
        self.assertIn("Afficher la bibliothèque", surface)
        self.assertIn("Retour à Aujourd’hui", surface)
        self.assertIn("content.style.display = 'none'", surface)
        self.assertIn("appMain.style.display = 'none'", surface)
        self.assertIn("appMain.setAttribute('inert', '')", surface)
        self.assertIn("setClassicVisible(libraryVisible)", surface)
        self.assertIn("if (!atlasCourses.length)", surface)
        self.assertIn("appMain.style.display = classicDisplay", surface)

    def test_copy_is_learner_facing(self):
        surface = SURFACE.read_text(encoding="utf-8")
        self.assertNotIn("Plan Atlas calculé localement", surface)
        self.assertNotIn("Reconfirmation due selon", surface)
        self.assertNotIn("Prochaine reconfirmation au plus tôt le", surface)
        self.assertIn("Une reconfirmation est disponible.", surface)
        self.assertIn("Prochaine reconfirmation à partir du", surface)
        self.assertIn("Prochaine étape :", surface)

    def test_feedback_keeps_completed_activity_visible_before_next_activity(self):
        session = SESSION.read_text(encoding="utf-8")
        start = session.index("async function showFeedbackTransition")
        end = session.index("function assertAtlasControlVisible", start)
        transition = session[start:end]

        self.assertIn("data-atlas-feedback-transition", transition)
        self.assertIn("nextLabel = 'Activité suivante'", transition)
        self.assertIn(".querySelectorAll('input, select')", transition)
        self.assertIn("control.disabled = true", transition)
        self.assertIn("sessionActions.remove()", transition)
        self.assertIn("activityWrapper.append(transition)", transition)
        self.assertNotIn("container.replaceChildren", transition)

        self.assertIn("await showFeedbackTransition(", session)
        self.assertIn("wrapper,\n                sessionActions,", session)
        self.assertIn("await renderCurrent();", session)
        self.assertIn("'Voir le bilan'", session)
        self.assertIn("lastLifecycle?.kind", session)
        self.assertIn("'session-completed'", session)
        self.assertNotIn(
            "await renderCurrent(\n                outcomeFeedback,",
            session,
        )
        self.assertNotIn("await renderCurrent(\n              feedbackHtml(", session)

    def test_r5_today_uses_one_primary_action_and_compact_duration_selector(self):
        surface = SURFACE.read_text(encoding="utf-8")
        self.assertIn("buildCourseProgressSummary", surface)
        self.assertIn("renderCourseProgressSummary", surface)
        self.assertIn("learnerStateCopy", surface)
        self.assertIn("course-progress-compact", surface)
        self.assertIn("atlas-duration-select", surface)
        self.assertIn("data-atlas-course-start", surface)
        self.assertIn("applyLibraryActionHierarchy", surface)
        self.assertIn("compactImportPanel", surface)
        self.assertNotIn("atlas-duration-control", surface)
        self.assertIn("course-list-row", surface)
        self.assertNotIn("course.progress", surface)

    def test_session_keeps_transfer_semantics_and_classic_surface_hidden_while_active(self):
        session = SESSION.read_text(encoding="utf-8")
        self.assertIn("classicMain.style.display = 'none'", session)
        self.assertIn("data-atlas-session-active", session)
        self.assertIn("modules.summary.renderSummary", session)
        self.assertIn("learnerObjectiveLabels(context)", session)
        self.assertNotIn("transfer-completed", session)


if __name__ == "__main__":
    unittest.main(verbosity=2)
