#!/usr/bin/env python3
from __future__ import annotations

import functools
import hashlib
import http.server
import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile
import textwrap
import threading
import unittest


APP = pathlib.Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
BASE = "c8e6e2a01a9a517f0aa7bdbfc2e01a600d2f30ba"
GENERATOR_PATH = APP / "dev/controlled_time_navigator.py"
INJECTION_PATH = APP / "dev/controlled_time_inject.js"
WORK_PACKAGE_PATH = ROOT / "work-packages/DEV-WP-032.json"


def load_generator():
    spec = importlib.util.spec_from_file_location("controlled_time_navigator", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load controlled-time generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NAV = load_generator()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


class ControlledTimeNavigatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="learnit-controlled-time-test-")
        cls.directory = pathlib.Path(cls.temporary.name)
        canonical_path = cls.directory / "canonical.html"
        canonical = NAV.run_canonical_build(canonical_path)
        cls.canonical_identity = NAV.artifact_identity(canonical)
        injection = NAV.injection_source()
        cls.candidate = NAV.render_candidate(canonical, injection)
        cls.candidate_path = cls.directory / "controlled-time.html"
        cls.candidate_path.write_bytes(cls.candidate)
        (cls.directory / "blank.html").write_text(
            "<!doctype html><meta charset=utf-8><title>storage probe</title>\n",
            encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def run_node(self, body: str) -> str:
        completed = subprocess.run(
            ["node", "-e", textwrap.dedent(body), str(APP)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return completed.stdout

    def test_scope_and_canonical_product_are_immutable(self):
        package = json.loads(WORK_PACKAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(package["id"], "DEV-WP-032")
        self.assertEqual(package["authority"]["issue"], 231)
        self.assertEqual(package["baseline"]["baseCommit"], BASE)
        self.assertEqual(
            self.canonical_identity,
            {
                "bytes": package["baseline"]["canonicalArtifactBytes"],
                "sha256": package["baseline"]["canonicalArtifactSha256"],
            },
        )
        changed = set(subprocess.check_output(
            ["git", "diff", "--name-only", BASE],
            cwd=ROOT,
            text=True,
        ).splitlines())
        allowed = set(package["scope"]["allowedPaths"])
        self.assertFalse(changed - allowed, sorted(changed - allowed))
        self.assertNotIn("work-packages/QA-WP-019.json", changed)
        protected = [
            "apps/learnit-next/src",
            "apps/learnit-next/source_manifest.json",
            "apps/learnit-next/build.py",
            ".github/workflows/learnit-next-pages.yml",
        ]
        completed = subprocess.run(
            ["git", "diff", "--exit-code", BASE, "--", *protected],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_candidate_is_distinct_deterministic_and_visibly_simulated(self):
        second = NAV.render_candidate(
            (self.directory / "canonical.html").read_bytes(),
            NAV.injection_source(),
        )
        self.assertEqual(self.candidate, second)
        self.assertNotEqual(hashlib.sha256(self.candidate).hexdigest(), NAV.CANONICAL_SHA256)
        decoded = self.candidate.decode("utf-8")
        self.assertEqual(decoded.count(NAV.INJECTION_MARKER), 1)
        for required in (
            "TEMPS SIMULÉ — DONNÉES DE TEST",
            "Retour au temps système",
            "dataset.controlledTimeDays",
            "learnit_dev_controlled_time_next_v1",
            "learnit_dev_controlled_time_atlas_m1_v2",
            "learnit.dev.controlled-time.next.v1.",
            "CONTROLLED_TIME_NON_CANONICAL_TIMESTAMP",
            "globalThis.__LEARNIT_ATLAS_CLOCK__.now()",
        ):
            self.assertIn(required, decoded)
        self.assertEqual(decoded.count("globalThis.__LEARNIT_ATLAS_CLOCK__.now()"), 2)
        injection = INJECTION_PATH.read_text(encoding="utf-8")
        for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource"):
            self.assertNotIn(forbidden, injection)

    def test_generator_refuses_protected_and_non_html_targets(self):
        with self.assertRaisesRegex(NAV.NavigatorError, "OUTPUT_TARGET_PROTECTED"):
            NAV.normalized_output(NAV.CANONICAL_ARTIFACT)
        with self.assertRaisesRegex(NAV.NavigatorError, "OUTPUT_MUST_BE_HTML"):
            NAV.normalized_output(self.directory / "candidate.bin")
        with self.assertRaisesRegex(NAV.NavigatorError, "REPOSITORY_OUTPUT_OUTSIDE_DIST"):
            NAV.normalized_output(APP / "controlled-time-overwrite.html")
        tampered = bytearray((self.directory / "canonical.html").read_bytes())
        tampered[-2] = (tampered[-2] + 1) % 255
        with self.assertRaisesRegex(NAV.NavigatorError, "CANONICAL_ARTIFACT_IDENTITY_MISMATCH"):
            NAV.render_candidate(bytes(tampered), NAV.injection_source())

    def test_clock_boundaries_and_transfer_cannot_unlock_from_time_alone(self):
        output = self.run_node(r"""
          const assert = require('assert');
          const root = process.argv[1];
          const C = require(root + '/src/core/atlas_clock.js');
          const M = require(root + '/src/core/atlas_memory.js');
          const T = require(root + '/src/core/atlas_transfer.js');
          const E = require(root + '/src/core/atlas_evidence.js');

          const origin = '2026-08-01T10:00:00.000Z';
          const clock = new C.ControlledAtlasClock(origin);
          assert.equal(clock.now(), origin);
          assert.throws(() => clock.set('2026-08-01'), /NON_CANONICAL_TIMESTAMP/);
          assert.throws(() => clock.advance(1.5), /INVALID_CLOCK_DELTA/);

          const objectiveRef = {
            courseRef:{packageLineageId:'pkg',courseLineageId:'course'},
            objectiveId:'objective',
          };
          const validation = (executionId, action, scoredAt) => ({
            executionId,
            action,
            executionClass:'validation',
            objectiveRef,
            outcome:'correct',
            assistance:'none',
            scoredAt,
          });
          const e0 = validation('e0','attempt-validation',origin);
          const e1 = validation('e1','maintain-recent-validation','2026-08-02T10:00:00.000Z');
          const e2 = validation('e2','maintain-recent-validation','2026-08-05T10:00:00.000Z');
          const e3 = validation('e3','maintain-recent-validation','2026-08-12T10:00:00.000Z');
          const chain = [e0,e1,e2,e3];

          for (const [history, before, at, days] of [
            [[e0], '2026-08-02T09:59:59.999Z', '2026-08-02T10:00:00.000Z', 1],
            [[e0,e1], '2026-08-05T09:59:59.999Z', '2026-08-05T10:00:00.000Z', 3],
            [[e0,e1,e2], '2026-08-12T09:59:59.999Z', '2026-08-12T10:00:00.000Z', 7],
            [chain, '2026-09-02T09:59:59.999Z', '2026-09-02T10:00:00.000Z', 21],
          ]) {
            const ids = new Set(history.map(item => item.executionId));
            const prior = M.status({now:before,executions:history,objectiveRef,admissibleExecutionIds:ids,evidenceModule:E});
            const boundary = M.status({now:at,executions:history,objectiveRef,admissibleExecutionIds:ids,evidenceModule:E});
            assert.equal(prior.intervalDays, days);
            assert.equal(prior.due, false);
            assert.equal(boundary.due, true);
          }

          clock.set('2040-01-01T00:00:00.000Z');
          const onlyInitial = T.status({
            learningEvents:[],
            scoredExecutions:[e0],
            objectiveRef,
            admissibleExecutionIds:new Set([e0.executionId]),
            evidenceModule:E,
          });
          assert.equal(onlyInitial.eligible, false);
          assert.equal(onlyInitial.reconfirmationCount, 0);
          const afterReconfirmation = T.status({
            learningEvents:[],
            scoredExecutions:[e0,e1],
            objectiveRef,
            admissibleExecutionIds:new Set([e0.executionId,e1.executionId]),
            evidenceModule:E,
          });
          assert.equal(afterReconfirmation.eligible, true);
          assert.equal(afterReconfirmation.reconfirmationCount, 1);
          console.log('CONTROLLED_TIME_BOUNDARIES_PASS');
        """)
        self.assertIn("CONTROLLED_TIME_BOUNDARIES_PASS", output)

    def test_browser_storage_banner_controls_and_reset(self):
        if os.environ.get("LEARNIT_CONTROLLED_TIME_BROWSER") != "1":
            self.assertTrue(self.candidate_path.is_file())
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            self.fail(f"browser evidence requested but Playwright is unavailable: {exc}")

        handler = functools.partial(QuietHandler, directory=str(self.directory))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_address[1]}"
        candidate_url = f"{origin}/{self.candidate_path.name}"
        blank_url = f"{origin}/blank.html"

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context()
                external = []

                def route_request(route):
                    if route.request.url.startswith(origin):
                        route.continue_()
                    else:
                        external.append(route.request.url)
                        route.abort()

                context.route("**/*", route_request)
                page = context.new_page()
                page.goto(blank_url)
                page.evaluate("""
                  async () => {
                    localStorage.setItem('learnit.next.v1.normal-proof','KEEP');
                    await new Promise((resolve,reject) => {
                      const request=indexedDB.open('learnit_next_v1',2);
                      request.onupgradeneeded=()=>{
                        if(!request.result.objectStoreNames.contains('normalProof')){
                          request.result.createObjectStore('normalProof');
                        }
                      };
                      request.onerror=()=>reject(request.error);
                      request.onsuccess=()=>{
                        const db=request.result;
                        const tx=db.transaction('normalProof','readwrite');
                        tx.objectStore('normalProof').put('KEEP','marker');
                        tx.oncomplete=()=>{db.close();resolve();};
                        tx.onerror=()=>reject(tx.error);
                      };
                    });
                  }
                """)

                page.goto(candidate_url)
                page.locator("#learnit-controlled-time-panel").wait_for()
                api = page.evaluate("window.__LEARNIT_CONTROLLED_TIME__")
                self.assertEqual(api["mode"], "system")
                self.assertEqual(
                    api["storage"]["indexedDbNames"],
                    [
                        "learnit_dev_controlled_time_next_v1",
                        "learnit_dev_controlled_time_atlas_m1_v2",
                    ],
                )

                exact = "2026-08-01T10:00:00.000Z"
                page.locator("[data-controlled-time-iso]").fill(exact)
                with page.expect_navigation():
                    page.locator("[data-controlled-time-set]").click()
                page.locator("#learnit-controlled-time-panel").wait_for()
                self.assertIn(
                    "TEMPS SIMULÉ — DONNÉES DE TEST",
                    page.locator("#learnit-controlled-time-panel").inner_text(),
                )
                self.assertEqual(page.evaluate("new Date().toISOString()"), exact)
                page.evaluate("localStorage.setItem('learnit.next.v1.sim-proof','SIMULATED')")

                with page.expect_navigation():
                    page.locator('[data-controlled-time-days="1"]').click()
                self.assertEqual(
                    page.evaluate("new Date().toISOString()"),
                    "2026-08-02T10:00:00.000Z",
                )
                with page.expect_navigation():
                    page.locator('[data-controlled-time-days="21"]').click()
                self.assertEqual(
                    page.evaluate("new Date().toISOString()"),
                    "2026-08-22T10:00:00.000Z",
                )

                with page.expect_navigation():
                    page.locator('[data-controlled-time-days="0"]').click()
                self.assertEqual(page.evaluate("new Date().toISOString()"), exact)
                self.assertIsNone(page.evaluate(
                    "localStorage.getItem('learnit.next.v1.sim-proof')",
                ))

                page.locator("[data-controlled-time-iso]").fill("2026-08-01")
                page.locator("[data-controlled-time-set]").click()
                self.assertEqual(
                    page.locator("[data-controlled-time-iso]").get_attribute("aria-invalid"),
                    "true",
                )

                before_system = page.evaluate("Date.now()")
                with page.expect_navigation():
                    page.locator("[data-controlled-time-system]").click()
                api = page.evaluate("window.__LEARNIT_CONTROLLED_TIME__")
                self.assertEqual(api["mode"], "system")
                self.assertNotEqual(page.evaluate("Date.now()"), before_system)

                page.goto(blank_url)
                self.assertEqual(
                    page.evaluate("localStorage.getItem('learnit.next.v1.normal-proof')"),
                    "KEEP",
                )
                self.assertEqual(page.evaluate("""
                  async () => await new Promise((resolve,reject) => {
                    const request=indexedDB.open('learnit_next_v1',2);
                    request.onerror=()=>reject(request.error);
                    request.onsuccess=()=>{
                      const db=request.result;
                      const tx=db.transaction('normalProof','readonly');
                      const get=tx.objectStore('normalProof').get('marker');
                      get.onsuccess=()=>{const value=get.result;db.close();resolve(value);};
                      get.onerror=()=>reject(get.error);
                    };
                  })
                """), "KEEP")
                self.assertEqual(external, [])
                context.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
