"""Independent contradictory QA for sealing, publication, replay, and crash boundaries."""

from __future__ import annotations

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from tools.codespace_evidence import OUTCOME_MARKER, PUBLICATION_LIMIT_BYTES
from tools.codespace_evidence.github import GhClient, GitHubError, PublicationResult
from tools.codespace_evidence.outcome import (
    OutcomeError,
    allocate_attempt,
    ensure_publication_budget,
    seal_bundle,
    write_bundle_files,
    write_publication_receipt,
)


REPOSITORY = "stefm78/learnit-platform"
SHA = "1" * 40
DIGEST = "2" * 64


class EmptyRunner:
    def records_summary(self, *, excerpt_bytes: int = 4096) -> list[object]:
        del excerpt_bytes
        return []

    def combined_stdout(self) -> str:
        return ""

    def combined_stderr(self) -> str:
        return ""


class ReadBackClient(GhClient):
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def read_comment(self, *, repository: str, comment_id: int) -> dict[str, object]:
        del repository, comment_id
        return self.response


class ExistingCommentClient(GhClient):
    def __init__(self, comments: list[dict[str, object]]) -> None:
        self.comments = comments

    def list_origin_comments(self, repository: str, origin_number: int) -> list[dict[str, object]]:
        del repository, origin_number
        return self.comments


def marker_only_body() -> str:
    return (
        f"{OUTCOME_MARKER}\n"
        "job_id: CEB-QA-PUB-1\n"
        f"request_sha256: {DIGEST}\n"
        f"repository: {REPOSITORY}\n"
        "origin: issue#102\n"
        f"target_sha: {SHA}\n"
        "completion_state: FINAL_SEALED\n"
    )


class PublicationTests(unittest.TestCase):
    def test_publication_below_limit_is_accepted(self) -> None:
        ensure_publication_budget("a" * (PUBLICATION_LIMIT_BYTES - 1))

    def test_publication_exactly_at_58000_utf8_bytes_is_accepted(self) -> None:
        body = "é" * (PUBLICATION_LIMIT_BYTES // 2)
        self.assertEqual(len(body.encode("utf-8")), PUBLICATION_LIMIT_BYTES)
        ensure_publication_budget(body)

    def test_publication_above_limit_is_rejected(self) -> None:
        with self.assertRaisesRegex(OutcomeError, "limit is 58000"):
            ensure_publication_budget("a" * (PUBLICATION_LIMIT_BYTES + 1))

    def test_attempt_002_never_overwrites_attempt_001(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = allocate_attempt(root, "CEB-QA-PUB-1")
            sentinel = first.root / "sentinel.txt"
            sentinel.write_text("first", encoding="utf-8")
            second = allocate_attempt(root, "CEB-QA-PUB-1")
            self.assertEqual(first.number, 1)
            self.assertEqual(second.number, 2)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "first")
            self.assertNotEqual(first.root, second.root)

    def test_crash_before_sealing_has_no_manifest_or_final_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            attempt = allocate_attempt(Path(directory), "CEB-QA-PUB-2")
            write_bundle_files(
                attempt,
                facts={"status": "FAILED"},
                summary="partial",
                runner=EmptyRunner(),
                environment={},
                artifacts={},
            )
            self.assertFalse((attempt.bundle / "manifest.sha256").exists())
            self.assertFalse((attempt.publication / "receipt.json").exists())

    def test_sealed_bundle_and_publication_receipt_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            attempt = allocate_attempt(Path(directory), "CEB-QA-PUB-3")
            write_bundle_files(
                attempt,
                facts={"status": "COMPLETED"},
                summary="complete",
                runner=EmptyRunner(),
                environment={"python": "test"},
                artifacts={"diff.patch": "diff --git a/a b/a\n"},
            )
            sealed = seal_bundle(attempt)
            manifest_before = (attempt.bundle / "manifest.sha256").read_bytes()
            write_publication_receipt(attempt, {"state": "VERIFIED", "comment_id": 7})
            self.assertTrue((attempt.publication / "receipt.json").is_file())
            self.assertFalse((attempt.bundle / "receipt.json").exists())
            self.assertEqual((attempt.bundle / "manifest.sha256").read_bytes(), manifest_before)
            self.assertEqual(len(sealed.manifest_sha256), 64)
            self.assertEqual(len(sealed.bundle_sha256), 64)

    def test_exact_comment_readback_is_required(self) -> None:
        expected = "exact body"
        result = PublicationResult(77, "https://example.invalid/comment/77", expected, None)
        client = ReadBackClient(
            {
                "id": 77,
                "issue_url": f"https://api.github.com/repos/{REPOSITORY}/issues/102",
                "body": expected,
                "html_url": "https://example.invalid/comment/77",
            }
        )
        receipt = client.verify_publication(
            repository=REPOSITORY,
            origin_number=102,
            result=result,
            expected_body=expected,
            required_fragments=["exact"],
        )
        self.assertEqual(receipt["state"], "VERIFIED")

    def test_changed_comment_body_fails_readback(self) -> None:
        result = PublicationResult(77, "https://example.invalid/comment/77", "posted", None)
        client = ReadBackClient(
            {
                "id": 77,
                "issue_url": f"https://api.github.com/repos/{REPOSITORY}/issues/102",
                "body": "changed",
            }
        )
        with self.assertRaisesRegex(GitHubError, "body differs"):
            client.verify_publication(
                repository=REPOSITORY,
                origin_number=102,
                result=result,
                expected_body="posted",
                required_fragments=["posted"],
            )

    def test_restart_does_not_trust_unverified_marker_only_comment(self) -> None:
        """A POST-before-readback crash must not turn a marker-shaped comment into verified evidence."""
        client = ExistingCommentClient([{"id": 77, "body": marker_only_body()}])
        existing = client.find_existing_final_publication(
            repository=REPOSITORY,
            origin_type="issue",
            origin_number=102,
            job_id="CEB-QA-PUB-1",
            request_digest=DIGEST,
            target_sha=SHA,
        )
        self.assertIsNone(
            existing,
            "restart must require a cryptographically complete and reverified publication, not marker fragments alone",
        )

    def test_multiple_final_publications_are_rejected(self) -> None:
        client = ExistingCommentClient(
            [{"id": 1, "body": marker_only_body()}, {"id": 2, "body": marker_only_body()}]
        )
        with self.assertRaisesRegex(GitHubError, "multiple verified final publications"):
            client.find_existing_final_publication(
                repository=REPOSITORY,
                origin_type="issue",
                origin_number=102,
                job_id="CEB-QA-PUB-1",
                request_digest=DIGEST,
                target_sha=SHA,
            )


if __name__ == "__main__":
    unittest.main()
