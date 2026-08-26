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

from . import GATE0_OPERATIONS
from .contracts import ContractError, QueueJob, exact_int, validate_gate0_operation
from .github_transport import Gate1GitHub

# This is intentionally duplicated as a drift sentinel, not as an extension of
# Gate 0.  Any change to the accepted Gate 0 operation surface fails closed.
EXPECTED_GATE0_OPERATIONS = frozenset(
    {
        "pr-snapshot",
        "pr-governor-evidence",
        "run-repository-validation",
        "run-test-profile",
    }
)


@dataclass(frozen=True)
class Gate0Invocation:
    return_code: int
    timed_out: bool
    output_root: str
    authoritative_comment_id: int | None


def _require_exact_gate0_surface() -> None:
    if GATE0_OPERATIONS != EXPECTED_GATE0_OPERATIONS:
        raise ContractError("Gate 0 operation surface drifted from the four accepted operations")


def _request_from_source(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
) -> EvidenceRequest:
    """Re-read the exact source through EFFECT_GATEWAY before Gate 0."""
    gateway = Gate1GitHub(runner, repository_root, job.repository)
    gateway.preflight()
    source = gateway.comment(job.request_comment_id)
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
    return request


def _authoritative_outcome(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
) -> int | None:
    """Delegate outcome election to the unchanged accepted Gate 0 logic."""
    request = _request_from_source(
        runner=runner,
        repository_root=repository_root,
        job=job,
    )

    # Gate 0 owns its existing GitHub publication/election TCB.  Reusing its
    # exact GhClient here is deliberately limited to Gate 0 outcome arbitration
    # so the lane does not copy or fork accepted election semantics.
    gh = GhClient(runner, repository_root)
    gh.preflight(job.repository)
    election = _discover_candidates(gh, request)
    incumbent = election.incumbent
    if incumbent is None:
        return None
    if incumbent.request_digest != job.request_digest or incumbent.target_sha != job.target_sha:
        raise ContractError("Gate 0 authoritative outcome differs from selected job identity")
    return exact_int(incumbent.comment_id, "Gate 0 authoritative comment id", minimum=1)


def invoke_once(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
    timeout_seconds: int = 3600,
) -> Gate0Invocation:
    _require_exact_gate0_surface()
    validate_gate0_operation(job.operation)
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
        raise ContractError("timeout_seconds must be an exact integer")
    if not 30 <= timeout_seconds <= 3600:
        raise ContractError("timeout_seconds outside fixed Gate 0 range")

    # Re-read and bind the source via the raw R5 EFFECT_GATEWAY immediately
    # before entering the accepted Gate 0 implementation.  Gate 0 then repeats
    # its own request/target/publication checks; it remains byte-for-byte
    # unchanged by this lane.
    _request_from_source(
        runner=runner,
        repository_root=repository_root,
        job=job,
    )

    # Gate 0 is the already-trusted execution boundary. Calling its fixed entry
    # point in-process avoids treating that entry point as an untrusted requested
    # command. No requested argv, executable, shell fragment or profile can be
    # substituted here.
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
                "--request",
                str(descriptor),
                "--output-root",
                str(output),
            ]
        )
        if isinstance(return_code, bool) or not isinstance(return_code, int):
            raise ContractError("Gate 0 entry point returned a non-integer status")
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
