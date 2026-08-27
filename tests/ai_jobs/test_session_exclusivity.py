"""Independent contradictory human-grant and local-process exclusivity tests."""
from __future__ import annotations

import unittest

from tools.ai_jobs.contracts import ContractError, LedgerRecord, SessionGrant
from tools.ai_jobs.credential_boundary import acquire_session_process_fence
from tools.ai_jobs.session import require_exclusive_session


def grant(session_id: str, generation: int, digest_char: str) -> SessionGrant:
    return SessionGrant(
        repository="stefm78/learnit-platform",
        authority_issue=160,
        session_id=session_id,
        codespace_name="qa-codespace",
        generation=generation,
        granted_by="stefm78",
        created_at="2026-08-26T13:00:00Z",
        grant_comment_id=1000 + generation,
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


def active_chain(g: SessionGrant) -> list[LedgerRecord]:
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
    return chain


def closed_chain(g: SessionGrant) -> list[LedgerRecord]:
    chain = active_chain(g)
    append(chain, g, "SESSION_CLOSE_CANDIDATE", {
        "request_snapshot_sha256": "c" * 64,
        "cutoff_comment_id": 1,
    })
    append(chain, g, "SESSION_CLOSED", {
        "final_request_snapshot_sha256": "c" * 64,
    })
    return chain


class SessionExclusivityTests(unittest.TestCase):
    def test_two_grants_cannot_be_active_or_unresolved_concurrently(self) -> None:
        first = grant("G1S-QA1", 1, "a")
        second = grant("G1S-QA2", 2, "b")
        with self.assertRaises(ContractError):
            require_exclusive_session([first, second], active_chain(first), second)

    def test_prior_generation_must_be_durably_closed_before_next(self) -> None:
        first = grant("G1S-QA1", 1, "a")
        second = grant("G1S-QA2", 2, "b")
        require_exclusive_session([first, second], closed_chain(first), second)

    def test_only_highest_generation_can_be_selected(self) -> None:
        first = grant("G1S-QA1", 1, "a")
        second = grant("G1S-QA2", 2, "b")
        with self.assertRaises(ContractError):
            require_exclusive_session([first, second], closed_chain(second), first)

    def test_duplicate_session_generation_or_generation_number_fails_closed(self) -> None:
        one = grant("G1S-QA1", 1, "a")
        duplicate = grant("G1S-QA1", 1, "a")
        same_generation = grant("G1S-QA2", 1, "b")
        with self.assertRaises(ContractError):
            require_exclusive_session([one, duplicate], [], one)
        with self.assertRaises(ContractError):
            require_exclusive_session([one, same_generation], [], same_generation)

    def test_session_id_reuse_across_generations_fails_closed(self) -> None:
        one = grant("G1S-QA1", 1, "a")
        reused = grant("G1S-QA1", 2, "b")
        with self.assertRaises(ContractError):
            require_exclusive_session([one, reused], [], reused)

    def test_ledger_without_matching_grant_fails_closed(self) -> None:
        selected = grant("G1S-QA1", 2, "b")
        orphan = grant("G1S-ORP", 3, "c")
        with self.assertRaises(ContractError):
            require_exclusive_session([selected], active_chain(orphan), selected)

    def test_two_processes_for_same_authority_cannot_hold_fence(self) -> None:
        first = grant("G1S-QA1", 1, "a")
        second = grant("G1S-QA2", 2, "b")
        fence = acquire_session_process_fence(first)
        try:
            with self.assertRaises(ContractError):
                acquire_session_process_fence(second)
        finally:
            fence.close()
        replacement = acquire_session_process_fence(second)
        replacement.close()


if __name__ == "__main__":
    unittest.main()
