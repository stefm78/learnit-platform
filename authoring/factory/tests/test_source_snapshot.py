#!/usr/bin/env python3
"""Product oracle for ATLAS-WP-017 real-source snapshot runner."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import source_admission as admission
from authoring.factory import source_snapshot as snapshot

CATALOG = ROOT / "authoring/factory/benchmark_sources_v1.json"


class FakeFetcher:
    def __init__(self, *, fail_url=None, duplicate_urls=None):
        self.calls = []
        self.fail_url = fail_url
        self.duplicate_urls = set(duplicate_urls or [])

    def __call__(self, url):
        self.calls.append(url)
        if url == self.fail_url:
            raise snapshot.SnapshotError("synthetic retrieval failure")
        if url in self.duplicate_urls:
            data = b"same-primary-source-bytes\n"
        else:
            data = ("snapshot:" + url + "\n").encode("utf-8")
        media = "application/octet-stream"
        if url.endswith(".pdf"):
            media = "application/pdf"
        elif url.endswith(".zip"):
            media = "application/zip"
        elif url.endswith("/") or "." not in url.rsplit("/", 1)[-1]:
            media = "text/html"
        return {
            "bytes": data,
            "mediaType": media,
            "finalUrl": url,
            "etag": None,
            "lastModified": None,
        }


class SnapshotTests(unittest.TestCase):
    def catalog(self):
        return admission.load_catalog(CATALOG)[0]

    def source_url(self, source_id):
        return admission.source_by_id(self.catalog(), source_id)["sourceUrl"]

    def test_full_catalog_snapshot_passes_and_never_fetches_negative_controls(self):
        fetcher = FakeFetcher()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = snapshot.snapshot_catalog(
                CATALOG,
                root,
                "2026-09-01",
                fetcher=fetcher,
            )
            self.assertEqual(snapshot.PASS, manifest["verdict"])
            primary = [
                row for row in manifest["sources"]
                if row["benchmarkRole"] == "primary"
            ]
            self.assertEqual(admission.REQUIRED_DOMAINS, {row["domain"] for row in primary})
            self.assertTrue(all(row["retrieval"] == "downloaded" for row in primary))
            self.assertTrue(all(row["admissionVerdict"] == admission.PASS for row in primary))

            catalog = self.catalog()
            negative_urls = {
                item["sourceUrl"]
                for item in catalog["sources"]
                if item["benchmarkRole"] == "negative-control"
            }
            self.assertTrue(negative_urls.isdisjoint(fetcher.calls))

            negative_rows = [
                row for row in manifest["sources"]
                if row["benchmarkRole"] == "negative-control"
            ]
            self.assertTrue(all(row["retrieval"] == "not-attempted" for row in negative_rows))
            self.assertTrue(all(row["admissionVerdict"] == admission.HOLD_PERMISSION for row in negative_rows))

            rendered = json.dumps(manifest, sort_keys=True)
            self.assertNotIn(str(root), rendered)
            self.assertTrue((root / "source_snapshot_manifest.json").exists())

    def test_exact_constitution_source_version_is_preserved_in_admission(self):
        fetcher = FakeFetcher()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = snapshot.snapshot_catalog(
                CATALOG,
                root,
                "2026-09-01",
                fetcher=fetcher,
            )
            self.assertEqual(snapshot.PASS, manifest["verdict"])
            record_path = root / "admissions" / "nara_us-constitution-transcript.json"
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(
                "1787-parchment-transcript",
                record["source"]["version"],
            )
            self.assertEqual(admission.PASS, record["decision"]["verdict"])

    def test_text_endpoint_html_interstitial_is_rejected(self):
        with self.assertRaisesRegex(snapshot.SnapshotError, "source-content mismatch"):
            snapshot.validate_fetched_payload(
                "https://gallica.bnf.fr/ark:/12148/bpt6k701569.texteBrut",
                "text/html",
                b"<html><title>Gallica | Verification de securite</title></html>",
            )

    def test_generic_security_interstitial_is_rejected(self):
        payload = (
            "<html><head><title>Gallica | Vérification de sécurité</title></head>"
            "<body><altcha-widget></altcha-widget></body></html>"
        ).encode("utf-8")
        with self.assertRaisesRegex(snapshot.SnapshotError, "interstitial/security page"):
            snapshot.validate_fetched_payload(
                "https://example.test/source",
                "text/html",
                payload,
            )

    def test_retrieval_failure_holds_snapshot(self):
        failed_url = self.source_url("python:docs-fr-3.14.7-text")
        fetcher = FakeFetcher(fail_url=failed_url)
        with tempfile.TemporaryDirectory() as td:
            manifest = snapshot.snapshot_catalog(
                CATALOG,
                Path(td),
                "2026-09-01",
                fetcher=fetcher,
            )
            self.assertEqual(snapshot.HOLD, manifest["verdict"])
            self.assertTrue(any(
                reason.startswith("SOURCE_RETRIEVAL_FAILED:python:docs-fr-3.14.7-text")
                for reason in manifest["reasons"]
            ))
            row = next(
                row for row in manifest["sources"]
                if row["sourceId"] == "python:docs-fr-3.14.7-text"
            )
            self.assertEqual("failed", row["retrieval"])
            self.assertIsNone(row["sha256"])

    def test_duplicate_primary_content_is_rejected(self):
        catalog = self.catalog()
        primary_urls = [
            item["sourceUrl"]
            for item in catalog["sources"]
            if item["benchmarkRole"] == "primary"
        ]
        fetcher = FakeFetcher(duplicate_urls=primary_urls[:2])
        with tempfile.TemporaryDirectory() as td:
            manifest = snapshot.snapshot_catalog(
                CATALOG,
                Path(td),
                "2026-09-01",
                fetcher=fetcher,
            )
            self.assertEqual(snapshot.HOLD, manifest["verdict"])
            self.assertTrue(any(
                reason.startswith("DUPLICATE_PRIMARY_SOURCE_CONTENT:")
                for reason in manifest["reasons"]
            ))

    def test_artifact_locators_are_relative_and_path_free(self):
        fetcher = FakeFetcher()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = snapshot.snapshot_catalog(
                CATALOG,
                root,
                "2026-09-01",
                fetcher=fetcher,
            )
            for row in manifest["sources"]:
                artifact = row["artifactFile"]
                if artifact is not None:
                    self.assertTrue(artifact.startswith("sources/"))
                    self.assertFalse(Path(artifact).is_absolute())
            self.assertNotIn(str(root), json.dumps(manifest))

    def test_snapshot_date_must_be_iso_date(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(snapshot.SnapshotError):
                snapshot.snapshot_catalog(
                    CATALOG,
                    Path(td),
                    "01/09/2026",
                    fetcher=FakeFetcher(),
                )

    def test_negative_control_catalog_regression_stays_blocked(self):
        catalog = self.catalog()
        for source_id in (
            "openstax:calculus-volume-1",
            "nice:guidelines-ai-negative-control",
        ):
            source = admission.source_by_id(catalog, source_id)
            verdict, reasons, _ = admission.pre_ingestion_decision(
                source,
                catalog["defaultUseContext"],
                set(source["rights"]["conditions"]),
                None,
            )
            self.assertEqual(admission.HOLD_PERMISSION, verdict)
            self.assertTrue(reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
