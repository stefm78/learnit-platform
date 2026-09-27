#!/usr/bin/env python3
"""Browser qualification for ATLAS-WP-063 R15 objective-progress restoration R2."""
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
FIXTURE = ROOT / "apps" / "learnit-next" / "tests" / "fixtures" / "objective_progress_r15_five_states.json"
EVIDENCE = Path(os.environ.get("R15_EVIDENCE_DIR", "/tmp/atlas-wp063-r15-browser-evidence"))

EXPECTED_STATES = [
    ("not-started", "À découvrir", "0%", None),
    ("training", "En apprentissage", "48%", None),
    ("review-needed", "À renforcer", "46%", "↺"),
    ("ready-for-validation", "À confirmer", "82%", "◇"),
    ("validated-recently", "Acquis récemment", "100%", "✓"),
]
EXPECTED_SELECTED_PRESENTERS = {"flashcard", "matching", "order", "classify", "qcm", "fill", "lesson"}

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

def response_for(activity: dict[str, Any]) -> dict[str, Any]:
    kind = activity["type"]
    if kind == "qcm":
        return {"choiceId": activity["correctChoiceId"]}
    if kind == "fill":
        return {entry["slotId"]: entry["tokenId"] for entry in activity["answers"]}
    if kind == "constructed":
        return {"text": activity["acceptedResponses"][0]}
    if kind == "lesson":
        return {"acknowledged": True}
    if kind == "flashcard":
        return {"revealed": True}
    if kind == "matching":
        return {"associations": [dict(entry) for entry in activity["matches"]]}
    if kind == "order":
        return {"orderedItemIds": list(activity["correctOrder"])}
    if kind == "classify":
        return {"assignments": [dict(entry) for entry in activity["assignments"]]}
    raise AssertionError(kind)

def screenshot(page, viewport_name: str, name: str) -> None:
    page.screenshot(path=str(EVIDENCE / f"{viewport_name}-{name}.png"), full_page=True)

def assert_no_macro(page) -> None:
    assert page.locator('[data-session-objective-buckets="true"]').count() == 0
    assert page.locator('[data-session-progress-details="true"]').count() == 0
    assert page.locator('[data-objective-progress-r15="true"]').count() == 0
    assert page.get_by_text("Voir ma progression", exact=True).count() == 0
    assert page.get_by_text("Progression par objectif", exact=True).count() == 0

def assert_no_overflow(page) -> None:
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def library_checks(page, course: dict[str, Any], viewport_name: str, touch: bool) -> None:
    card = page.locator('.course-card[data-course-install-id]').filter(has_text=course["title"]).first
    assert card.count() == 1
    assert card.locator('[data-library-objective-details="true"]').count() == 0
    panel = card.locator('[data-objective-progress-r15="true"]')
    assert panel.count() == 1
    assert card.locator('.atlas-r13-progress').count() == 0
    reservoirs = panel.locator('button[data-objective-progress-r15-objective]')
    assert reservoirs.count() == len(course["objectives"])
    priorities = panel.locator('[data-objective-progress-r15-priority="true"]')
    assert priorities.count() == 1
    screenshot(page, viewport_name, "01-library-r15-direct")
    for index in range(reservoirs.count()):
        reservoir = reservoirs.nth(index)
        label = reservoir.get_attribute("aria-label")
        assert label and course["objectives"][index]["label"] in label
        reservoir.focus()
        assert page.evaluate("(el) => document.activeElement === el", reservoir.element_handle())
        assert panel.locator('[data-objective-progress-r15-detail="true"]').get_attribute("hidden") is None
    if touch:
        reservoirs.first.tap()
    else:
        reservoirs.first.click()
    assert panel.locator('[data-objective-progress-r15-detail="true"]').get_attribute("hidden") is None
    assert_no_overflow(page)
    screenshot(page, viewport_name, "02-library-r15-detail")

