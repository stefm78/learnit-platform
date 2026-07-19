"""Exact four-operation Gate 0 dispatch table."""
from __future__ import annotations
from dataclasses import dataclass, field
import json, re, sys
from pathlib import Path
from typing import Any, Callable
from . import OPERATIONS
from .execute import CommandRunner, redact_text
from .github import GhClient, GitHubError
from .request import EvidenceRequest
from .workspace import WorkspaceError, exact_sha_workspace

@dataclass
class OperationResult:
    status: str
    classification: str
    facts: dict[str, Any]
    missing_proof: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    summary: str = ""

class OperationError(RuntimeError):
    pass

def _diff_paths(diff: str) -> list[str]:
    return sorted(set(m.group(2) for line in diff.splitlines() if (m := re.match(r"diff --git a/(.*?) b/(.*)$", line))))

def _groups(paths: list[str]) -> dict[str, list[str]]:
    result = {"ci_ops": [], "governance": [], "qa": [], "product": [], "other": []}
    for path in paths:
        if path.startswith((".github/", ".devcontainer/", "tools/", "docs/operations/")): key = "ci_ops"
        elif path.startswith(("governance/", "work-packages/", "docs/governance/")): key = "governance"
        elif path.startswith(("tests/", "apps/learnit-next/tests/", "apps/player/tests/")): key = "qa"
        elif path.startswith(("apps/", "authoring/", "contracts/", "kits/")): key = "product"
        else: key = "other"
        result[key].append(path)
    return result

def _reviews(reviews: list[Any], target_sha: str) -> list[dict[str, Any]]:
    out = []
    for review in reviews:
        if not isinstance(review, dict): continue
        user = review.get("user")
        sha = review.get("commit_id")
        out.append({"id": review.get("id"), "state": review.get("state"),
                    "reviewer": user.get("login") if isinstance(user, dict) else None,
                    "submitted_at": review.get("submitted_at"), "reviewed_sha": sha,
                    "matches_target_sha": sha == target_sha})
    return out

