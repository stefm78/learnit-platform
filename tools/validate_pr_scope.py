#!/usr/bin/env python3
"""Validate a pull request against one canonical Learn-it work package."""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
WP_RE = re.compile(r"\b([A-Z][A-Z0-9-]*-WP-\d{3})\b")
FORBIDDEN_ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz", ".7z", ".rar", ".exe", ".dll", ".so", ".dylib")
GENERATED_PREFIXES = (".agent-jobs/", ".agent-runtime/", ".agent-result/", ".import/", "apps/player/dist/", "apps/player/reports/", "apps/player/release/")
SENSITIVE_DOMAINS = {
    "player-runtime": ("apps/player/src/**",),
    "workflow": (".github/workflows/**",),
    "governance": ("governance/**", "docs/governance/**"),
    "architecture": ("docs/architecture/**",),
    "contracts": ("contracts/**", "apps/player/contract/**"),
    "platform": ("platform/**",),
}
AGENT_JOB_ROOT = ".agent-jobs"
AGENT_JOB_FILES = {"READY", "change.patch", "job.json"}
AGENT_BRANCH_RE = re.compile(r"^agent/[A-Za-z0-9._/-]+$")
JOB_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]{2,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GLOB_TOKENS = ("*", "?", "[")


class ScopeError(RuntimeError):
    pass


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
    if check and completed.returncode:
        raise ScopeError(completed.stderr.strip() or completed.stdout.strip() or f"command failed: {' '.join(args)}")
    return completed


def git(*args: str) -> str:
    return run(["git", *args]).stdout.strip()


def normalize_path(value: str) -> str:
    raw = value.replace("\\", "/").strip()
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "." in path.parts or "\x00" in raw:
        raise ScopeError(f"unsafe repository path: {value!r}")
    return path.as_posix()


def matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def load_work_package(body: str) -> tuple[str, dict[str, Any], Path]:
    ids = sorted(set(WP_RE.findall(body or "")))
    if len(ids) != 1:
        raise ScopeError(f"pull request body must name exactly one work package; found {ids}")
    wp_id = ids[0]
    path = ROOT / "work-packages" / f"{wp_id}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScopeError(f"missing canonical work package: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ScopeError(f"invalid work package JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("id") != wp_id:
        raise ScopeError("work package id does not match its canonical file")
    return wp_id, payload, path


def changed_files(base: str, head: str) -> list[dict[str, str]]:
    git("cat-file", "-e", f"{base}^{{commit}}")
    git("cat-file", "-e", f"{head}^{{commit}}")
    if git("merge-base", base, head) != base:
        raise ScopeError("base commit is not an ancestor of head commit")
    output = git("diff", "--name-status", "-z", f"{base}...{head}")
    if not output:
        raise ScopeError("pull request has no changed files")
    tokens = output.split("\0")
    rows: list[dict[str, str]] = []
    index = 0
    while index < len(tokens) and tokens[index]:
        status = tokens[index]
        index += 1
        if status.startswith(("R", "C")):
            old_path = normalize_path(tokens[index])
            new_path = normalize_path(tokens[index + 1])
            index += 2
            rows.append({"status": status, "path": new_path, "oldPath": old_path})
        else:
            path = normalize_path(tokens[index])
            index += 1
            rows.append({"status": status, "path": path})
    return rows


def validate_modes(base: str, head: str) -> None:
    summary = git("diff", "--summary", f"{base}...{head}")
    if "mode 120000" in summary or "mode 160000" in summary or "Subproject commit" in summary:
        raise ScopeError("symbolic links and submodules are forbidden")
    numstat = git("diff", "--numstat", f"{base}...{head}")
    for line in numstat.splitlines():
        parts = line.split("\t", 2)
        if len(parts) >= 2 and (parts[0] == "-" or parts[1] == "-"):
            raise ScopeError(f"binary change is forbidden: {line}")


def canonical_path_error(path: str, allowed: list[str], forbidden: list[str], wp_id: str) -> str | None:
    if path.lower().endswith(FORBIDDEN_ARCHIVE_SUFFIXES):
        return f"{path}: archive or executable payload is forbidden"
    if matches(path, forbidden):
        return f"{path}: explicitly forbidden by {wp_id}"
    if not matches(path, allowed):
        return f"{path}: outside allowedPaths of {wp_id}"
    return None


def parse_patch_paths(patch_path: Path, *, check_apply: bool) -> list[str]:
    try:
        patch_text = patch_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ScopeError("Remote Agent change.patch is missing") from exc
    if "GIT binary patch" in patch_text or "\x00" in patch_text:
        raise ScopeError("Remote Agent patch must contain text changes only")
    if "mode 120000" in patch_text or "mode 160000" in patch_text or "Subproject commit" in patch_text:
        raise ScopeError("Remote Agent patch cannot create symbolic links or submodules")
    if check_apply:
        run(["git", "apply", "--check", "--whitespace=error-all", str(patch_path)])
    rows = run(["git", "apply", "--numstat", str(patch_path)]).stdout.splitlines()
    paths: list[str] = []
    for line in rows:
        parts = line.split("\t", 2)
        if len(parts) != 3 or parts[0] == "-" or parts[1] == "-":
            raise ScopeError(f"invalid Remote Agent patch numstat: {line}")
        paths.append(normalize_path(parts[2]))
    if not paths or len(paths) != len(set(paths)):
        raise ScopeError("Remote Agent patch must change unique text files")
    return paths


def validate_agent_transport(
    rows: list[dict[str, str]],
    *,
    base: str,
    wp_id: str,
    allowed: list[str],
    forbidden: list[str],
) -> dict[str, Any] | None:
    changed_paths = sorted({row["path"] for row in rows})
    transport_paths = [path for path in changed_paths if path.startswith(f"{AGENT_JOB_ROOT}/")]
    if not transport_paths:
        return None

    job_dirs = {str(PurePosixPath(path).parent) for path in transport_paths}
    if len(job_dirs) != 1:
        raise ScopeError("Remote Agent pull request must contain exactly one job directory")
    job_dir = next(iter(job_dirs))
    job_id = PurePosixPath(job_dir).name
    if not JOB_ID_RE.fullmatch(job_id):
        raise ScopeError("Remote Agent job directory has an invalid id")

    expected = {f"{job_dir}/{name}" for name in AGENT_JOB_FILES}
    if set(transport_paths) != expected:
        missing = sorted(expected - set(transport_paths))
        extra = sorted(set(transport_paths) - expected)
        raise ScopeError(
            "Remote Agent transport must contain exactly READY, change.patch and job.json; "
            f"missing={missing}, extra={extra}"
        )

    job_path = ROOT / job_dir / "job.json"
    patch_path = ROOT / job_dir / "change.patch"
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScopeError("Remote Agent job.json is missing") from exc
    except json.JSONDecodeError as exc:
        raise ScopeError(f"Remote Agent job.json is invalid: {exc}") from exc
    if not isinstance(job, dict) or job.get("schemaVersion") != 1:
        raise ScopeError("Remote Agent job.json must use schemaVersion 1")
    if job.get("id") != job_id:
        raise ScopeError("Remote Agent job id must match its directory")
    branch = str(job.get("branch", ""))
    if not AGENT_BRANCH_RE.fullmatch(branch):
        raise ScopeError("Remote Agent job branch must use agent/**")
    job_base = str(job.get("baseCommit", "")).lower()
    if not SHA_RE.fullmatch(job_base) or job_base != base:
        raise ScopeError("Remote Agent job baseCommit must equal the pull request base SHA")
    patch_rel = normalize_path(str(job.get("patchFile", "")))
    if patch_rel != f"{job_dir}/change.patch":
        raise ScopeError("Remote Agent patchFile must reference its own change.patch")

    job_allowed = job.get("allowedPaths")
    if not isinstance(job_allowed, list) or not job_allowed or not all(isinstance(item, str) for item in job_allowed):
        raise ScopeError("Remote Agent allowedPaths must be a non-empty string list")
    normalized_job_allowed = [normalize_path(item) for item in job_allowed]
    if len(normalized_job_allowed) != len(set(normalized_job_allowed)):
        raise ScopeError("Remote Agent allowedPaths must be unique")
    if any(any(token in item for token in GLOB_TOKENS) for item in normalized_job_allowed):
        raise ScopeError("Remote Agent allowedPaths must be exact files, not globs")
    for path in normalized_job_allowed:
        if path.startswith(GENERATED_PREFIXES):
            raise ScopeError(f"{path}: generated path cannot be an implementation target")
        error = canonical_path_error(path, allowed, forbidden, wp_id)
        if error:
            raise ScopeError(error)

    result_paths = sorted(path for path in changed_paths if path not in transport_paths)
    patch_paths = parse_patch_paths(patch_path, check_apply=not result_paths)
    for path in patch_paths:
        if path not in normalized_job_allowed:
            raise ScopeError(f"{path}: Remote Agent patch path is outside job allowedPaths")
        error = canonical_path_error(path, allowed, forbidden, wp_id)
        if error:
            raise ScopeError(error)

    for path in result_paths:
        if path.startswith(GENERATED_PREFIXES):
            raise ScopeError(f"{path}: generated result path is forbidden")
        if path not in normalized_job_allowed:
            raise ScopeError(f"{path}: tested result path is outside Remote Agent allowedPaths")
        error = canonical_path_error(path, allowed, forbidden, wp_id)
        if error:
            raise ScopeError(error)

    return {
        "mode": "remote-agent-envelope" if not result_paths else "remote-agent-tested-result",
        "jobId": job_id,
        "jobBranch": branch,
        "transportPaths": transport_paths,
        "patchPaths": sorted(patch_paths),
        "resultPaths": result_paths,
        "effectivePaths": sorted(set(patch_paths) | set(result_paths)),
    }


def validate_scope(body: str, base: str, head: str) -> dict[str, Any]:
    wp_id, package, wp_path = load_work_package(body)
    scope = package.get("scope")
    if not isinstance(scope, dict):
        raise ScopeError("work package has no scope object")
    allowed = scope.get("allowedPaths")
    forbidden = scope.get("forbiddenPaths")
    if not isinstance(allowed, list) or not allowed or not all(isinstance(x, str) for x in allowed):
        raise ScopeError("allowedPaths must be a non-empty string list")
    if not isinstance(forbidden, list) or not all(isinstance(x, str) for x in forbidden):
        raise ScopeError("forbiddenPaths must be a string list")
    allowed = [normalize_path(value) for value in allowed]
    forbidden = [normalize_path(value) for value in forbidden]
    if any(value in {"*", "**", "**/*"} for value in allowed):
        raise ScopeError("global allowedPaths are forbidden")

    rows = changed_files(base, head)
    validate_modes(base, head)
    transport = validate_agent_transport(rows, base=base, wp_id=wp_id, allowed=allowed, forbidden=forbidden)

    violations: list[str] = []
    changed_paths: list[str] = []
    transport_paths = set(transport["transportPaths"]) if transport else set()
    for row in rows:
        candidates = [row["path"]]
        if row.get("oldPath"):
            candidates.append(row["oldPath"])
        for path in candidates:
            changed_paths.append(path)
            if path in transport_paths:
                continue
            if path.startswith(GENERATED_PREFIXES):
                violations.append(f"{path}: generated or transport path is forbidden")
            error = canonical_path_error(path, allowed, forbidden, wp_id)
            if error:
                violations.append(error)

    canonical_wp = wp_path.relative_to(ROOT).as_posix()
    if canonical_wp in changed_paths and not matches(canonical_wp, allowed):
        violations.append(f"{canonical_wp}: a changed work package must authorize its own canonical file")

    effective_paths = transport["effectivePaths"] if transport else changed_paths
    active_domains = sorted(
        name for name, patterns in SENSITIVE_DOMAINS.items()
        if any(matches(path, patterns) for path in effective_paths)
    )
    if "player-runtime" in active_domains and len(active_domains) > 1:
        violations.append("player runtime changes cannot be mixed with workflow, governance, architecture, contract, or platform domains")
    if "platform" in active_domains and any(name != "platform" for name in active_domains):
        violations.append("platform changes must not be mixed with other sensitive domains")

    if violations:
        raise ScopeError("scope violations:\n- " + "\n- ".join(sorted(set(violations))))

    report: dict[str, Any] = {
        "schema": "learnit.pr_scope_report.v2",
        "ok": True,
        "workPackage": wp_id,
        "workPackageStatus": package.get("status"),
        "baseCommit": base,
        "headCommit": head,
        "changedFiles": sorted(set(changed_paths)),
        "changedFileCount": len(set(changed_paths)),
        "effectiveScopedFiles": sorted(set(effective_paths)),
        "sensitiveDomains": active_domains,
        "allowedPaths": allowed,
        "forbiddenPaths": forbidden,
    }
    if transport:
        report["remoteAgent"] = {key: value for key, value in transport.items() if key != "effectivePaths"}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        body = args.body_file.read_text(encoding="utf-8")
        report = validate_scope(body, args.base.lower(), args.head.lower())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    except (ScopeError, OSError, ValueError) as exc:
        print(f"PR SCOPE ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
