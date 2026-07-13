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
    "SECURITY.md",
    ".gitignore",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/work-package.yml",
    "work-packages/ARC-WP-000.json",
    "docs/architecture/README.md",
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

BROAD_GLOBS = {"*", "**", "**/*", ".", "./**", "/**"}
WORK_PACKAGE_ID = re.compile(r"^[A-Z][A-Z0-9-]*-WP-[0-9]{3,}$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def require_string_list(
    value: Any, field: str, package_id: str, errors: list[str]
) -> list[str]:
    if not isinstance(value, list) or not value:
        fail(errors, f"{package_id}: {field} must be a non-empty list")
        return []
    invalid = [entry for entry in value if not isinstance(entry, str) or not entry.strip()]
    if invalid:
        fail(errors, f"{package_id}: {field} contains invalid entries")
    return [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]


def validate_work_package(path: Path, seen_ids: set[str], errors: list[str]) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(errors, f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
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
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            fail(errors, f"{package_id}: {field} is required")

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

    if artifact_sha is not None and not re.fullmatch(r"[0-9a-f]{64}", str(artifact_sha)):
        fail(errors, f"{package_id}: artifactSha256 must be null or 64 lowercase hex characters")


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

    if errors:
        print("REPOSITORY VALIDATION FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"REPOSITORY VALIDATION OK: {len(packages)} work package(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
