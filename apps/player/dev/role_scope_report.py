#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from fnmatch import fnmatchcase
from pathlib import Path
import json
import sys

ROLE_KEYS = (
    "developerWritePaths",
    "qaWritePaths",
    "integratorWritePaths",
    "governorWritePaths",
)
SCHEMA = "learnit.stage_d_role_scope_report.v1"


class ScopeError(ValueError):
    pass


def normalize_path(raw: object) -> str:
    value = str(raw).replace("\\", "/")
    if not value or value != value.strip():
        raise ScopeError(f"invalid path: {raw!r}")
    parts = value.split("/")
    if value.startswith("/") or parts[0].endswith(":") or any(part in {"", ".", ".."} for part in parts):
        raise ScopeError(f"invalid repository-relative path: {value}")
    return "/".join(parts)


def load_role_scopes(work_package: dict) -> dict[str, tuple[str, ...]]:
    role_scopes = work_package.get("roleScopes")
    if not isinstance(role_scopes, dict):
        raise ScopeError("work package roleScopes must be an object")
    unexpected = sorted(set(role_scopes) - set(ROLE_KEYS))
    if unexpected:
        raise ScopeError(f"unexpected role scopes: {unexpected}")
    normalized: dict[str, tuple[str, ...]] = {}
    for role in ROLE_KEYS:
        patterns = role_scopes.get(role)
        if not isinstance(patterns, list) or not patterns:
            raise ScopeError(f"{role} must be a non-empty list")
        values = tuple(sorted(normalize_path(pattern) for pattern in patterns))
        if len(values) != len(set(values)):
            raise ScopeError(f"{role} contains duplicate patterns")
        normalized[role] = values
    return normalized


def evaluate(work_package: dict, changed_paths: list[object]) -> dict:
    if not isinstance(changed_paths, list):
        raise ScopeError("changed paths must be a list")
    roles = load_role_scopes(work_package)
    paths = sorted({normalize_path(path) for path in changed_paths})

    pattern_owners: dict[str, list[str]] = {}
    for role in ROLE_KEYS:
        for pattern in roles[role]:
            pattern_owners.setdefault(pattern, []).append(role)
    duplicate_patterns = [
        {"pattern": pattern, "roles": sorted(owners)}
        for pattern, owners in sorted(pattern_owners.items())
        if len(owners) > 1
    ]

    assignments = []
    unowned_paths = []
    multiply_owned_paths = []
    for path in paths:
        owners = [
            role
            for role in ROLE_KEYS
            if any(fnmatchcase(path, pattern) for pattern in roles[role])
        ]
        assignments.append({"path": path, "owners": owners})
        if not owners:
            unowned_paths.append(path)
        elif len(owners) > 1:
            multiply_owned_paths.append({"path": path, "owners": owners})

    ok = not duplicate_patterns and not unowned_paths and not multiply_owned_paths
    return {
        "schema": SCHEMA,
        "ok": ok,
        "roles": {role: list(roles[role]) for role in ROLE_KEYS},
        "changedPaths": assignments,
        "unownedPaths": unowned_paths,
        "multiplyOwnedPaths": multiply_owned_paths,
        "duplicatePatterns": duplicate_patterns,
        "summary": {
            "roles": len(ROLE_KEYS),
            "changedPaths": len(paths),
            "ownedExactlyOnce": sum(len(item["owners"]) == 1 for item in assignments),
            "unowned": len(unowned_paths),
            "multiplyOwned": len(multiply_owned_paths),
            "duplicatePatterns": len(duplicate_patterns),
        },
    }


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _read_paths(path: Path) -> list[object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ScopeError("paths JSON must contain a list")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description="Validate changed paths against disjoint Stage D role scopes.")
    parser.add_argument("--work-package", required=True, type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--paths-json", type=Path)
    source.add_argument("--path", action="append", dest="paths")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        work_package = json.loads(args.work_package.read_text(encoding="utf-8"))
        changed_paths = _read_paths(args.paths_json) if args.paths_json else list(args.paths or [])
        report = evaluate(work_package, changed_paths)
    except (OSError, json.JSONDecodeError, ScopeError) as error:
        print(json.dumps({"schema": SCHEMA, "ok": False, "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 2

    rendered = canonical_json(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
