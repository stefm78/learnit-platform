#!/usr/bin/env python3
"""Real-control preflight proving the repaired product accepts the generated canonical V4 kit."""
from __future__ import annotations
import argparse
import json
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "apps" / "learnit-next" / "dist" / "learnit-next.html"
FORBIDDEN = {"correctChoiceId", "answers", "acceptedResponses", "matches", "correctOrder", "assignments"}

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

def assert_no_secrets(page, family: str) -> None:
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
      return {
        keys: activity ? Object.keys(activity).sort() : [],
        type: activity?.presentation?.type ?? null,
        hits,
        serialized: JSON.stringify(activity),
      };
    }""", sorted(FORBIDDEN))
    assert snapshot["keys"] == ["activityRevisionId", "presentation"], snapshot
    assert snapshot["type"] == family, snapshot
    assert snapshot["hits"] == [], snapshot
    html = page.locator(f'[data-activity-presentation="{family}"]').evaluate("(element) => element.outerHTML")
    for key in FORBIDDEN:
        assert key not in html, (key, html)

def submit(page) -> None:
    page.locator('[data-served-activity-submit="true"]').click()
    page.locator("[data-served-feedback]").wait_for()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit", type=Path, required=True)
    args = parser.parse_args()
    kit = json.loads(args.kit.read_text(encoding="utf-8"))
    activities = kit["courses"][0]["activities"]
    assert [item["type"] for item in activities[:3]] == ["lesson", "flashcard", "matching"]
    assert ARTIFACT.is_file(), "canonical app build is required"

    with artifact_server() as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        context = browser.new_context(viewport={"width": 1365, "height": 768})
        page = context.new_page()
        external = []
        origin = url.rsplit("/", 1)[0]
        page.on("request", lambda request: external.append(request.url)
                if request.url.startswith(("http://", "https://")) and not request.url.startswith(origin) else None)
        page.goto(url)
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

        with page.expect_file_chooser() as chooser_info:
            page.locator("#kit-file").click()
        chooser_info.value.set_files(str(args.kit.resolve()))
        page.locator("form.import-panel button[type='submit']").click()
        page.get_by_text(kit["courses"][0]["title"], exact=True).wait_for()
        page.get_by_role("button", name="Commencer").click()

        page.locator('[data-activity-presentation="lesson"]').wait_for()
        assert_no_secrets(page, "lesson")
        page.locator('[data-activity-continue="lesson"]').click()
        submit(page)
        page.locator('[data-served-next-action="true"]').click()

        page.locator('[data-activity-presentation="flashcard"]').wait_for()
        assert_no_secrets(page, "flashcard")
        page.locator('[data-flashcard-reveal="true"]').click()
        page.locator('[data-activity-continue="flashcard"]').click()
        submit(page)
        page.locator('[data-served-next-action="true"]').click()

        matching = activities[2]
        page.locator('[data-activity-presentation="matching"]').wait_for()
        assert_no_secrets(page, "matching")
        for pair in matching["matches"]:
            page.locator(f'[data-matching-left="{pair["leftItemId"]}"]').click()
            page.locator(f'[data-matching-right="{pair["rightItemId"]}"]').click()
        submit(page)
        feedback = page.locator("[data-served-feedback]")
        assert feedback.get_attribute("data-served-feedback") == "scored"
        assert "Réponse correcte" in feedback.inner_text()
        assert external == [], external
        context.close()
        browser.close()

    print("STUDENT_V01_JOB07_R2_OLD_BLOCKER_CLOSED=PASS")
    print("STUDENT_V01_JOB07_R2_GENERATED_KIT_REAL_CONTROLS=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
