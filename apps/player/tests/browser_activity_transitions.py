#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "browser_activity_transitions_report.json"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        OUT.write_text(json.dumps({"schema": "learnit.rc623.activity_keyboard_transition_stress.v1", "ok": False, "error": str(exc)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    rows: list[dict] = []
    errors: list[str] = []

    def add(code: str, ok: bool, detail: str = "") -> None:
        rows.append({"code": code, "ok": bool(ok), "detail": detail})

    chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    html = (ROOT / "dist" / "learnit.html").read_text(encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=chromium) if chromium else playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            page = context.new_page()
            page.on("pageerror", lambda exc: errors.append(f"pageerror:{exc}"))
            page.on("console", lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type == "error" else None)
            page.set_content(html, wait_until="domcontentloaded")
            page.wait_for_timeout(450)

            result = page.evaluate(
                """async () => {
                  const r=window.__LEARNIT_TEST__.runtime;
                  const wait=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
                  const kit={kind:'learnit-course-package',schema_version:'learnit.import.v1.1',packageId:'rc516-transition-stress',source:'runtime stress fixture',assets:[],generation_report:{activity_count:5,validation_status:'test'},courses:[{schemaVersion:'learnit-content-v2',contentVersion:'rc516-transition-course-v1',courseId:'rc516-transition-course',title:'RC516 Transition Stress',sequence:'Five activity states',objectives:['verify clean entry states'],activities:[
                    {id:'t-qcm',type:'qcm',objective:'Choose',question:'Choose B',choices:['A','B','C'],answer:1,why:'B',remediation:'Choose B'},
                    {id:'t-fill',type:'fill',objective:'Complete',question:'Complete',parts:['Value ',0],tokens:['A','B'],answer:['B'],sentence:'Value B',why:'B',remediation:'Use B'},
                    {id:'t-match',type:'matching',objective:'Match',question:'Match',pairs:[['A','1'],['B','2']],why:'Pairs',remediation:'Match pairs'},
                    {id:'t-order',type:'order',objective:'Order',question:'Order',tokens:['First','Second'],answer:['First','Second'],why:'Sequence',remediation:'Start first'},
                    {id:'t-flash',type:'flashcard',objective:'Recall',question:'Recall B',front:'Recall B',answer:'B',back:'B',why:'B',remediation:'Review B'}
                  ]}]};
                  const imported=r.contentStore.applyImportDraft(JSON.stringify(kit));
                  if(!imported.ok) throw new Error('stress fixture import failed: '+imported.error);
                  const importedId=imported.report&&imported.report.rows&&imported.report.rows[0]&&imported.report.rows[0].courseId;
                  r.contentStore.setActiveCourse(importedId); r.appState.alignWithContent(); r.answer.reset();
                  const runs=[];
                  for(let cycle=0; cycle<4; cycle++){
                    r.session.start(); r.answer.reset(); r.go('session'); await wait();
                    let guard=0; const entries=[];
                    while(r.session.session.status==='active' && guard++<100){
                      const a=r.session.currentActivity();
                      const entry={cycle,id:a.id,type:a.type,feedback:r.answer.feedback,pending:JSON.parse(JSON.stringify(r.answer.pending)),ok:true,reason:''};
                      if(r.answer.feedback!==null){entry.ok=false;entry.reason='stale-feedback';}
                      if(a.type==='qcm'){
                        const selected=document.querySelectorAll('[data-qcm-choice].selected,[data-qcm-choice][aria-checked="true"],[data-qcm-choice][aria-pressed="true"]').length;
                        const leaked=document.querySelectorAll('[data-qcm-choice].correct,[data-qcm-choice].wrong').length;
                        if(r.answer.pending!==null||selected!==0||leaked!==0){entry.ok=false;entry.reason=`qcm-not-idle pending=${r.answer.pending} selected=${selected} leaked=${leaked}`;}
                        r.answer.selectQcm(a.answer); r.answer.validate();
                      }else if(a.type==='fill'){
                        if(!Array.isArray(r.answer.pending)||r.answer.pending.some(Boolean)){entry.ok=false;entry.reason='fill-not-empty';}
                        r.answer.pending=[...a.answer]; r.answer.validate();
                      }else if(a.type==='matching'){
                        if(!r.answer.pending||Object.keys(r.answer.pending.matches||{}).length!==0){entry.ok=false;entry.reason='matching-not-empty';}
                        r.answer.pending={matches:Object.fromEntries(a.pairs),selectedRight:null}; r.answer.validate();
                      }else if(a.type==='order'){
                        if(!Array.isArray(r.answer.pending)||r.answer.pending.length!==a.tokens.length||r.answer.selectedOrderToken!==null){entry.ok=false;entry.reason='order-initial-invalid';}
                        r.answer.pending=[...a.answer]; r.answer.validate();
                      }else if(a.type==='flashcard'){
                        if(!r.answer.pending||r.answer.pending.revealed!==false||r.answer.pending.grade!==null){entry.ok=false;entry.reason='flashcard-not-hidden';}
                        r.answer.gradeFlashcard(true);
                      }
                      if(!r.answer.feedback){entry.ok=false;entry.reason=entry.reason||'missing-feedback-after-answer';}
                      entries.push(entry);
                      r.answer.continue(); await wait();
                    }
                    runs.push({cycle,status:r.session.session.status,entries,guard});
                  }
                  return runs;
                }"""
            )
            flattened = [entry for run in result for entry in run["entries"]]
            add("four-complete-session-cycles", len(result) == 4 and all(run["status"] == "completed" for run in result), json.dumps([{"cycle": r["cycle"], "status": r["status"], "entries": len(r["entries"])} for r in result], ensure_ascii=False))
            add("all-activity-entries-clean", bool(flattened) and all(entry["ok"] for entry in flattened), json.dumps([entry for entry in flattened if not entry["ok"]][:12], ensure_ascii=False))
            seen_types = sorted({entry["type"] for entry in flattened})
            add("all-five-activity-types-covered", seen_types == ["fill", "flashcard", "matching", "order", "qcm"], str(seen_types))
            qcm_entries = [entry for entry in flattened if entry["type"] == "qcm"]
            add("qcm-idle-on-every-entry", len(qcm_entries) >= 4 and all(entry["pending"] is None and entry["ok"] for entry in qcm_entries), json.dumps(qcm_entries[:8], ensure_ascii=False))

            # RC614/615: every activity is operable without pointer input and focus remains meaningful.
            def start_activity(activity_id: str) -> None:
                page.evaluate("id => {const r=window.__LEARNIT_TEST__.runtime;r.session.startTargetedReview([id],{summary:'keyboard activity gate'});r.answer.reset();r.go('session');}", activity_id)
                page.wait_for_timeout(220)

            start_activity("t-qcm")
            qcm_first = page.locator('[data-qcm-choice]').first
            qcm_first.focus(); qcm_first.press("ArrowDown"); page.wait_for_timeout(120)
            qcm_state = page.evaluate("({checked:Array.from(document.querySelectorAll('[data-qcm-choice]')).map(x=>x.getAttribute('aria-checked')),focus:document.activeElement&&document.activeElement.dataset.qcmChoice,pending:window.__LEARNIT_TEST__.runtime.answer.pending})")
            add("keyboard-qcm-arrows", qcm_state["checked"].count("true") == 1 and qcm_state["focus"] == str(qcm_state["pending"]) and qcm_state["pending"] is not None, json.dumps(qcm_state, ensure_ascii=False))
            page.locator('[data-action="validate"]').press("Enter"); page.wait_for_timeout(150)
            qcm_feedback = page.evaluate("({feedback:!!window.__LEARNIT_TEST__.runtime.answer.feedback,role:document.activeElement&&document.activeElement.getAttribute('role'),text:document.activeElement&&document.activeElement.textContent})")
            add("keyboard-qcm-validate-focus", qcm_feedback["feedback"] and qcm_feedback["role"] in {"status", "alert"}, json.dumps(qcm_feedback, ensure_ascii=False))

            start_activity("t-fill")
            page.locator('[data-fill-slot]').first.press("Enter"); page.wait_for_timeout(100)
            page.locator('[data-fill-token="B"]').press("Enter"); page.wait_for_timeout(180)
            fill_pending = page.evaluate("window.__LEARNIT_TEST__.runtime.answer.pending")
            add("keyboard-fill-buttons", fill_pending == ["B"], json.dumps(fill_pending, ensure_ascii=False))

            start_activity("t-match")
            page.locator('[data-drag-match-right="1"]').focus(); page.keyboard.press("Enter"); page.wait_for_timeout(80)
            page.locator('[data-match-left="A"]').focus(); page.keyboard.press("Enter"); page.wait_for_timeout(120)
            match_pending = page.evaluate("window.__LEARNIT_TEST__.runtime.answer.pending")
            add("keyboard-matching-alternative", match_pending.get("matches", {}).get("A") == "1" and match_pending.get("selectedRight") is None, json.dumps(match_pending, ensure_ascii=False))

            start_activity("t-order")
            order_before = page.evaluate("window.__LEARNIT_TEST__.runtime.answer.pending.slice()")
            first_order = page.locator('[data-drag-order-token]').first
            first_order.focus(); page.keyboard.press("Alt+ArrowDown"); page.wait_for_timeout(160)
            order_after = page.evaluate("window.__LEARNIT_TEST__.runtime.answer.pending.slice()")
            order_focus = page.evaluate("document.activeElement&&document.activeElement.dataset.dragOrderToken")
            add("keyboard-order-reorder", order_before != order_after and bool(order_focus), json.dumps({"before": order_before, "after": order_after, "focus": order_focus}, ensure_ascii=False))

            start_activity("t-flash")
            page.locator('[data-action="flashcard-reveal"]').focus(); page.keyboard.press("Enter"); page.wait_for_timeout(120)
            revealed = page.locator('.flashcard-face.back').count() == 1
            page.get_by_role("button", name="Je savais").focus(); page.keyboard.press("Space"); page.wait_for_timeout(120)
            flash_feedback = page.evaluate("!!window.__LEARNIT_TEST__.runtime.answer.feedback")
            add("keyboard-flashcard", revealed and flash_feedback, f"revealed={revealed} feedback={flash_feedback}")

            add("no-browser-errors", not errors, " | ".join(errors[-10:]))
            context.close()
        finally:
            browser.close()

    ok = all(row["ok"] for row in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "learnit.rc623.activity_keyboard_transition_stress.v1", "ok": ok, "checks": rows, "errors": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "passed": sum(row["ok"] for row in rows), "total": len(rows), "report": str(OUT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
