#!/usr/bin/env python3
"""Execute one verified Gate 0 evidence request."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.codespace_evidence import (
    OUTCOME_MARKER,
    OUTCOME_SCHEMA_VERSION,
    PUBLICATION_LIMIT_BYTES,
    STATEMENT,
)
from tools.codespace_evidence.execute import (
    CommandRunner,
    collect_environment,
    redact_value,
    utc_now,
)
from tools.codespace_evidence.github import (
    GhClient,
    GitHubError,
    PublicationResult,
    _comment_login,
    _cryptographically_complete_publication,
    _publication_headers,
    _publication_payload,
)
from tools.codespace_evidence.operations import OperationResult, execute_operation
from tools.codespace_evidence.outcome import (
    allocate_attempt,
    build_facts,
    ensure_publication_budget,
    preview_capsule_size,
    render_capsule,
    render_oversize_diagnostic,
    seal_bundle,
    write_bundle_files,
    write_publication_failure,
    write_publication_receipt,
    write_stop_receipt,
)
from tools.codespace_evidence.request import LaunchDescriptor, load_and_verify_request
from tools.codespace_evidence.stop import stop_current_codespace
from tools.codespace_evidence.workspace import (
    compare_snapshots,
    discover_repository_root,
    snapshot_primary_checkout,
)

DEFAULT_REQUEST = Path(".codespace-evidence/request.json")
DEFAULT_OUTPUT = Path(".agent-result/codespace-evidence")
SHA256_HEX = set("0123456789abcdef")


class ArbitrationError(RuntimeError):
    """GitHub-only final-outcome arbitration failed closed."""


@dataclass(frozen=True)
class FinalCandidate:
    comment_id: int
    html_url: str
    body: str
    body_sha256: str
    request_digest: str
    target_sha: str
    created_at: str | None


@dataclass(frozen=True)
class DuplicateFinalOutcome:
    comment_id: int
    classification: str
    incumbent_comment_id: int
    repository: str
    job_id: str
    request_digest: str
    target_sha: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "comment_id": self.comment_id,
            "classification": self.classification,
            "incumbent_comment_id": self.incumbent_comment_id,
            "repository": self.repository,
            "job_id": self.job_id,
            "request_sha256": self.request_digest,
            "target_sha": self.target_sha,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class Election:
    incumbent: FinalCandidate | None
    valid: tuple[FinalCandidate, ...]
    losers: tuple[DuplicateFinalOutcome, ...]

    @property
    def duplicate_ids(self) -> list[int]:
        return [item.comment_id for item in self.losers]


def _claim_request(output_root: Path, job_id: str, request_digest: str) -> bool:
    """Bind a local output root to one digest without pretending it is a global claim.

    The file remains a local conflict detector. A same-digest restart is allowed because
    GitHub arbitration, not this file, determines the authoritative final outcome.
    """

    job_root = output_root / job_id
    job_root.mkdir(parents=True, exist_ok=True)
    claim_path = job_root / "request.sha256"
    payload = request_digest + "\n"
    try:
        fd = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = claim_path.read_text(encoding="utf-8").strip()
        if existing != request_digest:
            raise ArbitrationError("CONFLICT_DIFFERENT_DIGEST: local job_id binding differs")
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        claim_path.unlink(missing_ok=True)
        raise
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stop-after-success", action="store_true")
    return parser.parse_args(argv)


def _stale_before(request: Any, observed: dict[str, Any]) -> OperationResult:
    return OperationResult(
        "FAILED",
        "STALE_TARGET",
        {
            "requested_sha": request.target_sha,
            "observed_sha": observed.get("sha"),
            "operation_executed": False,
        },
        ["TARGET_MOVED_BEFORE_EXECUTION"],
        {},
        (
            f"Target moved before execution: requested {request.target_sha}, "
            f"observed {observed.get('sha')}. No operation ran."
        ),
    )


def _apply_stale_after(request: Any, result: OperationResult, observed: dict[str, Any]) -> None:
    if observed.get("sha") == request.target_sha:
        return
    result.status = "FAILED"
    result.classification = "STALE_AFTER_EXECUTION"
    result.missing_proof = sorted(set([*result.missing_proof, "TARGET_MOVED_AFTER_EXECUTION"]))
    result.facts = {
        **result.facts,
        "stale_after_execution": {
            "requested_sha": request.target_sha,
            "observed_sha": observed.get("sha"),
        },
    }
    result.summary += " Target moved after execution; facts are diagnostic only."


def _required_fragments(facts: dict[str, Any], manifest: str, bundle: str) -> list[str]:
    return [
        "AI_CODESPACE_OUTCOME_V1\n",
        f"job_id: {facts['job_id']}\n",
        f"attempt: {facts['attempt']}\n",
        f"request_sha256: {facts['request_sha256']}\n",
        f"repository: {facts['repository']}\n",
        f"origin: {facts['origin']['type']}#{facts['origin']['number']}\n",
        f"target_sha: {facts['target']['requested_sha']}\n",
        f"manifest_sha256: {manifest}\n",
        f"bundle_sha256: {bundle}\n",
        STATEMENT,
    ]


def _facts(
    request: Any,
    attempt: Any,
    result: OperationResult,
    started: str,
    before: dict[str, Any],
    after: dict[str, Any],
    checkout: dict[str, Any],
    preflight: dict[str, Any],
    runner: CommandRunner,
    excerpt: int = 4096,
) -> dict[str, Any]:
    return build_facts(
        request=request,
        attempt=attempt.number,
        status=result.status,
        classification=result.classification,
        started_at=started,
        completed_at=utc_now(),
        target_before=before,
        target_after=after,
        operation_facts=result.facts,
        missing_proof=result.missing_proof,
        checkout_proof=checkout,
        preflight=preflight,
        commands=runner.records_summary(excerpt_bytes=excerpt),
    )


def _failure_classification(exc: Exception) -> str:
    if isinstance(exc, (GitHubError, ArbitrationError, FileNotFoundError, ConnectionError, TimeoutError)):
        return "FAIL_ENVIRONMENT"
    return "FAIL_HARNESS"


def _unbound_attempt(output: Path, descriptor_path: Path) -> tuple[Any | None, dict[str, Any]]:
    try:
        descriptor = LaunchDescriptor.from_path(descriptor_path)
    except Exception:
        return None, {}
    job_id = f"UNBOUND-{descriptor.origin_type.upper()}-{descriptor.origin_number}-{descriptor.request_comment_id}"
    attempt = allocate_attempt(output, job_id)
    identity = {
        "job_id": job_id,
        "repository": descriptor.repository,
        "origin": {
            "type": descriptor.origin_type,
            "number": descriptor.origin_number,
            "request_comment_id": descriptor.request_comment_id,
        },
    }
    return attempt, identity


def _write_classified_failure(
    *,
    attempt: Any,
    request: Any | None,
    identity: dict[str, Any],
    exc: Exception,
    started: str,
    runner: CommandRunner,
) -> None:
    classification = _failure_classification(exc)
    error = redact_value({"type": type(exc).__name__, "message": str(exc)})
    if request is not None:
        facts: dict[str, Any] = {
            "schema_version": OUTCOME_SCHEMA_VERSION,
            "marker": OUTCOME_MARKER,
            "job_id": request.job_id,
            "attempt": attempt.number,
            "request_sha256": request.digest_sha256,
            "operation": request.operation,
            "repository": request.repository,
            "origin": {
                "type": request.origin.type,
                "number": request.origin.number,
                "request_comment_id": request.origin.request_comment_id,
            },
            "target": {
                "type": request.target_type,
                "number": request.target_number,
                "requested_sha": request.target_sha,
                "resolution_state": "NOT_COMPLETED",
            },
        }
    else:
        facts = {
            "schema_version": OUTCOME_SCHEMA_VERSION,
            "marker": OUTCOME_MARKER,
            "job_id": identity.get("job_id", f"UNBOUND-{attempt.number:03d}"),
            "attempt": attempt.number,
            "request_sha256": None,
            "operation": None,
            "repository": identity.get("repository"),
            "origin": identity.get("origin"),
            "target": {"resolution_state": "REQUEST_NOT_BOUND"},
        }
    facts.update(
        {
            "status": "FAILED",
            "classification": classification,
            "started_at": started,
            "completed_at": utc_now(),
            "commands": runner.records_summary(excerpt_bytes=1024),
            "facts": {"failure": error},
            "missing_proof": ["GITHUB_PREFLIGHT_OR_REQUEST_BINDING_FAILED"],
            "primary_checkout": {"unchanged": None, "state": "NOT_CAPTURED"},
            "github_preflight": {"state": "FAILED", "error": error},
            "statement": STATEMENT,
        }
    )
    manifest_path = attempt.bundle / "manifest.sha256"
    sealed = None
    if not manifest_path.exists():
        write_bundle_files(
            attempt,
            facts=redact_value(facts),
            summary=f"{classification}: GitHub request binding or preflight failed; no target operation ran.",
            runner=runner,
            environment={"capture_state": "MINIMAL_FAILURE_ONLY"},
            artifacts={},
        )
        sealed = seal_bundle(attempt)
    failure_path = attempt.publication / "failure.json"
    if not failure_path.exists():
        payload: dict[str, Any] = {
            "state": "EXECUTION_ABORTED_BEFORE_VERIFIED_PUBLICATION",
            "status": "FAILED",
            "classification": classification,
            "error": error,
        }
        if sealed is not None:
            payload.update(
                {
                    "manifest_sha256": sealed.manifest_sha256,
                    "bundle_sha256": sealed.bundle_sha256,
                }
            )
        write_publication_failure(attempt, payload)
    stop_path = attempt.stop / "receipt.json"
    if not stop_path.exists():
        write_stop_receipt(
            attempt,
            {"state": "DISABLED_NOT_DURABLY_VERIFIED", "classification": classification},
        )


def _valid_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= SHA256_HEX


def _candidate_matches_complete_identity(payload: dict[str, Any], request: Any) -> bool:
    facts = payload.get("facts")
    if facts is None:
        # FINAL_DIAGNOSTIC_ONLY is already cryptographically bound to its
        # declared repository, origin, digest and target SHA.
        return True
    if not isinstance(facts, dict):
        return False
    origin = facts.get("origin")
    target = facts.get("target")
    return (
        facts.get("operation") == request.operation
        and isinstance(origin, dict)
        and origin.get("type") == request.origin.type
        and origin.get("number") == request.origin.number
        and origin.get("request_comment_id") == request.origin.request_comment_id
        and isinstance(target, dict)
        and target.get("type") == request.target_type
        and target.get("number") == request.target_number
        and target.get("requested_sha") == request.target_sha
    )


def _declared_final_failure(
    *,
    comment_id: int,
    category: str,
    reason: str,
    stage: str,
) -> ArbitrationError:
    diagnostic = {
        "classification": "INVALID_DECLARED_FINAL_OUTCOME",
        "comment_id": comment_id,
        "category": category,
        "reason": reason,
        "validation_stage": stage,
    }
    return ArbitrationError(
        "INVALID_DECLARED_FINAL_OUTCOME: "
        + json.dumps(diagnostic, sort_keys=True, separators=(",", ":"))
    )


def _parse_declared_origin(value: Any) -> tuple[str, int] | None:
    if not isinstance(value, str) or "#" not in value:
        return None
    origin_type, number = value.rsplit("#", 1)
    if origin_type not in {"issue", "pull_request"}:
        return None
    try:
        parsed_number = int(number)
    except ValueError:
        return None
    if parsed_number < 1:
        return None
    return origin_type, parsed_number


def _discover_candidates(gh: GhClient, request: Any) -> Election:
    """Discover by repository+job_id, reject collisions, validate, then elect."""

    trusted_login = gh.authenticated_login
    if not isinstance(trusted_login, str) or not trusted_login:
        raise ArbitrationError("authenticated publisher identity is unavailable")

    valid_same_digest: list[FinalCandidate] = []
    seen_ids: set[int] = set()

    for comment in gh.list_origin_comments(request.repository, request.origin.number):
        comment_id = comment.get("id")
        body = comment.get("body")

        if not isinstance(comment_id, int) or comment_id in seen_ids:
            continue
        seen_ids.add(comment_id)

        if not isinstance(body, str):
            continue

        # A comment without a final-outcome claim is ordinary conversation.
        if OUTCOME_MARKER not in body:
            continue

        # From this point onward the comment declared itself final. It may no
        # longer disappear through permissive filtering.
        if _comment_login(comment) != trusted_login:
            raise _declared_final_failure(
                comment_id=comment_id,
                category="UNAUTHORIZED_AUTHOR",
                reason="declared final outcome author differs from authenticated publisher",
                stage="author_validation",
            )

        headers = _publication_headers(body)
        if headers is None:
            raise _declared_final_failure(
                comment_id=comment_id,
                category="MALFORMED_OR_TRUNCATED_SCHEMA",
                reason="marker exists but the closed unique header shape is invalid",
                stage="header_parsing",
            )

        payload = _publication_payload(body)
        if payload is None:
            raise _declared_final_failure(
                comment_id=comment_id,
                category="MALFORMED_OR_TRUNCATED_PAYLOAD",
                reason="marker exists but exactly one strict JSON payload was not obtained",
                stage="payload_parsing",
            )

        declared_repository = headers.get("repository")
        declared_job_id = headers.get("job_id")
        digest = headers.get("request_sha256")
        declared_target_sha = headers.get("target_sha")
        declared_origin = _parse_declared_origin(headers.get("origin"))

        if declared_repository != request.repository:
            raise _declared_final_failure(
                comment_id=comment_id,
                category="CANONICAL_REPOSITORY_MISMATCH",
                reason="declared final outcome names another canonical repository",
                stage="repository_job_discovery",
            )

        if declared_job_id != request.job_id:
            raise _declared_final_failure(
                comment_id=comment_id,
                category="JOB_ID_MISMATCH_OR_AMBIGUITY",
                reason="declared final outcome names another or missing job_id",
                stage="repository_job_discovery",
            )

        if not _valid_digest(digest):
            raise _declared_final_failure(
                comment_id=comment_id,
                category="INVALID_REQUEST_DIGEST",
                reason="request_sha256 is not a full lowercase SHA-256",
                stage="digest_validation",
            )

        if not isinstance(declared_target_sha, str) or len(declared_target_sha) != 40:
            raise _declared_final_failure(
                comment_id=comment_id,
                category="INVALID_TARGET_SHA",
                reason="target_sha is absent or malformed",
                stage="declared_identity_validation",
            )

        if declared_origin is None:
            raise _declared_final_failure(
                comment_id=comment_id,
                category="INVALID_ORIGIN",
                reason="origin header is absent or malformed",
                stage="declared_identity_validation",
            )

        declared_origin_type, declared_origin_number = declared_origin

        # Validate the candidate against what it declared. This deliberately
        # happens before comparison with operation, source comment or target
        # identity of the incoming request.
        if not _cryptographically_complete_publication(
            body,
            repository=declared_repository,
            origin_type=declared_origin_type,
            origin_number=declared_origin_number,
            job_id=declared_job_id,
            request_digest=digest,
            target_sha=declared_target_sha,
        ):
            raise _declared_final_failure(
                comment_id=comment_id,
                category="CRYPTOGRAPHIC_OR_SCHEMA_INCONSISTENCY",
                reason=(
                    "declared final outcome failed manifest, bundle, embedded hash, "
                    "diagnostic digest or identity verification"
                ),
                stage="cryptographic_validation",
            )

        # Collision detection is keyed only by canonical repository + job_id.
        # No operation, origin, request comment, target or author field can
        # mask a different digest after the candidate is proven valid.
        if digest != request.digest_sha256:
            raise ArbitrationError(
                "CONFLICT_DIFFERENT_DIGEST: "
                + json.dumps(
                    {
                        "comment_id": comment_id,
                        "repository": request.repository,
                        "job_id": request.job_id,
                        "incumbent_request_sha256": digest,
                        "incoming_request_sha256": request.digest_sha256,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

        if (
            declared_origin_type != request.origin.type
            or declared_origin_number != request.origin.number
            or declared_target_sha != request.target_sha
            or not _candidate_matches_complete_identity(payload, request)
        ):
            raise _declared_final_failure(
                comment_id=comment_id,
                category="FULL_IDENTITY_MISMATCH",
                reason=(
                    "same-digest declared result does not match operation, origin, "
                    "source request comment or target identity"
                ),
                stage="complete_identity_validation",
            )

        valid_same_digest.append(
            FinalCandidate(
                comment_id=comment_id,
                html_url=str(comment.get("html_url", "")),
                body=body,
                body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                request_digest=digest,
                target_sha=declared_target_sha,
                created_at=(
                    comment.get("created_at")
                    if isinstance(comment.get("created_at"), str)
                    else None
                ),
            )
        )

    valid_same_digest.sort(key=lambda item: item.comment_id)
    incumbent = valid_same_digest[0] if valid_same_digest else None

    losers: tuple[DuplicateFinalOutcome, ...] = ()
    if incumbent is not None:
        losers = tuple(
            DuplicateFinalOutcome(
                comment_id=item.comment_id,
                classification="DUPLICATE_FINAL_OUTCOME",
                incumbent_comment_id=incumbent.comment_id,
                repository=request.repository,
                job_id=request.job_id,
                request_digest=item.request_digest,
                target_sha=item.target_sha,
                reason="larger_comment_id_than_deterministic_incumbent",
            )
            for item in valid_same_digest[1:]
        )

    return Election(incumbent, tuple(valid_same_digest), losers)


def _check_recorded_incumbent(output_root: Path, request: Any, election: Election) -> None:
    """Fail closed if a previously verified incumbent was edited or deleted."""

    job_root = output_root / request.job_id
    if not job_root.exists():
        return
    for receipt_path in sorted(job_root.glob("attempt-*/publication/receipt.json")):
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise ArbitrationError("REGISTRY_INTEGRITY_LOST: unreadable verified receipt")
        recorded_id = receipt.get("authoritative_comment_id", receipt.get("comment_id"))
        recorded_sha = receipt.get("authoritative_body_sha256")
        if not isinstance(recorded_id, int) or not isinstance(recorded_sha, str):
            continue
        match = next((item for item in election.valid if item.comment_id == recorded_id), None)
        if match is None or match.body_sha256 != recorded_sha:
            raise ArbitrationError("REGISTRY_INTEGRITY_LOST: recorded incumbent was edited or deleted")


def _decision_for_request(election: Election, request: Any) -> str:
    incumbent = election.incumbent
    if incumbent is None:
        return "ABSENT"
    if incumbent.request_digest != request.digest_sha256:
        return "CONFLICT_DIFFERENT_DIGEST"
    return "AUTHORITATIVE_SAME_DIGEST"


def _record_election_receipt(
    attempt: Any,
    request: Any,
    election: Election,
    *,
    state: str,
    posted_id: int | None = None,
) -> None:
    incumbent = election.incumbent
    if incumbent is None:
        raise ArbitrationError("cannot persist an election receipt without an incumbent")
    write_publication_receipt(
        attempt,
        {
            "state": state,
            "classification": (
                "DUPLICATE_FINAL_OUTCOME"
                if posted_id is not None and posted_id != incumbent.comment_id
                else "AUTHORITATIVE_FINAL_OUTCOME"
            ),
            "authoritative_comment_id": incumbent.comment_id,
            "authoritative_body_sha256": incumbent.body_sha256,
            "authoritative_html_url": incumbent.html_url,
            "posted_comment_id": posted_id,
            "duplicate_comment_ids": election.duplicate_ids,
            "duplicate_final_outcomes": [
                item.as_dict() for item in election.losers
            ],
            "request_comment_id": request.origin.request_comment_id,
            "request_sha256": request.digest_sha256,
        },
    )


def _recover_existing(output: Path, attempt: Any, gh: GhClient, request: Any) -> bool:
    election = _discover_candidates(gh, request)
    _check_recorded_incumbent(output, request, election)
    decision = _decision_for_request(election, request)
    if decision == "CONFLICT_DIFFERENT_DIGEST":
        raise ArbitrationError("CONFLICT_DIFFERENT_DIGEST: authoritative incumbent uses another digest")
    if decision == "AUTHORITATIVE_SAME_DIGEST":
        _record_election_receipt(attempt, request, election, state="RECOVERED_AUTHORITATIVE_OUTCOME")
        write_stop_receipt(
            attempt,
            {"state": "DISABLED_RECOVERY_ONLY", "reason": "Authoritative outcome reverified."},
        )
        print(
            f"AUTHORITATIVE_FINAL_OUTCOME: re-read and verified comment "
            f"{election.incumbent.comment_id}; no operation or POST performed."
        )
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.request.exists():
        print(f"Codespace Evidence Bridge: no launch descriptor at {args.request}; nothing to do.")
        return 0

    runner = CommandRunner()
    root = discover_repository_root(runner, Path.cwd())
    request_path = args.request if args.request.is_absolute() else root / args.request
    output = args.output_root if args.output_root.is_absolute() else root / args.output_root
    gh = GhClient(runner, root)
    request = None
    attempt = None
    failure_identity: dict[str, Any] = {}
    started = utc_now()

    try:
        _descriptor, request, _comment = load_and_verify_request(request_path, gh.fetch_request_comment)
        _claim_request(output, request.job_id, request.digest_sha256)
        attempt = allocate_attempt(output, request.job_id)
        preflight = gh.preflight(request.repository)

        if _recover_existing(output, attempt, gh, request):
            return 0

        primary_before = snapshot_primary_checkout(runner, root)
        target_before = gh.resolve_target(
            repository=request.repository,
            target_type=request.target_type,
            target_number=request.target_number,
            target_sha=request.target_sha,
        )
        if target_before.get("sha") != request.target_sha:
            result = _stale_before(request, target_before)
            target_after = target_before
        else:
            result = execute_operation(request, gh, runner)
            target_after = gh.resolve_target(
                repository=request.repository,
                target_type=request.target_type,
                target_number=request.target_number,
                target_sha=request.target_sha,
            )
            _apply_stale_after(request, result, target_after)

        environment = collect_environment(runner, root)
        checkout = compare_snapshots(primary_before, snapshot_primary_checkout(runner, root))
        if not checkout["unchanged"]:
            result.status = "FAILED"
            result.classification = "FAIL_HARNESS"
            result.missing_proof = sorted(set([*result.missing_proof, "PRIMARY_CHECKOUT_CHANGED"]))
            result.summary += " Primary checkout changed; publication is diagnostic only."

        facts = _facts(
            request, attempt, result, started, target_before, target_after, checkout, preflight, runner
        )
        preview = preview_capsule_size(facts=facts, summary=result.summary, artifacts=result.artifacts)
        oversize = preview > PUBLICATION_LIMIT_BYTES
        if oversize:
            result.classification = "INCONCLUSIVE"
            result.missing_proof = sorted(set([*result.missing_proof, "DURABLE_CAPSULE_OVERSIZE"]))
            result.summary += (
                f" Required capsule is {preview} UTF-8 bytes; limit is {PUBLICATION_LIMIT_BYTES}."
            )
            facts = _facts(
                request,
                attempt,
                result,
                started,
                target_before,
                target_after,
                checkout,
                preflight,
                runner,
                1024,
            )

        write_bundle_files(
            attempt,
            facts=facts,
            summary=result.summary,
            runner=runner,
            environment=environment,
            artifacts=result.artifacts,
        )
        sealed = seal_bundle(attempt)
        body = (
            render_oversize_diagnostic(
                facts=facts,
                manifest_sha256=sealed.manifest_sha256,
                bundle_sha256=sealed.bundle_sha256,
            )
            if oversize
            else render_capsule(
                facts=facts,
                summary=result.summary,
                manifest_sha256=sealed.manifest_sha256,
                bundle_sha256=sealed.bundle_sha256,
                artifact_digests=sealed.artifact_digests,
                diff_content=result.artifacts.get("diff.patch"),
            )
        )
        ensure_publication_budget(body)

        # A concurrent client may have published while this read-only operation ran.
        before_post = _discover_candidates(gh, request)
        _check_recorded_incumbent(output, request, before_post)
        before_post_decision = _decision_for_request(before_post, request)
        if before_post_decision == "CONFLICT_DIFFERENT_DIGEST":
            raise ArbitrationError("CONFLICT_DIFFERENT_DIGEST: incumbent appeared before POST")
        if before_post_decision == "AUTHORITATIVE_SAME_DIGEST":
            _record_election_receipt(
                attempt, request, before_post, state="CONCURRENT_AUTHORITATIVE_OUTCOME_REUSED"
            )
            write_stop_receipt(
                attempt,
                {"state": "DISABLED_DUPLICATE_FINAL_OUTCOME", "classification": "DUPLICATE_FINAL_OUTCOME"},
            )
            print("DUPLICATE_FINAL_OUTCOME: concurrent authoritative outcome reused; no POST performed.")
            return 0

        # Required immediate SHA resolution: no unrelated GitHub call may occur between
        # this successful check and the POST below.
        publication_target = gh.resolve_target(
            repository=request.repository,
            target_type=request.target_type,
            target_number=request.target_number,
            target_sha=request.target_sha,
        )
        if publication_target.get("sha") != request.target_sha:
            failure = {
                "state": "TARGET_MOVED_IMMEDIATELY_BEFORE_PUBLICATION",
                "status": "FAILED",
                "classification": "STALE_AFTER_EXECUTION",
                "requested_sha": request.target_sha,
                "observed_sha": publication_target.get("sha"),
            }
            write_publication_failure(attempt, failure)
            write_stop_receipt(
                attempt,
                {"state": "DISABLED_TARGET_MOVED_BEFORE_PUBLICATION", "classification": "STALE_AFTER_EXECUTION"},
            )
            print(
                f"STALE_AFTER_EXECUTION: target moved immediately before publication: "
                f"requested {request.target_sha}, observed {publication_target.get('sha')}; no comment posted.",
                file=sys.stderr,
            )
            return 1

        posted: PublicationResult | None = None
        try:
            posted = gh.publish_comment(
                repository=request.repository,
                origin_number=request.origin.number,
                body=body,
            )
        except GitHubError:
            # A timeout may hide a successful POST. Only exhaustive cryptographic reread
            # may convert that ambiguity into success.
            ambiguous = _discover_candidates(gh, request)
            _check_recorded_incumbent(output, request, ambiguous)
            if _decision_for_request(ambiguous, request) != "AUTHORITATIVE_SAME_DIGEST":
                raise
            _record_election_receipt(
                attempt, request, ambiguous, state="RECOVERED_AFTER_AMBIGUOUS_POST"
            )
            write_stop_receipt(
                attempt,
                {"state": "DISABLED_AMBIGUOUS_POST_RECOVERY", "classification": "AUTHORITATIVE_FINAL_OUTCOME"},
            )
            print("AUTHORITATIVE_FINAL_OUTCOME: recovered by exhaustive reread after ambiguous POST.")
            return 0

        gh.verify_publication(
            repository=request.repository,
            origin_number=request.origin.number,
            result=posted,
            expected_body=body,
            required_fragments=_required_fragments(
                facts, sealed.manifest_sha256, sealed.bundle_sha256
            ),
        )

        # POST success is not authority. Exhaustively reread the exact origin and elect
        # the smallest cryptographically valid comment_id after convergence.
        election = _discover_candidates(gh, request)
        _check_recorded_incumbent(output, request, election)
        decision = _decision_for_request(election, request)
        if decision == "CONFLICT_DIFFERENT_DIGEST":
            raise ArbitrationError("CONFLICT_DIFFERENT_DIGEST: another digest won final election")
        if decision != "AUTHORITATIVE_SAME_DIGEST" or election.incumbent is None:
            raise ArbitrationError("publication did not produce a cryptographically valid incumbent")
        if not any(item.comment_id == posted.comment_id for item in election.valid):
            raise ArbitrationError("posted comment absent or invalid during authoritative reread")

        lost = posted.comment_id != election.incumbent.comment_id
        _record_election_receipt(
            attempt,
            request,
            election,
            state="POSTED_AND_ELECTED" if not lost else "POSTED_BUT_LOST_DETERMINISTIC_ELECTION",
            posted_id=posted.comment_id,
        )

        stop_eligible = not lost and not oversize and result.status == "COMPLETED"
        stop_receipt = (
            stop_current_codespace(
                runner,
                repository_root=root,
                repository=request.repository,
                publication_verified=True,
            )
            if args.stop_after_success and stop_eligible
            else {
                "state": (
                    "NOT_REQUESTED"
                    if not args.stop_after_success
                    else "DISABLED_OUTCOME_NOT_STOP_ELIGIBLE"
                ),
                "status": result.status,
                "classification": "DUPLICATE_FINAL_OUTCOME" if lost else result.classification,
            }
        )
        write_stop_receipt(attempt, stop_receipt)
        if lost:
            print(
                f"DUPLICATE_FINAL_OUTCOME: comment {posted.comment_id} lost to authoritative "
                f"comment {election.incumbent.comment_id}."
            )
            return 0
        print(
            f"{result.classification}: authoritative outcome {election.incumbent.html_url}; "
            f"attempt {attempt.number}."
        )
        return 0 if result.status == "COMPLETED" and result.classification != "INCONCLUSIVE" else 1

    except Exception as exc:
        if attempt is None:
            attempt, failure_identity = _unbound_attempt(output, request_path)
        if attempt is not None:
            try:
                _write_classified_failure(
                    attempt=attempt,
                    request=request,
                    identity=failure_identity,
                    exc=exc,
                    started=started,
                    runner=runner,
                )
            except Exception:
                pass
        print(f"HOLD: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