def _checks(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    checks = snapshot.get("checks", {})
    for item in checks.get("status_contexts", []):
        if isinstance(item, dict) and isinstance(item.get("context"), str):
            result[item["context"]] = {"source": "status", "state": item.get("state"), "sha": item.get("sha")}
    for item in checks.get("check_runs", []):
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            result[item["name"]] = {"source": "check_run", "status": item.get("status"),
                                      "conclusion": item.get("conclusion"), "head_sha": item.get("head_sha")}
    return result

def pr_snapshot(request: EvidenceRequest, gh: GhClient, runner: CommandRunner) -> OperationResult:
    del runner
    assert request.target_number is not None
    snapshot, artifacts, missing = gh.collect_pr_snapshot(
        repository=request.repository, pr_number=request.target_number, target_sha=request.target_sha,
        include_logs=request.parameters.include_logs, include_artifacts=request.parameters.include_artifacts)
    rest = sorted(x["filename"] for x in snapshot["changed_files"] if isinstance(x.get("filename"), str))
    diff = _diff_paths(artifacts["diff.patch"])
    if rest != diff: missing.append("REST_FILE_INVENTORY_DIFFERS_FROM_UNIFIED_DIFF")
    return OperationResult("COMPLETED", "EVIDENCE_CANDIDATE" if not missing else "INCONCLUSIVE",
        {"pull_request": snapshot, "inventory_consistency": {"consistent": rest == diff, "rest_paths": rest, "diff_paths": diff}},
        sorted(set(missing)), artifacts,
        f"Collected current PR #{request.target_number} evidence at {request.target_sha}; {len(rest)} changed files.")

def pr_governor_evidence(request: EvidenceRequest, gh: GhClient, runner: CommandRunner) -> OperationResult:
    result = pr_snapshot(request, gh, runner)
    snapshot = result.facts["pull_request"]
    inventory = _checks(snapshot)
    required: dict[str, Any] = {}
    for name in request.parameters.required_checks:
        required[name] = inventory.get(name, {"missing": True})
        if name not in inventory: result.missing_proof.append(f"REQUIRED_CHECK_MISSING:{name}")
    paths = [x["filename"] for x in snapshot.get("changed_files", []) if isinstance(x.get("filename"), str)]
    result.facts["governor_evidence"] = {
        "review_sha_bindings": _reviews(snapshot.get("reviews", []), request.target_sha),
        "required_checks": required, "changed_path_groups": _groups(paths),
        "governance_decision": None,
        "interpretation_boundary": "Factual evidence only; no merge, release, acceptance or governor decision."}
    result.missing_proof = sorted(set(result.missing_proof))
    result.classification = "EVIDENCE_CANDIDATE" if not result.missing_proof else "INCONCLUSIVE"
    result.summary = f"Collected governor-oriented factual evidence for PR #{request.target_number} at {request.target_sha}; no decision made."
    return result

PROFILES: dict[str, list[str]] = {
    "repository": [sys.executable, "tools/validate_repository.py"],
    "learnit-next-strict": [sys.executable, "apps/learnit-next/dev/run_checks.py", "--strict"],
    "player-fast": ["make", "-C", "apps/player", "test-fast"],
    "player-full": ["make", "-C", "apps/player", "test"],
}

def _failure(stdout: str, stderr: str, code: int, timed_out: bool) -> tuple[str, str]:
    text = f"{stdout}\n{stderr}".lower()
    if timed_out: return "TIMED_OUT", "FAIL_ENVIRONMENT"
    if "frozen base moved" in text or "parent order differs" in text or "topology" in text: return "FAILED", "FAIL_TOPOLOGY"
    if code in {126, 127} or "not found" in text or "no such file" in text: return "FAILED", "FAIL_ENVIRONMENT"
    return "FAILED", "FAIL_PRODUCT"

def _copy_report(root: Path, relative: str, artifacts: dict[str, str], name: str) -> None:
    path = root / relative
    if path.is_file(): artifacts[name] = redact_text(path.read_text(encoding="utf-8", errors="replace"))

def _run_profile(request: EvidenceRequest, runner: CommandRunner, profile: str) -> OperationResult:
    artifacts: dict[str, str] = {}
    with exact_sha_workspace(runner, repository=request.repository, target_sha=request.target_sha) as workspace:
        before = runner.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=workspace.path, timeout_seconds=30)
        command = runner.run(PROFILES[profile], cwd=workspace.path, timeout_seconds=request.timeout_seconds)
        after = runner.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=workspace.path, timeout_seconds=30)
        _copy_report(workspace.path, "apps/learnit-next/.agent-result/run_checks.json", artifacts, "test-report.json")
        _copy_report(workspace.path, ".agent-result/repository-validation.json", artifacts, "repository-validation.json")
        workspace_facts = {"repository": workspace.repository, "target_sha": workspace.target_sha, "disposable": True,
                           "initial_status": before.stdout, "final_status": after.stdout,
                           "tracked_checkout_changed": any(line and not line.startswith("??") for line in after.stdout.splitlines())}
        command_facts = command.summary(excerpt_bytes=8192)
        status, classification = ("COMPLETED", "TEST_RESULT") if command.return_code == 0 and not command.timed_out else _failure(command.stdout, command.stderr, command.return_code, command.timed_out)
        artifacts.setdefault("test-report.json", json.dumps({"profile": profile, "target_sha": request.target_sha,
            "command": command_facts, "workspace": workspace_facts}, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        return OperationResult(status, classification, {"test_profile": profile, "command": command_facts, "workspace": workspace_facts}, [], artifacts,
            f"Executed fixed profile {profile} in disposable exact-SHA workspace; return code {command.return_code}.")

def run_repository_validation(request: EvidenceRequest, gh: GhClient, runner: CommandRunner) -> OperationResult:
    del gh
    return _run_profile(request, runner, "repository")

def run_test_profile(request: EvidenceRequest, gh: GhClient, runner: CommandRunner) -> OperationResult:
    del gh
    profile = request.parameters.test_profile
    if profile not in PROFILES: raise OperationError("unsupported fixed test profile")
    return _run_profile(request, runner, profile)

HANDLERS: dict[str, Callable[[EvidenceRequest, GhClient, CommandRunner], OperationResult]] = {
    "pr-snapshot": pr_snapshot, "pr-governor-evidence": pr_governor_evidence,
    "run-repository-validation": run_repository_validation, "run-test-profile": run_test_profile}
if frozenset(HANDLERS) != OPERATIONS: raise RuntimeError("dispatch table differs from exact operation allowlist")

def execute_operation(request: EvidenceRequest, gh: GhClient, runner: CommandRunner) -> OperationResult:
    try: return HANDLERS[request.operation](request, gh, runner)
    except (GitHubError, WorkspaceError) as exc:
        return OperationResult("FAILED", "FAIL_ENVIRONMENT", {"error": str(exc)}, [type(exc).__name__], {},
                               f"Operation environment unavailable: {exc}")
