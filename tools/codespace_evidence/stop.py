"""Best-effort self-stop after verified durable publication only."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any

from .execute import CommandRunner

CODESPACE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{1,79}$")


class StopError(RuntimeError):
    """Raised when the current Codespace identity is unsafe or ambiguous."""


def _repository_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("nameWithOwner", "fullName", "name"):
            if isinstance(value.get(key), str):
                return value[key]
    return None


def stop_current_codespace(
    runner: CommandRunner,
    *,
    repository_root: Path,
    repository: str,
    publication_verified: bool,
) -> dict[str, Any]:
    if not publication_verified:
        return {"state": "DISABLED_PUBLICATION_NOT_VERIFIED"}
    name = os.environ.get("CODESPACE_NAME", "")
    if not name:
        return {"state": "DISABLED_NO_CODESPACE_NAME"}
    if not CODESPACE_NAME_RE.fullmatch(name):
        return {"state": "DISABLED_AMBIGUOUS_CODESPACE_NAME"}

    listing = runner.run(
        ["gh", "codespace", "list", "--json", "name,repository,state"],
        cwd=repository_root,
        timeout_seconds=60,
    )
    if listing.return_code != 0 or listing.timed_out:
        return {"state": "STOP_FAILED", "reason": "CODESPACE_LIST_FAILED", "command_id": listing.id}
    try:
        entries = json.loads(listing.stdout)
    except json.JSONDecodeError:
        return {"state": "STOP_FAILED", "reason": "CODESPACE_LIST_INVALID_JSON", "command_id": listing.id}
    if not isinstance(entries, list):
        return {"state": "STOP_FAILED", "reason": "CODESPACE_LIST_INVALID_SHAPE", "command_id": listing.id}

    matches = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("name") != name:
            continue
        repo = _repository_name(entry.get("repository"))
        if repo == repository:
            matches.append(entry)
    if len(matches) != 1:
        return {
            "state": "DISABLED_IDENTITY_NOT_EXACT",
            "codespace_name": name,
            "matching_entries": len(matches),
        }

    stop = runner.run(
        ["gh", "codespace", "stop", "-c", name],
        cwd=repository_root,
        timeout_seconds=120,
    )
    if stop.return_code != 0 or stop.timed_out:
        return {"state": "STOP_FAILED", "codespace_name": name, "command_id": stop.id}
    return {"state": "STOP_REQUESTED", "codespace_name": name, "command_id": stop.id}
