#!/usr/bin/env python3
"""Execute one verified Gate 0 evidence request."""

from __future__ import annotations

import argparse
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
from tools.codespace_evidence.github import GhClient, GitHubError
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


def _claim_request(output_root: Path, job_id: str, request_digest: str) -> bool:
    """Atomically bind one job ID to one digest and permit only its first execution."""

    job_root = output_root / job_id
    job_root.mkdir(parents=True, exist_ok=True)
    claim_path = job_root / "request.sha256"
    payload = request_digest + "\n"
    try:
        fd = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = claim_path.read_text(encoding="utf-8").strip()
        if existing != request_digest:
            raise RuntimeError("job_id is already bound to a different request digest")
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
    if isinstance(exc, (GitHubError, FileNotFoundError, ConnectionError, TimeoutError)):
        return "FAIL_ENVIRONMENT"
    return "FAIL_HARNESS"


def _unbound_attempt(output: Path, descriptor_path: Path) -> tuple[Any | None, dict[str, Any]]:
    """Allocate deterministic local evidence when GitHub cannot bind the request.

    A valid launch descriptor contains no job ID, so an origin-scoped synthetic ID
    is used only for the pre-binding failure record. It is never published as a
    verified request outcome.
    """

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
            {
                "state": "DISABLED_NOT_DURABLY_VERIFIED",
                "classification": classification,
            },
        )


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
        first_claim = _claim_request(output, request.job_id, request.digest_sha256)
        if first_claim:
            # The first claimant allocates before preflight so missing gh/auth/network/private
            # repository access still leaves one immutable classified local attempt.
            attempt = allocate_attempt(output, request.job_id)
        preflight = gh.preflight(request.repository)
        existing = gh.find_existing_final_publication(
            repository=request.repository,
            origin_type=request.origin.type,
            origin_number=request.origin.number,
            job_id=request.job_id,
            request_digest=request.digest_sha256,
            target_sha=request.target_sha,
        )
        if existing is not None:
            if attempt is not None:
                write_publication_receipt(
                    attempt,
                    {
                        "state": "RECOVERED_AND_REVERIFIED_EXISTING_PUBLICATION",
                        "comment_id": existing.get("id"),
                        "html_url": existing.get("html_url"),
                        "request_comment_id": request.origin.request_comment_id,
                        "request_sha256": request.digest_sha256,
                        "body_bytes": len(str(existing.get("body", "")).encode("utf-8")),
                    },
                )
                write_stop_receipt(
                    attempt,
                    {
                        "state": "DISABLED_RECOVERY_ONLY",
                        "reason": "Existing publication was reverified; no new operation executed.",
                    },
                )
            print(f"Existing sealed publication for {request.job_id} was re-read and verified; no duplicate posted.")
            return 0
        if not first_claim:
            raise RuntimeError(
                "strict idempotence: this job_id and request digest were already claimed "
                "without a verified final publication; submit a new job_id"
            )
        assert attempt is not None

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
            request,
            attempt,
            result,
            started,
            target_before,
            target_after,
            checkout,
            preflight,
            runner,
        )
        preview = preview_capsule_size(facts=facts, summary=result.summary, artifacts=result.artifacts)
        oversize = preview > PUBLICATION_LIMIT_BYTES
        if oversize:
            result.classification = "INCONCLUSIVE"
            result.missing_proof = sorted(set([*result.missing_proof, "DURABLE_CAPSULE_OVERSIZE"]))
            result.summary += (
                f" Required capsule is {preview} UTF-8 bytes; "
                f"limit is {PUBLICATION_LIMIT_BYTES}."
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
                {
                    "state": "DISABLED_TARGET_MOVED_BEFORE_PUBLICATION",
                    "classification": "STALE_AFTER_EXECUTION",
                },
            )
            print(
                f"STALE_AFTER_EXECUTION: target moved immediately before publication: "
                f"requested {request.target_sha}, observed {publication_target.get('sha')}; no comment posted.",
                file=sys.stderr,
            )
            return 1

        posted = gh.publish_comment(
            repository=request.repository,
            origin_number=request.origin.number,
            body=body,
        )
        receipt = gh.verify_publication(
            repository=request.repository,
            origin_number=request.origin.number,
            result=posted,
            expected_body=body,
            required_fragments=_required_fragments(
                facts,
                sealed.manifest_sha256,
                sealed.bundle_sha256,
            ),
        )
        write_publication_receipt(
            attempt,
            {
                **receipt,
                "request_comment_id": request.origin.request_comment_id,
                "request_sha256": request.digest_sha256,
                "manifest_sha256": sealed.manifest_sha256,
                "bundle_sha256": sealed.bundle_sha256,
            },
        )

        stop_eligible = not oversize and result.status == "COMPLETED"
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
                "classification": result.classification,
            }
        )
        write_stop_receipt(attempt, stop_receipt)
        print(f"{result.classification}: published and verified {posted.html_url}; attempt {attempt.number}.")
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
