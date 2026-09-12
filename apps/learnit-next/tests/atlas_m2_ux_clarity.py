#!/usr/bin/env python3
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
SURFACE = APP / "src/integration/atlas/surface.js"
SESSION = APP / "src/integration/atlas/session.js"
MAIN = APP / "src/main.js"
STYLES = APP / "src/styles.css"


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

    def test_r6_summary_uses_plain_states_visual_overview_and_secondary_history(self):
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
assert.match(html,/Conjugué/);
assert.match(html,/Module/);
assert.doesNotMatch(html,/2026-08-29T15:24:48\.965Z/);
assert.match(html,/Votre progression après cette séance/);
assert.match(html,/1 acquis récemment · 1 à renforcer/);
assert.match(html,/course-objective-track/);
assert.match(html,/Acquis récemment/);
assert.match(html,/À renforcer/);
assert.match(html,/Revenir à Aujourd’hui pour la prochaine étape/);
assert.doesNotMatch(html,/Rien à faire maintenant/);
assert.match(html,/Reprendre avec un exercice ciblé/);
assert.match(html,/class="atlas-objective-details"/);
assert.match(html,/<summary>Voir le détail<\/summary>/);
assert.match(html,/Dernière activité/);
assert.doesNotMatch(html,/Validation autonome récente|L’essentiel d’abord|Dernière preuve|preuves enregistrées|certification|rétention durable/i);
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
        self.assertNotIn("Une reconfirmation est disponible.", surface)
        self.assertNotIn("Prochaine reconfirmation à partir du", surface)
        self.assertIn("À faire maintenant :", surface)
        self.assertIn("À découvrir", surface)
        self.assertIn("Acquis récemment", surface)

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

    def test_r6_today_uses_visual_objective_states_action_semantics_and_composite_control(self):
        surface = SURFACE.read_text(encoding="utf-8")
        for token in (
            "buildCourseProgressSummary",
            "renderCourseProgressSummary",
            "learnerStateLabel",
            "learnerActionCopy",
            "learnerOverview",
            "actionForEvidence",
            "course-objective-track",
            "course-objective-status-list",
            "atlas-duration-select",
            "data-atlas-session-start-control",
            "data-atlas-course-start",
            "Voir les objectifs",
            "Renommer",
            "applyLibraryActionHierarchy",
            "compactImportPanel",
            "course-list-row",
        ):
            self.assertIn(token, surface)
        self.assertIn("Consolider :", surface)
        self.assertIn("Réutiliser dans un nouvel exercice :", surface)
        self.assertNotIn("atlas-duration-control", surface)
        self.assertNotIn("stateLabel: 'À jour'", surface)
        self.assertNotIn("Validation autonome récente", surface)
        self.assertNotIn("course.progress", surface)

    def test_r13_visual_contract_uses_vertical_reservoirs_priority_outline_and_demand_detail(self):
        main = MAIN.read_text(encoding="utf-8")
        for token in (
            "atlasR13StateFromSegment",
            "atlasR13StateLabel",
            "atlasR13VisualLevel",
            "renderAtlasR13Progress",
            "enhanceAtlasR13VisualProgress",
            "installAtlasR13RuntimeBehavior",
            "data-atlas-r13-group",
            "objectifs-du-cours",
            "Objectifs du cours",
            "data-atlas-r13-priority",
            "data-atlas-r13-detail",
            "Priorité Learn-it",
            "atlas-r13-reservoir--review-needed",
            "repeating-linear-gradient",
            "atlas-r13-group--consolidated",
        ):
            self.assertIn(token, main)
        self.assertIn("reservoir.addEventListener('click'", main)
        self.assertIn("reservoir.addEventListener('focus'", main)
        self.assertNotIn("mouseenter", main)
        self.assertNotIn("progressPercent", main)
        self.assertNotIn("Math.round(", main)
        self.assertNotIn("aria-valuenow", main)
        self.assertNotIn("Séquence 1", main)
        self.assertNotIn("Chapitre 1", main)

    def test_r13_removes_intermediate_start_and_active_course_progress(self):
        main = MAIN.read_text(encoding="utf-8")
        surface = SURFACE.read_text(encoding="utf-8")
        self.assertIn(
            "const plan = await buildSessionPlan(context, duration, atlasRuntime);",
            surface,
        )
        self.assertIn("await runAtlasSession({", surface)
        self.assertNotIn("atlasRuntime.modules.today.renderToday", surface)
        self.assertNotIn("ATLAS_START_CONTROL_MISSING", surface)
        self.assertNotIn("data-atlas-r13-auto-started", main)
        self.assertNotIn("start.click()", main)
        self.assertIn("data-atlas-r13-session-owned", SESSION.read_text(encoding="utf-8"))
        self.assertIn(
            '.atlas-course-card[data-atlas-r13-session-owned="true"]>.course-row-main{display:none!important}',
            main,
        )
        self.assertIn(
            '.atlas-course-card[data-atlas-r13-session-owned="true"]>.atlas-course-actions{display:none!important}',
            main,
        )
        self.assertIn("data-atlas-session-active", SESSION.read_text(encoding="utf-8"))

    def test_r13_final_projection_is_reentrant_and_build_badge_is_replay_only(self):
        surface = SURFACE.read_text(encoding="utf-8")
        main = MAIN.read_text(encoding="utf-8")
        self.assertNotIn(
            "card.getAttribute('data-atlas-library-r6') === 'true'",
            surface,
        )
        self.assertIn(
            "card.querySelector('.course-row-main .course-progress-compact')?.remove()",
            surface,
        )
        self.assertIn(
            "actions.querySelector('[data-atlas-rest-status=\"true\"]')?.remove()",
            surface,
        )
        self.assertIn(
            "if (libraryVisible) queueMicrotask(applyLibraryActionHierarchy)",
            surface,
        )
        self.assertIn("if (!identity) return null;", main)
        self.assertNotIn("build unbound", main)
        self.assertNotIn("Build Learn-it non vérifiable", main)

    def test_r10_recommendation_full_ties_preserve_course_input_order(self):
        result = run_node(r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./src/core/atlas_recommendation.js');

const courseRef = {packageLineageId:'pkg',courseLineageId:'course'};
const ref = objectiveId => ({courseRef,objectiveId});
const row = (objectiveId,state='not-started') => {
  const objectiveRef=ref(objectiveId);
  return {objectiveRef,evidence:{objectiveRef,state}};
};
const ids = rows => R.rankRecommendations(rows).map(item=>item.objectiveRef.objectiveId);

assert.deepEqual(
  ids([row('z-first'),row('a-second'),row('m-third')]),
  ['z-first','a-second','m-third'],
);

assert.equal(
  R.rankRecommendations([row('z-first'),row('a-review','review-needed')])[0].objectiveRef.objectiveId,
  'a-review',
);

const event = (eventId,occurredAt,objectiveIds) => ({
  kind:'session-started',
  eventId,
  occurredAt,
  selectedItems:objectiveIds.map(objectiveId=>({objectiveRef:ref(objectiveId)})),
});

const lastSelectedEvents = [
  event('event-1','2026-01-01T00:00:00.000Z',['z-first']),
  event('event-2','2026-01-02T00:00:00.000Z',['a-second']),
];
assert.equal(
  R.rankRecommendations([row('a-second'),row('z-first')],lastSelectedEvents)[0].objectiveRef.objectiveId,
  'z-first',
);

const recentCountEvents = [
  event('event-1','2026-01-01T00:00:00.000Z',['a-second']),
  event('event-2','2026-01-02T00:00:00.000Z',['a-second']),
  event('event-3','2026-01-03T00:00:00.000Z',['z-first','a-second']),
];
assert.equal(
  R.rankRecommendations([row('a-second'),row('z-first')],recentCountEvents)[0].objectiveRef.objectiveId,
  'z-first',
);

const kit = JSON.parse(fs.readFileSync(
  path.resolve('../../authoring/v2/golden/signaux_electriques.json'),
  'utf8',
));
const course = kit.courses[0];
const realCourseRef = {
  packageLineageId:kit.packageLineageId,
  courseLineageId:course.courseLineageId,
};
const realRows = course.objectives.map(objective => {
  const objectiveRef={courseRef:realCourseRef,objectiveId:objective.objectiveId};
  return {objectiveRef,evidence:{objectiveRef,state:'not-started'}};
});
assert.equal(course.objectives[0].objectiveId,'e6a159cb-cd4d-4565-9d61-eda32db9002e');
assert.equal(course.objectives[1].objectiveId,'324ec962-5ca9-4ed2-8737-654020805939');
assert.equal(
  R.rankRecommendations(realRows)[0].objectiveRef.objectiveId,
  course.objectives[0].objectiveId,
);

assert.throws(
  () => R.rankRecommendations([
    {objectiveRef:{courseRef},evidence:{state:'not-started'}},
    row('valid'),
  ]),
  /MISSING_FIELD|UNQUALIFIED_REFERENCE/,
);

console.log(JSON.stringify({ok:true,realFirst:course.objectives[0].objectiveId}));
""")
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["realFirst"],
            "e6a159cb-cd4d-4565-9d61-eda32db9002e",
        )

    def test_r10_today_summary_and_preview_share_the_same_ranked_sequence(self):
        surface = SURFACE.read_text(encoding="utf-8")
        ranking_call = (
            "const ranked = modules.recommendation."
            "rankRecommendations(rows, state.learningEvents);"
        )
        self.assertEqual(surface.count(ranking_call), 2)
        self.assertIn("const next = ranked[0] ?? rows[0] ?? null;", surface)
        self.assertIn("const recommendations = ranked.map(row => {", surface)

    def test_session_keeps_transfer_semantics_and_classic_surface_hidden_while_active(self):
        session = SESSION.read_text(encoding="utf-8")
        self.assertIn("classicMain.style.display = 'none'", session)
        self.assertIn("data-atlas-session-active", session)
        self.assertIn("modules.summary.renderSummary", session)
        self.assertIn("learnerObjectiveLabels(context)", session)
        self.assertNotIn("transfer-completed", session)

    def test_r12_fails_closed_on_runtime_qualified_atlas_context(self):
        surface = SURFACE.read_text(encoding="utf-8")
        self.assertIn("authority.contextAccepted(context)", surface)
        self.assertIn("compatibleAtlasCourse(context, atlasRuntime)", surface)

    def test_r12_stops_same_day_repeat_when_every_objective_is_waiting(self):
        surface = SURFACE.read_text(encoding="utf-8")
        for token in (
            "sessionAvailableNow",
            "nextAvailableAt",
            "À jour pour aujourd’hui",
            "Pour consolider dans la durée, revenez à partir du",
            "data-atlas-rest-status",
        ):
            self.assertIn(token, surface)
        self.assertIn("detail.memory.due", surface)
        self.assertIn("detail?.memory?.dueAt", surface)

    def test_r12_library_hover_preview_and_active_session_focus_are_explicit(self):
        surface = SURFACE.read_text(encoding="utf-8")
        styles = STYLES.read_text(encoding="utf-8")
        self.assertIn("title: `${item.label} — ${item.stateLabel}`", surface)
        self.assertIn("Préparation de la séance de ${duration} minutes…", surface)
        self.assertNotIn("Voici ce que vous allez travailler pendant cette séance.", surface)
        self.assertIn("settingsDisclosure.textContent = 'Renommer'", surface)
        self.assertIn('data-atlas-session-active="true"', styles)
        self.assertIn("> .course-row-main", styles)
        self.assertIn("display: none", styles)
        self.assertIn(".atlas-r9-stat-symbol { display: none; }", styles)
        self.assertIn("counter-reset: atlas-objective", styles)
        self.assertNotIn("progressPercent", styles)

    def test_r13_browser_dom_density_state_priority_focus_and_mobile(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            self.fail(f"playwright required for R13 browser qualification: {exc}")

        artifact = APP / "dist/learnit-next.html"
        self.assertTrue(artifact.is_file(), "deterministic build artifact must exist before browser test")
        chrome = (
            shutil.which("google-chrome")
            or shutil.which("chromium")
            or shutil.which("chromium-browser")
        )
        self.assertIsNotNone(chrome, "system Chromium/Chrome is required for R13 browser qualification")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=chrome)
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto(artifact.as_uri(), wait_until="load")
            page.wait_for_function(
                "() => Boolean(window.__LEARNIT_NEXT_TEST__?.renderAtlasR13Fixture)"
            )

            for count in (5, 8, 12, 20):
                states = [
                    (
                        "review-needed" if index == 1
                        else "ready-for-validation" if index == 2
                        else "validated-recently" if index % 4 == 3
                        else "training"
                    )
                    for index in range(count)
                ]
                result = page.evaluate(
                    """({states, priority}) => {
                      const host = document.createElement('div');
                      host.className = 'course-progress-compact';
                      document.body.append(host);
                      window.__LEARNIT_NEXT_TEST__.renderAtlasR13Fixture(host, states, priority);
                      const reservoirs = [...host.querySelectorAll('[data-atlas-r13-objective]')];
                      const detail = host.querySelector('[data-atlas-r13-detail]');
                      const priorityEl = host.querySelector('[data-atlas-r13-priority=\"true\"]');
                      const before = detail.hidden;
                      priorityEl.focus();
                      const after = detail.hidden;
                      const strip = host.querySelector('.atlas-r13-reservoirs');
                      const value = {
                        count: reservoirs.length,
                        group: host.querySelector('[data-atlas-r13-group]')?.textContent,
                        before,
                        after,
                        priorityLabel: priorityEl.getAttribute('aria-label'),
                        reinforceMark: host.querySelector('[data-atlas-r13-state=\"review-needed\"] .atlas-r13-state-mark')?.textContent,
                        confirmMark: host.querySelector('[data-atlas-r13-state=\"ready-for-validation\"] .atlas-r13-state-mark')?.textContent,
                        overflow: strip.scrollWidth >= strip.clientWidth,
                      };
                      host.remove();
                      return value;
                    }""",
                    {"states": states, "priority": min(2, count - 1)},
                )
                self.assertEqual(result["count"], count)
                self.assertIn("Objectifs du cours", result["group"])
                self.assertTrue(result["before"])
                self.assertFalse(result["after"])
                self.assertIn("Priorité Learn-it", result["priorityLabel"])
                self.assertEqual(result["reinforceMark"], "↺")
                self.assertEqual(result["confirmMark"], "◇")
                if count == 20:
                    self.assertTrue(result["overflow"])

            consolidated = page.evaluate(
                """() => {
                  const host = document.createElement('div');
                  host.className = 'course-progress-compact';
                  document.body.append(host);
                  window.__LEARNIT_NEXT_TEST__.renderAtlasR13Fixture(
                    host,
                    Array(8).fill('validated-recently'),
                    0,
                  );
                  const value = host.querySelector('[data-atlas-r13-group]')
                    ?.getAttribute('data-atlas-r13-consolidated');
                  host.remove();
                  return value;
                }"""
            )
            self.assertEqual(consolidated, "true")
            browser.close()

    def test_r13_browser_real_today_and_library_enter_same_atlas_session(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            self.fail(f"playwright required for R13 browser qualification: {exc}")

        artifact = APP / "dist/learnit-next.html"
        fixture = ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json"
        self.assertTrue(artifact.is_file())
        self.assertTrue(fixture.is_file())
        chrome = (
            shutil.which("google-chrome")
            or shutil.which("chromium")
            or shutil.which("chromium-browser")
        )
        self.assertIsNotNone(chrome)

        def import_fixture(page):
            page.goto(artifact.as_uri(), wait_until="load")
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__?.importPackage)")
            self.assertEqual(page.locator('[data-learnit-build-identity]').count(), 0)
            page.locator('#kit-file').set_input_files(str(fixture))
            page.locator('.import-panel button[type="submit"]').click()
            page.wait_for_selector('[data-atlas-course-install-id]', timeout=10000)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=chrome)

            today_context = browser.new_context(viewport={"width": 900, "height": 900})
            today_page = today_context.new_page()
            import_fixture(today_page)
            today_page.locator('[data-atlas-course-start="true"]').first.click()
            today_page.wait_for_selector('[data-atlas-session-active="true"] form', timeout=10000)
            self.assertEqual(
                today_page.locator('[data-atlas-session-active="true"] form').count(),
                1,
            )
            today_context.close()

            library_context = browser.new_context(viewport={"width": 900, "height": 900})
            library_page = library_context.new_page()
            import_fixture(library_page)
            library_page.locator('[data-atlas-library-toggle="true"]').click()
            library_page.wait_for_function(
                """() => {
                  const card = [...document.querySelectorAll('.course-card[data-course-install-id]')]
                    .find(item => item.textContent.includes('Conjugué et module des nombres complexes'));
                  if (!card) return false;
                  const actions = card.querySelector('.course-row-actions');
                  return Boolean(actions?.querySelector('[data-course-learning-action="learn"], [data-atlas-rest-status="true"]'));
                }""",
                timeout=10000,
            )
            action = library_page.locator(
                '.course-card[data-course-install-id] [data-course-learning-action="learn"]'
            ).first
            if action.count():
                action.click()
                library_page.wait_for_selector('[data-atlas-session-active="true"] form', timeout=10000)
                self.assertEqual(
                    library_page.locator('[data-atlas-session-active="true"] form').count(),
                    1,
                )
            else:
                self.assertEqual(
                    library_page.locator(
                        '.course-card[data-course-install-id] [data-atlas-rest-status="true"]'
                    ).count(),
                    1,
                )
            library_context.close()
            browser.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
