#!/usr/bin/env python3
"""Deterministic M3.1 authoring core for existing canonical Atlas kits."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import sys
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "contracts/learnit-kit-v2.schema.json"
V2_VALIDATOR_PATH = ROOT / "authoring/v2/validate_kit.py"
ATLAS_VALIDATOR_PATH = ROOT / "authoring/v2/atlas/validate_atlas_content.py"
NAMESPACE = "learnit.authoring.m3.v1"
DRAFT_SCHEMA = "learnit.authoring.m3.draft.v1"
ZERO_DIGEST = "sha256:" + "0" * 64
MAX_SOURCE_BYTES = 2_000_000
PREVIEW_AUTHORITY = "AUTHOR_PREVIEW_ONLY"


class AuthoringError(ValueError):
    """Fail-closed authoring error with an author-facing diagnostic."""

    def __init__(self, code: str, cause: str, path: str = "$", value: Any = None):
        super().__init__(f"{code}: {path}: {cause}")
        self.code = code
        self.cause = cause
        self.path = path
        self.value = value

    def diagnostic(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "severity": "blocking",
            "code": self.code,
            "path": self.path,
            "cause": self.cause,
        }
        if self.value is not None:
            result["value"] = self.value
        return result


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuthoringError("AUTHORITY_LOAD_FAILED", f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_V2 = None
_ATLAS = None


def authorities():
    global _V2, _ATLAS
    if _V2 is None:
        _V2 = _load_module("learnit_m3_v2_authority", V2_VALIDATOR_PATH)
    if _ATLAS is None:
        _ATLAS = _load_module("learnit_m3_atlas_authority", ATLAS_VALIDATOR_PATH)
    return _V2, _ATLAS


def quality_authority():
    global _QUALITY
    if _QUALITY is None:
        _QUALITY = _load_module("learnit_m3_1_quality_authority", PEDAGOGICAL_QUALITY_PATH)
    return _QUALITY


def _pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise AuthoringError("DUPLICATE_JSON_KEY", "Duplicate JSON object key", "$", key)
        out[key] = value
    return out


def normalize(value: Any, path: str = "$") -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise AuthoringError("NON_CANONICAL_FLOAT", "Floating-point values are unsupported", path, value)
    if isinstance(value, list):
        return [normalize(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise AuthoringError("NON_STRING_KEY", "Object keys must be strings", path)
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in out:
                raise AuthoringError(
                    "NFC_KEY_COLLISION",
                    "Object keys collide after Unicode NFC normalization",
                    path,
                    normalized_key,
                )
            out[normalized_key] = normalize(item, f"{path}.{normalized_key}")
        return out
    raise AuthoringError(
        "NON_CANONICAL_VALUE", f"Unsupported canonical value {type(value).__name__}", path
    )


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_package_bytes(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, (bytes, bytearray)):
        raise AuthoringError("SOURCE_TYPE", "Imported source must be bytes")
    raw = bytes(raw)
    if not raw:
        raise AuthoringError("SOURCE_EMPTY", "Imported source is empty")
    if len(raw) > MAX_SOURCE_BYTES:
        raise AuthoringError("SOURCE_TOO_LARGE", "Imported source exceeds 2 MB")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AuthoringError("SOURCE_UTF8", "Imported source is not valid UTF-8", "$", str(exc)) from exc
    try:
        value = json.loads(text, object_pairs_hook=_pairs)
    except AuthoringError:
        raise
    except json.JSONDecodeError as exc:
        raise AuthoringError(
            "SOURCE_JSON",
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
        ) from exc
    if not isinstance(value, dict):
        raise AuthoringError("SOURCE_ROOT", "Kit root must be a JSON object")
    return normalize(value)


def _schema() -> dict[str, Any]:
    v2, _ = authorities()
    schema = v2.load(SCHEMA_PATH)
    if not isinstance(schema, dict):
        raise AuthoringError("SCHEMA_INVALID", "Canonical kit schema root must be an object")
    return schema


def _split_general_diagnostic(message: str) -> tuple[str, str]:
    if ": " in message:
        path, cause = message.split(": ", 1)
        return path.strip(), cause.strip()
    return "$", message


def _authoritative_diagnostics(package: dict[str, Any]) -> list[dict[str, Any]]:
    v2, atlas = authorities()
    diagnostics: list[dict[str, Any]] = []
    try:
        report = v2.validate(Path("<authoring-draft>"), package, _schema(), False)
    except Exception as exc:
        diagnostics.append(
            {
                "severity": "blocking",
                "code": "GENERAL_VALIDATOR_FAILURE",
                "path": "$",
                "cause": str(exc),
            }
        )
    else:
        for message in report.errors:
            path, cause = _split_general_diagnostic(message)
            diagnostics.append(
                {
                    "severity": "blocking",
                    "code": "GENERAL_VALIDATION",
                    "path": path,
                    "cause": cause,
                }
            )
        for message in report.warnings:
            path, cause = _split_general_diagnostic(message)
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "GENERAL_WARNING",
                    "path": path,
                    "cause": cause,
                }
            )
    try:
        atlas.validate_package(package)
    except Exception as exc:
        diagnostics.append(
            {
                "severity": "blocking",
                "code": "ATLAS_EDITORIAL_VALIDATION",
                "path": "$",
                "cause": str(exc),
            }
        )
    return diagnostics


def _validate_draft_shape(draft: Any) -> dict[str, Any]:
    if not isinstance(draft, dict) or draft.get("schema") != DRAFT_SCHEMA:
        raise AuthoringError("DRAFT_SHAPE", "Unsupported or missing M3 authoring draft schema")
    if draft.get("namespace") != NAMESPACE:
        raise AuthoringError("DRAFT_NAMESPACE", "Draft storage namespace is not the M3 authoring namespace")
    if not isinstance(draft.get("package"), dict) or not isinstance(draft.get("originalPackage"), dict):
        raise AuthoringError("DRAFT_PACKAGE", "Draft package payload is missing")
    source = draft.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("rawBase64"), str):
        raise AuthoringError("DRAFT_PROVENANCE", "Draft import provenance is missing")
    allocations = draft.get("revisionAllocations")
    if not isinstance(allocations, dict):
        raise AuthoringError("DRAFT_ALLOCATIONS", "Draft revision allocation state is missing")
    return draft


def _valid_uuid4(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        return False
    return parsed.version == 4 and str(parsed) == value.lower()


def _activity_semantic(activity: dict[str, Any]) -> Any:
    base = {
        key: activity.get(key)
        for key in (
            "prompt", "explanation", "difficulty", "learningPhase",
            "assessmentRole", "estimatedMinutes",
        )
    }
    if activity.get("type") == "qcm":
        base["choices"] = [choice.get("label") for choice in activity.get("choices", [])]
        base["correctChoiceId"] = activity.get("correctChoiceId")
    elif activity.get("type") == "fill":
        base["segments"] = [segment.get("text") if "text" in segment else None for segment in activity.get("segments", [])]
        base["tokens"] = [
            [token.get("label"), token.get("maxUses")] for token in activity.get("tokens", [])
        ]
        base["answers"] = [answer.get("tokenId") for answer in activity.get("answers", [])]
    return normalize(base)


def _draft_integrity_diagnostics(draft: dict[str, Any]) -> list[dict[str, Any]]:
    """Reject structural/identity tampering in the browser-persisted draft envelope."""
    diagnostics: list[dict[str, Any]] = []

    def add(code: str, path: str, cause: str, value: Any = None) -> None:
        item: dict[str, Any] = {
            "severity": "blocking", "code": code, "path": path, "cause": cause,
        }
        if value is not None:
            item["value"] = value
        diagnostics.append(item)

    package = draft["package"]
    original = draft["originalPackage"]
    allocations = draft["revisionAllocations"]

    if package.get("contract") != original.get("contract"):
        add("DRAFT_STRUCTURE", "$.contract", "Contract identity is immutable in M3.0")
    if package.get("packageLineageId") != original.get("packageLineageId"):
        add("LINEAGE_MUTATION", "$.packageLineageId", "Package lineage is immutable")

    current_courses = package.get("courses")
    original_courses = original.get("courses")
    if not isinstance(current_courses, list) or not isinstance(original_courses, list) or len(current_courses) != len(original_courses):
        add("DRAFT_STRUCTURE", "$.courses", "Course count/order is immutable in M3.0")
        return diagnostics

    allocated_courses = allocations.get("courses", [])
    allocated_activities = allocations.get("activities", [])
    if not isinstance(allocated_courses, list) or len(set(allocated_courses)) != len(allocated_courses):
        add("DRAFT_ALLOCATIONS", "$.revisionAllocations.courses", "Course allocation list is malformed")
        allocated_courses = []
    if not isinstance(allocated_activities, list) or len(set(allocated_activities)) != len(allocated_activities):
        add("DRAFT_ALLOCATIONS", "$.revisionAllocations.activities", "Activity allocation list is malformed")
        allocated_activities = []

    known_courses: set[str] = set()
    known_activities: set[str] = set()
    package_needs_revision = any(
        package.get(key) != original.get(key)
        for key in ("title", "description", "versionLabel", "language")
    )

    for ci, (course, before_course) in enumerate(zip(current_courses, original_courses)):
        cp = f"$.courses[{ci}]"
        if not isinstance(course, dict) or not isinstance(before_course, dict):
            add("DRAFT_STRUCTURE", cp, "Course objects are required")
            continue
        lineage = before_course.get("courseLineageId")
        if course.get("courseLineageId") != lineage:
            add("LINEAGE_MUTATION", cp + ".courseLineageId", "Course lineage is immutable")
        if isinstance(lineage, str):
            known_courses.add(lineage)

        objectives = course.get("objectives")
        before_objectives = before_course.get("objectives")
        course_direct_change = any(
            course.get(key) != before_course.get(key)
            for key in ("title", "subtitle", "estimatedMinutes")
        )
        if not isinstance(objectives, list) or not isinstance(before_objectives, list) or len(objectives) != len(before_objectives):
            add("DRAFT_STRUCTURE", cp + ".objectives", "Objective count/order is immutable in M3.0")
            continue
        for oi, (objective, before_objective) in enumerate(zip(objectives, before_objectives)):
            op = f"{cp}.objectives[{oi}]"
            if objective.get("objectiveId") != before_objective.get("objectiveId"):
                add("LINEAGE_MUTATION", op + ".objectiveId", "Objective identity is immutable")
            if objective.get("label") != before_objective.get("label"):
                course_direct_change = True

        activities = course.get("activities")
        before_activities = before_course.get("activities")
        if not isinstance(activities, list) or not isinstance(before_activities, list) or len(activities) != len(before_activities):
            add("DRAFT_STRUCTURE", cp + ".activities", "Activity count/order is immutable in M3.0")
            continue
        activity_change = False
        for ai, (activity, before_activity) in enumerate(zip(activities, before_activities)):
            ap = f"{cp}.activities[{ai}]"
            if not isinstance(activity, dict) or not isinstance(before_activity, dict):
                add("DRAFT_STRUCTURE", ap, "Activity objects are required")
                continue
            activity_lineage = before_activity.get("activityLineageId")
            if activity.get("activityLineageId") != activity_lineage:
                add("LINEAGE_MUTATION", ap + ".activityLineageId", "Activity lineage is immutable")
            if isinstance(activity_lineage, str):
                known_activities.add(activity_lineage)
            for key in ("type", "objectiveIds"):
                if activity.get(key) != before_activity.get(key):
                    add("DRAFT_STRUCTURE", ap + f".{key}", f"Activity {key} is structurally frozen in M3.0")

            if activity.get("type") == "qcm" and before_activity.get("type") == "qcm":
                choices, before_choices = activity.get("choices"), before_activity.get("choices")
                if not isinstance(choices, list) or not isinstance(before_choices, list) or len(choices) != len(before_choices):
                    add("DRAFT_STRUCTURE", ap + ".choices", "QCM choice count/order is immutable")
                else:
                    for xi, (choice, before_choice) in enumerate(zip(choices, before_choices)):
                        if choice.get("choiceId") != before_choice.get("choiceId"):
                            add("LINEAGE_MUTATION", f"{ap}.choices[{xi}].choiceId", "QCM choice identity is immutable")
            elif activity.get("type") == "fill" and before_activity.get("type") == "fill":
                segments, before_segments = activity.get("segments"), before_activity.get("segments")
                if not isinstance(segments, list) or not isinstance(before_segments, list) or len(segments) != len(before_segments):
                    add("DRAFT_STRUCTURE", ap + ".segments", "Fill segment count/order is immutable")
                else:
                    for si, (segment, before_segment) in enumerate(zip(segments, before_segments)):
                        current_slot, old_slot = segment.get("slotId"), before_segment.get("slotId")
                        if ("slotId" in segment) != ("slotId" in before_segment) or current_slot != old_slot:
                            add("DRAFT_STRUCTURE", f"{ap}.segments[{si}]", "Fill slot structure is immutable")
                tokens, before_tokens = activity.get("tokens"), before_activity.get("tokens")
                if not isinstance(tokens, list) or not isinstance(before_tokens, list) or len(tokens) != len(before_tokens):
                    add("DRAFT_STRUCTURE", ap + ".tokens", "Fill token count/order is immutable")
                else:
                    for ti, (token, before_token) in enumerate(zip(tokens, before_tokens)):
                        if token.get("tokenId") != before_token.get("tokenId"):
                            add("LINEAGE_MUTATION", f"{ap}.tokens[{ti}].tokenId", "Fill token identity is immutable")
                answers, before_answers = activity.get("answers"), before_activity.get("answers")
                if not isinstance(answers, list) or not isinstance(before_answers, list) or len(answers) != len(before_answers):
                    add("DRAFT_STRUCTURE", ap + ".answers", "Fill answer count/order is immutable")
                else:
                    for ni, (answer, before_answer) in enumerate(zip(answers, before_answers)):
                        if answer.get("slotId") != before_answer.get("slotId"):
                            add("DRAFT_STRUCTURE", f"{ap}.answers[{ni}].slotId", "Fill answer slot identity is immutable")

            semantic_changed = _activity_semantic(activity) != _activity_semantic(before_activity)
            activity_change = activity_change or semantic_changed
            allocated = activity_lineage in allocated_activities
            if semantic_changed and not allocated:
                add("STALE_ACTIVITY_REVISION", ap + ".activityRevisionId", "Semantic activity edit lacks a fresh draft revision")
            if allocated:
                if activity.get("activityRevisionId") == before_activity.get("activityRevisionId") or not _valid_uuid4(activity.get("activityRevisionId")):
                    add("STALE_ACTIVITY_REVISION", ap + ".activityRevisionId", "Allocated activity revision is not a fresh UUIDv4")
                if activity.get("activityRevisionDigest") != ZERO_DIGEST:
                    add("DRAFT_DIGEST_TAMPER", ap + ".activityRevisionDigest", "Allocated activity digest must remain pending until canonical materialization")
            else:
                if activity.get("activityRevisionId") != before_activity.get("activityRevisionId"):
                    add("REVISION_ID_TAMPER", ap + ".activityRevisionId", "Activity revision changed without an allocation")
                if activity.get("activityRevisionDigest") != before_activity.get("activityRevisionDigest"):
                    add("DRAFT_DIGEST_TAMPER", ap + ".activityRevisionDigest", "Unedited activity digest must remain unchanged")

        if course.get("atlasValidationIndependenceClaims") != before_course.get("atlasValidationIndependenceClaims"):
            add("CLAIM_TAMPER", cp + ".atlasValidationIndependenceClaims", "Atlas claims are canonical derived fields, not draft-editable fields")

        course_needs_revision = course_direct_change or activity_change
        package_needs_revision = package_needs_revision or course_needs_revision
        course_allocated = lineage in allocated_courses
        if course_needs_revision and not course_allocated:
            add("STALE_COURSE_REVISION", cp + ".courseRevisionId", "Semantic course content changed without a fresh course revision")
        if course_allocated:
            if course.get("courseRevisionId") == before_course.get("courseRevisionId") or not _valid_uuid4(course.get("courseRevisionId")):
                add("STALE_COURSE_REVISION", cp + ".courseRevisionId", "Allocated course revision is not a fresh UUIDv4")
            if course.get("courseRevisionDigest") != ZERO_DIGEST:
                add("DRAFT_DIGEST_TAMPER", cp + ".courseRevisionDigest", "Allocated course digest must remain pending until materialization")
        else:
            if course.get("courseRevisionId") != before_course.get("courseRevisionId"):
                add("REVISION_ID_TAMPER", cp + ".courseRevisionId", "Course revision changed without an allocation")
            if course.get("courseRevisionDigest") != before_course.get("courseRevisionDigest"):
                add("DRAFT_DIGEST_TAMPER", cp + ".courseRevisionDigest", "Unedited course digest must remain unchanged")

    unknown_courses = sorted(set(allocated_courses) - known_courses)
    unknown_activities = sorted(set(allocated_activities) - known_activities)
    if unknown_courses:
        add("DRAFT_ALLOCATIONS", "$.revisionAllocations.courses", "Unknown course lineage in allocation state", unknown_courses)
    if unknown_activities:
        add("DRAFT_ALLOCATIONS", "$.revisionAllocations.activities", "Unknown activity lineage in allocation state", unknown_activities)

    package_allocated = allocations.get("package") is True
    if package_needs_revision and not package_allocated:
        add("STALE_PACKAGE_REVISION", "$.packageRevisionId", "Semantic package content changed without a fresh package revision")
    if package_allocated:
        if package.get("packageRevisionId") == original.get("packageRevisionId") or not _valid_uuid4(package.get("packageRevisionId")):
            add("STALE_PACKAGE_REVISION", "$.packageRevisionId", "Allocated package revision is not a fresh UUIDv4")
        if package.get("packageRevisionDigest") != ZERO_DIGEST:
            add("DRAFT_DIGEST_TAMPER", "$.packageRevisionDigest", "Allocated package digest must remain pending until materialization")
        if draft.get("dirty") is not True:
            add("DRAFT_DIRTY_STATE", "$.dirty", "Allocated draft revision must be marked dirty")
    else:
        if package.get("packageRevisionId") != original.get("packageRevisionId"):
            add("REVISION_ID_TAMPER", "$.packageRevisionId", "Package revision changed without an allocation")
        if package.get("packageRevisionDigest") != original.get("packageRevisionDigest"):
            add("DRAFT_DIGEST_TAMPER", "$.packageRevisionDigest", "Unedited package digest must remain unchanged")
        if draft.get("dirty") not in (False, None):
            add("DRAFT_DIRTY_STATE", "$.dirty", "Unallocated draft cannot be marked dirty")

    return diagnostics


def _assert_draft_integrity(draft: dict[str, Any]) -> None:
    diagnostics = _draft_integrity_diagnostics(draft)
    if diagnostics:
        first = diagnostics[0]
        raise AuthoringError(first["code"], first["cause"], first["path"], first.get("value"))


def _materialize(package: dict[str, Any]) -> dict[str, Any]:
    _, atlas = authorities()
    value = copy.deepcopy(normalize(package))
    try:
        atlas.rewrite_claims(value)
        for course in value.get("courses", []):
            for activity in course.get("activities", []):
                activity["activityRevisionDigest"] = atlas.revision_digest(
                    activity, "activityRevisionDigest"
                )
            course["courseRevisionDigest"] = atlas.revision_digest(
                course, "courseRevisionDigest"
            )
        value["packageRevisionDigest"] = atlas.revision_digest(
            value, "packageRevisionDigest"
        )
    except Exception as exc:
        raise AuthoringError(
            "MATERIALIZATION_FAILED",
            f"Atlas claim/digest materialization failed: {exc}",
        ) from exc
    return value


def create_draft(raw: bytes, source_name: str = "kit.json") -> dict[str, Any]:
    package = parse_package_bytes(raw)
    materialized = _materialize(package)
    diagnostics = _authoritative_diagnostics(materialized)
    blocking = [item for item in diagnostics if item["severity"] == "blocking"]
    if blocking:
        first = blocking[0]
        raise AuthoringError(
            "IMPORT_REJECTED",
            first["cause"],
            first.get("path", "$"),
        )
    if materialized != package:
        raise AuthoringError(
            "IMPORT_NON_CANONICAL_REVISION",
            "Imported Atlas kit has stale claims or revision digests",
        )
    return {
        "schema": DRAFT_SCHEMA,
        "namespace": NAMESPACE,
        "source": {
            "name": str(source_name or "kit.json"),
            "sha256": sha256_bytes(bytes(raw)),
            "rawBase64": base64.b64encode(bytes(raw)).decode("ascii"),
        },
        "originalPackage": copy.deepcopy(package),
        "package": copy.deepcopy(package),
        "revisionAllocations": {
            "package": False,
            "courses": [],
            "activities": [],
        },
        "dirty": False,
    }


def _uuid4(factory: Callable[[], Any]) -> str:
    raw = str(factory())
    try:
        parsed = uuid.UUID(raw)
    except ValueError as exc:
        raise AuthoringError("REVISION_UUID", "Revision factory did not return a UUID", "$", raw) from exc
    if parsed.version != 4:
        raise AuthoringError("REVISION_UUID", "Revision identity must be UUIDv4", "$", raw)
    return str(parsed)


def _allocate_package(package: dict[str, Any], allocations: dict[str, Any], factory: Callable[[], Any]) -> None:
    if not allocations.get("package"):
        package["packageRevisionId"] = _uuid4(factory)
        allocations["package"] = True
    package["packageRevisionDigest"] = ZERO_DIGEST


def _allocate_course(
    package: dict[str, Any], course_index: int, allocations: dict[str, Any], factory: Callable[[], Any]
) -> None:
    course = package["courses"][course_index]
    lineage = course["courseLineageId"]
    courses = allocations.setdefault("courses", [])
    if lineage not in courses:
        course["courseRevisionId"] = _uuid4(factory)
        courses.append(lineage)
    course["courseRevisionDigest"] = ZERO_DIGEST
    _allocate_package(package, allocations, factory)


def _allocate_activity(
    package: dict[str, Any], course_index: int, activity_index: int,
    allocations: dict[str, Any], factory: Callable[[], Any]
) -> None:
    activity = package["courses"][course_index]["activities"][activity_index]
    lineage = activity["activityLineageId"]
    activities = allocations.setdefault("activities", [])
    if lineage not in activities:
        activity["activityRevisionId"] = _uuid4(factory)
        activities.append(lineage)
    activity["activityRevisionDigest"] = ZERO_DIGEST
    _allocate_course(package, course_index, allocations, factory)


def _index(value: Any, index: Any, path: str) -> int:
    if type(index) is not int or index < 0 or not isinstance(value, list) or index >= len(value):
        raise AuthoringError("EDIT_PATH", "Invalid array index", path, index)
    return index


def _resolve_edit(package: dict[str, Any], path: list[Any]) -> tuple[Any, Any, str, tuple[str, int, int | None]]:
    """Return parent, key, printable path, and affected level metadata."""
    if not isinstance(path, list) or not path:
        raise AuthoringError("EDIT_PATH", "Edit path must be a non-empty array")

    if len(path) == 1 and path[0] in {"title", "description", "versionLabel", "language"}:
        return package, path[0], f"$.{path[0]}", ("package", -1, None)

    if len(path) < 3 or path[0] != "courses":
        raise AuthoringError("EDIT_PATH", "Field is outside the M3.0 editable surface")
    ci = _index(package.get("courses"), path[1], "$.courses")
    course = package["courses"][ci]

    if len(path) == 3 and path[2] in {"title", "subtitle", "estimatedMinutes"}:
        return course, path[2], f"$.courses[{ci}].{path[2]}", ("course", ci, None)

    if path[2] == "objectives" and len(path) == 5 and path[4] == "label":
        oi = _index(course.get("objectives"), path[3], f"$.courses[{ci}].objectives")
        objective = course["objectives"][oi]
        return objective, "label", f"$.courses[{ci}].objectives[{oi}].label", ("course", ci, None)

    if path[2] != "activities" or len(path) < 5:
        raise AuthoringError("EDIT_PATH", "Field is outside the M3.0 editable surface")
    ai = _index(course.get("activities"), path[3], f"$.courses[{ci}].activities")
    activity = course["activities"][ai]
    field = path[4]
    base = f"$.courses[{ci}].activities[{ai}]"

    if len(path) == 5 and field in {
        "prompt", "explanation", "difficulty", "learningPhase", "assessmentRole", "estimatedMinutes"
    }:
        return activity, field, f"{base}.{field}", ("activity", ci, ai)

    if activity.get("type") == "qcm":
        if field == "correctChoiceId" and len(path) == 5:
            return activity, field, f"{base}.correctChoiceId", ("activity", ci, ai)
        if field == "choices" and len(path) == 7 and path[6] == "label":
            xi = _index(activity.get("choices"), path[5], f"{base}.choices")
            return activity["choices"][xi], "label", f"{base}.choices[{xi}].label", ("activity", ci, ai)

    if activity.get("type") == "fill":
        if field == "segments" and len(path) == 7 and path[6] == "text":
            si = _index(activity.get("segments"), path[5], f"{base}.segments")
            segment = activity["segments"][si]
            if set(segment) != {"text"}:
                raise AuthoringError("EDIT_PATH", "Fill slot structure is not editable", f"{base}.segments[{si}]")
            return segment, "text", f"{base}.segments[{si}].text", ("activity", ci, ai)
        if field == "tokens" and len(path) == 7 and path[6] in {"label", "maxUses"}:
            ti = _index(activity.get("tokens"), path[5], f"{base}.tokens")
            return activity["tokens"][ti], path[6], f"{base}.tokens[{ti}].{path[6]}", ("activity", ci, ai)
        if field == "answers" and len(path) == 7 and path[6] == "tokenId":
            ni = _index(activity.get("answers"), path[5], f"{base}.answers")
            return activity["answers"][ni], "tokenId", f"{base}.answers[{ni}].tokenId", ("activity", ci, ai)

    raise AuthoringError("EDIT_PATH", "Field is outside the M3.0 editable surface", base)


def apply_edit(
    draft: dict[str, Any], path: list[Any], value: Any,
    uuid_factory: Callable[[], Any] = uuid.uuid4,
) -> dict[str, Any]:
    current = copy.deepcopy(_validate_draft_shape(draft))
    _assert_draft_integrity(current)
    package = current["package"]
    parent, key, printable, affected = _resolve_edit(package, path)
    normalized_value = normalize(value, printable)
    if parent.get(key) == normalized_value:
        return current
    parent[key] = normalized_value
    level, ci, ai = affected
    allocations = current["revisionAllocations"]
    if level == "package":
        _allocate_package(package, allocations, uuid_factory)
    elif level == "course":
        _allocate_course(package, ci, allocations, uuid_factory)
    elif level == "activity" and ai is not None:
        _allocate_activity(package, ci, ai, allocations, uuid_factory)
    else:
        raise AuthoringError("EDIT_LEVEL", "Unsupported revision allocation level")
    current["dirty"] = True
    return current


def validate_draft(draft: dict[str, Any]) -> dict[str, Any]:
    quality = None
    try:
        current = _validate_draft_shape(draft)
        diagnostics = _draft_integrity_diagnostics(current)
        if diagnostics:
            return {
                "ok": False,
                "exportAvailable": False,
                "diagnostics": diagnostics,
                "blockingCount": len(diagnostics),
                "warningCount": 0,
                "materializedSha256": None,
                "pedagogicalQuality": None,
            }
        materialized = _materialize(current["package"])
        diagnostics = _authoritative_diagnostics(materialized)
    except AuthoringError as exc:
        diagnostics = [exc.diagnostic()]
        materialized = None

    blocking = [item for item in diagnostics if item.get("severity") == "blocking"]
    if materialized is not None and not blocking:
        try:
            quality = quality_authority().analyze_package(materialized)
        except Exception as exc:
            diagnostics.append(
                {
                    "severity": "blocking",
                    "code": "PEDAGOGICAL_QUALITY_ENGINE_FAILURE",
                    "path": "$",
                    "cause": str(exc),
                }
            )
        else:
            if not quality.get("canonicalValid"):
                diagnostics.append(
                    {
                        "severity": "blocking",
                        "code": "PEDAGOGICAL_QUALITY_CANONICAL_DIVERGENCE",
                        "path": "$",
                        "cause": "Pedagogical quality authority rejected content already accepted by the Studio canonical validators",
                    }
                )

    blocking = [item for item in diagnostics if item.get("severity") == "blocking"]
    warnings = [item for item in diagnostics if item.get("severity") == "warning"]
    return {
        "ok": not blocking,
        "exportAvailable": not blocking,
        "diagnostics": diagnostics,
        "blockingCount": len(blocking),
        "warningCount": len(warnings),
        "materializedSha256": sha256_bytes(canonical_bytes(materialized)) if materialized is not None and not blocking else None,
        "pedagogicalQuality": quality if not blocking else None,
    }


def export_draft(draft: dict[str, Any]) -> tuple[bytes, str]:
    current = _validate_draft_shape(draft)
    _assert_draft_integrity(current)
    materialized = _materialize(current["package"])
    diagnostics = _authoritative_diagnostics(materialized)
    blocking = [item for item in diagnostics if item.get("severity") == "blocking"]
    if blocking:
        first = blocking[0]
        raise AuthoringError("EXPORT_BLOCKED", first["cause"], first.get("path", "$"))

    if current["package"] == current["originalPackage"]:
        try:
            raw = base64.b64decode(current["source"]["rawBase64"], validate=True)
        except Exception as exc:
            raise AuthoringError("DRAFT_PROVENANCE", "Stored source bytes are invalid") from exc
        parsed = parse_package_bytes(raw)
        if parsed != materialized:
            raise AuthoringError("NOOP_DRIFT", "No-op export source no longer matches the validated draft")
        return raw, sha256_bytes(raw)

    output = canonical_bytes(materialized)
    return output, sha256_bytes(output)


def reimport_export(draft: dict[str, Any], source_name: str = "export.json") -> dict[str, Any]:
    raw, _ = export_draft(draft)
    return create_draft(raw, source_name)


def build_preview(draft: dict[str, Any], course_index: int, activity_index: int) -> dict[str, Any]:
    current = _validate_draft_shape(draft)
    _assert_draft_integrity(current)
    package = current["package"]
    ci = _index(package.get("courses"), course_index, "$.courses")
    course = package["courses"][ci]
    ai = _index(course.get("activities"), activity_index, f"$.courses[{ci}].activities")
    activity = course["activities"][ai]
    objectives = {
        objective.get("objectiveId"): objective.get("label")
        for objective in course.get("objectives", [])
        if isinstance(objective, dict)
    }
    preview: dict[str, Any] = {
        "authority": PREVIEW_AUTHORITY,
        "disclaimer": "Aperçu auteur uniquement — aucune sémantique de recommandation, mémoire, transfert ou maîtrise apprenant.",
        "courseTitle": course.get("title"),
        "objectiveLabels": [objectives.get(item, item) for item in activity.get("objectiveIds", [])],
        "type": activity.get("type"),
        "prompt": activity.get("prompt"),
        "explanation": activity.get("explanation"),
        "difficulty": activity.get("difficulty"),
        "learningPhase": activity.get("learningPhase"),
        "assessmentRole": activity.get("assessmentRole"),
        "estimatedMinutes": activity.get("estimatedMinutes"),
    }
    if activity.get("type") == "qcm":
        correct = activity.get("correctChoiceId")
        preview["choices"] = [
            {"label": choice.get("label"), "correct": choice.get("choiceId") == correct}
            for choice in activity.get("choices", [])
        ]
    elif activity.get("type") == "fill":
        token_labels = {
            token.get("tokenId"): token.get("label") for token in activity.get("tokens", [])
        }
        answer_by_slot = {
            answer.get("slotId"): token_labels.get(answer.get("tokenId"), answer.get("tokenId"))
            for answer in activity.get("answers", [])
        }
        preview["segments"] = [
            {"text": segment["text"]}
            if "text" in segment
            else {"blank": segment.get("slotId"), "answer": answer_by_slot.get(segment.get("slotId"))}
            for segment in activity.get("segments", [])
        ]
        preview["tokens"] = [
            {"label": token.get("label"), "maxUses": token.get("maxUses")}
            for token in activity.get("tokens", [])
        ]
    else:
        raise AuthoringError("PREVIEW_TYPE", "M3.0 preview supports only existing QCM/fill activities")
    return preview


__all__ = [
    "AuthoringError",
    "DRAFT_SCHEMA",
    "NAMESPACE",
    "PREVIEW_AUTHORITY",
    "apply_edit",
    "build_preview",
    "canonical_bytes",
    "create_draft",
    "export_draft",
    "parse_package_bytes",
    "reimport_export",
    "sha256_bytes",
    "validate_draft",
]
