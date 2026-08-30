#!/usr/bin/env python3
"""Independent contradictory oracle for the DEV-WP-032 frozen head."""
from __future__ import annotations

import functools
import hashlib
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
PACKAGE_PATH = ROOT / "work-packages/QA-WP-019.json"
BUILD = APP / "build.py"
GENERATOR = APP / "dev/controlled_time_navigator.py"
INJECTION = APP / "dev/controlled_time_inject.js"

BASE = "c8e6e2a01a9a517f0aa7bdbfc2e01a600d2f30ba"
DEV_HEAD = "e3ee52addb4147e19b74f0a491493bc8eb224d08"
DEV_TREE = "b87699579685c6ec59813ad09b9ecf29a8bb827a"
CANONICAL_BYTES = 366_412
CANONICAL_SHA256 = "4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7"
CANDIDATE_BYTES = 382_079
CANDIDATE_SHA256 = "f9388f8f79ef771c4e54cc5ffbfe014709e4152f561bb21c2e5fd82c440ac88e"
ALLOWED = {
    "work-packages/QA-WP-019.json",
    "apps/learnit-next/tests/qa_controlled_time_navigator.py",
    ".github/workflows/atlas-controlled-time-navigator-qa.yml",
}
SOURCES_OPEN = "const __sources=Object.freeze("
SOURCES_CLOSE = ");\nconst __dependencies=Object.freeze("
SURFACE = "apps/learnit-next/src/integration/atlas/surface.js"
SESSION = "apps/learnit-next/src/integration/atlas/session.js"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(command: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )


def git(*args: str) -> str:
    completed = run(["git", *args])
    if completed.returncode:
        raise AssertionError(completed.stdout)
    return completed.stdout.strip()


def module_sources(artifact: bytes) -> dict[str, str]:
    text = artifact.decode("utf-8")
    if text.count(SOURCES_OPEN) != 1 or text.count(SOURCES_CLOSE) != 1:
        raise AssertionError("module source table is not unique")
    encoded = text.split(SOURCES_OPEN, 1)[1].split(SOURCES_CLOSE, 1)[0]
    value = json.loads(encoded)
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(source, str) for key, source in value.items()
    ):
        raise AssertionError("module source table is invalid")
    return value


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


