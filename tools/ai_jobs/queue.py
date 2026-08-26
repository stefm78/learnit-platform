"""Pure deterministic queue election."""
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
    """Elect exactly one oldest admissible request.

    A job_id reused with another digest is a hard conflict.  An already-started
    digest can never be elected again after a crash; recovery must reconcile its
    existing Gate 0 outcome.
    """
    by_job: dict[str, list[QueueJob]] = {}
    for job in jobs:
        by_job.setdefault(job.job_id, []).append(job)

    duplicate_ids: list[str] = []
    conflicts: list[str] = []
    unique: list[QueueJob] = []
    for job_id, group in sorted(by_job.items()):
        digests = {item.request_digest for item in group}
        if len(digests) > 1:
            conflicts.append(job_id)
            continue
        canonical = min(group, key=lambda item: item.order_key)
        if len(group) > 1:
            duplicate_ids.append(job_id)
        unique.append(canonical)

    if conflicts:
        raise ContractError(
            "queue contains job_id conflicts with different digests: "
            + ",".join(conflicts)
        )

    pending = tuple(sorted(
        (
            item for item in unique
            if item.request_digest not in terminal_request_digests
            and item.request_digest not in started_request_digests
        ),
        key=lambda item: item.order_key,
    ))
    return QueueDecision(
        pending=pending,
        selected=pending[0] if pending else None,
        duplicate_job_ids=tuple(duplicate_ids),
        conflicts=tuple(conflicts),
    )
