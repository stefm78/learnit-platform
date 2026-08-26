"""Independent contradictory snapshot, pagination and byte-budget tests."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.ai_jobs.contracts import ContractError
import tools.ai_jobs.snapshot as snapshot_mod


def comment(comment_id: int, body: str = "ok", *, updated_at: str | None = None) -> dict:
    created_at = "2026-08-26T13:00:00Z"
    return {
        "id": comment_id,
        "node_id": f"IC_{comment_id}",
        "body": body,
        "user": {"login": "qa-user", "id": 100 + comment_id, "node_id": f"U_{comment_id}"},
        "created_at": created_at,
        "updated_at": created_at if updated_at is None else updated_at,
        "html_url": f"https://github.com/stefm78/learnit-platform/issues/170#issuecomment-{comment_id}",
        "issue_url": "https://api.github.com/repos/stefm78/learnit-platform/issues/170",
    }


class StableSnapshotTests(unittest.TestCase):
    def test_same_comments_in_different_page_order_are_stable(self) -> None:
        scans = [[comment(2), comment(1)], [comment(1), comment(2)]]
        result = snapshot_mod.stable_double_scan(lambda: scans.pop(0))
        self.assertEqual([item["id"] for item in result.comments], [1, 2])
        self.assertEqual(result.cutoff_comment_id, 2)

    def test_content_change_between_scans_fails_closed(self) -> None:
        scans = [[comment(1, "first")], [comment(1, "second")]]
        with self.assertRaises(ContractError):
            snapshot_mod.stable_double_scan(lambda: scans.pop(0))

    def test_addition_or_deletion_between_scans_fails_closed(self) -> None:
        for scans in (
            [[comment(1), comment(2)], [comment(1)]],
            [[comment(1)], [comment(1), comment(2)]],
        ):
            work = [list(scans[0]), list(scans[1])]
            with self.subTest(first=len(scans[0]), second=len(scans[1])):
                with self.assertRaises(ContractError):
                    snapshot_mod.stable_double_scan(lambda: work.pop(0))

    def test_overlapping_pagination_duplicate_comment_ids_fail_closed(self) -> None:
        with self.assertRaises(ContractError):
            snapshot_mod.stable_double_scan(lambda: [comment(1), comment(1)])

    def test_comment_count_global_bound_is_enforced(self) -> None:
        with patch.object(snapshot_mod, "MAX_COMMENTS_PER_ISSUE", 2):
            with self.assertRaises(ContractError):
                snapshot_mod.stable_double_scan(lambda: [comment(1), comment(2), comment(3)])

    def test_chunk_byte_bound_uses_utf8_bytes(self) -> None:
        with patch.object(snapshot_mod, "MAX_CHUNK_BYTES", 3):
            with self.assertRaises(ContractError):
                snapshot_mod.stable_double_scan(lambda: [comment(1, "éé")])
            result = snapshot_mod.stable_double_scan(lambda: [comment(1, "é")])
            self.assertEqual(result.cutoff_comment_id, 1)

    def test_snapshot_total_byte_bound_is_enforced(self) -> None:
        with patch.object(snapshot_mod, "MAX_SNAPSHOT_BYTES", 8):
            with self.assertRaises(ContractError):
                snapshot_mod.stable_double_scan(lambda: [comment(1, "x")])

    def test_fractional_invalid_and_out_of_domain_comment_times_are_rejected(self) -> None:
        for timestamp in (
            "2026-08-26T13:00:00.1Z",
            "2026-02-30T13:00:00Z",
            "2101-01-01T00:00:00Z",
        ):
            raw = comment(1)
            raw["created_at"] = timestamp
            raw["updated_at"] = timestamp
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(ContractError):
                    snapshot_mod.stable_double_scan(lambda: [raw])


if __name__ == "__main__":
    unittest.main()
