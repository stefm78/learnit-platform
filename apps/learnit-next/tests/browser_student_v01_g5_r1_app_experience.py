#!/usr/bin/env python3
from __future__ import annotations
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
LEARNER_STATES = {"À découvrir", "En apprentissage", "À renforcer", "À confirmer", "Acquis récemment"}

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

def run_viewport(browser, url: str, viewport: dict[str, int], touch: bool) -> None:
    context = browser.new_context(viewport=viewport, has_touch=touch)
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url)
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

    page.locator("#kit-file").set_input_files({
        "name": FIXTURE.name,
        "mimeType": "application/json",
        "buffer": FIXTURE.read_bytes(),
    })
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_text("Student V0.1 runtime fixture", exact=True).wait_for()

    assert page.get_by_text("Aucun parcours Atlas installé", exact=True).count() == 0
    assert page.locator("[data-atlas-int-surface]").evaluate("(el) => getComputedStyle(el).display === 'none'")
    assert page.locator(".app-main").evaluate("(el) => getComputedStyle(el).display !== 'none'")

    page.get_by_role("button", name="Commencer").click()
    page.locator('[data-activity-presentation="qcm"]').wait_for()

    assert page.evaluate("""() => {
      const activity = document.querySelector('.served-activity-form');
      const buckets = document.querySelector('[data-session-objective-buckets="true"]');
      const details = document.querySelector('[data-session-progress-details="true"]');
      return Boolean(activity && buckets && details
        && (activity.compareDocumentPosition(buckets) & Node.DOCUMENT_POSITION_FOLLOWING)
        && (activity.compareDocumentPosition(details) & Node.DOCUMENT_POSITION_FOLLOWING));
    }""")

    buckets = page.locator('[data-session-objective-buckets="true"] [data-objective-bucket]')
    expected = page.evaluate("""async () => {
      const courses = await window.__LEARNIT_NEXT_TEST__.listCourses();
      return courses[0].progress.objectives.length;
    }""")
    assert expected > 0 and buckets.count() == expected
    visible_states = page.locator('[data-session-objective-buckets="true"] .objective-bucket__state').all_inner_texts()
    assert visible_states and set(visible_states) <= LEARNER_STATES, visible_states

    details = page.locator('[data-session-progress-details="true"]')
    assert details.get_attribute("open") is None
    assert not page.get_by_text("Prochaine action recommandée", exact=True).is_visible()
    summary = details.locator("summary")
    assert summary.inner_text() == "Voir ma progression"
    summary.focus()
    page.keyboard.press("Enter")
    assert details.get_attribute("open") is not None
    assert page.get_by_text("Prochaine action recommandée", exact=True).is_visible()
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")

    page.reload()
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    page.locator('[data-activity-presentation="qcm"]').wait_for()
    assert page.locator('[data-session-progress-details="true"]').get_attribute("open") is None
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    assert errors == [], errors
    context.close()

def main() -> int:
    assert ARTIFACT.is_file(), "build artifact is required"
    with artifact_server() as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        run_viewport(browser, url, {"width": 1365, "height": 768}, False)
        run_viewport(browser, url, {"width": 390, "height": 844}, True)
        browser.close()
    for marker in (
        "FALSE_EMPTY_STATE_BROWSER=PASS",
        "ACTIVITY_PRIMARY_BROWSER=PASS",
        "COMPACT_OBJECTIVE_BUCKETS_BROWSER=PASS",
        "PROGRESSIVE_DISCLOSURE_BROWSER=PASS",
        "KEYBOARD_DISCLOSURE=PASS",
        "DESKTOP_MOBILE_LAYOUT=PASS",
        "RESUME_RECOVERY_SMOKE=PASS",
    ):
        print(marker)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
