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
    SHA256_RE,
    canonical_json_bytes,
    exact_int,
    iso_utc,
    sha256_canonical,
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

FULL_V6_SECURITY = "FULL_V6_SECURITY"
PILOT_READ_ONLY = "GATE1_PILOT_READ_ONLY"
_PILOT_PERMIT_SCHEMA = "learnit.gate1.pilot-read-only.effect-permit.v1"


@dataclass(frozen=True)
class Gate0Invocation:
    return_code: int
    timed_out: bool
    output_root: str
    authoritative_comment_id: int | None


@dataclass(frozen=True)
class PilotEffectPermit:
    """Closed integrity handoff for the explicitly weaker read-only pilot.

    This permit is deliberately *not* a cryptographic authorization primitive.
    It binds one adapter call to the exact durable ``JOB_STARTED`` record and
    selected job inside the already-trusted pilot coordinator domain. The
    accepted #171 owner amendment requires callers and evidence to preserve
    that distinction: this profile must never be represented as full V6 effect
    isolation or compromised-broker resistance.
    """

    schema: str
    profile: str
    repository: str
    authority_issue: int
    session_id: str
    generation: int
    job_id: str
    request_digest: str
    request_comment_id: int
    operation: str
    target: Mapping[str, Any]
    started_record_sha256: str
    started_sequence: int
    issued_at: str
    permit_sha256: str

    @classmethod
    def build(
        cls,
        *,
        repository: str,
        authority_issue: int,
        session_id: str,
        generation: int,
        job: QueueJob,
        started_record_sha256: str,
        started_sequence: int,
        issued_at: str,
    ) -> "PilotEffectPermit":
        material = {
            "schema": _PILOT_PERMIT_SCHEMA,
            "profile": PILOT_READ_ONLY,
            "repository": repository,
            "authority_issue": authority_issue,
            "session_id": session_id,
            "generation": generation,
            "job_id": job.job_id,
            "request_digest": job.request_digest,
            "request_comment_id": job.request_comment_id,
            "operation": job.operation,
            "target": _selected_target(job),
            "started_record_sha256": started_record_sha256,
            "started_sequence": started_sequence,
            "issued_at": issued_at,
        }
        return cls(**material, permit_sha256=sha256_canonical(material))

    def __post_init__(self) -> None:
        if self.schema != _PILOT_PERMIT_SCHEMA or self.profile != PILOT_READ_ONLY:
            raise ContractError("pilot effect permit profile/schema is invalid")
        if not isinstance(self.repository, str) or "/" not in self.repository:
            raise ContractError("pilot effect permit repository is invalid")
        exact_int(self.authority_issue, "pilot permit authority_issue", minimum=1)
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ContractError("pilot effect permit session_id is unavailable")
        exact_int(self.generation, "pilot permit generation", minimum=1)
        if not isinstance(self.job_id, str) or not self.job_id:
            raise ContractError("pilot effect permit job_id is unavailable")
        if not isinstance(self.request_digest, str) or SHA256_RE.fullmatch(self.request_digest) is None:
            raise ContractError("pilot effect permit request digest is invalid")
        exact_int(self.request_comment_id, "pilot permit request_comment_id", minimum=1)
        validate_gate0_operation(self.operation)
        if self.operation not in EXPECTED_GATE0_OPERATIONS:
            raise ContractError("pilot permit operation is outside the fixed read-only surface")
        if not isinstance(self.target, Mapping):
            raise ContractError("pilot effect permit target is unavailable")
        canonical_json_bytes(dict(self.target))
        if (
            not isinstance(self.started_record_sha256, str)
            or SHA256_RE.fullmatch(self.started_record_sha256) is None
        ):
            raise ContractError("pilot effect permit JOB_STARTED digest is invalid")
        exact_int(self.started_sequence, "pilot permit started_sequence", minimum=1)
        iso_utc(self.issued_at, "pilot permit issued_at")
        if not isinstance(self.permit_sha256, str) or SHA256_RE.fullmatch(self.permit_sha256) is None:
            raise ContractError("pilot effect permit digest is invalid")
        material = {
            "schema": self.schema,
            "profile": self.profile,
            "repository": self.repository,
            "authority_issue": self.authority_issue,
            "session_id": self.session_id,
            "generation": self.generation,
            "job_id": self.job_id,
            "request_digest": self.request_digest,
            "request_comment_id": self.request_comment_id,
            "operation": self.operation,
            "target": dict(self.target),
            "started_record_sha256": self.started_record_sha256,
            "started_sequence": self.started_sequence,
            "issued_at": self.issued_at,
        }
        if sha256_canonical(material) != self.permit_sha256:
            raise ContractError("pilot effect permit self-digest mismatch")


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


def _verify_pilot_permit(*, job: QueueJob, permit: PilotEffectPermit | None) -> None:
    if permit is None:
        raise ContractError("read-only pilot effect permit is required")
    if permit.profile != PILOT_READ_ONLY:
        raise ContractError("pilot effect permit profile mismatch")
    if permit.repository != job.repository:
        raise ContractError("pilot effect permit repository mismatch")
    if permit.job_id != job.job_id or permit.request_digest != job.request_digest:
        raise ContractError("pilot effect permit job identity mismatch")
    if permit.request_comment_id != job.request_comment_id:
        raise ContractError("pilot effect permit source comment mismatch")
    if permit.operation != job.operation:
        raise ContractError("pilot effect permit operation mismatch")
    if canonical_json_bytes(dict(permit.target)) != canonical_json_bytes(_selected_target(job)):
        raise ContractError("pilot effect permit target mismatch")


def invoke_once(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
    timeout_seconds: int = 3600,
    security_profile: str = FULL_V6_SECURITY,
    capability: Mapping[str, Any] | None = None,
    verifier: EffectCapabilityVerifier | None = None,
    expectation: EffectCapabilityExpectation | None = None,
    pilot_permit: PilotEffectPermit | None = None,
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
    # this integration layer.
    _request_from_source(
        runner=runner,
        repository_root=repository_root,
        job=job,
    )

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

        if security_profile == FULL_V6_SECURITY:
            if pilot_permit is not None:
                raise ContractError("pilot permit cannot be mixed with FULL_V6_SECURITY")
            _verify_effect_capability(
                job=job,
                capability=capability,
                verifier=verifier,
                expectation=expectation,
            )
        elif security_profile == PILOT_READ_ONLY:
            if capability is not None or verifier is not None or expectation is not None:
                raise ContractError("pilot profile cannot masquerade as signed V6 authority")
            _verify_pilot_permit(job=job, permit=pilot_permit)
        else:
            raise ContractError("unknown Gate 1 security profile")

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
