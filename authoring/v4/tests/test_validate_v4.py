#!/usr/bin/env python3
"""Product evidence for ATLAS-WP-029 v4 canonical authoring validation."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.v4 import validate_kit as v4

ZERO = "sha256:" + "0" * 64


def uid(index: int) -> str:
    return f"00000000-0000-4000-8000-{index:012x}"


def _common(index: int, objective_id: str, activity_type: str, phase: str, minutes: int = 2) -> dict:
    return {
        "activityLineageId": uid(index),
        "activityRevisionId": uid(index + 1),
        "activityRevisionDigest": ZERO,
        "objectiveIds": [objective_id],
        "type": activity_type,
        "learningPhase": phase,
        "estimatedMinutes": minutes,
    }


def make_valid_v4() -> dict:
    objective_id = uid(10)
    asset_id = uid(20)

    lesson = _common(100, objective_id, "lesson", "comprehension", 3)
    lesson.update({
        "title": "Why the conservation relation matters",
        "body": "A conserved quantity keeps the same total across the bounded transformation described in the source example.",
        "keyPoints": ["Track the same quantity before and after the transformation."],
        "contextNote": "Use the relation only inside the stated assumptions.",
        "media": [{"assetId": asset_id, "placement": "content", "display": "contained", "zoomable": False}],
    })

    flashcard = _common(110, objective_id, "flashcard", "activation", 1)
    flashcard.update({
        "front": "What stays invariant in the source transformation?",
        "back": "The total conserved quantity.",
        "explanation": "The source relation equates the total before and after the transformation.",
    })

    matching = _common(120, objective_id, "matching", "application", 3)
    matching.update({
        "prompt": "Associate each situation with the corresponding interpretation.",
        "explanation": "Each situation maps to exactly one source-supported interpretation.",
        "difficulty": "medium",
        "assessmentRole": "practice",
        "leftItems": [
            {"itemId": uid(130), "label": "Total before transformation"},
            {"itemId": uid(131), "label": "Total after transformation"},
        ],
        "rightItems": [
            {"itemId": uid(132), "label": "Reference side"},
            {"itemId": uid(133), "label": "Compared side"},
        ],
        "matches": [
            {"leftItemId": uid(130), "rightItemId": uid(132)},
            {"leftItemId": uid(131), "rightItemId": uid(133)},
        ],
    })

    order = _common(140, objective_id, "order", "application", 3)
    order.update({
        "prompt": "Reconstruct the method used to test the conservation relation.",
        "explanation": "The method identifies the quantity, computes both sides, then compares them.",
        "difficulty": "medium",
        "assessmentRole": "practice",
        "items": [
            {"itemId": uid(146), "label": "Compare both totals"},
            {"itemId": uid(144), "label": "Identify the conserved quantity"},
            {"itemId": uid(145), "label": "Compute the two totals"},
        ],
        "correctOrder": [uid(144), uid(145), uid(146)],
    })

    classify = _common(150, objective_id, "classify", "application", 3)
    classify.update({
        "prompt": "Sort each statement by whether it respects the source assumptions.",
        "explanation": "The source relation is valid only under its stated assumptions.",
        "difficulty": "medium",
        "assessmentRole": "practice",
        "buckets": [
            {"bucketId": uid(157), "label": "Assumption respected"},
            {"bucketId": uid(158), "label": "Assumption violated"},
        ],
        "items": [
            {"itemId": uid(159), "label": "Same bounded system before and after"},
            {"itemId": uid(164), "label": "No external contribution"},
            {"itemId": uid(165), "label": "Different unrelated systems"},
            {"itemId": uid(166), "label": "Untracked external contribution"},
        ],
        "assignments": [
            {"itemId": uid(159), "bucketId": uid(157)},
            {"itemId": uid(164), "bucketId": uid(157)},
            {"itemId": uid(165), "bucketId": uid(158)},
            {"itemId": uid(166), "bucketId": uid(158)},
        ],
    })

    qcm = _common(160, objective_id, "qcm", "validation", 2)
    qcm.update({
        "prompt": "Which statement is compatible with the conservation relation?",
        "explanation": "The correct choice preserves the same total under the source assumptions.",
        "difficulty": "medium",
        "assessmentRole": "validation",
        "choices": [
            {"choiceId": uid(162), "label": "The total is unchanged."},
            {"choiceId": uid(163), "label": "The total changes arbitrarily."},
        ],
        "correctChoiceId": uid(162),
    })

    fill = _common(170, objective_id, "fill", "application", 2)
    fill.update({
        "prompt": "Complete the bounded relation.",
        "explanation": "The same total appears on both sides of the relation.",
        "difficulty": "easy",
        "assessmentRole": "practice",
        "segments": [{"text": "before = "}, {"slotId": uid(172)}],
        "tokens": [{"tokenId": uid(173), "label": "after", "maxUses": 1}],
        "answers": [{"slotId": uid(172), "tokenId": uid(173)}],
    })

    constructed = _common(180, objective_id, "constructed", "validation", 4)
    constructed.update({
        "prompt": "Explain why the two totals must agree under the stated assumptions.",
        "explanation": "A valid response states the conservation relation and its bounded assumptions.",
        "difficulty": "advanced",
        "assessmentRole": "validation",
        "acceptedResponses": [
            "The total is conserved because no contribution enters or leaves the bounded system.",
            "No contribution enters or leaves the bounded system, so the total is conserved.",
        ],
    })

    activities = [lesson, flashcard, matching, order, classify, qcm, fill, constructed]
    package = {
        "contract": "learnit.kit.v4",
        "packageLineageId": uid(1),
        "packageRevisionId": uid(2),
        "packageRevisionDigest": ZERO,
        "title": "Student V0.1 v4 authoring qualification",
        "versionLabel": "test-v4",
        "language": "en",
        "assets": [{
            "assetId": asset_id,
            "type": "image",
            "format": "svg",
            "alt": "Two equal totals connected by an equality sign",
            "pedagogicalRole": "concept_visual",
            "data": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 20"><rect x="1" y="1" width="98" height="18"/><text x="40" y="14">A = B</text></svg>',
        }],
        "courses": [{
            "courseLineageId": uid(3),
            "courseRevisionId": uid(4),
            "courseRevisionDigest": ZERO,
            "title": "Conservation relation",
            "estimatedMinutes": sum(a["estimatedMinutes"] for a in activities),
            "objectives": [{"objectiveId": objective_id, "label": "Apply and justify the conservation relation"}],
            "activities": activities,
        }],
    }
    errors = v4.fill_new_digests(package)
    if errors:
        raise AssertionError(errors)
    return package


def refresh(package: dict) -> dict:
    package = copy.deepcopy(package)
    package["packageRevisionDigest"] = ZERO
    for course in package["courses"]:
        course["courseRevisionDigest"] = ZERO
        for activity in course["activities"]:
            activity["activityRevisionDigest"] = ZERO
    errors = v4.fill_new_digests(package)
    if errors:
        raise AssertionError(errors)
    return package


def validate(package: dict):
    schema = v4.load(v4.SCHEMA_PATH)
    return v4.validate(Path("candidate-v4.json"), package, schema)


def activity(package: dict, activity_type: str) -> dict:
    return next(item for item in package["courses"][0]["activities"] if item["type"] == activity_type)


class V4CanonicalValidationTests(unittest.TestCase):
    def test_representative_v4_candidate_passes(self):
        report = validate(make_valid_v4())
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(8, sum(report.activities.values()))
        self.assertEqual(1, report.assets)
        self.assertEqual(1, report.media_refs)

    def test_lesson_and_flashcard_cannot_be_validation_evidence(self):
        for family in ("lesson", "flashcard"):
            package = make_valid_v4()
            activity(package, family)["learningPhase"] = "validation"
            package = refresh(package)
            report = validate(package)
            self.assertFalse(report.ok)
            self.assertTrue(any("cannot provide diagnostic or validation evidence" in error for error in report.errors), report.errors)

    def test_matching_incomplete_duplicate_and_unknown_references_fail(self):
        mutations = []
        p = make_valid_v4(); activity(p, "matching")["matches"].pop(); mutations.append(p)
        p = make_valid_v4(); m = activity(p, "matching"); m["matches"][1]["leftItemId"] = m["matches"][0]["leftItemId"]; mutations.append(p)
        p = make_valid_v4(); activity(p, "matching")["matches"][0]["rightItemId"] = uid(999); mutations.append(p)
        for package in mutations:
            report = validate(refresh(package))
            self.assertFalse(report.ok)
            self.assertTrue(any("matching" in error.lower() or "every left" in error.lower() or "every right" in error.lower() for error in report.errors), report.errors)

    def test_order_initial_sequence_must_not_expose_correct_order(self):
        package = make_valid_v4()
        order = activity(package, "order")
        by_id = {item["itemId"]: item for item in order["items"]}
        order["items"] = [by_id[item_id] for item_id in order["correctOrder"]]
        report = validate(refresh(package))
        self.assertFalse(report.ok)
        self.assertTrue(any("exposes correctOrder" in error for error in report.errors), report.errors)

    def test_classify_missing_duplicate_unknown_and_multilabel_fail(self):
        candidates = []
        p = make_valid_v4(); activity(p, "classify")["assignments"].pop(); candidates.append(p)
        p = make_valid_v4(); c = activity(p, "classify"); c["assignments"].append(copy.deepcopy(c["assignments"][0])); candidates.append(p)
        p = make_valid_v4(); activity(p, "classify")["assignments"][0]["bucketId"] = uid(997); candidates.append(p)
        p = make_valid_v4(); c = activity(p, "classify"); c["assignments"].append({"itemId": c["items"][0]["itemId"], "bucketId": c["buckets"][1]["bucketId"]}); candidates.append(p)
        for package in candidates:
            report = validate(refresh(package))
            self.assertFalse(report.ok)
            self.assertTrue(any("classify" in error.lower() for error in report.errors), report.errors)

    def test_constructed_preserves_canonical_text_match_uniqueness(self):
        package = make_valid_v4()
        constructed = activity(package, "constructed")
        constructed["acceptedResponses"] = ["Same answer", "  Same   answer  "]
        report = validate(refresh(package))
        self.assertFalse(report.ok)
        self.assertTrue(any("canonical-text-match-v1" in error for error in report.errors), report.errors)

    def test_unsafe_svg_and_remote_media_fail_closed(self):
        unsafe_payloads = [
            '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><div>bad</div></foreignObject></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><rect onclick="x()"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><a href="https://example.test/x"><text>x</text></a></svg>',
        ]
        for payload in unsafe_payloads:
            package = make_valid_v4()
            package["assets"][0]["data"] = payload
            report = validate(refresh(package))
            self.assertFalse(report.ok)
            self.assertTrue(any("SVG" in error for error in report.errors), report.errors)

        package = make_valid_v4()
        package["assets"][0]["format"] = "png"
        package["assets"][0]["data"] = "https://example.test/image.png"
        report = validate(refresh(package))
        self.assertFalse(report.ok)
        self.assertTrue(any("remote/active media" in error for error in report.errors), report.errors)

    def test_unused_media_is_warning_not_silent_quality_credit(self):
        package = make_valid_v4()
        activity(package, "lesson").pop("media")
        report = validate(refresh(package))
        self.assertTrue(report.ok, report.errors)
        self.assertTrue(any("unused package media" in warning for warning in report.warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
