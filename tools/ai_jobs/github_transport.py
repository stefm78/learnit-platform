"""Closed privileged GitHub transport for the Gate 1 EFFECT_GATEWAY.

Only the fixed GitHub observations required by Gate 1 and same-authority issue
comment publication are exposed.  The transport owns the authenticated ``gh``
subprocess boundary, pins github.com, uses ``shell=False``, and never accepts a
caller supplied argv, method, host, or arbitrary API route.

Every normative GET is consumed as a raw HTTP envelope.  R5 lexical header
checks are completed before JSON interpretation.  A publication is attempted
once and is authoritative only after a durable exact read-back/reconciliation;
an ambiguous effect hard-fences further mutation in the current gateway.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

from tools.codespace_evidence.execute import (
    CommandRunner,
    redact_text,
    safe_environment,
)
from tools.codespace_evidence.github import GitHubError

from . import MAX_CHUNK_BYTES, MAX_COMMENTS_PER_ISSUE
from .contracts import (
    ContractError,
    SHA_RE,
    canonical_json_bytes,
    exact_int,
    iso_utc,
)

REQUEST_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)*$",
    re.ASCII,
)
CONTENT_LENGTH_RE = re.compile(r"^[0-9]+$", re.ASCII)
HTTP_STATUS_RE = re.compile(r"^HTTP/[^ ]+ ([0-9]{3})(?: .*)?$", re.ASCII)
GITHUB_LOGIN_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}[A-Za-z0-9])?(?:\[bot\])?$",
    re.ASCII,
)

_API_VERSION = "2022-11-28"
_ACCEPT = "application/vnd.github+json"
_GITHUB_HOST = "github.com"


def validate_r5_readback_envelope(
    *,
    status: Any,
    headers: Mapping[str, Any],
    body: bytes,
    expected_body_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate the exact R5 lexical controls before body interpretation.

    R5 requires HTTP 200, a non-empty ASCII segmented
    ``x-github-request-id`` and lexical decimal-ASCII ``content-length``.
    Zero-padded decimal length is valid when its integer value equals the exact
    decoded body length.
    """
    code = exact_int(status, "github.status", minimum=100, maximum=599)
    if code != 200:
        raise ContractError(f"GitHub read-back HTTP status is not 200: {code}")
    if not isinstance(headers, Mapping):
        raise ContractError("GitHub read-back headers are unavailable")
    if not isinstance(body, bytes):
        raise ContractError("GitHub read-back body must be exact bytes")

    lowered: dict[str, str] = {}
    for raw_name, raw_value in headers.items():
        if not isinstance(raw_name, str) or not isinstance(raw_value, str):
            raise ContractError("GitHub read-back header name/value must be text")
        try:
            raw_name.encode("ascii")
            raw_value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ContractError("GitHub read-back selected headers must be ASCII") from exc
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


def _split_http_envelope(raw: bytes) -> tuple[int, dict[str, str], bytes]:
    """Split one ``gh api --include`` response without normalizing body bytes."""
    if not isinstance(raw, bytes) or not raw:
        raise ContractError("GitHub raw read-back is empty")

    crlf_index = raw.find(b"\r\n\r\n")
    lf_index = raw.find(b"\n\n")
    candidates = [
        (index, sep)
        for index, sep in ((crlf_index, b"\r\n\r\n"), (lf_index, b"\n\n"))
        if index >= 0
    ]
    if not candidates:
        raise ContractError("GitHub raw read-back omitted the HTTP header boundary")
    index, separator = min(candidates, key=lambda item: item[0])
    header_bytes = raw[:index]
    body = raw[index + len(separator) :]
    try:
        header_text = header_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ContractError("GitHub raw read-back headers are not ASCII") from exc

    lines = header_text.replace("\r\n", "\n").split("\n")
    if not lines or HTTP_STATUS_RE.fullmatch(lines[0]) is None:
        raise ContractError("GitHub raw read-back status line is invalid")
    status_match = HTTP_STATUS_RE.fullmatch(lines[0])
    assert status_match is not None
    status = int(status_match.group(1), 10)

    selected: dict[str, str] = {}
    for line in lines[1:]:
        if not line:
            continue
        if line[:1] in {" ", "\t"} or ":" not in line:
            raise ContractError("GitHub raw read-back contains an invalid header line")
        raw_name, raw_value = line.split(":", 1)
        try:
            raw_name.encode("ascii")
            raw_value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ContractError("GitHub raw read-back contains a non-ASCII header") from exc
        name = raw_name.lower()
        # HTTP field syntax conventionally emits one SP after ':'.  Remove
        # exactly that delimiter SP; any additional leading/trailing space is
        # part of the selected lexical value and is rejected by the R5 grammar.
        value = raw_value[1:] if raw_value.startswith(" ") else raw_value
        if name in {"x-github-request-id", "content-length"}:
            if name in selected:
                raise ContractError(f"duplicate GitHub read-back selected header: {name}")
            selected[name] = value

    if body.startswith(b"HTTP/"):
        raise ContractError("multiple HTTP envelopes are not accepted at the Gate 1 boundary")
    return status, selected, body


