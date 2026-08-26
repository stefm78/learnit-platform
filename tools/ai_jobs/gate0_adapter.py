"""Single-invocation adapter to the already accepted Gate 0 runner."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from tools.codespace_evidence.execute import CommandRunner
from tools.codespace_evidence.request import EvidenceRequest, parse_request_envelope
from tools.codespace_evidence.run import _discover_candidates, main as gate0_main

from . import GATE0_OPERATIONS
from .contracts import (
    ContractError,
    QueueJob,
    canonical_json_bytes,
    exact_int,
    validate_gate0_operation,
)
from .credential_boundary import EffectCapabilityExpectation, EffectCapabilityVerifier
from .github_transport import Gate1GitHub

# This is intentionally duplicated as a drift sentinel, not as an extension of
# Gate 0. Any change to the accepted Gate 0 operation surface fails closed.
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


@dataclass(frozen=True)
class _Gate0ElectionReadback:
    """Minimal read-only view consumed by the unchanged Gate 0 election code.

    GitHub access remains inside ``Gate1GitHub``. The accepted Gate 0 election
    receives only the authenticated publisher identity and normalized origin
    comments; this adapter does not acquire, retain, forward or expose GitHub
    credentials.
    """

    gateway: Gate1GitHub
    repository: str
    authenticated_login: str

    def list_origin_comments(self, repository: str, origin_number: int) -> list[dict[str, Any]]:
        if repository != self.repository:
            raise ContractError("Gate 0 election requested another repository")
        number = exact_int(origin_number, "Gate 0 origin number", minimum=1)
        return self.gateway.comments(number)


def _require_exact_gate0_surface() -> None:
    if GATE0_OPERATIONS != EXPECTED_GATE0_OPERATIONS:
        raise ContractError("Gate 0 operation surface drifted from the four accepted operations")


def _request_via_gateway(*, gateway: Gate1GitHub, job: QueueJob) -> EvidenceRequest:
    """Re-read and bind the exact immutable Gate 0 source through EFFECT_GATEWAY."""
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


def _gateway(
    *,
    runner: CommandRunner,
    repository_root: Path,
    repository: str,
) -> tuple[Gate1GitHub, str]:
    gateway = Gate1GitHub(runner, repository_root, repository)
    preflight = gateway.preflight()
    login = preflight.get("authenticated_login")
    if not isinstance(login, str) or not login:
        raise ContractError("EFFECT_GATEWAY authenticated identity is unavailable")
    return gateway, login


def _request_from_source(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
) -> EvidenceRequest:
    """Re-read the exact source through EFFECT_GATEWAY before Gate 0."""
    gateway, _login = _gateway(
        runner=runner,
        repository_root=repository_root,
        repository=job.repository,
    )
    return _request_via_gateway(gateway=gateway, job=job)


def _authoritative_outcome(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
) -> int | None:
    """Delegate unchanged Gate 0 outcome election over gateway-only read-back."""
    gateway, login = _gateway(
        runner=runner,
        repository_root=repository_root,
        repository=job.repository,
    )
    request = _request_via_gateway(gateway=gateway, job=job)
    readback = _Gate0ElectionReadback(
        gateway=gateway,
        repository=job.repository,
        authenticated_login=login,
    )

    # Gate 0 retains ownership of its accepted final-outcome validation and
    # election algorithm. Only the transport dependency is replaced by the
    # narrow EFFECT_GATEWAY read-back view; no election semantics are copied.
    election = _discover_candidates(readback, request)
    incumbent = election.incumbent
    if incumbent is None:
        return None
    if incumbent.request_digest != job.request_digest or incumbent.target_sha != job.target_sha:
        raise ContractError("Gate 0 authoritative outcome differs from selected job identity")
    return exact_int(incumbent.comment_id, "Gate 0 authoritative comment id", minimum=1)


def _selected_target(job: QueueJob) -> dict[str, Any]:
    return {
        "type": job.target_type,
        "number": job.target_number,
        "sha": job.target_sha,
    }


def _verify_effect_capability(
    *,
    job: QueueJob,
    capability: Mapping[str, Any] | None,
    verifier: EffectCapabilityVerifier | None,
    expectation: EffectCapabilityExpectation | None,
) -> None:
    """Consume external signed authority at the last lane-owned pre-effect point."""
    if capability is None or verifier is None or expectation is None:
        raise ContractError("signed single-use effect capability is required")
    if canonical_json_bytes(dict(expectation.target)) != canonical_json_bytes(_selected_target(job)):
        raise ContractError("capability expectation target differs from selected Gate 0 job")
    verifier.verify_and_consume(capability=capability, expected=expectation)


def invoke_once(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
    timeout_seconds: int = 3600,
    capability: Mapping[str, Any] | None = None,
    verifier: EffectCapabilityVerifier | None = None,
    expectation: EffectCapabilityExpectation | None = None,
) -> Gate0Invocation:
    _require_exact_gate0_surface()
    validate_gate0_operation(job.operation)
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
        raise ContractError("timeout_seconds must be an exact integer")
    if not 30 <= timeout_seconds <= 3600:
        raise ContractError("timeout_seconds outside fixed Gate 0 range")

    # Re-read and bind the source via raw R5 EFFECT_GATEWAY immediately before
    # entering the accepted Gate 0 implementation. Gate 0 then repeats its own
    # request/target/publication checks; it remains byte-for-byte unchanged by
    # this lane.
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

        # The signer and private key stay outside EFFECT_GATEWAY. The parent
        # presents an already-issued capability plus the trusted verifier and
        # exact expectation. Verification/nonce consumption is the final action
        # owned by this lane before Gate 0 can create an external effect.
        _verify_effect_capability(
            job=job,
            capability=capability,
            verifier=verifier,
            expectation=expectation,
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
