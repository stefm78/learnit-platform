"""Independent adversarial QA for GitHub-only final-outcome arbitration."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
import unittest

from tools.codespace_evidence import OUTCOME_MARKER, STATEMENT
from tools.codespace_evidence.run import ArbitrationError, _discover_candidates


REPOSITORY = "stefm78/learnit-platform"
TARGET_SHA = "1" * 40
DIGEST = "2" * 64


class ArbitrationClient:
    def __init__(self, comments: list[dict[str, object]]) -> None:
        self.comments = comments
        self.authenticated_login = "bridge-bot"

    def list_origin_comments(self, repository: str, origin_number: int) -> list[dict[str, object]]:
        self.seen_repository = repository
        self.seen_origin_number = origin_number
        return list(self.comments)


def request_for(job_id: str = "CEB-QA-CURRENT", digest: str = DIGEST) -> SimpleNamespace:
    return SimpleNamespace(
        repository=REPOSITORY,
        job_id=job_id,
        digest_sha256=digest,
        operation="pr-snapshot",
        origin=SimpleNamespace(type="issue", number=105, request_comment_id=5015000000),
        target_type="pull_request",
        target_number=103,
        target_sha=TARGET_SHA,
    )


def complete_body(*, job_id: str, digest: str = DIGEST) -> str:
    facts = {
        "job_id": job_id,
        "request_sha256": digest,
        "operation": "pr-snapshot",
        "repository": REPOSITORY,
        "origin": {
            "type": "issue",
            "number": 105,
            "request_comment_id": 5015000000,
        },
        "target": {
            "type": "pull_request",
            "number": 103,
            "requested_sha": TARGET_SHA,
        },
    }
    summary = "independent arbitration fixture"
    facts_text = json.dumps(
        facts,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    summary_text = summary + "\n"
    artifact_digests = {
        "facts.json": hashlib.sha256(facts_text.encode("utf-8")).hexdigest(),
        "summary.md": hashlib.sha256(summary_text.encode("utf-8")).hexdigest(),
    }
    manifest_text = "".join(
        f"{value}  {name}\n" for name, value in sorted(artifact_digests.items())
    )
    manifest_digest = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
    bundle_digest = hashlib.sha256(
        (manifest_digest + "\n" + manifest_text).encode("utf-8")
    ).hexdigest()
    payload = {
        "facts": facts,
        "summary": summary,
        "sealed_bundle": {
            "manifest_sha256": manifest_digest,
            "bundle_sha256": bundle_digest,
            "artifact_sha256": artifact_digests,
        },
    }
    header = (
        f"{OUTCOME_MARKER}\n"
        f"job_id: {job_id}\n"
        "attempt: 1\n"
        f"request_sha256: {digest}\n"
        "operation: pr-snapshot\n"
        f"repository: {REPOSITORY}\n"
        "origin: issue#105\n"
        f"target_sha: {TARGET_SHA}\n"
        "status: COMPLETED\n"
        "classification: EVIDENCE_CANDIDATE\n"
        f"manifest_sha256: {manifest_digest}\n"
        f"bundle_sha256: {bundle_digest}\n"
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


def sealed_body_for(request: SimpleNamespace) -> str:
    """Build a fresh sealed capsule after all request identity fields are fixed."""
    return complete_body(job_id=request.job_id, digest=request.digest_sha256)


def comment(comment_id: int, body: str, *, author: str = "bridge-bot") -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": author},
        "html_url": f"https://example.invalid/comments/{comment_id}",
    }


def replace_job_header(body: str, replacement: str | None) -> str:
    lines = body.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("job_id:"):
            if replacement is None:
                del lines[index]
            else:
                lines[index] = f"job_id: {replacement}\n"
            return "".join(lines)
    raise AssertionError("fixture lacks job_id header")


class OutcomeArbitrationTests(unittest.TestCase):
    def assert_declared_final_rejected(self, body: str, *, author: str = "bridge-bot") -> str:
        with self.assertRaises(ArbitrationError) as raised:
            _discover_candidates(
                ArbitrationClient([comment(701, body, author=author)]),
                request_for(),
            )
        message = str(raised.exception)
        self.assertIn("INVALID_DECLARED_FINAL_OUTCOME", message)
        return message

    def test_valid_final_outcome_for_another_job_does_not_poison_discovery(self) -> None:
        """A strictly valid other partition remains isolated from the current job."""
        unrelated_request = request_for("CEB-QA-UNRELATED", "3" * 64)
        client = ArbitrationClient(
            [comment(700, sealed_body_for(unrelated_request))]
        )

        election = _discover_candidates(client, request_for())

        self.assertIsNone(election.incumbent)
        self.assertEqual(election.valid, ())
        self.assertEqual(election.losers, ())
        self.assertEqual(client.seen_repository, REPOSITORY)
        self.assertEqual(client.seen_origin_number, 105)

    def test_missing_job_id_is_not_silently_treated_as_another_job(self) -> None:
        message = self.assert_declared_final_rejected(
            replace_job_header(complete_body(job_id="CEB-QA-CURRENT"), None)
        )
        self.assertIn("INVALID_JOB_ID", message)
        self.assertIn("repository_job_discovery", message)

    def test_null_empty_wrong_type_and_syntax_invalid_job_ids_fail_closed(self) -> None:
        original = complete_body(job_id="CEB-QA-CURRENT")
        for invalid in ("", "null", "7", "CEB QA CURRENT", "../CEB-QA-CURRENT"):
            with self.subTest(job_id=invalid):
                message = self.assert_declared_final_rejected(
                    replace_job_header(original, invalid)
                )
                self.assertIn("INVALID_JOB_ID", message)
                self.assertIn("repository_job_discovery", message)

    def test_near_forged_job_id_cannot_escape_as_another_partition(self) -> None:
        message = self.assert_declared_final_rejected(
            replace_job_header(
                complete_body(job_id="CEB-QA-CURRENT"),
                "CEB-QA-CURRENT!",
            )
        )
        self.assertIn("INVALID_JOB_ID", message)

    def test_wrong_author_plus_invalid_job_id_is_rejected_at_partition_validation(self) -> None:
        body = replace_job_header(complete_body(job_id="CEB-QA-CURRENT"), "null")
        message = self.assert_declared_final_rejected(body, author="attacker")
        self.assertIn("INVALID_JOB_ID", message)

    def test_altered_payload_plus_invalid_job_id_cannot_bypass_validation(self) -> None:
        body = complete_body(job_id="CEB-QA-CURRENT").replace(
            "independent arbitration fixture",
            "hostile altered payload",
            1,
        )
        body = replace_job_header(body, "null")
        message = self.assert_declared_final_rejected(body)
        self.assertIn("INVALID_JOB_ID", message)

    def test_bad_digest_plus_invalid_job_id_cannot_bypass_validation(self) -> None:
        body = complete_body(job_id="CEB-QA-CURRENT").replace(
            f"request_sha256: {DIGEST}",
            f"request_sha256: {'f' * 64}",
            1,
        )
        body = replace_job_header(body, "null")
        message = self.assert_declared_final_rejected(body)
        self.assertIn("INVALID_JOB_ID", message)

    def test_mixed_current_other_and_hostile_candidates_fail_closed(self) -> None:
        unrelated_request = request_for("CEB-QA-UNRELATED", "3" * 64)
        comments = [
            comment(720, sealed_body_for(unrelated_request)),
            comment(721, complete_body(job_id="CEB-QA-CURRENT")),
            comment(
                722,
                replace_job_header(
                    complete_body(job_id="CEB-QA-CURRENT"),
                    "CEB-QA-CURRENT!",
                ),
                author="attacker",
            ),
        ]
        with self.assertRaises(ArbitrationError) as raised:
            _discover_candidates(ArbitrationClient(comments), request_for())

        message = str(raised.exception)
        self.assertIn("INVALID_DECLARED_FINAL_OUTCOME", message)
        self.assertTrue(
            "INVALID_JOB_ID" in message
            or "CRYPTOGRAPHIC_OR_SCHEMA_INCONSISTENCY" in message,
            message,
        )
        self.assertTrue(
            "repository_job_discovery" in message
            or "cryptographic_validation" in message,
            message,
        )

    def test_removing_job_id_cannot_downgrade_a_digest_conflict_to_unrelated(self) -> None:
        conflicting = complete_body(job_id="CEB-QA-CURRENT", digest="3" * 64)
        stripped = replace_job_header(conflicting, None)
        message = self.assert_declared_final_rejected(stripped)
        self.assertIn("INVALID_DECLARED_FINAL_OUTCOME", message)

    def test_other_valid_jobs_do_not_change_current_job_election_or_idempotence(self) -> None:
        current_request = request_for()
        unrelated_request = request_for("CEB-QA-UNRELATED", "3" * 64)
        current = comment(730, sealed_body_for(current_request))
        unrelated = comment(729, sealed_body_for(unrelated_request))

        first = _discover_candidates(
            ArbitrationClient([unrelated, current]),
            current_request,
        )
        second = _discover_candidates(
            ArbitrationClient([current, unrelated]),
            current_request,
        )

        self.assertIsNotNone(first.incumbent)
        self.assertIsNotNone(second.incumbent)
        self.assertEqual(first.incumbent.comment_id, 730)
        self.assertEqual(second.incumbent.comment_id, 730)
        self.assertEqual(first.incumbent.body_sha256, second.incumbent.body_sha256)
        self.assertEqual([item.comment_id for item in first.valid], [730])
        self.assertEqual([item.comment_id for item in second.valid], [730])
        self.assertEqual(first.duplicate_ids, [])
        self.assertEqual(second.duplicate_ids, [])
        self.assertEqual(first.losers, ())
        self.assertEqual(second.losers, ())

    def test_simultaneous_identity_mutation_does_not_bypass_job_validation(self) -> None:
        body = complete_body(job_id="CEB-QA-CURRENT")
        body = replace_job_header(body, "CEB-QA-CURRENT!")
        body = body.replace(f"repository: {REPOSITORY}", "repository: STEFM78/learnit-platform", 1)
        body = body.replace("origin: issue#105", "origin: issue#104", 1)
        body = body.replace(f"target_sha: {TARGET_SHA}", f"target_sha: {'4' * 40}", 1)
        message = self.assert_declared_final_rejected(body, author="attacker")
        self.assertIn("INVALID_DECLARED_FINAL_OUTCOME", message)


if __name__ == "__main__":
    unittest.main()