def _loads_api_json(body: bytes, label: str) -> Any:
    try:
        text = body.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{label} is not valid UTF-8 JSON") from exc

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContractError(f"{label} contains duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ContractError(f"{label} contains invalid JSON constant: {value}")
            ),
        )
    except ContractError:
        raise
    except json.JSONDecodeError as exc:
        raise ContractError(f"{label} did not return valid JSON: {exc}") from exc


def _github_login(value: Any, label: str) -> str:
    if not isinstance(value, str) or GITHUB_LOGIN_RE.fullmatch(value) is None:
        raise ContractError(f"{label} is not a canonical GitHub login")
    return value


def _comment_object(
    value: Any,
    *,
    repository: str,
    issue_number: int | None = None,
) -> dict[str, Any]:
    """Normalize a GitHub issue comment to the closed Gate 1 field set."""
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
    expected_html_prefixes = (
        f"https://github.com/{repository}/issues/",
        f"https://github.com/{repository}/pull/",
    )
    if not isinstance(html_url, str) or not html_url.startswith(expected_html_prefixes):
        raise ContractError("GitHub comment html_url differs from the canonical repository")
    expected_issue_prefix = f"https://api.github.com/repos/{repository}/issues/"
    if not isinstance(issue_url, str) or not issue_url.startswith(expected_issue_prefix):
        raise ContractError("GitHub comment issue_url differs from the canonical repository")
    if issue_number is not None and issue_url != f"{expected_issue_prefix}{issue_number}":
        raise ContractError("GitHub comment belongs to another issue")
    if not isinstance(user, dict):
        raise ContractError("GitHub comment user is unavailable")
    user_id = exact_int(user.get("id"), "github.comment.user.id", minimum=1)
    user_login = _github_login(user.get("login"), "github.comment.user.login")
    user_node_id = user.get("node_id")
    if not isinstance(user_node_id, str) or not user_node_id:
        raise ContractError("GitHub comment user node_id is unavailable")

    # Do not leak the broad GitHub object into core/reconciler code.  Only the
    # exact normalized fields used by Gate 1 cross the EFFECT_GATEWAY boundary.
    return {
        "id": comment_id,
        "node_id": node_id,
        "body": body,
        "html_url": html_url,
        "issue_url": issue_url,
        "created_at": created_at,
        "updated_at": updated_at,
        "user": {
            "id": user_id,
            "login": user_login,
            "node_id": user_node_id,
        },
    }


