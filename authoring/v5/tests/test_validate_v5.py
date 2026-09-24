#!/usr/bin/env python3
"""Qualification tests for the explicit ``learnit.kit.v5`` contract."""
from __future__ import annotations

import copy
from pathlib import Path
import socket
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.v4 import validate_kit as v4
from authoring.v4.tests.test_validate_v4 import make_valid_v4, activity
from authoring.v5 import validate_kit as v5

ZERO = "sha256:" + "0" * 64
FAMILIES = ("lesson", "flashcard", "matching", "order", "classify", "qcm", "fill", "constructed")


def refresh_v5(package: dict) -> dict:
    package = copy.deepcopy(package)
    package["packageRevisionDigest"] = ZERO
    for course in package["courses"]:
        course["courseRevisionDigest"] = ZERO
        for item in course["activities"]:
            item["activityRevisionDigest"] = ZERO
    errors = v5.fill_new_digests(package)
    if errors:
        raise AssertionError(errors)
    return package


def make_valid_v5() -> dict:
    package = make_valid_v4()
    package["contract"] = "learnit.kit.v5"
    return refresh_v5(package)


def validate_v5(package: dict):
    schema = v5.load(v5.SCHEMA_PATH)
    return v5.validate(Path("candidate-v5.json"), package, schema)


def validate_v4(package: dict):
    schema = v4.load(v4.SCHEMA_PATH)
    return v4.validate(Path("candidate-v4.json"), package, schema)


def chain(package: dict, activity_type: str = "lesson") -> tuple[str, str, str]:
    item = activity(package, activity_type)
    course = package["courses"][0]
    return (
        item["activityRevisionDigest"],
        course["courseRevisionDigest"],
        package["packageRevisionDigest"],
    )


