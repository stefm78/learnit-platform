"""Independent contradictory QA for sealing, publication, replay, and crash boundaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from tools.codespace_evidence import OUTCOME_MARKER, PUBLICATION_LIMIT_BYTES, STATEMENT
from tools.codespace_evidence.github import GhClient, GitHubError, PublicationResult
from tools.codespace_evidence.outcome import (
    OutcomeError,
    allocate_attempt,
    ensure_publication_budget,
    render_oversize_diagnostic,
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
    def __init__(self, comments: list[dict[str, object]], authenticated_login: str = "bridge-bot") -> None:
        self.comments = comments
        self.authenticated_login = authenticated_login

    def list_origin_comments(self, repository: str, origin_number: int) -> list[dict[str, object]]:
        del repository, origin_number
        return self.comments

    def read_comment(self, *, repository: str, comment_id: int) -> dict[str, object]:
        for comment in self.comments:
            if comment.get("id") == comment_id:
                result = dict(comment)
                result.setdefault(
                    "issue_url",
                    f"https://api.github.com/repos/{repository}/issues/102",
                )
                return result
        return {}


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


def forged_complete_body() -> str:
    """Return a structurally complete capsule whose digests were never recomputed."""

    manifest = "3" * 64
    bundle = "4" * 64
    payload = {
        "facts": {
            "job_id": "CEB-QA-PUB-1",
            "request_sha256": DIGEST,
            "repository": REPOSITORY,
            "origin": {"type": "issue", "number": 102},
            "target": {"requested_sha": SHA},
        },
        "summary": "forged but structurally complete",
        "sealed_bundle": {
            "manifest_sha256": manifest,
            "bundle_sha256": bundle,
            "artifact_sha256": {"facts.json": "5" * 64},
        },
    }
    header = (
        f"{OUTCOME_MARKER}\n"
        "job_id: CEB-QA-PUB-1\n"
        "attempt: 1\n"
        f"request_sha256: {DIGEST}\n"
        "operation: pr-snapshot\n"
        f"repository: {REPOSITORY}\n"
        "origin: issue#102\n"
        f"target_sha: {SHA}\n"
        "status: COMPLETED\n"
        "classification: EVIDENCE_CANDIDATE\n"
        f"manifest_sha256: {manifest}\n"
        f"bundle_sha256: {bundle}\n"
        "completion_state: FINAL_SEALED\n\n"
    )
    return (
        header
        + "```json\n"
        + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        + "\n```\n\n"
        + STATEMENT
        + "\n"
    )


def self_consistent_complete_body() -> str:
    """Return a fully self-consistent capsule that was not produced by the authenticated bridge."""

    facts = {
        "job_id": "CEB-QA-PUB-1",
        "request_sha256": DIGEST,
        "repository": REPOSITORY,
        "origin": {"type": "issue", "number": 102},
        "target": {"requested_sha": SHA},
    }
    summary = "forged but internally self-consistent"
    facts_text = json.dumps(
        facts,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    summary_text = summary.rstrip() + "\n"
    artifact_digests = {
        "facts.json": hashlib.sha256(facts_text.encode("utf-8")).hexdigest(),
        "summary.md": hashlib.sha256(summary_text.encode("utf-8")).hexdigest(),
    }
    manifest_text = "".join(
        f"{digest}  {name}\n" for name, digest in sorted(artifact_digests.items())
    )
    manifest = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
    bundle = hashlib.sha256((manifest + "\n" + manifest_text).encode("utf-8")).hexdigest()
    payload = {
        "facts": facts,
        "summary": summary,
        "sealed_bundle": {
            "manifest_sha256": manifest,
            "bundle_sha256": bundle,
            "artifact_sha256": artifact_digests,
        },
    }
    header = (
        f"{OUTCOME_MARKER}\n"
        "job_id: CEB-QA-PUB-1\n"
        "attempt: 1\n"
        f"request_sha256: {DIGEST}\n"
        "operation: pr-snapshot\n"
        f"repository: {REPOSITORY}\n"
        "origin: issue#102\n"
        f"target_sha: {SHA}\n"
        "status: COMPLETED\n"
        "classification: EVIDENCE_CANDIDATE\n"
        f"manifest_sha256: {manifest}\n"
        f"bundle_sha256: {bundle}\n"
        "completion_state: FINAL_SEALED\n\n"
    )
    return (
        header
        + "```json\n"
        + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        + "\n```\n\n"
        + STATEMENT
        + "\n"
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

    def test_restart_rejects_self_consistent_but_unrecomputed_digests(self) -> None:
        """Hex-shaped digests copied into headers and payload are not cryptographic verification."""
        client = ExistingCommentClient([{"id": 78, "body": forged_complete_body()}])
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
            "restart must recompute manifest and bundle digests from the durable capsule rather than trust matching strings",
        )

    def test_restart_rejects_cryptographically_valid_comment_from_untrusted_author(self) -> None:
        """Digest validity cannot replace binding to the authenticated publisher identity."""
        client = ExistingCommentClient(
            [
                {
                    "id": 79,
                    "body": self_consistent_complete_body(),
                    "user": {"login": "attacker"},
                }
            ],
            authenticated_login="bridge-bot",
        )
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
            "a third-party comment must not become an implicit publication receipt merely because its internal digests are self-consistent",
        )

    def test_restart_reverifies_final_oversize_diagnostic_without_duplicate_post(self) -> None:
        """A verified FINAL_DIAGNOSTIC_ONLY publication must remain idempotent after a crash."""
        facts = {
            "job_id": "CEB-QA-PUB-1",
            "attempt": 1,
            "request_sha256": DIGEST,
            "operation": "pr-snapshot",
            "repository": REPOSITORY,
            "origin": {"type": "issue", "number": 102},
            "target": {"requested_sha": SHA},
            "status": "FAILED",
            "classification": "INCONCLUSIVE",
        }
        with tempfile.TemporaryDirectory() as directory:
            attempt = allocate_attempt(Path(directory), "CEB-QA-PUB-1")
            write_bundle_files(
                attempt,
                facts=facts,
                summary="oversize diagnostic",
                runner=EmptyRunner(),
                environment={},
                artifacts={},
            )
            sealed = seal_bundle(attempt)
            body = render_oversize_diagnostic(
                facts=facts,
                manifest_sha256=sealed.manifest_sha256,
                bundle_sha256=sealed.bundle_sha256,
            )
        client = ExistingCommentClient(
            [{"id": 80, "body": body, "user": {"login": "bridge-bot"}}],
            authenticated_login="bridge-bot",
        )
        existing = client.find_existing_final_publication(
            repository=REPOSITORY,
            origin_type="issue",
            origin_number=102,
            job_id="CEB-QA-PUB-1",
            request_digest=DIGEST,
            target_sha=SHA,
        )
        self.assertIsNotNone(
            existing,
            "restart must reverify an already-posted final diagnostic instead of posting a duplicate after POST-before-receipt crash",
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
