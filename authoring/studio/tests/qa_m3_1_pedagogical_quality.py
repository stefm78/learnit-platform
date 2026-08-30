#!/usr/bin/env python3
"""Independent contradictory QA for ATLAS-WP-012 M3.1 pedagogical quality."""
from __future__ import annotations

import copy
import hashlib
import http.server
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.studio.core import apply_edit, create_draft, validate_draft
from authoring.studio.pages.build_pages import build as build_pages
from authoring.v2 import validate_kit as v2
from authoring.v2.atlas import pedagogical_quality as quality
from authoring.v2.atlas import validate_atlas_content as atlas

SIGNALS = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"
COMPLEX = ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json"
QUALITY_PATH = ROOT / "authoring/v2/atlas/pedagogical_quality.py"
ZERO = "sha256:" + "0" * 64


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def refresh(package: dict) -> dict:
    """Refresh only canonical derived values after an adversarial semantic mutation."""
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


def objective_rows(package: dict, objective_index: int) -> tuple[dict, dict, list[tuple[int, dict]]]:
    course = package["courses"][0]
    objective = course["objectives"][objective_index]
    oid = objective["objectiveId"]
    rows = [
        (index, activity)
        for index, activity in enumerate(course["activities"])
        if activity["objectiveIds"] == [oid]
    ]
    if len(rows) != 5:
        raise AssertionError(f"expected five Atlas rows, got {len(rows)}")
    return course, objective, rows


def excellent_signals_candidate() -> dict:
    """Build a canonical one-objective candidate distinct from product-test fixtures."""
    package = copy.deepcopy(load(SIGNALS))
    course = package["courses"][0]
    objective = course["objectives"][0]
    oid = objective["objectiveId"]
    course["objectives"] = [objective]
    course["activities"] = [
        activity for activity in course["activities"] if activity["objectiveIds"] == [oid]
    ]
    course["atlasValidationIndependenceClaims"] = [
        claim
        for claim in course["atlasValidationIndependenceClaims"]
        if claim["objectiveId"] == oid
    ]
    course["atlasValidationIndependenceClaims"][0]["basisCode"] = "alternate-representation"
    course["estimatedMinutes"] = sum(a["estimatedMinutes"] for a in course["activities"])
    package["courses"] = [course]
    return refresh(package)


