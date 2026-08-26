"""Credential-free stop authorization semantics for Gate 1.

This module is data-only. It decides whether a privileged outer boundary may
request a Codespace stop, but it never performs the external effect itself.
"""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import ContractError, SessionGrant


@dataclass(frozen=True)
class StopIntent:
    repository: str
    authority_issue: int
    session_id: str
    generation: int
    codespace_name: str


def stop_after_closed(
    *,
    grant: SessionGrant,
    state: str,
    publication_verified: bool = True,
) -> StopIntent:
    """Authorize, but never execute, stop only after durable publication/close."""
    if type(publication_verified) is not bool or not publication_verified:
        raise ContractError(
            "Codespace stop is forbidden before durable publication is verified"
        )
    if state != "CLOSED":
        raise ContractError(
            "Codespace stop is forbidden before durable CLOSED state"
        )
    return StopIntent(
        repository=grant.repository,
        authority_issue=grant.authority_issue,
        session_id=grant.session_id,
        generation=grant.generation,
        codespace_name=grant.codespace_name,
    )
