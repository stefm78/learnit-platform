#!/usr/bin/env python3
from __future__ import annotations
import json
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
FIXTURE = APP / "tests" / "fixtures" / "student_v01_v4_runtime.json"
FORBIDDEN_ACTIVITY_KEYS = {"correctChoiceId", "answers", "acceptedResponses", "matches", "correctOrder", "assignments"}
FAMILIES = ["qcm", "fill", "constructed", "lesson", "flashcard", "matching", "order", "classify"]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return

@contextmanager
def artifact_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ARTIFACT.parent)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/{ARTIFACT.name}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

def assert_safe_runtime_activity(page, expected_type: str) -> None:
    snapshot = page.evaluate("""async forbidden => {
      const session = await window.__LEARNIT_NEXT_TEST__.getSession();
      const activity = session?.currentActivity;
      const hits = [];
      const walk = value => {
        if (!value || typeof value !== 'object') return;
        for (const [key, child] of Object.entries(value)) {
          if (forbidden.includes(key)) hits.push(key);
          walk(child);
        }
      };
      walk(activity);
      return {keys: activity ? Object.keys(activity).sort() : [], type: activity?.presentation?.type ?? null, hits};
    }""", sorted(FORBIDDEN_ACTIVITY_KEYS))
    assert snapshot["keys"] == ["activityRevisionId", "presentation"], snapshot
    assert snapshot["type"] == expected_type, snapshot
    assert snapshot["hits"] == [], snapshot

def submit(page, scored: bool) -> None:
    page.locator('[data-served-activity-submit="true"]').click()
    feedback = page.locator('[data-served-feedback]')
    feedback.wait_for()
    assert feedback.get_attribute("data-served-feedback") == ("scored" if scored else "non-scored")
    text = feedback.inner_text()
    if scored:
        assert "Réponse correcte" in text, text
    else:
        assert "Activité terminée" in text, text
        assert "Réponse correcte" not in text and "Pas tout à fait" not in text, text

def answer_family(page, family: str) -> None:
    if family == "qcm":
        page.locator('[data-activity-choice="true"]').nth(1).check()
        submit(page, True)
    elif family == "fill":
        page.locator('[data-activity-slot]').select_option(index=1)
        submit(page, True)
    elif family == "constructed":
        assert page.locator('[data-activity-media] img').count() >= 1
        page.locator('[data-constructed-response]').fill("Réponse exacte")
        submit(page, True)
    elif family == "lesson":
        page.locator('[data-activity-continue="lesson"]').click()
        submit(page, False)
    elif family == "flashcard":
        page.locator('[data-flashcard-reveal="true"]').click()
        assert page.get_by_text("Verso", exact=True).count() == 1
        page.locator('[data-activity-continue="flashcard"]').click()
        submit(page, False)
    elif family == "matching":
        page.locator('[data-matching-left="00000017-0017-4017-8017-000000000017"]').click()
        page.locator('[data-matching-right="00000019-0019-4019-8019-000000000019"]').click()
        page.locator('[data-matching-left="00000018-0018-4018-8018-000000000018"]').click()
        page.locator('[data-matching-right="0000001a-001a-401a-801a-00000000001a"]').click()
        submit(page, True)
    elif family == "order":
        page.locator('[data-order-item="0000001e-001e-401e-801e-00000000001e"] [data-order-move="up"]').click()
        submit(page, True)
    elif family == "classify":
        page.locator('[data-classify-select="00000024-0024-4024-8024-000000000024"]').select_option("00000023-0023-4023-8023-000000000023")
        page.locator('[data-classify-select="00000025-0025-4025-8025-000000000025"]').select_option("00000022-0022-4022-8022-000000000022")
        submit(page, True)
    else:
        raise AssertionError(family)

def run_viewport(browser, url: str, viewport: dict[str, int], touch: bool) -> None:
    context = browser.new_context(viewport=viewport, has_touch=touch)
    page = context.new_page()
    errors = []
    external = []
    origin = url.rsplit("/", 1)[0]
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url) if request.url.startswith(("http://", "https://")) and not request.url.startswith(origin) else None)
    page.goto(url)
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

    page.locator("#kit-file").set_input_files({
        "name": FIXTURE.name,
        "mimeType": "application/json",
        "buffer": FIXTURE.read_bytes(),
    })
    page.get_by_role("button", name="Importer").click()
    page.get_by_text("Student V0.1 runtime fixture", exact=True).wait_for()
    page.get_by_role("button", name="Commencer").click()

    for index, family in enumerate(FAMILIES):
        page.locator(f'[data-activity-presentation="{family}"]').wait_for()
        assert_safe_runtime_activity(page, family)
        assert page.locator("#activity-title").evaluate("e => document.activeElement === e")
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        answer_family(page, family)
        if family == "lesson":
            page.reload()
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
            page.locator('[data-activity-presentation="flashcard"]').wait_for()
            assert_safe_runtime_activity(page, "flashcard")
            continue
        if index < len(FAMILIES) - 1:
            page.locator('[data-served-next-action="true"]').click()

    page.locator('[data-served-next-action="true"]').click()
    page.get_by_text("Cours terminé", exact=True).wait_for()
    page.reload()
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    page.get_by_text("Cours terminé", exact=True).wait_for()
    progress = page.evaluate("""async () => (await window.__LEARNIT_NEXT_TEST__.listCourses())[0]?.progress""")
    assert progress["isComplete"] is True and progress["completed"] == 8, progress
    assert errors == [], errors
    assert external == [], external
    context.close()

def main() -> int:
    assert ARTIFACT.is_file(), "build artifact is required before served-browser qualification"
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert [item["type"] for item in fixture["courses"][0]["activities"]] == FAMILIES
    with artifact_server() as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        run_viewport(browser, url, {"width": 1365, "height": 768}, False)
        run_viewport(browser, url, {"width": 390, "height": 844}, True)
        browser.close()
    for marker in (
        "STUDENT_V01_SERVED_V4_BROWSER_PASS",
        "REAL_SERVED_V4_JOURNEY=PASS",
        "ALL_FAMILIES_REAL_PATH=PASS",
        "RELOAD_RESUME=PASS",
        "COMPLETION=PASS",
        "NON_SCORED_LESSON_FLASHCARD=PASS",
        "SECRET_BOUNDARY=PASS",
        "SAFE_MEDIA=PASS",
        "DESKTOP=PASS",
        "MOBILE=PASS",
        "ACCESSIBILITY_SMOKE=PASS",
    ):
        print(marker)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
