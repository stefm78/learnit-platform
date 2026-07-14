#!/usr/bin/env python3
"""Validated remote worktree runner for Learn-it agent branches."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / ".agent-runtime"
JOB_ROOT = ROOT / ".agent-jobs"
BRANCH_RE = re.compile(r"^agent/[A-Za-z0-9._/-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
JOB_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]{2,63}$")
HARD_MAX_PATCH_BYTES = 1_000_000
HARD_MAX_CHANGED_FILES = 80
HARD_MAX_CHANGED_LINES = 8_000
DEFAULT_FORBIDDEN = (
    ".github/**", ".agent-jobs/**", ".agent-runtime/**", ".agent-result/**", ".git/**", "governance/**",
    "docs/architecture/**", "work-packages/**", "tools/agent_worktree.py",
)
PROFILE_COMMANDS: dict[str, list[list[str]]] = {
    "repository": [],
    "player-fast": [["make", "-C", "apps/player", "test-fast"]],
    "player-full": [["make", "-C", "apps/player", "test"]],
}


class AgentError(RuntimeError):
    pass


def run(args: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(args, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and completed.returncode != 0:
        raise AgentError(
            f"command failed ({completed.returncode}): {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def git(*args: str, check: bool = True) -> str:
    return run(["git", *args], check=check).stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AgentError(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise AgentError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise AgentError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_repo_path(value: str) -> str:
    raw = value.replace("\\", "/").strip()
    if not raw or raw.startswith("/") or "\x00" in raw:
        raise AgentError(f"unsafe repository path: {value!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise AgentError(f"unsafe repository path: {value!r}")
    return path.as_posix()


def match_any(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def discover_job() -> tuple[Path, dict[str, Any]]:
    ready_files = sorted(JOB_ROOT.glob("*/READY"))
    if len(ready_files) != 1:
        raise AgentError(f"expected exactly one READY job, found {len(ready_files)}")
    job_dir = ready_files[0].parent
    return job_dir, load_json(job_dir / "job.json")


def validate_job(job_dir: Path, job: dict[str, Any]) -> dict[str, Any]:
    branch = os.environ.get("AGENT_BRANCH") or os.environ.get("GITHUB_REF_NAME", git("branch", "--show-current"))
    if not BRANCH_RE.fullmatch(branch):
        raise AgentError(f"remote worktree only accepts agent/** branches: {branch}")
    required = {
        "schemaVersion", "id", "baseCommit", "branch", "patchFile",
        "allowedPaths", "forbiddenPaths", "testProfile", "commitMessage",
    }
    missing = sorted(required - set(job))
    if missing:
        raise AgentError(f"job is missing required fields: {', '.join(missing)}")
    if job["schemaVersion"] != 1:
        raise AgentError("unsupported job schemaVersion")
    job_id = str(job["id"])
    if not JOB_ID_RE.fullmatch(job_id) or job_dir.name != job_id:
        raise AgentError("invalid job id or directory")
    base = str(job["baseCommit"]).lower()
    if not SHA_RE.fullmatch(base):
        raise AgentError("baseCommit must be a full lowercase SHA")
    if str(job["branch"]) != branch:
        raise AgentError("job branch does not match the triggering branch")

    patch_rel = normalize_repo_path(str(job["patchFile"]))
    prefix = f".agent-jobs/{job_id}/"
    if not patch_rel.startswith(prefix):
        raise AgentError("patchFile must be inside its own job directory")
    patch_path = ROOT / patch_rel
    if not patch_path.is_file():
        raise AgentError(f"missing patch file: {patch_rel}")
    limit = min(max(1, int(job.get("maxPatchBytes", HARD_MAX_PATCH_BYTES))), HARD_MAX_PATCH_BYTES)
    if patch_path.stat().st_size > limit:
        raise AgentError("patch exceeds size limit")
    patch_text = patch_path.read_text(encoding="utf-8")
    if "GIT binary patch" in patch_text or "\x00" in patch_text:
        raise AgentError("binary patches are forbidden")
    if "mode 120000" in patch_text or "mode 160000" in patch_text or "Subproject commit" in patch_text:
        raise AgentError("symbolic links and submodules are forbidden")

    allowed = job["allowedPaths"]
    forbidden = job["forbiddenPaths"]
    if not isinstance(allowed, list) or not allowed or not all(isinstance(x, str) for x in allowed):
        raise AgentError("allowedPaths must be a non-empty string list")
    if not isinstance(forbidden, list) or not all(isinstance(x, str) for x in forbidden):
        raise AgentError("forbiddenPaths must be a string list")
    if any(x in {"*", "**", "**/*"} for x in allowed):
        raise AgentError("overbroad allowedPaths are forbidden")
    allowed = [normalize_repo_path(x) for x in allowed]
    forbidden = [normalize_repo_path(x) for x in forbidden] + list(DEFAULT_FORBIDDEN)

    profile = str(job["testProfile"])
    if profile not in PROFILE_COMMANDS and profile != "player-targeted":
        raise AgentError(f"unsupported testProfile: {profile}")
    targets = job.get("testTargets", [])
    if profile == "player-targeted":
        if not isinstance(targets, list) or not targets:
            raise AgentError("player-targeted requires testTargets")
        clean_targets = []
        for target in targets:
            path = normalize_repo_path(str(target))
            if not path.startswith("apps/player/tests/") or not path.endswith(".py"):
                raise AgentError(f"invalid targeted test: {path}")
            clean_targets.append(path)
        targets = clean_targets
    elif targets:
        raise AgentError("testTargets only valid with player-targeted")

    message = str(job["commitMessage"]).strip()
    if not message or "\n" in message or len(message) > 120:
        raise AgentError("commitMessage must be one line of 1..120 chars")

    git("cat-file", "-e", f"{base}^{{commit}}")
    if git("merge-base", base, "HEAD") != base:
        raise AgentError("baseCommit is not an ancestor of the trigger commit")
    staged_paths = [x for x in git("diff", "--name-only", f"{base}...HEAD").splitlines() if x]
    foreign = [x for x in staged_paths if not x.startswith(prefix)]
    if foreign:
        raise AgentError("branch contains non-job changes before application: " + ", ".join(foreign))

    run(["git", "apply", "--check", "--whitespace=error-all", str(patch_path)])
    numstat = run(["git", "apply", "--numstat", str(patch_path)]).stdout.splitlines()
    patch_paths: list[str] = []
    additions = deletions = 0
    for line in numstat:
        parts = line.split("\t", 2)
        if len(parts) != 3 or "-" in parts[:2]:
            raise AgentError(f"invalid patch numstat: {line}")
        add_s, del_s, path_s = parts
        path = normalize_repo_path(path_s)
        additions += int(add_s)
        deletions += int(del_s)
        patch_paths.append(path)
    if not patch_paths or len(set(patch_paths)) != len(patch_paths):
        raise AgentError("patch must change unique text files")
    for target in targets:
        if not (ROOT / target).is_file() and target not in patch_paths:
            raise AgentError(f"targeted test not found in baseline or patch: {target}")
    violations = []
    for path in patch_paths:
        if match_any(path, forbidden):
            violations.append(f"{path}: forbidden")
        elif not match_any(path, allowed):
            violations.append(f"{path}: outside allowedPaths")
    if violations:
        raise AgentError("scope violations:\n" + "\n".join(violations))

    file_limit = min(max(1, int(job.get("maxChangedFiles", 40))), HARD_MAX_CHANGED_FILES)
    line_limit = min(max(1, int(job.get("maxChangedLines", 3000))), HARD_MAX_CHANGED_LINES)
    if len(patch_paths) > file_limit or additions + deletions > line_limit:
        raise AgentError("patch exceeds changed-file or changed-line limits")

    return {
        "schemaVersion": 1,
        "jobId": job_id,
        "jobDir": job_dir.relative_to(ROOT).as_posix(),
        "branch": branch,
        "baseCommit": base,
        "triggerCommit": git("rev-parse", "HEAD"),
        "patchFile": patch_rel,
        "patchSha256": sha256_file(patch_path),
        "allowedPaths": allowed,
        "forbiddenPaths": sorted(set(forbidden)),
        "testProfile": profile,
        "testTargets": targets,
        "commitMessage": message,
        "maxChangedFiles": file_limit,
        "maxChangedLines": line_limit,
        "patchPaths": patch_paths,
        "patchAdditions": additions,
        "patchDeletions": deletions,
    }


def load_plan(path: Path) -> dict[str, Any]:
    plan = load_json(path)
    if plan.get("schemaVersion") != 1:
        raise AgentError("invalid plan schema")
    return plan


def validate_changed_paths(plan: dict[str, Any], against: str) -> dict[str, Any]:
    mode_summary = git("diff", "--summary", against)
    if "mode 120000" in mode_summary or "mode 160000" in mode_summary or "Subproject commit" in mode_summary:
        raise AgentError("symbolic links and submodules are forbidden")
    raw = git("diff", "--numstat", against)
    paths: list[str] = []
    additions = deletions = 0
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        add_s, del_s, path_s = parts
        if add_s == "-" or del_s == "-":
            raise AgentError("binary changes are forbidden")
        path = normalize_repo_path(path_s)
        if path.startswith(plan["jobDir"] + "/") or path.startswith(".agent-runtime/") or path.startswith(".agent-result/"):
            continue
        if match_any(path, plan["forbiddenPaths"]):
            raise AgentError(f"generated change is forbidden: {path}")
        if not match_any(path, plan["allowedPaths"]):
            raise AgentError(f"generated change is outside allowedPaths: {path}")
        additions += int(add_s)
        deletions += int(del_s)
        paths.append(path)
    if len(set(paths)) > int(plan["maxChangedFiles"]) or additions + deletions > int(plan["maxChangedLines"]):
        raise AgentError("final changes exceed job limits")
    return {"paths": sorted(set(paths)), "additions": additions, "deletions": deletions}


def cmd_prepare(output: Path) -> None:
    job_dir, job = discover_job()
    plan = validate_job(job_dir, job)
    write_json(output, plan)
    print(json.dumps(plan, indent=2))


def cmd_apply(plan_path: Path) -> None:
    plan = load_plan(plan_path)
    patch_path = ROOT / plan["patchFile"]
    if sha256_file(patch_path) != plan["patchSha256"]:
        raise AgentError("patch changed after validation")
    run(["git", "apply", "--index", "--whitespace=error-all", str(patch_path)])
    summary = validate_changed_paths(plan, "HEAD")
    if not summary["paths"]:
        raise AgentError("applied patch produced no scoped changes")
    write_json(RUNTIME_DIR / "applied.json", summary)


def cmd_test(plan_path: Path) -> None:
    plan = load_plan(plan_path)
    commands = [*PROFILE_COMMANDS.get(plan["testProfile"], [])]
    if plan["testProfile"] == "player-targeted":
        commands = [["python", target] for target in plan["testTargets"]]
    results = []
    for command in commands:
        completed = run(command, check=False)
        results.append({
            "command": command,
            "returnCode": completed.returncode,
            "stdoutTail": completed.stdout[-4000:],
            "stderrTail": completed.stderr[-4000:],
        })
        if completed.returncode:
            write_json(RUNTIME_DIR / "tests.json", {"ok": False, "results": results})
            raise AgentError(f"test command failed: {' '.join(command)}")
    write_json(RUNTIME_DIR / "tests.json", {"ok": True, "results": results})


def cmd_package(plan_path: Path, output_patch: Path, output_manifest: Path) -> None:
    plan = load_plan(plan_path)
    job_dir = ROOT / plan["jobDir"]
    if job_dir.exists():
        shutil.rmtree(job_dir)
    run(["git", "add", "-A"])
    summary = validate_changed_paths(plan, plan["baseCommit"])
    if not summary["paths"]:
        raise AgentError("no final changes remain")
    output_patch.parent.mkdir(parents=True, exist_ok=True)
    patch = run([
        "git", "diff", "--cached", "--binary", plan["baseCommit"], "--", ".",
        ":(exclude).agent-jobs/**",
    ]).stdout
    if not patch.strip():
        raise AgentError("result patch is empty")
    output_patch.write_text(patch, encoding="utf-8")
    artifact = ROOT / "apps/player/dist/learnit.html"
    manifest = {
        "schemaVersion": 1,
        "jobId": plan["jobId"],
        "branch": plan["branch"],
        "baseCommit": plan["baseCommit"],
        "triggerCommit": plan["triggerCommit"],
        "commitMessage": plan["commitMessage"],
        "resultPatch": output_patch.name,
        "resultPatchSha256": sha256_file(output_patch),
        "changed": summary,
        "testProfile": plan["testProfile"],
        "artifact": ({
            "path": artifact.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(artifact),
            "size": artifact.stat().st_size,
        } if artifact.is_file() else None),
    }
    write_json(output_manifest, manifest)


def cmd_commit_prepare(manifest_path: Path, result_patch: Path) -> None:
    manifest = load_json(manifest_path)
    job_dir, job = discover_job()
    plan = validate_job(job_dir, job)
    for field in ("jobId", "branch", "baseCommit", "triggerCommit", "commitMessage"):
        if manifest.get(field) != plan.get(field):
            raise AgentError(f"result manifest mismatch for {field}")
    if git("rev-parse", "HEAD") != manifest["triggerCommit"]:
        raise AgentError("branch moved after validated run")
    if sha256_file(result_patch) != manifest.get("resultPatchSha256"):
        raise AgentError("result patch digest mismatch")
    run(["git", "apply", "--check", "--whitespace=error-all", str(result_patch)])
    run(["git", "apply", "--index", "--whitespace=error-all", str(result_patch)])
    if job_dir.exists():
        shutil.rmtree(job_dir)
    run(["git", "add", "-A"])
    summary = validate_changed_paths(plan, plan["baseCommit"])
    if summary != manifest.get("changed"):
        raise AgentError("final changes differ from tested result")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("apply"); p.add_argument("--plan", type=Path, required=True)
    p = sub.add_parser("test"); p.add_argument("--plan", type=Path, required=True)
    p = sub.add_parser("package"); p.add_argument("--plan", type=Path, required=True); p.add_argument("--output-patch", type=Path, required=True); p.add_argument("--output-manifest", type=Path, required=True)
    p = sub.add_parser("commit-prepare"); p.add_argument("--manifest", type=Path, required=True); p.add_argument("--result-patch", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    os.chdir(ROOT)
    args = parse_args()
    try:
        if args.command == "prepare": cmd_prepare(args.output)
        elif args.command == "apply": cmd_apply(args.plan)
        elif args.command == "test": cmd_test(args.plan)
        elif args.command == "package": cmd_package(args.plan, args.output_patch, args.output_manifest)
        elif args.command == "commit-prepare": cmd_commit_prepare(args.manifest, args.result_patch)
        return 0
    except AgentError as exc:
        print(f"REMOTE AGENT ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
