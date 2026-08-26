"""Independent hostile static guards against Gate 1 scope/security expansion."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest

import tools.ai_jobs as gate1
import tools.ai_jobs.gate0_adapter as adapter
import tools.ai_jobs.run as run_mod

EXPECTED_QA_PATHS = {
    "tests/ai_jobs/test_contracts.py",
    "tests/ai_jobs/test_snapshot.py",
    "tests/ai_jobs/test_session_exclusivity.py",
    "tests/ai_jobs/test_queue_order.py",
    "tests/ai_jobs/test_crash_recovery.py",
    "tests/ai_jobs/test_publication_ambiguity.py",
    "tests/ai_jobs/test_credential_boundary.py",
    "tests/ai_jobs/test_gate0_integration.py",
    "tests/ai_jobs/test_stop.py",
    "tests/ai_jobs/test_governance_guards.py",
}


class GovernanceGuardTests(unittest.TestCase):
    @property
    def root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def test_work_package_preserves_exact_independent_qa_allowlist(self) -> None:
        work_package = json.loads(
            (self.root / "work-packages" / "OPS-WP-007.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(work_package["scope"]["independentQaAllowedPaths"]), EXPECTED_QA_PATHS)

    def test_later_gates_and_automatic_privileged_actions_remain_forbidden(self) -> None:
        required = {
            "codespace-create", "codespace-start", "codespace-restart", "generic-shell",
            "branch-create", "commit", "push", "workflow-dispatch", "merge", "release",
            "promotion", "governor-decision", "gate2-fan-in",
            "gate3-repository-write-job", "gate4-parallel-execution",
        }
        self.assertTrue(required.issubset(gate1.FORBIDDEN_RUNTIME_CAPABILITIES))

    def test_gate1_cli_has_no_arbitrary_command_repo_write_or_later_gate_switch(self) -> None:
        option_strings: set[str] = set()
        tree = ast.parse(Path(run_mod.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("--"):
                        option_strings.add(arg.value)
        forbidden_fragments = (
            "command", "argv", "shell", "repo-write", "branch", "commit", "push",
            "workflow", "merge", "release", "promot", "gate2", "gate3", "gate4",
            "codespace-create", "codespace-start", "codespace-restart",
        )
        offending = sorted(
            option for option in option_strings
            if any(fragment in option.lower() for fragment in forbidden_fragments)
        )
        self.assertEqual(offending, [])

    def test_privileged_github_transport_has_only_comment_mutation_not_repo_writes(self) -> None:
        source = (self.root / "tools" / "ai_jobs" / "github_transport.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        literals = [
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        forbidden = (
            "/codespaces", "/git/refs", "/merges", "/releases", "/actions/workflows",
            "/deployments", "workflow_dispatch",
        )
        offending = sorted({
            literal for literal in literals
            if any(fragment in literal.lower() for fragment in forbidden)
        })
        self.assertEqual(offending, [])

    def test_no_gate2_gate3_gate4_runtime_modules_exist(self) -> None:
        files = {path.name.lower() for path in (self.root / "tools" / "ai_jobs").glob("*.py")}
        self.assertFalse(any("gate2" in name or "gate3" in name or "gate4" in name for name in files))

    def test_pilot_profile_is_explicitly_not_full_v6_security(self) -> None:
        adapter_source = Path(adapter.__file__).read_text(encoding="utf-8")
        run_source = Path(run_mod.__file__).read_text(encoding="utf-8")
        self.assertIn('PILOT_READ_ONLY = "GATE1_PILOT_READ_ONLY"', adapter_source)
        self.assertIn('FULL_V6_SECURITY = "FULL_V6_SECURITY"', adapter_source)
        self.assertIn("not a cryptographic authorization primitive", adapter_source)
        self.assertIn("not represented as full V6 cryptographic isolation", run_source)

    def test_full_v6_verifier_path_remains_present_but_not_silently_selected_by_pilot(self) -> None:
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        self.assertIn("_verify_effect_capability", source)
        self.assertIn("EffectCapabilityVerifier", source)
        self.assertIn("pilot profile cannot masquerade as signed V6 authority", source)
        self.assertIn("pilot permit cannot be mixed with FULL_V6_SECURITY", source)


if __name__ == "__main__":
    unittest.main()
