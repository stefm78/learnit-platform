#!/usr/bin/env python3
"""Fail-closed causal probe for the Student V0.1 JOB07 rich-V4 pilot blocker.

This probe is intentionally read-only. It does not import or patch product code.
It proves that the exact current V4 contract and served-session integration are
structurally incompatible for the non-scored lesson/flashcard families.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "contracts/learnit-kit-v4.schema.json"
SURFACE = ROOT / "apps/learnit-next/src/integration/atlas/surface.js"
CLASSIC_RENDER = ROOT / "apps/learnit-next/src/ui/render.js"
SESSION = ROOT / "apps/learnit-next/src/core/session.js"
CANONICAL_FIXTURE = ROOT / "authoring/v4/tests/test_validate_v4.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    surface = SURFACE.read_text(encoding="utf-8")
    classic_render = CLASSIC_RENDER.read_text(encoding="utf-8")
    session = SESSION.read_text(encoding="utf-8")
    fixture = CANONICAL_FIXTURE.read_text(encoding="utf-8")

    unit_common = schema["$defs"]["unitCommon"]
    require(
        "assessmentRole" not in unit_common["properties"],
        "V4 unitCommon unexpectedly admits assessmentRole",
    )

    for family in ("lesson", "flashcard"):
        definition = schema["$defs"][family]
        refs = [
            item.get("$ref")
            for item in definition["allOf"]
            if isinstance(item, dict) and "$ref" in item
        ]
        own = next(
            item for item in definition["allOf"]
            if isinstance(item, dict) and "properties" in item
        )
        require("#/$defs/unitCommon" in refs, f"{family} no longer derives from unitCommon")
        require(
            definition.get("unevaluatedProperties") is False,
            f"{family} no longer fails closed on unevaluated properties",
        )
        require(
            "assessmentRole" not in own["properties"],
            f"{family} unexpectedly admits assessmentRole",
        )

    require(
        "course.activities.every(activity => (" in surface,
        "Atlas course compatibility predicate changed",
    )
    require(
        "typeof activity.assessmentRole === 'string'" in surface,
        "Atlas course compatibility no longer requires assessmentRole for every activity",
    )

    lesson_block = fixture.split(
        'lesson = _common(100, objective_id, "lesson"', 1
    )[1].split(
        'flashcard = _common(110, objective_id, "flashcard"', 1
    )[0]
    flashcard_block = fixture.split(
        'flashcard = _common(110, objective_id, "flashcard"', 1
    )[1].split(
        'matching = _common(120, objective_id, "matching"', 1
    )[0]
    require('"assessmentRole"' not in lesson_block, "canonical lesson fixture changed")
    require('"assessmentRole"' not in flashcard_block, "canonical flashcard fixture changed")
    require(
        "activities = [lesson, flashcard, matching, order, classify, qcm, fill, constructed]"
        in fixture,
        "canonical rich V4 family order changed",
    )

    require(
        "return course.activities.findIndex(activity => !complete.has(activity.activityRevisionId));"
        in session,
        "classic session no longer follows first incomplete authored activity",
    )
    require(
        "active = { courseRecord, mode: 'learn', currentIndex: 0 };" in session,
        "classic startCourse entry position changed",
    )
    require(
        "activity.type === 'qcm'" in classic_render
        and ": renderFillForm(activity" in classic_render,
        "classic served renderer no longer routes every non-QCM family to fill",
    )
    require(
        "for (const segment of activity.segments)" in classic_render,
        "fill fallback no longer requires activity.segments",
    )

    print("JOB07_BLOCKER_PROBE=PASS")
    print("RICH_V4_CONTRACT_VALID_NON_SCORED_FAMILIES=lesson,flashcard")
    print("ATLAS_COMPATIBILITY_REQUIRES_ASSESSMENT_ROLE_FOR_ALL=TRUE")
    print("RICH_V4_ATLAS_COMPATIBILITY=FAIL")
    print("CLASSIC_FALLBACK_FIRST_ACTIVITY=lesson")
    print("CLASSIC_FALLBACK_RENDERER=fill")
    print("PRODUCT_BLOCKER=ATLAS_SESSION_INTEGRATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
