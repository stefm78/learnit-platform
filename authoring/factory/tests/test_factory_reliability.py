#!/usr/bin/env python3
"""Product evidence for ATLAS-WP-015 M3.2.5 Factory Reliability."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import reliability

SIGNALS = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"
DOMAINS = [
    "mathematics", "physics", "computer-science", "history",
    "law", "medicine", "literature", "management",
]


def semantic_review(context: dict, *, hold: bool = False) -> dict:
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
            "status": "hold" if hold and name == "answerCorrectness" else "pass",
            "summary": f"Independent {name} review completed.",
            "evidence": evidence,
        }
    finding = {
        "id": "REL-HOLD-001",
        "severity": "major",
        "dimension": "answerCorrectness",
        "path": "$.courses[0].activities[0]",
        "problem": "Deliberate benchmark defect.",
        "impact": "The candidate must not pass.",
        "fix": "Repair from the source and review a new exact kit.",
        "evidence": [{
            "sourceId": source_id,
            "locator": "section-1",
            "basis": "The benchmark intentionally contradicts this source statement.",
        }],
    }
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
            "authorScratchpadSeen": False,
            "authorActiveContextReused": False,
        },
        "dimensions": dimensions,
        "findings": [finding] if hold else [],
        "limitations": [],
        "verdict": factory.SEMANTIC_HOLD if hold else factory.SEMANTIC_PASS,
    }


class Workspace:
    def __init__(self, root: Path, source_name: str = "course.txt"):
        self.root = root
        self.kit = root / "candidate.json"
        self.brief = root / "brief.json"
        self.source = root / source_name
        self.review = root / "review.json"
        self.kit.write_bytes(SIGNALS.read_bytes())
        self.brief.write_text(json.dumps({
            "schema": factory.BRIEF_SCHEMA,
            "audience": "élève ingénieur",
            "goal": "Comprendre et appliquer les relations du cours",
            "language": "fr",
            "timeBudgetMinutes": 45,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.source.write_text(
            "Tension, intensité, résistance et puissance sont les notions de cette source de test.\n",
            encoding="utf-8",
        )

    def source_spec(self, version: str = "2026-01") -> str:
        return f"course@{version}={self.source}"

    def write_review(self, hold: bool = False) -> None:
        context = factory.build_context(
            self.kit, self.brief, [f"course={self.source}"]
        )
        self.review.write_text(
            json.dumps(semantic_review(context, hold=hold), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def run(self, version: str = "2026-01") -> dict:
        return reliability.build_run(
            self.kit, self.brief, self.review, [self.source_spec(version)]
        )


class ResourceIdentityTests(unittest.TestCase):
    def test_resource_spec_requires_version_and_unique_id(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.txt"
            source.write_text("same bytes\n", encoding="utf-8")
            with self.assertRaises(reliability.ReliabilityInputError):
                reliability.parse_resources([f"course={source}"])
            with self.assertRaises(reliability.ReliabilityInputError):
                reliability.parse_resources([
                    f"course@v1={source}", f"course@v2={source}",
                ])
            identities, _ = reliability.parse_resources([f"course@v1={source}"])
            self.assertEqual("course", identities[0]["resourceId"])
            self.assertEqual("v1", identities[0]["version"])
            self.assertNotIn(str(source), factory.canonical_output({"resources": identities}))

    def test_relocation_preserves_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a_dir = root / "a"
            b_dir = root / "b"
            a_dir.mkdir(); b_dir.mkdir()
            a = Workspace(a_dir)
            a.write_review()
            run_a = a.run()

            b = Workspace(b_dir, "moved-source.txt")
            b.kit.write_bytes(a.kit.read_bytes())
            b.brief.write_bytes(a.brief.read_bytes())
            b.source.write_bytes(a.source.read_bytes())
            b.review.write_bytes(a.review.read_bytes())
            run_b = b.run()

            self.assertEqual(run_a, run_b)
            packed = factory.canonical_output(run_a)
            self.assertNotIn(str(a_dir), packed)
            self.assertNotIn(str(b_dir), packed)

    def test_version_changes_logical_run_identity_not_m3_2_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = Workspace(root)
            ws.write_review()
            one = ws.run("2026-01")
            two = ws.run("2026-02")
            self.assertNotEqual(one["resourceSetDigest"], two["resourceSetDigest"])
            self.assertEqual(one["resourceContentDigest"], two["resourceContentDigest"])
            self.assertNotEqual(one["runId"], two["runId"])
            self.assertEqual(one["factoryContextDigest"], two["factoryContextDigest"])
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", one["decision"]["verdict"])
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", two["decision"]["verdict"])


class FactoryRunTests(unittest.TestCase):
    def test_run_is_deterministic_and_self_verifying(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td)); ws.write_review()
            a = ws.run(); b = ws.run()
            self.assertEqual(a, b)
            self.assertEqual(a, reliability.verify_run(copy.deepcopy(a)))
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", a["decision"]["verdict"])

    def test_tampered_run_layers_fail_verification(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td)); ws.write_review()
            baseline = ws.run()
            mutants = []

            value = copy.deepcopy(baseline)
            value["decision"]["verdict"] = "PASS_FAKE"
            mutants.append(value)

            value = copy.deepcopy(baseline)
            value["evidenceBundle"]["resources"][0]["sha256"] = "sha256:" + "0" * 64
            mutants.append(value)

            value = copy.deepcopy(baseline)
            value["evidenceBundle"]["artifacts"]["generatedKit"]["sha256"] = "sha256:" + "1" * 64
            mutants.append(value)

            value = copy.deepcopy(baseline)
            value["evidenceBundle"]["validators"]["canonicalValid"] = not value["evidenceBundle"]["validators"]["canonicalValid"]
            mutants.append(value)

            value = copy.deepcopy(baseline)
            value["evidenceBundle"]["bundleSha256"] = "sha256:" + "2" * 64
            mutants.append(value)

            value = copy.deepcopy(baseline)
            value["runId"] = "sha256:" + "3" * 64
            mutants.append(value)

            for mutant in mutants:
                with self.subTest(mutant=mutant["runId"]):
                    with self.assertRaises(reliability.ReliabilityInputError):
                        reliability.verify_run(mutant)

    def test_source_byte_drift_remains_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td)); ws.write_review()
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", ws.run()["decision"]["verdict"])
            ws.source.write_text("changed bytes\n", encoding="utf-8")
            changed = ws.run()
            self.assertEqual("HOLD_FACTORY_REVIEW_BINDING", changed["decision"]["verdict"])
            self.assertTrue(changed["decision"]["reasons"])

    def test_semantic_hold_is_preserved_and_justified(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td)); ws.write_review(hold=True)
            run = ws.run()
            self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", run["decision"]["verdict"])
            self.assertTrue(run["decision"]["reasons"])
            reliability.verify_run(run)


class BenchmarkTests(unittest.TestCase):
    def _contract(self, root: Path) -> Path:
        path = root / "contract.json"
        path.write_text(json.dumps({
            "schema": reliability.BENCHMARK_CONTRACT_SCHEMA,
            "profile": reliability.BENCHMARK_PROFILE,
            "requiredDomains": DOMAINS,
            "minimumRuns": 8,
            "minimumPass": 2,
            "minimumHold": 2,
            "maximumHumanEscalationRate": 0.25,
        }), encoding="utf-8")
        return path

    def _manifest(self, root: Path, *, all_pass: bool = False, all_hold: bool = False, duplicate_run: bool = False) -> Path:
        cases = []
        first_path = None
        for index, domain in enumerate(DOMAINS):
            case_root = root / f"case-{index}"
            case_root.mkdir()
            ws = Workspace(case_root)
            ws.source.write_text(
                ws.source.read_text(encoding="utf-8") + f"Benchmark domain: {domain}.\n",
                encoding="utf-8",
            )
            hold = True if all_hold else (False if all_pass else index >= 4)
            ws.write_review(hold=hold)
            run = ws.run(version=f"v{index+1}")
            run_path = case_root / "run.json"
            run_path.write_text(factory.canonical_output(run), encoding="utf-8")
            if first_path is None:
                first_path = run_path
            if duplicate_run and index == 1:
                run_path = first_path
            cases.append({
                "caseId": f"case-{index+1}",
                "domain": domain,
                "run": str(run_path),
                "expectedDecision": "PASS" if not hold else "HOLD",
                "humanEscalation": index == 7,
            })
        path = root / "manifest.json"
        path.write_text(json.dumps({
            "schema": reliability.BENCHMARK_MANIFEST_SCHEMA,
            "cases": cases,
        }), encoding="utf-8")
        return path

    def test_benchmark_requires_real_pass_and_hold_diversity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = reliability.run_benchmark(
                self._contract(root), self._manifest(root)
            )
            self.assertEqual("PASS_FACTORY_BENCHMARK_V1", report["verdict"])
            self.assertEqual(4, report["metrics"]["pass"])
            self.assertEqual(4, report["metrics"]["hold"])
            self.assertEqual(sorted(DOMAINS), report["metrics"]["domainsCovered"])

    def test_all_pass_corpus_is_benchmark_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = reliability.run_benchmark(
                self._contract(root), self._manifest(root, all_pass=True)
            )
            self.assertEqual("HOLD_FACTORY_BENCHMARK_V1", report["verdict"])
            self.assertTrue(any(x.startswith("BENCHMARK_TOO_FEW_HOLD") for x in report["reasons"]))

    def test_all_hold_corpus_is_benchmark_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = reliability.run_benchmark(
                self._contract(root), self._manifest(root, all_hold=True)
            )
            self.assertEqual("HOLD_FACTORY_BENCHMARK_V1", report["verdict"])
            self.assertTrue(any(x.startswith("BENCHMARK_TOO_FEW_PASS") for x in report["reasons"]))

    def test_missing_domain_and_run_count_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract = self._contract(root)
            manifest_path = self._manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            removed = manifest["cases"].pop()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = reliability.run_benchmark(contract, manifest_path)
            self.assertEqual("HOLD_FACTORY_BENCHMARK_V1", report["verdict"])
            self.assertIn("BENCHMARK_DOMAIN_MISSING:" + removed["domain"], report["reasons"])
            self.assertTrue(any(x.startswith("BENCHMARK_TOO_FEW_RUNS") for x in report["reasons"]))

    def test_expectation_mismatch_holds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract = self._contract(root)
            manifest_path = self._manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["cases"][0]["expectedDecision"] = "HOLD"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = reliability.run_benchmark(contract, manifest_path)
            self.assertEqual("HOLD_FACTORY_BENCHMARK_V1", report["verdict"])
            self.assertTrue(any(x.startswith("BENCHMARK_EXPECTATION_MISMATCH:case-1") for x in report["reasons"]))

    def test_excessive_human_escalation_holds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract = self._contract(root)
            manifest_path = self._manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for case in manifest["cases"][:3]:
                case["humanEscalation"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = reliability.run_benchmark(contract, manifest_path)
            self.assertEqual("HOLD_FACTORY_BENCHMARK_V1", report["verdict"])
            self.assertTrue(any(x.startswith("BENCHMARK_HUMAN_ESCALATION_RATE") for x in report["reasons"]))

    def test_same_source_content_cannot_be_relabelled_across_domains(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract = self._contract(root)
            manifest_path = self._manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            first_path = Path(manifest["cases"][0]["run"])
            second_path = Path(manifest["cases"][1]["run"])
            second_run = copy.deepcopy(
                json.loads(first_path.read_text(encoding="utf-8"))
            )
            second_run["evidenceBundle"]["resources"][0]["version"] = "relabelled-version"
            second_run["resourceSetDigest"] = reliability.digest(
                second_run["evidenceBundle"]["resources"]
            )
            second_run["evidenceBundle"]["resourceSetDigest"] = second_run["resourceSetDigest"]
            bundle = second_run["evidenceBundle"]
            bundle_core = {k: v for k, v in bundle.items() if k != "bundleSha256"}
            bundle["bundleSha256"] = reliability.digest(bundle_core)
            run_core = {k: v for k, v in second_run.items() if k != "runId"}
            second_run["runId"] = reliability.digest(run_core)
            second_path.write_text(
                factory.canonical_output(second_run), encoding="utf-8"
            )

            with self.assertRaisesRegex(
                reliability.ReliabilityInputError,
                "duplicate benchmark source content",
            ):
                reliability.run_benchmark(contract, manifest_path)

    def test_duplicate_run_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(reliability.ReliabilityInputError):
                reliability.run_benchmark(
                    self._contract(root), self._manifest(root, duplicate_run=True)
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
