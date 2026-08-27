"""Independent contradictory deterministic queue and identity-conflict tests."""
from __future__ import annotations

import itertools
import unittest

from tools.ai_jobs.contracts import ContractError, QueueJob
from tools.ai_jobs.queue import elect


def job(comment_id: int, job_id: str, digest: str, *, target_sha: str | None = None) -> QueueJob:
    return QueueJob(
        repository="stefm78/learnit-platform",
        origin_type="issue",
        origin_number=170,
        request_comment_id=comment_id,
        request_author="stefm78",
        created_at="2026-08-26T13:00:00Z",
        job_id=job_id,
        operation="pr-snapshot",
        target_type="commit",
        target_number=None,
        target_sha=target_sha or ("1" * 40),
        request_digest=digest,
    )


class QueueOrderTests(unittest.TestCase):
    def test_election_is_total_and_input_order_independent(self) -> None:
        jobs = [
            job(30, "J-C", "c" * 64),
            job(10, "J-B", "b" * 64),
            job(11, "J-A", "a" * 64),
        ]
        expected = min(jobs, key=lambda item: item.order_key)
        for permutation in itertools.permutations(jobs):
            with self.subTest(order=[item.job_id for item in permutation]):
                decision = elect(permutation)
                self.assertEqual(decision.selected, expected)
                self.assertEqual(list(decision.pending), sorted(jobs, key=lambda item: item.order_key))

    def test_duplicate_source_comment_identity_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            elect([job(10, "J-A", "a" * 64), job(10, "J-B", "b" * 64)])

    def test_duplicate_logical_request_same_digest_is_collapsed_once(self) -> None:
        duplicate_a = job(10, "J-DUP", "a" * 64)
        duplicate_b = job(11, "J-DUP", "a" * 64)
        decision = elect([duplicate_b, duplicate_a])
        self.assertEqual(decision.duplicate_job_ids, ("J-DUP",))
        self.assertEqual(len(decision.pending), 1)
        self.assertEqual(decision.selected.request_comment_id, 10)

    def test_same_logical_job_with_different_content_is_hard_conflict(self) -> None:
        with self.assertRaises(ContractError):
            elect([job(10, "J-CONFLICT", "a" * 64), job(11, "J-CONFLICT", "b" * 64)])

    def test_reused_request_digest_under_another_job_id_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            elect([job(10, "J-A", "a" * 64), job(11, "J-B", "a" * 64)])

    def test_started_and_terminal_requests_are_never_re_elected(self) -> None:
        started = job(10, "J-STARTED", "a" * 64)
        terminal = job(11, "J-TERMINAL", "b" * 64)
        fresh = job(12, "J-FRESH", "c" * 64)
        decision = elect(
            [started, terminal, fresh],
            started_request_digests=frozenset({started.request_digest, terminal.request_digest}),
            terminal_request_digests=frozenset({terminal.request_digest}),
        )
        self.assertEqual(decision.pending, (fresh,))
        self.assertEqual(decision.selected, fresh)

    def test_terminal_digest_without_started_digest_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            elect([], terminal_request_digests=frozenset({"a" * 64}))


if __name__ == "__main__":
    unittest.main()
