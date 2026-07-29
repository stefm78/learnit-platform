#!/usr/bin/env python3
"""Deterministic lane tests for Atlas M1 canonical content."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = ROOT / "authoring/v2/atlas/validate_atlas_content.py"
KITS = (
    ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json",
    ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json",
)
spec = importlib.util.spec_from_file_location("atlas_content_validator", VALIDATOR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = VALIDATOR
spec.loader.exec_module(VALIDATOR)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(path: Path, document: dict[str, Any]):
    return VALIDATOR.validate_document(path, document)


def redigest(document: dict[str, Any]) -> dict[str, Any]:
    refreshed = VALIDATOR.refresh_digests(document)
    document.clear()
    document.update(refreshed)
    return document


class AtlasContentTests(unittest.TestCase):
    maxDiff = None

    def test_canonical_kits_pass(self) -> None:
        reports = VALIDATOR.validate_paths(KITS)
        self.assertEqual(2, len(reports))
        for report in reports:
            with self.subTest(path=report.path.name):
                self.assertTrue(report.ok, "\n".join(report.errors))
                self.assertFalse(report.warnings)

    def test_profiles_cover_5_15_30_and_complete_loops(self) -> None:
        for path in KITS:
            report = validate(path, load(path))
            with self.subTest(path=path.name):
                self.assertEqual([5, 15, 30], [course["estimatedMinutes"] for course in report.courses])
                for course in report.courses:
                    self.assertEqual(5, course["activities"])
                    self.assertEqual(1, len(course["objectives"]))
                    objective = course["objectives"][0]
                    for key in ("training", "errorOpportunity", "correction", "validation", "transfer"):
                        self.assertTrue(objective[key], key)
                    self.assertLess(min(objective["correction"]), min(objective["validation"]))
                    self.assertLess(min(objective["validation"]), min(objective["transfer"]))

    def test_practice_and_validation_are_distinct(self) -> None:
        for path in KITS:
            for course in load(path)["courses"]:
                practice = {a["activityLineageId"] for a in course["activities"] if a["assessmentRole"] == "practice"}
                validation = {a["activityLineageId"] for a in course["activities"] if a["assessmentRole"] == "validation"}
                self.assertTrue(practice.isdisjoint(validation))

    def test_rejects_missing_correction(self) -> None:
        path = KITS[0]
        document = copy.deepcopy(load(path))
        document["courses"][0]["activities"][2]["learningPhase"] = "comprehension"
        result = validate(path, redigest(document))
        self.assertFalse(result.ok)
        self.assertTrue(any("training <= error < correction < validation < transfer" in item for item in result.errors), result.errors)

    def test_rejects_validation_before_correction(self) -> None:
        path = KITS[0]
        document = copy.deepcopy(load(path))
        activities = document["courses"][1]["activities"]
        activities[2], activities[3] = activities[3], activities[2]
        result = validate(path, redigest(document))
        self.assertFalse(result.ok)
        self.assertTrue(any("training <= error < correction < validation < transfer" in item for item in result.errors), result.errors)

    def test_rejects_ambiguous_qcm_labels(self) -> None:
        path = KITS[1]
        document = copy.deepcopy(load(path))
        qcm = document["courses"][0]["activities"][0]
        qcm["choices"][1]["label"] = "  " + qcm["choices"][0]["label"].swapcase() + "  "
        result = validate(path, redigest(document))
        self.assertFalse(result.ok)
        self.assertTrue(any("ambiguous duplicate label" in item for item in result.errors), result.errors)

    def test_rejects_lineage_drift_even_with_valid_digest(self) -> None:
        path = KITS[0]
        document = copy.deepcopy(load(path))
        document["courses"][2]["activities"][0]["activityLineageId"] = "11111111-1111-4111-8111-111111111111"
        result = validate(path, redigest(document))
        self.assertFalse(result.ok)
        self.assertTrue(any("canonical activity lineage identity or order drift" in item for item in result.errors), result.errors)

    def test_rejects_remote_url_placeholder_and_stale_digest(self) -> None:
        path = KITS[0]
        document = copy.deepcopy(load(path))
        document["courses"][0]["activities"][0]["prompt"] = "TODO https://example.invalid"
        result = validate(path, document)
        self.assertFalse(result.ok)
        self.assertTrue(any("unresolved placeholder" in item for item in result.errors), result.errors)
        self.assertTrue(any("remote URL" in item for item in result.errors), result.errors)
        self.assertTrue(any("declared digest differs" in item for item in result.errors), result.errors)

    def test_cli_json_is_deterministic(self) -> None:
        command = [sys.executable, str(VALIDATOR_PATH), "--format", "json", *(str(path) for path in KITS)]
        first = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        second = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        self.assertEqual(0, first.returncode, first.stdout)
        self.assertEqual(first.stdout, second.stdout)
        payload = json.loads(first.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(all(len(item["profiles"]) == 3 for item in payload["files"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
