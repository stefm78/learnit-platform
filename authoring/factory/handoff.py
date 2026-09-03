#!/usr/bin/env python3
"""Deterministic portable review handoff around the promoted Atlas factory.

This module packages one exact candidate/brief/source case for a logically
independent semantic reviewer, then consumes the returned semantic review into
the existing M3.2.5 FactoryRun builder. It adds no semantic authority, model
provider, source ingestion, network call, learner runtime behavior or automatic
publication.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import reliability
from authoring.factory import source_admission
from authoring.factory import transient_source_admission
from authoring.v2.atlas import pedagogical_quality as quality

HANDOFF_SCHEMA = "learnit.atlas.review_handoff.v1"
HANDOFF_PROFILE = "atlas.review-handoff.v1"
RESULT_SCHEMA = "learnit.atlas.review_handoff_result.v1"
PASS_PREPARED = "PASS_REVIEW_HANDOFF_PREPARED_V1"
PASS_CONSUMED = "PASS_REVIEW_HANDOFF_CONSUMED_V1"
HOLD_INPUT = "HOLD_REVIEW_HANDOFF_INPUT_V1"
FACTORY_BASELINE = "16bae3e7a5c58f667609e481d4d38f2b1b2fa584"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

CATALOG_PATH = ROOT / "authoring/factory/benchmark_sources_v1.json"
REVIEWER_SKILL_PATH = ROOT / "authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md"

REVIEW_REQUEST = """# REVIEW REQUEST

