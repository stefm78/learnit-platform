"""Credential and effect-boundary checks immediately before Gate 0 invocation."""
from __future__ import annotations

import os
from typing import Any

from .contracts import ContractError, QueueJob, SessionGrant


def require_runtime_identity(
    *,
    preflight: dict[str, Any],
    grant: SessionGrant,
    codespace_name: str | None = None,
) -> str:
    login = preflight.get("authenticated_login")
    if not isinstance(login, str) or not login:
        raise ContractError("authenticated GitHub identity is unavailable")
    observed_codespace = codespace_name or os.environ.get("CODESPACE_NAME")
    if not isinstance(observed_codespace, str) or observed_codespace != grant.codespace_name:
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
