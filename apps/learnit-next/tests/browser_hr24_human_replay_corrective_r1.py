#!/usr/bin/env python3
"""Browser oracle for JOB_26_HR24_HUMAN_REPLAY_CORRECTIVE_R1."""
from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps" / "learnit-next"
ARTIFACT = APP / "dist" / "learnit-next.html"
KIT = ROOT / "showcase" / "student-v0.1" / "nombres-complexes" / "nombres_complexes_student_v01_v5.json"
EVIDENCE = Path(os.environ.get("JOB26_EVIDENCE_DIR", "/tmp/atlas-wp068-hr24-corrective-evidence"))
EVIDENCE.mkdir(parents=True, exist_ok=True)

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return

@contextmanager
def serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ARTIFACT.parent)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/{ARTIFACT.name}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

def no_overflow(page) -> None:
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def shot(page, scene: str) -> None:
    page.screenshot(path=str(EVIDENCE / f"mobile-390x844-{scene}.png"), full_page=True)

def engine_snapshot(page) -> dict[str, Any]:
    return page.evaluate(
        """async () => {
          const report=await window.__LEARNIT_NEXT_TEST__.storageReport();
          return new Promise((resolve,reject)=>{
            const req=indexedDB.open(report.indexedDbName);
            req.onerror=()=>reject(req.error);
            req.onsuccess=()=>{
              const db=req.result;
              const stores=['courses','progress','objectiveProgress'].filter(x=>db.objectStoreNames.contains(x));
              const tx=db.transaction(stores,'readonly');
              const result={};
              let pending=stores.length;
              if(!pending){db.close();resolve(result);return;}
              for(const name of stores){
                const get=tx.objectStore(name).getAll();
                get.onerror=()=>reject(get.error);
                get.onsuccess=()=>{result[name]=get.result;pending-=1;};
              }
              tx.oncomplete=()=>{db.close();resolve(result);};
              tx.onerror=()=>reject(tx.error);
              tx.onabort=()=>reject(tx.error);
            };
          });
        }"""
    )

def library_metadata(page) -> list[dict[str, Any]]:
    return page.evaluate(
        """async () => {
          const report=await window.__LEARNIT_NEXT_TEST__.storageReport();
          return new Promise((resolve,reject)=>{
            const req=indexedDB.open(report.indexedDbName);
            req.onerror=()=>reject(req.error);
            req.onsuccess=()=>{
              const db=req.result;
              const tx=db.transaction('libraryMetadata','readonly');
              const get=tx.objectStore('libraryMetadata').getAll();
              get.onerror=()=>reject(get.error);
              get.onsuccess=()=>{const rows=get.result;tx.oncomplete=()=>{db.close();resolve(rows);};};
              tx.onerror=()=>reject(tx.error);
            };
          });
        }"""
    )

def open_library(page) -> None:
    trigger = page.get_by_role("button", name="Ouvrir la navigation")
    trigger.click()
    page.get_by_role("button", name="Tous les cours").click()
    page.get_by_role("heading", name="Vos cours").wait_for()

def import_kit(page) -> dict[str, Any]:
    page.locator("#kit-file").set_input_files({
        "name": KIT.name,
        "mimeType": "application/json",
        "buffer": KIT.read_bytes(),
    })
    page.get_by_role("button", name="Ajouter à la bibliothèque").click()
    card = page.locator(".course-card[data-course-install-id]").first
    card.wait_for()
    rows = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
    assert len(rows) == 1
    return rows[0]

def clone_to_fifty(page) -> None:
    page.evaluate(
        """async () => {
          const report=await window.__LEARNIT_NEXT_TEST__.storageReport();
          await new Promise((resolve,reject)=>{
            const req=indexedDB.open(report.indexedDbName);
            req.onerror=()=>reject(req.error);
            req.onsuccess=()=>{
              const db=req.result;
              const tx=db.transaction(['courses','libraryMetadata'],'readwrite');
              const courses=tx.objectStore('courses');
              const metadata=tx.objectStore('libraryMetadata');
              const get=courses.getAll();
              get.onerror=()=>reject(get.error);
              get.onsuccess=()=>{
                const source=get.result[0];
                if(!source) throw new Error('missing source course');
                for(let i=2;i<=50;i++){
                  const clone=structuredClone(source);
                  clone.courseInstallId=source.courseInstallId+'-scale-'+String(i).padStart(2,'0');
                  clone.packageRevisionId='synthetic-no-atlas-'+i;
                  clone.displayLabel=source.title;
                  clone.installedAt='2099-01-01T00:00:'+String(i).padStart(2,'0')+'Z';
                  courses.put(clone);
                  metadata.put({
                    courseInstallId: clone.courseInstallId,
                    displayLabel: 'Cours représentatif '+String(i).padStart(2,'0'),
                  });
                }
              };
              tx.oncomplete=()=>{db.close();resolve();};
              tx.onerror=()=>reject(tx.error);
              tx.onabort=()=>reject(tx.error);
            };
          });
        }"""
    )

