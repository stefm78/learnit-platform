#!/usr/bin/env python3
"""Product evidence for ATLAS-WP-012 M3.1 pedagogical quality."""
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

KITS = (
    ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json",
    ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json",
)
ZERO = "sha256:" + "0" * 64


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def refresh(package: dict) -> dict:
    """Refresh all derived Atlas claims/digests after a controlled mutation."""
    package = copy.deepcopy(package)
    package["packageRevisionDigest"] = ZERO
    for course in package["courses"]:
        course["courseRevisionDigest"] = ZERO
        for activity in course["activities"]:
            activity["activityRevisionDigest"] = ZERO
    atlas.rewrite_claims(package)
    errors = v2.fill_new_digests(package)
    if errors:
        raise AssertionError(errors)
    atlas.validate_package(package)
    return package


def first_objective(package: dict) -> tuple[dict, dict, list[dict]]:
    course = package["courses"][0]
    objective = course["objectives"][0]
    activities = [
        activity
        for activity in course["activities"]
        if activity["objectiveIds"] == [objective["objectiveId"]]
    ]
    return course, objective, activities


def make_excellent(package: dict) -> dict:
    """Produce a canonical one-objective candidate with zero M3.1 diagnostics."""
    package = copy.deepcopy(package)
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
    course["estimatedMinutes"] = sum(a["estimatedMinutes"] for a in course["activities"])
    # The first canonical objective already has qcm/fill diversity between validations.
    # Mark the second claim alternate-representation only in this controlled candidate.
    course["atlasValidationIndependenceClaims"][1]["basisCode"] = "alternate-representation"
    package["courses"] = [course]
    return refresh(package)


class QualityEngineTests(unittest.TestCase):
    def test_canonical_kits_pass_upstream_and_report_deterministically(self):
        schema = v2.load(ROOT / "contracts/learnit-kit-v2.schema.json")
        for path in KITS:
            package = load(path)
            self.assertTrue(v2.validate(path, package, schema, False).ok)
            self.assertTrue(atlas.validate_package(package))
            first = quality.analyze_package(package)
            second = quality.analyze_package(copy.deepcopy(package))
            self.assertTrue(first["canonicalValid"])
            self.assertEqual("PASS_ATLAS_PEDAGOGICAL_PROFILE_V1", first["verdict"])
            self.assertEqual(quality.report_bytes(first), quality.report_bytes(second))
            self.assertIn(first["qualityBand"], {"STRONG", "EXCELLENT_BY_PROFILE"})

    def test_canonical_invalid_never_gets_positive_quality_verdict(self):
        package = load(KITS[0])
        package["contract"] = "not.learnit.kit.v2"
        report = quality.analyze_package(package)
        self.assertFalse(report["canonicalValid"])
        self.assertEqual("HOLD_CANONICAL_INVALID", report["verdict"])
        self.assertEqual("BLOCKED", report["qualityBand"])
        self.assertGreater(report["counts"]["blocking"], 0)

    def test_malformed_canonical_input_is_hold_not_engine_error(self):
        package = {"contract": "learnit.kit.v2"}
        report = quality.analyze_package(package)
        self.assertFalse(report["canonicalValid"])
        self.assertEqual("HOLD_CANONICAL_INVALID", report["verdict"])
        self.assertEqual("BLOCKED", report["qualityBand"])

    def test_duration_warning(self):
        package = load(KITS[0])
        package["courses"][0]["estimatedMinutes"] += 1
        package = refresh(package)
        codes = {d["code"] for d in quality.analyze_package(package)["diagnostics"]}
        self.assertIn("PQ_COURSE_DURATION_MISMATCH", codes)

    def test_duplicate_stimulus_warning(self):
        package = load(KITS[0])
        _, _, activities = first_objective(package)
        source, correction = activities[0], activities[1]
        correction["prompt"] = source["prompt"]
        for left, right in zip(correction["choices"], source["choices"]):
            left["label"] = right["label"]
        correct_label = next(
            choice["label"] for choice in source["choices"]
            if choice["choiceId"] == source["correctChoiceId"]
        )
        correction["correctChoiceId"] = next(
            choice["choiceId"] for choice in correction["choices"]
            if choice["label"] == correct_label
        )
        package = refresh(package)
        codes = {d["code"] for d in quality.analyze_package(package)["diagnostics"]}
        self.assertIn("PQ_OBJECTIVE_DUPLICATE_STIMULUS", codes)

    def test_transfer_not_harder_warning(self):
        package = load(KITS[0])
        _, _, activities = first_objective(package)
        activities[4]["difficulty"] = activities[0]["difficulty"]
        package = refresh(package)
        codes = {d["code"] for d in quality.analyze_package(package)["diagnostics"]}
        self.assertIn("PQ_TRANSFER_NOT_HARDER", codes)

    def test_validation_chain_warning_does_not_require_third_claim(self):
        package = load(KITS[0])
        course, objective, _ = first_objective(package)
        claims = [
            claim for claim in course["atlasValidationIndependenceClaims"]
            if claim["objectiveId"] == objective["objectiveId"]
        ]
        self.assertEqual(2, len(claims))
        claims[0]["basisCode"] = "new-context"
        package = refresh(package)
        report = quality.analyze_package(package)
        self.assertTrue(report["canonicalValid"])
        self.assertEqual(
            2,
            len([
                claim
                for claim in package["courses"][0]["atlasValidationIndependenceClaims"]
                if claim["objectiveId"] == objective["objectiveId"]
            ]),
        )
        codes = {d["code"] for d in report["diagnostics"]}
        self.assertIn("PQ_VALIDATION_CHAIN_WEAK", codes)
        self.assertNotIn("PQ_TRANSFER_CLAIM_WEAK", codes)

    def test_advice_rules_are_present_without_becoming_blockers(self):
        package = load(KITS[1])
        report = quality.analyze_package(package)
        codes = {d["code"] for d in report["diagnostics"]}
        self.assertIn("PQ_OBJECTIVE_SINGLE_ACTIVITY_TYPE", codes)
        self.assertIn("PQ_VALIDATIONS_SAME_ACTIVITY_TYPE", codes)
        self.assertIn("PQ_NO_ALTERNATE_REPRESENTATION", codes)
        self.assertEqual(0, report["counts"]["blocking"])
        self.assertTrue(report["canonicalValid"])

    def test_excellent_candidate_and_cli_exit_contract(self):
        package = make_excellent(load(KITS[0]))
        report = quality.analyze_package(package)
        self.assertEqual("EXCELLENT_BY_PROFILE", report["qualityBand"])
        self.assertEqual({"blocking": 0, "warning": 0, "advice": 0}, report["counts"])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "excellent.json"
            path.write_text(json.dumps(package, ensure_ascii=False) + "\n", encoding="utf-8")
            command = [
                sys.executable,
                "-B",
                str(ROOT / "authoring/v2/atlas/pedagogical_quality.py"),
                str(path),
                "--json",
                "--require-excellent",
            ]
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            after = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(before, after)
            packed = json.loads(completed.stdout)
            self.assertEqual("EXCELLENT_BY_PROFILE", packed["qualityBand"])

    def test_require_excellent_rejects_non_excellent_without_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "strong.json"
            path.write_bytes(KITS[0].read_bytes())
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "authoring/v2/atlas/pedagogical_quality.py"),
                    str(path),
                    "--json",
                    "--require-excellent",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(3, completed.returncode)
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertTrue(json.loads(completed.stdout)["canonicalValid"])

    def test_engine_contains_no_network_or_write_api(self):
        text = (ROOT / "authoring/v2/atlas/pedagogical_quality.py").read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "httpx",
            "aiohttp",
            "urllib.request",
            "socket.",
            ".write_text(",
            ".write_bytes(",
            "open(",
        ):
            self.assertNotIn(forbidden, text)