class ControlledTimeContradictoryQa(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="learnit-qa-controlled-time-")
        cls.directory = Path(cls.temporary.name)
        cls.canonical_path = cls.directory / "canonical.html"
        cls.candidate_path = cls.directory / "candidate.html"
        cls.blank_path = cls.directory / "blank.html"
        cls.blank_path.write_text("<!doctype html><title>QA blank origin</title>\n", encoding="utf-8")

        built = run([sys.executable, "-B", str(BUILD), "--output", str(cls.canonical_path)])
        if built.returncode:
            raise AssertionError(built.stdout)
        cls.canonical = cls.canonical_path.read_bytes()

        generated = run([
            sys.executable,
            "-B",
            str(GENERATOR),
            "--output",
            str(cls.candidate_path),
        ])
        if generated.returncode:
            raise AssertionError(generated.stdout)
        cls.generator_result = json.loads(generated.stdout.splitlines()[-1])
        cls.candidate = cls.candidate_path.read_bytes()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_exact_dev_head_binding_and_read_only_product_scope(self) -> None:
        package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(package["id"], "QA-WP-019")
        self.assertEqual(package["authority"]["issue"], 234)
        self.assertEqual(package["baseline"]["devHead"], DEV_HEAD)
        self.assertEqual(package["execution"]["devHead"], DEV_HEAD)
        self.assertEqual(package["baseline"]["devTree"], DEV_TREE)
        self.assertEqual(set(package["scope"]["allowedPaths"]), ALLOWED)

        self.assertEqual(git("rev-parse", f"{DEV_HEAD}^{{tree}}"), DEV_TREE)
        self.assertEqual(git("merge-base", DEV_HEAD, "HEAD"), DEV_HEAD)
        changed = set(git("diff", "--name-only", DEV_HEAD, "--").splitlines())
        self.assertEqual(changed, ALLOWED)

        protected = [
            "apps/learnit-next/src",
            "apps/learnit-next/build.py",
            "apps/learnit-next/source_manifest.json",
            ".github/workflows/learnit-next-pages.yml",
            "authoring",
            "contracts",
            "governance",
        ]
        product_diff = run(["git", "diff", "--exit-code", BASE, DEV_HEAD, "--", *protected])
        self.assertEqual(product_diff.returncode, 0, product_diff.stdout)

    def test_canonical_and_candidate_identities_are_exact(self) -> None:
        self.assertEqual((len(self.canonical), digest(self.canonical)), (
            CANONICAL_BYTES,
            CANONICAL_SHA256,
        ))
        self.assertEqual((len(self.candidate), digest(self.candidate)), (
            CANDIDATE_BYTES,
            CANDIDATE_SHA256,
        ))
        self.assertEqual(self.generator_result["canonical"], {
            "bytes": CANONICAL_BYTES,
            "sha256": CANONICAL_SHA256,
        })
        self.assertEqual(self.generator_result["candidate"]["bytes"], CANDIDATE_BYTES)
        self.assertEqual(self.generator_result["candidate"]["sha256"], CANDIDATE_SHA256)
        self.assertFalse(self.generator_result["networkRequired"])
        self.assertFalse(self.generator_result["publishedToNormalPages"])
        self.assertTrue(self.generator_result["storage"]["isolated"])

    def test_candidate_changes_only_two_clock_seams_plus_visible_injection(self) -> None:
        canonical_sources = module_sources(self.canonical)
        candidate_sources = module_sources(self.candidate)
        self.assertEqual(set(canonical_sources), set(candidate_sources))
        changed_modules = {
            name for name in canonical_sources
            if canonical_sources[name] != candidate_sources[name]
        }
        self.assertEqual(changed_modules, {SURFACE, SESSION})

        seams = {
            SURFACE: (
                "const now = new Date().toISOString();",
                "const now = globalThis.__LEARNIT_ATLAS_CLOCK__.now();",
            ),
            SESSION: (
                "return new Date().toISOString();",
                "return globalThis.__LEARNIT_ATLAS_CLOCK__.now();",
            ),
        }
        for module, (ambient, controlled) in seams.items():
            self.assertEqual(canonical_sources[module].count(ambient), 1)
            self.assertEqual(canonical_sources[module].count(controlled), 0)
            self.assertEqual(candidate_sources[module].count(ambient), 0)
            self.assertEqual(candidate_sources[module].count(controlled), 1)

        decoded = self.candidate.decode("utf-8")
        self.assertEqual(decoded.count("LEARNIT_CONTROLLED_TIME_INJECT_V1"), 1)
        for required in (
            "TEMPS SIMULÉ — DONNÉES DE TEST",
            "Retour au temps système",
            "learnit_dev_controlled_time_next_v1",
            "learnit_dev_controlled_time_atlas_m1_v2",
            "learnit.dev.controlled-time.next.v1.",
        ):
            self.assertIn(required, decoded)
        injection = INJECTION.read_text(encoding="utf-8")
        for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource"):
            self.assertNotIn(forbidden, injection)

    def test_generator_refuses_canonical_non_html_and_repository_targets(self) -> None:
        cases = [
            (APP / "dist/learnit-next.html", "OUTPUT_TARGET_PROTECTED"),
            (APP / "qa-controlled-time.html", "REPOSITORY_OUTPUT_OUTSIDE_DIST"),
            (self.directory / "candidate.bin", "OUTPUT_MUST_BE_HTML"),
        ]
        for target, expected in cases:
            completed = run([
                sys.executable,
                "-B",
                str(GENERATOR),
                "--output",
                str(target),
            ])
            self.assertNotEqual(completed.returncode, 0, str(target))
            self.assertIn(expected, completed.stdout)

    def test_independent_boundary_policy_and_transfer_oracle(self) -> None:
        script = r"""
          const assert = require('assert');
          const root = process.argv[1];
          const Clock = require(root + '/apps/learnit-next/src/core/atlas_clock.js');
          const Memory = require(root + '/apps/learnit-next/src/core/atlas_memory.js');
          const Transfer = require(root + '/apps/learnit-next/src/core/atlas_transfer.js');
          const Evidence = require(root + '/apps/learnit-next/src/core/atlas_evidence.js');

          assert.equal(Memory.POLICY_VERSION, 'atlas.memory-policy.v1');
          assert.equal(Memory.DAY_MS, 86400000);
          assert.deepEqual([...Memory.INTERVAL_DAYS], [1, 3, 7, 21]);

          const start = '2026-08-01T10:00:00.000Z';
          const clock = new Clock.ControlledAtlasClock(start);
          assert.equal(clock.now(), start);
          assert.throws(() => clock.set('2026-08-01T10:00:00Z'), /NON_CANONICAL_TIMESTAMP/);
          assert.throws(() => clock.set('not-a-date'), /NON_CANONICAL_TIMESTAMP/);
          assert.throws(() => clock.advance(0.5), /INVALID_CLOCK_DELTA/);
          assert.throws(() => clock.advance('86400000'), /INVALID_CLOCK_DELTA/);

          const objectiveRef = {
            courseRef: {packageLineageId: 'pkg-qa', courseLineageId: 'course-qa'},
            objectiveId: 'objective-qa',
          };
          const validation = (executionId, action, scoredAt) => ({
            executionId,
            action,
            executionClass: 'validation',
            objectiveRef,
            outcome: 'correct',
            assistance: 'none',
            scoredAt,
          });
          const history = [
            validation('initial', 'attempt-validation', '2026-08-01T10:00:00.000Z'),
            validation('r1', 'maintain-recent-validation', '2026-08-02T10:00:00.000Z'),
            validation('r2', 'maintain-recent-validation', '2026-08-05T10:00:00.000Z'),
            validation('r3', 'maintain-recent-validation', '2026-08-12T10:00:00.000Z'),
          ];
          const boundaries = [
            {count: 1, days: 1, before: '2026-08-02T09:59:59.999Z', at: '2026-08-02T10:00:00.000Z'},
            {count: 2, days: 3, before: '2026-08-05T09:59:59.999Z', at: '2026-08-05T10:00:00.000Z'},
            {count: 3, days: 7, before: '2026-08-12T09:59:59.999Z', at: '2026-08-12T10:00:00.000Z'},
            {count: 4, days: 21, before: '2026-09-02T09:59:59.999Z', at: '2026-09-02T10:00:00.000Z'},
          ];
          for (const boundary of boundaries) {
            const executions = history.slice(0, boundary.count);
            const ids = new Set(executions.map(item => item.executionId));
            const before = Memory.status({
              now: boundary.before, executions, objectiveRef,
              admissibleExecutionIds: ids, evidenceModule: Evidence,
            });
            const at = Memory.status({
              now: boundary.at, executions, objectiveRef,
              admissibleExecutionIds: ids, evidenceModule: Evidence,
            });
            assert.equal(before.intervalDays, boundary.days);
            assert.equal(before.due, false);
            assert.equal(at.intervalDays, boundary.days);
            assert.equal(at.due, true);
          }

          clock.set('2099-12-31T23:59:59.999Z');
          const initialOnly = Transfer.status({
            learningEvents: [], scoredExecutions: [history[0]], objectiveRef,
            admissibleExecutionIds: new Set(['initial']), evidenceModule: Evidence,
          });
          assert.equal(initialOnly.eligible, false);
          assert.equal(initialOnly.reconfirmationCount, 0);

          const reconfirmed = Transfer.status({
            learningEvents: [], scoredExecutions: history.slice(0, 2), objectiveRef,
            admissibleExecutionIds: new Set(['initial', 'r1']), evidenceModule: Evidence,
          });
          assert.equal(reconfirmed.eligible, true);
          assert.equal(reconfirmed.reconfirmationCount, 1);
          console.log('QA_CONTROLLED_TIME_BOUNDARIES_AND_TRANSFER_PASS');
        """
        completed = run(["node", "-e", script, str(ROOT)])
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("QA_CONTROLLED_TIME_BOUNDARIES_AND_TRANSFER_PASS", completed.stdout)

    def test_browser_isolation_banner_controls_and_selective_reset(self) -> None:
        if os.environ.get("LEARNIT_CONTROLLED_TIME_QA_BROWSER") != "1":
            self.assertTrue(self.candidate_path.is_file())
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            self.fail(f"browser QA requested but Playwright is unavailable: {exc}")

        handler = functools.partial(QuietHandler, directory=str(self.directory))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_address[1]}"
        candidate_url = f"{origin}/{self.candidate_path.name}"
        blank_url = f"{origin}/{self.blank_path.name}"

        seed_normal_storage = r"""
          async () => {
            localStorage.setItem('learnit.next.v1.qa-normal-proof', 'KEEP');
            const open = (name, version, stores, proofStore) => new Promise((resolve, reject) => {
              const request = indexedDB.open(name, version);
              request.onupgradeneeded = () => {
                const db = request.result;
                for (const store of stores) {
                  if (!db.objectStoreNames.contains(store)) db.createObjectStore(store, {keyPath: 'key'});
                }
              };
              request.onerror = () => reject(request.error);
              request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction(proofStore, 'readwrite');
                tx.objectStore(proofStore).put({key: 'qa-normal-proof', value: 'KEEP'});
                tx.oncomplete = () => { db.close(); resolve(); };
                tx.onerror = () => reject(tx.error);
              };
            });
            await open(
              'learnit_next_v1', 2,
              ['packages', 'courses', 'progress', 'meta', 'objectiveProgress'], 'meta',
            );
            await open(
              'learnit_atlas_m1_v2', 1,
              ['learningEvents', 'scoredExecutions', 'resumeStates', 'atlasMeta'], 'atlasMeta',
            );
          }
        """
        put_synthetic_dev_databases = r"""
          async () => {
            const put = (name, version, store) => new Promise((resolve, reject) => {
              const request = indexedDB.open(name, version);
              request.onupgradeneeded = () => {
                const db = request.result;
                if (name.endsWith('next_v1')) {
                  for (const entry of [
                    ['packages', 'packageInstallId'],
                    ['courses', 'courseInstallId'],
                    ['progress', ['courseInstallId', 'activityRevisionId']],
                    ['meta', 'key'],
                    ['objectiveProgress', ['courseInstallId', 'objectiveId']],
                  ]) {
                    if (!db.objectStoreNames.contains(entry[0])) {
                      db.createObjectStore(entry[0], {keyPath: entry[1]});
                    }
                  }
                } else {
                  for (const entry of [
                    ['learningEvents', 'eventId'],
                    ['scoredExecutions', 'executionId'],
                    ['resumeStates', 'sessionRef.sessionId'],
                    ['atlasMeta', 'key'],
                  ]) {
                    if (!db.objectStoreNames.contains(entry[0])) {
                      db.createObjectStore(entry[0], {keyPath: entry[1]});
                    }
                  }
                }
              };
              request.onerror = () => reject(request.error);
              request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction(store, 'readwrite');
                tx.objectStore(store).put({key: 'qa-synthetic', value: 'SIMULATED'});
                tx.oncomplete = () => { db.close(); resolve(); };
                tx.onerror = () => reject(tx.error);
              };
            });
            await put('learnit_dev_controlled_time_next_v1', 2, 'meta');
            await put('learnit_dev_controlled_time_atlas_m1_v2', 1, 'atlasMeta');
          }
        """
        read_proofs = r"""
          async ({namespace, proofKey}) => {
            const dev = namespace === 'dev';
            const nextName = dev ? 'learnit_dev_controlled_time_next_v1' : 'learnit_next_v1';
            const atlasName = dev ? 'learnit_dev_controlled_time_atlas_m1_v2' : 'learnit_atlas_m1_v2';
            const localKey = dev
              ? 'learnit.dev.controlled-time.next.v1.' + proofKey
              : 'learnit.next.v1.' + proofKey;
            const get = (name, version, store, stores) => new Promise((resolve, reject) => {
              const request = indexedDB.open(name, version);
              request.onupgradeneeded = () => {
                const db = request.result;
                for (const entry of stores) {
                  if (!db.objectStoreNames.contains(entry[0])) {
                    db.createObjectStore(entry[0], {keyPath: entry[1]});
                  }
                }
              };
              request.onerror = () => reject(request.error);
              request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction(store, 'readonly');
                const query = tx.objectStore(store).get(proofKey);
                query.onsuccess = () => { const value = query.result || null; db.close(); resolve(value); };
                query.onerror = () => reject(query.error);
              };
            });
            return {
              local: localStorage.getItem(localKey),
              next: await get(nextName, 2, 'meta', [
                ['packages', 'packageInstallId'],
                ['courses', 'courseInstallId'],
                ['progress', ['courseInstallId', 'activityRevisionId']],
                ['meta', 'key'],
                ['objectiveProgress', ['courseInstallId', 'objectiveId']],
              ]),
              atlas: await get(atlasName, 1, 'atlasMeta', [
                ['learningEvents', 'eventId'],
                ['scoredExecutions', 'executionId'],
                ['resumeStates', 'sessionRef.sessionId'],
                ['atlasMeta', 'key'],
              ]),
            };
          }
        """

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context()
                external: list[str] = []

                def route_request(route: object) -> None:
                    request = route.request
                    if request.url.startswith(origin):
                        route.continue_()
                    else:
                        external.append(request.url)
                        route.abort()

                context.route("**/*", route_request)
                storage_page = context.new_page()
                storage_page.goto(blank_url)
                storage_page.evaluate(seed_normal_storage)

                page = context.new_page()
                page.goto(candidate_url)
                panel = page.locator("#learnit-controlled-time-panel")
                panel.wait_for(state="visible")
                api = page.evaluate("window.__LEARNIT_CONTROLLED_TIME__")
                self.assertEqual(api["mode"], "system")
                self.assertEqual(api["quickDays"], [0, 1, 3, 7, 21])
                self.assertEqual(api["storage"], {
                    "indexedDbNames": [
                        "learnit_dev_controlled_time_next_v1",
                        "learnit_dev_controlled_time_atlas_m1_v2",
                    ],
                    "localStoragePrefix": "learnit.dev.controlled-time.next.v1.",
                })

                origin_iso = "2026-08-01T10:00:00.000Z"
                page.locator("[data-controlled-time-iso]").fill(origin_iso)
                with page.expect_navigation():
                    page.locator("[data-controlled-time-set]").click()
                panel = page.locator("#learnit-controlled-time-panel")
                panel.wait_for(state="visible")
                self.assertTrue(panel.is_visible())
                self.assertIn("TEMPS SIMULÉ — DONNÉES DE TEST", panel.inner_text())
                self.assertEqual(page.evaluate("new Date().toISOString()"), origin_iso)
                self.assertEqual(
                    page.evaluate("window.__LEARNIT_ATLAS_CLOCK__.now()"),
                    origin_iso,
                )
                page.evaluate(
                    "localStorage.setItem('learnit.next.v1.qa-synthetic','SIMULATED')",
                )
                storage_page.evaluate(put_synthetic_dev_databases)
                simulated = storage_page.evaluate(read_proofs, {
                    "namespace": "dev",
                    "proofKey": "qa-synthetic",
                })
                self.assertEqual(simulated, {
                    "local": "SIMULATED",
                    "next": {"key": "qa-synthetic", "value": "SIMULATED"},
                    "atlas": {"key": "qa-synthetic", "value": "SIMULATED"},
                })

                start = datetime(2026, 8, 1, 10, tzinfo=timezone.utc)
                for days in (1, 3, 7, 21):
                    with page.expect_navigation():
                        page.locator(f'[data-controlled-time-days="{days}"]').click()
                    expected = (start + timedelta(days=days)).isoformat(timespec="milliseconds")
                    expected = expected.replace("+00:00", "Z")
                    self.assertEqual(page.evaluate("new Date().toISOString()"), expected)
                    panel = page.locator("#learnit-controlled-time-panel")
                    panel.wait_for(state="visible")
                    self.assertTrue(panel.is_visible())
                    self.assertIn("TEMPS SIMULÉ — DONNÉES DE TEST", panel.inner_text())

                with page.expect_navigation():
                    page.locator('[data-controlled-time-days="0"]').click()
                self.assertEqual(page.evaluate("new Date().toISOString()"), origin_iso)
                cleared = storage_page.evaluate(read_proofs, {
                    "namespace": "dev",
                    "proofKey": "qa-synthetic",
                })
                self.assertEqual(cleared, {"local": None, "next": None, "atlas": None})

                page.locator("[data-controlled-time-iso]").fill("2026-08-01T10:00:00Z")
                page.locator("[data-controlled-time-set]").click()
                self.assertEqual(
                    page.locator("[data-controlled-time-iso]").get_attribute("aria-invalid"),
                    "true",
                )
                self.assertEqual(page.evaluate("new Date().toISOString()"), origin_iso)

                page.evaluate(
                    "localStorage.setItem('learnit.next.v1.qa-synthetic','SIMULATED')",
                )
                storage_page.evaluate(put_synthetic_dev_databases)
                with page.expect_navigation():
                    page.locator("[data-controlled-time-system]").click()
                api = page.evaluate("window.__LEARNIT_CONTROLLED_TIME__")
                self.assertEqual(api["mode"], "system")
                self.assertIsNone(api["nowIso"])
                self.assertLess(abs(page.evaluate("Date.now()") - int(datetime.now().timestamp() * 1000)), 60_000)
                cleared = storage_page.evaluate(read_proofs, {
                    "namespace": "dev",
                    "proofKey": "qa-synthetic",
                })
                self.assertEqual(cleared, {"local": None, "next": None, "atlas": None})

                normal = storage_page.evaluate(read_proofs, {
                    "namespace": "normal",
                    "proofKey": "qa-normal-proof",
                })
                self.assertEqual(normal["local"], "KEEP")
                self.assertEqual(normal["next"], {"key": "qa-normal-proof", "value": "KEEP"})
                self.assertEqual(normal["atlas"], {"key": "qa-normal-proof", "value": "KEEP"})
                self.assertEqual(external, [])
                context.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