def run_cli(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(QUALITY_PATH), str(path), "--json", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


class IndependentQualityOracle(unittest.TestCase):
    def test_malformed_and_canonical_invalid_fail_closed(self):
        malformed = quality.analyze_package({"contract": "learnit.kit.v2"})
        self.assertFalse(malformed["canonicalValid"])
        self.assertEqual("HOLD_CANONICAL_INVALID", malformed["verdict"])
        self.assertEqual("BLOCKED", malformed["qualityBand"])
        self.assertGreater(malformed["counts"]["blocking"], 0)

        wrong_contract = load(SIGNALS)
        wrong_contract["contract"] = "learnit.kit.v999"
        invalid = quality.analyze_package(wrong_contract)
        self.assertFalse(invalid["canonicalValid"])
        self.assertEqual("HOLD_CANONICAL_INVALID", invalid["verdict"])
        self.assertTrue(all(d["severity"] == "blocking" for d in invalid["diagnostics"]))

        required = {"code", "severity", "path", "refs", "cause", "impact", "fix"}
        for item in malformed["diagnostics"] + invalid["diagnostics"]:
            self.assertTrue(required.issubset(item), item)

    def test_report_bytes_and_diagnostic_order_are_deterministic(self):
        package = load(SIGNALS)
        first = quality.analyze_package(package)
        second = quality.analyze_package(copy.deepcopy(package))
        self.assertEqual(quality.report_bytes(first), quality.report_bytes(second))
        self.assertTrue(quality.report_bytes(first).endswith(b"\n"))
        keys = [
            (quality.SEVERITY_ORDER.get(d["severity"], 99), d["path"], d["code"])
            for d in first["diagnostics"]
        ]
        self.assertEqual(sorted(keys), keys)

    def test_advice_is_not_a_schema_or_export_blocker(self):
        report = quality.analyze_package(load(SIGNALS))
        self.assertTrue(report["canonicalValid"])
        self.assertEqual("PASS_ATLAS_PEDAGOGICAL_PROFILE_V1", report["verdict"])
        self.assertEqual(0, report["counts"]["blocking"])
        self.assertGreater(report["counts"]["advice"], 0)
        self.assertNotEqual("BLOCKED", report["qualityBand"])

        draft = create_draft(SIGNALS.read_bytes(), SIGNALS.name)
        validation = validate_draft(draft)
        self.assertTrue(validation["ok"], validation)
        self.assertTrue(validation["exportAvailable"], validation)
        self.assertEqual(0, validation["pedagogicalQuality"]["counts"]["blocking"])

    def test_duration_mismatch_is_quality_warning_only(self):
        package = load(SIGNALS)
        package["courses"][0]["estimatedMinutes"] += 3
        package = refresh(package)
        report = quality.analyze_package(package)
        codes = {d["code"] for d in report["diagnostics"]}
        self.assertIn("PQ_COURSE_DURATION_MISMATCH", codes)
        self.assertTrue(report["canonicalValid"])
        self.assertEqual(0, report["counts"]["blocking"])

    def test_duplicate_stimulus_detected_on_second_signals_objective(self):
        package = load(SIGNALS)
        _, _, rows = objective_rows(package, 1)
        source = rows[0][1]
        duplicate = rows[3][1]
        self.assertEqual("qcm", source["type"])
        self.assertEqual("qcm", duplicate["type"])
        self.assertEqual(len(source["choices"]), len(duplicate["choices"]))

        duplicate["prompt"] = source["prompt"]
        for left, right in zip(duplicate["choices"], source["choices"]):
            left["label"] = right["label"]
        source_answer = next(
            c["label"] for c in source["choices"] if c["choiceId"] == source["correctChoiceId"]
        )
        duplicate["correctChoiceId"] = next(
            c["choiceId"] for c in duplicate["choices"] if c["label"] == source_answer
        )
        package = refresh(package)
        report = quality.analyze_package(package)
        self.assertIn(
            "PQ_OBJECTIVE_DUPLICATE_STIMULUS",
            {d["code"] for d in report["diagnostics"]},
        )
        self.assertTrue(report["canonicalValid"])

    def test_transfer_calibration_detected_on_second_signals_objective(self):
        package = load(SIGNALS)
        _, _, rows = objective_rows(package, 1)
        practice = rows[0][1]
        transfer = rows[4][1]
        transfer["difficulty"] = practice["difficulty"]
        package = refresh(package)
        report = quality.analyze_package(package)
        self.assertIn("PQ_TRANSFER_NOT_HARDER", {d["code"] for d in report["diagnostics"]})
        self.assertTrue(report["canonicalValid"])

    def test_weak_claim_topology_keeps_exactly_two_claims(self):
        package = load(SIGNALS)
        course, objective, _ = objective_rows(package, 1)
        oid = objective["objectiveId"]
        claims = [c for c in course["atlasValidationIndependenceClaims"] if c["objectiveId"] == oid]
        self.assertEqual(2, len(claims))
        claims[0]["basisCode"] = "new-context"
        package = refresh(package)

        report = quality.analyze_package(package)
        self.assertTrue(report["canonicalValid"])
        self.assertIn("PQ_VALIDATION_CHAIN_WEAK", {d["code"] for d in report["diagnostics"]})
        self.assertNotIn("PQ_TRANSFER_CLAIM_WEAK", {d["code"] for d in report["diagnostics"]})
        final_claims = [
            c
            for c in package["courses"][0]["atlasValidationIndependenceClaims"]
            if c["objectiveId"] == oid
        ]
        self.assertEqual(2, len(final_claims))

    def test_cli_exit_classes_and_no_input_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            excellent = root / "excellent.json"
            strong = root / "strong.json"
            invalid = root / "invalid.json"
            broken = root / "broken.json"

            excellent.write_text(json.dumps(excellent_signals_candidate(), ensure_ascii=False) + "\n", encoding="utf-8")
            strong.write_bytes(SIGNALS.read_bytes())
            bad = load(SIGNALS)
            bad["contract"] = "learnit.kit.bad"
            invalid.write_text(json.dumps(bad, ensure_ascii=False) + "\n", encoding="utf-8")
            broken.write_text('{"contract":', encoding="utf-8")

            before = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (excellent, strong, invalid, broken)
            }
            self.assertEqual(0, run_cli(excellent, "--require-excellent").returncode)
            self.assertEqual(3, run_cli(strong, "--require-excellent").returncode)
            self.assertEqual(2, run_cli(invalid).returncode)
            self.assertEqual(4, run_cli(broken).returncode)
            after = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (excellent, strong, invalid, broken)
            }
            self.assertEqual(before, after)

    def test_quality_engine_has_no_network_or_write_primitive(self):
        source = QUALITY_PATH.read_text(encoding="utf-8")
        forbidden = (
            "requests",
            "httpx",
            "aiohttp",
            "urllib.request",
            "socket.",
            "WebSocket",
            "XMLHttpRequest",
            ".write_text(",
            ".write_bytes(",
        )
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_studio_separates_canonical_validity_quality_and_export(self):
        draft = create_draft(SIGNALS.read_bytes(), SIGNALS.name)
        baseline = validate_draft(draft)
        self.assertTrue(baseline["ok"], baseline)
        self.assertTrue(baseline["exportAvailable"], baseline)
        self.assertTrue(baseline["pedagogicalQuality"]["canonicalValid"])

        _, _, rows = objective_rows(draft["package"], 0)
        transfer_index, transfer = rows[4]
        first_practice = rows[0][1]
        edited = apply_edit(
            draft,
            ["courses", 0, "activities", transfer_index, "difficulty"],
            first_practice["difficulty"],
        )
        verdict = validate_draft(edited)
        self.assertTrue(verdict["ok"], verdict)
        self.assertTrue(verdict["exportAvailable"], verdict)
        self.assertTrue(verdict["pedagogicalQuality"]["canonicalValid"])
        self.assertIn(
            "PQ_TRANSFER_NOT_HARDER",
            {d["code"] for d in verdict["pedagogicalQuality"]["diagnostics"]},
        )

    def test_browser_javascript_is_renderer_not_quality_authority(self):
        js = (ROOT / "authoring/studio/web/studio.js").read_text(encoding="utf-8")
        html = (ROOT / "authoring/studio/web/index.html").read_text(encoding="utf-8")
        self.assertNotIn("PQ_", js)
        self.assertEqual(1, js.count("function renderPedagogicalQuality("))
        self.assertEqual(1, js.count("function renderDiagnostics("))
        self.assertIn("pedagogicalQuality", js)
        self.assertIn('id="diagnostics-title">Validité du kit', html)
        self.assertIn('id="quality-title">Complétude et solidité', html)
        self.assertIn("ne prouve ni maîtrise, ni rétention", html)


