#!/usr/bin/env python3
"""Deterministic M3.0 authoring core for existing canonical Atlas kits."""
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
    try:
        current = _validate_draft_shape(draft)
        materialized = _materialize(current["package"])
        diagnostics = _authoritative_diagnostics(materialized)
    except AuthoringError as exc:
        diagnostics = [exc.diagnostic()]
        materialized = None
    blocking = [item for item in diagnostics if item.get("severity") == "blocking"]
    warnings = [item for item in diagnostics if item.get("severity") == "warning"]
    return {
        "ok": not blocking,
        "exportAvailable": not blocking,
        "diagnostics": diagnostics,
        "blockingCount": len(blocking),
        "warningCount": len(warnings),
        "materializedSha256": sha256_bytes(canonical_bytes(materialized)) if materialized is not None and not blocking else None,
    }


def export_draft(draft: dict[str, Any]) -> tuple[bytes, str]:
    current = _validate_draft_shape(draft)
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
