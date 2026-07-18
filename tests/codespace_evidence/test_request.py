"""Independent contradictory QA for the Gate 0 request contract."""

from __future__ import annotations

import contextlib
import io
import tempfile
from pathlib import Path
import unittest

from tools.codespace_evidence import SCHEMA_VERSION
from tools.codespace_evidence.request import (
    EvidenceRequest,
    RequestError,
    loads_exact,
    request_digest,
)
from tools.codespace_evidence.run import main


SHA = "a" * 40


def valid_request(operation: str = "pr-snapshot") -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "job_id": "CEB-QA-0001",
        "operation": operation,
        "repository": "stefm78/learnit-platform",
        "target_type": "pull_request",
        "target_number": 103,
        "target_sha": SHA,
        "origin": {
            "type": "issue",
            "number": 102,
            "request_comment_id": 12345,
        },
        "created_at": "2026-07-18T12:00:00Z",
        "timeout_seconds": 300,
        "parameters": {
            "test_profile": None,
            "required_checks": [],
            "include_logs": False,
            "include_artifacts": False,
        },
        "allow_new_attempt": False,
    }
    if operation in {"run-repository-validation", "run-test-profile"}:
        value["target_type"] = "commit"
        value.pop("target_number")
        parameters = value["parameters"]
        assert isinstance(parameters, dict)
        parameters["test_profile"] = "repository" if operation == "run-test-profile" else None
    return value


class RequestContractTests(unittest.TestCase):
    def parse(self, value: dict[str, object]) -> EvidenceRequest:
        return EvidenceRequest.from_value(value, request_digest(value))

    def test_missing_launch_descriptor_is_an_idempotent_noop_outside_codespace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "absent.json"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["--request", str(missing)])
        self.assertEqual(result, 0)
        self.assertIn("nothing to do", output.getvalue())

    def test_unknown_top_level_field_fails_closed(self) -> None:
        value = valid_request()
        value["unexpected"] = True
        with self.assertRaisesRegex(RequestError, "unknown fields"):
            self.parse(value)

    def test_unknown_nested_parameter_field_fails_closed(self) -> None:
        value = valid_request()
        parameters = value["parameters"]
        assert isinstance(parameters, dict)
        parameters["command"] = "rm -rf ."
        with self.assertRaisesRegex(RequestError, "unknown fields"):
            self.parse(value)

    def test_unknown_operation_is_rejected(self) -> None:
        value = valid_request()
        value["operation"] = "arbitrary-shell"
        with self.assertRaisesRegex(RequestError, "unsupported operation"):
            self.parse(value)

    def test_invalid_abbreviated_uppercase_and_non_hex_shas_are_rejected(self) -> None:
        for invalid in ("a" * 39, "A" * 40, "g" * 40, "main", ""):
            with self.subTest(invalid=invalid):
                value = valid_request()
                value["target_sha"] = invalid
                with self.assertRaisesRegex(RequestError, "full lowercase 40-character SHA"):
                    self.parse(value)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(RequestError, "duplicate JSON key"):
            loads_exact('{"job_id":"A","job_id":"B"}')

    def test_non_standard_json_constants_are_rejected(self) -> None:
        with self.assertRaisesRegex(RequestError, "invalid JSON constant"):
            loads_exact('{"timeout_seconds":NaN}')

    def test_operation_specific_fields_are_strict(self) -> None:
        value = valid_request("run-repository-validation")
        parameters = value["parameters"]
        assert isinstance(parameters, dict)
        parameters["include_logs"] = True
        with self.assertRaisesRegex(RequestError, "does not accept GitHub evidence parameters"):
            self.parse(value)

    def test_run_test_profile_requires_a_fixed_profile(self) -> None:
        value = valid_request("run-test-profile")
        parameters = value["parameters"]
        assert isinstance(parameters, dict)
        parameters["test_profile"] = None
        with self.assertRaisesRegex(RequestError, "requires parameters.test_profile"):
            self.parse(value)


if __name__ == "__main__":
    unittest.main()
