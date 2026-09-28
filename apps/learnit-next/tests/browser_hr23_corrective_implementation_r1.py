#!/usr/bin/env python3
"""Browser qualification for JOB_24_HR23_CORRECTIVE_IMPLEMENTATION_R1."""
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
EVIDENCE = Path(os.environ.get("JOB24_EVIDENCE_DIR", "/tmp/atlas-wp066-hr23-corrective-evidence"))
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

def wait_activity(page, revision_id: str, activity_type: str) -> None:
    page.wait_for_function(
        """id => window.__LEARNIT_NEXT_TEST__.getSession()
          .then(s => s && s.currentActivity && s.currentActivity.activityRevisionId === id)""",
        arg=revision_id,
    )
    page.locator(f'.served-activity-form[data-served-activity-type="{activity_type}"]').wait_for()

def import_kit(page, kit: dict[str, Any]) -> dict[str, Any]:
    page.locator("#kit-file").set_input_files({
        "name": KIT.name,
        "mimeType": "application/json",
        "buffer": KIT.read_bytes(),
    })
    page.get_by_role("button", name="Ajouter à la bibliothèque").click()
    card = page.locator(".course-card[data-course-install-id]").first
    card.wait_for()
    courses = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
    assert len(courses) == 1
    assert courses[0]["title"] == kit["courses"][0]["title"]
    return courses[0]

def choose_matching_by_slot(page, activity: dict[str, Any], correct: bool) -> None:
    expected = {x["leftItemId"]: x["rightItemId"] for x in activity["matches"]}
    left_ids = [x["itemId"] for x in activity["leftItems"]]
    rights = [expected[left] for left in left_ids]
    if not correct:
        rights = rights[1:] + rights[:1]
    for left, right in zip(left_ids, rights):
        page.locator(f'[data-card-id="{left}"]').click()
        slot = page.locator(f'.activity-pair-slot[data-target-id="{right}"]')
        assert slot.get_attribute("role") == "button"
        slot.click()

def choose_order(page, activity: dict[str, Any], correct: bool) -> None:
    ids = list(activity["correctOrder"])
    if not correct:
        ids.reverse()
    page.evaluate(
        """ids => {
          const list=document.querySelector('[data-order-list="true"]');
          const overlay=list.querySelector('.activity-order-insert-overlay');
          for(const id of ids){
            const row=list.querySelector('[data-order-item="'+id+'"]');
            list.insertBefore(row,overlay);
          }
        }""",
        ids,
    )

def submit_current(page, activity: dict[str, Any], correct: bool = True) -> bool:
    typ = activity["type"]
    if typ == "lesson":
        page.get_by_role("button", name="Continuer").click()
        return False
    if typ == "flashcard":
        page.locator(".activity-flash-card").click()
        page.get_by_role("button", name="Continuer").click()
        return False
    if typ == "qcm":
        correct_id = activity["correctChoiceId"]
        choice = correct_id if correct else next(x["choiceId"] for x in activity["choices"] if x["choiceId"] != correct_id)
        page.locator(f'input[data-activity-choice="true"][value="{choice}"]').check()
    elif typ == "matching":
        choose_matching_by_slot(page, activity, correct)
    elif typ == "order":
        choose_order(page, activity, correct)
    else:
        raise AssertionError(f"Unhandled exact-showcase activity type: {typ}")

    page.locator('[data-served-activity-submit="true"]').click()
    panel = page.locator('[data-served-feedback="scored"]')
    panel.wait_for()
    if correct:
        assert panel.get_by_role("heading", name="Bonne réponse").count() == 1
        assert panel.get_by_role("heading", name="Réponse attendue").count() == 0
    else:
        assert panel.get_by_role("heading", name="À corriger").count() == 1

    if typ == "matching":
        assert panel.get_by_role("heading", name="Correspondances").count() == 1
        assert panel.locator("table").count() == 1
        assert panel.get_by_role("columnheader", name="Élément").count() == 1
        assert panel.get_by_role("columnheader", name="Votre réponse").count() == 1
        assert panel.get_by_role("columnheader", name="Attendu").count() == (0 if correct else 1)
        assert "Élément :" not in panel.inner_text()
        assert "votre choix :" not in panel.inner_text()
    else:
        assert panel.get_by_role("heading", name="Votre réponse").count() == 1
        assert panel.get_by_role("heading", name="Réponse attendue").count() == (0 if correct else 1)

    assert panel.get_by_role("heading", name="Explication").count() == (1 if activity.get("explanation") else 0)
    assert panel.locator('[data-served-next-action="true"]').count() == 1
    return True

