#!/usr/bin/env python3
"""Product tests for ATLAS-WP-010 static GitHub Pages packaging."""
from __future__ import annotations

import hashlib
import http.server
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
PRODUCT_HEAD = "a1b9259955ce748cd7e47531a470cd12b7dc0436"
PYODIDE_BASE = "https://cdn.jsdelivr.net/pyodide/v0.29.4/full/"
FROZEN_PRODUCT_PATHS = (
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


def run(*args: str) -> str:
    completed = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise AssertionError(completed.stderr or completed.stdout)
    return completed.stdout.strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PackagingStaticTests(unittest.TestCase):
    def test_frozen_m3_product_files_are_unchanged(self):
        changed = run("git", "diff", "--name-only", PRODUCT_HEAD, "--", *FROZEN_PRODUCT_PATHS)
        self.assertEqual(changed, "")

    def test_build_copies_exact_authorities_and_injects_bridge_before_ui(self):
        from authoring.studio.pages.build_pages import build
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "site"
            evidence = build(out)
            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertLess(index.index('pages-bootstrap.js'), index.index('studio.js'))
            self.assertIn("STATIC_BROWSER_PYTHON_AUTHORITY", json.loads((out / "pages-evidence.json").read_text())["mode"])
            for relative, record in evidence["authority"].items():
                self.assertEqual(record["sha256"], sha(ROOT / relative))
                self.assertEqual(record["sha256"], sha(out / "_authority" / relative))

    def test_bootstrap_has_fail_closed_network_and_no_semantic_validator(self):
        text = (ROOT / "authoring/studio/pages/pages-bootstrap.js").read_text(encoding="utf-8")
        self.assertIn("M3_PAGES_EXTERNAL_NETWORK_BLOCKED", text)
        self.assertIn("pyodide.loadPackage('jsonschema')", text)
        self.assertIn("from authoring.studio import core as _core", text)
        self.assertNotIn("function validatePackage", text)
        self.assertNotIn("fetch('http", text)


class BrowserEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise unittest.SkipTest(f"playwright unavailable: {exc}")
        cls.sync_playwright = staticmethod(sync_playwright)

    def test_pages_noop_and_edit_match_python_reference_and_network_boundary(self):
        from authoring.studio.core import apply_edit, create_draft, export_draft
        from authoring.studio.pages.build_pages import build

        kit_path = ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json"
        raw = kit_path.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            site = Path(td) / "site"
            build(site)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]

            handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(site), **kw)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with self.sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    context = browser.new_context(accept_downloads=True)
                    page = context.new_page()
                    requests = []
                    page.on("request", lambda request: requests.append(
                        (request.url, request.method, request.post_data)
                    ))
                    page.goto(f"http://127.0.0.1:{port}/", wait_until="domcontentloaded", timeout=120000)
                    page.wait_for_function("window.__learnitPagesReady === true", timeout=120000)

                    page.locator("#kit-file").set_input_files({
                        "name": kit_path.name,
                        "mimeType": "application/json",
                        "buffer": raw,
                    })
                    page.wait_for_function("!document.querySelector('#export').disabled", timeout=60000)

                    with page.expect_download(timeout=60000) as info:
                        page.locator("#export").click()
                    noop_bytes = Path(info.value.path()).read_bytes()
                    self.assertEqual(noop_bytes, raw)

                    new_title = "Nombres complexes — validation Pages"
                    title = page.locator("#package-fields input").first
                    title.fill(new_title)
                    title.evaluate("(node) => node.dispatchEvent(new Event('change', {bubbles:true}))")
                    page.wait_for_function("!document.querySelector('#export').disabled", timeout=60000)

                    original = create_draft(raw, kit_path.name)
                    reference = apply_edit(original, ["title"], new_title)
                    browser_draft = json.loads(
                        page.evaluate("localStorage.getItem('learnit.authoring.m3.v1')")
                    )
                    self.assertEqual(browser_draft["package"]["title"], reference["package"]["title"])
                    self.assertEqual(
                        browser_draft["package"]["packageLineageId"],
                        original["package"]["packageLineageId"],
                    )
                    self.assertNotEqual(
                        browser_draft["package"]["packageRevisionId"],
                        original["package"]["packageRevisionId"],
                    )
                    expected, _ = export_draft(browser_draft)

                    with page.expect_download(timeout=60000) as info2:
                        page.locator("#export").click()
                    browser_bytes = Path(info2.value.path()).read_bytes()
                    self.assertEqual(browser_bytes, expected)

                    keys = page.evaluate("Object.keys(localStorage)")
                    self.assertEqual(keys, ["learnit.authoring.m3.v1"])
                    page.reload(wait_until="domcontentloaded", timeout=120000)
                    page.wait_for_function("window.__learnitPagesReady === true", timeout=120000)
                    page.wait_for_function("!document.querySelector('#export').disabled", timeout=60000)

                    page.once("dialog", lambda dialog: dialog.accept())
                    page.locator("#discard").click()
                    self.assertEqual(page.evaluate("localStorage.getItem('learnit.authoring.m3.v1')"), None)

                    origin = f"http://127.0.0.1:{port}"
                    external = [(u, m, d) for u, m, d in requests if not u.startswith(origin)]
                    self.assertTrue(external, "Pyodide must have been loaded from its pinned distribution")
                    for url, method, post_data in external:
                        self.assertTrue(url.startswith(PYODIDE_BASE), url)
                        self.assertEqual(method, "GET", url)
                        self.assertFalse(post_data, url)
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
