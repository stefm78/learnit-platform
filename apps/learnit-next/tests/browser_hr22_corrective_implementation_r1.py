#!/usr/bin/env python3
"""Browser qualification for JOB_23_HR22_CORRECTIVE_IMPLEMENTATION_R1."""
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
EVIDENCE = Path(os.environ.get("JOB23_EVIDENCE_DIR", "/tmp/atlas-wp065-hr22-corrective-evidence"))
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

def choose_matching(page, activity: dict[str, Any], correct: bool) -> None:
    expected = {x["leftItemId"]: x["rightItemId"] for x in activity["matches"]}
    left_ids = [x["itemId"] for x in activity["leftItems"]]
    rights = [expected[left] for left in left_ids]
    if not correct:
        rights = rights[1:] + rights[:1]
        assert all(expected[left] != right for left, right in zip(left_ids, rights))
    for left, right in zip(left_ids, rights):
        page.locator(f'[data-card-id="{left}"]').click()
        page.locator(f'.activity-pair-target[data-target-id="{right}"]').click()

def choose_order(page, activity: dict[str, Any], correct: bool) -> None:
    ids = list(activity["correctOrder"])
    if not correct:
        ids.reverse()
        assert ids != activity["correctOrder"]
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
        choose_matching(page, activity, correct)
    elif typ == "order":
        choose_order(page, activity, correct)
    else:
        raise AssertionError(f"Unhandled exact-showcase activity type: {typ}")
    page.locator('[data-served-activity-submit="true"]').click()
    panel = page.locator('[data-served-feedback="scored"]')
    panel.wait_for()
    if correct:
        assert panel.get_by_role("heading", name="Bonne réponse").count() == 1
        assert panel.get_by_role("heading", name="Votre réponse").count() == 1
        assert panel.get_by_role("heading", name="Réponse attendue").count() == 0
    else:
        assert panel.get_by_role("heading", name="À corriger").count() == 1
        assert panel.get_by_role("heading", name="Votre réponse").count() == 1
        assert panel.get_by_role("heading", name="Réponse attendue").count() == 1
    assert panel.get_by_role("heading", name="Explication").count() == (1 if activity.get("explanation") else 0)
    assert panel.locator(".feedback-answer ul").count() == 0
    assert panel.locator(".feedback-lines").count() >= 1
    assert panel.locator('[data-served-next-action="true"]').count() == 1
    return True

def complete_course(page, activities: list[dict[str, Any]], *, final_correct: bool) -> None:
    for index, activity in enumerate(activities):
        wait_activity(page, activity["activityRevisionId"], activity["type"])
        # Prove reload/resume on a real in-progress activity.
        if index == 3:
            page.reload()
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
            wait_activity(page, activity["activityRevisionId"], activity["type"])
        scored = submit_current(page, activity, correct=(final_correct if index == len(activities)-1 else True))
        if index == 4:
            progress = page.evaluate(
                "() => window.__LEARNIT_NEXT_TEST__.listCourses().then(xs => xs[0].progress.objectives)"
            )
            by_id = {x["objectiveId"]: x for x in progress}
            first_id = activities[2]["objectiveIds"][0]
            assert by_id[first_id]["status"] == "validated-recently", by_id
        if index < len(activities) - 1:
            if scored:
                page.locator('[data-served-next-action="true"]').click()
            wait_activity(page, activities[index + 1]["activityRevisionId"], activities[index + 1]["type"])

