#!/usr/bin/env python3
"""Independent contradictory QA for the exact ATLAS-WP-010 Pages candidate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

PRODUCT_HEAD = "e3db34b2da3fc270451a6f63b6229c16e8e5113e"
FROZEN_M3_HEAD = "a1b9259955ce748cd7e47531a470cd12b7dc0436"
LIVE_ROOT = "https://stefm78.github.io/learnit-platform/"
LIVE_AUTHORING = LIVE_ROOT + "authoring/"
PYODIDE_BASE = "https://cdn.jsdelivr.net/pyodide/v0.29.4/full/"
LEARNER_BYTES = 366412
LEARNER_SHA = "4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7"

QA_PATHS = {
    "work-packages/QA-WP-020.json",
    "authoring/studio/tests/qa_m3_pages_packaging.py",
    ".github/workflows/atlas-m3-pages-qa.yml",
}
PRODUCT_PATHS = {
    "work-packages/ATLAS-WP-010.json",
    "authoring/studio/pages/README.md",
    "authoring/studio/pages/build_pages.py",
    "authoring/studio/pages/pages-bootstrap.js",
    "authoring/studio/tests/test_m3_pages_packaging.py",
    ".github/workflows/atlas-m3-pages-candidate.yml",
}
FROZEN_M3_PATHS = (
    "work-packages/ATLAS-WP-009.json",
    "authoring/studio/README.md",
    "authoring/studio/core.py",
    "authoring/studio/server.py",
    "authoring/studio/web/index.html",
    "authoring/studio/web/studio.css",
    "authoring/studio/web/studio.js",
    "authoring/studio/tests/test_m3_authoring_foundation.py",
    ".github/workflows/atlas-m3-authoring-foundation-ci.yml",
)


def git(*args: str) -> str:
    done = subprocess.run(("git",) + args, cwd=ROOT, text=True, capture_output=True, check=False)
    if done.returncode:
        raise AssertionError(done.stderr or done.stdout)
    return done.stdout.strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "learnit-qa-wp-020"})
    with urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise AssertionError(f"HTTP {response.status}: {url}")
        return response.read()


class ExactHeadAndStaticOracle(unittest.TestCase):
    def test_qa_delta_is_exactly_qa_owned(self):
        changed = set(filter(None, git("diff", "--name-only", PRODUCT_HEAD + "...HEAD").splitlines()))
        self.assertEqual(changed, QA_PATHS)

    def test_product_delta_is_exact_packaging_scope(self):
        changed = set(filter(None, git("diff", "--name-only", FROZEN_M3_HEAD + "..." + PRODUCT_HEAD).splitlines()))
        self.assertEqual(changed, PRODUCT_PATHS)

    def test_frozen_m3_foundation_is_byte_unchanged(self):
        changed = git("diff", "--name-only", FROZEN_M3_HEAD, PRODUCT_HEAD, "--", *FROZEN_M3_PATHS)
        self.assertEqual(changed, "")

    def test_generated_authorities_and_samples_are_exact_copies(self):
        from authoring.studio.pages.build_pages import build

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "site"
            evidence = build(out)
            for relative, record in evidence["authority"].items():
                source = ROOT / relative
                copy = out / "_authority" / relative
                self.assertEqual(record["sha256"], sha256(source.read_bytes()))
                self.assertEqual(copy.read_bytes(), source.read_bytes())
            atlas = ROOT / "authoring" / "v2" / "atlas"
            for name, record in evidence["samples"].items():
                source = atlas / name
                copy = out / "samples" / name
                self.assertEqual(record["sha256"], sha256(source.read_bytes()))
                self.assertEqual(copy.read_bytes(), source.read_bytes())

    def test_adapter_delegates_to_python_and_contains_network_guard(self):
        text = (ROOT / "authoring/studio/pages/pages-bootstrap.js").read_text(encoding="utf-8")
        self.assertIn("from authoring.studio import core as _core", text)
        for call in ("_core.create_draft", "_core.apply_edit", "_core.validate_draft", "_core.build_preview", "_core.export_draft"):
            self.assertIn(call, text)
        self.assertIn("M3_PAGES_EXTERNAL_NETWORK_BLOCKED", text)
        self.assertIn(PYODIDE_BASE, text)
        self.assertNotIn("function validatePackage", text)

    def test_live_learner_root_and_samples_are_exact(self):
        learner = fetch(LIVE_ROOT)
        self.assertEqual(len(learner), LEARNER_BYTES)
        self.assertEqual(sha256(learner), LEARNER_SHA)
        atlas = ROOT / "authoring" / "v2" / "atlas"
        for name in ("nombres_complexes_atlas.json", "signaux_electriques_atlas.json"):
            self.assertEqual(fetch(LIVE_AUTHORING + "samples/" + name), (atlas / name).read_bytes())


class LiveBrowserContradictoryOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise unittest.SkipTest(f"playwright unavailable: {exc}")
        cls.sync_playwright = staticmethod(sync_playwright)

    def test_live_authoring_noop_edit_tamper_preview_and_network(self):
        from authoring.studio.core import create_draft, export_draft

        source_path = ROOT / "authoring" / "v2" / "atlas" / "nombres_complexes_atlas.json"
        source = source_path.read_bytes()
        with self.sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            requests = []
            page.on("request", lambda req: requests.append((req.url, req.method, req.post_data)))

            page.goto(LIVE_AUTHORING, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_function("window.__learnitPagesReady === true", timeout=120000)
            self.assertTrue(page.locator("#sample-complexes").is_visible())
            self.assertTrue(page.locator("#sample-signaux").is_visible())

            page.locator("#sample-complexes").click()
            page.wait_for_function("!document.querySelector('#export').disabled", timeout=60000)

            with page.expect_download(timeout=60000) as download:
                page.locator("#export").click()
            self.assertEqual(Path(download.value.path()).read_bytes(), source)

            preview_notice = page.locator(".notice").inner_text()
            for forbidden in ("prouve la recommandation", "prouve la mémoire", "prouve le transfert", "prouve la maîtrise"):
                self.assertNotIn(forbidden, preview_notice.lower())
            self.assertIn("aperçu auteur uniquement", preview_notice.lower())

            original = json.loads(page.evaluate("localStorage.getItem('learnit.authoring.m3.v1')"))
            old_lineage = original["package"]["packageLineageId"]
            old_revision = original["package"]["packageRevisionId"]

            new_title = "Nombres complexes — QA-WP-020 live"
            title = page.locator("#package-fields input").first
            title.fill(new_title)
            title.evaluate("(node) => node.dispatchEvent(new Event('change', {bubbles:true}))")
            page.wait_for_function("!document.querySelector('#export').disabled", timeout=60000)

            browser_draft = json.loads(page.evaluate("localStorage.getItem('learnit.authoring.m3.v1')"))
            self.assertEqual(browser_draft["package"]["title"], new_title)
            self.assertEqual(browser_draft["package"]["packageLineageId"], old_lineage)
            self.assertNotEqual(browser_draft["package"]["packageRevisionId"], old_revision)

            expected, _ = export_draft(browser_draft)
            with page.expect_download(timeout=60000) as edited:
                page.locator("#export").click()
            self.assertEqual(Path(edited.value.path()).read_bytes(), expected)

            tampered = json.loads(json.dumps(browser_draft))
            tampered["package"]["packageRevisionId"] = old_revision
            page.evaluate(
                "(value) => localStorage.setItem('learnit.authoring.m3.v1', JSON.stringify(value))",
                tampered,
            )
            page.reload(wait_until="domcontentloaded", timeout=120000)
            page.wait_for_function("window.__learnitPagesReady === true", timeout=120000)
            page.wait_for_function("document.querySelector('#export').disabled === true", timeout=60000)
            self.assertIn("bloquante", page.locator("#validation-badge").inner_text().lower())
            self.assertIn("STALE_PACKAGE_REVISION", page.locator("#diagnostic-list").inner_text())

            page.locator("#refresh-preview").click()
            page.wait_for_function(
                "document.querySelector('#preview-content').innerText.includes('fresh package revision')",
                timeout=60000,
            )
            self.assertIsNotNone(page.evaluate("localStorage.getItem('learnit.authoring.m3.v1')"))

            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#discard").click()
            self.assertIsNone(page.evaluate("localStorage.getItem('learnit.authoring.m3.v1')"))

            origin = LIVE_ROOT.rstrip("/")
            external = [(u, m, body) for u, m, body in requests if not u.startswith(origin)]
            self.assertTrue(external, "expected pinned Pyodide network reads")
            for url, method, body in external:
                self.assertTrue(url.startswith(PYODIDE_BASE), url)
                self.assertEqual(method, "GET", url)
                self.assertFalse(body, url)

            browser.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