class StudioIntegrationTests(unittest.TestCase):
    def test_studio_returns_quality_separately_from_export_validity(self):
        raw = KITS[0].read_bytes()
        draft = create_draft(raw, KITS[0].name)
        verdict = validate_draft(draft)
        self.assertTrue(verdict["ok"])
        self.assertTrue(verdict["exportAvailable"])
        self.assertIsNotNone(verdict["pedagogicalQuality"])
        self.assertTrue(verdict["pedagogicalQuality"]["canonicalValid"])

        package = draft["package"]
        _, _, activities = first_objective(package)
        transfer_index = package["courses"][0]["activities"].index(activities[4])
        edited = apply_edit(
            draft,
            ["courses", 0, "activities", transfer_index, "difficulty"],
            activities[0]["difficulty"],
        )
        verdict = validate_draft(edited)
        self.assertTrue(verdict["exportAvailable"])
        codes = {
            item["code"]
            for item in verdict["pedagogicalQuality"]["diagnostics"]
        }
        self.assertIn("PQ_TRANSFER_NOT_HARDER", codes)

    def test_browser_javascript_renders_but_does_not_define_quality_rules(self):
        js = (ROOT / "authoring/studio/web/studio.js").read_text(encoding="utf-8")
        self.assertIn("pedagogicalQuality", js)
        self.assertIn("qualityBand", js)
        self.assertNotIn("PQ_", js)


class PagesIntegrationTests(unittest.TestCase):
    def test_pages_bundle_copies_exact_quality_engine(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "site"
            evidence = build_pages(out)
            relative = "authoring/v2/atlas/pedagogical_quality.py"
            source = ROOT / relative
            bundled = out / "_authority" / relative
            self.assertEqual(source.read_bytes(), bundled.read_bytes())
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(),
                evidence["authority"][relative]["sha256"],
            )
            bootstrap = (out / "pages-bootstrap.js").read_text(encoding="utf-8")
            self.assertIn("pedagogical_quality.py", bootstrap)
            self.assertNotIn("PQ_", bootstrap)

    def test_pages_and_python_core_return_equivalent_quality_report(self):
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
                    page.wait_for_function(
                        "window.__learnitPagesReady === true", timeout=120000
                    )
                    page.locator("#sample-complexes").click()
                    page.wait_for_function(
                        "() => Boolean(localStorage.getItem('learnit.authoring.m3.v1'))",
                        timeout=60000,
                    )
                    draft = json.loads(
                        page.evaluate(
                            "() => localStorage.getItem('learnit.authoring.m3.v1')"
                        )
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
                    self.assertTrue(page.locator("#quality-badge").is_visible())
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
