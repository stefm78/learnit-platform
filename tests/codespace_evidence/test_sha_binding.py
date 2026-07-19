"""Independent contradictory QA for exact SHA binding and staleness."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from tools.codespace_evidence.operations import OperationResult
from tools.codespace_evidence.outcome import build_facts
from tools.codespace_evidence.run import _apply_stale_after, _stale_before


SHA = "c" * 40
MOVED_SHA = "d" * 40


def request() -> SimpleNamespace:
    return SimpleNamespace(
        job_id="CEB-QA-SHA-1",
        digest_sha256="e" * 64,
        operation="pr-snapshot",
        repository="stefm78/learnit-platform",
        origin=SimpleNamespace(type="issue", number=102, request_comment_id=123),
        target_type="pull_request",
        target_number=103,
        target_sha=SHA,
    )


class ShaBindingTests(unittest.TestCase):
    def test_stale_target_before_execution_fails_without_operation(self) -> None:
        result = _stale_before(request(), {"sha": MOVED_SHA})
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.classification, "STALE_TARGET")
        self.assertFalse(result.facts["operation_executed"])
        self.assertIn("TARGET_MOVED_BEFORE_EXECUTION", result.missing_proof)

    def test_target_moved_after_execution_is_downgraded(self) -> None:
        result = OperationResult("COMPLETED", "EVIDENCE_CANDIDATE", {"value": 1})
        _apply_stale_after(request(), result, {"sha": MOVED_SHA})
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.classification, "STALE_AFTER_EXECUTION")
        self.assertIn("TARGET_MOVED_AFTER_EXECUTION", result.missing_proof)
        self.assertEqual(result.facts["stale_after_execution"]["observed_sha"], MOVED_SHA)

    def test_unchanged_target_preserves_result(self) -> None:
        result = OperationResult("COMPLETED", "EVIDENCE_CANDIDATE", {})
        _apply_stale_after(request(), result, {"sha": SHA})
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.classification, "EVIDENCE_CANDIDATE")

    def test_outcome_records_before_and_after_sha_independently(self) -> None:
        facts = build_facts(
            request=request(),
            attempt=1,
            status="FAILED",
            classification="STALE_AFTER_EXECUTION",
            started_at="2026-07-18T12:00:00Z",
            completed_at="2026-07-18T12:01:00Z",
            target_before={"sha": SHA},
            target_after={"sha": MOVED_SHA},
            operation_facts={},
            missing_proof=["TARGET_MOVED_AFTER_EXECUTION"],
            checkout_proof={"unchanged": True},
            preflight={},
            commands=[],
        )
        self.assertFalse(facts["target"]["stale_before"])
        self.assertTrue(facts["target"]["stale_after"])
        self.assertEqual(facts["target"]["requested_sha"], SHA)
        self.assertEqual(facts["target"]["resolved_after"]["sha"], MOVED_SHA)

    def test_ordinary_outcome_schema_rejects_governance_decision(self) -> None:
        with self.assertRaisesRegex(Exception, "forbidden classification"):
            build_facts(
                request=request(),
                attempt=1,
                status="COMPLETED",
                classification="GOVERNANCE_DECISION",
                started_at="2026-07-18T12:00:00Z",
                completed_at="2026-07-18T12:01:00Z",
                target_before={"sha": SHA},
                target_after={"sha": SHA},
                operation_facts={},
                missing_proof=[],
                checkout_proof={"unchanged": True},
                preflight={},
                commands=[],
            )


if __name__ == "__main__":
    unittest.main()
