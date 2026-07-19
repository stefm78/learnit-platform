"""Independent adversarial QA for GitHub-only final-outcome arbitration."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
import unittest

from tools.codespace_evidence import OUTCOME_MARKER, STATEMENT
from tools.codespace_evidence.run import _discover_candidates


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


def request_for(job_id: str = "CEB-QA-CURRENT") -> SimpleNamespace:
    return SimpleNamespace(
        repository=REPOSITORY,
        job_id=job_id,
        digest_sha256=DIGEST,
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


class OutcomeArbitrationTests(unittest.TestCase):
    def test_valid_final_outcome_for_another_job_does_not_poison_discovery(self) -> None:
        """Discovery is keyed by canonical repository plus job_id, not by origin alone."""
        client = ArbitrationClient(
            [
                {
                    "id": 700,
                    "body": complete_body(job_id="CEB-QA-UNRELATED"),
                    "user": {"login": "bridge-bot"},
                    "html_url": "https://example.invalid/comments/700",
                }
            ]
        )

        election = _discover_candidates(client, request_for())

        self.assertIsNone(election.incumbent)
        self.assertEqual(election.valid, ())
        self.assertEqual(election.losers, ())
        self.assertEqual(client.seen_repository, REPOSITORY)
        self.assertEqual(client.seen_origin_number, 105)


if __name__ == "__main__":
    unittest.main()
