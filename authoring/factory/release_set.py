#!/usr/bin/env python3
"""Deterministic M3.4 Qualified Release Set builder/verifier.

Composes exact canonical kit bytes with already self-verifying PASS FactoryRuns.
No semantic review, model/provider, source ingestion, network call, remote
publication or learner-runtime behavior is introduced here.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import handoff
from authoring.factory import reliability
from authoring.v2.atlas import validate_atlas_content as atlas

RELEASE_SCHEMA = "learnit.atlas.qualified_release_set.v1"
RELEASE_PROFILE = "atlas.qualified-release-set.v1"
RESULT_SCHEMA = "learnit.atlas.qualified_release_set_result.v1"
PASS_BUILT = "PASS_QUALIFIED_RELEASE_SET_BUILT_V1"
PASS_VERIFIED = "PASS_QUALIFIED_RELEASE_SET_VERIFICATION_V1"
HOLD_INPUT = "HOLD_QUALIFIED_RELEASE_SET_INPUT_V1"
UPSTREAM_AUTHORITY = "c102ca81f3b144bea1140860ef633a0d01987d59"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
UUID4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
EXIT_HOLD = 8


class ReleaseSetInputError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return factory.canonical_json_bytes(value)


def sha(data: bytes) -> str:
    return factory.sha256_bytes(data)


def digest(value: Any) -> str:
    return sha(canonical(value))


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = set(value) if isinstance(value, dict) else set()
        raise ReleaseSetInputError(
            f"{label} fields mismatch; missing={sorted(keys-actual)} extra={sorted(actual-keys)}"
        )
    return value


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseSetInputError(f"{label} must be a non-empty string")
    return value


def integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReleaseSetInputError(f"{label} must be an integer >= 0")
    return value


def load_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ReleaseSetInputError(f"{label}: {exc}") from exc


def load_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseSetInputError(f"{label}: invalid UTF-8 JSON: {exc}") from exc


def parse_entry_specs(specs: list[str]) -> list[tuple[Path, Path]]:
    if not specs:
        raise ReleaseSetInputError("at least one --entry RUN_PATH=KIT_PATH is required")
    rows: list[tuple[Path, Path]] = []
    seen: set[tuple[str, str]] = set()
    for spec in specs:
        if "=" not in spec:
            raise ReleaseSetInputError(
                f"invalid entry {spec!r}; expected RUN_PATH=KIT_PATH"
            )
        run_raw, kit_raw = spec.split("=", 1)
        if not run_raw or not kit_raw:
            raise ReleaseSetInputError("entry paths must be non-empty")
        key = (run_raw, kit_raw)
        if key in seen:
            raise ReleaseSetInputError("duplicate release entry binding")
        seen.add(key)
        rows.append((Path(run_raw), Path(kit_raw)))
    return rows


def revision_rows(package: dict[str, Any]) -> list[tuple[str, str, str]]:
    rows = [
        ("package", package["packageRevisionId"], package["packageRevisionDigest"])
    ]
    for course in package["courses"]:
        rows.append(("course", course["courseRevisionId"], course["courseRevisionDigest"]))
        for activity in course["activities"]:
            rows.append(
                (
                    "activity",
                    activity["activityRevisionId"],
                    activity["activityRevisionDigest"],
                )
            )
    return rows


def validate_kit_value(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReleaseSetInputError(f"{label}: kit root must be an object")
    try:
        atlas.validate_package(value)
    except Exception as exc:
        raise ReleaseSetInputError(f"{label}: canonical Atlas validation failed: {exc}") from exc
    for key in ("packageLineageId", "packageRevisionId"):
        if not UUID4.fullmatch(text(value.get(key), f"{label}.{key}")):
            raise ReleaseSetInputError(f"{label}.{key} is not a UUIDv4")
    if not SHA256.fullmatch(text(value.get("packageRevisionDigest"), f"{label}.packageRevisionDigest")):
        raise ReleaseSetInputError(f"{label}.packageRevisionDigest is invalid")
    return value


def entry_from_bytes(
    run_raw: bytes,
    kit_raw: bytes,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any], list[tuple[str, str, str]]]:
    run_value = load_json_bytes(run_raw, label + " FactoryRun")
    try:
        run = reliability.verify_run(run_value)
    except reliability.ReliabilityInputError as exc:
        raise ReleaseSetInputError(f"{label}: FactoryRun verification failed: {exc}") from exc
    if reliability.decision_class(run) != "PASS":
        raise ReleaseSetInputError(
            f"{label}: FactoryRun is not releasable ({run['decision']['verdict']})"
        )

    expected_kit_sha = run["evidenceBundle"]["artifacts"]["generatedKit"]["sha256"]
    actual_kit_sha = sha(kit_raw)
    if actual_kit_sha != expected_kit_sha:
        raise ReleaseSetInputError(
            f"{label}: exact kit bytes do not match FactoryRun generatedKit.sha256"
        )

    kit = validate_kit_value(load_json_bytes(kit_raw, label + " kit"), label + " kit")
    entry = {
        "packageLineageId": kit["packageLineageId"],
        "packageRevisionId": kit["packageRevisionId"],
        "packageRevisionDigest": kit["packageRevisionDigest"],
        "title": text(kit["title"], label + ".title"),
        "versionLabel": text(kit["versionLabel"], label + ".versionLabel"),
        "language": text(kit["language"], label + ".language"),
        "kit": {"bytes": len(kit_raw), "sha256": actual_kit_sha},
        "factoryRun": {
            "runId": run["runId"],
            "bytes": len(run_raw),
            "sha256": sha(run_raw),
            "factoryContextDigest": run["factoryContextDigest"],
        },
    }
    return entry, kit, revision_rows(kit)


def collision_check(
    rows: list[tuple[dict[str, Any], dict[str, Any], list[tuple[str, str, str]]]]
) -> None:
    package_lineages: set[str] = set()
    run_ids: set[str] = set()
    revision_index: dict[str, tuple[str, str]] = {}
    package_revision_index: dict[str, tuple[str, str]] = {}

    for entry, _kit, revisions in rows:
        lineage = entry["packageLineageId"]
        if lineage in package_lineages:
            raise ReleaseSetInputError(
                f"duplicate packageLineageId in release set: {lineage}"
            )
        package_lineages.add(lineage)

        package_revision_id = entry["packageRevisionId"]
        package_revision_binding = (
            entry["packageRevisionDigest"],
            entry["kit"]["sha256"],
        )
        previous_package_revision = package_revision_index.get(package_revision_id)
        if (
            previous_package_revision is not None
            and previous_package_revision != package_revision_binding
        ):
            raise ReleaseSetInputError(
                f"package revision exact-byte collision: {package_revision_id}"
            )
        package_revision_index[package_revision_id] = package_revision_binding

        run_id = entry["factoryRun"]["runId"]
        if run_id in run_ids:
            raise ReleaseSetInputError(f"duplicate FactoryRun identity: {run_id}")
        run_ids.add(run_id)

        for level, revision_id, revision_digest in revisions:
            previous = revision_index.get(revision_id)
            if previous is not None and previous[1] != revision_digest:
                raise ReleaseSetInputError(
                    f"revision digest collision: {revision_id} "
                    f"({previous[0]}={previous[1]} vs {level}={revision_digest})"
                )
            revision_index[revision_id] = (level, revision_digest)


def metrics(
    rows: list[tuple[dict[str, Any], dict[str, Any], list[tuple[str, str, str]]]]
) -> dict[str, int]:
    return {
        "packages": len(rows),
        "courses": sum(len(kit["courses"]) for _entry, kit, _revisions in rows),
        "activities": sum(
            len(course["activities"])
            for _entry, kit, _revisions in rows
            for course in kit["courses"]
        ),
    }


def build_manifest(
    rows: list[tuple[dict[str, Any], dict[str, Any], list[tuple[str, str, str]]]]
) -> dict[str, Any]:
    if not rows:
        raise ReleaseSetInputError("release set must contain at least one entry")
    collision_check(rows)
    entries = sorted((row[0] for row in rows), key=lambda item: item["packageLineageId"])
    core = {
        "schema": RELEASE_SCHEMA,
        "profile": RELEASE_PROFILE,
        "factoryAuthority": UPSTREAM_AUTHORITY,
        "entries": entries,
        "metrics": metrics(rows),
    }
    return {**core, "releaseSetId": digest(core)}


def kit_member(entry: dict[str, Any]) -> str:
    return f"kits/{entry['packageLineageId']}/{entry['packageRevisionId']}.json"


def run_member(entry: dict[str, Any]) -> str:
    run_id = entry["factoryRun"]["runId"]
    if not isinstance(run_id, str) or not SHA256.fullmatch(run_id):
        raise ReleaseSetInputError("FactoryRun runId is invalid")
    return f"factory-runs/{run_id.split(':', 1)[1]}.json"


def build_release_archive(specs: list[str], out: Path) -> dict[str, Any]:
    bindings = parse_entry_specs(specs)
    rows: list[tuple[dict[str, Any], dict[str, Any], list[tuple[str, str, str]]]] = []
    raw_by_lineage: dict[str, tuple[bytes, bytes]] = {}

    input_paths: set[Path] = set()
    for index, (run_path, kit_path) in enumerate(bindings):
        input_paths.update({run_path.resolve(), kit_path.resolve()})
        run_raw = load_bytes(run_path, f"entry[{index}] FactoryRun")
        kit_raw = load_bytes(kit_path, f"entry[{index}] kit")
        row = entry_from_bytes(run_raw, kit_raw, f"entry[{index}]")
        rows.append(row)
        lineage = row[0]["packageLineageId"]
        if lineage in raw_by_lineage:
            raise ReleaseSetInputError(f"duplicate packageLineageId in release set: {lineage}")
        raw_by_lineage[lineage] = (run_raw, kit_raw)

    manifest = build_manifest(rows)
    members: dict[str, bytes] = {"release-set.json": canonical(manifest)}
    for entry in manifest["entries"]:
        run_raw, kit_raw = raw_by_lineage[entry["packageLineageId"]]
        members[kit_member(entry)] = kit_raw
        members[run_member(entry)] = run_raw

    archive = handoff.zip_bytes(members)
    if out.resolve() in input_paths:
        raise ReleaseSetInputError("output path must not overwrite an input")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(archive)
    except OSError as exc:
        raise ReleaseSetInputError(f"output: {exc}") from exc

    verified = verify_release_archive(out)
    if verified["manifest"] != manifest:
        raise ReleaseSetInputError("self-verification changed release-set manifest")

    return {
        "schema": RESULT_SCHEMA,
        "verdict": PASS_BUILT,
        "releaseSetId": manifest["releaseSetId"],
        "releaseSha256": sha(archive),
        "releaseBytes": len(archive),
        "metrics": manifest["metrics"],
    }


def validate_manifest(value: Any) -> dict[str, Any]:
    manifest = exact(
        value,
        {"schema", "profile", "factoryAuthority", "entries", "metrics", "releaseSetId"},
        "release set",
    )
    if manifest["schema"] != RELEASE_SCHEMA or manifest["profile"] != RELEASE_PROFILE:
        raise ReleaseSetInputError("unsupported release-set schema/profile")
    authority = text(manifest["factoryAuthority"], "factoryAuthority")
    if not SHA40.fullmatch(authority) or authority != UPSTREAM_AUTHORITY:
        raise ReleaseSetInputError("factoryAuthority mismatch")

    entries = manifest["entries"]
    if not isinstance(entries, list) or not entries:
        raise ReleaseSetInputError("entries must be a non-empty list")
    if entries != sorted(entries, key=lambda item: item.get("packageLineageId", "")):
        raise ReleaseSetInputError("entries must be sorted by packageLineageId")

    for index, entry in enumerate(entries):
        entry = exact(
            entry,
            {
                "packageLineageId",
                "packageRevisionId",
                "packageRevisionDigest",
                "title",
                "versionLabel",
                "language",
                "kit",
                "factoryRun",
            },
            f"entries[{index}]",
        )
        if not UUID4.fullmatch(text(entry["packageLineageId"], f"entries[{index}].packageLineageId")):
            raise ReleaseSetInputError("invalid packageLineageId")
        if not UUID4.fullmatch(text(entry["packageRevisionId"], f"entries[{index}].packageRevisionId")):
            raise ReleaseSetInputError("invalid packageRevisionId")
        if not SHA256.fullmatch(text(entry["packageRevisionDigest"], f"entries[{index}].packageRevisionDigest")):
            raise ReleaseSetInputError("invalid packageRevisionDigest")
        for key in ("title", "versionLabel", "language"):
            text(entry[key], f"entries[{index}].{key}")

        kit = exact(entry["kit"], {"bytes", "sha256"}, f"entries[{index}].kit")
        integer(kit["bytes"], f"entries[{index}].kit.bytes")
        if not SHA256.fullmatch(text(kit["sha256"], f"entries[{index}].kit.sha256")):
            raise ReleaseSetInputError("invalid kit sha256")

        run = exact(
            entry["factoryRun"],
            {"runId", "bytes", "sha256", "factoryContextDigest"},
            f"entries[{index}].factoryRun",
        )
        integer(run["bytes"], f"entries[{index}].factoryRun.bytes")
        for key in ("runId", "sha256", "factoryContextDigest"):
            if not SHA256.fullmatch(text(run[key], f"entries[{index}].factoryRun.{key}")):
                raise ReleaseSetInputError(f"invalid factoryRun {key}")

    metric = exact(manifest["metrics"], {"packages", "courses", "activities"}, "metrics")
    for key in metric:
        integer(metric[key], f"metrics.{key}")
    if metric["packages"] != len(entries):
        raise ReleaseSetInputError("metrics.packages mismatch")

    core = {
        key: manifest[key]
        for key in ("schema", "profile", "factoryAuthority", "entries", "metrics")
    }
    if manifest["releaseSetId"] != digest(core):
        raise ReleaseSetInputError("releaseSetId mismatch")
    return manifest


def read_canonical_archive(raw: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ReleaseSetInputError("duplicate archive member")
            members: dict[str, bytes] = {}
            for info in infos:
                name = handoff.safe_member_name(info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if mode not in (0, stat.S_IFREG):
                    raise ReleaseSetInputError(f"non-regular archive member: {name}")
                members[name] = zf.read(info)
    except ReleaseSetInputError:
        raise
    except handoff.HandoffInputError as exc:
        raise ReleaseSetInputError(f"invalid release ZIP member: {exc}") from exc
    except (zipfile.BadZipFile, OSError, KeyError, RuntimeError) as exc:
        raise ReleaseSetInputError(f"invalid release ZIP: {exc}") from exc

    if handoff.zip_bytes(members) != raw:
        raise ReleaseSetInputError("release ZIP is not canonical deterministic form")
    return members


def verify_release_archive(path: Path) -> dict[str, Any]:
    raw = load_bytes(path, "release")
    members = read_canonical_archive(raw)
    if "release-set.json" not in members:
        raise ReleaseSetInputError("release-set.json is missing")

    manifest = validate_manifest(
        load_json_bytes(members["release-set.json"], "release-set.json")
    )
    expected = {"release-set.json"}
    rows: list[tuple[dict[str, Any], dict[str, Any], list[tuple[str, str, str]]]] = []

    for index, declared in enumerate(manifest["entries"]):
        kp = kit_member(declared)
        rp = run_member(declared)
        expected.update({kp, rp})
        if kp not in members or rp not in members:
            raise ReleaseSetInputError(f"entry[{index}] declared member is missing")
        rebuilt = entry_from_bytes(members[rp], members[kp], f"entry[{index}]")
        if rebuilt[0] != declared:
            raise ReleaseSetInputError(f"entry[{index}] manifest binding mismatch")
        rows.append(rebuilt)

    if set(members) != expected:
        raise ReleaseSetInputError(
            f"archive members mismatch; missing={sorted(expected-set(members))} "
            f"extra={sorted(set(members)-expected)}"
        )

    rebuilt_manifest = build_manifest(rows)
    if rebuilt_manifest != manifest:
        raise ReleaseSetInputError("release-set manifest does not match embedded bytes")

    return {
        "schema": RESULT_SCHEMA,
        "verdict": PASS_VERIFIED,
        "releaseSetId": manifest["releaseSetId"],
        "releaseSha256": sha(raw),
        "releaseBytes": len(raw),
        "metrics": manifest["metrics"],
        "manifest": manifest,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Atlas M3.4 Qualified Release Set")
    sub = root.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument(
        "--entry",
        action="append",
        default=[],
        metavar="RUN_PATH=KIT_PATH",
        help="Bind one PASS FactoryRun to its exact kit. Repeat for multiple packages.",
    )
    build.add_argument("--out", type=Path, required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--release", type=Path, required=True)
    return root


def public_result(value: dict[str, Any]) -> dict[str, Any]:
    return {key: val for key, val in value.items() if key != "manifest"}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "build":
            result = build_release_archive(args.entry, args.out)
        else:
            result = verify_release_archive(args.release)
    except ReleaseSetInputError as exc:
        error = {
            "schema": RESULT_SCHEMA,
            "verdict": HOLD_INPUT,
            "cause": str(exc),
        }
        sys.stdout.write(canonical(error).decode("utf-8") + "\n")
        return EXIT_HOLD
    sys.stdout.write(canonical(public_result(result)).decode("utf-8") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
