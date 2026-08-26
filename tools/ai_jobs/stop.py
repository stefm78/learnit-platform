"""Gate 1 optional stop boundary."""
from __future__ import annotations

from pathlib import Path

from tools.codespace_evidence.execute import CommandRunner
from tools.codespace_evidence.stop import stop_current_codespace

from .contracts import ContractError, SessionGrant


def stop_after_closed(
    *,
    runner: CommandRunner,
    repository_root: Path,
    grant: SessionGrant,
    state: str,
) -> dict:
    if state != "CLOSED":
        raise ContractError("Codespace stop is forbidden before durable CLOSED state")
    return stop_current_codespace(
        runner,
        repository_root=repository_root,
        repository=grant.repository,
        publication_verified=True,
    )
