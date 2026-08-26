"""Independent contradictory Gate 0 byte-identity and fixed-surface tests."""
from __future__ import annotations

import inspect
from pathlib import Path
import subprocess
import unittest

from tools.ai_jobs import GATE0_OPERATIONS
from tools.ai_jobs.contracts import ContractError, validate_gate0_operation
from tools.codespace_evidence import OPERATIONS as GATE0_CANONICAL_OPERATIONS
import tools.ai_jobs.gate0_adapter as adapter

MAIN_SHA = "d32f6ad7f32e213ec5a9d97c3fb9149f985ae491"
EXPECTED = frozenset({
    "pr-snapshot", "pr-governor-evidence",
    "run-repository-validation", "run-test-profile",
})


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=Path(__file__).resolve().parents[2],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


class Gate0IntegrationTests(unittest.TestCase):
    def test_gate0_implementation_tree_is_byte_identical_to_exact_main(self) -> None:
        self.assertEqual(
            git("rev-parse", f"{MAIN_SHA}:tools/codespace_evidence"),
            git("rev-parse", "HEAD:tools/codespace_evidence"),
        )

    def test_gate0_regression_test_tree_is_byte_identical_to_exact_main(self) -> None:
        self.assertEqual(
            git("rev-parse", f"{MAIN_SHA}:tests/codespace_evidence"),
            git("rev-parse", "HEAD:tests/codespace_evidence"),
        )

    def test_gate1_and_gate0_share_exactly_four_operations(self) -> None:
        self.assertEqual(GATE0_OPERATIONS, EXPECTED)
        self.assertEqual(GATE0_CANONICAL_OPERATIONS, EXPECTED)
        self.assertEqual(adapter.EXPECTED_GATE0_OPERATIONS, EXPECTED)

    def test_repo_write_and_later_gate_operations_are_not_gate0_operations(self) -> None:
        for operation in (
            "repo-write", "branch-create", "commit", "push", "workflow-dispatch",
            "merge", "release", "promotion", "gate2-fan-in",
            "gate3-repository-write-job", "gate4-parallel-execution",
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(ContractError):
                    validate_gate0_operation(operation)

    def test_adapter_exposes_no_generic_command_or_request_argv_channel(self) -> None:
        params = set(inspect.signature(adapter.invoke_once).parameters)
        self.assertTrue({"runner", "repository_root", "job"}.issubset(params))
        self.assertFalse(params & {"command", "argv", "shell", "script", "repo_write"})

    def test_adapter_does_not_spawn_generic_subprocess_or_shell(self) -> None:
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("os.system", source)

    def test_adapter_delegates_to_accepted_gate0_entry_and_outcome_election(self) -> None:
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        self.assertIn("gate0_main", source)
        self.assertIn("_discover_candidates", source)
        self.assertIn("_request_via_gateway", source)
        self.assertIn("_authoritative_outcome", source)

    def test_read_only_surface_contains_no_repository_write_operation_alias(self) -> None:
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "repo-write", "branch-create", "workflow-dispatch",
            "gate3-repository-write-job", "gate4-parallel-execution",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(f'"{forbidden}"', source)


if __name__ == "__main__":
    unittest.main()
