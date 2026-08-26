"""Credential and effect-boundary checks immediately before Gate 0 invocation."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import platform
import tempfile
from typing import Any, BinaryIO

from .contracts import ContractError, QueueJob, SessionGrant


@dataclass
class SessionProcessFence:
    """Held file descriptor for same-Codespace single-process execution."""

    handle: BinaryIO
    path: Path

    def close(self) -> None:
        self.handle.close()


def acquire_session_process_fence(grant: SessionGrant) -> SessionProcessFence:
    """Acquire a non-blocking process fence for the exact human grant.

    GitHub remains the durable authority across restart/host loss. This local
    Linux fence only closes the same-Codespace race in which two coordinator
    processes could otherwise publish competing non-terminal records before a
    later GitHub reconstruction detects the conflict.
    """
    if platform.system() != "Linux":
        raise ContractError("Gate 1 process fencing requires the Linux Codespace runtime")
    try:
        import fcntl
    except ImportError as exc:  # pragma: no cover - Linux Codespaces provide fcntl
        raise ContractError("Gate 1 process fencing requires fcntl") from exc

    material = (
        f"{grant.repository}|{grant.authority_issue}|{grant.session_id}|"
        f"{grant.generation}|{grant.codespace_name}"
    ).encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    path = Path(tempfile.gettempdir()) / f"learnit-gate1-{digest}.lock"
    handle = path.open("a+b")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise ContractError(
            "another Gate 1 coordinator process already holds this session fence"
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


def final_effect_guard(
    *,
    job: QueueJob,
    request_comment: dict[str, Any],
    current_target_sha: str,
    permission: str,
    suspended: bool,
) -> None:
    """Revalidate all mutable authority immediately at the effect boundary."""
    if suspended:
        raise ContractError("Gate 1 is suspended at the invocation boundary")
    require_request_authority(permission)
    if request_comment.get("id") != job.request_comment_id:
        raise ContractError("source request comment identity moved")
    if request_comment.get("body") is None:
        raise ContractError("source request comment disappeared")
    if request_comment.get("created_at") != request_comment.get("updated_at"):
        raise ContractError("source request comment was edited")
    if current_target_sha != job.target_sha:
        raise ContractError("target SHA moved before Gate 0 invocation")
