"""Immutable evidence bundles, bounded capsules and separate receipts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from . import CLASSIFICATIONS, OUTCOME_MARKER, OUTCOME_SCHEMA_VERSION, PUBLICATION_LIMIT_BYTES, STATEMENT
from .execute import CommandRunner, redact_value

ATTEMPT_RE = re.compile(r"^attempt-(\d{3})$")


class OutcomeError(RuntimeError):
    """Evidence could not be sealed or rendered safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def _write_once(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


@dataclass(frozen=True)
class AttemptPaths:
    root: Path
    bundle: Path
    publication: Path
    stop: Path
    number: int


@dataclass(frozen=True)
class SealedBundle:
    attempt: AttemptPaths
    manifest_sha256: str
    bundle_sha256: str
    artifact_digests: dict[str, str]


def allocate_attempt(output_root: Path, job_id: str) -> AttemptPaths:
    job_root = output_root / job_id
    job_root.mkdir(parents=True, exist_ok=True)
    seen = [int(match.group(1)) for child in job_root.iterdir() if (match := ATTEMPT_RE.fullmatch(child.name))]
    number = max(seen, default=0) + 1
    if number > 999:
        raise OutcomeError("attempt limit exceeded")
    root = job_root / f"attempt-{number:03d}"
    root.mkdir(mode=0o700)
    bundle, publication, stop = root / "bundle", root / "publication", root / "stop"
    for path in (bundle, publication, stop):
        path.mkdir(mode=0o700)
    return AttemptPaths(root, bundle, publication, stop, number)


def build_facts(
    *, request: Any, attempt: int, status: str, classification: str,
    started_at: str, completed_at: str, target_before: Mapping[str, Any],
    target_after: Mapping[str, Any], operation_facts: Mapping[str, Any],
    missing_proof: list[str], checkout_proof: Mapping[str, Any],
    preflight: Mapping[str, Any], commands: list[dict[str, Any]],
) -> dict[str, Any]:
    if classification not in CLASSIFICATIONS:
        raise OutcomeError(f"forbidden classification: {classification}")
    facts = {
        "schema_version": OUTCOME_SCHEMA_VERSION,
        "marker": OUTCOME_MARKER,
        "job_id": request.job_id,
        "attempt": attempt,
        "request_sha256": request.digest_sha256,
        "operation": request.operation,
        "repository": request.repository,
        "origin": {"type": request.origin.type, "number": request.origin.number,
                   "request_comment_id": request.origin.request_comment_id},
        "target": {"type": request.target_type, "number": request.target_number,
                   "requested_sha": request.target_sha, "resolved_before": dict(target_before),
                   "resolved_after": dict(target_after),
                   "stale_before": target_before.get("sha") != request.target_sha,
                   "stale_after": target_after.get("sha") != request.target_sha},
        "status": status,
        "classification": classification,
        "started_at": started_at,
        "completed_at": completed_at,
        "commands": commands,
        "facts": dict(operation_facts),
        "missing_proof": sorted(set(missing_proof)),
        "primary_checkout": dict(checkout_proof),
        "github_preflight": dict(preflight),
        "statement": STATEMENT,
    }
    text = json.dumps(facts, ensure_ascii=False)
    if "GOVERNANCE_DECISION" in text:
        raise OutcomeError("ordinary evidence must not contain GOVERNANCE_DECISION")
    return redact_value(facts)


def write_bundle_files(
    attempt: AttemptPaths, *, facts: Mapping[str, Any], summary: str,
    runner: CommandRunner, environment: Mapping[str, Any], artifacts: Mapping[str, str],
) -> None:
    _write_once(attempt.bundle / "facts.json", _json(facts))
    _write_once(attempt.bundle / "summary.md", summary.rstrip() + "\n")
    _write_once(attempt.bundle / "commands.json", _json(runner.records_summary(excerpt_bytes=0)))
    _write_once(attempt.bundle / "stdout.log", runner.combined_stdout())
    _write_once(attempt.bundle / "stderr.log", runner.combined_stderr())
    _write_once(attempt.bundle / "environment.json", _json(redact_value(environment)))
    for name, content in sorted(artifacts.items()):
        if not name or "/" in name or "\\" in name or name == "manifest.sha256":
            raise OutcomeError(f"unsafe artifact name: {name!r}")
        _write_once(attempt.bundle / name, str(content))


def seal_bundle(attempt: AttemptPaths) -> SealedBundle:
    files = sorted(path for path in attempt.bundle.iterdir() if path.is_file() and path.name != "manifest.sha256")
    if not files:
        raise OutcomeError("cannot seal an empty bundle")
    digests = {path.name: _sha(path.read_bytes()) for path in files}
    manifest_text = "".join(f"{digest}  {name}\n" for name, digest in sorted(digests.items()))
    _write_once(attempt.bundle / "manifest.sha256", manifest_text)
    for name, digest in digests.items():
        if _sha((attempt.bundle / name).read_bytes()) != digest:
            raise OutcomeError(f"digest verification failed for {name}")
    manifest_sha = _sha(manifest_text.encode("utf-8"))
    bundle_sha = _sha((manifest_sha + "\n" + manifest_text).encode("utf-8"))
    for path in [*files, attempt.bundle / "manifest.sha256"]:
        path.chmod(0o400)
    attempt.bundle.chmod(0o500)
    return SealedBundle(attempt, manifest_sha, bundle_sha, digests)


def _header(facts: Mapping[str, Any], manifest_sha: str, bundle_sha: str, completion: str) -> str:
    return (
        f"{OUTCOME_MARKER}\njob_id: {facts['job_id']}\nattempt: {facts['attempt']}\n"
        f"request_sha256: {facts['request_sha256']}\noperation: {facts['operation']}\n"
        f"repository: {facts['repository']}\norigin: {facts['origin']['type']}#{facts['origin']['number']}\n"
        f"target_sha: {facts['target']['requested_sha']}\nstatus: {facts['status']}\n"
        f"classification: {facts['classification']}\nmanifest_sha256: {manifest_sha}\n"
        f"bundle_sha256: {bundle_sha}\ncompletion_state: {completion}\n\n"
    )


def render_capsule(
    *, facts: Mapping[str, Any], summary: str, manifest_sha256: str,
    bundle_sha256: str, artifact_digests: Mapping[str, str], diff_content: str | None,
) -> str:
    payload: dict[str, Any] = {
        "facts": facts, "summary": summary,
        "sealed_bundle": {"manifest_sha256": manifest_sha256, "bundle_sha256": bundle_sha256,
                          "artifact_sha256": dict(sorted(artifact_digests.items()))},
    }
    if diff_content is not None:
        payload["required_diff"] = diff_content
    return _header(facts, manifest_sha256, bundle_sha256, "FINAL_SEALED") + "```json\n" + json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n```\n\n" + STATEMENT + "\n"


def preview_capsule_size(*, facts: Mapping[str, Any], summary: str, artifacts: Mapping[str, str]) -> int:
    digests = {name: _sha(str(content).encode("utf-8")) for name, content in artifacts.items()}
    body = render_capsule(facts=facts, summary=summary, manifest_sha256="0" * 64,
                          bundle_sha256="0" * 64, artifact_digests=digests,
                          diff_content=artifacts.get("diff.patch"))
    return len(body.encode("utf-8"))


def render_oversize_diagnostic(*, facts: Mapping[str, Any], manifest_sha256: str, bundle_sha256: str) -> str:
    diagnostic = {"job_id": facts["job_id"], "attempt": facts["attempt"],
                  "request_sha256": facts["request_sha256"], "target_sha": facts["target"]["requested_sha"],
                  "classification": "INCONCLUSIVE", "reason": "DURABLE_CAPSULE_OVERSIZE",
                  "manifest_sha256": manifest_sha256, "bundle_sha256": bundle_sha256, "statement": STATEMENT}
    copy = dict(facts)
    copy["classification"] = "INCONCLUSIVE"
    body = _header(copy, manifest_sha256, bundle_sha256, "FINAL_DIAGNOSTIC_ONLY") + "reason: DURABLE_CAPSULE_OVERSIZE\n\n```json\n" + json.dumps(
        diagnostic, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n```\n\n" + STATEMENT + "\n"
    ensure_publication_budget(body)
    return body


def ensure_publication_budget(body: str) -> None:
    size = len(body.encode("utf-8"))
    if size > PUBLICATION_LIMIT_BYTES:
        raise OutcomeError(f"publication is {size} bytes; limit is {PUBLICATION_LIMIT_BYTES}")


def _receipt(directory: Path, name: str, value: Mapping[str, Any]) -> Path:
    path = directory / name
    _write_once(path, _json(redact_value({**value, "recorded_at": utc_now()})), mode=0o400)
    return path


def write_publication_receipt(attempt: AttemptPaths, receipt: Mapping[str, Any]) -> Path:
    return _receipt(attempt.publication, "receipt.json", receipt)


def write_publication_failure(attempt: AttemptPaths, failure: Mapping[str, Any]) -> Path:
    return _receipt(attempt.publication, "failure.json", failure)


def write_stop_receipt(attempt: AttemptPaths, receipt: Mapping[str, Any]) -> Path:
    return _receipt(attempt.stop, "receipt.json", receipt)
