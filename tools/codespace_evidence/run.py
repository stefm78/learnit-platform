#!/usr/bin/env python3
"""Execute one verified Gate 0 evidence request."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.codespace_evidence import PUBLICATION_LIMIT_BYTES, STATEMENT
from tools.codespace_evidence.execute import CommandRunner, collect_environment, utc_now
from tools.codespace_evidence.github import GhClient
from tools.codespace_evidence.operations import OperationResult, execute_operation
from tools.codespace_evidence.outcome import (
    allocate_attempt, build_facts, ensure_publication_budget, preview_capsule_size,
    render_capsule, render_oversize_diagnostic, seal_bundle, write_bundle_files,
    write_publication_failure, write_publication_receipt, write_stop_receipt,
)
from tools.codespace_evidence.request import load_and_verify_request
from tools.codespace_evidence.stop import stop_current_codespace
from tools.codespace_evidence.workspace import compare_snapshots, discover_repository_root, snapshot_primary_checkout

DEFAULT_REQUEST = Path(".codespace-evidence/request.json")
DEFAULT_OUTPUT = Path(".agent-result/codespace-evidence")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stop-after-success", action="store_true")
    return parser.parse_args(argv)


def _stale_before(request: Any, observed: dict[str, Any]) -> OperationResult:
    return OperationResult(
        "FAILED", "STALE_TARGET",
        {"requested_sha": request.target_sha, "observed_sha": observed.get("sha"), "operation_executed": False},
        ["TARGET_MOVED_BEFORE_EXECUTION"], {},
        f"Target moved before execution: requested {request.target_sha}, observed {observed.get('sha')}. No operation ran.",
    )


def _apply_stale_after(request: Any, result: OperationResult, observed: dict[str, Any]) -> None:
    if observed.get("sha") == request.target_sha:
        return
    result.status = "FAILED"
    result.classification = "STALE_AFTER_EXECUTION"
    result.missing_proof = sorted(set([*result.missing_proof, "TARGET_MOVED_AFTER_EXECUTION"]))
    result.facts = {**result.facts, "stale_after_execution": {
        "requested_sha": request.target_sha, "observed_sha": observed.get("sha")}}
    result.summary += " Target moved after execution; facts are diagnostic only."


def _required_fragments(facts: dict[str, Any], manifest: str, bundle: str) -> list[str]:
    return [
        "AI_CODESPACE_OUTCOME_V1\n", f"job_id: {facts['job_id']}\n",
        f"attempt: {facts['attempt']}\n", f"request_sha256: {facts['request_sha256']}\n",
        f"repository: {facts['repository']}\n",
        f"origin: {facts['origin']['type']}#{facts['origin']['number']}\n",
        f"target_sha: {facts['target']['requested_sha']}\n",
        f"manifest_sha256: {manifest}\n", f"bundle_sha256: {bundle}\n", STATEMENT,
    ]


def _facts(request: Any, attempt: Any, result: OperationResult, started: str,
           before: dict[str, Any], after: dict[str, Any], checkout: dict[str, Any],
           preflight: dict[str, Any], runner: CommandRunner, excerpt: int = 4096) -> dict[str, Any]:
    return build_facts(
        request=request, attempt=attempt.number, status=result.status,
        classification=result.classification, started_at=started, completed_at=utc_now(),
        target_before=before, target_after=after, operation_facts=result.facts,
        missing_proof=result.missing_proof, checkout_proof=checkout, preflight=preflight,
        commands=runner.records_summary(excerpt_bytes=excerpt),
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
    started = utc_now()

    try:
        _descriptor, request, _comment = load_and_verify_request(request_path, gh.fetch_request_comment)
        preflight = gh.preflight(request.repository)
        existing = gh.find_existing_final_publication(
            repository=request.repository, origin_type=request.origin.type,
            origin_number=request.origin.number, job_id=request.job_id,
            request_digest=request.digest_sha256, target_sha=request.target_sha,
        )
        if existing is not None and not request.allow_new_attempt:
            print(f"Existing sealed publication for {request.job_id}; no duplicate posted.")
            return 0

        attempt = allocate_attempt(output, request.job_id)
        primary_before = snapshot_primary_checkout(runner, root)
        target_before = gh.resolve_target(
            repository=request.repository, target_type=request.target_type,
            target_number=request.target_number, target_sha=request.target_sha,
        )
        if target_before.get("sha") != request.target_sha:
            result = _stale_before(request, target_before)
            target_after = target_before
        else:
            result = execute_operation(request, gh, runner)
            target_after = gh.resolve_target(
                repository=request.repository, target_type=request.target_type,
                target_number=request.target_number, target_sha=request.target_sha,
            )
            _apply_stale_after(request, result, target_after)

        environment = collect_environment(runner, root)
        checkout = compare_snapshots(primary_before, snapshot_primary_checkout(runner, root))
        if not checkout["unchanged"]:
            result.status = "FAILED"
            result.classification = "FAIL_HARNESS"
            result.missing_proof = sorted(set([*result.missing_proof, "PRIMARY_CHECKOUT_CHANGED"]))
            result.summary += " Primary checkout changed; publication is diagnostic only."

        facts = _facts(request, attempt, result, started, target_before, target_after, checkout, preflight, runner)
        preview = preview_capsule_size(facts=facts, summary=result.summary, artifacts=result.artifacts)
        oversize = preview > PUBLICATION_LIMIT_BYTES
        if oversize:
            result.classification = "INCONCLUSIVE"
            result.missing_proof = sorted(set([*result.missing_proof, "DURABLE_CAPSULE_OVERSIZE"]))
            result.summary += f" Required capsule is {preview} UTF-8 bytes; limit is {PUBLICATION_LIMIT_BYTES}."
            facts = _facts(request, attempt, result, started, target_before, target_after, checkout, preflight, runner, 1024)

        write_bundle_files(attempt, facts=facts, summary=result.summary, runner=runner,
                           environment=environment, artifacts=result.artifacts)
        sealed = seal_bundle(attempt)
        body = render_oversize_diagnostic(
            facts=facts, manifest_sha256=sealed.manifest_sha256, bundle_sha256=sealed.bundle_sha256,
        ) if oversize else render_capsule(
            facts=facts, summary=result.summary, manifest_sha256=sealed.manifest_sha256,
            bundle_sha256=sealed.bundle_sha256, artifact_digests=sealed.artifact_digests,
            diff_content=result.artifacts.get("diff.patch"),
        )
        ensure_publication_budget(body)

        posted = gh.publish_comment(repository=request.repository, origin_number=request.origin.number, body=body)
        receipt = gh.verify_publication(
            repository=request.repository, origin_number=request.origin.number, result=posted,
            expected_body=body, required_fragments=_required_fragments(
                facts, sealed.manifest_sha256, sealed.bundle_sha256),
        )
        write_publication_receipt(attempt, {
            **receipt, "request_comment_id": request.origin.request_comment_id,
            "request_sha256": request.digest_sha256,
            "manifest_sha256": sealed.manifest_sha256, "bundle_sha256": sealed.bundle_sha256,
        })

        stop_eligible = not oversize and result.status == "COMPLETED"
        stop_receipt = stop_current_codespace(
            runner, repository_root=root, repository=request.repository, publication_verified=True,
        ) if args.stop_after_success and stop_eligible else {
            "state": "NOT_REQUESTED" if not args.stop_after_success else "DISABLED_OUTCOME_NOT_STOP_ELIGIBLE",
            "status": result.status, "classification": result.classification,
        }
        write_stop_receipt(attempt, stop_receipt)
        print(f"{result.classification}: published and verified {posted.html_url}; attempt {attempt.number}.")
        return 0 if result.status == "COMPLETED" and result.classification != "INCONCLUSIVE" else 1

    except Exception as exc:
        if attempt is not None:
            try:
                write_publication_failure(attempt, {
                    "state": "PUBLICATION_FAILED_OR_EXECUTION_ABORTED",
                    "error_type": type(exc).__name__, "error": str(exc),
                })
                write_stop_receipt(attempt, {"state": "DISABLED_NOT_DURABLY_VERIFFED"})
            except Exception:
                pass
        print(f"HOLD: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
