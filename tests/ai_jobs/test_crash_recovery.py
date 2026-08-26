"""Independent contradictory crash-boundary, post-start and no-replay tests."""
from __future__ import annotations

from pathlib import Path
import unittest

from tools.ai_jobs.contracts import ContractError, LedgerRecord, QueueJob, SessionGrant
from tools.ai_jobs.queue import elect
from tools.ai_jobs.session import project, require_exclusive_session
import tools.ai_jobs.run as run_mod


def grant(session_id: str = "G1S-QA1", generation: int = 1, digest_char: str = "a") -> SessionGrant:
    return SessionGrant(
        repository="stefm78/learnit-platform",
        authority_issue=160,
        session_id=session_id,
        codespace_name="qa-codespace",
        generation=generation,
        granted_by="stefm78",
        created_at="2026-08-26T13:00:00Z",
        grant_comment_id=900 + generation,
        grant_digest=digest_char * 64,
    )


def append(chain: list[LedgerRecord], g: SessionGrant, record_type: str, payload: dict) -> LedgerRecord:
    record = LedgerRecord.build(
        record_type=record_type,
        repository=g.repository,
        authority_issue=g.authority_issue,
        session_id=g.session_id,
        generation=g.generation,
        sequence=len(chain) + 1,
        previous_record_sha256=chain[-1].record_sha256 if chain else None,
        created_at="2026-08-26T13:00:00Z",
        payload=payload,
    )
    chain.append(record)
    return record


def selected_chain(g: SessionGrant, digest: str) -> list[LedgerRecord]:
    chain: list[LedgerRecord] = []
    append(chain, g, "SESSION_GRANT", {
        "grant_comment_id": g.grant_comment_id,
        "grant_digest": g.grant_digest,
        "request_issue": 170,
    })
    append(chain, g, "SESSION_ACTIVE", {
        "codespace_name": g.codespace_name,
        "request_issue": 170,
    })
    append(chain, g, "JOB_SELECTED", {
        "job_id": "J-1",
        "request_digest": digest,
        "request_comment_id": 200,
        "target_type": "commit",
        "target_number": None,
        "target_sha": "1" * 40,
    })
    return chain


def start(chain: list[LedgerRecord], g: SessionGrant, digest: str) -> None:
    append(chain, g, "JOB_STARTED", {
        "job_id": "J-1",
        "request_digest": digest,
        "request_comment_id": 200,
        "target_sha": "1" * 40,
    })


def terminal(chain: list[LedgerRecord], g: SessionGrant, digest: str) -> None:
    append(chain, g, "JOB_TERMINAL", {
        "job_id": "J-1",
        "request_digest": digest,
        "result": "COMPLETED",
        "gate0_return_code": 0,
        "gate0_timed_out": False,
        "gate0_authoritative_comment_id": 300,
    })


def queue_job(digest: str) -> QueueJob:
    return QueueJob(
        repository="stefm78/learnit-platform",
        origin_type="issue",
        origin_number=170,
        request_comment_id=200,
        request_author="stefm78",
        created_at="2026-08-26T13:00:00Z",
        job_id="J-1",
        operation="pr-snapshot",
        target_type="commit",
        target_number=None,
        target_sha="1" * 40,
        request_digest=digest,
    )