Review only the candidate in this bundle as an independent Atlas semantic reviewer.
Follow SKILL_ATLAS_KIT_REVIEW_V1.md and review-handoff.json.
Use only the supplied candidate, learner brief, exact sources, quality report and factory context.
Do not repair or modify anything.
Bind target exactly to the supplied factory context.
Return only the final learnit.atlas.semantic_review.v1 JSON.
"""

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
FILE_MODE = stat.S_IFREG | 0o644
SOURCE_MEMBER_SUFFIXES = (".pdf", ".zip", ".txt", ".bin")

ROLE_PATHS = {
    "candidate": "candidate.json",
    "learner-brief": "learner-brief.json",
    "factory-context": "factory-context.json",
    "quality-report": "quality-report.json",
    "reviewer-skill": "SKILL_ATLAS_KIT_REVIEW_V1.md",
    "review-request": "REVIEW_REQUEST.md",
}
OPTIONAL_ROLE_PATHS = {
    "source-catalog": "source-catalog.json",
}
SINGLETON_ROLES = set(ROLE_PATHS) | set(OPTIONAL_ROLE_PATHS)
MULTI_ROLES = {"source-admission", "source"}
ALL_ROLES = SINGLETON_ROLES | MULTI_ROLES


class HandoffInputError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return factory.canonical_json_bytes(value)


def digest(value: Any) -> str:
    return factory.sha256_bytes(canonical(value))


def sha(data: bytes) -> str:
    return factory.sha256_bytes(data)


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = set(value) if isinstance(value, dict) else set()
        raise HandoffInputError(
            f"{label} fields mismatch; missing={sorted(keys-actual)} extra={sorted(actual-keys)}"
        )
    return value


def nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffInputError(f"{label} must be a non-empty string")
    return value


def load_json_bytes(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HandoffInputError(f"{label}: invalid UTF-8 JSON: {exc}") from exc


def load_path(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise HandoffInputError(f"{label}: {exc}") from exc


def parse_bindings(specs: list[str], label: str) -> dict[str, Path]:
    if not specs:
        raise HandoffInputError(f"at least one --{label} SOURCE_ID=PATH is required")
    out: dict[str, Path] = {}
    folded: dict[str, str] = {}
    for spec in specs:
        if "=" not in spec:
            raise HandoffInputError(f"invalid {label} binding {spec!r}; expected SOURCE_ID=PATH")
        source_id, raw_path = spec.split("=", 1)
        if not factory.SOURCE_ID.fullmatch(source_id):
            raise HandoffInputError(f"invalid sourceId {source_id!r}")
        if source_id in out:
            raise HandoffInputError(f"duplicate {label} sourceId {source_id!r}")
        folded_id = source_id.casefold()
        prior = folded.get(folded_id)
        if prior is not None and prior != source_id:
            raise HandoffInputError(
                f"{label} sourceIds collide on case-insensitive filesystems: "
                f"{prior!r} vs {source_id!r}"
            )
        folded[folded_id] = source_id
        if not raw_path:
            raise HandoffInputError(f"{label} path must be non-empty")
        out[source_id] = Path(raw_path)
    return out


def source_suffix(data: bytes) -> str:
    if data.startswith(b"%PDF-"):
        return ".pdf"
    if data.startswith(b"PK\x03\x04"):
        return ".zip"
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return ".bin"
    return ".txt"


def artifact(role: str, path: str, data: bytes) -> dict[str, Any]:
    if role not in ALL_ROLES:
        raise HandoffInputError(f"unsupported artifact role {role!r}")
    return {"role": role, "path": path, "bytes": len(data), "sha256": sha(data)}


def safe_member_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise HandoffInputError(f"unsafe archive path {name!r}")
    posix = PurePosixPath(name)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise HandoffInputError(f"unsafe archive path {name!r}")
    normalized = posix.as_posix()
    if normalized != name:
        raise HandoffInputError(f"non-canonical archive path {name!r}")
    return normalized


def zip_bytes(members: dict[str, bytes]) -> bytes:
    names = sorted(members)
    for name in names:
        safe_member_name(name)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.comment = b""
        for name in names:
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = FILE_MODE << 16
            info.flag_bits = 0
            zf.writestr(info, members[name])
    return buffer.getvalue()


def target_from_context(context: dict[str, Any]) -> dict[str, str]:
    return {
        "contextDigest": context["contextDigest"],
        "kitSha256": context["kitSha256"],
        "sourceSetDigest": context["sourceSetDigest"],
        "briefSha256": context["briefSha256"],
    }


def source_admission_rows(
    source_paths: dict[str, Path],
    admission_paths: dict[str, Path],
) -> tuple[list[dict[str, Any]], dict[str, bytes], bytes | None]:
    if set(source_paths) != set(admission_paths):
        raise HandoffInputError(
            f"source/admission IDs mismatch; sources={sorted(source_paths)} admissions={sorted(admission_paths)}"
        )

    catalog: dict[str, Any] | None = None
    catalog_sha: str | None = None
    catalog_raw: bytes | None = None

    rows: list[dict[str, Any]] = []
    admission_bytes: dict[str, bytes] = {}
    for source_id in sorted(source_paths):
        source_path = source_paths[source_id]
        source_data = load_path(source_path, f"source {source_id}")
        raw_admission = load_path(admission_paths[source_id], f"admission {source_id}")
        record = load_json_bytes(raw_admission, f"admission {source_id}")
        schema = record.get("schema") if isinstance(record, dict) else None

        if schema == source_admission.ADMISSION_SCHEMA:
            if catalog is None:
                try:
                    catalog, catalog_sha = source_admission.load_catalog(CATALOG_PATH)
                    catalog_raw = CATALOG_PATH.read_bytes()
                except (OSError, source_admission.SourceAdmissionError) as exc:
                    raise HandoffInputError(f"source catalog: {exc}") from exc
            try:
                record = source_admission.verify_admission(record)
            except source_admission.SourceAdmissionError as exc:
                raise HandoffInputError(f"admission {source_id}: {exc}") from exc

            admission_source_id = record["source"]["sourceId"]
            if record["catalogSha256"] != catalog_sha:
                raise HandoffInputError(f"admission {source_id}: catalogSha256 mismatch")
            if record["decision"]["verdict"] != source_admission.PASS:
                raise HandoffInputError(
                    f"admission {source_id}: source is not admitted ({record['decision']['verdict']})"
                )
            if record["content"] is None:
                raise HandoffInputError(f"admission {source_id}: admitted source has no content binding")
            version = record["source"]["version"]
            if not isinstance(version, str) or not reliability.VERSION.fullmatch(version):
                raise HandoffInputError(f"admission {source_id}: invalid resource version")

            rebuilt = source_admission.build_admission(
                catalog,
                catalog_sha,
                admission_source_id,
                record["useContext"],
                source_path,
                list(record["acceptedConditions"]),
                version,
            )
            if rebuilt != record:
                raise HandoffInputError(
                    f"admission {source_id}: record is not reproducible from current catalog and exact bytes"
                )
        elif schema == transient_source_admission.ADMISSION_SCHEMA:
            try:
                record = transient_source_admission.verify_admission(record)
            except transient_source_admission.TransientSourceAdmissionError as exc:
                raise HandoffInputError(f"admission {source_id}: {exc}") from exc
            if record["decision"]["verdict"] != transient_source_admission.PASS:
                raise HandoffInputError(
                    f"admission {source_id}: source is not admitted ({record['decision']['verdict']})"
                )
            declaration = record["declaration"]
            if declaration["sourceId"] != source_id:
                raise HandoffInputError(
                    f"admission {source_id}: transient declaration sourceId mismatch"
                )
            version = declaration["version"]
            if not reliability.VERSION.fullmatch(version):
                raise HandoffInputError(f"admission {source_id}: invalid resource version")
            try:
                transient_source_admission.reproduce_admission(record, source_path)
            except transient_source_admission.TransientSourceAdmissionError as exc:
                raise HandoffInputError(f"admission {source_id}: {exc}") from exc
        else:
            raise HandoffInputError(
                f"admission {source_id}: unsupported admission schema {schema!r}"
            )

        if record["content"] != {"bytes": len(source_data), "sha256": sha(source_data)}:
            raise HandoffInputError(f"admission {source_id}: exact source byte binding mismatch")

        rows.append(
            {
                "schema": reliability.RESOURCE_SCHEMA,
                "resourceId": source_id,
                "version": version,
                "bytes": len(source_data),
                "sha256": sha(source_data),
            }
        )
        admission_bytes[source_id] = canonical(record)

    return rows, admission_bytes, catalog_raw


def prepare_review_bundle(
    kit: Path,
    brief: Path,
    source_specs: list[str],
    admission_specs: list[str],
    out: Path,
) -> dict[str, Any]:
    source_paths = parse_bindings(source_specs, "source")
    admission_paths = parse_bindings(admission_specs, "admission")

    kit_raw = load_path(kit, "kit")
    brief_raw = load_path(brief, "learner brief")
    kit_value = load_json_bytes(kit_raw, "kit")
    load_json_bytes(brief_raw, "learner brief")

    resources, admission_bytes, catalog_raw = source_admission_rows(source_paths, admission_paths)

    try:
        context = factory.build_context(
            kit,
            brief,
            [f"{source_id}={source_paths[source_id]}" for source_id in sorted(source_paths)],
        )
        quality_report = quality.analyze_package(kit_value)
    except (factory.FactoryInputError, ValueError) as exc:
        raise HandoffInputError(f"factory eligibility: {exc}") from exc

    if not quality_report["canonicalValid"]:
        raise HandoffInputError("candidate is canonical-invalid")
    if quality_report["qualityBand"] not in {"STRONG", "EXCELLENT_BY_PROFILE"}:
        raise HandoffInputError(
            f"candidate is not factory-eligible: qualityBand={quality_report['qualityBand']}"
        )

    versions = {row["resourceId"]: row["version"] for row in resources}
    expected_resources = [
        {
            "schema": reliability.RESOURCE_SCHEMA,
            "resourceId": row["sourceId"],
            "version": versions[row["sourceId"]],
            "bytes": row["bytes"],
            "sha256": row["sha256"],
        }
        for row in context["sources"]
    ]
    if resources != expected_resources:
        raise HandoffInputError("resource identities do not match FactoryContext source binding")

    reviewer_skill = load_path(REVIEWER_SKILL_PATH, "reviewer skill")
    review_request = REVIEW_REQUEST.encode("utf-8")
    context_raw = canonical(context)
    quality_raw = canonical(quality_report)

    members: dict[str, bytes] = {
        ROLE_PATHS["candidate"]: kit_raw,
        ROLE_PATHS["learner-brief"]: brief_raw,
        ROLE_PATHS["factory-context"]: context_raw,
        ROLE_PATHS["quality-report"]: quality_raw,
        ROLE_PATHS["reviewer-skill"]: reviewer_skill,
        ROLE_PATHS["review-request"]: review_request,
    }
    records = [
        artifact("candidate", ROLE_PATHS["candidate"], kit_raw),
        artifact("learner-brief", ROLE_PATHS["learner-brief"], brief_raw),
        artifact("factory-context", ROLE_PATHS["factory-context"], context_raw),
        artifact("quality-report", ROLE_PATHS["quality-report"], quality_raw),
        artifact("reviewer-skill", ROLE_PATHS["reviewer-skill"], reviewer_skill),
        artifact("review-request", ROLE_PATHS["review-request"], review_request),
    ]
    if catalog_raw is not None:
        catalog_path = OPTIONAL_ROLE_PATHS["source-catalog"]
        members[catalog_path] = catalog_raw
        records.append(artifact("source-catalog", catalog_path, catalog_raw))

    for resource in resources:
        source_id = resource["resourceId"]
        source_data = load_path(source_paths[source_id], f"source {source_id}")
        source_member = f"sources/{source_id}{source_suffix(source_data)}"
        admission_member = f"source-admission/{source_id}.json"
        members[source_member] = source_data
        members[admission_member] = admission_bytes[source_id]
        records.append(artifact("source", source_member, source_data))
        records.append(artifact("source-admission", admission_member, admission_bytes[source_id]))

    records.sort(key=lambda item: item["path"])
    core = {
        "schema": HANDOFF_SCHEMA,
        "profile": HANDOFF_PROFILE,
        "factoryMain": FACTORY_BASELINE,
        "target": target_from_context(context),
        "reviewEvidenceSourceIds": sorted(source_paths),
        "independence": {
            "reviewerContextMustBeSeparate": True,
            "authorScratchpadSeenMustBe": False,
            "authorActiveContextReusedMustBe": False,
        },
        "resources": resources,
        "artifacts": records,
    }
    manifest = {**core, "bundleDigest": digest(core)}
    members["review-handoff.json"] = canonical(manifest)
    archive_raw = zip_bytes(members)

    input_paths = {kit.resolve(), brief.resolve()}
    input_paths.update(path.resolve() for path in source_paths.values())
    input_paths.update(path.resolve() for path in admission_paths.values())
    if out.resolve() in input_paths:
        raise HandoffInputError("output path must not overwrite any input")

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(archive_raw)
    except OSError as exc:
        raise HandoffInputError(f"output: {exc}") from exc

    verified = verify_review_bundle(out)
    if verified["manifest"] != manifest:
        raise HandoffInputError("self-verification changed the handoff manifest")

    return {
        "schema": RESULT_SCHEMA,
        "verdict": PASS_PREPARED,
        "bundleDigest": manifest["bundleDigest"],
        "bundleSha256": sha(archive_raw),
        "bundleBytes": len(archive_raw),
        "target": manifest["target"],
        "reviewEvidenceSourceIds": manifest["reviewEvidenceSourceIds"],
    }


def validate_manifest(value: Any) -> dict[str, Any]:
    manifest = exact(
        value,
        {
            "schema",
            "profile",
            "factoryMain",
            "target",
            "reviewEvidenceSourceIds",
            "independence",
            "resources",
            "artifacts",
            "bundleDigest",
        },
        "review handoff",
    )
    if manifest["schema"] != HANDOFF_SCHEMA or manifest["profile"] != HANDOFF_PROFILE:
        raise HandoffInputError("unsupported review handoff schema/profile")
    if not SHA40.fullmatch(nonempty(manifest["factoryMain"], "factoryMain")):
        raise HandoffInputError("factoryMain must be an exact lowercase SHA40")
    if manifest["factoryMain"] != FACTORY_BASELINE:
        raise HandoffInputError("factoryMain does not match this handoff implementation baseline")

    target = exact(
        manifest["target"],
        {"contextDigest", "kitSha256", "sourceSetDigest", "briefSha256"},
        "target",
    )
    for key, value in target.items():
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            raise HandoffInputError(f"target.{key} is invalid")

    independence = exact(
        manifest["independence"],
        {
            "reviewerContextMustBeSeparate",
            "authorScratchpadSeenMustBe",
            "authorActiveContextReusedMustBe",
        },
        "independence",
    )
    if independence != {
        "reviewerContextMustBeSeparate": True,
        "authorScratchpadSeenMustBe": False,
        "authorActiveContextReusedMustBe": False,
    }:
        raise HandoffInputError("handoff independence contract mismatch")

    source_ids = manifest["reviewEvidenceSourceIds"]
    if (
        not isinstance(source_ids, list)
        or not source_ids
        or source_ids != sorted(source_ids)
        or len(source_ids) != len(set(source_ids))
    ):
        raise HandoffInputError("reviewEvidenceSourceIds must be a sorted unique non-empty list")
    for source_id in source_ids:
        if not isinstance(source_id, str) or not factory.SOURCE_ID.fullmatch(source_id):
            raise HandoffInputError("invalid review evidence source ID")

    resources = manifest["resources"]
    if not isinstance(resources, list) or not resources:
        raise HandoffInputError("resources must be a non-empty list")
    seen_resources: set[str] = set()
    for index, row in enumerate(resources):
        row = exact(
            row,
            {"schema", "resourceId", "version", "bytes", "sha256"},
            f"resources[{index}]",
        )
        resource_id = nonempty(row["resourceId"], f"resources[{index}].resourceId")
        if row["schema"] != reliability.RESOURCE_SCHEMA or not factory.SOURCE_ID.fullmatch(resource_id):
            raise HandoffInputError("invalid resource identity")
        if resource_id in seen_resources:
            raise HandoffInputError("duplicate resourceId")
        seen_resources.add(resource_id)
        if not reliability.VERSION.fullmatch(nonempty(row["version"], "resource.version")):
            raise HandoffInputError("invalid resource version")
        if isinstance(row["bytes"], bool) or not isinstance(row["bytes"], int) or row["bytes"] < 0:
            raise HandoffInputError("resource bytes must be an integer >= 0")
        if not isinstance(row["sha256"], str) or not SHA256.fullmatch(row["sha256"]):
            raise HandoffInputError("invalid resource sha256")
    if resources != sorted(resources, key=lambda item: item["resourceId"]):
        raise HandoffInputError("resources must be sorted")
    if sorted(seen_resources) != source_ids:
        raise HandoffInputError("resource IDs must equal reviewEvidenceSourceIds")

    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise HandoffInputError("artifacts must be a non-empty list")
    paths: set[str] = set()
    roles: dict[str, list[str]] = {}
    for index, row in enumerate(artifacts):
        row = exact(row, {"role", "path", "bytes", "sha256"}, f"artifacts[{index}]")
        role = nonempty(row["role"], f"artifacts[{index}].role")
        if role not in ALL_ROLES:
            raise HandoffInputError(f"unsupported artifact role {role!r}")
        path = safe_member_name(nonempty(row["path"], f"artifacts[{index}].path"))
        if path in paths:
            raise HandoffInputError(f"duplicate artifact path {path!r}")
        paths.add(path)
        roles.setdefault(role, []).append(path)
        if isinstance(row["bytes"], bool) or not isinstance(row["bytes"], int) or row["bytes"] < 0:
            raise HandoffInputError("artifact bytes must be an integer >= 0")
        if not isinstance(row["sha256"], str) or not SHA256.fullmatch(row["sha256"]):
            raise HandoffInputError("invalid artifact sha256")
    if artifacts != sorted(artifacts, key=lambda item: item["path"]):
        raise HandoffInputError("artifacts must be sorted by path")

    for role, expected_path in ROLE_PATHS.items():
        if roles.get(role) != [expected_path]:
            raise HandoffInputError(f"artifact role {role} must map exactly to {expected_path}")
    for role, expected_path in OPTIONAL_ROLE_PATHS.items():
        actual_paths = roles.get(role, [])
        if actual_paths not in ([], [expected_path]):
            raise HandoffInputError(
                f"optional artifact role {role} must be absent or map exactly to {expected_path}"
            )
    if len(roles.get("source", [])) != len(resources):
        raise HandoffInputError("source artifact count must match resources")
    if len(roles.get("source-admission", [])) != len(resources):
        raise HandoffInputError("source-admission artifact count must match resources")

    core = {key: item for key, item in manifest.items() if key != "bundleDigest"}
    if manifest["bundleDigest"] != digest(core):
        raise HandoffInputError("bundleDigest mismatch")
    return manifest


def read_archive(path: Path) -> tuple[bytes, dict[str, bytes], dict[str, Any]]:
    raw = load_path(path, "handoff bundle")
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos]
            if not infos or names != sorted(names):
                raise HandoffInputError("archive members must be sorted")
            if len(names) != len(set(names)):
                raise HandoffInputError("archive contains duplicate members")
            members: dict[str, bytes] = {}
            for info in infos:
                name = safe_member_name(info.filename)
                if info.is_dir():
                    raise HandoffInputError("archive directory entries are not allowed")
                if info.compress_type != zipfile.ZIP_STORED:
                    raise HandoffInputError("archive members must use ZIP_STORED")
                if tuple(info.date_time) != FIXED_ZIP_TIME:
                    raise HandoffInputError("archive member timestamp is not canonical")
                if info.create_system != 3:
                    raise HandoffInputError("archive member create_system is not canonical")
                if (info.external_attr >> 16) != FILE_MODE:
                    raise HandoffInputError("archive member mode is not canonical")
                if info.flag_bits & 0x1:
                    raise HandoffInputError("encrypted archive members are forbidden")
                members[name] = zf.read(info)
    except zipfile.BadZipFile as exc:
        raise HandoffInputError(f"handoff bundle: invalid ZIP: {exc}") from exc

    if "review-handoff.json" not in members:
        raise HandoffInputError("review-handoff.json is missing")
    manifest = load_json_bytes(members["review-handoff.json"], "review-handoff.json")
    manifest = validate_manifest(manifest)
    if members["review-handoff.json"] != canonical(manifest):
        raise HandoffInputError("review-handoff.json must use canonical JSON bytes")

    artifact_rows = {row["path"]: row for row in manifest["artifacts"]}
    expected_names = sorted(set(artifact_rows) | {"review-handoff.json"})
    if sorted(members) != expected_names:
        extra = sorted(set(members) - set(expected_names))
        missing = sorted(set(expected_names) - set(members))
        raise HandoffInputError(f"archive members mismatch; missing={missing} extra={extra}")

    for path_name, row in artifact_rows.items():
        data = members[path_name]
        if len(data) != row["bytes"] or sha(data) != row["sha256"]:
            raise HandoffInputError(f"artifact digest mismatch: {path_name}")
    return raw, members, manifest


def verify_embedded_authorities(
    members: dict[str, bytes],
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if members[ROLE_PATHS["reviewer-skill"]] != load_path(REVIEWER_SKILL_PATH, "reviewer skill"):
        raise HandoffInputError("embedded reviewer skill differs from repository authority")
    if members[ROLE_PATHS["review-request"]] != REVIEW_REQUEST.encode("utf-8"):
        raise HandoffInputError("embedded REVIEW_REQUEST.md differs from deterministic template")

    catalog_path = OPTIONAL_ROLE_PATHS["source-catalog"]
    catalog: dict[str, Any] | None = None
    catalog_sha: str | None = None
    if catalog_path in members:
        if members[catalog_path] != load_path(CATALOG_PATH, "source catalog"):
            raise HandoffInputError("embedded source catalog differs from repository authority")
        catalog_raw = members[catalog_path]
        catalog_value = load_json_bytes(catalog_raw, "source-catalog.json")
        try:
            catalog = source_admission.validate_catalog(catalog_value)
        except source_admission.SourceAdmissionError as exc:
            raise HandoffInputError(f"embedded source catalog: {exc}") from exc
        catalog_sha = sha(catalog_raw)

    resources = {row["resourceId"]: row for row in manifest["resources"]}
    source_member_by_id: dict[str, str] = {}
    for source_id in resources:
        candidates = [
            candidate
            for suffix in SOURCE_MEMBER_SUFFIXES
            if (candidate := f"sources/{source_id}{suffix}") in members
        ]
        if len(candidates) != 1:
            raise HandoffInputError(f"source artifact path for {source_id} is not unique")
        source_member = candidates[0]
        source_data = members[source_member]
        expected = f"sources/{source_id}{source_suffix(source_data)}"
        if source_member != expected:
            raise HandoffInputError(f"source artifact extension mismatch for {source_id}")
        row = resources[source_id]
        if row["bytes"] != len(source_data) or row["sha256"] != sha(source_data):
            raise HandoffInputError(f"resource/source binding mismatch for {source_id}")
        source_member_by_id[source_id] = source_member

    benchmark_admissions = 0
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        kit_path = temp / "candidate.json"
        brief_path = temp / "brief.json"
        kit_path.write_bytes(members[ROLE_PATHS["candidate"]])
        brief_path.write_bytes(members[ROLE_PATHS["learner-brief"]])
        source_paths: dict[str, Path] = {}

        for source_id, resource in sorted(resources.items()):
            source_path = temp / f"{source_id}.source"
            source_path.write_bytes(members[source_member_by_id[source_id]])
            source_paths[source_id] = source_path

            admission_path = f"source-admission/{source_id}.json"
            record_value = load_json_bytes(members[admission_path], admission_path)
            schema = record_value.get("schema") if isinstance(record_value, dict) else None

            if schema == source_admission.ADMISSION_SCHEMA:
                benchmark_admissions += 1
                if catalog is None or catalog_sha is None:
                    raise HandoffInputError(
                        f"{admission_path}: benchmark admission requires embedded source catalog"
                    )
                try:
                    record = source_admission.verify_admission(record_value)
                except source_admission.SourceAdmissionError as exc:
                    raise HandoffInputError(f"{admission_path}: {exc}") from exc
                if members[admission_path] != canonical(record):
                    raise HandoffInputError(f"{admission_path} must use canonical JSON bytes")
                if record["catalogSha256"] != catalog_sha:
                    raise HandoffInputError(f"{admission_path}: catalog binding mismatch")
                if record["decision"]["verdict"] != source_admission.PASS:
                    raise HandoffInputError(f"{admission_path}: source admission is not PASS")
                admission_source_id = record["source"]["sourceId"]
                if record["source"]["version"] != resource["version"]:
                    raise HandoffInputError(f"{admission_path}: resource version mismatch")
                rebuilt = source_admission.build_admission(
                    catalog,
                    catalog_sha,
                    admission_source_id,
                    record["useContext"],
                    source_path,
                    list(record["acceptedConditions"]),
                    record["source"]["version"],
                )
                if rebuilt != record:
                    raise HandoffInputError(f"{admission_path}: admission does not reproduce")
            elif schema == transient_source_admission.ADMISSION_SCHEMA:
                try:
                    record = transient_source_admission.verify_admission(record_value)
                    transient_source_admission.reproduce_admission(record, source_path)
                except transient_source_admission.TransientSourceAdmissionError as exc:
                    raise HandoffInputError(f"{admission_path}: {exc}") from exc
                if members[admission_path] != canonical(record):
                    raise HandoffInputError(f"{admission_path} must use canonical JSON bytes")
                if record["decision"]["verdict"] != transient_source_admission.PASS:
                    raise HandoffInputError(f"{admission_path}: transient source admission is not PASS")
                declaration = record["declaration"]
                if declaration["sourceId"] != source_id:
                    raise HandoffInputError(f"{admission_path}: sourceId mismatch")
                if declaration["version"] != resource["version"]:
                    raise HandoffInputError(f"{admission_path}: resource version mismatch")
            else:
                raise HandoffInputError(
                    f"{admission_path}: unsupported admission schema {schema!r}"
                )

        if benchmark_admissions == 0 and catalog is not None:
            raise HandoffInputError(
                "source-catalog.json is forbidden when no benchmark SourceAdmission is present"
            )

        try:
            rebuilt_context = factory.build_context(
                kit_path,
                brief_path,
                [f"{source_id}={source_paths[source_id]}" for source_id in sorted(source_paths)],
            )
        except factory.FactoryInputError as exc:
            raise HandoffInputError(f"embedded FactoryContext cannot be rebuilt: {exc}") from exc

        embedded_context = load_json_bytes(
            members[ROLE_PATHS["factory-context"]], "factory-context.json"
        )
        if members[ROLE_PATHS["factory-context"]] != canonical(embedded_context):
            raise HandoffInputError("factory-context.json must use canonical JSON bytes")
        if rebuilt_context != embedded_context:
            raise HandoffInputError("embedded FactoryContext does not match embedded inputs")
        if target_from_context(rebuilt_context) != manifest["target"]:
            raise HandoffInputError("handoff target does not match embedded FactoryContext")

        kit_value = load_json_bytes(members[ROLE_PATHS["candidate"]], "candidate.json")
        rebuilt_quality = quality.analyze_package(kit_value)
        embedded_quality = load_json_bytes(
            members[ROLE_PATHS["quality-report"]], "quality-report.json"
        )
        if members[ROLE_PATHS["quality-report"]] != canonical(embedded_quality):
            raise HandoffInputError("quality-report.json must use canonical JSON bytes")
        if rebuilt_quality != embedded_quality:
            raise HandoffInputError("embedded quality report does not match embedded candidate")
        if not rebuilt_quality["canonicalValid"] or rebuilt_quality["qualityBand"] not in {
            "STRONG",
            "EXCELLENT_BY_PROFILE",
        }:
            raise HandoffInputError("embedded candidate is not factory-eligible")

    return embedded_context, embedded_quality


def verify_review_bundle(path: Path) -> dict[str, Any]:
    raw, members, manifest = read_archive(path)
    context, quality_report = verify_embedded_authorities(members, manifest)
    return {
        "raw": raw,
        "members": members,
        "manifest": manifest,
        "context": context,
        "quality": quality_report,
    }


def review_source_ids(review: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for dimension in review["dimensions"].values():
        ids.update(row["sourceId"] for row in dimension["evidence"])
    for finding in review["findings"]:
        ids.update(row["sourceId"] for row in finding["evidence"])
    return ids


def consume_review_bundle(
    handoff_path: Path,
    review_path: Path,
    run_out: Path,
) -> dict[str, Any]:
    verified = verify_review_bundle(handoff_path)
    manifest = verified["manifest"]
    members = verified["members"]
    context = verified["context"]

    review_raw = load_path(review_path, "semantic review")
    review = load_json_bytes(review_raw, "semantic review")
    try:
        review = factory.validate_review(review, context)
    except factory.FactoryInputError as exc:
        raise HandoffInputError(f"semantic review: {exc}") from exc

    binding = factory.binding_reasons(review, context)
    if binding:
        raise HandoffInputError("semantic review target mismatch: " + ",".join(binding))
    if review["independence"]["authorScratchpadSeen"]:
        raise HandoffInputError("semantic review declares authorScratchpadSeen=true")
    if review["independence"]["authorActiveContextReused"]:
        raise HandoffInputError("semantic review declares authorActiveContextReused=true")

    allowed_ids = set(manifest["reviewEvidenceSourceIds"])
    used_ids = review_source_ids(review)
    if not used_ids.issubset(allowed_ids):
        raise HandoffInputError(
            f"semantic review uses source IDs outside handoff allowlist: {sorted(used_ids-allowed_ids)}"
        )
    inconsistent = [
        reason
        for reason in factory.semantic_reasons(review)
        if reason.startswith("INCONSISTENT_REVIEW_VERDICT:")
    ]
    if inconsistent:
        raise HandoffInputError("semantic review verdict is inconsistent with its findings/statuses")

    if run_out.resolve() in {handoff_path.resolve(), review_path.resolve()}:
        raise HandoffInputError("FactoryRun output must not overwrite handoff or review input")

    resources = {row["resourceId"]: row for row in manifest["resources"]}
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        kit_path = temp / "candidate.json"
        brief_path = temp / "learner-brief.json"
        temp_review = temp / "semantic-review.json"
        kit_path.write_bytes(members[ROLE_PATHS["candidate"]])
        brief_path.write_bytes(members[ROLE_PATHS["learner-brief"]])
        temp_review.write_bytes(review_raw)

        resource_specs: list[str] = []
        for source_id in sorted(resources):
            candidates = [name for name in members if name.startswith(f"sources/{source_id}.")]
            if len(candidates) != 1:
                raise HandoffInputError(f"source artifact path for {source_id} is not unique")
            source_path = temp / f"{source_id}.source"
            source_path.write_bytes(members[candidates[0]])
            resource_specs.append(
                f"{source_id}@{resources[source_id]['version']}={source_path}"
            )

        try:
            run = reliability.build_run(kit_path, brief_path, temp_review, resource_specs)
            reliability.verify_run(run)
        except reliability.ReliabilityInputError as exc:
            raise HandoffInputError(f"FactoryRun: {exc}") from exc

    run_raw = canonical(run)
    try:
        run_out.parent.mkdir(parents=True, exist_ok=True)
        run_out.write_bytes(run_raw)
    except OSError as exc:
        raise HandoffInputError(f"FactoryRun output: {exc}") from exc

    return {
        "schema": RESULT_SCHEMA,
        "verdict": PASS_CONSUMED,
        "bundleDigest": manifest["bundleDigest"],
        "reviewSha256": sha(review_raw),
        "reviewVerdict": review["verdict"],
        "factoryDecision": run["decision"],
        "runId": run["runId"],
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Atlas M3.3 portable review handoff")
    sub = root.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare-review")
    prepare.add_argument("--kit", type=Path, required=True)
    prepare.add_argument("--brief", type=Path, required=True)
    prepare.add_argument("--source", action="append", default=[], metavar="SOURCE_ID=PATH")
    prepare.add_argument("--admission", action="append", default=[], metavar="SOURCE_ID=PATH")
    prepare.add_argument("--out", type=Path, required=True)

    verify = sub.add_parser("verify-review")
    verify.add_argument("--handoff", type=Path, required=True)

    consume = sub.add_parser("consume-review")
    consume.add_argument("--handoff", type=Path, required=True)
    consume.add_argument("--review", type=Path, required=True)
    consume.add_argument("--run-out", type=Path, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare-review":
            result = prepare_review_bundle(
                args.kit, args.brief, args.source, args.admission, args.out
            )
        elif args.command == "verify-review":
            verified = verify_review_bundle(args.handoff)
            result = {
                "schema": RESULT_SCHEMA,
                "verdict": "PASS_REVIEW_HANDOFF_VERIFICATION_V1",
                "bundleDigest": verified["manifest"]["bundleDigest"],
                "bundleSha256": sha(verified["raw"]),
                "target": verified["manifest"]["target"],
            }
        else:
            result = consume_review_bundle(args.handoff, args.review, args.run_out)
        sys.stdout.write(canonical(result).decode("utf-8") + "\n")
        return 0
    except HandoffInputError as exc:
        sys.stdout.write(
            canonical({"schema": RESULT_SCHEMA, "verdict": HOLD_INPUT, "cause": str(exc)}).decode(
                "utf-8"
            )
            + "\n"
        )
        return factory.EXIT_CODES["HOLD_FACTORY_INPUT"]


if __name__ == "__main__":
    raise SystemExit(main())
