"""Narrow privileged GitHub transport for Gate 1.

Only reads and same-authority issue-comment publication are exposed. Repository
content, refs, workflows, releases, metadata mutation and merge endpoints are
unreachable through this module. The R5 lexical read-back contract is kept here
because EFFECT_GATEWAY is the only component allowed to possess GitHub auth.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from tools.codespace_evidence.execute import CommandRunner, redact_value
from tools.codespace_evidence.github import GhClient, GitHubError

from . import MAX_CHUNK_BYTES
from .contracts import ContractError, SHA_RE, exact_int, iso_utc

REQUEST_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)*$",
    re.ASCII,
)
CONTENT_LENGTH_RE = re.compile(r"^[0-9]+$", re.ASCII)


def validate_r5_readback_envelope(
    *,
    status: Any,
    headers: Mapping[str, Any],
    body: bytes,
    expected_body_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate the exact R5 lexical controls available at EFFECT_GATEWAY.

    R5 requires a successful HTTP read-back before body interpretation, a
    non-empty ASCII segmented ``x-github-request-id`` and lexical decimal ASCII
    ``content-length``. Zero-padded decimal length is intentionally accepted if
    its integer value equals the exact decoded body length.

    The function is deliberately transport-agnostic. A caller that cannot
    provide the raw selected headers must fail closed rather than synthesize
    them from parsed JSON.
    """
    code = exact_int(status, "github.status", minimum=100, maximum=599)
    if code != 200:
        raise ContractError(f"GitHub read-back HTTP status is not 200: {code}")
    if not isinstance(headers, Mapping):
        raise ContractError("GitHub read-back headers are unavailable")

    lowered: dict[str, str] = {}
    for raw_name, raw_value in headers.items():
        if not isinstance(raw_name, str) or not isinstance(raw_value, str):
            raise ContractError("GitHub read-back header name/value must be text")
        name = raw_name.lower()
        if name in lowered:
            raise ContractError(f"duplicate GitHub read-back header: {name}")
        lowered[name] = raw_value

    request_id = lowered.get("x-github-request-id")
    if not isinstance(request_id, str) or REQUEST_ID_RE.fullmatch(request_id) is None:
        raise ContractError("GITHUB_HEADER_INVALID: x-github-request-id")

    content_length = lowered.get("content-length")
    if not isinstance(content_length, str) or CONTENT_LENGTH_RE.fullmatch(content_length) is None:
        raise ContractError("GITHUB_HEADER_INVALID: content-length")
    if int(content_length, 10) != len(body):
        raise ContractError("GitHub content-length differs from exact decoded body length")
    if len(body) > MAX_CHUNK_BYTES:
        raise ContractError("GitHub read-back body exceeds the canonical chunk bound")

    body_sha256 = hashlib.sha256(body).hexdigest()
    if expected_body_sha256 is not None and body_sha256 != expected_body_sha256:
        raise ContractError("GitHub read-back body digest mismatch")

    return {
        "status": code,
        "x-github-request-id": request_id,
        "content-length": content_length,
        "body_sha256": body_sha256,
        "body_length": len(body),
    }


