#!/usr/bin/env python3
"""Product oracle for ATLAS-WP-016 source admission."""
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
from authoring.factory import source_admission as admission

CATALOG = ROOT / "authoring/factory/benchmark_sources_v1.json"


class SourceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.catalog, self.catalog_sha = admission.load_catalog(CATALOG)

    def source(self, source_id):
        return admission.source_by_id(self.catalog, source_id)

    def accepted(self, source_id):
        return list(self.source(source_id)["rights"]["conditions"])

    def write_bytes(self, root: Path, name="source.bin", data=b"official source bytes\n"):
        path = root / name
        path.write_bytes(data)
        return path

    def test_catalog_has_eight_primary_domains_and_two_negative_controls(self):
        primary = {
            item["domain"]
            for item in self.catalog["sources"]
            if item["benchmarkRole"] == "primary"
        }
        negative = [
            item
            for item in self.catalog["sources"]
            if item["benchmarkRole"] == "negative-control"
        ]
        self.assertEqual(admission.REQUIRED_DOMAINS, primary)
        self.assertGreaterEqual(len(negative), 2)
        self.assertEqual(
            {"openstax:calculus-volume-1", "nice:guidelines-ai-negative-control"},
            {item["sourceId"] for item in negative},
        )

    def test_allowed_source_passes_only_after_conditions_and_bytes(self):
        source_id = "eduscol:math-specialite-examples-2024"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self.write_bytes(root)
            missing = admission.build_admission(
                self.catalog,
                self.catalog_sha,
                source_id,
                "internal-rd-noncommercial",
                path,
                [],
                None,
            )
            self.assertEqual(admission.HOLD_CONDITIONS, missing["decision"]["verdict"])
            self.assertIsNone(missing["content"])
            self.assertTrue(missing["preIngestionHold"])

            passed = admission.build_admission(
                self.catalog,
                self.catalog_sha,
                source_id,
                "internal-rd-noncommercial",
                path,
                self.accepted(source_id),
                None,
            )
            self.assertEqual(admission.PASS, passed["decision"]["verdict"])
            self.assertFalse(passed["preIngestionHold"])
            self.assertEqual(factory.sha256_bytes(path.read_bytes()), passed["content"]["sha256"])
            admission.verify_admission(passed)

    def test_permission_required_negative_controls_do_not_read_bytes(self):
        for source_id in (
            "openstax:calculus-volume-1",
            "nice:guidelines-ai-negative-control",
        ):
            with self.subTest(source_id=source_id):
                missing_path = Path("/definitely/not/a/source/document")
                record = admission.build_admission(
                    self.catalog,
                    self.catalog_sha,
                    source_id,
                    "internal-rd-noncommercial",
                    missing_path,
                    [],
                    None,
                )
                self.assertEqual(admission.HOLD_PERMISSION, record["decision"]["verdict"])
                self.assertTrue(record["preIngestionHold"])
                self.assertIsNone(record["content"])
                admission.verify_admission(record)

    def test_conditional_bnf_source_is_context_bound(self):
        source_id = "bnf:gallica-tartuffe-1669-textebrut"
        with tempfile.TemporaryDirectory() as td:
            path = self.write_bytes(Path(td), data=b"gallica selection snapshot\n")
            commercial = admission.build_admission(
                self.catalog,
                self.catalog_sha,
                source_id,
                "commercial-product",
                path,
                self.accepted(source_id),
                None,
            )
            self.assertEqual(admission.HOLD_CONTEXT, commercial["decision"]["verdict"])
            self.assertIsNone(commercial["content"])

            research = admission.build_admission(
                self.catalog,
                self.catalog_sha,
                source_id,
                "internal-rd-noncommercial",
                path,
                self.accepted(source_id),
                None,
            )
            self.assertEqual(admission.PASS, research["decision"]["verdict"])
            self.assertIsNotNone(research["content"])

    def test_fixed_eurlex_legal_source_preserves_exact_version(self):
        source_id = "eurlex:gdpr-32016R0679-fr-oj"
        with tempfile.TemporaryDirectory() as td:
            path = self.write_bytes(Path(td), data=b"official journal snapshot\n")
            record = admission.build_admission(
                self.catalog,
                self.catalog_sha,
                source_id,
                "internal-rd-noncommercial",
                path,
                self.accepted(source_id),
                None,
            )
            self.assertEqual(admission.PASS, record["decision"]["verdict"])
            self.assertEqual(
                "CELEX-32016R0679-OJ-2016-05-04",
                record["source"]["version"],
            )

    def test_unresolved_third_party_rights_fail_before_file_read(self):
        mutated = copy.deepcopy(self.catalog)
        source = admission.source_by_id(mutated, "eu:pm2-v3.1")
        source["rights"]["thirdPartyContentStatus"] = "present-unresolved"
        missing_path = Path("/definitely/not/read")
        record = admission.build_admission(
            mutated,
            admission.digest(mutated),
            "eu:pm2-v3.1",
            "internal-rd-noncommercial",
            missing_path,
            self.accepted("eu:pm2-v3.1"),
            None,
        )
        self.assertEqual(admission.HOLD_THIRD_PARTY, record["decision"]["verdict"])
        self.assertIsNone(record["content"])

    def test_unknown_rights_fail_before_file_read(self):
        mutated = copy.deepcopy(self.catalog)
        source = admission.source_by_id(mutated, "eu:pm2-v3.1")
        source["rights"]["status"] = "unknown"
        source["rights"]["allowedUseContexts"] = []
        record = admission.build_admission(
            mutated,
            admission.digest(mutated),
            "eu:pm2-v3.1",
            "internal-rd-noncommercial",
            Path("/not/read"),
            [],
            None,
        )
        self.assertEqual(admission.HOLD_UNKNOWN, record["decision"]["verdict"])
        self.assertIsNone(record["content"])

    def test_physical_path_never_leaks_into_admission_record(self):
        source_id = "python:docs-fr-3.14.7-text"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self.write_bytes(root, "python-docs.zip", b"python docs snapshot\n")
            record = admission.build_admission(
                self.catalog,
                self.catalog_sha,
                source_id,
                "internal-rd-noncommercial",
                path,
                self.accepted(source_id),
                None,
            )
            rendered = factory.canonical_output(record)
            self.assertNotIn(str(root), rendered)
            self.assertNotIn(str(path), rendered)

    def test_missing_source_bytes_holds_without_exception(self):
        source_id = "eu:pm2-v3.1"
        record = admission.build_admission(
            self.catalog,
            self.catalog_sha,
            source_id,
            "internal-rd-noncommercial",
            None,
            self.accepted(source_id),
            None,
        )
        self.assertEqual(admission.HOLD_BYTES, record["decision"]["verdict"])
        self.assertIsNone(record["content"])
        admission.verify_admission(record)

    def test_tampered_admission_id_is_rejected(self):
        source_id = "has:flash-prescription-retranscription-2026"
        with tempfile.TemporaryDirectory() as td:
            path = self.write_bytes(Path(td))
            record = admission.build_admission(
                self.catalog,
                self.catalog_sha,
                source_id,
                "internal-rd-noncommercial",
                path,
                self.accepted(source_id),
                None,
            )
            record["decision"]["verdict"] = "PASS_FAKE"
            with self.assertRaises(admission.SourceAdmissionError):
                admission.verify_admission(record)

    def test_catalog_rejects_missing_primary_domain(self):
        mutated = copy.deepcopy(self.catalog)
        mutated["sources"] = [
            item for item in mutated["sources"]
            if not (item["domain"] == "management" and item["benchmarkRole"] == "primary")
        ]
        with self.assertRaises(admission.SourceAdmissionError):
            admission.validate_catalog(mutated)

    def test_catalog_rejects_negative_control_that_is_not_blocked(self):
        mutated = copy.deepcopy(self.catalog)
        source = admission.source_by_id(mutated, "openstax:calculus-volume-1")
        source["rights"]["status"] = "allowed"
        source["rights"]["allowedUseContexts"] = ["internal-rd-noncommercial"]
        with self.assertRaises(admission.SourceAdmissionError):
            admission.validate_catalog(mutated)


if __name__ == "__main__":
    unittest.main(verbosity=2)
