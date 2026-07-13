#!/usr/bin/env python3
"""Validate the minimum Learn-it repository governance contract.

This validator intentionally uses only the Python standard library so the
bootstrap repository can be checked before a dependency toolchain exists.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "SECURITY.md",
    ".gitignore",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/work-package.yml",
    "governance/governor-state.json",
    "work-packages/ARC-WP-000.json",
    "work-packages/GOV-WP-001.json",
    "docs/architecture/README.md",
    "docs/governance/DECISION_RIGHTS.md",
    "docs/governance/GOVERNOR_REVIEW_TEMPLATE.md",
    "docs/roadmap/STANDALONE_TO_PLATFORM.md",
)

ALLOWED_STATUSES = {
    "proposed",
    "proposed-blocked",
    "challenged",
    "approved",
    "in-progress",
    "under-qa",
    "human-gate",
    "accepted",
    "rejected",
    "superseded",
}

ALLOWED_GOVERNOR_DECISIONS = {"GO", "GO_WITH_CONDITIONS", "HOLD", "NO_GO"}
ALLOWED_PHASE_STATUSES = {"planned", "active", "blocked", "complete", "superseded"}
ALLOWED_BASELINE_STATUSES = {"not-selected", "selected", "imported", "promoted", "superseded"}
ALLOWED_RISK_SEVERITIES = {"low", "moderate", "high", "critical"}

BROAD_GLOBS = {"*", "**", "**/*", ".", "./**", "/**"}
WORK_PACKAGE_ID = re.compile(r"^[A-Z][A-Z0-9-]*-WP-[0-9]{3,}$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def read_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(errors, f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return None


def require_string(value: Any, field: str, owner: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        fail(errors, f"{owner}: {field} is required")
        return None
    return value.strip()


def require_string_list(
    value: Any, field: str, owner: str, errors: list[str], *, allow_empty: bool = False
) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a list" if allow_empty else "a non-empty list"
        fail(errors, f"{owner}: {field} must be {qualifier}")
        return []
    invalid = [entry for entry in value if not isinstance(entry, str) or not entry.strip()]
    if invalid:
        fail(errors, f"{owner}: {field} contains invalid entries")
    return [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]


def validate_work_package(path: Path, seen_ids: set[str], errors: list[str]) -> None:
    payload = read_json(path, errors)
    if payload is None:
        return

    if not isinstance(payload, dict):
        fail(errors, f"{path.relative_to(ROOT)}: root must be an object")
        return

    package_id = payload.get("id")
    if not isinstance(package_id, str) or not WORK_PACKAGE_ID.fullmatch(package_id):
        fail(errors, f"{path.relative_to(ROOT)}: invalid work package id")
        package_id = path.stem
    elif package_id in seen_ids:
        fail(errors, f"duplicate work package id: {package_id}")
    else:
        seen_ids.add(package_id)

    if path.stem != package_id:
        fail(errors, f"{package_id}: filename must be {package_id}.json")

    if payload.get("schemaVersion") != 1:
        fail(errors, f"{package_id}: schemaVersion must equal 1")

    status = payload.get("status")
    if status not in ALLOWED_STATUSES:
        fail(errors, f"{package_id}: unsupported status {status!r}")

    for field in ("title", "purpose", "rollback"):
        require_string(payload.get(field), field, package_id, errors)

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        fail(errors, f"{package_id}: scope must be an object")
        scope = {}

    allowed = require_string_list(scope.get("allowedPaths"), "scope.allowedPaths", package_id, errors)
    forbidden = require_string_list(
        scope.get("forbiddenPaths"), "scope.forbiddenPaths", package_id, errors
    )

    for pattern in allowed:
        if pattern in BROAD_GLOBS:
            fail(errors, f"{package_id}: forbidden overbroad allowed path {pattern!r}")
        if pattern.startswith("/") or ".." in Path(pattern).parts:
            fail(errors, f"{package_id}: allowed path must be repository-relative: {pattern!r}")

    overlap = sorted(set(allowed) & set(forbidden))
    if overlap:
        fail(errors, f"{package_id}: paths are both allowed and forbidden: {overlap}")

    for field in (
        "invariants",
        "requiredEvidence",
        "adversarialTests",
        "nonGoals",
        "independentReview",
    ):
        require_string_list(payload.get(field), field, package_id, errors)

    baseline = payload.get("baseline")
    if not isinstance(baseline, dict):
        fail(errors, f"{package_id}: baseline must be an object")
        baseline = {}

    base_commit = baseline.get("baseCommit")
    artifact_sha = baseline.get("artifactSha256")
    blocked_status = status in {"proposed", "proposed-blocked", "challenged"}

    if blocked_status:
        if base_commit is not None and not FULL_SHA.fullmatch(str(base_commit)):
            fail(errors, f"{package_id}: baseCommit must be null or a full 40-character SHA")
    else:
        if not isinstance(base_commit, str) or not FULL_SHA.fullmatch(base_commit):
            fail(errors, f"{package_id}: executable status requires a full baseCommit SHA")

    if artifact_sha is not None and not SHA256.fullmatch(str(artifact_sha)):
        fail(errors, f"{package_id}: artifactSha256 must be null or 64 lowercase hex characters")


def validate_governor_state(path: Path, errors: list[str]) -> None:
    payload = read_json(path, errors)
    owner = "governor-state"
    if payload is None:
        return
    if not isinstance(payload, dict):
        fail(errors, f"{owner}: root must be an object")
        return

    if payload.get("schemaVersion") != 1:
        fail(errors, f"{owner}: schemaVersion must equal 1")

    for field in ("repository", "stateId", "accountableOwner", "operatingModel"):
        require_string(payload.get(field), field, owner, errors)

    effective_commit = payload.get("effectiveFromCommit")
    if not isinstance(effective_commit, str) or not FULL_SHA.fullmatch(effective_commit):
        fail(errors, f"{owner}: effectiveFromCommit must be a full 40-character SHA")

    phase = payload.get("currentPhase")
    if not isinstance(phase, dict):
        fail(errors, f"{owner}: currentPhase must be an object")
        phase = {}
    require_string(phase.get("id"), "currentPhase.id", owner, errors)
    require_string(phase.get("description"), "currentPhase.description", owner, errors)
    if phase.get("status") not in ALLOWED_PHASE_STATUSES:
        fail(errors, f"{owner}: unsupported currentPhase.status {phase.get('status')!r}")

    baseline = payload.get("promotedBaseline")
    if not isinstance(baseline, dict):
        fail(errors, f"{owner}: promotedBaseline must be an object")
        baseline = {}
    if baseline.get("status") not in ALLOWED_BASELINE_STATUSES:
        fail(errors, f"{owner}: unsupported promotedBaseline.status {baseline.get('status')!r}")
    work_package = baseline.get("workPackage")
    if not isinstance(work_package, str) or not WORK_PACKAGE_ID.fullmatch(work_package):
        fail(errors, f"{owner}: promotedBaseline.workPackage must be a valid work-package id")
    source_commit = baseline.get("sourceCommit")
    if source_commit is not None and not FULL_SHA.fullmatch(str(source_commit)):
        fail(errors, f"{owner}: promotedBaseline.sourceCommit must be null or a full SHA")
    artifact_sha = baseline.get("artifactSha256")
    if artifact_sha is not None and not SHA256.fullmatch(str(artifact_sha)):
        fail(errors, f"{owner}: promotedBaseline.artifactSha256 must be null or a SHA-256")

    authorized = require_string_list(payload.get("authorizedWork"), "authorizedWork", owner, errors)
    held = require_string_list(payload.get("heldWork"), "heldWork", owner, errors)
    prohibited = require_string_list(payload.get("prohibitedWork"), "prohibitedWork", owner, errors)

    overlaps = {
        "authorized/held": sorted(set(authorized) & set(held)),
        "authorized/prohibited": sorted(set(authorized) & set(prohibited)),
        "held/prohibited": sorted(set(held) & set(prohibited)),
    }
    for label, entries in overlaps.items():
        if entries:
            fail(errors, f"{owner}: contradictory exact entries in {label}: {entries}")

    risks = payload.get("activeRisks")
    if not isinstance(risks, list):
        fail(errors, f"{owner}: activeRisks must be a list")
        risks = []
    risk_ids: set[str] = set()
    for index, risk in enumerate(risks):
        prefix = f"{owner}: activeRisks[{index}]"
        if not isinstance(risk, dict):
            fail(errors, f"{prefix} must be an object")
            continue
        risk_id = require_string(risk.get("id"), "id", prefix, errors)
        if risk_id:
            if risk_id in risk_ids:
                fail(errors, f"{owner}: duplicate risk id {risk_id}")
            risk_ids.add(risk_id)
        if risk.get("severity") not in ALLOWED_RISK_SEVERITIES:
            fail(errors, f"{prefix}: unsupported severity {risk.get('severity')!r}")
        require_string(risk.get("statement"), "statement", prefix, errors)
        require_string(risk.get("closureGate"), "closureGate", prefix, errors)

    exceptions = payload.get("activeExceptions")
    if not isinstance(exceptions, list):
        fail(errors, f"{owner}: activeExceptions must be a list")
        exceptions = []
    for index, exception in enumerate(exceptions):
        prefix = f"{owner}: activeExceptions[{index}]"
        if not isinstance(exception, dict):
            fail(errors, f"{prefix} must be an object")
            continue
        for field in ("id", "rule", "reason", "owner", "expiryOrRemovalGate", "rollback"):
            require_string(exception.get(field), field, prefix, errors)

    next_gate = payload.get("nextMandatoryGate")
    if not isinstance(next_gate, dict):
        fail(errors, f"{owner}: nextMandatoryGate must be an object")
        next_gate = {}
    gate_id = next_gate.get("id")
    if not isinstance(gate_id, str) or not WORK_PACKAGE_ID.fullmatch(gate_id):
        fail(errors, f"{owner}: nextMandatoryGate.id must be a work-package id")
    require_string(next_gate.get("condition"), "nextMandatoryGate.condition", owner, errors)

    review = payload.get("review")
    if not isinstance(review, dict):
        fail(errors, f"{owner}: review must be an object")
        review = {}
    reviewed_at = review.get("lastReviewedAt")
    if not isinstance(reviewed_at, str) or not DATE.fullmatch(reviewed_at):
        fail(errors, f"{owner}: review.lastReviewedAt must be YYYY-MM-DD")
    require_string(review.get("lastReviewedBy"), "review.lastReviewedBy", owner, errors)
    if review.get("decision") not in ALLOWED_GOVERNOR_DECISIONS:
        fail(errors, f"{owner}: unsupported review.decision {review.get('decision')!r}")
    require_string(review.get("nextReviewTrigger"), "review.nextReviewTrigger", owner, errors)


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            fail(errors, f"missing required file: {relative}")

    forbidden_files = sorted(
        path.relative_to(ROOT).as_posix()
        for pattern in ("*.zip", "*.p12", "*.pfx", "*.pem", "*.key")
        for path in ROOT.rglob(pattern)
        if ".git" not in path.parts
    )
    if forbidden_files:
        fail(errors, f"forbidden generated archive or credential-like files: {forbidden_files}")

    work_package_dir = ROOT / "work-packages"
    packages = sorted(work_package_dir.glob("*.json")) if work_package_dir.is_dir() else []
    if not packages:
        fail(errors, "no canonical JSON work package found")

    seen_ids: set[str] = set()
    for package in packages:
        validate_work_package(package, seen_ids, errors)

    validate_governor_state(ROOT / "governance/governor-state.json", errors)

    if errors:
        print("REPOSITORY VALIDATION FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"REPOSITORY VALIDATION OK: {len(packages)} work package(s), governor state valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
