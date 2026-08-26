"""Stable GitHub snapshot construction for Gate 1."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Callable

from . import MAX_CHUNK_BYTES, MAX_COMMENTS_PER_ISSUE, MAX_SNAPSHOT_BYTES
from .contracts import ContractError, canonical_json_bytes, exact_int, iso_utc


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
        comment_id = exact_int(raw.get("id"), "github.comment.id", minimum=1)
        node_id = raw.get("node_id")
        body = raw.get("body")
        user = raw.get("user")
        login = user.get("login") if isinstance(user, dict) else None
        user_id = user.get("id") if isinstance(user, dict) else None
        user_node_id = user.get("node_id") if isinstance(user, dict) else None
        if comment_id in seen:
            raise ContractError("GitHub comments contain duplicate ids")
        if not isinstance(node_id, str) or not node_id:
            raise ContractError("GitHub comment node_id is unavailable")
        if not isinstance(body, str) or not isinstance(login, str) or not login:
            raise ContractError("GitHub comment is missing normative fields")
        user_id = exact_int(user_id, "github.comment.user.id", minimum=1)
        if not isinstance(user_node_id, str) or not user_node_id:
            raise ContractError("GitHub comment user node_id is unavailable")
        if len(body.encode("utf-8")) > MAX_CHUNK_BYTES:
            raise ContractError("GitHub comment exceeds the canonical Gate 1 chunk bound")
        created_at = iso_utc(raw.get("created_at"), "github.comment.created_at")
        updated_at = iso_utc(raw.get("updated_at"), "github.comment.updated_at")
        html_url = raw.get("html_url")
        issue_url = raw.get("issue_url")
        if not isinstance(html_url, str) or not isinstance(issue_url, str):
            raise ContractError("GitHub comment canonical URLs are unavailable")
        seen.add(comment_id)
        normalized.append({
            "id": comment_id,
            "node_id": node_id,
            "body": body,
            "author": login,
            "author_id": user_id,
            "author_node_id": user_node_id,
            "created_at": created_at,
            "updated_at": updated_at,
            "html_url": html_url,
            "issue_url": issue_url,
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
