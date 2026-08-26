"""Stable GitHub snapshot construction for Gate 1."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Callable

from . import MAX_COMMENTS_PER_ISSUE, MAX_SNAPSHOT_BYTES
from .contracts import ContractError, canonical_json_bytes


@dataclass(frozen=True)
class StableSnapshot:
    comments: tuple[dict[str, Any], ...]
    digest_sha256: str
    size_bytes: int
    cutoff_comment_id: int


def _normalize(comments: list[Any]) -> tuple[dict[str, Any], ...]:
    if len(comments) > MAX_COMMENTS_PER_ISSUE:
        raise ContractError("comment count exceeds global Gate 1 bound")
    normalized: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in comments:
        if not isinstance(raw, dict):
            raise ContractError("GitHub comment page contains a non-object")
        comment_id = raw.get("id")
        body = raw.get("body")
        user = raw.get("user")
        login = user.get("login") if isinstance(user, dict) else None
        if not isinstance(comment_id, int) or comment_id < 1 or comment_id in seen:
            raise ContractError("GitHub comments contain invalid or duplicate ids")
        if not isinstance(body, str) or not isinstance(login, str) or not login:
            raise ContractError("GitHub comment is missing normative fields")
        created_at = raw.get("created_at")
        updated_at = raw.get("updated_at")
        if not isinstance(created_at, str) or not isinstance(updated_at, str):
            raise ContractError("GitHub comment timestamps are unavailable")
        seen.add(comment_id)
        normalized.append({
            "id": comment_id,
            "body": body,
            "author": login,
            "created_at": created_at,
            "updated_at": updated_at,
            "html_url": raw.get("html_url"),
            "issue_url": raw.get("issue_url"),
        })
    return tuple(sorted(normalized, key=lambda item: item["id"]))


def stable_double_scan(fetch: Callable[[], list[Any]]) -> StableSnapshot:
    first = _normalize(fetch())
    second = _normalize(fetch())
    first_bytes = canonical_json_bytes(list(first))
    second_bytes = canonical_json_bytes(list(second))
    if first_bytes != second_bytes:
        raise ContractError("GitHub snapshot changed between required scans")
    if len(first_bytes) > MAX_SNAPSHOT_BYTES:
        raise ContractError("snapshot exceeds global Gate 1 byte bound")
    return StableSnapshot(
        comments=first,
        digest_sha256=hashlib.sha256(first_bytes).hexdigest(),
        size_bytes=len(first_bytes),
        cutoff_comment_id=max((item["id"] for item in first), default=0),
    )
