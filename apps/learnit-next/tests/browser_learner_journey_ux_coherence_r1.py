#!/usr/bin/env python3
"""Browser Human-Replay-style qualification for ATLAS-WP-064."""
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
EVIDENCE = Path(os.environ.get("JOB22_EVIDENCE_DIR", "/tmp/atlas-wp064-learner-journey-evidence"))
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

def shot(page, viewport: str, scene: str) -> None:
    page.screenshot(path=str(EVIDENCE / f"{viewport}-{scene}.png"), full_page=True)

def no_overflow(page) -> None:
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def learner_presentation_is_safe(page) -> None:
    presentation = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession().then(x => x.currentActivity.presentation)")
    forbidden = {"correctChoiceId", "answers", "acceptedResponses", "matches", "correctOrder", "assignments"}
    assert forbidden.isdisjoint(presentation), presentation

def wrong_matching(page, activity: dict[str, Any]) -> None:
    expected = {x["leftItemId"]: x["rightItemId"] for x in activity["matches"]}
    left_ids = [x["itemId"] for x in activity["leftItems"]]
    correct_rights = [expected[left] for left in left_ids]
    wrong_rights = correct_rights[1:] + correct_rights[:1]
    assert all(expected[left] != right for left, right in zip(left_ids, wrong_rights))
    for left, right in zip(left_ids, wrong_rights):
        page.locator(f'[data-card-id="{left}"]').click()
        page.locator(f'.activity-pair-target[data-target-id="{right}"]').click()

def assert_scored_feedback(page, activity: dict[str, Any]) -> None:
    panel = page.locator('[data-served-feedback="scored"]')
    panel.wait_for()
    assert panel.get_by_role("heading", name="Votre réponse").count() == 1
    assert panel.get_by_role("heading", name="Réponse attendue").count() == 1
    if activity.get("explanation"):
        assert panel.get_by_role("heading", name="Explication").count() == 1
        assert activity["explanation"] in panel.inner_text()
    assert panel.locator('[data-served-next-action="true"]').count() == 1
    assert page.get_by_role("button", name="Revenir au parcours").count() == 0
    assert page.locator(".progress-summary").count() == 0

