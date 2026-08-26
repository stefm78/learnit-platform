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

from tools.ai_jobs.contracts import ContractError, LedgerRecord
from tools.ai_jobs.credential_boundary import (
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
from tools.ai_jobs.session import SessionProjection, project
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


def _publish_record(
    gh: Gate1GitHub,
    issue: int,
    *,
    record_type: str,
    grant: Any,
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
    return record


def _enter_recovery(
    gh: Gate1GitHub,
    authority_issue: int,
    *,
    grant: Any,
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
    grant: Any,
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

    authority_snapshot = stable_double_scan(
        lambda: gh.comments(args.authority_issue)
    )
    grants = [
        item for raw in authority_snapshot.comments
        if (item := grant_from_comment(
            {
                "id": raw["id"], "body": raw["body"],
                "user": {"login": raw["author"]},
                "created_at": raw["created_at"], "updated_at": raw["updated_at"],
            },
            repository=args.repository,
            authority_issue=args.authority_issue,
        )) is not None
        and item.session_id == args.session_id
    ]
    if len(grants) != 1:
        raise ContractError("exactly one immutable human session grant is required")
    grant = grants[0]
    require_runtime_identity(
        preflight=preflight,
        grant=grant,
        codespace_name=args.codespace_name,
    )
    require_request_authority(gh.permission(grant.granted_by))

    suspended = any(
        is_suspend_comment(
            {
                "id": raw["id"], "body": raw["body"],
                "user": {"login": raw["author"]},
                "created_at": raw["created_at"], "updated_at": raw["updated_at"],
            },
            repository=args.repository,
            authority_issue=args.authority_issue,
        )
        for raw in authority_snapshot.comments
    )
    if suspended:
        raise ContractError("Gate 1 authority contains an active suspension record")

    ledger_records = [
        item for raw in authority_snapshot.comments
        if (item := ledger_from_comment(
            {
                "id": raw["id"], "body": raw["body"],
                "user": {"login": raw["author"]},
                "created_at": raw["created_at"], "updated_at": raw["updated_at"],
            },
            repository=args.repository,
            authority_issue=args.authority_issue,
        )) is not None
        and item.session_id == grant.session_id
        and item.generation == grant.generation
    ]

    current = project(ledger_records, grant)
    last = current.last_record
    if current.state == "CLOSED":
        if last is not None:
            # A durable closed generation is immutable and cannot be reopened.
            return 0
        last = _publish_record(
            gh, args.authority_issue,
            record_type="SESSION_GRANT",
            grant=grant,
            previous=None,
            payload={"grant_comment_id": grant.grant_comment_id, "grant_digest": grant.grant_digest},
        )
        _publish_record(
            gh, args.authority_issue,
            record_type="SESSION_ACTIVE",
            grant=grant,
            previous=last,
            payload={"codespace_name": grant.codespace_name},
        )
    elif current.state == "GRANT_PENDING":
        if last is None:
            raise ContractError("GRANT_PENDING has no durable predecessor")
        _publish_record(
            gh, args.authority_issue,
            record_type="SESSION_ACTIVE",
            grant=grant,
            previous=last,
            payload={"codespace_name": grant.codespace_name},
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

    completed = 0
    while completed < args.max_jobs:
        request_snapshot = stable_double_scan(
            lambda: gh.comments(args.request_issue)
        )
        jobs = []
        for raw in request_snapshot.comments:
            job = queue_job_from_comment(
                {
                    "id": raw["id"], "body": raw["body"],
                    "user": {"login": raw["author"]},
                    "created_at": raw["created_at"], "updated_at": raw["updated_at"],
                    "issue_url": raw["issue_url"],
                },
                repository=args.repository,
                origin_type="issue",
                origin_number=args.request_issue,
            )
            if job is not None:
                jobs.append(job)

        authority_snapshot = stable_double_scan(
            lambda: gh.comments(args.authority_issue)
        )
        records = [
            item for raw in authority_snapshot.comments
            if (item := ledger_from_comment(
                {
                    "id": raw["id"], "body": raw["body"],
                    "user": {"login": raw["author"]},
                    "created_at": raw["created_at"], "updated_at": raw["updated_at"],
                },
                repository=args.repository,
                authority_issue=args.authority_issue,
            )) is not None
            and item.session_id == grant.session_id
            and item.generation == grant.generation
        ]
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
                gh, args.authority_issue,
                record_type="SESSION_ACTIVE",
                grant=grant,
                previous=last,
                payload={"codespace_name": grant.codespace_name},
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
            raise ContractError(
                f"Gate 1 reconstruction reached non-runnable state {current.state}"
            )

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
                last = _publish_record(
                    gh, args.authority_issue,
                    record_type="SESSION_CLOSE_CANDIDATE",
                    grant=grant,
                    previous=last,
                    payload={
                        "request_snapshot_sha256": request_snapshot.digest_sha256,
                        "cutoff_comment_id": request_snapshot.cutoff_comment_id,
                    },
                )
                closing_scan = stable_double_scan(lambda: gh.comments(args.request_issue))
                closing_projection = project([
                    *records,
                    ledger_from_comment(
                        {
                            "id": 1,
                            "body": render_record(last),
                            "user": {"login": grant.granted_by},
                            "created_at": last.created_at,
                            "updated_at": last.created_at,
                        },
                        repository=args.repository,
                        authority_issue=args.authority_issue,
                    ),
                ], grant)
                # The synthetic parse above exists only to reuse the same close
                # transition helper with the already round-tripped local record.
                # Replace it immediately with an explicit projection object so
                # no synthetic GitHub identity participates in authority.
                closing_projection = SessionProjection(
                    state="CLOSING",
                    last_record=last,
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

            selected = _publish_record(
                gh, args.authority_issue,
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

        permission = gh.permission(job.request_author)
        require_request_authority(permission)
        source_comment = gh.comment(job.request_comment_id)

        authority_now = stable_double_scan(lambda: gh.comments(args.authority_issue))
        suspended_now = any(
            is_suspend_comment(
                {
                    "id": raw["id"], "body": raw["body"],
                    "user": {"login": raw["author"]},
                    "created_at": raw["created_at"], "updated_at": raw["updated_at"],
                },
                repository=args.repository,
                authority_issue=args.authority_issue,
            )
            for raw in authority_now.comments
        )
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
            gh, args.authority_issue,
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
                gh, args.authority_issue,
                record_type="SESSION_RECOVERY_REQUIRED",
                grant=grant,
                previous=started,
                payload={
                    "request_digest": job.request_digest,
                    "reason": type(exc).__name__,
                },
            )
            raise

        if invocation.authoritative_comment_id is None:
            _publish_record(
                gh, args.authority_issue,
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

        terminal_result = (
            "COMPLETED"
            if invocation.return_code == 0 and not invocation.timed_out
            else "FAILED"
        )
        _publish_record(
            gh, args.authority_issue,
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

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"GATE1_FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