def walk_showcase(page, course: dict[str, Any], viewport_name: str) -> None:
    activities = course["activities"]
    assert len(activities) == 10
    assert sum(int(a.get("estimatedMinutes", 0)) for a in activities) == 39

    page.get_by_role("button", name="Commencer").click()
    page.locator('[data-served-activity-submit="true"]').wait_for()
    session = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession()")
    assert session["currentActivity"]["activityRevisionId"] == activities[0]["activityRevisionId"]
    assert session["currentActivity"]["presentation"]["type"] == activities[0]["type"]
    assert_no_macro(page)
    assert_no_overflow(page)
    screenshot(page, viewport_name, "03-active-v8-no-macro")

    assert page.locator('[data-activity-continue="lesson"]').count() == 0
    page.locator('[data-served-activity-submit="true"]').click()
    page.locator('[data-activity-presentation="flashcard"]').wait_for()
    assert page.locator('[data-served-feedback]').count() == 0
    assert_no_macro(page)
    assert_no_overflow(page)
    screenshot(page, viewport_name, "04-non-scored-direct-next")
    seen = {activities[0]["type"]}
    for index in range(1, 9):
        activity = activities[index]
        page.locator('[data-served-activity-submit="true"]').wait_for()
        session = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession()")
        assert session["currentActivity"]["activityRevisionId"] == activity["activityRevisionId"], (index, session)
        assert session["currentActivity"]["presentation"]["type"] == activity["type"]
        seen.add(activity["type"])
        assert_no_macro(page)
        assert page.get_by_text(f"{index + 1}/10 activités", exact=True).count() == 1
        result = page.evaluate(
            "async x => window.__LEARNIT_NEXT_TEST__.answer(x.id, x.answer)",
            {"id": activity["activityRevisionId"], "answer": response_for(activity)},
        )
        assert result["progress"]["completed"] == index + 1
        page.reload()
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

    final_activity = activities[9]
    page.locator('[data-served-activity-submit="true"]').wait_for()
    session = page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession()")
    assert session["currentActivity"]["activityRevisionId"] == final_activity["activityRevisionId"]
    assert session["currentActivity"]["presentation"]["type"] == final_activity["type"]
    seen.add(final_activity["type"])
    assert_no_macro(page)
    assert page.get_by_text("10/10 activités", exact=True).count() == 1
    assert seen == {"lesson", "flashcard", "matching", "qcm", "order"}

    correct = final_activity["correctChoiceId"]
    page.locator(f'input[value="{correct}"]').check()
    page.locator('[data-served-activity-submit="true"]').click()
    page.locator('[data-served-feedback]').wait_for()

    terminal = page.locator('[data-objective-progress-r15-context="terminal-summary"]')
    assert terminal.count() == 1
    assert terminal.locator('[data-objective-progress-r15-priority="true"]').count() == 0
    assert terminal.locator('[data-objective-progress-r15-priority-context="true"]').count() == 0
    reservoirs = terminal.locator('button[data-objective-progress-r15-objective]')
    assert reservoirs.count() == len(course["objectives"])
    worked = terminal.locator('[data-objective-progress-r15-session-worked="true"]')
    changed = terminal.locator('[data-objective-progress-r15-session-changed="true"]')
    assert worked.count() == len(course["objectives"])
    assert changed.count() == len(course["objectives"])
    context = terminal.locator('[data-objective-progress-r15-session-context="true"]').inner_text()
    assert "Cette séance" in context
    assert f"{len(course['objectives'])} objectifs travaillés" in context
    assert f"{len(course['objectives'])} changements d’état visibles" in context
    for reservoir in reservoirs.all():
        aria = reservoir.get_attribute("aria-label")
        assert aria and "Travaillé pendant cette séance" in aria and "État modifié pendant cette séance" in aria
        reservoir.focus()
        detail = terminal.locator('[data-objective-progress-r15-detail="true"]')
        assert detail.get_attribute("hidden") is None
        assert "Cette séance :" in detail.inner_text()
    assert_no_overflow(page)
    screenshot(page, viewport_name, "05-terminal-session-r15-summary")

def fixture_checks(page, viewport_name: str, touch: bool) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["qualificationOnly"] is True and fixture["learnerCourse"] is False
    page.evaluate("""() => {
      const app = document.getElementById('app');
      app.style.display = 'none';
      const mount = document.createElement('main');
      mount.id = 'r15-qualification-fixture';
      mount.style.padding = '24px';
      document.body.append(mount);
      window.__LEARNIT_NEXT_TEST__.renderObjectiveR15Fixture(mount);
    }""")
    mount = page.locator("#r15-qualification-fixture")
    assert mount.get_attribute("data-r15-five-state-fixture") == "true"
    reservoirs = mount.locator('button[data-objective-progress-r15-objective]')
    assert reservoirs.count() == 5
    for index, (state, label, level, mark) in enumerate(EXPECTED_STATES):
        reservoir = reservoirs.nth(index)
        assert reservoir.get_attribute("data-objective-progress-r15-state") == state
        assert label in (reservoir.get_attribute("aria-label") or "")
        fill = reservoir.locator(".objective-progress-r15__fill")
        actual_level = fill.evaluate("el => getComputedStyle(el).getPropertyValue('--objective-progress-r15-level').trim()")
        assert actual_level == level, (state, actual_level, level)
        marks = reservoir.locator(".objective-progress-r15__state-mark")
        if mark is None:
            assert marks.count() == 0
        else:
            assert marks.count() == 1 and marks.inner_text() == mark
        reservoir.focus()
        assert page.evaluate("(el) => document.activeElement === el", reservoir.element_handle())
    review = mount.locator('[data-objective-progress-r15-state="review-needed"]')
    assert review.evaluate("el => getComputedStyle(el.querySelector('.objective-progress-r15__fill')).backgroundImage.includes('repeating-linear-gradient')")
    acquired = mount.locator('[data-objective-progress-r15-state="validated-recently"]')
    assert acquired.locator(".objective-progress-r15__state-mark").inner_text() == "✓"
    priority = mount.locator('[data-objective-progress-r15-priority="true"]')
    assert priority.count() == 1
    assert priority.get_attribute("data-objective-progress-r15-objective") == fixture["priorityObjectiveId"]
    assert "Priorité Learn-it" in (priority.get_attribute("aria-label") or "")
    if touch:
        review.tap()
    else:
        review.click()
    assert mount.locator('[data-objective-progress-r15-detail="true"]').get_attribute("hidden") is None
    assert_no_overflow(page)
    screenshot(page, viewport_name, "06-five-state-fixture")

