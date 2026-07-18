"""Disposable exact-SHA workspace and primary-checkout immutability proofs."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterator

from .execute import CommandRunner, ExecutionError


class WorkspaceError(RuntimeError):
    """Raised when exact-SHA workspace isolation cannot be established."""


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def discover_repository_root(runner: CommandRunner, cwd: Path) -> Path:
    record = runner.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, timeout_seconds=30)
    if record.return_code != 0:
        raise WorkspaceError("current directory is not inside a Git repository")
    return Path(record.stdout.strip()).resolve()


def _git_text(runner: CommandRunner, root: Path, args: list[str]) -> str:
    record = runner.run(["git", *args], cwd=root, timeout_seconds=60)
    if record.return_code != 0:
        raise WorkspaceError(f"git command failed: {' '.join(args)}")
    return record.stdout


@dataclass(frozen=True)
class CheckoutSnapshot:
    root: str
    head_sha: str
    branch: str
    status_sha256: str
    refs_sha256: str
    index_sha256: str
    remotes_sha256: str

    def as_dict(self) -> dict[str, str]:
        return {
            "root": self.root,
            "head_sha": self.head_sha,
            "branch": self.branch,
            "status_sha256": self.status_sha256,
            "refs_sha256": self.refs_sha256,
            "index_sha256": self.index_sha256,
            "remotes_sha256": self.remotes_sha256,
        }


def snapshot_primary_checkout(runner: CommandRunner, root: Path) -> CheckoutSnapshot:
    head = _git_text(runner, root, ["rev-parse", "HEAD"]).strip()
    branch = _git_text(runner, root, ["branch", "--show-current"]).strip()
    status = _git_text(runner, root, ["status", "--porcelain=v1", "--untracked-files=all"])
    refs = _git_text(runner, root, ["show-ref"])
    index = _git_text(runner, root, ["ls-files", "-s"])
    remotes = _git_text(runner, root, ["remote", "-v"])
    return CheckoutSnapshot(
        root=str(root.resolve()),
        head_sha=head,
        branch=branch,
        status_sha256=_digest_text(status),
        refs_sha256=_digest_text(refs),
        index_sha256=_digest_text(index),
        remotes_sha256=_digest_text(remotes),
    )


def compare_snapshots(before: CheckoutSnapshot, after: CheckoutSnapshot) -> dict[str, Any]:
    before_dict = before.as_dict()
    after_dict = after.as_dict()
    changed = sorted(key for key in before_dict if before_dict[key] != after_dict[key])
    return {
        "unchanged": not changed,
        "changed_fields": changed,
        "before": before_dict,
        "after": after_dict,
    }


@dataclass
class DisposableWorkspace:
    path: Path
    target_sha: str
    repository: str
    clone_command_id: str
    fetch_command_id: str
    checkout_command_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "target_sha": self.target_sha,
            "repository": self.repository,
            "commands": {
                "clone": self.clone_command_id,
                "fetch": self.fetch_command_id,
                "checkout": self.checkout_command_id,
            },
        }


@contextmanager
def exact_sha_workspace(
    runner: CommandRunner,
    *,
    repository: str,
    target_sha: str,
    parent: Path | None = None,
) -> Iterator[DisposableWorkspace]:
    temp_root = Path(tempfile.mkdtemp(prefix="codespace-evidence-", dir=str(parent) if parent else None))
    checkout = temp_root / "repository"
    try:
        clone = runner.run(
            [
                "gh",
                "repo",
                "clone",
                repository,
                str(checkout),
                "--",
                "--no-checkout",
                "--filter=blob:none",
            ],
            cwd=temp_root,
            timeout_seconds=600,
        )
        if clone.return_code != 0:
            raise WorkspaceError("failed to clone the repository into the disposable workspace")
        fetch = runner.run(
            ["git", "fetch", "--no-tags", "--force", "origin", target_sha],
            cwd=checkout,
            timeout_seconds=600,
            github_credentials=True,
        )
        if fetch.return_code != 0:
            raise WorkspaceError("failed to fetch the exact target SHA")
        cat_file = runner.run(
            ["git", "cat-file", "-e", f"{target_sha}^{{commit}}"],
            cwd=checkout,
            timeout_seconds=60,
        )
        if cat_file.return_code != 0:
            raise WorkspaceError("target SHA is not an available commit")
        checkout_record = runner.run(
            ["git", "checkout", "--detach", target_sha],
            cwd=checkout,
            timeout_seconds=300,
        )
        if checkout_record.return_code != 0:
            raise WorkspaceError("failed to detach the disposable workspace at target SHA")
        resolved = runner.run(["git", "rev-parse", "HEAD"], cwd=checkout, timeout_seconds=30)
        if resolved.return_code != 0 or resolved.stdout.strip() != target_sha:
            raise WorkspaceError("disposable workspace is not bound to the exact target SHA")
        yield DisposableWorkspace(
            path=checkout,
            target_sha=target_sha,
            repository=repository,
            clone_command_id=clone.id,
            fetch_command_id=fetch.id,
            checkout_command_id=checkout_record.id,
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
