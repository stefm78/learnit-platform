#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright
from support import ROOT

REPORT = ROOT / "reports" / "browser_contract_golden_kits_report.json"


def main() -> int:
    fixture = json.loads((ROOT / "authoring" / "contract-fixtures.json").read_text(encoding="utf-8"))
    positives = [case for case in fixture["cases"] if case["expected"] == "pass"]
    diagnostic_cases = fixture.get("diagnostic_cases", [])
    source_contracts = {
        "learnit-capabilities": json.loads((ROOT / "contract" / "learnit-capabilities.json").read_text(encoding="utf-8")),
        "learnit-import-schema": json.loads((ROOT / "contract" / "learnit-import.schema.json").read_text(encoding="utf-8")),
        "learnit-pedagogical-taxonomy": json.loads((ROOT / "contract" / "pedagogical-taxonomy.json").read_text(encoding="utf-8")),
    }
    rows = []
    console_errors = []
    with sync_playwright() as p:
        chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        browser = p.chromium.launch(headless=True, executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: console_errors.append(f"pageerror:{exc}"))
            page.set_content((ROOT / "dist" / "learnit.html").read_text(encoding="utf-8"), wait_until="domcontentloaded")
            page.wait_for_timeout(450)
            page.wait_for_function("() => !!window.__LEARNIT_TEST__ && !!window.__LEARNIT_TEST__.runtime")

            embedded = page.evaluate("""() => Object.fromEntries(['learnit-capabilities','learnit-import-schema','learnit-pedagogical-taxonomy'].map(id => [id, JSON.parse(document.getElementById(id).textContent)]))""")
            rows.append({"code": "embedded-contracts-exact", "ok": embedded == source_contracts})

            for case in diagnostic_cases:
                text = json.dumps(case["payload"], ensure_ascii=False)
                report = page.evaluate("text => window.__LEARNIT_TEST__.kitDiagnostics(text)", text)
                findings = report.get("items", []) or [*report.get("blockers", []), *report.get("warnings", []), *report.get("advice", [])]
                actual = {row.get("code"): row.get("severity") for row in findings}
                expected_codes = case.get("expected_codes", [])
                expected_severity = case.get("expected_severity")
                rows.append({"code": f"{case['id']}-runtime-diagnostic", "ok": all(actual.get(code) == expected_severity for code in expected_codes), "detail": actual})

            imported_titles = []
            for case in positives:
                text = json.dumps(case["payload"], ensure_ascii=False)
                result = page.evaluate("""text => {
                    const api = window.__LEARNIT_TEST__;
                    const preview = api.importPreview(text);
                    const contract = api.contractDiagnostics(text);
                    const pedagogy = api.pedagogicalQuality(text);
                    const applied = api.runtime.contentStore.applyImportDraft(text);
                    api.runtime.afterContentChange();
                    return {preview, contract, pedagogy, applied, courses: api.runtime.contentStore.courseList()};
                }""", text)
                expected_title = case["payload"]["courses"][0]["title"]
                imported_titles.append(expected_title)
                rows.append({"code": f"{case['id']}-preview-contract-apply", "ok": bool(result["preview"]["ok"] and result["contract"]["ok"] and result["applied"]["ok"] and any(row["title"] == expected_title for row in result["courses"]))})

            real_golden_paths = [
                ROOT / "data" / "golden-kits" / "golden_nombres_complexes.json",
                ROOT / "data" / "golden-kits" / "golden_signaux_electriques.json",
            ]
            for golden_path in real_golden_paths:
                payload = json.loads(golden_path.read_text(encoding="utf-8"))
                title = payload["courses"][0]["title"]
                text = json.dumps(payload, ensure_ascii=False)
                result = page.evaluate("""text => {
                    const api = window.__LEARNIT_TEST__;
                    const preview = api.importPreview(text);
                    const contract = api.contractDiagnostics(text);
                    const pedagogy = api.pedagogicalQuality(text);
                    const applied = api.runtime.contentStore.applyImportDraft(text);
                    api.runtime.afterContentChange();
                    const row = api.runtime.contentStore.courseList().find(item => item.title === JSON.parse(text).courses[0].title);
                    if(!row) return {preview, contract, pedagogy, applied, missing:true};
                    const course = api.runtime.contentStore.courseById(row.courseId);
                    const mediaActivity = course.activities.find(activity => Array.isArray(activity.media) && activity.media.length);
                    api.runtime.contentStore.setActiveCourse(row.courseId);
                    api.runtime.appState.alignWithContent();
                    api.runtime.answer.reset();
                    api.runtime.session.startTargetedReview([mediaActivity.id], {summary:'real golden media probe',focus:mediaActivity.objective,objectives:[],hints:[],typeCounts:{},metadataCoverage:1});
                    api.runtime.go('session');
                    api.runtime.render();
                    return {
                        preview, contract, pedagogy, applied,
                        activityCount: row.activityCount,
                        types: Object.keys(row.types).sort(),
                        renderedType: document.querySelector('[data-activity-type]')?.getAttribute('data-activity-type'),
                        mediaState: document.querySelector('[data-media-state]')?.getAttribute('data-media-state'),
                        svg: !!document.querySelector('.media-svg-wrap svg')
                    };
                }""", text)
                imported_titles.append(title)
                rows.append({
                    "code": f"{golden_path.stem}-real-course-import-render",
                    "ok": bool(
                        result.get("preview", {}).get("ok")
                        and result.get("contract", {}).get("ok")
                        and result.get("applied", {}).get("ok")
                        and result.get("activityCount") == len(payload["courses"][0]["activities"])
                        and result.get("types") == ["fill", "flashcard", "matching", "order", "qcm"]
                        and result.get("renderedType") == "qcm"
                        and result.get("mediaState") == "rendered-svg"
                        and result.get("svg") is True
                    ),
                    "detail": result,
                })

            persisted = page.evaluate("() => window.__LEARNIT_TEST__.runtime.contentStore.loadImportedCourses().map(course => course.title)")
            rows.append({"code": "golden-imports-persist-in-store", "ok": all(title in persisted for title in imported_titles), "detail": persisted})

            rich_case = next(case for case in positives if case.get('id') == 'positive-rich-media')
            rich_title = rich_case["payload"]["courses"][0]["title"]
            render = page.evaluate("""title => {
                const api = window.__LEARNIT_TEST__;
                const row = api.runtime.contentStore.courseList().find(item => item.title === title);
                if(!row) return {missing:true};
                api.runtime.contentStore.setActiveCourse(row.courseId);
                api.runtime.appState.alignWithContent();
                api.runtime.answer.reset();
                api.runtime.session.start();
                api.runtime.go('session');
                api.runtime.render();
                return {
                    activityType: document.querySelector('[data-activity-type]')?.getAttribute('data-activity-type'),
                    mediaState: document.querySelector('[data-media-state]')?.getAttribute('data-media-state'),
                    svg: !!document.querySelector('.media-svg-wrap svg')
                };
            }""", rich_title)
            rows.append({"code": "rich-golden-media-renders", "ok": render == {"activityType": "qcm", "mediaState": "rendered-svg", "svg": True}, "detail": render})
        finally:
            browser.close()

    rows.append({"code": "browser-console-clean", "ok": not console_errors, "detail": console_errors})
    ok = all(row["ok"] for row in rows)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"schema": "learnit.rc712.browser_contract_golden_kits.v1", "ok": ok, "checks": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "passed": sum(row["ok"] for row in rows), "total": len(rows), "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
