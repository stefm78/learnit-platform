"""Independent contradictory R5 transport and publication ambiguity tests."""
from __future__ import annotations

import hashlib
import unittest
from unittest.mock import patch

from tools.ai_jobs.contracts import ContractError
import tools.ai_jobs.github_transport as transport
from tools.ai_jobs.github_transport import Gate1GitHub, GitHubError, validate_r5_readback_envelope


class FakeTransport:
    def __init__(self, hint=None, error=None) -> None:
        self.hint = hint
        self.error = error
        self.calls = 0
    def post_issue_comment_once(self, *, endpoint, body):
        self.calls += 1
        return self.hint, self.error


def published(comment_id: int, body: str = "candidate") -> dict:
    return {
        "id": comment_id,
        "issue_url": "https://api.github.com/repos/stefm78/learnit-platform/issues/160",
        "body": body,
        "user": {"login": "stefm78"},
    }


def bare_client(*, hint=None, error=None) -> Gate1GitHub:
    client = object.__new__(Gate1GitHub)
    client.repository = "stefm78/learnit-platform"
    client._authenticated_login = "stefm78"
    client._ambiguous_effect = False
    client._transport = FakeTransport(hint, error)
    return client


class R5ReadbackTests(unittest.TestCase):
    def test_request_id_accepts_segmented_ascii_forms(self) -> None:
        for request_id in ("ABC123", "abc.def_9-Z", "A:B", "A1:B_2:C-3"):
            with self.subTest(request_id=request_id):
                result = validate_r5_readback_envelope(
                    status=200,
                    headers={"x-github-request-id": request_id, "content-length": "3"},
                    body=b"abc",
                )
                self.assertEqual(result["x-github-request-id"], request_id)

    def test_request_id_rejects_noncanonical_forms(self) -> None:
        for request_id in ("", ":A", "A:", "A::B", "A B", "A/B", "é", "A:é"):
            with self.subTest(request_id=request_id):
                with self.assertRaises(ContractError):
                    validate_r5_readback_envelope(
                        status=200,
                        headers={"x-github-request-id": request_id, "content-length": "3"},
                        body=b"abc",
                    )

    def test_content_length_decimal_ascii_accepts_zero_padding(self) -> None:
        for value in ("3", "03", "003"):
            with self.subTest(value=value):
                validate_r5_readback_envelope(
                    status=200,
                    headers={"x-github-request-id": "A:B", "content-length": value},
                    body=b"abc",
                )

    def test_content_length_rejects_space_sign_hex_non_ascii_and_mismatch(self) -> None:
        for value in (" 3", "3 ", "+3", "-3", "0x3", "٣", "３", "4", ""):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ContractError):
                    validate_r5_readback_envelope(
                        status=200,
                        headers={"x-github-request-id": "A:B", "content-length": value},
                        body=b"abc",
                    )

    def test_http2_without_content_length_is_accepted_only_for_explicit_http2(self) -> None:
        for protocol in ("HTTP/2", "HTTP/2.0"):
            with self.subTest(protocol=protocol):
                result = validate_r5_readback_envelope(
                    status=200,
                    headers={"x-github-request-id": "A:B"},
                    body=b"abc",
                    http_protocol=protocol,
                )
                self.assertIsNone(result["content-length"])

    def test_http1_or_unknown_without_content_length_is_rejected(self) -> None:
        for protocol in (None, "HTTP/1.0", "HTTP/1.1", "HTTP/3"):
            with self.subTest(protocol=protocol):
                with self.assertRaises(ContractError):
                    validate_r5_readback_envelope(
                        status=200,
                        headers={"x-github-request-id": "A:B"},
                        body=b"abc",
                        http_protocol=protocol,
                    )

    def test_non200_noninteger_duplicate_headers_digest_and_chunk_budget_fail_closed(self) -> None:
        good = {"x-github-request-id": "A:B", "content-length": "3"}
        for status in (True, 200.0, 199, 201, 403, 600):
            with self.subTest(status=status):
                with self.assertRaises(ContractError):
                    validate_r5_readback_envelope(status=status, headers=good, body=b"abc")
        with self.assertRaises(ContractError):
            validate_r5_readback_envelope(
                status=200,
                headers={"X-GitHub-Request-Id": "A", "x-github-request-id": "B", "content-length": "3"},
                body=b"abc",
            )
        with self.assertRaises(ContractError):
            validate_r5_readback_envelope(status=200, headers=good, body=b"abc", expected_body_sha256="0" * 64)
        with patch.object(transport, "MAX_CHUNK_BYTES", 2):
            with self.assertRaises(ContractError):
                validate_r5_readback_envelope(status=200, headers=good, body=b"abc")
        expected = hashlib.sha256(b"abc").hexdigest()
        self.assertEqual(
            validate_r5_readback_envelope(status=200, headers=good, body=b"abc", expected_body_sha256=expected)["body_sha256"],
            expected,
        )

    def test_post_reconciles_one_exact_durable_comment_and_never_retries(self) -> None:
        client = bare_client(hint={"id": 7})
        scans = [[], [published(7)]]
        client._stable_comment_scan = lambda _issue: scans.pop(0)
        client.comment = lambda _cid: published(7)
        result = client.publish_authority_comment(160, "candidate")
        self.assertEqual(result["id"], 7)
        self.assertEqual(client._transport.calls, 1)

    def test_post_success_with_unavailable_or_incoherent_direct_readback_is_not_silently_authoritative(self) -> None:
        client = bare_client(hint={"id": 7})
        scans = [[], [published(7)]]
        client._stable_comment_scan = lambda _issue: scans.pop(0)
        client.comment = lambda _cid: published(7, "different")
        with self.assertRaises(GitHubError):
            client.publish_authority_comment(160, "candidate")
        self.assertTrue(client._ambiguous_effect)
        self.assertEqual(client._transport.calls, 1)

    def test_post_with_unstable_reconciliation_enters_ambiguity_hold(self) -> None:
        client = bare_client(hint={"id": 7})
        calls = 0
        def scan(_issue):
            nonlocal calls
            calls += 1
            if calls == 1:
                return []
            raise GitHubError("unstable")
        client._stable_comment_scan = scan
        client.comment = lambda _cid: published(7)
        with self.assertRaises(GitHubError):
            client.publish_authority_comment(160, "candidate")
        self.assertTrue(client._ambiguous_effect)
        with self.assertRaises(GitHubError):
            client.publish_authority_comment(160, "candidate")
        self.assertEqual(client._transport.calls, 1)

    def test_r5_validator_is_wired_into_privileged_transport(self) -> None:
        source = open(transport.__file__, encoding="utf-8").read()
        self.assertGreaterEqual(source.count("validate_r5_readback_envelope("), 2)
        self.assertIn("post_issue_comment_once", source)
        self.assertIn("G1_PUBLICATION_UNKNOWN_HOLD", source)


if __name__ == "__main__":
    unittest.main()
