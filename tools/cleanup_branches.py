#!/usr/bin/env python3
"""Delete only GitHub branches that are proven safe to remove.

Safety policy:
- never delete the repository default branch;
- never delete a branch backing an open pull request;
- delete a same-repository branch referenced by a closed pull request;
- otherwise delete only when the branch has no commits absent from default;
- retain unproven orphan branches for explicit review.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"GitHub API {status}: {message}")
        self.status = status


@dataclass(frozen=True)
class PullRequestHeads:
    open_heads: frozenset[str]
    closed_heads: frozenset[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def api_request(token: str, method: str, path: str) -> tuple[Any, dict[str, str]]:
    request = Request(
        f"{API_ROOT}{path}",
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "learnit-branch-hygiene",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            payload = json.loads(raw.decode("utf-8")) if raw else None
            return payload, {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
            message = str(payload.get("message") or raw)
        except json.JSONDecodeError:
            message = raw or str(exc)
        raise ApiError(exc.code, message) from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub API unavailable: {exc}") from exc


def api_get_all(token: str, path: str) -> list[Any]:
    separator = "&" if "?" in path else "?"
    page = 1
    items: list[Any] = []
    while True:
        payload, _ = api_request(token, "GET", f"{path}{separator}per_page=100&page={page}")
        if not isinstance(payload, list):
            raise RuntimeError(f"Expected list from {path}, received {type(payload).__name__}")
        items.extend(payload)
        if len(payload) < 100:
            return items
        page += 1
        if page > 100:
            raise RuntimeError(f"Pagination safety limit exceeded for {path}")


def collect_pr_heads(token: str, repository: str) -> PullRequestHeads:
    pulls = api_get_all(token, f"/repos/{repository}/pulls?state=all")
    open_heads: set[str] = set()
    closed_heads: set[str] = set()
    for pull in pulls:
        head = pull.get("head") or {}
        head_repo = head.get("repo") or {}
        if head_repo.get("full_name") != repository:
            continue
        branch = head.get("ref")
        if not isinstance(branch, str) or not branch:
            continue
        if pull.get("state") == "open":
            open_heads.add(branch)
        else:
            closed_heads.add(branch)
    return PullRequestHeads(frozenset(open_heads), frozenset(closed_heads))


def classify_branch(
    branch: str,
    default_branch: str,
    open_heads: frozenset[str],
    closed_heads: frozenset[str],
    fully_merged: bool,
) -> tuple[str, bool]:
    if branch == default_branch:
        return "default-branch", False
    if branch in open_heads:
        return "open-pull-request", False
    if branch in closed_heads:
        return "closed-pull-request", True
    if fully_merged:
        return "fully-merged", True
    return "unproven-orphan", False


def branch_fully_merged(token: str, repository: str, branch: str, default_branch: str) -> bool:
    base = quote(branch, safe="")
    head = quote(default_branch, safe="")
    payload, _ = api_request(token, "GET", f"/repos/{repository}/compare/{base}...{head}")
    if not isinstance(payload, dict):
        return False
    return int(payload.get("behind_by", 1)) == 0


def delete_branch(token: str, repository: str, branch: str) -> str:
    encoded = quote(branch, safe="")
    try:
        api_request(token, "DELETE", f"/repos/{repository}/git/refs/heads/{encoded}")
        return "deleted"
    except ApiError as exc:
        if exc.status in {404, 422}:
            return "already-absent"
        raise


def self_test() -> None:
    open_heads = frozenset({"feature/open"})
    closed_heads = frozenset({"smoke/closed"})
    cases = {
        "main": (False, "default-branch", False),
        "feature/open": (False, "open-pull-request", False),
        "smoke/closed": (False, "closed-pull-request", True),
        "feature/merged": (True, "fully-merged", True),
        "orphan/unproven": (False, "unproven-orphan", False),
    }
    for branch, (merged, expected_reason, expected_delete) in cases.items():
        reason, should_delete = classify_branch(branch, "main", open_heads, closed_heads, merged)
        assert (reason, should_delete) == (expected_reason, expected_delete), (
            branch,
            reason,
            should_delete,
        )
    print(json.dumps({"ok": True, "cases": len(cases), "policy": "safe-delete-v1"}))


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely remove proven-stale GitHub branches.")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--execute", action="store_true", help="Delete eligible branches. Default is dry-run.")
    parser.add_argument("--output", default="branch-hygiene-report.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not REPOSITORY_RE.fullmatch(args.repository):
        raise SystemExit("Invalid or missing owner/repository identifier")
    if not args.token:
        raise SystemExit("Missing GITHUB_TOKEN")

    repository_payload, _ = api_request(args.token, "GET", f"/repos/{args.repository}")
    default_branch = str(repository_payload.get("default_branch") or "")
    if not default_branch:
        raise RuntimeError("Repository default branch is unavailable")

    branches = api_get_all(args.token, f"/repos/{args.repository}/branches")
    pull_heads = collect_pr_heads(args.token, args.repository)
    default_before, _ = api_request(
        args.token,
        "GET",
        f"/repos/{args.repository}/branches/{quote(default_branch, safe='')}",
    )
    default_sha_before = str((default_before.get("commit") or {}).get("sha") or "")

    decisions: list[dict[str, Any]] = []
    for item in sorted(branches, key=lambda value: str(value.get("name") or "")):
        branch = str(item.get("name") or "")
        if not branch:
            continue
        merged = False
        merge_error = None
        if branch != default_branch and branch not in pull_heads.open_heads and branch not in pull_heads.closed_heads:
            try:
                merged = branch_fully_merged(args.token, args.repository, branch, default_branch)
            except Exception as exc:  # retain rather than delete when proof is unavailable
                merge_error = str(exc)
        reason, eligible = classify_branch(
            branch,
            default_branch,
            pull_heads.open_heads,
            pull_heads.closed_heads,
            merged,
        )
        action = "retain"
        error = merge_error
        if eligible:
            action = "would-delete"
            if args.execute:
                try:
                    action = delete_branch(args.token, args.repository, branch)
                except Exception as exc:
                    action = "delete-failed"
                    error = str(exc)
        decisions.append(
            {
                "branch": branch,
                "sha": str((item.get("commit") or {}).get("sha") or ""),
                "reason": reason,
                "eligible": eligible,
                "action": action,
                "error": error,
            }
        )

    default_after, _ = api_request(
        args.token,
        "GET",
        f"/repos/{args.repository}/branches/{quote(default_branch, safe='')}",
    )
    default_sha_after = str((default_after.get("commit") or {}).get("sha") or "")
    default_unchanged = bool(default_sha_before) and default_sha_before == default_sha_after

    report = {
        "schema": "learnit.branch-hygiene-report.v1",
        "generatedAt": utc_now(),
        "repository": args.repository,
        "mode": "execute" if args.execute else "dry-run",
        "defaultBranch": default_branch,
        "defaultBranchShaBefore": default_sha_before,
        "defaultBranchShaAfter": default_sha_after,
        "defaultBranchUnchanged": default_unchanged,
        "openPullRequestHeads": sorted(pull_heads.open_heads),
        "closedPullRequestHeads": sorted(pull_heads.closed_heads),
        "summary": {
            "branchesObserved": len(decisions),
            "deleted": sum(item["action"] == "deleted" for item in decisions),
            "alreadyAbsent": sum(item["action"] == "already-absent" for item in decisions),
            "retainedOpen": sum(item["reason"] == "open-pull-request" for item in decisions),
            "retainedOrphan": sum(item["reason"] == "unproven-orphan" for item in decisions),
            "failures": sum(item["action"] == "delete-failed" for item in decisions),
        },
        "decisions": decisions,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

    if not default_unchanged:
        print("Default branch changed during cleanup", file=sys.stderr)
        return 1
    if report["summary"]["failures"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