class _ClosedGhTransport:
    """Private fixed-command carrier; no caller-controlled argv is exposed."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        executable = shutil.which("gh")
        if executable is None:
            raise GitHubError("gh executable absent")
        self.gh_executable = Path(executable).resolve()
        try:
            self.gh_executable.relative_to(self.repository_root)
        except ValueError:
            pass
        else:
            raise GitHubError("refusing a workspace-provided gh executable")

    def _environment(self) -> dict[str, str]:
        host = os.environ.get("GH_HOST")
        if host and host != _GITHUB_HOST:
            raise GitHubError("GH_HOST differs from canonical github.com")
        return safe_environment(
            {
                "GH_PAGER": "cat",
                "PAGER": "cat",
                "NO_COLOR": "1",
            },
            include_github_auth=True,
        )

    def _get(self, endpoint: str, *, timeout: int = 120) -> bytes:
        if (
            not isinstance(endpoint, str)
            or not endpoint
            or endpoint.startswith(("http://", "https://"))
            or any(char in endpoint for char in "\r\n\x00")
        ):
            raise ContractError("GitHub GET endpoint is outside the closed route form")
        argv = [
            str(self.gh_executable),
            "api",
            "--hostname",
            _GITHUB_HOST,
            "--include",
            "--method",
            "GET",
            "-H",
            f"Accept: {_ACCEPT}",
            "-H",
            f"X-GitHub-Api-Version: {_API_VERSION}",
            endpoint,
        ]
        try:
            completed = subprocess.run(
                argv,
                cwd=str(self.repository_root),
                env=self._environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitHubError("GitHub GET timed out") from exc
        except OSError as exc:
            raise GitHubError("GitHub GET could not start") from exc
        if completed.returncode != 0:
            detail = redact_text(completed.stderr.decode("utf-8", "replace"))[:1024]
            raise GitHubError(f"GitHub GET failed: {detail}")
        status, headers, body = _split_http_envelope(completed.stdout)
        validate_r5_readback_envelope(status=status, headers=headers, body=body)
        return body

    def get_json(self, endpoint: str, *, timeout: int = 120) -> Any:
        return _loads_api_json(self._get(endpoint, timeout=timeout), endpoint)

    def post_issue_comment_once(
        self,
        *,
        endpoint: str,
        body: str,
        timeout: int = 120,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Attempt exactly one POST; returned JSON is a hint, never authority."""
        if not endpoint.startswith("repos/") or not endpoint.endswith("/comments"):
            raise ContractError("GitHub mutation endpoint is outside the comment allowlist")
        payload_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                suffix=".json",
                prefix="learnit-gate1-effect-",
                delete=False,
            ) as handle:
                os.chmod(handle.name, 0o600)
                json.dump({"body": body}, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
                payload_path = Path(handle.name)
            argv = [
                str(self.gh_executable),
                "api",
                "--hostname",
                _GITHUB_HOST,
                "--method",
                "POST",
                "-H",
                f"Accept: {_ACCEPT}",
                "-H",
                f"X-GitHub-Api-Version: {_API_VERSION}",
                endpoint,
                "--input",
                str(payload_path),
            ]
            try:
                completed = subprocess.run(
                    argv,
                    cwd=str(self.repository_root),
                    env=self._environment(),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                    check=False,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return None, "POST_TIMEOUT_EFFECT_UNKNOWN"
            except OSError:
                return None, "POST_START_FAILURE_EFFECT_UNKNOWN"
            if completed.returncode != 0:
                # Conservatively classify as unknown: the remote effect may
                # have committed before the local CLI observed its failure.
                return None, "POST_NONZERO_EFFECT_UNKNOWN"
            try:
                value = _loads_api_json(completed.stdout, "GitHub comment POST response")
            except ContractError:
                return None, "POST_RESPONSE_INVALID_EFFECT_UNKNOWN"
            return value if isinstance(value, dict) else None, None
        finally:
            if payload_path is not None:
                payload_path.unlink(missing_ok=True)

    def version(self) -> str:
        try:
            completed = subprocess.run(
                [str(self.gh_executable), "--version"],
                cwd=str(self.repository_root),
                env=self._environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitHubError("gh version probe failed") from exc
        if completed.returncode != 0:
            raise GitHubError("gh version probe failed")
        lines = completed.stdout.decode("utf-8", "replace").strip().splitlines()
        return lines[0] if lines else ""


def _checkout_repository(repository_root: Path) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise GitHubError("git executable absent")
    git_executable = Path(executable).resolve()
    try:
        git_executable.relative_to(repository_root.resolve())
    except ValueError:
        pass
    else:
        raise GitHubError("refusing a workspace-provided git executable")

    with tempfile.TemporaryDirectory(prefix="learnit-gate1-git-") as tmp:
        env = safe_environment(
            {},
            include_github_auth=False,
            isolated_config_root=Path(tmp),
        )
        completed = subprocess.run(
            [str(git_executable), "remote", "get-url", "origin"],
            cwd=str(repository_root),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False,
            timeout=30,
        )
    if completed.returncode != 0:
        raise GitHubError("checkout origin remote could not be established")
    remote = completed.stdout.decode("utf-8", "strict").strip()
    patterns = (
        re.compile(r"^https://github\.com/([^/]+/[^/]+?)(?:\.git)?$"),
        re.compile(r"^git@github\.com:([^/]+/[^/]+?)(?:\.git)?$"),
        re.compile(r"^ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?$"),
    )
    for pattern in patterns:
        match = pattern.fullmatch(remote)
        if match:
            return match.group(1)
    raise GitHubError("checkout origin is not the canonical github.com repository form")


class Gate1GitHub:
    """Privileged EFFECT_GATEWAY-side GitHub facade with a closed surface."""

    def __init__(self, runner: CommandRunner, repository_root: Path, repository: str) -> None:
        # ``runner`` remains in the constructor for the parent integration API,
        # but the gateway intentionally does not retain or expose it.  All
        # privileged GitHub execution is owned by the fixed private carrier.
        _ = runner
        if not isinstance(repository, str) or repository.count("/") != 1:
            raise ContractError("Gate 1 repository must use owner/name")
        owner, name = repository.split("/", 1)
        if not owner or not name or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-" for char in owner + name):
            raise ContractError("Gate 1 repository contains invalid characters")
        self.repository_root = repository_root.resolve()
        self.repository = repository
        self._transport = _ClosedGhTransport(self.repository_root)
        self._authenticated_login: str | None = None
        self._ambiguous_effect = False

    def _get_json(self, endpoint: str, *, timeout: int = 120) -> Any:
        return self._transport.get_json(endpoint, timeout=timeout)

    def preflight(self) -> dict[str, Any]:
        checkout_repository = _checkout_repository(self.repository_root)
        if checkout_repository != self.repository:
            raise GitHubError(
                f"requested repository {self.repository} differs from current checkout {checkout_repository}"
            )

        user = self._get_json("user", timeout=60)
        if not isinstance(user, dict):
            raise GitHubError("authenticated GitHub identity response is invalid")
        login = _github_login(user.get("login"), "authenticated GitHub login")
        exact_int(user.get("id"), "authenticated GitHub user id", minimum=1)
        if not isinstance(user.get("node_id"), str) or not user["node_id"]:
            raise GitHubError("authenticated GitHub user node_id is unavailable")

        repo = self._get_json(f"repos/{self.repository}", timeout=60)
        if not isinstance(repo, dict) or repo.get("full_name") != self.repository:
            raise GitHubError("authenticated GitHub context resolved a different repository")
        exact_int(repo.get("id"), "github.repository.id", minimum=1)
        if not isinstance(repo.get("node_id"), str) or not repo["node_id"]:
            raise GitHubError("GitHub repository node_id is unavailable")
        private = repo.get("private")
        if not isinstance(private, bool):
            raise GitHubError("GitHub repository privacy state is unavailable")
        html_url = repo.get("html_url")
        default_branch = repo.get("default_branch")
        if html_url != f"https://github.com/{self.repository}":
            raise GitHubError("GitHub repository canonical URL mismatch")
        if not isinstance(default_branch, str) or not default_branch:
            raise GitHubError("GitHub repository default branch is unavailable")

        self._authenticated_login = login
        return {
            "gh_version": self._transport.version(),
            "authenticated_host": _GITHUB_HOST,
            "authenticated_login": login,
            "checkout_repository": checkout_repository,
            "repository": {
                "nameWithOwner": self.repository,
                "isPrivate": private,
                "url": html_url,
                "defaultBranchRef": {"name": default_branch},
            },
            "credential_capabilities": "not inferred from token scope",
            "bridge_exposed_mutations": ["same-origin issue conversation comment creation"],
            "raw_r5_readback": True,
        }

    def issue(self, issue_number: int) -> dict[str, Any]:
        issue_number = exact_int(issue_number, "issue_number", minimum=1)
        value = self._get_json(f"repos/{self.repository}/issues/{issue_number}")
        if not isinstance(value, dict):
            raise ContractError("GitHub issue read-back is not an object")
        if exact_int(value.get("number"), "github.issue.number", minimum=1) != issue_number:
            raise ContractError("GitHub issue read-back identity mismatch")
        issue_id = exact_int(value.get("id"), "github.issue.id", minimum=1)
        node_id = value.get("node_id")
        state = value.get("state")
        html_url = value.get("html_url")
        if not isinstance(node_id, str) or not node_id:
            raise ContractError("GitHub issue node_id is unavailable")
        if state not in {"open", "closed"}:
            raise ContractError("GitHub issue state is unavailable")
        if html_url not in {
            f"https://github.com/{self.repository}/issues/{issue_number}",
            f"https://github.com/{self.repository}/pull/{issue_number}",
        }:
            raise ContractError("GitHub issue canonical URL mismatch")
        return {
            "id": issue_id,
            "node_id": node_id,
            "number": issue_number,
            "state": state,
            "html_url": html_url,
        }

    def comments(self, issue_number: int) -> list[Any]:
        issue_number = exact_int(issue_number, "issue_number", minimum=1)
        result: list[Any] = []
        seen: set[int] = set()
        page = 1
        while True:
            value = self._get_json(
                f"repos/{self.repository}/issues/{issue_number}/comments?per_page=100&page={page}",
                timeout=180,
            )
            if not isinstance(value, list):
                raise ContractError("paginated comment endpoint returned a non-list page")
            for item in value:
                normalized = _comment_object(
                    item,
                    repository=self.repository,
                    issue_number=issue_number,
                )
                if normalized["id"] in seen:
                    raise ContractError("GitHub comment pagination repeated an id")
                seen.add(normalized["id"])
                result.append(normalized)
                if len(result) > MAX_COMMENTS_PER_ISSUE:
                    raise ContractError("comment count exceeds global Gate 1 bound")
            if len(value) < 100:
                break
            page += 1
            if page > (MAX_COMMENTS_PER_ISSUE // 100) + 1:
                raise ContractError("GitHub comment pagination exceeds the canonical bound")
        return result

    def comment(self, comment_id: int) -> dict[str, Any]:
        comment_id = exact_int(comment_id, "comment_id", minimum=1)
        value = self._get_json(f"repos/{self.repository}/issues/comments/{comment_id}")
        normalized = _comment_object(value, repository=self.repository)
        if normalized.get("id") != comment_id:
            raise ContractError("comment read-back identity mismatch")
        return normalized

    def resolve_target_sha(self, job: Any) -> str:
        if job.target_type == "commit":
            value = self._get_json(f"repos/{self.repository}/commits/{job.target_sha}")
            sha = value.get("sha") if isinstance(value, dict) else None
        elif job.target_type == "pull_request" and isinstance(job.target_number, int):
            target_number = exact_int(job.target_number, "target_number", minimum=1)
            value = self._get_json(f"repos/{self.repository}/pulls/{target_number}")
            if not isinstance(value, dict) or exact_int(
                value.get("number"), "github.pull.number", minimum=1
            ) != target_number:
                raise ContractError("pull request target identity mismatch")
            head = value.get("head")
            sha = head.get("sha") if isinstance(head, dict) else None
        else:
            raise ContractError("unsupported Gate 1 target binding")
        if not isinstance(sha, str) or SHA_RE.fullmatch(sha) is None:
            raise ContractError("target SHA could not be resolved as exact lowercase SHA")
        return sha

    def permission(self, login: str) -> str:
        login = _github_login(login, "permission login")
        value = self._get_json(f"repos/{self.repository}/collaborators/{login}/permission")
        permission = value.get("permission") if isinstance(value, dict) else None
        if permission not in {"admin", "maintain", "write", "triage", "read"}:
            raise ContractError("GitHub permission could not be established")
        user = value.get("user") if isinstance(value, dict) else None
        if isinstance(user, dict) and user.get("login") != login:
            raise ContractError("GitHub permission response identity mismatch")
        return permission

    def _stable_comment_scan(self, issue_number: int) -> list[dict[str, Any]]:
        first = self.comments(issue_number)
        second = self.comments(issue_number)
        if canonical_json_bytes(first) != canonical_json_bytes(second):
            raise GitHubError("GitHub publication reconciliation snapshot is unstable")
        return first

    def publish_authority_comment(self, issue_number: int, body: str) -> dict[str, Any]:
        """POST once, then reconcile exact durable authority; never blind-retry."""
        issue_number = exact_int(issue_number, "issue_number", minimum=1)
        if self._ambiguous_effect:
            raise GitHubError("G1_PUBLICATION_UNKNOWN_HOLD: gateway mutation fence is active")
        if not isinstance(body, str) or not body or len(body.encode("utf-8")) > 58_000:
            raise ContractError("Gate 1 comment is empty or exceeds publication budget")
        if not isinstance(self._authenticated_login, str):
            raise ContractError("Gate 1 publication requires successful authenticated preflight")

        before = self._stable_comment_scan(issue_number)
        before_ids = {item["id"] for item in before}
        endpoint = f"repos/{self.repository}/issues/{issue_number}/comments"

        posted_hint, post_error = self._transport.post_issue_comment_once(
            endpoint=endpoint,
            body=body,
        )
        hinted_id = posted_hint.get("id") if isinstance(posted_hint, dict) else None
        if hinted_id is not None and (isinstance(hinted_id, bool) or not isinstance(hinted_id, int)):
            hinted_id = None
            post_error = post_error or "POST_RESPONSE_ID_INVALID_EFFECT_UNKNOWN"

        # Direct read-back is attempted when an ID was returned, but the final
        # decision always comes from a stable bounded scan so concurrent or
        # duplicate effects cannot be hidden by the POST response.
        direct: dict[str, Any] | None = None
        if isinstance(hinted_id, int) and hinted_id > 0:
            try:
                direct = self.comment(hinted_id)
            except Exception:
                direct = None

        try:
            after = self._stable_comment_scan(issue_number)
        except Exception as exc:
            self._ambiguous_effect = True
            raise GitHubError(
                "G1_PUBLICATION_UNKNOWN_HOLD: durable reconciliation unavailable after one POST"
            ) from exc

        expected_issue_url = f"https://api.github.com/repos/{self.repository}/issues/{issue_number}"
        matches = [
            item
            for item in after
            if item["id"] not in before_ids
            and item.get("issue_url") == expected_issue_url
            and item.get("body") == body
            and isinstance(item.get("user"), dict)
            and item["user"].get("login") == self._authenticated_login
        ]

        if len(matches) != 1:
            self._ambiguous_effect = True
            raise GitHubError(
                "G1_PUBLICATION_UNKNOWN_HOLD: one POST did not reconcile to exactly one exact comment"
            )
        authoritative = matches[0]
        if isinstance(hinted_id, int) and authoritative["id"] != hinted_id:
            self._ambiguous_effect = True
            raise GitHubError(
                "G1_PUBLICATION_UNKNOWN_HOLD: POST identity differs from durable reconciliation"
            )
        if direct is not None and direct != authoritative:
            self._ambiguous_effect = True
            raise GitHubError(
                "G1_PUBLICATION_UNKNOWN_HOLD: direct read-back differs from stable reconciliation"
            )
        if post_error is not None and authoritative["id"] in before_ids:
            # Defensive unreachable guard: an ambiguous POST may only recover
            # through a newly observed exact effect.
            self._ambiguous_effect = True
            raise GitHubError("G1_PUBLICATION_UNKNOWN_HOLD: no new durable effect observed")
        return authoritative
