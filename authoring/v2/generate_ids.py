#!/usr/bin/env python3
"""Allocate persistent UUID v4 identifiers in a learnit.kit.v2 authoring draft.

Existing UUIDs are preserved. New UUIDs are allocated only with --write.
Temporary aliases use the explicit syntax ``@id:name`` and are replaced consistently
across definitions and references. Invalid non-alias identifiers are never rewritten.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable

UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
ALIAS_RE = re.compile(r"^@id:[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class AuthoringError(ValueError):
    """Raised when an identifier cannot be preserved or safely allocated."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuthoringError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuthoringError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def _is_uuid4(value: Any) -> bool:
    return isinstance(value, str) and UUID4_RE.fullmatch(value) is not None


def _is_alias(value: Any) -> bool:
    return isinstance(value, str) and ALIAS_RE.fullmatch(value) is not None


def _definition_locations(document: dict[str, Any]) -> Iterable[tuple[dict[str, Any], str, str]]:
    yield document, "packageLineageId", "package lineage"
    yield document, "packageRevisionId", "package revision"

    for course_index, course in enumerate(document.get("courses", [])):
        if not isinstance(course, dict):
            continue
        prefix = f"courses[{course_index}]"
        yield course, "courseLineageId", f"{prefix} lineage"
        yield course, "courseRevisionId", f"{prefix} revision"

        for objective_index, objective in enumerate(course.get("objectives", [])):
            if isinstance(objective, dict):
                yield objective, "objectiveId", f"{prefix}.objectives[{objective_index}]"

        for activity_index, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict):
                continue
            activity_prefix = f"{prefix}.activities[{activity_index}]"
            yield activity, "activityLineageId", f"{activity_prefix} lineage"
            yield activity, "activityRevisionId", f"{activity_prefix} revision"

            if activity.get("type") == "qcm":
                for choice_index, choice in enumerate(activity.get("choices", [])):
                    if isinstance(choice, dict):
                        yield choice, "choiceId", f"{activity_prefix}.choices[{choice_index}]"

            if activity.get("type") == "fill":
                for segment_index, segment in enumerate(activity.get("segments", [])):
                    if isinstance(segment, dict) and "slotId" in segment:
                        yield segment, "slotId", f"{activity_prefix}.segments[{segment_index}]"
                for token_index, token in enumerate(activity.get("tokens", [])):
                    if isinstance(token, dict):
                        yield token, "tokenId", f"{activity_prefix}.tokens[{token_index}]"


def _reference_locations(document: dict[str, Any]) -> Iterable[tuple[Any, Any, str]]:
    for course_index, course in enumerate(document.get("courses", [])):
        if not isinstance(course, dict):
            continue
        prefix = f"courses[{course_index}]"
        for activity_index, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict):
                continue
            activity_prefix = f"{prefix}.activities[{activity_index}]"
            objective_ids = activity.get("objectiveIds", [])
            if isinstance(objective_ids, list):
                for index in range(len(objective_ids)):
                    yield objective_ids, index, f"{activity_prefix}.objectiveIds[{index}]"

            if activity.get("type") == "qcm" and "correctChoiceId" in activity:
                yield activity, "correctChoiceId", f"{activity_prefix}.correctChoiceId"

            if activity.get("type") == "fill":
                for answer_index, answer in enumerate(activity.get("answers", [])):
                    if not isinstance(answer, dict):
                        continue
                    if "slotId" in answer:
                        yield answer, "slotId", f"{activity_prefix}.answers[{answer_index}].slotId"
                    if "tokenId" in answer:
                        yield answer, "tokenId", f"{activity_prefix}.answers[{answer_index}].tokenId"


def inspect(document: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    missing: list[str] = []
    alias_definitions: dict[str, list[str]] = {}

    for container, key, location in _definition_locations(document):
        if key not in container or container[key] in (None, ""):
            missing.append(location)
            continue
        value = container[key]
        if _is_uuid4(value):
            continue
        if _is_alias(value):
            alias_definitions.setdefault(value, []).append(location)
            continue
        raise AuthoringError(
            f"{location}: existing identifier {value!r} is neither a lowercase UUID v4 "
            "nor an @id: alias; refusing to replace it"
        )

    duplicate_aliases = {
        alias: locations for alias, locations in alias_definitions.items() if len(locations) > 1
    }
    if duplicate_aliases:
        details = "; ".join(
            f"{alias} defines multiple entities at {', '.join(locations)}"
            for alias, locations in sorted(duplicate_aliases.items())
        )
        raise AuthoringError(details)

    for container, key, location in _reference_locations(document):
        value = container[key]
        if _is_uuid4(value) or _is_alias(value):
            continue
        raise AuthoringError(
            f"{location}: reference {value!r} is neither a lowercase UUID v4 nor an @id: alias"
        )

    return missing, alias_definitions


def allocate(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str], int]:
    result = copy.deepcopy(document)
    missing, alias_definitions = inspect(result)
    alias_map = {alias: str(uuid.uuid4()) for alias in sorted(alias_definitions)}
    allocated_missing = 0

    for container, key, _location in _definition_locations(result):
        if key not in container or container[key] in (None, ""):
            container[key] = str(uuid.uuid4())
            allocated_missing += 1
        elif _is_alias(container[key]):
            container[key] = alias_map[container[key]]

    for container, key, _location in _reference_locations(result):
        value = container[key]
        if _is_alias(value):
            if value not in alias_map:
                raise AuthoringError(
                    f"reference alias {value!r} has no matching definition in this document"
                )
            container[key] = alias_map[value]

    # A second inspection guarantees that allocation left no aliases or invalid identities.
    remaining_missing, remaining_aliases = inspect(result)
    if remaining_missing or remaining_aliases:
        raise AuthoringError("internal allocation error: unresolved identifiers remain")
    return result, alias_map, allocated_missing


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preserve existing IDs and explicitly allocate missing or @id: aliased UUID v4 IDs."
    )
    parser.add_argument("kit", type=Path, help="learnit.kit.v2 JSON authoring draft")
    parser.add_argument(
        "--write",
        action="store_true",
        help="persist newly allocated UUIDs in place; without this flag no UUID is allocated",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        document = _load_json(args.kit)
        if not isinstance(document, dict):
            raise AuthoringError("the JSON root must be an object")
        missing, aliases = inspect(document)

        if not args.write:
            print(f"CHECK {args.kit}")
            print(f"existing identifiers preserved: yes")
            print(f"missing definition identifiers: {len(missing)}")
            print(f"explicit aliases awaiting allocation: {len(aliases)}")
            if missing:
                print("missing:")
                for location in missing:
                    print(f"  - {location}")
            if aliases:
                print("aliases:")
                for alias, locations in sorted(aliases.items()):
                    print(f"  - {alias}: {locations[0]}")
            if missing or aliases:
                print("no file changed; rerun with --write to allocate new UUID v4 values")
                return 1
            print("PASS: no allocation required; no file changed")
            return 0

        result, alias_map, allocated_missing = allocate(document)
        args.kit.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"UPDATED {args.kit}")
        print(f"new UUIDs for missing definitions: {allocated_missing}")
        print(f"new UUIDs for explicit aliases: {len(alias_map)}")
        print("existing UUIDs changed: 0")
        for alias, allocated in sorted(alias_map.items()):
            print(f"  {alias} -> {allocated}")
        return 0
    except AuthoringError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
