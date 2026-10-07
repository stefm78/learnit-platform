#!/usr/bin/env python3
"""Student V0.1 v4 compatibility evidence for the M3.1 quality engine."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from authoring.v2.atlas import pedagogical_quality as quality
from authoring.v4.tests.test_validate_v4 import activity, make_valid_v4, refresh


class StudentV01V4QualityTests(unittest.TestCase):
    def test_balanced_v4_candidate_is_canonical_and_excellent(self):
        report = quality.analyze_package(make_valid_v4())
        self.assertTrue(report["canonicalValid"], report)
        self.assertEqual("atlas.pedagogy.student-v0.1.v4", report["profile"])
        self.assertEqual("EXCELLENT_BY_PROFILE", report["qualityBand"], report["diagnostics"])

    def test_exposure_never_counts_as_validation_evidence(self):
        package = make_valid_v4()
        course = package["courses"][0]
        course["activities"] = [item for item in course["activities"] if item.get("assessmentRole") != "validation"]
        course["estimatedMinutes"] = sum(item["estimatedMinutes"] for item in course["activities"])
        package = refresh(package)
        report = quality.analyze_package(package)
        self.assertTrue(report["canonicalValid"], report)
        codes = {item["code"] for item in report["diagnostics"]}
        self.assertIn("PQ_V4_EXPOSURE_WITHOUT_VALIDATION", codes)
        self.assertEqual("COMPLETE", report["qualityBand"])

    def test_lesson_heavy_without_practice_is_warning(self):
        package = make_valid_v4()
        course = package["courses"][0]
        keep = {"lesson", "flashcard", "qcm", "constructed"}
        course["activities"] = [item for item in course["activities"] if item["type"] in keep]
        course["estimatedMinutes"] = sum(item["estimatedMinutes"] for item in course["activities"])
        package = refresh(package)
        report = quality.analyze_package(package)
        self.assertTrue(report["canonicalValid"], report)
        codes = {item["code"] for item in report["diagnostics"]}
        self.assertIn("PQ_V4_EXPOSURE_WITHOUT_PRACTICE", codes)

    def test_no_activity_family_quota(self):
        package = make_valid_v4()
        course = package["courses"][0]
        course["activities"] = [activity(package, "matching"), activity(package, "qcm")]
        course["estimatedMinutes"] = sum(item["estimatedMinutes"] for item in course["activities"])
        package["assets"] = []
        package = refresh(package)
        report = quality.analyze_package(package)
        self.assertTrue(report["canonicalValid"], report)
        self.assertEqual(0, report["counts"]["warning"], report["diagnostics"])

    def test_fake_classify_and_low_operation_constructed_are_advice(self):
        package = make_valid_v4()
        classify = activity(package, "classify")
        classify["items"] = classify["items"][:2]
        classify["assignments"] = [
            {"itemId": classify["items"][0]["itemId"], "bucketId": classify["buckets"][0]["bucketId"]},
            {"itemId": classify["items"][1]["itemId"], "bucketId": classify["buckets"][1]["bucketId"]},
        ]
        activity(package, "constructed")["prompt"] = "What is the conserved total?"
        package = refresh(package)
        report = quality.analyze_package(package)
        self.assertTrue(report["canonicalValid"], report)
        codes = {item["code"] for item in report["diagnostics"]}
        self.assertIn("PQ_V4_CLASSIFY_ONE_ITEM_PER_BUCKET", codes)
        self.assertIn("PQ_V4_CONSTRUCTED_LOW_OPERATION_SIGNAL", codes)
        self.assertEqual(0, report["counts"]["warning"])

    def test_v4_quality_report_is_byte_deterministic(self):
        package = make_valid_v4()
        self.assertEqual(
            quality.report_bytes(quality.analyze_package(package)),
            quality.report_bytes(quality.analyze_package(copy.deepcopy(package))),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
