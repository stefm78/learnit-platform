#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "browser_product_flow_report.json"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        OUT.write_text(json.dumps({"schema": "learnit.rc623.product_accessibility_resilience.v1", "ok": False, "error": str(exc)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    rows = []
    errors = []

    def add(code: str, ok: bool, detail: str = ""):
        rows.append({"code": code, "ok": bool(ok), "detail": detail})

    kit = {
        "kind": "learnit-course-package",
        "schema_version": "learnit.import.v1.1",
        "packageId": "rc505-smoke-package",
        "source": "automated browser product smoke",
        "assets": [],
        "generation_report": {"source_coverage": "smoke", "activity_count": 4, "validation_status": "test"},
        "courses": [
            {
                "schemaVersion": "learnit-content-v2",
                "courseId": "rc505-smoke-course",
                "title": "RC505 Smoke Course",
                "sequence": "Automated checks",
                "objectives": ["validate import surface"],
                "activities": [
                    {"id": "s1", "type": "qcm", "objective": "Choose.", "question": "2 + 2 ?", "choices": ["4", "5"], "answer": 0, "why": "2 + 2 = 4.", "remediation": "Recalculate.", "difficulty": "easy", "learning_phase": "activation"},
                    {"id": "s2", "type": "fill", "objective": "Complete.", "question": "Complete.", "parts": ["A = ", 0], "tokens": ["1", "2"], "answer": ["1"], "sentence": "A = 1", "why": "Expected token.", "remediation": "Use 1.", "difficulty": "medium", "learning_phase": "application"},
                    {"id": "s3", "type": "matching", "objective": "Match.", "question": "Match.", "pairs": [["A", "1"], ["B", "2"]], "why": "Pairs.", "remediation": "Start with A.", "difficulty": "medium", "learning_phase": "consolidation"},
                    {"id": "s4", "type": "order", "objective": "Order.", "question": "Order.", "tokens": ["First", "Second"], "answer": ["First", "Second"], "why": "Sequence.", "remediation": "Start with First.", "difficulty": "advanced", "learning_phase": "validation"},
                ],
            }
        ],
    }
    kit_text = json.dumps(kit, ensure_ascii=False)
    chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=chromium) if chromium else playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1024, "height": 768})
            page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
            page.on("console", lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type == "error" else None)
            page.set_content((ROOT / "dist/learnit.html").read_text(encoding="utf-8"), wait_until="domcontentloaded")
            page.wait_for_timeout(450)

            for name in ["qcmModule", "flashcardModule", "fillModule", "matchingModule", "orderModule", "importFileSelector"]:
                value = page.evaluate(f"window.__LEARNIT_TEST__.{name}()")
                add(f"module-{name}", bool(value.get("available")), json.dumps(value, ensure_ascii=False))

            add("file-selector-visible", page.locator('input[type="file"]').count() == 1 and "json" in (page.locator('input[type="file"]').get_attribute("accept") or "").lower(), page.locator('input[type="file"]').get_attribute("accept") or "")
            course_qa = page.evaluate("window.__LEARNIT_TEST__.courseQa()")
            add("course-qa", bool(course_qa.get("ok")) and course_qa.get("total", 0) >= 3, json.dumps(course_qa, ensure_ascii=False)[:1200])
            surface = page.evaluate("window.__LEARNIT_TEST__.surfaceReport()")
            add("surface-report", bool(surface.get("ok")) and all(key in surface for key in ["learn", "library", "bilan"]), json.dumps(surface, ensure_ascii=False)[:1200])
            interaction = page.evaluate("window.__LEARNIT_TEST__.interactionRegressionAudit()")
            add("interaction-regression-audit", bool(interaction.get("ok")), interaction.get("summary", ""))
            density = page.evaluate("window.__LEARNIT_TEST__.surfaceDensityAudit()")
            add("surface-density-audit", bool(density.get("ok")), density.get("summary", ""))

            progress = page.evaluate("window.__LEARNIT_TEST__.progressAudit()")
            progress_rows = progress.get("rows", [])
            course_ids = [row.get("courseId") for row in progress_rows]
            add("progress-by-course", len(progress_rows) >= 3 and len(course_ids) == len(set(course_ids)), json.dumps(course_ids, ensure_ascii=False))
            persistence = page.evaluate("window.__LEARNIT_TEST__.libraryStatePersistenceReport()")
            add("library-state-persistence", bool(persistence.get("installed")) and bool(persistence.get("storesCourse")) and bool(persistence.get("storesChapter")), json.dumps(persistence, ensure_ascii=False))
            accessibility = page.evaluate("window.__LEARNIT_TEST__.accessibilityReport()")
            add("accessibility-runtime-contract", bool(accessibility.get("installed")) and accessibility.get("activePanels") == 1 and accessibility.get("inactivePanelsInert") == 3 and accessibility.get("hiddenFocusable") == 0 and accessibility.get("keyboardRoutes") and accessibility.get("keyboardActivities") and accessibility.get("focusRestoration"), json.dumps(accessibility, ensure_ascii=False))

            migration = page.evaluate("""() => {
              const r=window.__LEARNIT_TEST__.runtime;
              const legacy={activeCourseId:r.contentStore.activeCourseId,session:{status:'active',currentIndex:'broken',queue:['a1'],answers:null},sessionByCourseId:null,lastBilanByCourseId:[],activityProgressByCourseId:{bad:'broken'}};
              const migrated=r.appState.migrate(legacy);
              const reset=r.appState.migrate('not-an-object');
              return {version:migrated.stateSchemaVersion,status:migrated.session.status,index:migrated.session.currentIndex,answersType:typeof migrated.session.answers,badProgress:migrated.activityProgressByCourseId.bad,resetVersion:reset.stateSchemaVersion,resetSession:reset.session.status};
            }""")
            add("versioned-state-migration", migration.get("version") == 4 and migration.get("index") == 0 and migration.get("answersType") == "object" and migration.get("badProgress") is None and migration.get("resetVersion") == 4 and migration.get("resetSession") == "idle", json.dumps(migration, ensure_ascii=False))

            checkpoint = page.evaluate("""() => {const r=window.__LEARNIT_TEST__.runtime;r.session.start();r.answer.reset();window.__LEARNIT_TEST__.checkpoint('browser-product-flow');return window.__LEARNIT_TEST__.resilienceReport();}""")
            add("interruption-checkpoint", checkpoint.get("stateSchemaVersion") == 4 and checkpoint.get("checkpoint", {}).get("reason") == "browser-product-flow" and checkpoint.get("checkpoint", {}).get("sessionStatus") == "active", json.dumps(checkpoint, ensure_ascii=False))

            preview = page.evaluate("text => window.__LEARNIT_TEST__.importPreview(text)", kit_text)
            contract = page.evaluate("text => window.__LEARNIT_TEST__.contractDiagnostics(text)", kit_text)
            pedagogy = page.evaluate("text => window.__LEARNIT_TEST__.pedagogicalQuality(text)", kit_text)
            add("import-preview-valid", bool(preview.get("ok")) and preview.get("count") == 1 and preview.get("rows", [{}])[0].get("activityCount") == 4, json.dumps(preview, ensure_ascii=False))
            add("import-contract-no-blocker", bool(contract.get("ok")) and contract.get("blockers") == 0, json.dumps(contract, ensure_ascii=False)[:1200])
            add("pedagogical-diagnostic-available", isinstance(pedagogy.get("score"), (int, float)) and pedagogy.get("score", 0) > 0, json.dumps(pedagogy, ensure_ascii=False)[:1200])

            route_smoke = page.evaluate("window.__LEARNIT_TEST__.surfaceRouteSmoke()")
            add("all-routes-runtime", len(route_smoke) == 4 and all(item.get("ok") for item in route_smoke), json.dumps(route_smoke, ensure_ascii=False))
            page.locator('nav.nav button[data-nav="bilan"]').click()
            page.wait_for_timeout(350)
            main = page.locator("main[data-route-carousel]")
            bilan_heading = page.locator('.route-panel[data-route="bilan"] h1').first.text_content()
            add("bilan-route-visible", main.get_attribute("data-active-route") == "bilan" and bool(bilan_heading), bilan_heading or "")
            add("no-browser-errors", not errors, " | ".join(errors[-10:]))
        finally:
            browser.close()

    ok = all(row["ok"] for row in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "learnit.rc623.product_accessibility_resilience.v1", "ok": ok, "checks": rows, "errors": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "passed": sum(row["ok"] for row in rows), "total": len(rows), "report": str(OUT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
