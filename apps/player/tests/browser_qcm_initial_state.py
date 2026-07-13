#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "browser_qcm_initial_state_report.json"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        OUT.write_text(json.dumps({"schema": "learnit.rc511.qcm_initial_state_smoke.v1", "ok": False, "error": str(exc)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    rows: list[dict] = []
    errors: list[str] = []

    def add(profile: str, code: str, ok: bool, detail: str = "") -> None:
        rows.append({"profile": profile, "code": code, "ok": bool(ok), "detail": detail})

    chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    html = (ROOT / "dist" / "learnit.html").read_text(encoding="utf-8")

    def snapshot(page):
        return page.evaluate(
            """() => {
              const runtime=window.__LEARNIT_TEST__.runtime;
              const activity=runtime.session.currentActivity();
              const choices=[...document.querySelectorAll('[data-qcm-choice]')].map(el=>({
                index:Number(el.dataset.qcmChoice),
                text:el.textContent.trim(),
                cls:el.className,
                state:el.dataset.qcmState,
                checked:el.getAttribute('aria-checked'),
                pressed:el.getAttribute('aria-pressed'),
                role:el.getAttribute('role')
              }));
              return {
                activity:{id:activity&&activity.id,type:activity&&activity.type,answer:activity&&activity.answer},
                pending:runtime.answer.pending,
                feedback:runtime.answer.feedback,
                phase:(document.querySelector('[data-activity-type="qcm"]')||{}).dataset?.qcmPhase||null,
                selected:choices.filter(x=>x.cls.includes('selected')||x.checked==='true'||x.pressed==='true').length,
                correct:choices.filter(x=>x.cls.includes('correct')).length,
                wrong:choices.filter(x=>x.cls.includes('wrong')).length,
                choices,
                validateDisabled:!!document.querySelector('[data-action="validate"]')?.disabled,
                groupRole:document.querySelector('.activity-answer-panel')?.getAttribute('role')||null
              };
            }"""
        )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=chromium) if chromium else playwright.chromium.launch(headless=True)
        try:
            for profile, mobile in (("desktop", False), ("android-touch", True)):
                context = browser.new_context(
                    viewport={"width": 390 if mobile else 1024, "height": 844 if mobile else 768},
                    is_mobile=mobile,
                    has_touch=mobile,
                )
                page = context.new_page()
                page.on("pageerror", lambda exc, profile=profile: errors.append(f"{profile}:pageerror:{exc}"))
                page.on("console", lambda msg, profile=profile: errors.append(f"{profile}:console:{msg.type}:{msg.text}") if msg.type == "error" else None)
                page.set_content(html, wait_until="domcontentloaded")
                page.wait_for_timeout(450)
                page.evaluate("""() => { const r=window.__LEARNIT_TEST__.runtime; const ids=r.contentStore.content.activities.filter(a=>a.type==='qcm').slice(0,2).map(a=>a.id); r.session.startTargetedReview(ids,{summary:'qcm state isolation'}); r.answer.reset(); r.go('session'); }""")
                page.wait_for_timeout(220)

                first = snapshot(page)
                add(profile, "first-qcm-is-idle", first["activity"]["type"] == "qcm" and first["pending"] is None and first["phase"] == "idle", json.dumps(first, ensure_ascii=False))
                add(profile, "no-default-selection", first["selected"] == 0 and first["correct"] == 0 and first["wrong"] == 0, json.dumps(first, ensure_ascii=False))
                add(profile, "idle-cannot-validate", first["validateDisabled"] is True, str(first["validateDisabled"]))
                add(profile, "radio-semantics", first["groupRole"] == "radiogroup" and all(row["role"] == "radio" and row["checked"] == "false" for row in first["choices"]), json.dumps(first["choices"], ensure_ascii=False))

                answer = first["activity"]["answer"]
                page.locator(f'[data-qcm-choice="{answer}"]').tap() if mobile else page.locator(f'[data-qcm-choice="{answer}"]').click()
                page.wait_for_timeout(100)
                chosen = snapshot(page)
                add(profile, "selection-explicit-only", chosen["selected"] == 1 and chosen["phase"] == "selected" and chosen["correct"] == 0 and chosen["wrong"] == 0 and chosen["validateDisabled"] is False, json.dumps(chosen, ensure_ascii=False))

                page.locator('[data-action="validate"]').tap() if mobile else page.locator('[data-action="validate"]').click()
                page.wait_for_timeout(100)
                locked = snapshot(page)
                add(profile, "answer-revealed-after-validation-only", locked["phase"] == "feedback" and locked["correct"] == 1 and locked["selected"] == 1, json.dumps(locked, ensure_ascii=False))

                page.locator('[data-action="continue"]').tap() if mobile else page.locator('[data-action="continue"]').click()
                page.wait_for_timeout(150)
                second = snapshot(page)
                add(profile, "consecutive-qcm-resets-idle", second["activity"]["type"] == "qcm" and second["activity"]["id"] != first["activity"]["id"] and second["pending"] is None and second["selected"] == 0 and second["correct"] == 0 and second["wrong"] == 0 and second["phase"] == "idle", json.dumps(second, ensure_ascii=False))

                wrong_index = next(row["index"] for row in second["choices"] if row["index"] != second["activity"]["answer"])
                page.locator(f'[data-qcm-choice="{wrong_index}"]').tap() if mobile else page.locator(f'[data-qcm-choice="{wrong_index}"]').click()
                page.locator('[data-action="validate"]').tap() if mobile else page.locator('[data-action="validate"]').click()
                page.wait_for_timeout(80)
                page.locator('[data-action="retry"]').tap() if mobile else page.locator('[data-action="retry"]').click()
                page.wait_for_timeout(120)
                retried = snapshot(page)
                add(profile, "retry-resets-idle", retried["pending"] is None and retried["selected"] == 0 and retried["correct"] == 0 and retried["wrong"] == 0 and retried["phase"] == "idle", json.dumps(retried, ensure_ascii=False))
                context.close()
        finally:
            browser.close()

    add("global", "no-browser-errors", not errors, " | ".join(errors[-10:]))
    ok = all(row["ok"] for row in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "learnit.rc511.qcm_initial_state_smoke.v1", "ok": ok, "checks": rows, "errors": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "passed": sum(row["ok"] for row in rows), "total": len(rows), "report": str(OUT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