def _comment_object(value: Any, *, repository: str, issue_number: int | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("GitHub comment read-back is not an object")
    comment_id = exact_int(value.get("id"), "github.comment.id", minimum=1)
    node_id = value.get("node_id")
    body = value.get("body")
    html_url = value.get("html_url")
    issue_url = value.get("issue_url")
    created_at = iso_utc(value.get("created_at"), "github.comment.created_at")
    updated_at = iso_utc(value.get("updated_at"), "github.comment.updated_at")
    user = value.get("user")
    if not isinstance(node_id, str) or not node_id:
        raise ContractError("GitHub comment node_id is unavailable")
    if not isinstance(body, str):
        raise ContractError("GitHub comment body is unavailable")
    if len(body.encode("utf-8")) > MAX_CHUNK_BYTES:
        raise ContractError("GitHub comment body exceeds the canonical chunk bound")
    if not isinstance(html_url, str) or not html_url.startswith("https://github.com/"):
        raise ContractError("GitHub comment html_url is unavailable")
    expected_issue_prefix = f"https://api.github.com/repos/{repository}/issues/"
    if not isinstance(issue_url, str) or not issue_url.startswith(expected_issue_prefix):
        raise ContractError("GitHub comment issue_url differs from the canonical repository")
    if issue_number is not None and issue_url != f"{expected_issue_prefix}{issue_number}":
        raise ContractError("GitHub comment belongs to another issue")
    if not isinstance(user, dict):
        raise ContractError("GitHub comment user is unavailable")
    user_id = exact_int(user.get("id"), "github.comment.user.id", minimum=1)
    user_login = user.get("login")
    user_node_id = user.get("node_id")
    if not isinstance(user_login, str) or not user_login:
        raise ContractError("GitHub comment user login is unavailable")
    if not isinstance(user_node_id, str) or not user_node_id:
        raise ContractError("GitHub comment user node_id is unavailable")
    return {
        **value,
        "id": comment_id,
        "node_id": node_id,
        "body": body,
        "html_url": html_url,
        "issue_url": issue_url,
        "created_at": created_at,
        "updated_at": updated_at,
        "user": {
            **user,
            "id": user_id,
            "login": user_login,
            "node_id": user_node_id,
        },
    }


class Gate1GitHub:
    """Privileged EFFECT_GATEWAY-side GitHub facade.

    The current repository bootstrap reuses the accepted Gate 0 ``GhClient``.
    Raw R5 header validation is exposed above and must be applied by the final
    gateway transport before this implementation can claim complete V6 runtime
    conformance; parsed JSON is never used as a substitute for missing headers.
    """

    def __init__(self, runner: CommandRunner, repository_root: Path, repository: str) -> None:
        self.runner = runner
        self.repository_root = repository_root
        self.repository = repository
        self.gh = GhClient(runner, repository_root)

    def preflight(self) -> dict[str, Any]:
        return self.gh.preflight(self.repository)

    def issue(self, issue_number: int) -> dict[str, Any]:
        issue_number = exact_int(issue_number, "issue_number", minimum=1)
        value = self.gh.api_json(f"repos/{self.repository}/issues/{issue_number}")
        if not isinstance(value, dict) or value.get("number") != issue_number:
            raise ContractError("GitHub issue read-back identity mismatch")
        if not isinstance(value.get("node_id"), str) or not value["node_id"]:
            raise ContractError("GitHub issue node_id is unavailable")
        if value.get("state") not in {"open", "closed"}:
            raise ContractError("GitHub issue state is unavailable")
        return value

    def comments(self, issue_number: int) -> list[Any]:
        issue_number = exact_int(issue_number, "issue_number", minimum=1)
        value = self.gh.api_json(
            f"repos/{self.repository}/issues/{issue_number}/comments?per_page=100",
            paginate=True,
        )
        pages = value if isinstance(value, list) else [value]
        result: list[Any] = []
        for page in pages:
            if not isinstance(page, list):
                raise ContractError("paginated comment endpoint returned non-list page")
            result.extend(
                _comment_object(item, repository=self.repository, issue_number=issue_number)
                for item in page
            )
        return result

    def comment(self, comment_id: int) -> dict[str, Any]:
        comment_id = exact_int(comment_id, "comment_id", minimum=1)
        value = self.gh.api_json(f"repos/{self.repository}/issues/comments/{comment_id}")
        normalized = _comment_object(value, repository=self.repository)
        if normalized.get("id") != comment_id:
            raise ContractError("comment read-back identity mismatch")
        return normalized

    def resolve_target_sha(self, job: Any) -> str:
        if job.target_type == "commit":
            value = self.gh.api_json(f"repos/{self.repository}/commits/{job.target_sha}")
            sha = value.get("sha") if isinstance(value, dict) else None
        elif job.target_type == "pull_request" and isinstance(job.target_number, int):
            value = self.gh.api_json(f"repos/{self.repository}/pulls/{job.target_number}")
            head = value.get("head") if isinstance(value, dict) else None
            sha = head.get("sha") if isinstance(head, dict) else None
        else:
            raise ContractError("unsupported Gate 1 target binding")
        if not isinstance(sha, str) or SHA_RE.fullmatch(sha) is None:
            raise ContractError("target SHA could not be resolved as exact lowercase SHA")
        return sha

    def permission(self, login: str) -> str:
        if not isinstance(login, str) or not login:
            raise ContractError("GitHub login is required for permission read-back")
        value = self.gh.api_json(f"repos/{self.repository}/collaborators/{login}/permission")
        permission = value.get("permission") if isinstance(value, dict) else None
        if permission not in {"admin", "maintain", "write", "triage", "read"}:
            raise ContractError("GitHub permission could not be established")
        return permission

    def publish_authority_comment(self, issue_number: int, body: str) -> dict[str, Any]:
        issue_number = exact_int(issue_number, "issue_number", minimum=1)
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
        # POST success is not durable authority. Exact direct read-back is
        # mandatory and is normalized independently of the POST response.
        reread = self.comment(comment_id)
        expected_issue_url = f"https://api.github.com/repos/{self.repository}/issues/{issue_number}"
        if reread.get("issue_url") != expected_issue_url or reread.get("body") != body:
            raise GitHubError("Gate 1 comment exact read-back failed")
        return redact_value(reread)
