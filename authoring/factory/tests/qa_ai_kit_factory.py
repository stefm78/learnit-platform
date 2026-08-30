#!/usr/bin/env python3
"""Independent contradictory QA for ATLAS-WP-014 M3.2 AI Kit Factory."""
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
from authoring.v2.atlas import validate_atlas_content as atlas

COMPLEX = ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json"
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


def rows_for_objective(package: dict, objective_index: int) -> list[tuple[int, dict]]:
    course = package["courses"][0]
    oid = course["objectives"][objective_index]["objectiveId"]
    rows = [
        (index, activity)
        for index, activity in enumerate(course["activities"])
        if activity["objectiveIds"] == [oid]
    ]
    if len(rows) != 5:
        raise AssertionError(rows)
    return rows


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.kit = root / "complex.json"
        self.brief = root / "brief.json"
        self.source_a = root / "cours-complexes.txt"
        self.source_b = root / "formules.txt"
        self.review = root / "review.json"

        self.kit.write_bytes(COMPLEX.read_bytes())
        self.brief.write_text(
            json.dumps(
                {
                    "schema": factory.BRIEF_SCHEMA,
                    "audience": "étudiant ingénieur en deuxième année",
                    "goal": "Savoir manipuler les nombres complexes du cours",
                    "language": "fr",
                    "timeBudgetMinutes": 50,
                    "preference": "exercices actifs",
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        self.source_a.write_text(
            "Nombres complexes : formes algébrique, polaire et exponentielle. "
            "Le module et l'argument permettent de changer de représentation.\n",
            encoding="utf-8",
        )
        self.source_b.write_text(
            "Règles de calcul et représentations utilisées par les exercices de cette qualification QA.\n",
            encoding="utf-8",
        )

    @property
    def sources(self) -> list[str]:
        return [f"course={self.source_a}", f"formulae={self.source_b}"]

    def context(self) -> dict:
        return factory.build_context(self.kit, self.brief, self.sources)

    def review_for(
        self,
        *,
        statuses: dict[str, str] | None = None,
        findings: list[dict] | None = None,
        scratchpad: bool = False,
        reused: bool = False,
        verdict: str | None = None,
    ) -> dict:
        context = self.context()
        statuses = statuses or {}
        findings = copy.deepcopy(findings or [])
        dimensions = {}
        for index, name in enumerate(factory.REQUIRED_DIMENSIONS):
            evidence = []
            if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
                source_id = "course" if index % 2 == 0 else "formulae"
                evidence = [{
                    "sourceId": source_id,
                    "locator": f"qa-locator-{index + 1}",
                    "basis": f"Independent QA evidence for {name}.",
                }]
            dimensions[name] = {
                "status": statuses.get(name, "pass"),
                "summary": f"Independent QA checked {name}.",
                "evidence": evidence,
            }

        should_pass = (
            not scratchpad
            and not reused
            and all(value["status"] == "pass" for value in dimensions.values())
            and not any(item["severity"] in ("blocking", "major") for item in findings)
        )
        if verdict is None:
            verdict = factory.SEMANTIC_PASS if should_pass else factory.SEMANTIC_HOLD

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
                "authorScratchpadSeen": scratchpad,
                "authorActiveContextReused": reused,
            },
            "dimensions": dimensions,
            "findings": findings,
            "limitations": ["QA synthetic sources are intentionally minimal."],
            "verdict": verdict,
        }

    def save_review(self, review: dict) -> None:
        self.review.write_text(
            json.dumps(review, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def run(self) -> dict:
        return factory.run_gate(self.kit, self.brief, self.review, self.sources)


class IndependentBindingOracle(unittest.TestCase):
    def test_context_is_source_order_independent_but_content_sensitive(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            first = f.context()
            reordered = factory.build_context(
                f.kit,
                f.brief,
                [f"formulae={f.source_b}", f"course={f.source_a}"],
            )
            self.assertEqual(first, reordered)
            self.assertEqual(
                ["course", "formulae"],
                [item["sourceId"] for item in first["sources"]],
            )
            self.assertNotIn(str(Path(td)), factory.canonical_output(first))

            f.source_b.write_bytes(f.source_b.read_bytes() + b"!")
            changed = f.context()
            self.assertNotEqual(first["sourceSetDigest"], changed["sourceSetDigest"])
            self.assertNotEqual(first["contextDigest"], changed["contextDigest"])

    def test_stale_review_rejected_after_each_semantic_input_drift(self):
        mutations = ("kit", "source", "brief")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                f.save_review(f.review_for())

                if mutation == "kit":
                    f.kit.write_bytes(f.kit.read_bytes() + b"\n")
                    expected = "kitSha256"
                elif mutation == "source":
                    f.source_a.write_bytes(f.source_a.read_bytes() + b"x")
                    expected = "sourceSetDigest"
                else:
                    brief = load(f.brief)
                    brief["timeBudgetMinutes"] = 35
                    f.brief.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
                    expected = "briefSha256"

                evidence = f.run()
                self.assertEqual("HOLD_FACTORY_REVIEW_BINDING", evidence["verdict"])
                self.assertTrue(any(expected in reason for reason in evidence["reasons"]))

    def test_bad_source_specs_and_brief_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            with self.assertRaises(factory.FactoryInputError):
                factory.build_context(f.kit, f.brief, [str(f.source_a)])
            with self.assertRaises(factory.FactoryInputError):
                factory.build_context(
                    f.kit,
                    f.brief,
                    [f"dup={f.source_a}", f"dup={f.source_b}"],
                )
            bad = load(f.brief)
            bad["timeBudgetMinutes"] = 0
            f.brief.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(factory.FactoryInputError):
                f.context()


class IndependentReviewContractOracle(unittest.TestCase):
    def test_missing_or_extra_dimension_fails_closed(self):
        for mode in ("missing", "extra"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                review = f.review_for()
                if mode == "missing":
                    del review["dimensions"]["ambiguity"]
                else:
                    review["dimensions"]["inventedDimension"] = {
                        "status": "pass",
                        "summary": "extra",
                        "evidence": [],
                    }
                f.save_review(review)
                with self.assertRaises(factory.FactoryInputError):
                    f.run()

    def test_required_dimension_without_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            review = f.review_for()
            review["dimensions"]["answerCorrectness"]["evidence"] = []
            f.save_review(review)
            with self.assertRaises(factory.FactoryInputError):
                f.run()

    def test_unknown_source_reference_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            review = f.review_for()
            review["dimensions"]["validationTransfer"]["evidence"][0]["sourceId"] = "ghost"
            f.save_review(review)
            with self.assertRaises(factory.FactoryInputError):
                f.run()

    def test_both_independence_violations_hold(self):
        for kwargs, reason in [
            ({"scratchpad": True}, "REVIEWER_SAW_AUTHOR_SCRATCHPAD"),
            ({"reused": True}, "REVIEWER_REUSED_AUTHOR_ACTIVE_CONTEXT"),
        ]:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                f.save_review(f.review_for(**kwargs))
                evidence = f.run()
                self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", evidence["verdict"])
                self.assertIn(reason, evidence["reasons"])

    def test_dimension_hold_cannot_hide_behind_pass_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            f.save_review(
                f.review_for(
                    statuses={"learnerFit": "hold"},
                    verdict=factory.SEMANTIC_PASS,
                )
            )
            evidence = f.run()
            self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", evidence["verdict"])
            self.assertIn("DIMENSION_HOLD:learnerFit", evidence["reasons"])
            self.assertTrue(
                any(reason.startswith("INCONSISTENT_REVIEW_VERDICT") for reason in evidence["reasons"])
            )

    def test_major_finding_cannot_hide_behind_pass_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            finding = {
                "id": "QA-MAJOR-1",
                "severity": "major",
                "dimension": "sourceFidelity",
                "path": "$.courses[0].activities[1]",
                "problem": "Synthetic QA major source-fidelity defect.",
                "impact": "A learner could encode unsupported content.",
                "fix": "Replace with source-supported content.",
                "evidence": [{
                    "sourceId": "course",
                    "locator": "qa-locator-major",
                    "basis": "QA contradictory evidence.",
                }],
            }
            f.save_review(f.review_for(findings=[finding], verdict=factory.SEMANTIC_PASS))
            evidence = f.run()
            self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", evidence["verdict"])
            self.assertIn("MAJOR_FINDING:QA-MAJOR-1", evidence["reasons"])

    def test_duplicate_finding_ids_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            base = {
                "id": "DUP",
                "severity": "minor",
                "dimension": "ambiguity",
                "path": "$",
                "problem": "p",
                "impact": "i",
                "fix": "f",
                "evidence": [],
            }
            f.save_review(f.review_for(findings=[base, copy.deepcopy(base)]))
            with self.assertRaises(factory.FactoryInputError):
                f.run()


class IndependentReleaseOracle(unittest.TestCase):
    def test_canonical_invalid_never_passes(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            kit = load(f.kit)
            kit["contract"] = "learnit.kit.invalid"
            f.kit.write_text(json.dumps(kit, ensure_ascii=False), encoding="utf-8")
            f.save_review(f.review_for())
            evidence = f.run()
            self.assertEqual("HOLD_FACTORY_CANONICAL_INVALID", evidence["verdict"])
            self.assertFalse(evidence["canonicalValid"])

    def test_complete_structural_band_never_passes(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            kit = load(f.kit)
            rows = rows_for_objective(kit, 1)
            rows[4][1]["difficulty"] = rows[0][1]["difficulty"]
            f.kit.write_text(
                json.dumps(refresh(kit), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            f.save_review(f.review_for())
            evidence = f.run()
            self.assertEqual("COMPLETE", evidence["pedagogicalQuality"]["qualityBand"])
            self.assertEqual("HOLD_FACTORY_PEDAGOGICAL_WARNING", evidence["verdict"])

    def test_strong_with_minor_and_advice_findings_can_pass(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            findings = [
                {
                    "id": "QA-MINOR-1",
                    "severity": "minor",
                    "dimension": "ambiguity",
                    "path": "$.courses[0].activities[0].prompt",
                    "problem": "Could be terser.",
                    "impact": "Small reading overhead.",
                    "fix": "Shorten without semantic change.",
                    "evidence": [],
                },
                {
                    "id": "QA-ADVICE-1",
                    "severity": "advice",
                    "dimension": "learnerFit",
                    "path": "$",
                    "problem": "Optional phrasing improvement.",
                    "impact": "No release impact.",
                    "fix": "Consider shorter introduction.",
                    "evidence": [],
                },
            ]
            f.save_review(f.review_for(findings=findings))
            evidence = f.run()
            self.assertIn(
                evidence["pedagogicalQuality"]["qualityBand"],
                {"STRONG", "EXCELLENT_BY_PROFILE"},
            )
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", evidence["verdict"])
            self.assertEqual(1, evidence["semanticReview"]["counts"]["minor"])
            self.assertEqual(1, evidence["semanticReview"]["counts"]["advice"])

    def test_factory_evidence_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            f.save_review(f.review_for())
            a = f.run()
            b = f.run()
            self.assertEqual(a, b)
            self.assertEqual(factory.canonical_output(a), factory.canonical_output(b))


class BoundaryOracle(unittest.TestCase):
    def test_factory_gate_is_read_only_network_free_and_non_extracting(self):
        source = (ROOT / "authoring/factory/factory_gate.py").read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "httpx",
            "aiohttp",
            "urllib.request",
            "socket.",
            ".write_text(",
            ".write_bytes(",
            "pypdf",
            "pdfplumber",
            "pymupdf",
            "tesseract",
        ):
            self.assertNotIn(forbidden, source.lower() if forbidden.islower() else source)

    def test_cli_does_not_mutate_any_input(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            f.save_review(f.review_for())
            paths = (f.kit, f.brief, f.source_a, f.source_b, f.review)
            before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
            command = [
                sys.executable,
                "-B",
                str(ROOT / "authoring/factory/factory_gate.py"),
                "gate",
                "--kit", str(f.kit),
                "--brief", str(f.brief),
                "--review", str(f.review),
                "--source", f"course={f.source_a}",
                "--source", f"formulae={f.source_b}",
                "--json",
            ]
            completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(0, completed.returncode, completed.stderr)
            after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
            self.assertEqual(before, after)

    def test_skills_preserve_role_separation(self):
        author = (ROOT / "authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V2.md").read_text(encoding="utf-8")
        reviewer = (ROOT / "authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md").read_text(encoding="utf-8")
        self.assertIn("Do not review your own final kit inside this active author context", author)
        self.assertIn("new independent reviewer context", author)
        self.assertIn("authorScratchpadSeen", reviewer)
        self.assertIn("authorActiveContextReused", reviewer)
        self.assertIn("You do not author or repair the kit", reviewer)
        self.assertNotIn("model provider", (ROOT / "authoring/factory/factory_gate.py").read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
