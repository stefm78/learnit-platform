"""Pure deterministic queue election with fail-closed identity semantics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .contracts import ContractError, QueueJob


@dataclass(frozen=True)
class QueueDecision:
    pending: tuple[QueueJob, ...]
    selected: QueueJob | None
    duplicate_job_ids: tuple[str, ...]
    conflicts: tuple[str, ...]


def elect(
    jobs: Iterable[QueueJob],
    *,
    terminal_request_digests: frozenset[str] = frozenset(),
    started_request_digests: frozenset[str] = frozenset(),
) -> QueueDecision:
    """Elect one oldest admissible logical request deterministically.

    Repeated observations of the same logical ``job_id`` with the same request
    digest are idempotent duplicates: exactly the oldest immutable comment is
    retained. Reusing a ``job_id`` with different request content, or reusing a
    request digest under a different ``job_id``, remains a hard conflict.
    """
    job_list = tuple(jobs)

    if not terminal_request_digests.issubset(started_request_digests):
        raise ContractError(
            "terminal request digests must be a subset of started request digests"
        )

    comment_ids = [job.request_comment_id for job in job_list]
    if len(comment_ids) != len(set(comment_ids)):
        raise ContractError(
            "queue contains duplicate request comment identities"
        )

    by_job: dict[str, list[QueueJob]] = {}
    digest_to_job_ids: dict[str, set[str]] = {}
    for job in job_list:
        by_job.setdefault(job.job_id, []).append(job)
        digest_to_job_ids.setdefault(job.request_digest, set()).add(job.job_id)

    duplicate_ids: list[str] = []
    conflicts: list[str] = []
    collapsed: list[QueueJob] = []

    for job_id, group in sorted(by_job.items()):
        digests = {item.request_digest for item in group}
        if len(digests) > 1:
            conflicts.append(job_id)
            continue
        if len(group) > 1:
            duplicate_ids.append(job_id)
        collapsed.append(min(group, key=lambda item: item.order_key))

    if conflicts:
        raise ContractError(
            "queue contains job_id conflicts with different digests: "
            + ",".join(conflicts)
        )

    reused_digests = sorted(
        digest
        for digest, job_ids in digest_to_job_ids.items()
        if len(job_ids) > 1
    )
    if reused_digests:
        raise ContractError(
            "queue contains reused request digest identities: "
            + ",".join(reused_digests)
        )

    pending = tuple(sorted(
        (
            item
            for item in collapsed
            if item.request_digest not in terminal_request_digests
            and item.request_digest not in started_request_digests
        ),
        key=lambda item: item.order_key,
    ))
    return QueueDecision(
        pending=pending,
        selected=pending[0] if pending else None,
        duplicate_job_ids=tuple(duplicate_ids),
        conflicts=(),
    )
