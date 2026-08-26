"""Stable deterministic snapshots over already-normalized GitHub comment data."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Callable, Iterable

from . import MAX_CHUNK_BYTES, MAX_COMMENTS_PER_ISSUE, MAX_SNAPSHOT_BYTES
from .contracts import (
    ContractError,
    FrozenDict,
    canonical_json_bytes,
    exact_int,
    freeze_json,
    iso_utc,
    validate_global_bounds,
)


@dataclass(frozen=True)
class StableSnapshot:
    comments: tuple[FrozenDict, ...]
    digest_sha256: str
    size_bytes: int
    cutoff_comment_id: int


def _normalize(comments: Iterable[Any]) -> tuple[FrozenDict, ...]:
    material = list(comments)
    exact_int(
        len(material),
        "comment_count",
        minimum=0,
        maximum=MAX_COMMENTS_PER_ISSUE,
    )

    normalized: list[FrozenDict] = []
    seen: set[int] = set()
    max_chunk_size = 0
    for raw in material:
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

        exact_int(user_id, "github.comment.user.id", minimum=1)
        if not isinstance(user_node_id, str) or not user_node_id:
            raise ContractError("GitHub comment user node_id is unavailable")

        body_size = len(body.encode("utf-8"))
        exact_int(
            body_size,
            "github.comment.body_size_bytes",
            minimum=0,
            maximum=MAX_CHUNK_BYTES,
        )
        max_chunk_size = max(max_chunk_size, body_size)

        created_at = iso_utc(
            raw.get("created_at"), "github.comment.created_at"
        )
        updated_at = iso_utc(
            raw.get("updated_at"), "github.comment.updated_at"
        )
        html_url = raw.get("html_url")
        issue_url = raw.get("issue_url")
        if not isinstance(html_url, str) or not isinstance(issue_url, str):
            raise ContractError("GitHub comment canonical URLs are unavailable")

        frozen = freeze_json({
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
        if not isinstance(frozen, FrozenDict):
            raise AssertionError("comment normalization did not produce an object")
        seen.add(comment_id)
        normalized.append(frozen)

    # Order is part of the snapshot contract; pagination order is not trusted.
    ordered = tuple(sorted(normalized, key=lambda item: item["id"]))

    # Execute the R5 metrics that are knowable at this single-issue layer.
    validate_global_bounds(
        generation=0,
        issue_count=1,
        comment_count=len(ordered),
        ledger_count=0,
        record_count=0,
        snapshot_size_bytes=0,
        max_chunk_size_bytes=max_chunk_size,
    )
    return ordered


def stable_double_scan(fetch: Callable[[], list[Any]]) -> StableSnapshot:
    """Require two byte-identical normalized scans before using a snapshot."""
    first = _normalize(fetch())
    second = _normalize(fetch())
    first_bytes = canonical_json_bytes(first)
    second_bytes = canonical_json_bytes(second)
    if first_bytes != second_bytes:
        raise ContractError("GitHub snapshot changed between required scans")

    size = len(first_bytes)
    exact_int(
        size,
        "snapshot_size_bytes",
        minimum=0,
        maximum=MAX_SNAPSHOT_BYTES,
    )
    validate_global_bounds(
        generation=0,
        issue_count=1,
        comment_count=len(first),
        ledger_count=0,
        record_count=0,
        snapshot_size_bytes=size,
        max_chunk_size_bytes=max(
            (len(item["body"].encode("utf-8")) for item in first),
            default=0,
        ),
    )
    return StableSnapshot(
        comments=first,
        digest_sha256=hashlib.sha256(first_bytes).hexdigest(),
        size_bytes=size,
        cutoff_comment_id=max(
            (item["id"] for item in first),
            default=0,
        ),
    )
