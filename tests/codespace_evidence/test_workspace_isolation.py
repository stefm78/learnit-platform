"""Independent contradictory QA for disposable workspace and primary checkout isolation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest

from tools.codespace_evidence.workspace import (
    CheckoutSnapshot,
    compare_snapshots,
    exact_sha_workspace,
)


SHA = "3" * 40
REPOSITORY = "stefm78/learnit-platform"


class WorkspaceRunner:
    def __init__(self) -> None:
        self.counter = 0
        self.argv: list[list[str]] = []

    def run(self, argv: list[str], *, cwd: Path, timeout_seconds: int = 300, **_: object) -> SimpleNamespace:
        del timeout_seconds
        self.counter += 1
        self.argv.append(list(argv))
        if argv[:3] == ["gh", "repo", "clone"]:
            Path(argv[4]).mkdir(parents=True, exist_ok=False)
        stdout = SHA + "\n" if argv[:3] == ["git", "rev-parse", "HEAD"] else ""
        return SimpleNamespace(
            id=f"cmd-{self.counter:03d}",
            return_code=0,
            timed_out=False,
            stdout=stdout,
            stderr="",
        )


class WorkspaceIsolationTests(unittest.TestCase):
    def snapshot(self, *, head: str = SHA, status: str = "s", refs: str = "r") -> CheckoutSnapshot:
        return CheckoutSnapshot(
            root="/primary",
            head_sha=head,
            branch="topic",
            status_sha256=status,
            refs_sha256=refs,
            index_sha256="i",
            remotes_sha256="m",
        )

    def test_identical_primary_checkout_snapshots_are_unchanged(self) -> None:
        proof = compare_snapshots(self.snapshot(), self.snapshot())
        self.assertTrue(proof["unchanged"])
        self.assertEqual(proof["changed_fields"], [])

    def test_any_primary_checkout_change_is_reported(self) -> None:
        proof = compare_snapshots(self.snapshot(), self.snapshot(head="4" * 40, status="changed"))
        self.assertFalse(proof["unchanged"])
        self.assertEqual(proof["changed_fields"], ["head_sha", "status_sha256"])

    def test_deliberately_mutating_profile_is_confined_to_disposable_workspace(self) -> None:
        runner = WorkspaceRunner()
        primary = Path(__file__).resolve()
        primary_before = primary.read_bytes()
        workspace_root: Path | None = None
        with exact_sha_workspace(runner, repository=REPOSITORY, target_sha=SHA) as workspace:
            workspace_root = workspace.path.parent
            self.assertEqual(workspace.target_sha, SHA)
            self.assertTrue(workspace.path.is_dir())
            (workspace.path / "MUTATION_FROM_PROFILE.txt").write_text("mutated", encoding="utf-8")
            self.assertTrue((workspace.path / "MUTATION_FROM_PROFILE.txt").is_file())
        assert workspace_root is not None
        self.assertFalse(workspace_root.exists())
        self.assertEqual(primary.read_bytes(), primary_before)

    def test_workspace_fetches_and_checks_out_the_exact_full_sha(self) -> None:
        runner = WorkspaceRunner()
        with exact_sha_workspace(runner, repository=REPOSITORY, target_sha=SHA):
            pass
        rendered = [" ".join(argv) for argv in runner.argv]
        self.assertTrue(any(f"origin {SHA}" in command for command in rendered))
        self.assertTrue(any(f"cat-file -e {SHA}^{{commit}}" in command for command in rendered))
        self.assertTrue(any(f"checkout --detach {SHA}" in command for command in rendered))

    def test_clone_is_private_to_a_fresh_temporary_directory(self) -> None:
        runner = WorkspaceRunner()
        with exact_sha_workspace(runner, repository=REPOSITORY, target_sha=SHA) as workspace:
            self.assertIn("codespace-evidence-", workspace.path.parent.name)
            self.assertEqual(workspace.path.name, "repository")
        clone = next(argv for argv in runner.argv if argv[:3] == ["gh", "repo", "clone"])
        self.assertIn("--no-checkout", clone)
        self.assertIn("--filter=blob:none", clone)


if __name__ == "__main__":
    unittest.main()
