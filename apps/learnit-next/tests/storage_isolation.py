#!/usr/bin/env python3
"""Prove RC718 storage is untouched and successor writes are transactional."""
from __future__ import annotations

import json
import os
import re
import threading
import unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "contracts" / "fixtures"
VALID = FIXTURES / "v2-valid-minimal.json"
LEGACY = FIXTURES / "v2-invalid-legacy.json"
ARTIFACT = ROOT / "apps" / "learnit-next" / "dist" / "learnit-next.html"
PROTECTED_KEYS = (
    "learnit_clean_state_v2",
    "learnit_imported_courses_v1",
    "learnit_import_history_v1",
    "learnit_import_last_applied_v1",
    "learnit_import_transaction_v1",
    "learnit_active_course_v1",
    "learnit_content_patches_v2",
    "learnit_library_revision_v1",
    "learnit_library_persistence_meta_v1",
)
LEGACY_DB = "learnit_durable_library_v1"
LEGACY_STORE = "snapshots"
NEXT_PREFIX = "learnit.next.v1."
NEXT_DB = "learnit_next_v1"
UNRELATED_KEY = "qa.unrelated.sentinel"
STRICT = os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION") == "1"
DOMAIN_REJECTION = re.compile(
    r"contract|contrat|legacy|schema|invalid|invalide|validation|reject|rejet|version", re.I
)


def require_or_skip(condition: bool, message: str) -> None:
    if condition:
        return
    if STRICT:
        raise RuntimeError(message)
    raise unittest.SkipTest(message)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def negative(result: Any) -> bool:
    if result is False:
        return True
    if not isinstance(result, dict):
        return False
    return any(
        result.get(key) is False
        for key in ("ok", "valid", "accepted", "imported", "success")
    ) or str(result.get("status", "")).lower() in {"error", "invalid", "rejected"}


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return


@contextmanager
def serve(path: Path):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Quiet, directory=str(path.parent))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        origin = f"http://127.0.0.1:{server.server_port}"
        yield origin, f"{origin}/{path.name}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


PREPARE = r"""async config => {
  for (const [index, key] of config.keys.entries()) {
    localStorage.setItem(key, JSON.stringify({
      marker:'RC718', index, key, unicode:'é Ω', bytes:[0,1,255]
    }));
  }
  localStorage.setItem(config.other, 'unrelated::é');
  await new Promise((resolve, reject) => {
    const request = indexedDB.deleteDatabase(config.db);
    request.onsuccess = resolve;
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error('legacy database deletion blocked during setup'));
  });
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open(config.db, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(
      config.store, {keyPath:'id'}
    );
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  await new Promise((resolve, reject) => {
    const tx = db.transaction(config.store, 'readwrite');
    const store = tx.objectStore(config.store);
    store.put({id:'library', revision:718, payload:{course:'legacy', answer:'é'}});
    store.put({id:'qa-shadow', payload:[true,false,null]});
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error('legacy setup aborted'));
  });
  db.close();
}"""

SNAPSHOT = r"""async config => {
  const encode = value => Array.from(new TextEncoder().encode(value));
  const local = {};
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index);
    const value = localStorage.getItem(key);
    local[key] = {value, utf8:encode(value)};
  }
  async function snap(name) {
    const db = await new Promise((resolve, reject) => {
      const request = indexedDB.open(name);
      request.onupgradeneeded = event => event.target.transaction.abort();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    }).catch(() => null);
    if (!db) return null;
    const stores = {};
    for (const storeName of Array.from(db.objectStoreNames).sort()) {
      stores[storeName] = await new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, 'readonly');
        const store = tx.objectStore(storeName);
        const keys = store.getAllKeys();
        const records = store.getAll();
        tx.oncomplete = () => resolve({
          keyPath:store.keyPath,
          autoIncrement:store.autoIncrement,
          indexes:Array.from(store.indexNames).sort(),
          keys:keys.result,
          records:records.result
        });
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error || new Error('snapshot aborted'));
      });
    }
    const result = {version:db.version, stores};
    db.close();
    return result;
  }
  let names = null;
  if (typeof indexedDB.databases === 'function') {
    names = (await indexedDB.databases())
      .map(item => item.name).filter(Boolean).sort();
  }
  return {
    local,
    names,
    legacy:await snap(config.legacy),
    next:names && names.includes(config.next) ? await snap(config.next) : null
  };
}"""

INSTALL_FAILURE = r"""(() => {
  let count = 0;
  const methods = [];
  for (const method of ['add', 'put']) {
    const original = IDBObjectStore.prototype[method];
    if (typeof original !== 'function') continue;
    IDBObjectStore.prototype[method] = function(...args) {
      if (this.transaction && this.transaction.db &&
          this.transaction.db.name === 'learnit_next_v1') {
        count += 1;
        methods.push(method);
        if (count === 3) {
          throw new DOMException(
            'QA forced after partial successor writes',
            'QuotaExceededError'
          );
        }
      }
      return original.apply(this, args);
    };
  }
  window.__qaFailureInstalled = true;
  window.__qaWriteEvidence = () => ({count, methods:[...methods]});
})();"""


class StorageIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path(os.environ.get("LEARNIT_NEXT_ARTIFACT", ARTIFACT))
        require_or_skip(path.exists(), f"WAITING_FOR_INTEGRATION: {path}")
        require_or_skip(sync_playwright is not None, "DEPENDENCY: Playwright")
        cls.valid = load(VALID)
        cls.legacy = load(LEGACY)
        cls.server = serve(path)
        cls.origin, cls.url = cls.server.__enter__()
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except Exception as error:
            cls.playwright.stop()
            cls.server.__exit__(None, None, None)
            require_or_skip(False, f"DEPENDENCY: Chromium: {error}")

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "browser"):
            cls.browser.close()
        if hasattr(cls, "playwright"):
            cls.playwright.stop()
        if hasattr(cls, "server"):
            cls.server.__exit__(None, None, None)

    def setUp(self) -> None:
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.goto(self.origin + "/__qa_prepare__")
        self.page.evaluate(
            PREPARE,
            {
                "keys": list(PROTECTED_KEYS),
                "other": UNRELATED_KEY,
                "db": LEGACY_DB,
                "store": LEGACY_STORE,
            },
        )
        self.before = self.snapshot()

    def tearDown(self) -> None:
        self.context.close()

    def boot(self) -> None:
        self.page.goto(self.url, wait_until="domcontentloaded")
        self.page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

    def invoke(self, operation: str, *args: Any) -> dict[str, Any]:
        return self.page.evaluate(
            """async ({operation,args}) => {
              const api = window.__LEARNIT_NEXT_TEST__;
              if (!api || typeof api[operation] !== 'function') {
                return {kind:'harness', message:`missing ${operation}`};
              }
              try {
                return {kind:'return', value:await api[operation](...args)};
              } catch (error) {
                return {
                  kind:'throw',
                  name:String(error && error.name || ''),
                  message:String(error && error.message || error || '')
                };
              }
            }""",
            {"operation": operation, "args": list(args)},
        )

    def call(self, operation: str, *args: Any) -> Any:
        result = self.invoke(operation, *args)
        self.assertEqual("return", result.get("kind"), result)
        return result.get("value")

    def snapshot(self) -> Any:
        return self.page.evaluate(
            SNAPSHOT, {"legacy": LEGACY_DB, "next": NEXT_DB}
        )

    def assert_rc718_untouched(self, after: Any) -> None:
        self.assertEqual(self.before["legacy"], after["legacy"])
        for key in PROTECTED_KEYS + (UNRELATED_KEY,):
            self.assertEqual(self.before["local"][key], after["local"].get(key))
        changed = {
            key
            for key in set(self.before["local"]) | set(after["local"])
            if self.before["local"].get(key) != after["local"].get(key)
        }
        self.assertEqual(
            [], sorted(key for key in changed if not key.startswith(NEXT_PREFIX))
        )
        if self.before["names"] is not None and after["names"] is not None:
            delta = set(self.before["names"]) ^ set(after["names"])
            self.assertEqual(
                [], sorted(name for name in delta if name != NEXT_DB)
            )

    def assert_domain_rejection(self, result: dict[str, Any]) -> None:
        self.assertNotEqual("harness", result.get("kind"), result)
        if result.get("kind") == "return":
            self.assertTrue(negative(result.get("value")), result)
            return
        self.assertEqual("throw", result.get("kind"), result)
        evidence = f"{result.get('name', '')}: {result.get('message', '')}"
        self.assertRegex(evidence, DOMAIN_REJECTION)

    def test_boot_preserves_rc718_byte_for_byte(self) -> None:
        self.boot()
        self.assert_rc718_untouched(self.snapshot())

    def test_import_and_session_preserve_rc718_record_for_record(self) -> None:
        self.boot()
        imported = self.invoke("importPackage", self.valid)
        self.assertEqual("return", imported.get("kind"), imported)
        self.assertFalse(negative(imported.get("value")), imported)
        course = self.call("listCourses")[0]
        self.call("startCourse", course["courseInstallId"])
        qcm = self.valid["courses"][0]["activities"][0]
        self.call("answer", qcm["activityRevisionId"], qcm["correctChoiceId"])
        self.assert_rc718_untouched(self.snapshot())

    def test_legacy_rejection_is_atomic(self) -> None:
        self.boot()
        before = self.snapshot()
        result = self.invoke("importPackage", self.legacy)
        self.assert_domain_rejection(result)
        after = self.snapshot()
        self.assert_rc718_untouched(after)
        self.assertEqual(before["next"], after["next"])
        self.assertEqual([], self.call("listCourses"))

    def test_forced_successor_write_failure_rolls_back_all_successor_stores(
        self,
    ) -> None:
        self.page.add_init_script(INSTALL_FAILURE)
        self.boot()
        self.assertTrue(self.page.evaluate("() => window.__qaFailureInstalled"))
        before = self.snapshot()

        result = self.invoke("importPackage", self.valid)
        evidence = self.page.evaluate("() => window.__qaWriteEvidence()")
        self.assertGreaterEqual(evidence["count"], 3, evidence)
        self.assertTrue(
            set(evidence["methods"]).issubset({"add", "put"}), evidence
        )
        self.assertNotEqual("harness", result.get("kind"), result)
        if result.get("kind") == "return":
            self.assertTrue(negative(result.get("value")), result)
        else:
            self.assertEqual("throw", result.get("kind"), result)
            failure = f"{result.get('name', '')}: {result.get('message', '')}"
            self.assertRegex(
                failure,
                re.compile(r"QuotaExceededError|QA forced|partial successor", re.I),
            )

        after = self.snapshot()
        self.assertEqual(
            before["next"],
            after["next"],
            "packages/courses/progress/meta must roll back record-for-record",
        )
        self.assertEqual([], self.call("listCourses"))
        self.assert_rc718_untouched(after)

    def test_reset_changes_only_successor_namespaces(self) -> None:
        self.boot()
        self.call("importPackage", self.valid)
        before = self.snapshot()
        self.call("resetNextData")
        after = self.snapshot()
        self.assert_rc718_untouched(after)
        self.assertEqual([], self.call("listCourses"))
        self.assertNotEqual(before["next"], after["next"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
