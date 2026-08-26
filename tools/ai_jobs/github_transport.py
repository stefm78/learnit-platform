"""Narrow GitHub transport for Gate 1.

Only reads and same-authority issue-comment publication are exposed. Repository
content, refs, workflows, releases, metadata and merge endpoints are unreachable
through this module.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.codespace_evidence.execute import CommandRunner, redact_value
from tools.codespace_evidence.github import GhClient, GitHubError

from .contracts import ContractError


class Gate1GitHub:
    def __init__(self, runner: CommandRunner, repository_root: Path, repository: str) -> None:
        self.runner = runner
        self.repository_root = repository_root
        self.repository = repository
        self.gh = GhClient(runner, repository_root)

    def preflight(self) -> dict[str, Any]:
        return self.gh.preflight(self.repository)

    def issue(self, issue_number: int) -> dict[str, Any]:
        value = self.gh.api_json(f"repos/{self.repository}/issues/{issue_number}")
        if not isinstance(value, dict) or value.get("number") != issue_number:
            raise ContractError("GitHub issue read-back identity mismatch")
        return value

    def comments(self, issue_number: int) -> list[Any]:
        value = self.gh.api_json(
            f"repos/{self.repository}/issues/{issue_number}/comments?per_page=100",
            paginate=True,
        )
        pages = value if isinstance(value, list) else [value]
        result: list[Any] = []
        for page in pages:
            if not isinstance(page, list):
                raise ContractError("paginated comment endpoint returned non-list page")
            result.extend(page)
        return result

    def comment(self, comment_id: int) -> dict[str, Any]:
        value = self.gh.api_json(
            f"repos/{self.repository}/issues/comments/{comment_id}"
        )
        if not isinstance(value, dict) or value.get("id") != comment_id:
            raise ContractError("comment read-back identity mismatch")
        return value

    def resolve_target_sha(self, job: Any) -> str:
        if job.target_type == "commit":
            value = self.gh.api_json(
                f"repos/{self.repository}/commits/{job.target_sha}"
            )
            sha = value.get("sha") if isinstance(value, dict) else None
        elif job.target_type == "pull_request" and isinstance(job.target_number, int):
            value = self.gh.api_json(
                f"repos/{self.repository}/pulls/{job.target_number}"
            )
            head = value.get("head") if isinstance(value, dict) else None
            sha = head.get("sha") if isinstance(head, dict) else None
        else:
            raise ContractError("unsupported Gate 1 target binding")
        if not isinstance(sha, str):
            raise ContractError("target SHA could not be resolved")
        return sha

    def permission(self, login: str) -> str:
        value = self.gh.api_json(
            f"repos/{self.repository}/collaborators/{login}/permission"
        )
        permission = value.get("permission") if isinstance(value, dict) else None
        if permission not in {"admin", "maintain", "write", "triage", "read"}:
            raise ContractError("GitHub permission could not be established")
        return permission

    def publish_authority_comment(self, issue_number: int, body: str) -> dict[str, Any]:
        if not isinstance(body, str) or not body or len(body.encode("utf-8")) > 58_000:
            raise ContractError("Gate 1 comment is empty or exceeds publication budget")
        endpoint = f"repos/{self.repository}/issues/{issue_number}/comments"
        record = self.runner.run(
            [
                "gh", "api",
                "-H", "X-GitHub-Api-Version: 2022-11-28",
                "--method", "POST",
                endpoint,
                "-f", f"body={body}",
            ],
            cwd=self.repository_root,
            timeout_seconds=60,
        )
        if record.return_code != 0 or record.timed_out:
            raise GitHubError("Gate 1 authority comment POST was not confirmed")
        try:
            posted = json.loads(record.stdout)
        except json.JSONDecodeError as exc:
            raise GitHubError("Gate 1 POST response was not JSON") from exc
        comment_id = posted.get("id") if isinstance(posted, dict) else None
        if not isinstance(comment_id, int):
            raise GitHubError("Gate 1 POST response omitted comment id")
        reread = self.comment(comment_id)
        if reread.get("body") != body:
            raise GitHubError("Gate 1 comment exact read-back failed")
        return redact_value(reread)