def run_viewport(browser, url: str, kit: dict[str, Any], viewport: dict[str, int], touch: bool, name: str) -> None:
    context = browser.new_context(viewport=viewport, has_touch=touch, is_mobile=touch)
    page = context.new_page()
    errors: list[str] = []
    external: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: external.append(r.url) if r.url.startswith(("http://", "https://")) and "127.0.0.1" not in r.url else None)
    page.goto(url, wait_until="load")
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    course = kit["courses"][0]
    activities = course["activities"]
    assert len(activities) == 10
    assert sum(int(a.get("estimatedMinutes", 0)) for a in activities) == 39

    # 01 — empty Library is import-first and destructive controls are absent.
    assert page.get_by_role("heading", name="Importer votre premier cours").count() == 1
    assert page.get_by_text("Réinitialiser les données locales", exact=True).count() == 0
    assert page.locator(".library-management").count() == 0
    assert page.locator("#kit-file").get_attribute("class") and "sr-only" in page.locator("#kit-file").get_attribute("class")
    assert page.get_by_text("Choisir un cours", exact=True).count() == 1
    no_overflow(page)
    shot(page, name, "01-library-empty")

    # 02 — selected file shows only learner-facing preview title, never the technical filename.
    page.locator("#kit-file").set_input_files({"name": KIT.name, "mimeType": "application/json", "buffer": KIT.read_bytes()})
    page.locator(".import-panel .help").filter(has_text=kit["title"]).wait_for()
    body = page.locator("body").inner_text()
    assert KIT.name not in body
    assert kit["title"] in body
    assert page.get_by_role("button", name="Ajouter à la bibliothèque").is_enabled()
    shot(page, name, "02-file-selected")

    # 03 — post-import course card is learning-first and R15 is directly visible.
    page.get_by_role("button", name="Ajouter à la bibliothèque").click()
    card = page.locator('.course-card[data-course-install-id]').filter(has_text=course["title"]).first
    card.wait_for()
    assert card.locator('[data-objective-progress-r15="true"]').count() == 1
    assert card.locator('[data-library-objective-details="true"]').count() == 0
    assert card.locator(".progress-summary").count() == 0
    assert page.get_by_text("À revoir : aucune activité.", exact=True).count() == 0
    assert page.get_by_text("Options du cours", exact=True).count() == 0
    assert page.get_by_text("Voir la progression détaillée", exact=True).count() == 0
    assert card.locator('button.primary[data-course-learning-action="learn"]').get_attribute("data-course-install-id")
    assert card.locator("button.primary").count() == 1
    assert page.locator(".library-management").get_attribute("open") is None
    no_overflow(page)
    shot(page, name, "03-library-post-import")

    # Start exact showcase.
    card.get_by_role("button", name="Commencer").click()
    page.locator('[data-activity-presentation="lesson"]').wait_for()
    learner_presentation_is_safe(page)

    # 07 — Lesson A: one visible pedagogical title and one transition CTA.
    assert page.locator("#activity-title").get_attribute("class") == "sr-only"
    assert page.locator(".activity-learning-card > h2").count() == 1
    assert page.locator('[data-activity-continue="lesson"]').count() == 0
    assert page.locator('[data-served-activity-submit="true"]').count() == 1
    assert page.get_by_role("button", name="Continuer").count() == 1
    no_overflow(page)
    shot(page, name, "07-lesson-single-cta")
    page.get_by_role("button", name="Continuer").click()
    page.locator('[data-activity-presentation="flashcard"]').wait_for()
    assert page.locator("[data-served-feedback]").count() == 0

    # 08 — Flashcard B: reveal in-place; the single outer Continue becomes enabled.
    submit = page.locator('[data-served-activity-submit="true"]')
    assert submit.is_disabled()
    assert page.locator('[data-activity-continue="flashcard"]').count() == 0
    page.locator(".activity-flash-card").click()
    assert submit.is_enabled()
    status = page.locator(".activity-interaction-status")
    assert status.count() == 1 and "sr-only" in (status.get_attribute("class") or "")
    shot(page, name, "08-flashcard-revealed-single-cta")
    submit.click()
    page.locator('[data-activity-presentation="matching"]').wait_for()
    assert page.locator("[data-served-feedback]").count() == 0

    # 09 — Matching B clean interaction; system narration remains SR-only.
    learner_presentation_is_safe(page)
    assert page.locator(".activity-prompt").count() == 1
    assert page.locator('[data-served-activity-submit="true"]').count() == 1
    matching_status = page.locator(".activity-interaction-status")
    assert "sr-only" in (matching_status.get_attribute("class") or "")
    no_overflow(page)
    shot(page, name, "09-matching-clean")

    # 10 — wrong matching gives learner answer + authored correction + explanation, one CTA.
    wrong_matching(page, activities[2])
    page.locator('[data-served-activity-submit="true"]').click()
    assert_scored_feedback(page, activities[2])
    feedback_text = page.locator('[data-served-feedback="scored"]').inner_text()
    for left in activities[2]["leftItems"]:
        assert left["label"] in feedback_text
    no_overflow(page)
    shot(page, name, "10-matching-wrong-contextual-feedback")

    # 04 — return to Library; qualified corrective recommendation owns the primary CTA.
    page.locator("#app").dispatch_event("learnit:show-library")
    card = page.locator('.course-card[data-course-install-id]').filter(has_text=course["title"]).first
    card.wait_for()
    courses = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
    current = next(x for x in courses if x["title"] == course["title"])
    review = page.evaluate("(cid) => window.__LEARNIT_NEXT_TEST__.getReviewQueue(cid)", current["courseInstallId"])
    assert current["progress"]["recommendation"]["action"] == "correct", current["progress"]["recommendation"]
    assert review["total"] > 0
    assert card.get_by_role("button", name="Renforcer maintenant").count() == 1
    assert card.get_by_role("button", name="Renforcer maintenant").get_attribute("class") == "primary"
    assert card.get_by_role("button", name="Reprendre").count() == 1
    assert "secondary" in (card.get_by_role("button", name="Reprendre").get_attribute("class") or "")
    assert card.locator('[data-objective-progress-r15="true"]').count() == 1
    assert card.locator('[data-objective-progress-r15-priority="true"]').count() == 1
    shot(page, name, "04-library-in-progress-r15-priority")

    # 05 — management is secondary and collapsed by default.
    management = page.locator(".library-management")
    assert management.get_attribute("open") is None
    reset_action = page.get_by_text("Réinitialiser les données locales", exact=True)
    assert reset_action.count() == 1 and not reset_action.is_visible()
    management.locator("summary").click()
    assert management.get_attribute("open") is not None
    assert reset_action.is_visible()
    shot(page, name, "05-library-management-open")

    # 06 — rename remains contextual with a short label and no explanatory paragraph.
    rename = card.locator(".course-settings-details")
    rename.locator("summary").click()
    assert rename.get_attribute("open") is not None
    assert rename.get_by_text("Nom local du cours", exact=True).count() == 1
    assert page.get_by_text("Ce nom est utilisé uniquement sur cet appareil.", exact=True).count() == 0
    shot(page, name, "06-course-inline-rename")

    # Resume the normal learning path, not the review queue.
    card.locator('[data-course-learning-action="learn"]').click()
    page.locator('[data-activity-presentation="qcm"]').wait_for()
    session = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession()")
    assert session["currentActivity"]["activityRevisionId"] == activities[3]["activityRevisionId"]
    learner_presentation_is_safe(page)

    # 11 — correct QCM feedback is contextual and still has a single transition.
    correct = activities[3]["correctChoiceId"]
    page.locator(f'input[data-activity-choice="true"][value="{correct}"]').check()
    page.locator('[data-served-activity-submit="true"]').click()
    assert_scored_feedback(page, activities[3])
    shot(page, name, "11-qcm-correct-contextual-feedback")

    # 12 — reload/resume remains exact; returning to Library is coherent afterwards.
    page.locator('[data-served-next-action="true"]').click()
    page.locator('[data-activity-presentation="qcm"]').wait_for()
    before_reload = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession().then(x => x.currentActivity.activityRevisionId)")
    page.reload()
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    page.locator('[data-served-activity-submit="true"]').wait_for()
    after_reload = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession().then(x => x.currentActivity.activityRevisionId)")
    assert after_reload == before_reload == activities[4]["activityRevisionId"]
    page.get_by_role("button", name="← Bibliothèque").click()
    card = page.locator('.course-card[data-course-install-id]').filter(has_text=course["title"]).first
    card.wait_for()
    assert card.locator('[data-objective-progress-r15="true"]').count() == 1
    assert page.locator(".library-management").get_attribute("open") is None
    no_overflow(page)
    shot(page, name, "12-library-after-reload-resume")

    assert not errors, errors
    assert not external, external
    context.close()

def main() -> int:
    assert ARTIFACT.is_file(), ARTIFACT
    kit = json.loads(KIT.read_text(encoding="utf-8"))
    assert kit["contract"] == "learnit.kit.v5"
    assert len(kit["courses"][0]["activities"]) == 10
    assert sum(a["estimatedMinutes"] for a in kit["courses"][0]["activities"]) == 39
    with serve() as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        run_viewport(browser, url, kit, {"width": 1365, "height": 768}, False, "desktop-1365x768")
        run_viewport(browser, url, kit, {"width": 390, "height": 844}, True, "mobile-390x844")
        browser.close()
    screenshots = sorted(EVIDENCE.glob("*.png"))
    assert len(screenshots) == 24, [p.name for p in screenshots]
    print("JOB22_VISUAL_EVIDENCE_24_SCENES: PASS")
    print("JOB22_DESKTOP_1365x768: PASS")
    print("JOB22_MOBILE_TOUCH_390x844: PASS")
    print("JOB22_EXACT_SHOWCASE_10_ACTIVITIES_39_MINUTES: PASS")
    print("JOB22_RELOAD_RESUME: PASS")
    print("JOB22_NO_UNEXPECTED_NETWORK_FETCH: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
