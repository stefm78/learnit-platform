"""Independent contradictory QA for machine-verifiable same-origin binding."""

from __future__ import annotations

import copy
import json
import unittest

from tools.codespace_evidence import REQUEST_MARKER, SCHEMA_VERSION
from tools.codespace_evidence.request import (
    LaunchDescriptor,
    RequestError,
    parse_request_envelope,
    request_digest,
    verify_bound_request,
)


SHA = "b" * 40
REPOSITORY = "stefm78/learnit-platform"
COMMENT_ID = 5011414879
ORIGIN_NUMBER = 102
ISSUE_URL = f"https://api.github.com/repos/{REPOSITORY}/issues/{ORIGIN_NUMBER}"


def request_value() -> dict[str, object]:
    """Build a minimal valid origin-bound request before injecting one anomaly."""
    return {
        "schema_version": SCHEMA_VERSION,
        "job_id": "CEB-QA-ORIGIN-1",
        "operation": "pr-governor-evidence",
        "repository": REPOSITORY,
        "target_type": "pull_request",
        "target_number": 103,
        "target_sha": SHA,
        "origin": {
            "type": "issue",
            "number": ORIGIN_NUMBER,
            "request_comment_id": COMMENT_ID,
        },
        "created_at": "2026-07-18T12:00:00Z",
        "timeout_seconds": 300,
        "parameters": {
            "test_profile": None,
            "required_checks": ["Repository governance", "PR scope"],
            "include_logs": True,
            "include_artifacts": True,
        },
    }


def envelope(value: dict[str, object], *, digest: str | None = None, marker: str = REQUEST_MARKER) -> str:
    expected = digest or request_digest(value)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    return f"{marker}\nrequest_sha256: {expected}\n\n```json\n{payload}\n```"


def descriptor() -> LaunchDescriptor:
    return LaunchDescriptor(REPOSITORY, "issue", ORIGIN_NUMBER, COMMENT_ID)


def comment(value: dict[str, object] | None = None) -> dict[str, object]:
    payload = value or request_value()
    return {"id": COMMENT_ID, "issue_url": ISSUE_URL, "body": envelope(payload)}


class OriginBindingTests(unittest.TestCase):
    def test_absent_or_duplicate_origin_marker_is_rejected(self) -> None:
        body = envelope(request_value())
        with self.assertRaisesRegex(RequestError, "expected exactly one"):
            parse_request_envelope(body.replace(REQUEST_MARKER, "MISSING_MARKER"))
        with self.assertRaisesRegex(RequestError, "expected exactly one"):
            parse_request_envelope(body + "\n" + REQUEST_MARKER)

    def test_request_digest_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(RequestError, "request digest mismatch"):
            parse_request_envelope(envelope(request_value(), digest="0" * 64))

    def test_origin_issue_url_must_be_exact(self) -> None:
        source = comment()
        source["issue_url"] = f"https://api.github.com/repos/{REPOSITORY}/issues/103"
        with self.assertRaisesRegex(RequestError, "not attached to the declared origin"):
            verify_bound_request(descriptor(), source, expected_issue_url=ISSUE_URL)

    def test_origin_comment_identity_must_be_exact(self) -> None:
        source = comment()
        source["id"] = COMMENT_ID + 1
        with self.assertRaisesRegex(RequestError, "comment identity mismatch"):
            verify_bound_request(descriptor(), source, expected_issue_url=ISSUE_URL)

    def test_repository_mismatch_is_rejected(self) -> None:
        value = request_value()
        value["repository"] = "stefm78/other"
        with self.assertRaisesRegex(RequestError, "repository differs"):
            verify_bound_request(descriptor(), comment(value), expected_issue_url=ISSUE_URL)

    def test_origin_type_mismatch_is_rejected(self) -> None:
        value = request_value()
        origin = value["origin"]
        assert isinstance(origin, dict)
        origin["type"] = "pull_request"
        with self.assertRaisesRegex(RequestError, "origin type differs"):
            verify_bound_request(descriptor(), comment(value), expected_issue_url=ISSUE_URL)

    def test_origin_number_mismatch_is_rejected(self) -> None:
        value = request_value()
        origin = value["origin"]
        assert isinstance(origin, dict)
        origin["number"] = ORIGIN_NUMBER + 1
        with self.assertRaisesRegex(RequestError, "origin number differs"):
            verify_bound_request(descriptor(), comment(value), expected_issue_url=ISSUE_URL)

    def test_origin_request_digest_and_comment_id_are_jointly_bound(self) -> None:
        value = copy.deepcopy(request_value())
        origin = value["origin"]
        assert isinstance(origin, dict)
        origin["request_comment_id"] = COMMENT_ID + 1
        with self.assertRaisesRegex(RequestError, "origin comment differs"):
            verify_bound_request(descriptor(), comment(value), expected_issue_url=ISSUE_URL)

    def test_exact_origin_binding_succeeds(self) -> None:
        request = verify_bound_request(descriptor(), comment(), expected_issue_url=ISSUE_URL)
        self.assertEqual(request.repository, REPOSITORY)
        self.assertEqual(request.origin.number, ORIGIN_NUMBER)
        self.assertEqual(request.origin.request_comment_id, COMMENT_ID)


if __name__ == "__main__":
    unittest.main()
