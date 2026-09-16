#!/usr/bin/env python3
"""Student V0.1 v4 compatibility evidence for the promoted AI Kit Factory gate."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.v4.tests.test_validate_v4 import make_valid_v4


def review_for(context: dict, *, hold_dimension: str | None = None) -> dict:
    source_id = context["sources"][0]["sourceId"]
    dimensions = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{"sourceId": source_id, "locator": "section-1", "basis": f"Source evidence checked for {name}."}]
        dimensions[name] = {
            "status": "hold" if name == hold_dimension else "pass",
            "summary": f"Independent {name} review completed.",
            "evidence": evidence,
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
        "independence": {"authorScratchpadSeen": False, "authorActiveContextReused": False},
        "dimensions": dimensions,
        "findings": [],
        "limitations": [],
        "verdict": factory.SEMANTIC_HOLD if hold_dimension else factory.SEMANTIC_PASS,
    }


class StudentV01V4FactoryTests(unittest.TestCase):
    def workspace(self, root: Path):
        kit = root / "candidate-v4.json"
        brief = root / "brief.json"
        source = root / "source.md"
        review = root / "review.json"
        kit.write_text(json.dumps(make_valid_v4(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        brief.write_text(json.dumps({
            "schema": factory.BRIEF_SCHEMA,
            "audience": "Student V0.1 learner",
            "goal": "Understand and apply the bounded source relation",
            "language": "en",
            "timeBudgetMinutes": 30,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        source.write_text("The source defines a conserved quantity in a bounded system and states the assumptions under which both totals are equal.\n", encoding="utf-8")
        return kit, brief, source, review

    def test_factory_accepts_qualified_v4_with_independent_semantic_pass(self):
        with tempfile.TemporaryDirectory() as td:
            kit, brief, source, review = self.workspace(Path(td))
            sources = [f"source={source}"]
            context = factory.build_context(kit, brief, sources)
            review.write_text(json.dumps(review_for(context), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            evidence = factory.run_gate(kit, brief, review, sources)
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", evidence["verdict"], evidence)
            self.assertTrue(evidence["canonicalValid"])
            self.assertIn(evidence["pedagogicalQuality"]["qualityBand"], {"STRONG", "EXCELLENT_BY_PROFILE"})

    def test_factory_v4_still_holds_on_semantic_review_failure(self):
        with tempfile.TemporaryDirectory() as td:
            kit, brief, source, review = self.workspace(Path(td))
            sources = [f"source={source}"]
            context = factory.build_context(kit, brief, sources)
            review.write_text(json.dumps(review_for(context, hold_dimension="sourceFidelity"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            evidence = factory.run_gate(kit, brief, review, sources)
            self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", evidence["verdict"], evidence)

    def test_factory_v4_review_binding_is_still_exact(self):
        with tempfile.TemporaryDirectory() as td:
            kit, brief, source, review = self.workspace(Path(td))
            sources = [f"source={source}"]
            context = factory.build_context(kit, brief, sources)
            review.write_text(json.dumps(review_for(context), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            source.write_text(source.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
            evidence = factory.run_gate(kit, brief, review, sources)
            self.assertEqual("HOLD_FACTORY_REVIEW_BINDING", evidence["verdict"], evidence)


if __name__ == "__main__":
    unittest.main(verbosity=2)