def complete_course(page, activities: list[dict[str, Any]], *, final_correct: bool) -> None:
    for index, activity in enumerate(activities):
        wait_activity(page, activity["activityRevisionId"], activity["type"])
        if index == 3:
            page.reload()
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
            wait_activity(page, activity["activityRevisionId"], activity["type"])
        scored = submit_current(page, activity, correct=(final_correct if index == len(activities)-1 else True))
        if index == 4:
            progress = page.evaluate(
                "() => window.__LEARNIT_NEXT_TEST__.listCourses().then(xs => xs[0].progress.objectives)"
            )
            assert any(x["status"] == "validated-recently" for x in progress), progress
        if index < len(activities) - 1 and scored:
            page.locator('[data-served-next-action="true"]').click()

def clone_course_records(page, total: int) -> None:
    page.evaluate(
        """async total => {
          const report=await window.__LEARNIT_NEXT_TEST__.storageReport();
          await new Promise((resolve,reject)=>{
            const req=indexedDB.open(report.indexedDbName);
            req.onerror=()=>reject(req.error);
            req.onsuccess=()=>{
              const db=req.result;
              const tx=db.transaction('courses','readwrite');
              const store=tx.objectStore('courses');
              const get=store.getAll();
              get.onerror=()=>reject(get.error);
              get.onsuccess=()=>{
                const source=get.result[0];
                if(!source) throw new Error('missing source course');
                for(let i=2;i<=total;i++){
                  const clone=structuredClone(source);
                  clone.courseInstallId=source.courseInstallId+'-scale-'+i;
                  clone.displayLabel='Cours représentatif '+i;
                  store.put(clone);
                }
              };
              tx.oncomplete=()=>{db.close();resolve();};
              tx.onerror=()=>reject(tx.error);
              tx.onabort=()=>reject(tx.error);
            };
          });
        }""",
        total,
    )

def visible_cards(page) -> int:
    return page.locator(".course-card").evaluate_all("xs => xs.filter(x => !x.hidden).length")

