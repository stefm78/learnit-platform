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
    """Elect exactly one oldest admissible request by immutable comment identity."""
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
    by_digest: dict[str, list[QueueJob]] = {}
    for job in job_list:
        by_job.setdefault(job.job_id, []).append(job)
        by_digest.setdefault(job.request_digest, []).append(job)

    duplicate_ids: list[str] = []
    conflicts: list[str] = []
    for job_id, group in sorted(by_job.items()):
        if len(group) <= 1:
            continue
        duplicate_ids.append(job_id)
        digests = {item.request_digest for item in group}
        if len(digests) > 1:
            conflicts.append(job_id)

    reused_digests = sorted(
        digest
        for digest, group in by_digest.items()
        if len(group) > 1
    )

    if conflicts:
        raise ContractError(
            "queue contains job_id conflicts with different digests: "
            + ",".join(conflicts)
        )
    if duplicate_ids:
        raise ContractError(
            "queue contains duplicate/reused job_id identities: "
            + ",".join(duplicate_ids)
        )
    if reused_digests:
        raise ContractError(
            "queue contains reused request digest identities: "
            + ",".join(reused_digests)
        )

    pending = tuple(sorted(
        (
            item
            for item in job_list
            if item.request_digest not in terminal_request_digests
            and item.request_digest not in started_request_digests
        ),
        key=lambda item: item.order_key,
    ))
    return QueueDecision(
        pending=pending,
        selected=pending[0] if pending else None,
        duplicate_job_ids=(),
        conflicts=(),
    )
