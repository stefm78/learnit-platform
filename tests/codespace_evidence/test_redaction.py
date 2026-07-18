"""Independent contradictory QA for secret handling across every evidence surface."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
from unittest import mock
import unittest

from tools.codespace_evidence.execute import (
    CommandRunner,
    collect_environment,
    redact_argv,
    redact_text,
    redact_value,
)


class RedactionTests(unittest.TestCase):
    def test_secret_in_argv_is_redacted(self) -> None:
        redacted = redact_argv(
            ["tool", "--token", "secret-next-argument", "--authorization=Bearer abc", "cookie=value"]
        )
        rendered = " ".join(redacted)
        self.assertNotIn("secret-next-argument", rendered)
        self.assertNotIn("Bearer abc", rendered)
        self.assertNotIn("cookie=value", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_secret_in_stdout_and_stderr_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = CommandRunner()
            record = runner.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import sys; "
                        "print('token=stdout-secret'); "
                        "print('Authorization: Bearer stderr-secret', file=sys.stderr)"
                    ),
                ],
                cwd=Path(directory),
                timeout_seconds=30,
            )
        self.assertNotIn("stdout-secret", record.stdout)
        self.assertNotIn("stderr-secret", record.stderr)
        self.assertIn("[REDACTED]", record.stdout)
        self.assertIn("[REDACTED]", record.stderr)

    def test_secret_in_nested_github_response_is_redacted(self) -> None:
        value = redact_value(
            {
                "login": "qa",
                "token": "github_pat_should_never_survive",
                "nested": {"Authorization": "Bearer secret", "url": "https://user:pass@example.invalid/a"},
            }
        )
        rendered = repr(value)
        self.assertNotIn("github_pat_should_never_survive", rendered)
        self.assertNotIn("Bearer secret", rendered)
        self.assertNotIn("user:pass", rendered)

    def test_environment_evidence_is_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = CommandRunner()
            with mock.patch.dict(
                os.environ,
                {"GH_TOKEN": "github_pat_environment_secret_value", "QA_UNRELATED": "not-recorded"},
                clear=False,
            ):
                facts = collect_environment(runner, Path(directory))
        rendered = repr(facts)
        self.assertNotIn("github_pat_environment_secret_value", rendered)
        self.assertNotIn("QA_UNRELATED", rendered)
        self.assertNotIn("GH_TOKEN", rendered)

    def test_ambient_secret_is_not_exposed_to_fixed_subprocess_output(self) -> None:
        """Ambient credentials must be scrubbed before subprocess launch, not merely hidden from environment.json."""
        secret = "opaque-value-7f51dcd4-that-does-not-look-like-a-token"
        with tempfile.TemporaryDirectory() as directory:
            runner = CommandRunner()
            with mock.patch.dict(os.environ, {"QA_PRIVATE_SECRET": secret}, clear=False):
                record = runner.run(
                    [
                        sys.executable,
                        "-c",
                        "import os; print(os.environ['QA_PRIVATE_SECRET'])",
                    ],
                    cwd=Path(directory),
                    timeout_seconds=30,
                )
        self.assertNotIn(
            secret,
            record.stdout,
            "subprocess environment must be allowlisted or secret values must be redacted even when printed without a key",
        )

    def test_common_authorization_and_url_credentials_are_removed(self) -> None:
        redacted = redact_text(
            "Authorization: Basic dXNlcjpwYXNz https://alice:password@example.invalid/path password=raw"
        )
        self.assertNotIn("dXNlcjpwYXNz", redacted)
        self.assertNotIn("alice:password", redacted)
        self.assertNotIn("password=raw", redacted)


if __name__ == "__main__":
    unittest.main()