class V5ContractQualificationTests(unittest.TestCase):
    def test_v5_without_hints_or_references_passes(self):
        report = validate_v5(make_valid_v5())
        self.assertTrue(report.ok, report.errors)

    def test_every_activity_family_accepts_hints_and_references(self):
        for family in FAMILIES:
            package = make_valid_v5()
            target = activity(package, family)
            target["hints"] = ["Commence par identifier la donnée utile.", "Applique ensuite la relation au cas donné."]
            target["references"] = [{
                "url": "https://example.org/reference",
                "label": "Référence utile",
                "hook": "Complément vérifié pour approfondir cette activité.",
            }]
            report = validate_v5(refresh_v5(package))
            self.assertTrue(report.ok, (family, report.errors))

    def test_hint_cardinality_and_non_whitespace(self):
        for count in (0, 1, 3):
            package = make_valid_v5()
            activity(package, "lesson")["hints"] = [f"Indice {i + 1}" for i in range(count)]
            self.assertTrue(validate_v5(refresh_v5(package)).ok)

        package = make_valid_v5()
        activity(package, "lesson")["hints"] = ["a", "b", "c", "d"]
        self.assertFalse(validate_v5(refresh_v5(package)).ok)

        for invalid in ("", "   ", "\t"):
            package = make_valid_v5()
            activity(package, "lesson")["hints"] = [invalid]
            report = validate_v5(refresh_v5(package))
            self.assertFalse(report.ok)
            self.assertTrue(any("hint" in error.lower() or "pattern" in error.lower() for error in report.errors), report.errors)

    def test_reference_closed_shape_and_https_static_safety(self):
        package = make_valid_v5()
        activity(package, "lesson")["references"] = [{
            "url": "https://example.org/doc?q=1#part",
            "label": "Document",
            "hook": "Pourquoi cette ressource aide cette activité.",
        }]
        with mock.patch.object(socket, "create_connection", side_effect=AssertionError("network I/O attempted")):
            report = validate_v5(refresh_v5(package))
        self.assertTrue(report.ok, report.errors)

        invalid_urls = [
            "http://example.org",
            "javascript:alert(1)",
            "file:///tmp/x",
            "blob:https://example.org/x",
            "//example.org/x",
            "not a url",
            "https://user:secret@example.org/x",
            "https:///missing-host",
            "https://example.org\\evil",
        ]
        for url in invalid_urls:
            package = make_valid_v5()
            activity(package, "lesson")["references"] = [{"url": url, "label": "Doc", "hook": "Hook utile"}]
            report = validate_v5(refresh_v5(package))
            self.assertFalse(report.ok, url)

        for mutation in (
            {"url": "https://example.org", "hook": "Hook utile"},
            {"url": "https://example.org", "label": "Doc"},
            {"url": "https://example.org", "label": "Doc", "hook": "Hook utile", "role": "source"},
            {"assetId": "00000000-0000-4000-8000-000000000020", "placement": "content", "label": "Doc", "hook": "Hook utile"},
        ):
            package = make_valid_v5()
            activity(package, "lesson")["references"] = [mutation]
            self.assertFalse(validate_v5(refresh_v5(package)).ok, mutation)

    def test_reference_count_is_small_and_bounded(self):
        package = make_valid_v5()
        activity(package, "lesson")["references"] = [
            {"url": f"https://example.org/{i}", "label": f"Doc {i}", "hook": "Hook utile"}
            for i in range(4)
        ]
        self.assertFalse(validate_v5(refresh_v5(package)).ok)

    def test_v5_schema_is_closed_for_unknown_activity_fields(self):
        package = make_valid_v5()
        activity(package, "lesson")["unexpectedV5Field"] = True
        report = validate_v5(refresh_v5(package))
        self.assertFalse(report.ok)
        self.assertTrue(any("unevaluated" in error.lower() or "unexpectedV5Field" in error for error in report.errors), report.errors)

    def test_media_semantics_are_reused_and_remote_media_still_fails(self):
        package = make_valid_v5()
        self.assertTrue(validate_v5(package).ok)

        remote = make_valid_v5()
        remote["assets"][0]["format"] = "png"
        remote["assets"][0]["data"] = "https://example.org/image.png"
        report = validate_v5(refresh_v5(remote))
        self.assertFalse(report.ok)
        self.assertTrue(any("remote/active media" in error for error in report.errors), report.errors)

        unsafe = make_valid_v5()
        unsafe["assets"][0]["data"] = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        report = validate_v5(refresh_v5(unsafe))
        self.assertFalse(report.ok)
        self.assertTrue(any("SVG" in error for error in report.errors), report.errors)

    def test_hints_and_references_participate_in_digest_chain(self):
        base = make_valid_v5()
        base_chain = chain(base)

        hint = copy.deepcopy(base)
        activity(hint, "lesson")["hints"] = ["Premier indice"]
        hint = refresh_v5(hint)
        self.assertNotEqual(base_chain, chain(hint))

        reference = copy.deepcopy(base)
        activity(reference, "lesson")["references"] = [{
            "url": "https://example.org/a",
            "label": "Doc A",
            "hook": "Hook A",
        }]
        reference = refresh_v5(reference)
        self.assertNotEqual(base_chain, chain(reference))

        for field_name, new_value in (
            ("url", "https://example.org/b"),
            ("label", "Doc B"),
            ("hook", "Hook B"),
        ):
            changed = copy.deepcopy(reference)
            activity(changed, "lesson")["references"][0][field_name] = new_value
            changed = refresh_v5(changed)
            self.assertNotEqual(chain(reference), chain(changed), field_name)

    def test_hint_order_is_digest_bearing_and_revalidation_is_deterministic(self):
        package = make_valid_v5()
        activity(package, "lesson")["hints"] = ["Indice général", "Indice procédural"]
        first = refresh_v5(package)
        second = refresh_v5(first)
        self.assertEqual(chain(first), chain(second))

        reordered = copy.deepcopy(first)
        activity(reordered, "lesson")["hints"] = list(reversed(activity(reordered, "lesson")["hints"]))
        reordered = refresh_v5(reordered)
        self.assertNotEqual(chain(first), chain(reordered))

    def test_version_separation_and_v4_rejects_v5_fields(self):
        v5_package = make_valid_v5()
        self.assertFalse(validate_v4(v5_package).ok)

        v4_package = make_valid_v4()
        self.assertFalse(validate_v5(v4_package).ok)

        for field_name, value in (
            ("hints", ["Indice"]),
            ("references", [{"url": "https://example.org", "label": "Doc", "hook": "Hook"}]),
        ):
            candidate = make_valid_v4()
            activity(candidate, "lesson")[field_name] = value
            candidate["packageRevisionDigest"] = ZERO
            candidate["courses"][0]["courseRevisionDigest"] = ZERO
            activity(candidate, "lesson")["activityRevisionDigest"] = ZERO
            errors = v4.fill_new_digests(candidate)
            self.assertFalse(errors)
            report = validate_v4(candidate)
            self.assertFalse(report.ok, (field_name, report.errors))
            self.assertTrue(any("unevaluated" in error.lower() or field_name in error for error in report.errors), report.errors)

    def test_v4_digest_behavior_remains_deterministic(self):
        first = make_valid_v4()
        second = copy.deepcopy(first)
        self.assertEqual(
            (
                activity(first, "lesson")["activityRevisionDigest"],
                first["courses"][0]["courseRevisionDigest"],
                first["packageRevisionDigest"],
            ),
            (
                activity(second, "lesson")["activityRevisionDigest"],
                second["courses"][0]["courseRevisionDigest"],
                second["packageRevisionDigest"],
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
