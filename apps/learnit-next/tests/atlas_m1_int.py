#!/usr/bin/env python3

import hashlib
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]

SURFACE = ROOT / "apps/learnit-next/src/integration/atlas/surface.js"
SESSION = ROOT / "apps/learnit-next/src/integration/atlas/session.js"
RENDER = ROOT / "apps/learnit-next/src/ui/render.js"
SUMMARY = ROOT / "apps/learnit-next/src/ui/atlas_summary.js"
MANIFEST = ROOT / "apps/learnit-next/source_manifest.json"
STYLES = ROOT / "apps/learnit-next/src/styles.css"


def blob_sha1(path):
    data = path.read_bytes()
    return hashlib.sha1(
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


class AtlasM1Int(unittest.TestCase):

    def test_session_composition_is_wired(self):
        surface = SURFACE.read_text(encoding="utf-8")
        session = SESSION.read_text(encoding="utf-8")

        for token in (
            "findResumableAtlasSession",
            "runAtlasSession",
            "ATLAS_SESSION_START_WIRED",
            "data-atlas-resume-session",
        ):
            self.assertIn(token, surface)

        self.assertNotIn(
            "if (start) start.remove();",
            surface,
        )

        for token in (
            "evaluateAnswer",
            "IndexedDbAtlasCoreService",
            "prepareStartRequest",
            "startSession",
            "createSessionController",
            "controller.submit",
            "requestHelp",
            "session-interrupted",
            "session-resumed",
            "session-completed",
            "renderSummary",
        ):
            self.assertIn(token, session)

    def test_learnit_is_answer_evaluation_authority(self):
        session = SESSION.read_text(encoding="utf-8")

        self.assertIn(
            "evaluateAnswer(\n            source,\n            rawResponse,",
            session,
        )

        self.assertIn(
            "learnit.kit.v2.${source.type}.v1",
            session,
        )

    def test_manifest_contains_exact_session_module(self):
        manifest = json.loads(
            MANIFEST.read_text(encoding="utf-8")
        )

        rows = [
            x
            for x in manifest["workingFiles"]
            if x["path"] == (
                "apps/learnit-next/src/integration/atlas/session.js"
            )
        ]

        self.assertEqual(len(rows), 1)

        self.assertEqual(
            rows[0]["fingerprint"],
            {
                "kind": "git-blob-sha1",
                "value": blob_sha1(SESSION),
            },
        )

    def test_javascript_syntax(self):
        for path in (SURFACE, SESSION):
            result = subprocess.run(
                ["node", "--check", str(path)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                result.returncode,
                0,
                result.stderr,
            )

    def test_active_session_hides_competing_surfaces(self):
        session = SESSION.read_text(encoding="utf-8")

        self.assertIn(
            "classicMain.style.display = 'none'",
            session,
        )
        self.assertIn(
            "classicMain.setAttribute('inert', '')",
            session,
        )
        self.assertIn(
            "plannerActions.style.display = 'none'",
            session,
        )
        self.assertIn(
            "classicMain.style.display = classicDisplay",
            session,
        )
        self.assertIn(
            "plannerActionsDisplay",
            session,
        )
        self.assertNotIn(
            "classicMain.hidden = true",
            session,
        )

    def test_session_controls_are_exposed(self):
        session = SESSION.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "data-atlas-session-actions",
            session,
        )

        self.assertIn(
            "data-atlas-pause-session",
            session,
        )

        self.assertIn(
            "data-atlas-help",
            session,
        )

    def test_surface_ownership_is_scoped_to_run_session(self):
        session = SESSION.read_text(encoding="utf-8")

        resume_pos = session.index(
            "export async function findResumableAtlasSession("
        )
        run_pos = session.index(
            "export async function runAtlasSession({"
        )
        ownership_pos = session.index(
            "container.setAttribute("
        )

        self.assertLess(resume_pos, run_pos)
        self.assertGreater(ownership_pos, run_pos)

        self.assertNotIn(
            "container.setAttribute(",
            session[:run_pos],
        )
        self.assertNotIn(
            "const classicMain =",
            session[:run_pos],
        )

    def test_active_atlas_session_owns_browser_surface(self):
        surface = SURFACE.read_text(encoding="utf-8")
        session = SESSION.read_text(encoding="utf-8")

        self.assertIn(
            'data-atlas-session-active="true"',
            surface,
        )
        self.assertIn(
            "data-atlas-session-active",
            session,
        )
        self.assertIn(
            "classicMain.style.display = 'none'",
            session,
        )
        self.assertIn(
            "releaseAtlasSurface",
            session,
        )

    def test_active_controls_are_deterministically_composed(self):
        surface = SURFACE.read_text(encoding="utf-8")
        session = SESSION.read_text(encoding="utf-8")

        self.assertIn(
            "data-atlas-planner-actions",
            surface,
        )

        for token in (
            '[data-atlas-planner-actions="true"]',
            "data-atlas-session-actions",
            "data-atlas-pause-session",
            "data-atlas-help",
            "data-atlas-control",
            "assertAtlasControlVisible",
            "ATLAS_SESSION_CONTROL_NOT_VISIBLE",
            "nextAtlasPaint",
            "text: 'Indice'",
        ):
            self.assertIn(token, session)

        self.assertNotIn(
            "atlasCard?.querySelector('.atlas-actions')",
            session,
        )

        self.assertNotIn(
            "      const actionBox =",
            session,
        )

    def test_library_atlas_learning_actions_use_atlas_entrypoint(self):
        render = RENDER.read_text(encoding="utf-8")
        surface = SURFACE.read_text(encoding="utf-8")

        for token in (
            "data-course-learning-action",
            "data-course-install-id",
            "learnit:show-library",
        ):
            self.assertIn(token, render)

        for token in (
            "atlasContextsByInstallId",
            "openAtlasCourse",
            "event.stopImmediatePropagation()",
            "data-atlas-course-install-id",
            "data-atlas-resume-session",
            "atlas-duration-select",
            "data-atlas-course-start",
        ):
            self.assertIn(token, surface)

    def test_active_session_hides_today_and_unrelated_atlas_courses(self):
        session = SESSION.read_text(encoding="utf-8")

        for token in (
            "surfaceHeading.style.display = 'none'",
            "courseTitle.style.display = 'none'",
            "courseMeta.style.display = 'none'",
            "otherAtlasCardDisplays",
            "card.style.display = 'none'",
            "surfaceHeading.style.display =",
            "courseTitle.style.display =",
            "courseMeta.style.display =",
        ):
            self.assertIn(token, session)

    def test_active_session_keeps_minimal_learner_context_and_contiguous_answers(self):
        session = SESSION.read_text(encoding="utf-8")

        self.assertIn("text: context.title", session)
        self.assertIn("text: `Objectif : ${objectiveLabel}`", session)
        self.assertIn("id: 'atlas-session-title'", session)
        self.assertIn("prompt\n      + '<fieldset class=\"answer-fieldset\">'", session)
        self.assertNotIn("renderObjectiveProgressPanel", session)
        self.assertNotIn("Prochaine action recommandée", session)

    def test_library_is_separate_and_detailed_progress_is_collapsed(self):
        render = RENDER.read_text(encoding="utf-8")
        surface = SURFACE.read_text(encoding="utf-8")

        for token in (
            "renderLibraryObjectiveDetails",
            "data-library-objective-details",
            "course-progress-details",
            "course-row-main",
            "course-row-actions",
            "Voir la progression détaillée",
            "runtime.importPackage(payload)",
            "Choisissez un fichier de cours à importer.",
        ):
            self.assertIn(token, render)

        for token in (
            "content.style.display = 'none'",
            "surfaceTitle.textContent = 'Bibliothèque'",
            "surfaceDescription.textContent = 'Choisissez un cours, consultez sa prochaine étape ou gérez votre bibliothèque.'",
            "libraryToggle.textContent = 'Retour à Aujourd’hui'",
            "setClassicVisible(false);",
            "compactImportPanel",
            "data-atlas-import-r5",
        ):
            self.assertIn(token, surface)

    def test_r6_visual_progress_action_semantics_and_composite_control_are_wired(self):
        surface = SURFACE.read_text(encoding="utf-8")
        session = SESSION.read_text(encoding="utf-8")
        summary = SUMMARY.read_text(encoding="utf-8")
        styles = STYLES.read_text(encoding="utf-8")

        for token in (
            "buildCourseProgressSummary",
            "renderCourseProgressSummary",
            "learnerStateLabel",
            "learnerActionCopy",
            "learnerOverview",
            "actionForEvidence",
            "course-objective-track",
            "course-objective-status-list",
            "À faire maintenant :",
            "atlas-duration-select",
            "data-atlas-session-start-control",
            "data-atlas-course-start",
            "course-list-row",
            "applyLibraryActionHierarchy",
            "Voir les objectifs",
            "Renommer le cours",
        ):
            self.assertIn(token, surface)

        self.assertNotIn("atlas-duration-control", surface)
        self.assertIn(".course-objective-track", styles)
        self.assertIn(".course-objective-status-list", styles)
        self.assertIn(".atlas-session-start-control", styles)
        self.assertIn(".atlas-summary-overview", styles)

        self.assertIn("'Voir le bilan'", session)
        self.assertIn("lastLifecycle?.kind", session)
        self.assertIn("'session-completed'", session)
        self.assertIn("nextLabel = 'Activité suivante'", session)
        self.assertNotIn(
            "await renderCurrent(\n                outcomeFeedback,",
            session,
        )

        self.assertIn('class="atlas-objective-details"', summary)
        self.assertIn("<summary>Voir le détail</summary>", summary)
        self.assertIn("Dernière activité", summary)
        self.assertIn("Acquis récemment", summary)
        self.assertIn("À renforcer", summary)
        self.assertIn("Rien à faire maintenant", summary)
        self.assertNotIn("Validation autonome récente", summary)
        self.assertNotIn("L’essentiel d’abord", summary)
        self.assertNotIn("Dernière preuve", summary)

    def test_primary_learner_copy_hides_internal_vocabulary(self):
        learner_copy = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (RENDER, SURFACE, SUMMARY)
        )

        for forbidden in (
            "Nouvelle génération isolée",
            "Atlas M2",
            "Importer un kit learnit.kit.v2",
            "titre canonique",
            "Les identités",
            "preuves enregistrées",
            "promesse de rétention durable",
            "Sélectionnez un fichier JSON à importer.",
        ):
            self.assertNotIn(forbidden, learner_copy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
