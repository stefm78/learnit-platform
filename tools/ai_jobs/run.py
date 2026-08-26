#!/usr/bin/env python3
"""Drain one Gate 1 session sequentially after a human has started a Codespace.

This executable is intentionally conservative. It never creates/starts a
Codespace, never performs repository writes, and never invokes more than one
Gate 0 job without reconstructing GitHub-authoritative state.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.codespace_evidence.execute import CommandRunner
from tools.codespace_evidence.workspace import discover_repository_root

from tools.ai_jobs.contracts import ContractError, LedgerRecord, SessionGrant
from tools.ai_jobs.credential_boundary import (
    acquire_session_process_fence,
    final_effect_guard,
    require_request_authority,
    require_runtime_identity,
)
from tools.ai_jobs.gate0_adapter import invoke_once
from tools.ai_jobs.github_transport import Gate1GitHub
from tools.ai_jobs.ledger import render_record
from tools.ai_jobs.parser import (
    grant_from_comment,
    is_suspend_comment,
    ledger_from_comment,
    queue_job_from_comment,
)
from tools.ai_jobs.queue import elect
from tools.ai_jobs.session import (
    SessionProjection,
    bound_request_issue,
    project,
    require_exclusive_session,
)
from tools.ai_jobs.snapshot import StableSnapshot, stable_double_scan


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--authority-issue", required=True, type=int)
    parser.add_argument("--request-issue", required=True, type=int)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--codespace-name")
    parser.add_argument("--max-jobs", type=int, default=1)
    return parser.parse_args(argv)


def _parser_comment(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw["id"],
        "body": raw["body"],
        "user": {"login": raw["author"]},
        "created_at": raw["created_at"],
        "updated_at": raw["updated_at"],
        "issue_url": raw.get("issue_url"),
    }


def _target_sha(gh: Gate1GitHub, job: Any) -> str:
    comment = gh.comment(job.request_comment_id)
    parsed = queue_job_from_comment(
        comment,
        repository=job.repository,
        origin_type=job.origin_type,
        origin_number=job.origin_number,
    )
    if parsed is None or parsed.request_digest != job.request_digest:
        raise ContractError("source request cannot be reproduced at effect boundary")
    return gh.resolve_target_sha(parsed)


def _grants(
    snapshot: StableSnapshot,
    *,
    repository: str,
    authority_issue: int,
) -> list[SessionGrant]:
    grants: list[SessionGrant] = []
    for raw in snapshot.comments:
        item = grant_from_comment(
            _parser_comment(raw),
            repository=repository,
            authority_issue=authority_issue,
        )
        if item is not None:
            grants.append(item)
    return grants


def _all_ledger_records(
    snapshot: StableSnapshot,
    *,
    repository: str,
    authority_issue: int,
) -> list[LedgerRecord]:
    records: list[LedgerRecord] = []
    for raw in snapshot.comments:
        item = ledger_from_comment(
            _parser_comment(raw),
            repository=repository,
            authority_issue=authority_issue,
        )
        if item is not None:
            records.append(item)
    return records


def _ledger_records(snapshot: StableSnapshot, grant: SessionGrant) -> list[LedgerRecord]:
    return [
        record
        for record in _all_ledger_records(
            snapshot,
            repository=grant.repository,
            authority_issue=grant.authority_issue,
        )
        if record.session_id == grant.session_id and record.generation == grant.generation
    ]


def _validated_session_records(
    snapshot: StableSnapshot,
    *,
    grant: SessionGrant,
    request_issue: int,
) -> list[LedgerRecord]:
    grants = _grants(
        snapshot,
        repository=grant.repository,
        authority_issue=grant.authority_issue,
    )
    all_records = _all_ledger_records(
        snapshot,
        repository=grant.repository,
        authority_issue=grant.authority_issue,
    )
    require_exclusive_session(grants, all_records, grant)
    records = [
        record
        for record in all_records
        if record.session_id == grant.session_id and record.generation == grant.generation
    ]
    binding = bound_request_issue(records)
    if binding is not None and binding != request_issue:
        raise ContractError("Gate 1 generation is already bound to another request issue")
    return records


def _is_suspended(snapshot: StableSnapshot, *, repository: str, authority_issue: int) -> bool:
    return any(
        is_suspend_comment(
            _parser_comment(raw),
            repository=repository,
            authority_issue=authority_issue,
        )
        for raw in snapshot.comments
    )


def _jobs(snapshot: StableSnapshot, *, repository: str, request_issue: int) -> list[Any]:
    jobs = []
    for raw in snapshot.comments:
        job = queue_job_from_comment(
            _parser_comment(raw),
            repository=repository,
            origin_type="issue",
            origin_number=request_issue,
        )
        if job is not None:
            jobs.append(job)
    return jobs


def _publish_record(
    gh: Gate1GitHub,
    issue: int,
    *,
    record_type: str,
    grant: SessionGrant,
    previous: LedgerRecord | None,
    payload: dict[str, Any],
) -> LedgerRecord:
    record = LedgerRecord.build(
        record_type=record_type,
        repository=grant.repository,
        authority_issue=grant.authority_issue,
        session_id=grant.session_id,
        generation=grant.generation,
        sequence=1 if previous is None else previous.sequence + 1,
        previous_record_sha256=None if previous is None else previous.record_sha256,
        created_at=utc_now(),
        payload=payload,
    )
    posted = gh.publish_authority_comment(issue, render_record(record))
    reread = ledger_from_comment(
        posted,
        repository=grant.repository,
        authority_issue=grant.authority_issue,
    )
    if reread is None or reread.record_sha256 != record.record_sha256:
        raise ContractError("published ledger record did not round-trip exactly")

    # The POST response is not authority. Reconstruct the exact generation from
    # a stable GitHub reread and require the new record to be the unique tail.
    snapshot = stable_double_scan(lambda: gh.comments(issue))
    records = _ledger_records(snapshot, grant)
    current = project(records, grant)
    if current.last_record is None or current.last_record.record_sha256 != record.record_sha256:
        raise ContractError("published ledger record is not the authoritative generation tail")
    return record


def _enter_recovery(
    gh: Gate1GitHub,
    authority_issue: int,
    *,
    grant: SessionGrant,
    current: SessionProjection,
    reason: str,
) -> None:
    if current.state != "JOB_STARTED" or current.last_record is None:
        raise ContractError("RECOVERY_REQUIRED can only be entered from durable JOB_STARTED")
    digest = current.active_job_digest
    if not isinstance(digest, str) or not digest:
        raise ContractError("durable JOB_STARTED has no active request digest")
    _publish_record(
        gh,
        authority_issue,
        record_type="SESSION_RECOVERY_REQUIRED",
        grant=grant,
        previous=current.last_record,
        payload={"request_digest": digest, "reason": reason},
    )
    raise ContractError(
        "durable JOB_STARTED requires reconciliation; automatic replay is forbidden"
    )


def _selected_job(jobs: list[Any], record: LedgerRecord) -> Any:
    payload = record.payload
    if not isinstance(payload, dict):
        raise ContractError("durable JOB_SELECTED payload is unavailable")
    matches = [
        job
        for job in jobs
        if job.job_id == payload.get("job_id")
        and job.request_digest == payload.get("request_digest")
        and job.request_comment_id == payload.get("request_comment_id")
        and job.target_type == payload.get("target_type")
        and job.target_number == payload.get("target_number")
        and job.target_sha == payload.get("target_sha")
    ]
    if len(matches) != 1:
        raise ContractError(
            "durable JOB_SELECTED cannot be reconstructed exactly from the request snapshot"
        )
    return matches[0]


def _finish_closing(
    gh: Gate1GitHub,
    authority_issue: int,
    *,
    grant: SessionGrant,
    current: SessionProjection,
    request_snapshot: StableSnapshot,
) -> bool:
    if current.state != "CLOSING" or current.last_record is None:
        raise ContractError("closing recovery requires a durable close candidate")
    payload = current.last_record.payload
    expected_digest = payload.get("request_snapshot_sha256") if isinstance(payload, dict) else None
    cutoff = payload.get("cutoff_comment_id") if isinstance(payload, dict) else None
    if not isinstance(expected_digest, str) or not isinstance(cutoff, int):
        raise ContractError("close candidate lacks its request snapshot binding")

    changed = (
        request_snapshot.digest_sha256 != expected_digest
        or any(raw["id"] > cutoff for raw in request_snapshot.comments)
    )
    if changed:
        _publish_record(
            gh,
            authority_issue,
            record_type="SESSION_CLOSE_ABORTED",
            grant=grant,
            previous=current.last_record,
            payload={"reason": "REQUEST_SNAPSHOT_CHANGED_DURING_CLOSE"},
        )
        return False

    _publish_record(
        gh,
        authority_issue,
        record_type="SESSION_CLOSED",
        grant=grant,
        previous=current.last_record,
        payload={"final_request_snapshot_sha256": request_snapshot.digest_sha256},
    )
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if isinstance(args.max_jobs, bool) or not 1 <= args.max_jobs <= 100:
        raise ContractError("--max-jobs must be an integer from 1 through 100")
    if args.authority_issue == args.request_issue:
        raise ContractError("authority issue and request issue must be distinct")

    runner = CommandRunner()
    root = discover_repository_root(runner, Path.cwd())
    gh = Gate1GitHub(runner, root, args.repository)
    preflight = gh.preflight()

    authority = gh.issue(args.authority_issue)
    if authority.get("state") != "open":
        raise ContractError("Gate 1 implementation authority issue is not open")

    authority_snapshot = stable_double_scan(lambda: gh.comments(args.authority_issue))
    all_grants = _grants(
        authority_snapshot,
        repository=args.repository,
        authority_issue=args.authority_issue,
    )
    grants = [item for item in all_grants if item.session_id == args.session_id]
    if len(grants) != 1:
        raise ContractError("exactly one immutable human session grant is required")
    grant = grants[0]

    require_runtime_identity(
        preflight=preflight,
        grant=grant,
        codespace_name=args.codespace_name,
    )
    require_request_authority(gh.permission(grant.granted_by))

    # Retained for the entire function lifetime. Linux closes the descriptor and
    # releases the fence on every return or process termination.
    _process_fence = acquire_session_process_fence(grant)

    if _is_suspended(
        authority_snapshot,
        repository=args.repository,
        authority_issue=args.authority_issue,
    ):
        raise ContractError("Gate 1 authority contains an active suspension record")

    records = _validated_session_records(
        authority_snapshot,
        grant=grant,
        request_issue=args.request_issue,
    )
    current = project(records, grant)
    last = current.last_record
    if current.state == "CLOSED":
        if last is not None:
            return 0
        last = _publish_record(
            gh,
            args.authority_issue,
            record_type="SESSION_GRANT",
            grant=grant,
            previous=None,
            payload={
                "grant_comment_id": grant.grant_comment_id,
                "grant_digest": grant.grant_digest,
                "request_issue": args.request_issue,
            },
        )
        _publish_record(
            gh,
            args.authority_issue,
            record_type="SESSION_ACTIVE",
            grant=grant,
            previous=last,
            payload={
                "codespace_name": grant.codespace_name,
                "request_issue": args.request_issue,
            },
        )
    elif current.state == "GRANT_PENDING":
        if last is None:
            raise ContractError("GRANT_PENDING has no durable predecessor")
        if bound_request_issue(records) != args.request_issue:
            raise ContractError("GRANT_PENDING is bound to another request issue")
        _publish_record(
            gh,
            args.authority_issue,
            record_type="SESSION_ACTIVE",
            grant=grant,
            previous=last,
            payload={
                "codespace_name": grant.codespace_name,
                "request_issue": args.request_issue,
            },
        )
    elif current.state == "JOB_STARTED":
        _enter_recovery(
            gh,
            args.authority_issue,
            grant=grant,
            current=current,
            reason="RESTART_AFTER_DURABLE_JOB_STARTED",
        )
    elif current.state in {"RECOVERY_REQUIRED", "GLOBAL_HOLD"}:
        raise ContractError(f"Gate 1 cannot autonomously advance state {current.state}")
    elif current.state not in {"ACTIVE_IDLE", "JOB_TERMINAL", "JOB_SELECTED", "CLOSING"}:
        raise ContractError(f"Gate 1 cannot resume state {current.state}")

    completed = 0
    while completed < args.max_jobs:
        request_snapshot = stable_double_scan(lambda: gh.comments(args.request_issue))
        jobs = _jobs(
            request_snapshot,
            repository=args.repository,
            request_issue=args.request_issue,
        )

        authority_snapshot = stable_double_scan(lambda: gh.comments(args.authority_issue))
        if _is_suspended(
            authority_snapshot,
            repository=args.repository,
            authority_issue=args.authority_issue,
        ):
            raise ContractError("Gate 1 is suspended")

        records = _validated_session_records(
            authority_snapshot,
            grant=grant,
            request_issue=args.request_issue,
        )
        current = project(records, grant)
        last = current.last_record

        if current.state == "CLOSED":
            return 0
        if current.state in {"RECOVERY_REQUIRED", "GLOBAL_HOLD"}:
            raise ContractError(f"Gate 1 cannot autonomously advance state {current.state}")
        if current.state == "JOB_STARTED":
            _enter_recovery(
                gh,
                args.authority_issue,
                grant=grant,
                current=current,
                reason="RECONSTRUCTION_FOUND_DURABLE_JOB_STARTED",
            )
        if current.state == "GRANT_PENDING":
            if last is None:
                raise ContractError("GRANT_PENDING has no durable predecessor")
            _publish_record(
                gh,
                args.authority_issue,
                record_type="SESSION_ACTIVE",
                grant=grant,
                previous=last,
                payload={
                    "codespace_name": grant.codespace_name,
                    "request_issue": args.request_issue,
                },
            )
            continue
        if current.state == "CLOSING":
            if _finish_closing(
                gh,
                args.authority_issue,
                grant=grant,
                current=current,
                request_snapshot=request_snapshot,
            ):
                return 0
            continue
        if current.state not in {"ACTIVE_IDLE", "JOB_TERMINAL", "JOB_SELECTED"}:
            raise ContractError(f"Gate 1 reconstruction reached non-runnable state {current.state}")

        if current.state == "JOB_SELECTED":
            if last is None:
                raise ContractError("JOB_SELECTED has no durable record")
            job = _selected_job(jobs, last)
            selected = last
        else:
            decision = elect(
                jobs,
                terminal_request_digests=current.terminal_request_digests,
                started_request_digests=current.started_request_digests,
            )
            job = decision.selected
            if job is None:
                candidate = _publish_record(
                    gh,
                    args.authority_issue,
                    record_type="SESSION_CLOSE_CANDIDATE",
                    grant=grant,
                    previous=last,
                    payload={
                        "request_snapshot_sha256": request_snapshot.digest_sha256,
                        "cutoff_comment_id": request_snapshot.cutoff_comment_id,
                    },
                )
                closing_scan = stable_double_scan(lambda: gh.comments(args.request_issue))
                closing_projection = SessionProjection(
                    state="CLOSING",
                    last_record=candidate,
                    started_request_digests=current.started_request_digests,
                    terminal_request_digests=current.terminal_request_digests,
                    active_job_digest=None,
                )
                if _finish_closing(
                    gh,
                    args.authority_issue,
                    grant=grant,
                    current=closing_projection,
                    request_snapshot=closing_scan,
                ):
                    return 0
                continue

            require_request_authority(gh.permission(job.request_author))
            selected = _publish_record(
                gh,
                args.authority_issue,
                record_type="JOB_SELECTED",
                grant=grant,
                previous=last,
                payload={
                    "job_id": job.job_id,
                    "request_digest": job.request_digest,
                    "request_comment_id": job.request_comment_id,
                    "target_type": job.target_type,
                    "target_number": job.target_number,
                    "target_sha": job.target_sha,
                },
            )

        source_comment = gh.comment(job.request_comment_id)
        authority_now = stable_double_scan(lambda: gh.comments(args.authority_issue))
        suspended_now = _is_suspended(
            authority_now,
            repository=args.repository,
            authority_issue=args.authority_issue,
        )
        before_effect_records = _validated_session_records(
            authority_now,
            grant=grant,
            request_issue=args.request_issue,
        )
        before_effect = project(before_effect_records, grant)
        if (
            before_effect.state != "JOB_SELECTED"
            or before_effect.last_record is None
            or before_effect.last_record.record_sha256 != selected.record_sha256
        ):
            raise ContractError("session authority changed after JOB_SELECTED")

        permission_now = gh.permission(job.request_author)
        current_target = _target_sha(gh, job)
        final_effect_guard(
            job=job,
            request_comment=source_comment,
            current_target_sha=current_target,
            permission=permission_now,
            suspended=suspended_now,
        )

        started = _publish_record(
            gh,
            args.authority_issue,
            record_type="JOB_STARTED",
            grant=grant,
            previous=selected,
            payload={
                "job_id": job.job_id,
                "request_digest": job.request_digest,
                "request_comment_id": job.request_comment_id,
                "target_sha": job.target_sha,
            },
        )

        try:
            invocation = invoke_once(
                runner=runner,
                repository_root=root,
                job=job,
            )
        except Exception as exc:
            _publish_record(
                gh,
                args.authority_issue,
                record_type="SESSION_RECOVERY_REQUIRED",
                grant=grant,
                previous=started,
                payload={"request_digest": job.request_digest, "reason": type(exc).__name__},
            )
            raise

        if invocation.authoritative_comment_id is None:
            _publish_record(
                gh,
                args.authority_issue,
                record_type="SESSION_RECOVERY_REQUIRED",
                grant=grant,
                previous=started,
                payload={
                    "request_digest": job.request_digest,
                    "reason": "GATE0_AUTHORITATIVE_OUTCOME_NOT_FOUND",
                },
            )
            raise ContractError(
                "Gate 0 returned without a cryptographically authoritative final outcome"
            )

        # Effects have already happened. Even if a suspension arrives now, the
        # durable authoritative Gate 0 outcome must be terminalized rather than
        # left ambiguous. Reconstruct GitHub state and require our JOB_STARTED to
        # remain the unique active tail before recording terminal truth.
        after_effect_snapshot = stable_double_scan(lambda: gh.comments(args.authority_issue))
        after_effect_records = _validated_session_records(
            after_effect_snapshot,
            grant=grant,
            request_issue=args.request_issue,
        )
        after_effect = project(after_effect_records, grant)
        if (
            after_effect.state != "JOB_STARTED"
            or after_effect.last_record is None
            or after_effect.last_record.record_sha256 != started.record_sha256
            or after_effect.active_job_digest != job.request_digest
        ):
            raise ContractError("session authority changed after Gate 0 effect")

        terminal_result = (
            "COMPLETED"
            if invocation.return_code == 0 and not invocation.timed_out
            else "FAILED"
        )
        _publish_record(
            gh,
            args.authority_issue,
            record_type="JOB_TERMINAL",
            grant=grant,
            previous=started,
            payload={
                "job_id": job.job_id,
                "request_digest": job.request_digest,
                "result": terminal_result,
                "gate0_return_code": invocation.return_code,
                "gate0_timed_out": invocation.timed_out,
                "gate0_authoritative_comment_id": invocation.authoritative_comment_id,
            },
        )
        completed += 1

    # Keep the local fence live through the last durable write.
    _process_fence.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"GATE1_FAIL_CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
