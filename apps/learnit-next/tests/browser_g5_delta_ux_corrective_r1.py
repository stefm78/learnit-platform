#!/usr/bin/env python3
"""Browser qualification oracle for JOB_28_G5_DELTA_UX_FINDINGS_CORRECTIVE_R1."""
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
EVIDENCE = Path(os.environ.get("JOB28_EVIDENCE_DIR", "/tmp/atlas-wp070-g5-delta-ux-evidence"))
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

def rect(locator) -> dict[str, float]:
    box = locator.bounding_box()
    assert box is not None
    return {k: float(box[k]) for k in ("x", "y", "width", "height")}

def stable(before: dict[str, float], after: dict[str, float], *, fields=("x", "y", "width", "height")) -> None:
    for field in fields:
        assert abs(before[field] - after[field]) <= 1.0, (field, before, after)

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

def open_import(page) -> None:
    menu = page.get_by_role("button", name="Ouvrir la navigation")
    menu.click()
    page.get_by_role("button", name="Importer un cours").click()
    page.locator(".library-file-picker").wait_for()

def open_library(page) -> None:
    menu = page.get_by_role("button", name="Ouvrir la navigation")
    menu.click()
    page.get_by_role("button", name="Tous les cours").click()
    page.get_by_role("heading", name="Vos cours").wait_for()

def import_kit(page) -> dict[str, Any]:
    page.locator("#kit-file").set_input_files({
        "name": KIT.name,
        "mimeType": "application/json",
        "buffer": KIT.read_bytes(),
    })
    page.get_by_role("button", name="Ajouter à la bibliothèque").click()
    page.locator(".course-card[data-course-install-id]").first.wait_for()
    rows = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
    assert len(rows) == 1
    return rows[0]