class CrashRecoveryTests(unittest.TestCase):
    def test_crash_after_job_selected_has_no_started_effect_claim(self) -> None:
        g = grant()
        digest = "c" * 64
        projection = project(selected_chain(g, digest), g)
        self.assertEqual(projection.state, "JOB_SELECTED")
        self.assertEqual(projection.started_request_digests, frozenset())
        self.assertIsNone(projection.active_job_digest)

    def test_durable_job_started_is_active_and_suppressed_from_election(self) -> None:
        g = grant()
        digest = "c" * 64
        chain = selected_chain(g, digest)
        start(chain, g, digest)
        projection = project(chain, g)
        self.assertEqual(projection.state, "JOB_STARTED")
        self.assertEqual(projection.active_job_digest, digest)
        decision = elect([queue_job(digest)], started_request_digests=projection.started_request_digests)
        self.assertIsNone(decision.selected)

    def test_recovery_required_after_durable_start_blocks_autonomous_advance(self) -> None:
        g = grant()
        digest = "c" * 64
        chain = selected_chain(g, digest)
        start(chain, g, digest)
        append(chain, g, "SESSION_RECOVERY_REQUIRED", {
            "request_digest": digest,
            "reason": "host-loss",
        })
        projection = project(chain, g)
        self.assertEqual(projection.state, "RECOVERY_REQUIRED")
        with self.assertRaises(ContractError):
            project(chain + [LedgerRecord.build(
                record_type="JOB_SELECTED",
                repository=g.repository,
                authority_issue=g.authority_issue,
                session_id=g.session_id,
                generation=g.generation,
                sequence=len(chain) + 1,
                previous_record_sha256=chain[-1].record_sha256,
                created_at="2026-08-26T13:00:00Z",
                payload={
                    "job_id": "J-2", "request_digest": "d" * 64,
                    "request_comment_id": 201, "target_type": "commit",
                    "target_number": None, "target_sha": "2" * 40,
                },
            )], g)

    def test_reconciled_terminal_digest_still_cannot_be_replayed(self) -> None:
        g = grant()
        digest = "c" * 64
        chain = selected_chain(g, digest)
        start(chain, g, digest)
        append(chain, g, "SESSION_RECOVERY_REQUIRED", {
            "request_digest": digest,
            "reason": "host-loss",
        })
        terminal(chain, g, digest)
        projection = project(chain, g)
        self.assertIn(digest, projection.started_request_digests)
        self.assertIn(digest, projection.terminal_request_digests)
        self.assertIsNone(elect(
            [queue_job(digest)],
            started_request_digests=projection.started_request_digests,
            terminal_request_digests=projection.terminal_request_digests,
        ).selected)

    def test_unresolved_started_generation_fences_second_human_session(self) -> None:
        first = grant("G1S-QA1", 1, "a")
        second = grant("G1S-QA2", 2, "b")
        digest = "c" * 64
        chain = selected_chain(first, digest)
        start(chain, first, digest)
        with self.assertRaises(ContractError):
            require_exclusive_session([first, second], chain, second)

    def test_post_job_started_controls_precede_permit_and_gate0_effect(self) -> None:
        source = Path(run_mod.__file__).read_text(encoding="utf-8")
        anchor = source.index("post_start_snapshot = stable_double_scan")
        ordered_fragments = (
            "post_start_snapshot = stable_double_scan",
            "post_start_records = _validated_session_records",
            "post_start = project",
            "suspended_post_start = _is_suspended",
            "source_post_start = gh.comment",
            "permission_post_start = gh.permission",
            "target_post_start = _target_sha",
            "final_effect_guard(",
            "pilot_permit = PilotEffectPermit.build",
            "invocation = invoke_once(",
        )
        positions = [source.index(fragment, anchor) for fragment in ordered_fragments]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("post_start.last_record.record_sha256 != started.record_sha256", source[anchor:positions[-1]])
        self.assertIn("post_start.active_job_digest != job.request_digest", source[anchor:positions[-1]])
        self.assertIn("_recover_post_started_if_authoritative(", source[positions[-1]:])

    def test_restart_after_durable_job_started_never_calls_gate0_before_recovery(self) -> None:
        source = Path(run_mod.__file__).read_text(encoding="utf-8")
        restart = source.index('elif current.state == "JOB_STARTED"')
        recovery = source.index("_enter_recovery(", restart)
        next_effect = source.find("invoke_once(", restart)
        self.assertGreaterEqual(recovery, restart)
        self.assertTrue(next_effect == -1 or recovery < next_effect)


if __name__ == "__main__":
    unittest.main()