class IndependentPagesOracle(unittest.TestCase):
    def test_pages_bundle_is_deterministic_and_copies_exact_python_authority(self):
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / "a"
            b = Path(td) / "b"
            evidence_a = build_pages(a)
            evidence_b = build_pages(b)
            self.assertEqual(evidence_a, evidence_b)
            relative = "authoring/v2/atlas/pedagogical_quality.py"
            bundled = a / "_authority" / relative
            self.assertEqual(QUALITY_PATH.read_bytes(), bundled.read_bytes())
            self.assertEqual(
                hashlib.sha256(QUALITY_PATH.read_bytes()).hexdigest(),
                evidence_a["authority"][relative]["sha256"],
            )
            bootstrap = (a / "pages-bootstrap.js").read_text(encoding="utf-8")
            self.assertIn("pedagogical_quality.py", bootstrap)
            self.assertNotIn("PQ_", bootstrap)

    def test_browser_pyodide_matches_direct_python_on_signals_sample(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            self.skipTest(f"playwright unavailable: {exc}")

        with tempfile.TemporaryDirectory() as td:
            site = Path(td) / "site"
            build_pages(site)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]

            handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
                *a, directory=str(site), **kw
            )
            server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(
                        f"http://127.0.0.1:{port}/",
                        wait_until="domcontentloaded",
                        timeout=120000,
                    )
                    page.wait_for_function("window.__learnitPagesReady === true", timeout=120000)
                    page.locator("#sample-signaux").click()
                    page.wait_for_function(
                        """() => Boolean(localStorage.getItem('learnit.authoring.m3.v1')) ||
                                 Boolean(window.__learnitPagesSampleError)""",
                        timeout=60000,
                    )
                    sample_error = page.evaluate("() => window.__learnitPagesSampleError || null")
                    self.assertIsNone(sample_error, sample_error)
                    draft = json.loads(
                        page.evaluate("() => localStorage.getItem('learnit.authoring.m3.v1')")
                    )
                    expected = validate_draft(draft)["pedagogicalQuality"]
                    actual = page.evaluate(
                        """async () => {
                          const draft = JSON.parse(localStorage.getItem('learnit.authoring.m3.v1'));
                          const response = await fetch('/api/validate', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({draft}),
                          });
                          return (await response.json()).validation.pedagogicalQuality;
                        }"""
                    )
                    self.assertEqual(expected, actual)
                    self.assertIn("Canonique", page.locator("#validation-badge").inner_text())
                    self.assertNotEqual("À analyser", page.locator("#quality-badge").inner_text())
                    self.assertFalse(page.locator("#export").is_disabled())
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
