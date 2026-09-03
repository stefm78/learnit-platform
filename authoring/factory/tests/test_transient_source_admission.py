#!/usr/bin/env python3
"""Product evidence for ATLAS-WP-023 transient private user-source admission."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import transient_source_admission as transient


def declaration(source_id: str = "epf_source", version: str = "2026-09") -> dict:
    return {
        "schema": transient.DECLARATION_SCHEMA,
        "profile": transient.DECLARATION_PROFILE,
        "declarationVersion": transient.DECLARATION_VERSION,
        "sourceId": source_id,
        "version": version,
        "provenance": transient.PROVENANCE,
        "processingContext": transient.PROCESSING_CONTEXT,
        "authorizationBasis": transient.AUTHORIZATION_BASIS,
        "userDeclarationAccepted": True,
        "retention": transient.RETENTION,
        "redistribution": transient.REDISTRIBUTION,
        "legalRightsVerified": False,
    }


class TransientAdmissionTests(unittest.TestCase):
    def test_pass_binds_exact_bytes_without_claiming_legal_verification(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.pdf"
            source.write_bytes(b"%PDF-1.7\nprivate user source\n")
            record = transient.build_admission(declaration(), source)
            self.assertEqual(transient.PASS, record["decision"]["verdict"])
            self.assertFalse(record["preIngestionHold"])
            self.assertFalse(record["declaration"]["legalRightsVerified"])
            self.assertEqual(len(source.read_bytes()), record["content"]["bytes"])
            transient.verify_admission(record)
            transient.reproduce_admission(record, source)

    def test_same_bytes_and_declaration_are_path_independent(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            left = Path(a) / "a.pdf"
            right = Path(b) / "renamed.pdf"
            payload = b"%PDF-1.7\nidentical source\n"
            left.write_bytes(payload)
            right.write_bytes(payload)
            self.assertEqual(
                transient.build_admission(declaration(), left),
                transient.build_admission(declaration(), right),
            )

    def test_source_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.pdf"
            source.write_bytes(b"original")
            record = transient.build_admission(declaration(), source)
            source.write_bytes(b"drift")
            with self.assertRaises(transient.TransientSourceAdmissionError):
                transient.reproduce_admission(record, source)

    def test_declaration_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.pdf"
            source.write_bytes(b"source")
            record = transient.build_admission(declaration(), source)
            tampered = copy.deepcopy(record)
            tampered["declaration"]["version"] = "changed"
            with self.assertRaises(transient.TransientSourceAdmissionError):
                transient.verify_admission(tampered)

    def assert_hold_without_reading_bytes(self, patch: dict, expected: str):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "does-not-exist.pdf"
            value = declaration()
            value.update(patch)
            record = transient.build_admission(value, missing)
            self.assertEqual(expected, record["decision"]["verdict"])
            self.assertTrue(record["preIngestionHold"])
            self.assertIsNone(record["content"])
            transient.verify_admission(record)

    def test_false_user_declaration_holds_before_bytes(self):
        self.assert_hold_without_reading_bytes(
            {"userDeclarationAccepted": False},
            transient.HOLD_DECLARATION,
        )

    def test_wrong_processing_context_holds_before_bytes(self):
        self.assert_hold_without_reading_bytes(
            {"processingContext": "public-demo"},
            transient.HOLD_CONTEXT,
        )

    def test_persistent_retention_holds_before_bytes(self):
        self.assert_hold_without_reading_bytes(
            {"retention": "persistent"},
            transient.HOLD_RETENTION,
        )

    def test_redistribution_not_prohibited_holds_before_bytes(self):
        self.assert_hold_without_reading_bytes(
            {"redistribution": "allowed"},
            transient.HOLD_REDISTRIBUTION,
        )

    def test_claiming_legal_verification_holds_before_bytes(self):
        self.assert_hold_without_reading_bytes(
            {"legalRightsVerified": True},
            transient.HOLD_LEGAL_CLAIM,
        )

    def test_wrong_provenance_holds_before_bytes(self):
        self.assert_hold_without_reading_bytes(
            {"provenance": "platform-catalog"},
            transient.HOLD_DECLARATION,
        )

    def test_missing_bytes_for_valid_declaration_is_hold(self):
        record = transient.build_admission(declaration(), None)
        self.assertEqual(transient.HOLD_BYTES, record["decision"]["verdict"])
        self.assertTrue(record["preIngestionHold"])
        self.assertIsNone(record["content"])
        transient.verify_admission(record)

    def test_missing_field_is_fail_closed_input_hold(self):
        value = declaration()
        del value["userDeclarationAccepted"]
        with self.assertRaises(transient.TransientSourceAdmissionError):
            transient.build_admission(value, None)

    def test_invalid_version_is_fail_closed(self):
        value = declaration(version="bad version")
        with self.assertRaises(transient.TransientSourceAdmissionError):
            transient.build_admission(value, None)

    def test_source_id_outside_factory_binding_grammar_is_rejected(self):
        value = declaration(source_id="user:private-course")
        self.assertIsNone(transient.SOURCE_ID.fullmatch(value["sourceId"]))
        with self.assertRaises(transient.TransientSourceAdmissionError):
            transient.build_admission(value, None)

    def test_factory_compatible_source_id_still_passes(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.pdf"
            source.write_bytes(b"%PDF-1.7\nsource\n")
            value = declaration(source_id="user.private-course_01")
            self.assertIsNotNone(transient.SOURCE_ID.fullmatch(value["sourceId"]))
            record = transient.build_admission(value, source)
            self.assertEqual(transient.PASS, record["decision"]["verdict"])

    def test_source_id_over_160_chars_is_rejected(self):
        value = declaration(source_id="a" * 161)
        self.assertIsNone(transient.SOURCE_ID.fullmatch(value["sourceId"]))
        with self.assertRaises(transient.TransientSourceAdmissionError):
            transient.build_admission(value, None)

    def test_very_long_source_id_is_rejected(self):
        value = declaration(source_id="a" * 300)
        self.assertIsNone(transient.SOURCE_ID.fullmatch(value["sourceId"]))
        with self.assertRaises(transient.TransientSourceAdmissionError):
            transient.build_admission(value, None)

    def test_source_id_exactly_160_chars_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.pdf"
            source.write_bytes(b"%PDF-1.7\nsource\n")
            value = declaration(source_id="a" * 160)
            self.assertIsNotNone(transient.SOURCE_ID.fullmatch(value["sourceId"]))
            record = transient.build_admission(value, source)
            self.assertEqual(transient.PASS, record["decision"]["verdict"])

    def test_windows_reserved_source_ids_are_rejected_before_bytes(self):
        missing = Path("/definitely/not/present/transient-reserved")
        for source_id in ("CON", "con.pdf", "PRN", "AUX", "NUL", "COM1", "com9.notes", "LPT1", "lpt9"):
            with self.subTest(source_id=source_id):
                with self.assertRaisesRegex(
                    transient.TransientSourceAdmissionError,
                    "portable on Windows",
                ):
                    transient.build_admission(declaration(source_id=source_id), missing)

    def test_cli_admit_and_verify_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.pdf"
            source.write_bytes(b"%PDF-1.7\nsource\n")
            decl = root / "declaration.json"
            decl.write_text(json.dumps(declaration()), encoding="utf-8")
            record = root / "admission.json"

            admit = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "authoring/factory/transient_source_admission.py"),
                    "admit",
                    "--declaration",
                    str(decl),
                    "--file",
                    str(source),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, admit.returncode, admit.stdout + admit.stderr)
            value = json.loads(admit.stdout)
            self.assertEqual(transient.PASS, value["decision"]["verdict"])
            record.write_text(admit.stdout, encoding="utf-8")

            verify = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "authoring/factory/transient_source_admission.py"),
                    "verify-admission",
                    "--record",
                    str(record),
                    "--file",
                    str(source),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
