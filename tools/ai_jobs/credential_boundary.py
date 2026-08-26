"""Credential/effect-boundary guards immediately before Gate 0 invocation."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import platform
import tempfile
from typing import Any, BinaryIO

from .contracts import (
    ContractError,
    QueueJob,
    SHA_RE,
    SessionGrant,
    exact_int,
    iso_utc,
)


@dataclass
class SessionProcessFence:
    """Held file descriptor for same-Codespace Gate 1 exclusivity."""

    handle: BinaryIO
    path: Path

    def close(self) -> None:
        if not self.handle.closed:
            self.handle.close()


def acquire_session_process_fence(grant: SessionGrant) -> SessionProcessFence:
    """Acquire a non-blocking fence for the whole authority in this Codespace."""
    if platform.system() != "Linux":
        raise ContractError("Gate 1 process fencing requires the Linux Codespace runtime")
    try:
        import fcntl
    except ImportError as exc:  # pragma: no cover - Linux Codespaces provide fcntl
        raise ContractError("Gate 1 process fencing requires fcntl") from exc

    material = (
        f"{grant.repository}|{grant.authority_issue}|{grant.codespace_name}"
    ).encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    path = Path(tempfile.gettempdir()) / f"learnit-gate1-authority-{digest}.lock"
    handle = path.open("a+b")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise ContractError(
            "another Gate 1 coordinator process already holds this authority fence"
        ) from exc
    except OSError as exc:
        handle.close()
        raise ContractError(f"Gate 1 process fence failed: {exc}") from exc
    return SessionProcessFence(handle=handle, path=path)


def require_runtime_identity(
    *,
    preflight: dict[str, Any],
    grant: SessionGrant,
    codespace_name: str | None = None,
) -> str:
    login = preflight.get("authenticated_login")
    if not isinstance(login, str) or not login:
        raise ContractError("authenticated GitHub identity is unavailable")
    if login != grant.granted_by:
        raise ContractError("authenticated GitHub identity differs from the human session grant")
    if preflight.get("authenticated_host") != "github.com":
        raise ContractError("Gate 1 authenticated host differs from canonical github.com")
    if preflight.get("checkout_repository") != grant.repository:
        raise ContractError("Gate 1 checkout repository differs from the human session grant")
    if preflight.get("raw_r5_readback") is not True:
        raise ContractError("Gate 1 raw R5 GitHub read-back is not active")

    observed_codespace = os.environ.get("CODESPACE_NAME")
    if not isinstance(observed_codespace, str) or not observed_codespace:
        raise ContractError("Gate 1 must run inside the human-started GitHub Codespace")
    if codespace_name is not None and codespace_name != observed_codespace:
        raise ContractError("explicit Codespace assertion differs from the runtime environment")
    if observed_codespace != grant.codespace_name:
        raise ContractError("Codespace identity differs from the human grant")
    return login


def require_request_authority(permission: str) -> None:
    if permission not in {"write", "maintain", "admin"}:
        raise ContractError("request author lacks Gate 1 execution authority")


def _validate_effect_comment(job: QueueJob, request_comment: dict[str, Any]) -> None:
    """Bind the final observation to the exact GitHub origin and real author."""
    if not isinstance(request_comment, dict):
        raise ContractError("source request comment is unavailable at the effect boundary")
    if exact_int(request_comment.get("id"), "request_comment.id", minimum=1) != job.request_comment_id:
        raise ContractError("source request comment identity moved")

    expected_issue_url = (
        f"https://api.github.com/repos/{job.repository}/issues/{job.origin_number}"
    )
    if request_comment.get("issue_url") != expected_issue_url:
        raise ContractError("source request comment origin moved")
    html_url = request_comment.get("html_url")
    expected_html_prefix = f"https://github.com/{job.repository}/"
    if not isinstance(html_url, str) or not html_url.startswith(expected_html_prefix):
        raise ContractError("source request comment canonical repository moved")

    body = request_comment.get("body")
    if not isinstance(body, str):
        raise ContractError("source request comment disappeared")

    created_at = iso_utc(request_comment.get("created_at"), "request_comment.created_at")
    updated_at = iso_utc(request_comment.get("updated_at"), "request_comment.updated_at")
    if created_at != updated_at:
        raise ContractError("source request comment was edited")
    if created_at != job.created_at:
        raise ContractError("source request comment timestamp differs from selected job identity")

    user = request_comment.get("user")
    if not isinstance(user, dict):
        raise ContractError("source request comment author is unavailable")
    exact_int(user.get("id"), "request_comment.user.id", minimum=1)
    if user.get("login") != job.request_author:
        raise ContractError("source request comment author differs from selected job identity")
    if not isinstance(user.get("node_id"), str) or not user["node_id"]:
        raise ContractError("source request comment author node_id is unavailable")


def final_effect_guard(
    *,
    job: QueueJob,
    request_comment: dict[str, Any],
    current_target_sha: str,
    permission: str,
    suspended: bool,
) -> None:
    """Revalidate every mutable authority immediately at the effect boundary."""
    if suspended:
        raise ContractError("Gate 1 is suspended at the invocation boundary")
    require_request_authority(permission)
    _validate_effect_comment(job, request_comment)

    if not isinstance(job.target_sha, str) or SHA_RE.fullmatch(job.target_sha) is None:
        raise ContractError("selected target SHA is not an exact lowercase SHA")
    if not isinstance(current_target_sha, str) or SHA_RE.fullmatch(current_target_sha) is None:
        raise ContractError("current target SHA is not an exact lowercase SHA")
    if current_target_sha != job.target_sha:
        raise ContractError("target SHA moved before Gate 0 invocation")