def main() -> int:
    assert ARTIFACT.is_file(), ARTIFACT
    kit = json.loads(KIT.read_text(encoding="utf-8"))
    course = kit["courses"][0]
    activities = course["activities"]
    assert kit["contract"] == "learnit.kit.v5"
    assert len(activities) == 10
    assert sum(int(a["estimatedMinutes"]) for a in activities) == 39

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

        # 01 — compact empty Library header has one structural title.
        assert page.get_by_role("heading", name="Learn-it").count() == 1
        assert page.get_by_role("heading", name="Importer votre premier cours").count() == 1
        assert page.get_by_text("BIBLIOTHÈQUE", exact=True).count() == 0
        no_overflow(page)

        # 02 — one-course Library remains learner-first and materially denser.
        current = import_kit(page, kit)
        card = page.locator(".course-card[data-course-install-id]").first
        assert card.get_by_text("Gérer", exact=True).count() == 1
        assert card.get_by_text("Renommer", exact=True).count() == 0
        assert card.locator('[data-objective-progress-r15="true"]').count() == 1
        height = card.bounding_box()["height"]
        assert height < 360, height
        shot(page, "01-one-course-compact")

        # 03 — representative 12-course scale fixture uses exact real card markup and remains scrollable/no-overflow.
        page.evaluate(
            """() => {
              const grid=document.querySelector('.course-grid');
              const source=grid.querySelector('.course-card');
              for(let i=2;i<=12;i++){
                const clone=source.cloneNode(true);
                clone.dataset.scaleFixture='true';
                clone.querySelector('h3').textContent='Cours représentatif '+i;
                clone.querySelectorAll('[id]').forEach(n=>n.removeAttribute('id'));
                grid.append(clone);
              }
            }"""
        )
        assert page.locator(".course-grid .course-card").count() == 12
        heights = page.locator(".course-grid .course-card").evaluate_all("xs => xs.map(x => x.getBoundingClientRect().height)")
        assert max(heights) < 360, max(heights)
        no_overflow(page)
        shot(page, "02-twelve-course-scale")
        page.locator('[data-scale-fixture="true"]').evaluate_all("xs => xs.forEach(x => x.remove())")

        # 04 — selecting/focusing reservoirs preserves interaction and exposes explicit selected semantics.
        reservoirs = card.locator('[data-objective-progress-r15-objective]')
        assert reservoirs.count() == 2
        reservoirs.nth(0).focus()
        assert reservoirs.nth(0).get_attribute("aria-pressed") == "true"
        assert reservoirs.nth(0).get_attribute("data-objective-progress-r15-selected") == "true"
        assert reservoirs.nth(1).get_attribute("aria-pressed") == "false"
        detail_id = reservoirs.nth(0).get_attribute("aria-controls")
        detail = page.locator(f"#{detail_id}")
        assert detail.is_visible()
        reservoirs.nth(1).click()
        assert reservoirs.nth(0).get_attribute("aria-pressed") == "false"
        assert reservoirs.nth(1).get_attribute("aria-pressed") == "true"
        shot(page, "03-selected-objective")

        # 05 — untouched objective truth starts at not-started / À découvrir.
        states = current["progress"]["objectives"]
        assert states and all(x["status"] == "not-started" for x in states)

        # 06 — exact 10-activity path, all scored answers correct.
        card.get_by_role("button", name="Commencer").click()
        complete_course(page, activities, final_correct=True)
        terminal_feedback = page.locator('[data-served-feedback="scored"]')
        assert terminal_feedback.get_by_role("heading", name="Réponse attendue").count() == 0
        terminal_feedback.locator('[data-served-next-action="true"]').click()
        card = page.locator(".course-card[data-course-install-id]").first
        card.wait_for()
        courses = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
        current = courses[0]
        assert current["progress"]["isComplete"] is True
        by_id = {x["objectiveId"]: x for x in current["progress"]["objectives"]}
        second_id = activities[-1]["objectiveIds"][0]
        assert by_id[second_id]["status"] == "ready-for-validation", by_id
        assert current["progress"]["recommendation"]["action"] == "validate"
        status = card.locator('[data-course-path-status="validate"]')
        assert status.count() == 1
        text = status.inner_text()
        assert "Parcours d’activités terminé" in text
        assert "à confirmer" in text
        assert "aucune nouvelle validation" in text
        assert "Cours terminé" not in card.inner_text()
        assert card.locator('[data-course-learning-action="learn"]').count() == 0
        shot(page, "04-complete-ready-for-validation-guidance")

        # 07 — reset and replay with final wrong answer: completed activity path remains immediately reviewable.
        page.evaluate("() => window.__LEARNIT_NEXT_TEST__.resetNextData()")
        page.reload()
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        current = import_kit(page, kit)
        card = page.locator(".course-card[data-course-install-id]").first
        card.get_by_role("button", name="Commencer").click()
        complete_course(page, activities, final_correct=False)
        wrong = page.locator('[data-served-feedback="scored"]')
        assert wrong.get_by_role("heading", name="Réponse attendue").count() == 1
        # Matching/math feedback comparison primitives are paragraphs, never list bullets.
        assert wrong.locator(".feedback-answer ul").count() == 0
        wrong.locator('[data-served-next-action="true"]').click()
        card = page.locator(".course-card[data-course-install-id]").first
        card.wait_for()
        courses = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
        current = courses[0]
        assert current["progress"]["isComplete"] is True
        assert current["progress"]["recommendation"]["action"] == "correct"
        review = page.evaluate("(cid) => window.__LEARNIT_NEXT_TEST__.getReviewQueue(cid)", current["courseInstallId"])
        assert review["total"] > 0
        status = card.locator('[data-course-path-status="correct"]')
        assert "Un objectif reste à renforcer" in status.inner_text()
        strengthen = card.get_by_role("button", name="Renforcer maintenant")
        assert strengthen.count() == 1 and "primary" in (strengthen.get_attribute("class") or "")
        assert "Cours terminé" not in card.inner_text()
        shot(page, "05-complete-review-needed-actionable")
        strengthen.click()
        page.wait_for_function("() => window.__LEARNIT_NEXT_TEST__.getSession().then(s => s && s.mode === 'review')")
        session = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession()")
        assert session["currentActivity"]["activityRevisionId"] == activities[-1]["activityRevisionId"]

        assert not errors, errors
        assert not external, external
        context.close()
        browser.close()

    screenshots = sorted(EVIDENCE.glob("*.png"))
    assert len(screenshots) == 5, [p.name for p in screenshots]
    print("HR22_BROWSER_MOBILE_390x844=PASS")
    print("HR22_LIBRARY_ONE_COURSE=PASS")
    print("HR22_LIBRARY_12_COURSE_SCALE=PASS")
    print("HR22_OBJECTIVE_NOT_STARTED=PASS")
    print("HR22_OBJECTIVE_VALIDATED_RECENTLY=PASS")
    print("HR22_OBJECTIVE_READY_FOR_VALIDATION=PASS")
    print("HR22_OBJECTIVE_REVIEW_NEEDED=PASS")
    print("HR22_TERMINAL_VALIDATE_GUIDANCE=PASS")
    print("HR22_TERMINAL_REVIEW_ACTION=PASS")
    print("HR22_CORRECT_FEEDBACK_NO_DUPLICATE_EXPECTED=PASS")
    print("HR22_INCORRECT_FEEDBACK_COMPARISON=PASS")
    print("HR22_SELECTED_OBJECTIVE_ARIA=PASS")
    print("HR22_RELOAD_RESUME=PASS")
    print("HR22_EXACT_SHOWCASE_10_ACTIVITIES_39_MINUTES=PASS")
    print("HR22_NO_UNEXPECTED_NETWORK_FETCH=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
