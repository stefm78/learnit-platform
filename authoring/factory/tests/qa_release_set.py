#!/usr/bin/env python3
"""Independent contradictory QA for QA-WP-024, frozen product HEAD 41f2245e..."""
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
from authoring.factory import release_set

FROZEN_HEAD = "41f2245e56b42a2e541d185f39a3edb5d8b6f01b"
KIT = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"


def canonical_write(path: Path, value: object) -> None:
    path.write_bytes(factory.canonical_json_bytes(value))


def hold_review(context: dict) -> dict:
    source_id = context["sources"][0]["sourceId"]
    dimensions = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": source_id,
                "locator": "qa-fixture",
                "basis": f"Independent QA fixture for {name}.",
            }]
        dimensions[name] = {
            "status": "hold" if name == "answerCorrectness" else "pass",
            "summary": f"Independent QA {name}.",
            "evidence": evidence,
        }
    finding = {
        "id": "QA-WP-024-F01",
        "severity": "major",
        "dimension": "answerCorrectness",
        "path": "$.courses[0].activities[0]",
        "problem": "Deliberate HOLD input for forged-PASS attack.",
        "impact": "Must never be admitted to a qualified release set.",
        "fix": "Not applicable in QA fixture.",
        "evidence": [{
            "sourceId": source_id,
            "locator": "qa-fixture",
            "basis": "Deliberate contradictory QA HOLD fixture.",
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
        "findings": [finding],
        "limitations": [],
        "verdict": factory.SEMANTIC_HOLD,
    }


class ContradictoryReleaseSetQA(unittest.TestCase):
    def test_forged_pass_decision_must_be_rejected(self):
        """#328 attack case 3: logically forged PASS must not become releasable."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.txt"
            source.write_text("Independent QA source fixture.\n", encoding="utf-8")
            brief = root / "brief.json"
            canonical_write(brief, {
                "schema": factory.BRIEF_SCHEMA,
                "audience": "independent QA fixture",
                "goal": "Attack release-set admission",
                "language": "fr",
                "timeBudgetMinutes": 20,
            })
            kit = root / "kit.json"
            kit.write_bytes(KIT.read_bytes())
            context = factory.build_context(kit, brief, [f"course={source}"])
            review = root / "review.json"
            canonical_write(review, hold_review(context))

            genuine_hold = reliability.build_run(
                kit, brief, review, [f"course@qa-v1={source}"]
            )
            self.assertEqual("HOLD", reliability.decision_class(genuine_hold))

            forged = copy.deepcopy(genuine_hold)
            forged_gate = forged["evidenceBundle"]["factoryEvidence"]
            forged_gate["verdict"] = "PASS_FACTORY_GATE_V1"
            forged_gate["reasons"] = []
            forged_decision = {"verdict": "PASS_FACTORY_GATE_V1", "reasons": []}
            forged["decision"] = forged_decision
            forged["evidenceBundle"]["finalDecision"] = copy.deepcopy(forged_decision)

            forged["evidenceBundle"]["factoryEvidenceSha256"] = reliability.digest(forged_gate)
            bundle = forged["evidenceBundle"]
            bundle_core = {k: v for k, v in bundle.items() if k != "bundleSha256"}
            bundle["bundleSha256"] = reliability.digest(bundle_core)
            run_core = {k: v for k, v in forged.items() if k != "runId"}
            forged["runId"] = reliability.digest(run_core)

            # The upstream verifier accepts the internally rehashed forged PASS.
            verified = reliability.verify_run(copy.deepcopy(forged))
            self.assertEqual("PASS", reliability.decision_class(verified))
            self.assertEqual(
                factory.SEMANTIC_HOLD,
                verified["evidenceBundle"]["factoryEvidence"]["semanticReview"]["verdict"],
                "fixture must remain semantically HOLD while decision is forged PASS",
            )

            run_path = root / "forged-run.json"
            canonical_write(run_path, forged)
            out = root / "release.zip"

            # Required product property: forged PASS is rejected.
            # Frozen HEAD currently violates this expectation by building a release.
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.build_release_archive([f"{run_path}={kit}"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
