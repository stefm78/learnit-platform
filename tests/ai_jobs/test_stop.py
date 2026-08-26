"""Independent contradictory credential-free stop authorization tests."""
from __future__ import annotations

from pathlib import Path
import unittest

from tools.ai_jobs import GATE0_OPERATIONS
from tools.ai_jobs.contracts import ContractError, SessionGrant
import tools.ai_jobs.stop as stop_mod


def grant() -> SessionGrant:
    return SessionGrant(
        repository="stefm78/learnit-platform", authority_issue=160,
        session_id="G1S-QA1", codespace_name="qa-codespace", generation=1,
        granted_by="stefm78", created_at="2026-08-26T13:00:00Z",
        grant_comment_id=100, grant_digest="a" * 64,
    )


class StopBoundaryTests(unittest.TestCase):
    def test_stop_authorization_is_forbidden_before_durable_closed_state(self) -> None:
        for state in (
            "ACTIVE_IDLE", "JOB_SELECTED", "JOB_STARTED", "RECOVERY_REQUIRED",
            "CLOSING", "GLOBAL_HOLD",
        ):
            with self.subTest(state=state):
                with self.assertRaises(ContractError):
                    stop_mod.stop_after_closed(grant=grant(), state=state)

    def test_stop_authorization_requires_verified_publication(self) -> None:
        for value in (False, None, 0, 1, "true"):
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    stop_mod.stop_after_closed(
                        grant=grant(), state="CLOSED", publication_verified=value
                    )

    def test_closed_state_returns_data_only_intent_without_external_stop(self) -> None:
        intent = stop_mod.stop_after_closed(
            grant=grant(), state="CLOSED", publication_verified=True
        )
        self.assertEqual(intent.repository, grant().repository)
        self.assertEqual(intent.codespace_name, grant().codespace_name)
        source = Path(stop_mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("stop_current_codespace", source)
        self.assertNotIn("subprocess", source)

    def test_stop_is_not_a_gate0_queue_operation_or_automatic_lifecycle_api(self) -> None:
        self.assertNotIn("stop-codespace", GATE0_OPERATIONS)
        source = Path(stop_mod.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "create_codespace", "start_codespace", "restart_codespace",
            "codespace-create", "codespace-start", "codespace-restart",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
