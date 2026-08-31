#!/usr/bin/env python3
"""Product evidence for ATLAS-WP-014 M3.2 AI Kit Factory."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.v2 import validate_kit as v2
from authoring.v2.atlas import pedagogical_quality as quality
from authoring.v2.atlas import validate_atlas_content as atlas

SIGNALS = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"
ZERO = "sha256:" + "0" * 64


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def refresh(package: dict) -> dict:
    value = copy.deepcopy(package)
    value["packageRevisionDigest"] = ZERO
    for course in value["courses"]:
        course["courseRevisionDigest"] = ZERO
        for activity in course["activities"]:
            activity["activityRevisionDigest"] = ZERO
    atlas.rewrite_claims(value)
    errors = v2.fill_new_digests(value)
    if errors:
        raise AssertionError(errors)
    atlas.validate_package(value)
    return value


def first_objective_rows(package: dict) -> list[tuple[int, dict]]:
    course = package["courses"][0]
    objective_id = course["objectives"][0]["objectiveId"]
    rows = [
        (index, activity)
        for index, activity in enumerate(course["activities"])
        if activity["objectiveIds"] == [objective_id]
    ]
    if len(rows) != 5:
        raise AssertionError(rows)
    return rows


def semantic_review(
    context: dict,
    *,
    findings: list[dict] | None = None,
    dimension_status: dict[str, str] | None = None,
    scratchpad_seen: bool = False,
    active_context_reused: bool = False,
    verdict: str | None = None,
) -> dict:
    findings = copy.deepcopy(findings or [])
    dimension_status = dimension_status or {}
    source_id = context["sources"][0]["sourceId"]
    dimensions = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": source_id,
                "locator": "section-1",
                "basis": f"Independent evidence for {name}.",
            }]
        dimensions[name] = {
            "status": dimension_status.get(name, "pass"),
            "summary": f"Independent {name} review completed.",
            "evidence": evidence,
        }

    would_pass = (
        not scratchpad_seen
        and not active_context_reused
        and all(item["status"] == "pass" for item in dimensions.values())
        and not any(item["severity"] in ("blocking", "major") for item in findings)
    )
    if verdict is None:
        verdict = factory.SEMANTIC_PASS if would_pass else factory.SEMANTIC_HOLD

    return {
        "schema": factory.REVIEW_SCHEMA,
        "profile": factory.REVIEW_PROFILE,
        "target": {
            "contextDigest": context["contextDigest"],
            "kitSha256": context["kitSha256"],
            "sourceSetDigest": context["sourceSetDigest"],
            "briefSha256": context["briefSha256"],
        },
        "independence": {
            "authorScratchpadSeen": scratchpad_seen,
            "authorActiveContextReused": active_context_reused,
        },
        "dimensions": dimensions,
        "findings": findings,
        "limitations": [],
        "verdict": verdict,
    }


class Workspace:
    def __init__(self, root: Path):
        self.root = root
        self.kit = root / "candidate.json"
        self.brief = root / "brief.json"
        self.source = root / "course.txt"
        self.review = root / "review.json"

        self.kit.write_bytes(SIGNALS.read_bytes())
        self.brief.write_text(
            json.dumps({
                "schema": factory.BRIEF_SCHEMA,
                "audience": "élève ingénieur",
                "goal": "Comprendre et appliquer les relations du cours",
                "language": "fr",
                "timeBudgetMinutes": 45,
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.source.write_text(
            "Tension, intensité, résistance et puissance sont les notions de cette source de test.\n",
            encoding="utf-8",
        )

    @property
    def sources(self) -> list[str]:
        return [f"course={self.source}"]

    def context(self) -> dict:
        return factory.build_context(self.kit, self.brief, self.sources)

    def write_review(self, review: dict) -> None:
        self.review.write_text(
            json.dumps(review, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def valid_review(self, **kwargs) -> dict:
        review = semantic_review(self.context(), **kwargs)
        self.write_review(review)
        return review

    def gate(self) -> dict:
        return factory.run_gate(self.kit, self.brief, self.review, self.sources)


class ContextContractTests(unittest.TestCase):
    def test_context_is_deterministic_ordered_and_hides_host_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = Workspace(root)
            extra = root / "extra.md"
            extra.write_text("additional source\n", encoding="utf-8")
            a = factory.build_context(
                ws.kit, ws.brief,
                [f"zeta={extra}", f"course={ws.source}"],
            )
            b = factory.build_context(
                ws.kit, ws.brief,
                [f"course={ws.source}", f"zeta={extra}"],
            )
            self.assertEqual(a, b)
            self.assertEqual(["course", "zeta"], [item["sourceId"] for item in a["sources"]])
            packed = factory.canonical_output(a)
            self.assertNotIn(str(root), packed)
            self.assertEqual(packed, factory.canonical_output(b))

    def test_one_source_byte_changes_context(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            before = ws.context()
            ws.source.write_text(ws.source.read_text(encoding="utf-8") + "x", encoding="utf-8")
            after = ws.context()
            self.assertNotEqual(before["sourceSetDigest"], after["sourceSetDigest"])
            self.assertNotEqual(before["contextDigest"], after["contextDigest"])

    def test_semantically_changed_brief_changes_context(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            before = ws.context()
            brief = json.loads(ws.brief.read_text(encoding="utf-8"))
            brief["timeBudgetMinutes"] = 30
            ws.brief.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            after = ws.context()
            self.assertNotEqual(before["briefSha256"], after["briefSha256"])
            self.assertNotEqual(before["contextDigest"], after["contextDigest"])


class FactoryGateTests(unittest.TestCase):
    def test_baseline_strong_candidate_can_pass_independent_review(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            band = quality.analyze_package(load(ws.kit))["qualityBand"]
            self.assertIn(band, {"STRONG", "EXCELLENT_BY_PROFILE"})
            ws.valid_review()
            evidence = ws.gate()
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", evidence["verdict"])
            self.assertTrue(evidence["canonicalValid"])
            self.assertEqual(factory.SEMANTIC_PASS, evidence["semanticReview"]["verdict"])

    def test_stale_review_after_kit_byte_change_holds_binding(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.valid_review()
            ws.kit.write_bytes(ws.kit.read_bytes() + b"\n")
            evidence = ws.gate()
            self.assertEqual("HOLD_FACTORY_REVIEW_BINDING", evidence["verdict"])
            self.assertIn("REVIEW_TARGET_MISMATCH:kitSha256", evidence["reasons"])

    def test_stale_review_after_source_change_holds_binding(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.valid_review()
            ws.source.write_text("changed source bytes\n", encoding="utf-8")
            evidence = ws.gate()
            self.assertEqual("HOLD_FACTORY_REVIEW_BINDING", evidence["verdict"])
            self.assertTrue(any("sourceSetDigest" in item for item in evidence["reasons"]))

    def test_stale_review_after_brief_change_holds_binding(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.valid_review()
            brief = json.loads(ws.brief.read_text(encoding="utf-8"))
            brief["goal"] = "Autre objectif"
            ws.brief.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            evidence = ws.gate()
            self.assertEqual("HOLD_FACTORY_REVIEW_BINDING", evidence["verdict"])
            self.assertIn("REVIEW_TARGET_MISMATCH:briefSha256", evidence["reasons"])

    def test_canonical_invalid_overrides_positive_semantic_review(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            kit = load(ws.kit)
            kit["contract"] = "learnit.kit.invalid"
            ws.kit.write_text(json.dumps(kit, ensure_ascii=False), encoding="utf-8")
            ws.valid_review()
            evidence = ws.gate()
            self.assertEqual("HOLD_FACTORY_CANONICAL_INVALID", evidence["verdict"])
            self.assertFalse(evidence["canonicalValid"])

    def test_m3_1_complete_is_factory_hold(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            kit = load(ws.kit)
            rows = first_objective_rows(kit)
            rows[4][1]["difficulty"] = rows[0][1]["difficulty"]
            kit = refresh(kit)
            ws.kit.write_text(json.dumps(kit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            ws.valid_review()
            evidence = ws.gate()
            self.assertEqual("COMPLETE", evidence["pedagogicalQuality"]["qualityBand"])
            self.assertEqual("HOLD_FACTORY_PEDAGOGICAL_WARNING", evidence["verdict"])

    def test_missing_dimension_is_input_hold(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            review = semantic_review(ws.context())
            del review["dimensions"]["learnerFit"]
            ws.write_review(review)
            with self.assertRaises(factory.FactoryInputError):
                ws.gate()

    def test_unknown_source_evidence_is_input_hold(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            review = semantic_review(ws.context())
            review["dimensions"]["sourceFidelity"]["evidence"][0]["sourceId"] = "unknown"
            ws.write_review(review)
            with self.assertRaises(factory.FactoryInputError):
                ws.gate()

    def test_independence_violation_is_semantic_hold(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.valid_review(scratchpad_seen=True)
            evidence = ws.gate()
            self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", evidence["verdict"])
            self.assertIn("REVIEWER_SAW_AUTHOR_SCRATCHPAD", evidence["reasons"])

    def test_major_finding_is_semantic_hold(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            finding = {
                "id": "R-001",
                "severity": "major",
                "dimension": "answerCorrectness",
                "path": "$.courses[0].activities[0]",
                "problem": "The claimed answer is not supported.",
                "impact": "A learner could encode a false rule.",
                "fix": "Recalculate and replace the activity using the source.",
                "evidence": [{
                    "sourceId": "course",
                    "locator": "section-1",
                    "basis": "The source relation contradicts the claimed result.",
                }],
            }
            ws.valid_review(findings=[finding])
            evidence = ws.gate()
            self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", evidence["verdict"])
            self.assertIn("MAJOR_FINDING:R-001", evidence["reasons"])

    def test_minor_finding_does_not_block_factory(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            finding = {
                "id": "R-002",
                "severity": "minor",
                "dimension": "ambiguity",
                "path": "$.courses[0].activities[0].prompt",
                "problem": "Wording could be slightly shorter.",
                "impact": "Small reading overhead.",
                "fix": "Shorten without changing meaning.",
                "evidence": [],
            }
            ws.valid_review(findings=[finding])
            evidence = ws.gate()
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", evidence["verdict"])
            self.assertEqual(1, evidence["semanticReview"]["counts"]["minor"])

    def test_inconsistent_pass_review_with_major_finding_holds(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            finding = {
                "id": "R-003",
                "severity": "major",
                "dimension": "sourceFidelity",
                "path": "$",
                "problem": "Unsupported claim.",
                "impact": "Source fidelity failure.",
                "fix": "Remove unsupported claim.",
                "evidence": [{
                    "sourceId": "course",
                    "locator": "section-1",
                    "basis": "No support for the candidate claim.",
                }],
            }
            ws.valid_review(findings=[finding], verdict=factory.SEMANTIC_PASS)
            evidence = ws.gate()
            self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", evidence["verdict"])
            self.assertTrue(any(item.startswith("INCONSISTENT_REVIEW_VERDICT") for item in evidence["reasons"]))

    def test_final_evidence_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.valid_review()
            a = ws.gate()
            b = ws.gate()
            self.assertEqual(a, b)
            self.assertEqual(factory.canonical_output(a), factory.canonical_output(b))


class CliBoundaryTests(unittest.TestCase):
    def test_cli_exit_classes_and_input_immutability(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.valid_review()
            paths = [ws.kit, ws.brief, ws.source, ws.review]
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            cmd = [
                sys.executable, "-B", str(ROOT / "authoring/factory/factory_gate.py"),
                "gate",
                "--kit", str(ws.kit),
                "--brief", str(ws.brief),
                "--review", str(ws.review),
                "--source", f"course={ws.source}",
                "--json",
            ]
            completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", json.loads(completed.stdout)["verdict"])
            after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            self.assertEqual(before, after)

    def test_context_cli_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            completed = subprocess.run(
                [
                    sys.executable, "-B", str(ROOT / "authoring/factory/factory_gate.py"),
                    "context",
                    "--kit", str(ws.kit),
                    "--brief", str(ws.brief),
                    "--source", f"course={ws.source}",
                ],
                cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            context = json.loads(completed.stdout)
            self.assertEqual(factory.CONTEXT_SCHEMA, context["schema"])

    def test_factory_gate_contains_no_network_or_write_primitive(self):
        source = (ROOT / "authoring/factory/factory_gate.py").read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "httpx",
            "aiohttp",
            "urllib.request",
            "socket.",
            "WebSocket",
            "XMLHttpRequest",
            ".write_text(",
            ".write_bytes(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