def main() -> int:
    assert ARTIFACT.is_file(), ARTIFACT
    kit = json.loads(KIT.read_text(encoding="utf-8"))
    canonical = kit["courses"][0]["title"]

    with serve() as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page = context.new_page()
        errors: list[str] = []
        external: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: external.append(r.url) if r.url.startswith(("http://", "https://")) and "127.0.0.1" not in r.url else None)
        page.goto(url, wait_until="load")
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

        # Drawer: modal behavior, Escape, backdrop, focus restoration, inert background.
        trigger = page.get_by_role("button", name="Ouvrir la navigation")
        assert trigger.get_attribute("aria-expanded") == "false"
        assert trigger.get_attribute("aria-controls") == "learnit-navigation-drawer"
        assert trigger.get_attribute("aria-label") == "Ouvrir la navigation"
        assert trigger.inner_text().strip() == ""
        assert trigger.locator(".nav-menu-bar").count() == 3
        trigger_box = trigger.bounding_box()
        assert trigger_box and trigger_box["width"] >= 44 and trigger_box["height"] >= 44
        trigger.focus()
        trigger.click()
        drawer = page.get_by_role("dialog")
        drawer.wait_for()
        assert trigger.get_attribute("aria-expanded") == "true"
        assert page.locator(".app-main").get_attribute("inert") is not None
        assert page.evaluate("() => document.activeElement?.textContent?.trim()") == "Fermer"
        assert page.get_by_role("button", name="Aujourd’hui").is_disabled()
        page.keyboard.press("Escape")
        assert drawer.is_hidden()
        assert trigger.get_attribute("aria-expanded") == "false"
        assert page.evaluate("() => document.activeElement === document.querySelector('.nav-menu-trigger')") is True
        trigger.click()
        page.locator(".nav-drawer-backdrop").click(position={"x": 380, "y": 400})
        assert drawer.is_hidden()
        trigger.click()
        page.get_by_role("button", name="Fermer la navigation").click()
        assert drawer.is_hidden()
        assert page.evaluate("() => document.activeElement === document.querySelector('.nav-menu-trigger')") is True
        trigger.focus()
        page.keyboard.press("Enter")
        assert drawer.is_visible()
        page.keyboard.press("Escape")
        assert drawer.is_hidden()
        no_overflow(page)
        shot(page, "01-drawer-closed-library-empty")

        # Import route is real and immediately useful.
        trigger.click()
        page.get_by_role("button", name="Importer un cours").click()
        page.locator(".library-file-picker").wait_for()
        import_kit(page)
        # Exact V5 showcase contains rich V8 activity families beyond the current
        # Atlas qcm/fill planner contract. Today remains a truthful real route but
        # disabled; the canonical V5/V8 library/session path stays authoritative.
        assert page.locator('.nav-drawer-link[data-shell-view="today"]').is_disabled()
        card = page.locator(".course-card[data-course-install-id]").first
        card.wait_for()
        assert card.get_by_role("heading", name=canonical).count() == 1
        no_overflow(page)

        # Rename cancellation is inline and leaves engine-owned stores byte-for-byte equivalent as JSON.
        before = engine_snapshot(page)
        metadata_before = library_metadata(page)
        options = card.locator(".course-settings-details > summary")
        options.click()
        card.get_by_role("button", name="Renommer").click()
        inline = card.locator("[data-course-inline-rename='true']")
        inline.wait_for()
        assert inline.locator("input").count() == 1
        assert card.locator(".course-row-actions [data-course-inline-rename='true']").count() == 0
        assert page.evaluate("() => document.activeElement?.matches('[data-course-inline-rename] input')") is True
        inline.locator("input").fill("Nom temporaire")
        page.keyboard.press("Escape")
        assert inline.count() == 0
        assert card.get_by_role("heading", name=canonical).count() == 1
        assert engine_snapshot(page) == before
        assert library_metadata(page) == metadata_before

        # Save via native Enter; alias changes only libraryMetadata and canonical title remains exact.
        options.click()
        card.get_by_role("button", name="Renommer").click()
        input_box = card.locator("[data-course-inline-rename] input")
        alias = "Nombres complexes — mon cours"
        input_box.fill(alias)
        input_box.press("Enter")
        page.get_by_role("heading", name=alias).wait_for()
        after = engine_snapshot(page)
        assert after == before
        metadata_after = library_metadata(page)
        assert metadata_after != metadata_before
        rows = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
        assert rows[0]["title"] == alias
        assert rows[0]["canonicalTitle"] == canonical
        assert page.locator(".course-label-form").count() == 0
        no_overflow(page)
        shot(page, "02-inline-rename-saved")

        # Drawer itself remains write-free after a course exists.
        stable = engine_snapshot(page)
        trigger.click()
        assert page.get_by_role("dialog").is_visible()
        page.keyboard.press("Tab")
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Escape")
        assert engine_snapshot(page) == stable

        # Reload persists alias; shell can return from Today to Library.
        page.reload()
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        page.wait_for_timeout(150)
        open_library(page)
        page.get_by_role("heading", name=alias).wait_for()
        rows = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
        assert rows[0]["title"] == alias
        assert rows[0]["canonicalTitle"] == canonical

        # 50-course synthetic harness, stable search, no pedagogical write from search.
        clone_to_fifty(page)
        page.reload()
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        page.wait_for_timeout(200)
        open_library(page)
        page.locator(".course-card").first.wait_for()
        assert page.locator(".course-card").count() == 50
        search = page.locator(".library-search-input")
        assert search.count() == 1
        search_before = engine_snapshot(page)
        original_order = page.locator(".course-card").evaluate_all("xs => xs.map(x => x.getAttribute('data-course-install-id'))")
        search.fill("représentatif 50")
        assert page.locator(".course-card").evaluate_all("xs => xs.filter(x => !x.hidden).length") == 1
        assert "Cours représentatif 50" in page.locator(".course-card:not([hidden])").inner_text()
        search.fill("50 représentatif")
        assert page.locator(".course-card").evaluate_all("xs => xs.filter(x => !x.hidden).length") == 1
        search.fill("  représentatif   50  ")
        assert page.locator(".course-card").evaluate_all("xs => xs.filter(x => !x.hidden).length") == 1
        search.fill("50 module")
        assert page.locator(".course-card").evaluate_all("xs => xs.filter(x => !x.hidden).length") == 1
        search.fill("module 50")
        assert page.locator(".course-card").evaluate_all("xs => xs.filter(x => !x.hidden).length") == 1
        search.fill("représentatif introuvable")
        assert page.locator(".course-card").evaluate_all("xs => xs.filter(x => !x.hidden).length") == 0
        search.fill("   ")
        assert page.locator(".course-card").evaluate_all("xs => xs.filter(x => !x.hidden).length") == 50
        search.fill("")
        assert page.locator(".course-card").evaluate_all("xs => xs.filter(x => !x.hidden).length") == 50
        restored_order = page.locator(".course-card").evaluate_all("xs => xs.map(x => x.getAttribute('data-course-install-id'))")
        assert restored_order == original_order
        assert engine_snapshot(page) == search_before
        search_ui_text = page.locator(".library-search").inner_text()
        assert "AND" not in search_ui_text and "Boolean" not in search_ui_text and "booléen" not in search_ui_text.lower()
        no_overflow(page)
        shot(page, "03-library-50-multi-term-and-search")

        # Long valid title remains stable at mobile width and persists.
        first = page.locator(".course-card").first
        first.locator(".course-settings-details > summary").click()
        first.get_by_role("button", name="Renommer").click()
        long_alias = "Cours " + ("très-long-" * 16) + "fin"
        assert len(long_alias) < 180
        first.locator("[data-course-inline-rename] input").fill(long_alias)
        first.locator("[data-course-inline-rename] input").press("Enter")
        page.get_by_role("heading", name=long_alias).wait_for()
        no_overflow(page)
        shot(page, "04-long-title-mobile-safe")

        assert not errors, errors
        assert not external, external
        browser.close()

    print("HAMBURGER_TRIGGER_BROWSER=PASS")
    print("RENAME_INLINE_BROWSER=PASS")
    print("LIBRARY_STORAGE_ISOLATION_BROWSER=PASS")
    print("LIBRARY_MULTI_TERM_AND_SEARCH_BROWSER=PASS")
    print("MOBILE_390x844_NO_HORIZONTAL_OVERFLOW=PASS")\n    print("ACCEPTED_HR24_REGRESSION_SMOKE=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