def clone_second_course(page) -> None:
    page.evaluate(
        """async () => {
          const report=await window.__LEARNIT_NEXT_TEST__.storageReport();
          await new Promise((resolve,reject)=>{
            const req=indexedDB.open(report.indexedDbName);
            req.onerror=()=>reject(req.error);
            req.onsuccess=()=>{
              const db=req.result;
              const names=['courses'];
              if(db.objectStoreNames.contains('libraryMetadata')) names.push('libraryMetadata');
              const tx=db.transaction(names,'readwrite');
              const courses=tx.objectStore('courses');
              const get=courses.getAll();
              get.onerror=()=>reject(get.error);
              get.onsuccess=()=>{
                const source=get.result[0];
                const clone=structuredClone(source);
                clone.courseInstallId=source.courseInstallId+'-second';
                clone.packageRevisionId='synthetic-layout-second';
                clone.displayLabel='Deuxième cours';
                clone.installedAt='2099-01-01T00:00:00Z';
                courses.put(clone);
                if(names.includes('libraryMetadata')){
                  tx.objectStore('libraryMetadata').put({
                    courseInstallId: clone.courseInstallId,
                    displayLabel: 'Deuxième cours',
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
    canonical = json.loads(KIT.read_text(encoding="utf-8"))["courses"][0]["title"]

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

        # Accepted hamburger behavior remains intact.
        menu = page.get_by_role("button", name="Ouvrir la navigation")
        assert menu.inner_text().strip() == ""
        assert menu.locator(".nav-menu-bar").count() == 3
        mb = menu.bounding_box()
        assert mb and mb["width"] >= 44 and mb["height"] >= 44
        menu.focus()
        menu.press("Enter")
        page.get_by_role("dialog").wait_for()
        page.keyboard.press("Escape")
        assert page.evaluate("() => document.activeElement === document.querySelector('.nav-menu-trigger')") is True

        open_import(page)
        import_kit(page)
        clone_second_course(page)
        page.reload()
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        open_library(page)
        cards = page.locator(".learner-course-card")
        assert cards.count() == 2
        card = cards.first
        next_card = cards.nth(1)
        title = card.locator(".course-title-slot")
        start = card.get_by_role("button", name="Commencer")
        objective = card.locator(".course-objectives-details > summary")
        assert title.count() == 1 and start.count() == 1 and objective.count() == 1

        # Accepted multi-term AND search remains behaviorally intact.
        search = page.locator(".library-search-input")
        search.fill("nombres complexes")
        assert page.locator(".course-card:not([hidden])").count() >= 1
        search.fill("complexes absent")
        assert page.locator(".course-card:not([hidden])").count() == 0
        search.fill("")
        assert page.locator(".course-card:not([hidden])").count() == 2

        # Direct edit control: accessible icon-only target, no one-action menu.
        edit = card.get_by_role("button", name=f"Renommer le cours {canonical}")
        assert edit.count() == 1
        eb = edit.bounding_box()
        assert eb and eb["width"] >= 44 and eb["height"] >= 44
        assert card.locator(".course-settings-details").count() == 0
        assert card.locator(".course-settings-menu").count() == 0
        assert edit.locator("[aria-hidden='true']").count() == 1

        before_engine = engine_snapshot(page)
        before = {
            "card": rect(card),
            "title": rect(title),
            "start": rect(start),
            "objective": rect(objective),
            "next": rect(next_card),
        }
        page.screenshot(path=str(EVIDENCE / "01-before-rename-overlay.png"), full_page=True)

        edit.click()
        overlay = card.locator("[data-course-rename-overlay='true']")
        overlay.wait_for()
        input_box = overlay.locator("input")
        assert page.evaluate("() => document.activeElement?.matches('[data-course-rename-overlay] input')") is True
        assert input_box.input_value() == canonical
        selection = input_box.evaluate("el => [el.selectionStart, el.selectionEnd, el.value.length]")
        assert selection == [0, len(canonical), len(canonical)]

        during = {
            "card": rect(card),
            "title": rect(title),
            "start": rect(start),
            "objective": rect(objective),
            "next": rect(next_card),
        }
        stable(before["card"], during["card"], fields=("height",))
        stable(before["title"], during["title"])
        stable(before["start"], during["start"])
        stable(before["objective"], during["objective"])
        stable(before["next"], during["next"])
        assert card.get_by_role("heading", name=canonical).count() == 1
        no_overflow(page)
        page.screenshot(path=str(EVIDENCE / "02-rename-overlay-open-no-reflow.png"), full_page=True)

        # Escape cancels and restores focus to the same direct edit button.
        input_box.fill("Nom temporaire")
        page.keyboard.press("Escape")
        assert overlay.count() == 0
        assert page.evaluate("() => document.activeElement?.classList.contains('course-rename-button')") is True
        assert card.get_by_role("heading", name=canonical).count() == 1
        assert engine_snapshot(page) == before_engine

        # Keyboard activation + Enter save; only library alias metadata may change.
        edit.press("Enter")
        overlay = card.locator("[data-course-rename-overlay='true']")
        overlay.wait_for()
        input_box = overlay.locator("input")
        alias = "Nombres complexes — édition locale"
        input_box.fill(alias)
        input_box.press("Enter")
        page.get_by_role("heading", name=alias).wait_for()
        updated_edit = page.get_by_role("button", name=f"Renommer le cours {alias}")
        assert updated_edit.count() == 1
        assert page.evaluate("() => document.activeElement?.classList.contains('course-rename-button')") is True
        assert engine_snapshot(page) == before_engine
        rows = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
        first = next(row for row in rows if row["courseInstallId"] != rows[1]["courseInstallId"] or row.get("canonicalTitle") == canonical)
        assert any(row["title"] == alias and row["canonicalTitle"] == canonical for row in rows)
        no_overflow(page)
        page.screenshot(path=str(EVIDENCE / "03-rename-saved.png"), full_page=True)

        # Persistence after reload; canonical title remains unchanged.
        page.reload()
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        open_library(page)
        page.get_by_role("heading", name=alias).wait_for()
        rows = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
        assert any(row["title"] == alias and row["canonicalTitle"] == canonical for row in rows)
        no_overflow(page)

        assert not errors, errors
        assert not external, external
        browser.close()

    print("DIRECT_RENAME_A11Y=PASS")
    print("RENAME_OVERLAY_NO_LAYOUT_SHIFT_390x844=PASS")
    print("RENAME_ESCAPE_FOCUS_RESTORE=PASS")
    print("RENAME_ENTER_SAVE_PERSISTENCE=PASS")
    print("MULTI_COURSE_LAYOUT=PASS")
    print("SEARCH_HAMBURGER_REGRESSION=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
