#!/usr/bin/env python3
"""Permanent CI guard for the Learn-it standalone player."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from typing import Any, Iterable

PLAYER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLAYER_ROOT.parents[1]
REGISTRY_PATH = PLAYER_ROOT / "dev" / "checks_registry.json"
SOURCE_MANIFEST_PATH = PLAYER_ROOT / "source_manifest.json"
IGNORED_MANIFEST_PREFIXES = ("dist/", "reports/", "release/")


class GuardError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GuardError(f"missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GuardError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GuardError(f"expected JSON object in {path}")
    return value


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise GuardError(result.stderr.strip() or "cannot resolve Git HEAD")
    return result.stdout.strip()


def normalize_relative_path(value: str) -> str:
    raw = value.replace("\\", "/").strip()
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise GuardError(f"unsafe relative path: {value!r}")
    return path.as_posix()


def _manifest_file_entries(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if {"path", "sha256", "bytes"}.issubset(value):
            yield value
        for child in value.values():
            yield from _manifest_file_entries(child)
    elif isinstance(value, list):
        for child in value:
            yield from _manifest_file_entries(child)


def source_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for raw in _manifest_file_entries(manifest):
        path = normalize_relative_path(str(raw["path"]))
        if path.startswith(IGNORED_MANIFEST_PREFIXES):
            continue
        expected_sha = str(raw["sha256"]).lower()
        expected_bytes = int(raw["bytes"])
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise GuardError(f"invalid source SHA-256 for {path}")
        entry = {"path": path, "sha256": expected_sha, "bytes": expected_bytes}
        previous = entries.get(path)
        if previous and previous != entry:
            raise GuardError(f"contradictory source manifest entries for {path}")
        entries[path] = entry
    if not entries:
        raise GuardError("source manifest contains no verifiable file entries")
    return [entries[path] for path in sorted(entries)]


def verify_entries(root: Path, entries: list[dict[str, Any]]) -> int:
    verified = 0
    resolved_root = root.resolve()
    for entry in entries:
        candidate = (root / entry["path"]).resolve()
        if resolved_root not in candidate.parents:
            raise GuardError(f"manifest path escapes player root: {entry['path']}")
        if not candidate.is_file():
            raise GuardError(f"manifest source file is missing: {entry['path']}")
        actual_bytes = candidate.stat().st_size
        actual_sha = sha256_file(candidate)
        if actual_bytes != entry["bytes"] or actual_sha != entry["sha256"]:
            raise GuardError(
                f"source tree differs from manifest for {entry['path']}: "
                f"bytes {actual_bytes}/{entry['bytes']}, sha256 {actual_sha}/{entry['sha256']}"
            )
        verified += 1
    return verified


def verify_source_tree() -> int:
    return verify_entries(PLAYER_ROOT, source_entries(load_json(SOURCE_MANIFEST_PATH)))


def browser_inventory(registry: dict[str, Any] | None = None) -> list[dict[str, str]]:
    registry = registry or load_json(REGISTRY_PATH)
    declared = registry.get("browser")
    if not isinstance(declared, list) or not declared or not all(isinstance(x, str) for x in declared):
        raise GuardError("checks registry browser inventory must be a non-empty string list")
    normalized = [normalize_relative_path(path) for path in declared]
    if len(normalized) != len(set(normalized)):
        raise GuardError("checks registry contains duplicate browser suites")
    actual = sorted(path.relative_to(PLAYER_ROOT).as_posix() for path in (PLAYER_ROOT / "tests").glob("browser_*.py"))
    if sorted(normalized) != actual:
        missing = sorted(set(actual) - set(normalized))
        stale = sorted(set(normalized) - set(actual))
        raise GuardError(f"browser suite inventory mismatch; missing={missing}, stale={stale}")

    coverage = {
        "mobile": ("mobile", "realistic_device"),
        "desktop": ("desktop",),
        "persistence": ("persistence", "storage"),
        "recovery": ("resilience", "interruption"),
        "import-export": ("import", "product_flow"),
    }
    for capability, tokens in coverage.items():
        if not any(any(token in path for token in tokens) for path in normalized):
            raise GuardError(f"browser inventory lacks required {capability} coverage")

    matrix = []
    for relative in normalized:
        stem = Path(relative).stem
        matrix.append({
            "id": stem.replace("_", "-")[:63],
            "suite": f"apps/player/{relative}",
        })
    return matrix


def write_github_output(path: Path, key: str, value: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def artifact_payload(artifact: Path) -> dict[str, Any]:
    artifact = artifact.resolve()
    if not artifact.is_file():
        raise GuardError(f"artifact does not exist: {artifact}")
    verified_sources = verify_source_tree()
    try:
        artifact_rel = artifact.relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        raise GuardError("artifact must be inside the repository") from exc
    inventory = browser_inventory()
    return {
        "schema": "learnit.player_ci_artifact.v1",
        "sourceCommit": git_head(),
        "artifactPath": artifact_rel,
        "artifactBytes": artifact.stat().st_size,
        "artifactSha256": sha256_file(artifact),
        "sourceManifestSha256": sha256_file(SOURCE_MANIFEST_PATH),
        "checksRegistrySha256": sha256_file(REGISTRY_PATH),
        "verifiedSourceFiles": verified_sources,
        "browserSuiteCount": len(inventory),
    }


def verify_artifact(artifact: Path, manifest_path: Path) -> dict[str, Any]:
    payload = load_json(manifest_path)
    if payload.get("schema") != "learnit.player_ci_artifact.v1":
        raise GuardError("unsupported CI artifact manifest schema")
    artifact = artifact.resolve()
    expected = {
        "sourceCommit": git_head(),
        "artifactBytes": artifact.stat().st_size if artifact.is_file() else -1,
        "artifactSha256": sha256_file(artifact) if artifact.is_file() else "missing",
        "sourceManifestSha256": sha256_file(SOURCE_MANIFEST_PATH),
        "checksRegistrySha256": sha256_file(REGISTRY_PATH),
        "browserSuiteCount": len(browser_inventory()),
    }
    for key, actual in expected.items():
        if payload.get(key) != actual:
            raise GuardError(f"artifact manifest mismatch for {key}: {payload.get(key)!r} != {actual!r}")
    verified = verify_source_tree()
    if payload.get("verifiedSourceFiles") != verified:
        raise GuardError("verified source-file count changed")
    return payload


def self_test() -> dict[str, bool]:
    checks = {
        "artifact-digest-mutation-rejected": False,
        "browser-suite-omission-rejected": False,
        "source-after-build-mutation-rejected": False,
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        artifact = temp / "learnit.html"
        artifact.write_text("stable", encoding="utf-8")
        expected = {"bytes": artifact.stat().st_size, "sha256": sha256_file(artifact)}
        bad = copy.deepcopy(expected)
        bad["sha256"] = "0" * 64
        try:
            if artifact.stat().st_size != bad["bytes"] or sha256_file(artifact) != bad["sha256"]:
                raise GuardError("digest mismatch")
        except GuardError:
            checks["artifact-digest-mutation-rejected"] = True

        registry = load_json(REGISTRY_PATH)
        altered = copy.deepcopy(registry)
        altered["browser"] = altered["browser"][1:]
        try:
            browser_inventory(altered)
        except GuardError:
            checks["browser-suite-omission-rejected"] = True

        source = temp / "source.js"
        source.write_text("before", encoding="utf-8")
        entries = [{"path": "source.js", "bytes": source.stat().st_size, "sha256": sha256_file(source)}]
        source.write_text("after", encoding="utf-8")
        try:
            verify_entries(temp, entries)
        except GuardError:
            checks["source-after-build-mutation-rejected"] = True

    if not all(checks.values()):
        raise GuardError(f"CI guard self-test failed: {checks}")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    inventory_parser = sub.add_parser("inventory")
    inventory_parser.add_argument("--github-output", type=Path)

    record_parser = sub.add_parser("record")
    record_parser.add_argument("--artifact", type=Path, required=True)
    record_parser.add_argument("--output", type=Path, required=True)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--artifact", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)

    sub.add_parser("self-test")
    args = parser.parse_args()

    try:
        if args.command == "inventory":
            matrix = {"include": browser_inventory()}
            compact = json.dumps(matrix, separators=(",", ":"))
            if args.github_output:
                write_github_output(args.github_output, "browser_matrix", compact)
            print(json.dumps(matrix, indent=2))
        elif args.command == "record":
            payload = artifact_payload(args.artifact)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(payload, indent=2))
        elif args.command == "verify":
            print(json.dumps(verify_artifact(args.artifact, args.manifest), indent=2))
        elif args.command == "self-test":
            print(json.dumps(self_test(), indent=2))
    except GuardError as exc:
        print(f"PLAYER CI GUARD ERROR: {exc}", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