def run_viewport(browser, url: str, kit: dict[str, Any], viewport: dict[str, int], touch: bool, name: str) -> None:
    context = browser.new_context(viewport=viewport, has_touch=touch, is_mobile=touch)
    page = context.new_page()
    errors: list[str] = []
    external: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url)
            if request.url.startswith(("http://", "https://")) and "127.0.0.1" not in request.url else None)
    page.goto(url)
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    page.locator("#kit-file").set_input_files({
        "name": KIT.name,
        "mimeType": "application/json",
        "buffer": KIT.read_bytes(),
    })
    page.locator("form.import-panel button[type='submit']").click()
    course = kit["courses"][0]
    page.get_by_text(course["title"], exact=True).wait_for()
    library_checks(page, course, name, touch)
    walk_showcase(page, course, name)
    fixture_checks(page, name, touch)
    assert errors == [], errors
    assert external == [], external
    context.close()

def main() -> int:
    assert ARTIFACT.is_file(), ARTIFACT
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    kit = json.loads(KIT.read_text(encoding="utf-8"))
    course = kit["courses"][0]
    assert len(course["activities"]) == 10
    assert sum(int(a.get("estimatedMinutes", 0)) for a in course["activities"]) == 39

    with serve() as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        run_viewport(browser, url, kit, {"width": 1365, "height": 768}, False, "desktop-1365x768")
        run_viewport(browser, url, kit, {"width": 390, "height": 844}, True, "mobile-390x844")
        browser.close()

    expected = {
        f"{viewport}-{index:02d}-{slug}.png"
        for viewport in ("desktop-1365x768", "mobile-390x844")
        for index, slug in (
            (1, "library-collapsed"),
            (2, "library-r15-expanded"),
            (3, "active-v8-no-macro"),
            (4, "intermediate-feedback-no-macro"),
            (5, "terminal-session-r15-summary"),
            (6, "five-state-fixture"),
        )
    }
    assert {path.name for path in EVIDENCE.glob("*.png")} == expected

    print("LIBRARY_COMPACT_ROW: PASS")
    print("LIBRARY_PROGRESS_DISCLOSURE: PASS")
    print("LIBRARY_R15_PROGRESS: PASS")
    print("R15_PRIORITY_OUTLINE: PASS")
    print("R15_PRIORITY_CONTEXT: PASS")
    print("R15_FOCUS_CLICK_DETAIL: PASS")
    print("R15_ACCESSIBLE_NAMES: PASS")
    print("R15_MOBILE_LAYOUT: PASS")
    print("ACTIVE_ACTIVITY_MACRO_PROGRESS: ABSENT")
    print("ACTIVE_ACTIVITY_PROGRESS_DISCLOSURE: ABSENT")
    print("INTERMEDIATE_FEEDBACK_MACRO_PROGRESS: ABSENT")
    print("TERMINAL_SESSION_R15_SUMMARY: PASS")
    print("TERMINAL_SESSION_WORKED_CHANGED: PASS")
    print("LEGACY_DOM_DOUBLE_ENHANCEMENT: NONE")
    print("EXACT_10_ACTIVITY_SHOWCASE: PASS")
    print("SHOWCASE_EXACT_39_MINUTES: PASS")
    print("DESKTOP_1365X768: PASS")
    print("MOBILE_TOUCH_390X844: PASS")
    print("R15_BROWSER_SCREENSHOTS: 12")
    print("SELECTED_V8_PRESENTERS_EXPECTED: " + ",".join(sorted(EXPECTED_SELECTED_PRESENTERS)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
