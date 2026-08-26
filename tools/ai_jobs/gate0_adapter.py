"""Single-invocation adapter to the already accepted Gate 0 runner."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile

from tools.codespace_evidence.execute import CommandRunner
from tools.codespace_evidence.github import GhClient
from tools.codespace_evidence.request import EvidenceRequest, parse_request_envelope
from tools.codespace_evidence.run import _discover_candidates, main as gate0_main

from .contracts import ContractError, QueueJob, validate_gate0_operation


@dataclass(frozen=True)
class Gate0Invocation:
    return_code: int
    timed_out: bool
    output_root: str
    authoritative_comment_id: int | None


def _request_from_source(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
) -> tuple[GhClient, EvidenceRequest]:
    gh = GhClient(runner, repository_root)
    gh.preflight(job.repository)
    source = gh.fetch_request_comment(job.repository, job.request_comment_id)
    body = source.get("body")
    if not isinstance(body, str):
        raise ContractError("Gate 0 source request body is unavailable during reconciliation")
    value, digest = parse_request_envelope(body)
    request = EvidenceRequest.from_value(value, digest)
    if (
        request.job_id != job.job_id
        or request.digest_sha256 != job.request_digest
        or request.repository != job.repository
        or request.origin.type != job.origin_type
        or request.origin.number != job.origin_number
        or request.origin.request_comment_id != job.request_comment_id
        or request.target_type != job.target_type
        or request.target_number != job.target_number
        or request.target_sha != job.target_sha
    ):
        raise ContractError("Gate 0 source request changed identity before reconciliation")
    return gh, request


def _authoritative_outcome(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
) -> int | None:
    gh, request = _request_from_source(
        runner=runner,
        repository_root=repository_root,
        job=job,
    )
    election = _discover_candidates(gh, request)
    incumbent = election.incumbent
    if incumbent is None:
        return None
    if incumbent.request_digest != job.request_digest or incumbent.target_sha != job.target_sha:
        raise ContractError("Gate 0 authoritative outcome differs from selected job identity")
    return incumbent.comment_id


def invoke_once(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
    timeout_seconds: int = 3600,
) -> Gate0Invocation:
    validate_gate0_operation(job.operation)
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
        raise ContractError("timeout_seconds must be an exact integer")
    if not 30 <= timeout_seconds <= 3600:
        raise ContractError("timeout_seconds outside fixed Gate 0 range")

    # Gate 0 is the already-trusted execution boundary. Calling its fixed
    # entry point in-process avoids treating that entry point as an untrusted
    # requested command. Gate 0 continues to verify the exact request and to
    # confine the actual operation subprocess itself.
    with tempfile.TemporaryDirectory(prefix="learnit-gate1-") as tmp:
        root = Path(tmp)
        descriptor = root / "launch.json"
        output = root / "gate0-output"
        descriptor.write_text(
            json.dumps(
                {
                    "repository": job.repository,
                    "origin_type": job.origin_type,
                    "origin_number": job.origin_number,
                    "request_comment_id": job.request_comment_id,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        return_code = gate0_main(
            [
                "--request", str(descriptor),
                "--output-root", str(output),
            ]
        )
        authoritative_comment_id = _authoritative_outcome(
            runner=runner,
            repository_root=repository_root,
            job=job,
        )
        return Gate0Invocation(
            return_code=return_code,
            timed_out=False,
            output_root=str(output),
            authoritative_comment_id=authoritative_comment_id,
        )
