#!/usr/bin/env python3
"""Focused regression tests for the PR-scope Remote Agent transport contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

MODULE_PATH = Path(__file__).with_name("validate_pr_scope.py")
spec = importlib.util.spec_from_file_location("validate_pr_scope", MODULE_PATH)
assert spec and spec.loader
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


def run(root: Path, *args: str) -> str:
    completed = subprocess.run(args, cwd=root, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def commit(root: Path, message: str) -> str:
    run(root, "git", "add", ".")
    run(root, "git", "commit", "-m", message)
    return run(root, "git", "rev-parse", "HEAD")


def build_repo(*, patch_target: str = "apps/player/a.txt", allowed_paths: list[str] | None = None) -> tuple[Path, str, str]:
    root = Path(tempfile.mkdtemp(prefix="learnit-pr-scope-"))
    (root / "work-packages").mkdir(parents=True)
    (root / "apps/player").mkdir(parents=True)
    run(root, "git", "init", "-q")
    run(root, "git", "config", "user.email", "scope@example.invalid")
    run(root, "git", "config", "user.name", "scope-test")
    (root / "apps/player/a.txt").write_text("old\n", encoding="utf-8")
    package = {
        "id": "ARC-WP-999",
        "status": "accepted",
        "scope": {
            "allowedPaths": ["apps/player/a.txt"],
            "forbiddenPaths": ["tools/**", ".github/**"],
        },
    }
    (root / "work-packages/ARC-WP-999.json").write_text(json.dumps(package), encoding="utf-8")
    base = commit(root, "base")

    job_dir = root / ".agent-jobs/JOB-001"
    job_dir.mkdir(parents=True)
    patch = (
        f"diff --git a/{patch_target} b/{patch_target}\n"
        f"--- a/{patch_target}\n"
        f"+++ b/{patch_target}\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    (job_dir / "change.patch").write_text(patch, encoding="utf-8")
    job = {
        "schemaVersion": 1,
        "id": "JOB-001",
        "baseCommit": base,
        "branch": "agent/test",
        "patchFile": ".agent-jobs/JOB-001/change.patch",
        "allowedPaths": allowed_paths or [patch_target],
        "forbiddenPaths": [],
        "testProfile": "repository",
        "commitMessage": "test",
    }
    (job_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
    (job_dir / "READY").write_text("ready\n", encoding="utf-8")
    head = commit(root, "envelope")
    return root, base, head


def expect_scope_error(fn, text: str) -> None:
    try:
        fn()
    except scope.ScopeError as exc:
        assert text in str(exc), str(exc)
    else:
        raise AssertionError(f"expected ScopeError containing {text!r}")


def main() -> int:
    body = "ARC-WP-999"

    root, base, head = build_repo()
    scope.ROOT = root
    report = scope.validate_scope(body, base, head)
    assert report["remoteAgent"]["mode"] == "remote-agent-envelope"
    assert report["effectiveScopedFiles"] == ["apps/player/a.txt"]

    run(root, "git", "apply", ".agent-jobs/JOB-001/change.patch")
    result_head = commit(root, "result")
    report = scope.validate_scope(body, base, result_head)
    assert report["remoteAgent"]["mode"] == "remote-agent-tested-result"
    assert report["remoteAgent"]["resultPaths"] == ["apps/player/a.txt"]

    root, base, head = build_repo(patch_target="tools/escape.txt")
    scope.ROOT = root
    expect_scope_error(lambda: scope.validate_scope(body, base, head), "explicitly forbidden")

    root, base, head = build_repo(allowed_paths=["apps/player/**"])
    scope.ROOT = root
    expect_scope_error(lambda: scope.validate_scope(body, base, head), "exact files, not globs")

    root, base, head = build_repo()
    scope.ROOT = root
    (root / ".agent-jobs/JOB-001/READY").unlink()
    commit(root, "remove ready")
    broken_head = run(root, "git", "rev-parse", "HEAD")
    expect_scope_error(lambda: scope.validate_scope(body, base, broken_head), "exactly READY")

    print("PASS: Remote Agent PR-scope transport contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
