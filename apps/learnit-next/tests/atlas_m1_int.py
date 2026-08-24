#!/usr/bin/env python3

import hashlib
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]

SURFACE = ROOT / "apps/learnit-next/src/integration/atlas/surface.js"
SESSION = ROOT / "apps/learnit-next/src/integration/atlas/session.js"
MANIFEST = ROOT / "apps/learnit-next/source_manifest.json"


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

if __name__ == "__main__":
    unittest.main(verbosity=2)