def main() -> int:
    assert ARTIFACT.is_file(), ARTIFACT
    kit = json.loads(KIT.read_text(encoding="utf-8"))
    course = kit["courses"][0]
    activities = course["activities"]
    assert len(activities) == 10
    assert course["estimatedMinutes"] == 39

    with serve() as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        context = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page = context.new_page()
        errors: list[str] = []
        external: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: external.append(r.url) if r.url.startswith(("http://", "https://")) and "127.0.0.1" not in r.url else None)
        page.goto(url, wait_until="load")
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

        # A/B/H — real scalable library records + local search + secondary options.
        import_kit(page, kit)
        clone_course_records(page, 12)
        page.reload()
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        page.locator(".course-card").first.wait_for()
        assert page.locator(".course-card").count() == 12
        search = page.locator(".library-search-input")
        assert search.count() == 1
        search.fill("représentatif 12")
        assert visible_cards(page) == 1
        search.fill("")
        assert visible_cards(page) == 12
        first = page.locator(".course-card").first
        assert "min estimées au total" in first.inner_text()
        assert first.get_by_text("Gérer", exact=True).count() == 0
        options_summary = first.locator(".course-settings-details > summary")
        assert options_summary.count() == 1
        assert (options_summary.get_attribute("aria-label") or "").startswith("Options du cours")
        assert first.locator(".course-objectives-details").count() == 1
        assert first.locator('[data-objective-progress-r15="true"]').is_hidden()
        no_overflow(page)
        shot(page, "01-library-12-searchable-compact")

        # A — visible reset returns immediately to the usable empty state; no reload/reopen.
        page.locator(".library-management > summary").click()
        page.get_by_role("button", name="Réinitialiser les données locales").click()
        page.get_by_role("button", name="Confirmer la réinitialisation").click()
        page.get_by_role("heading", name="Importer votre premier cours").wait_for()
        assert page.get_by_role("heading", name="Vos cours").count() == 1
        report = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.storageReport()")
        assert all(value == 0 for value in report["counts"].values()), report
        no_overflow(page)
        shot(page, "02-reset-immediate-empty-state")

        current = import_kit(page, kit)
        card = page.locator(".course-card").first

        # C — progressive disclosure keeps R15 direct interaction and adds a real toggle.
        progress_details = card.locator(".course-objectives-details")
        progress_details.locator("summary").click()
        reservoirs = progress_details.locator('[data-objective-progress-r15-objective]')
        assert reservoirs.count() == 2
        reservoirs.nth(0).focus()
        detail_id = reservoirs.nth(0).get_attribute("aria-controls")
        detail = page.locator(f"#{detail_id}")
        assert detail.is_visible()
        assert reservoirs.nth(0).get_attribute("aria-pressed") == "false"
        reservoirs.nth(0).click()
        assert reservoirs.nth(0).get_attribute("aria-pressed") == "true"
        assert reservoirs.nth(0).get_attribute("aria-expanded") == "true"
        reservoirs.nth(0).click()
        assert reservoirs.nth(0).get_attribute("aria-pressed") == "false"
        assert reservoirs.nth(0).get_attribute("aria-expanded") == "false"
        assert detail.is_hidden()
        reservoirs.nth(1).click()
        assert reservoirs.nth(1).get_attribute("aria-pressed") == "true"
        shot(page, "03-objective-toggle")

        # D/E/F/G — exact course; matching uses selected-source -> tap empty destination.
        card.get_by_role("button", name="Commencer").click()
        complete_course(page, activities, final_correct=True)
        terminal = page.locator('[data-served-feedback="scored"]')
        assert terminal.get_by_role("button", name="Voir le bilan de la séance").count() == 1
        assert terminal.locator('[data-objective-progress-r15-context="terminal-summary"]').count() == 0
        shot(page, "04-last-correction-before-summary")
        terminal.get_by_role("button", name="Voir le bilan de la séance").click()
        summary = page.locator('[data-session-summary="true"]')
        summary.wait_for()
        assert summary.get_by_role("heading", name="Bilan de la séance").count() == 1
        assert summary.locator('[data-objective-progress-r15-context="terminal-summary"]').count() == 1
        assert "Cette séance a travaillé" in summary.inner_text()
        shot(page, "05-dedicated-session-summary")
        summary.get_by_role("button", name="Retour à la bibliothèque").click()
        card = page.locator(".course-card").first
        card.wait_for()
        current = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses().then(xs => xs[0])")
        statuses = {x["status"] for x in current["progress"]["objectives"]}
        assert "validated-recently" in statuses and "ready-for-validation" in statuses, statuses
        assert current["progress"]["recommendation"]["action"] == "validate"
        guidance = card.locator('[data-course-path-status="validate"]')
        text = guidance.inner_text()
        assert "Parcours d’activités terminé" in text
        assert "Un objectif est acquis récemment et un autre reste à confirmer" in text
        assert "validation distincte" in text
        assert "ni nouvelle activité de validation à proposer ni date de disponibilité" in text
        assert "demain" not in text.lower()
        assert card.locator('[data-course-learning-action="learn"]').count() == 0
        shot(page, "06-awaiting-validation-truthful-gap")

        # F — incorrect terminal answer still separates correction from recap and preserves review action.
        page.evaluate("() => window.__LEARNIT_NEXT_TEST__.resetNextData()")
        page.reload()
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        import_kit(page, kit)
        page.locator(".course-card").first.get_by_role("button", name="Commencer").click()
        complete_course(page, activities, final_correct=False)
        wrong = page.locator('[data-served-feedback="scored"]')
        assert wrong.get_by_role("heading", name="À corriger").count() == 1
        assert wrong.get_by_role("button", name="Voir le bilan de la séance").count() == 1
        wrong.get_by_role("button", name="Voir le bilan de la séance").click()
        summary = page.locator('[data-session-summary="true"]')
        summary.wait_for()
        summary.get_by_role("button", name="Retour à la bibliothèque").click()
        card = page.locator(".course-card").first
        card.wait_for()
        current = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses().then(xs => xs[0])")
        assert current["progress"]["recommendation"]["action"] == "correct"
        assert card.get_by_role("button", name="Renforcer maintenant").count() == 1
        shot(page, "07-terminal-wrong-review-action")

        assert not errors, errors
        assert not external, external
        context.close()
        browser.close()

    screenshots = sorted(EVIDENCE.glob("*.png"))
    assert len(screenshots) == 7, [p.name for p in screenshots]
    print("HR23_BROWSER_MOBILE_390x844=PASS")
    print("HR23_RESET_NO_RELOAD=PASS")
    print("HR23_LIBRARY_12_SEARCHABLE=PASS")
    print("HR23_OPTIONS_SECONDARY=PASS")
    print("HR23_OBJECTIVE_TOGGLE=PASS")
    print("HR23_MATCHING_SLOT_TAP=PASS")
    print("HR23_MAPPING_TABLE_SEMANTICS=PASS")
    print("HR23_LAST_FEEDBACK_SUMMARY_SEPARATION=PASS")
    print("HR23_SESSION_DELTA_SUMMARY=PASS")
    print("HR23_AWAITING_VALIDATION_TRUTH=PASS")
    print("HR23_TERMINAL_WRONG_REVIEW_ACTION=PASS")
    print("HR23_RELOAD_RESUME=PASS")
    print("HR23_EXACT_SHOWCASE_10_ACTIVITIES_39_MINUTES=PASS")
    print("HR23_NO_UNEXPECTED_NETWORK_FETCH=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
