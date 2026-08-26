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
from tools.ai_jobs.session import project
from tools.ai_jobs.snapshot import stable_double_scan


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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if isinstance(args.max_jobs, bool) or not 1 <= args.max_jobs <= 100:
        raise ContractError("--max-jobs must be an integer from 1 through 100")

    root = discover_repository_root(Path.cwd())
    runner = CommandRunner()
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
    if current.state == "CLOSED" and last is None:
        last = _publish_record(
            gh, args.authority_issue,
            record_type="SESSION_GRANT",
            grant=grant,
            previous=None,
            payload={"grant_comment_id": grant.grant_comment_id, "grant_digest": grant.grant_digest},
        )
        last = _publish_record(
            gh, args.authority_issue,
            record_type="SESSION_ACTIVE",
            grant=grant,
            previous=last,
            payload={"codespace_name": grant.codespace_name},
        )

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
        if current.state in {"RECOVERY_REQUIRED", "GLOBAL_HOLD"}:
            raise ContractError(f"Gate 1 cannot autonomously advance state {current.state}")

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
            if any(raw["id"] > request_snapshot.cutoff_comment_id for raw in closing_scan.comments):
                _publish_record(
                    gh, args.authority_issue,
                    record_type="SESSION_CLOSE_ABORTED",
                    grant=grant,
                    previous=last,
                    payload={"reason": "REQUEST_ARRIVED_DURING_CLOSE"},
                )
                continue
            _publish_record(
                gh, args.authority_issue,
                record_type="SESSION_CLOSED",
                grant=grant,
                previous=last,
                payload={"final_request_snapshot_sha256": closing_scan.digest_sha256},
            )
            return 0

        permission = gh.permission(job.request_author)
        require_request_authority(permission)
        source_comment = gh.comment(job.request_comment_id)

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
