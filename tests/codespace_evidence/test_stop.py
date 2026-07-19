"""Independent contradictory QA for exact Codespace identity and best-effort stop."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import unittest

from tools.codespace_evidence.stop import stop_current_codespace


REPOSITORY = "stefm78/learnit-platform"
NAME = "learnit-qa-space"


class SequenceRunner:
    def __init__(self, records: list[SimpleNamespace]) -> None:
        self.records = list(records)
        self.argv: list[list[str]] = []

    def run(self, argv: list[str], **_: object) -> SimpleNamespace:
        self.argv.append(list(argv))
        if not self.records:
            raise AssertionError(f"unexpected command: {argv}")
        return self.records.pop(0)


def record(*, stdout: str = "", return_code: int = 0, timed_out: bool = False, command_id: str = "cmd-001") -> SimpleNamespace:
    return SimpleNamespace(
        id=command_id,
        stdout=stdout,
        stderr="",
        return_code=return_code,
        timed_out=timed_out,
    )


def codespaces(repository: str = REPOSITORY, name: str = NAME) -> str:
    return json.dumps([{"name": name, "repository": {"nameWithOwner": repository}, "state": "Available"}])


class StopTests(unittest.TestCase):
    def call(self, runner: SequenceRunner, *, verified: bool = True) -> dict[str, object]:
        return stop_current_codespace(
            runner,
            repository_root=Path("."),
            repository=REPOSITORY,
            publication_verified=verified,
        )

    def test_publication_not_verified_disables_stop(self) -> None:
        runner = SequenceRunner([])
        with mock.patch.dict(os.environ, {"CODESPACE_NAME": NAME}, clear=False):
            result = self.call(runner, verified=False)
        self.assertEqual(result["state"], "DISABLED_PUBLICATION_NOT_VERIFIED")
        self.assertEqual(runner.argv, [])

    def test_absent_codespace_name_disables_stop(self) -> None:
        runner = SequenceRunner([])
        with mock.patch.dict(os.environ, {}, clear=True):
            result = self.call(runner)
        self.assertEqual(result["state"], "DISABLED_NO_CODESPACE_NAME")
        self.assertEqual(runner.argv, [])

    def test_invalid_codespace_name_disables_stop(self) -> None:
        runner = SequenceRunner([])
        with mock.patch.dict(os.environ, {"CODESPACE_NAME": "wrong name; rm -rf /"}, clear=True):
            result = self.call(runner)
        self.assertEqual(result["state"], "DISABLED_AMBIGUOUS_CODESPACE_NAME")
        self.assertEqual(runner.argv, [])

    def test_wrong_codespace_repository_disables_stop(self) -> None:
        runner = SequenceRunner([record(stdout=codespaces(repository="stefm78/other"))])
        with mock.patch.dict(os.environ, {"CODESPACE_NAME": NAME}, clear=True):
            result = self.call(runner)
        self.assertEqual(result["state"], "DISABLED_IDENTITY_NOT_EXACT")
        self.assertEqual(result["matching_entries"], 0)
        self.assertEqual(len(runner.argv), 1)

    def test_wrong_codespace_name_disables_stop(self) -> None:
        runner = SequenceRunner([record(stdout=codespaces(name="another-space"))])
        with mock.patch.dict(os.environ, {"CODESPACE_NAME": NAME}, clear=True):
            result = self.call(runner)
        self.assertEqual(result["state"], "DISABLED_IDENTITY_NOT_EXACT")
        self.assertEqual(len(runner.argv), 1)

    def test_codespace_list_failure_is_separate_from_evidence_result(self) -> None:
        runner = SequenceRunner([record(return_code=1)])
        with mock.patch.dict(os.environ, {"CODESPACE_NAME": NAME}, clear=True):
            result = self.call(runner)
        self.assertEqual(result["state"], "STOP_FAILED")
        self.assertEqual(result["reason"], "CODESPACE_LIST_FAILED")

    def test_stop_command_failure_is_reported_without_reclassifying_evidence(self) -> None:
        runner = SequenceRunner(
            [record(stdout=codespaces(), command_id="cmd-001"), record(return_code=1, command_id="cmd-002")]
        )
        with mock.patch.dict(os.environ, {"CODESPACE_NAME": NAME}, clear=True):
            result = self.call(runner)
        self.assertEqual(result["state"], "STOP_FAILED")
        self.assertEqual(result["command_id"], "cmd-002")

    def test_exact_codespace_identity_requests_stop(self) -> None:
        runner = SequenceRunner(
            [record(stdout=codespaces(), command_id="cmd-001"), record(command_id="cmd-002")]
        )
        with mock.patch.dict(os.environ, {"CODESPACE_NAME": NAME}, clear=True):
            result = self.call(runner)
        self.assertEqual(result["state"], "STOP_REQUESTED")
        self.assertEqual(runner.argv[-1], ["gh", "codespace", "stop", "-c", NAME])


if __name__ == "__main__":
    unittest.main()
