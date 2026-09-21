#!/usr/bin/env python3
"""Independent real-browser contradictory QA for Student V0.1 JOB05 R1."""
from __future__ import annotations

import copy
import json
import sys
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from authoring.v4 import validate_kit as v4  # noqa: E402

ARTIFACT = ROOT / "apps" / "learnit-next" / "dist" / "learnit-next.html"
FIXTURE = Path(__file__).with_name("JOB05_CANONICAL_V4_FIXTURE.json")
ATLAS_FIXTURE = ROOT / "authoring" / "v2" / "atlas" / "nombres_complexes_atlas.json"
ZERO_DIGEST = "sha256:" + ("0" * 64)
FAMILIES = ["lesson", "flashcard", "matching", "order", "classify", "qcm", "fill", "constructed"]
SCORED = {"matching", "order", "classify", "qcm", "fill", "constructed"}
FORBIDDEN = {"correctChoiceId", "answers", "acceptedResponses", "matches", "correctOrder", "assignments"}

LESSON_ID = "10000000-0000-4000-8000-000000000011"
FLASHCARD_ID = "10000000-0000-4000-8000-000000000021"
MATCHING_ID = "10000000-0000-4000-8000-000000000035"
QCM_CORRECT = "10000000-0000-4000-8000-000000000061"
QCM_WRONG = "10000000-0000-4000-8000-000000000062"
FILL_SLOT = "10000000-0000-4000-8000-000000000071"
FILL_CORRECT = "10000000-0000-4000-8000-000000000072"
ORDER_EVAPORATION = "10000000-0000-4000-8000-000000000041"
MATCH_LEFT_1 = "10000000-0000-4000-8000-000000000031"
MATCH_LEFT_2 = "10000000-0000-4000-8000-000000000032"
MATCH_RIGHT_1 = "10000000-0000-4000-8000-000000000033"
MATCH_RIGHT_2 = "10000000-0000-4000-8000-000000000034"
CLASS_ITEM_1 = "10000000-0000-4000-8000-000000000053"
CLASS_ITEM_2 = "10000000-0000-4000-8000-000000000054"
CLASS_BUCKET_1 = "10000000-0000-4000-8000-000000000051"
CLASS_BUCKET_2 = "10000000-0000-4000-8000-000000000052"


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


def wait_runtime(page) -> None:
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")


def import_with_real_controls(page, fixture: dict) -> str:
    page.locator("#kit-file").set_input_files({
        "name": FIXTURE.name,
        "mimeType": "application/json",
        "buffer": json.dumps(fixture, ensure_ascii=False).encode("utf-8"),
    })
    page.locator("form.import-panel button[type='submit']").click()
    card = page.locator(".course-card", has_text=fixture["courses"][0]["title"]).first
    card.wait_for()
    assert card.is_visible()
    courses = page.evaluate("async () => await window.__LEARNIT_NEXT_TEST__.listCourses()")
    assert len(courses) == 1, courses
    course_id = courses[0]["courseInstallId"]
    assert page.locator("[data-atlas-course-install-id]").count() == 0, "rich V4 must not be intercepted by Atlas"
    return course_id


def start_with_real_control(page, title: str) -> None:
    card = page.locator(".course-card", has_text=title).first
    card.locator('button[data-course-learning-action="learn"]').click()


def runtime_snapshot(page, expected_family: str) -> dict:
    snapshot = page.evaluate("""async forbidden => {
      const session = await window.__LEARNIT_NEXT_TEST__.getSession();
      const activity = session?.currentActivity ?? null;
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
        activity,
        hits,
        keys: activity ? Object.keys(activity).sort() : [],
        type: activity?.presentation?.type ?? null,
        serialized: JSON.stringify(activity),
      };
    }""", sorted(FORBIDDEN))
    assert snapshot["keys"] == ["activityRevisionId", "presentation"], snapshot
    assert snapshot["type"] == expected_family, snapshot
    assert snapshot["hits"] == [], snapshot
    for field in FORBIDDEN:
        assert f'"{field}"' not in snapshot["serialized"], (field, snapshot)
    return snapshot


def dom_secret_scan(page, family: str) -> None:
    root = page.locator(f'[data-activity-presentation="{family}"]')
    root.wait_for()
    html = root.evaluate("(element) => element.outerHTML")
    for field in FORBIDDEN:
        assert field not in html, (field, html)


def meaningful_keyboard_controls(page, family: str) -> None:
    root = page.locator(f'[data-activity-presentation="{family}"]')
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    if family == "lesson":
        selectors = ['[data-activity-continue="lesson"]']
    elif family == "flashcard":
        selectors = ['[data-flashcard-reveal="true"]']
    elif family == "matching":
        selectors = ["[data-matching-left]", "[data-matching-right]"]
    elif family == "order":
        selectors = ['[data-order-move="up"]', '[data-order-move="down"]']
    elif family == "classify":
        selectors = ["[data-classify-select]"]
    elif family == "qcm":
        selectors = ['[data-activity-choice="true"]']
    elif family == "fill":
        selectors = ["[data-activity-slot]"]
    else:
        selectors = ["[data-constructed-response]"]
    count = 0
    for selector in selectors:
        loc = root.locator(selector)
        for index in range(loc.count()):
            item = loc.nth(index)
            if not item.is_visible():
                continue
            info = item.evaluate("""el => ({
              tabIndex: el.tabIndex,
              name: (el.getAttribute('aria-label') || el.labels?.[0]?.innerText || el.innerText || '').trim()
            })""")
            assert info["tabIndex"] >= 0, (family, selector, info)
            assert info["name"], (family, selector, info)
            count += 1
    assert count > 0, family
    if family == "matching":
        assert root.locator("[data-matching-left]").count() >= 2
        assert root.locator("[data-matching-right]").count() >= 2
    if family == "order":
        assert root.locator("[data-order-move]").count() >= 2
    if family == "classify":
        assert root.locator("[data-classify-select]").count() >= 2


def prepare_family(page, family: str, correct: bool = True) -> None:
    if family == "lesson":
        page.locator('[data-activity-continue="lesson"]').click()
    elif family == "flashcard":
        page.locator('[data-flashcard-reveal="true"]').click()
        page.locator('[data-flashcard-back="true"]').wait_for()
        page.locator('[data-activity-continue="flashcard"]').click()
    elif family == "matching":
        pairs = (
            [(MATCH_LEFT_1, MATCH_RIGHT_1), (MATCH_LEFT_2, MATCH_RIGHT_2)]
            if correct else
            [(MATCH_LEFT_1, MATCH_RIGHT_2), (MATCH_LEFT_2, MATCH_RIGHT_1)]
        )
        for left, right in pairs:
            page.locator(f'[data-matching-left="{left}"]').click()
            page.locator(f'[data-matching-right="{right}"]').click()
    elif family == "order":
        page.locator(f'[data-order-item="{ORDER_EVAPORATION}"] [data-order-move="up"]').click()
    elif family == "classify":
        page.locator(f'[data-classify-select="{CLASS_ITEM_1}"]').select_option(CLASS_BUCKET_1)
        page.locator(f'[data-classify-select="{CLASS_ITEM_2}"]').select_option(CLASS_BUCKET_2)
    elif family == "qcm":
        value = QCM_CORRECT if correct else QCM_WRONG
        page.locator(f'[data-activity-choice="true"][value="{value}"]').check()
    elif family == "fill":
        page.locator(f'[data-activity-slot="{FILL_SLOT}"]').select_option(FILL_CORRECT)
    elif family == "constructed":
        page.locator("[data-constructed-response]").fill("évaporation")
    else:
        raise AssertionError(family)


def submit_and_assert_feedback(page, scored: bool, correct: bool | None) -> None:
    page.locator('[data-served-activity-submit="true"]').click()
    feedback = page.locator("[data-served-feedback]")
    feedback.wait_for()
    assert feedback.get_attribute("data-served-feedback") == ("scored" if scored else "non-scored")
    text = feedback.inner_text()
    if scored:
        assert ("Réponse correcte" in text) is bool(correct), text
        assert ("Pas tout à fait" in text) is (not bool(correct)), text
    else:
        assert "Activité terminée" in text, text
        assert "Réponse correcte" not in text and "Pas tout à fait" not in text, text
    assert page.evaluate("() => document.activeElement?.getAttribute('role') === 'status'")


def progress_record(page, course_id: str, activity_revision_id: str) -> dict:
    progress = page.evaluate(
        "async id => await window.__LEARNIT_NEXT_TEST__.getProgress(id)",
        course_id,
    )
    matches = [item for item in progress["records"] if item["activityRevisionId"] == activity_revision_id]
    assert len(matches) == 1, (activity_revision_id, progress)
    return matches[0]


def run_wrong_answer(browser, url: str, fixture: dict) -> dict:
    context = browser.new_context(viewport={"width": 1365, "height": 768})
    page = context.new_page()
    errors: list[str] = []
    external: list[str] = []
    origin = url.rsplit("/", 1)[0]
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url)
            if request.url.startswith(("http://", "https://")) and not request.url.startswith(origin) else None)
    page.goto(url)
    wait_runtime(page)
    course_id = import_with_real_controls(page, fixture)
    start_with_real_control(page, fixture["courses"][0]["title"])

    for family in ("lesson", "flashcard"):
        page.locator(f'[data-activity-presentation="{family}"]').wait_for()
        runtime_snapshot(page, family)
        dom_secret_scan(page, family)
        prepare_family(page, family)
        submit_and_assert_feedback(page, False, None)
        page.locator('[data-served-next-action="true"]').click()

    page.locator('[data-activity-presentation="matching"]').wait_for()
    runtime_snapshot(page, "matching")
    dom_secret_scan(page, "matching")
    prepare_family(page, "matching", correct=False)
    submit_and_assert_feedback(page, True, False)
    record = progress_record(page, course_id, MATCHING_ID)
    assert record["correct"] is False and record["completed"] is True, record
    review = page.evaluate("async id => await window.__LEARNIT_NEXT_TEST__.getReviewQueue(id)", course_id)
    assert MATCHING_ID in review["activityRevisionIds"], review
    assert errors == [], errors
    assert external == [], external
    context.close()
    return {"feedbackScored": True, "correct": False, "progressCorrect": record["correct"], "reviewQueued": True}


def run_full_journey(browser, url: str, fixture: dict, viewport: dict[str, int], touch: bool) -> dict:
    context = browser.new_context(viewport=viewport, has_touch=touch)
    page = context.new_page()
    errors: list[str] = []
    external: list[str] = []
    origin = url.rsplit("/", 1)[0]
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url)
            if request.url.startswith(("http://", "https://")) and not request.url.startswith(origin) else None)
    page.goto(url)
    wait_runtime(page)
    page.evaluate("() => localStorage.setItem('job05-r1-legacy-sentinel', 'keep-me')")
    course_id = import_with_real_controls(page, fixture)
    start_with_real_control(page, fixture["courses"][0]["title"])

    reload_after = {"lesson": "flashcard", "matching": "order", "qcm": "fill"}
    non_scored_records = {}
    for index, family in enumerate(FAMILIES):
        page.locator(f'[data-activity-presentation="{family}"]').wait_for()
        snapshot = runtime_snapshot(page, family)
        dom_secret_scan(page, family)
        meaningful_keyboard_controls(page, family)
        if family == "lesson":
            image = page.locator('[data-activity-media] img')
            assert image.count() == 1 and image.first.is_visible()
            assert image.first.get_attribute("alt") == fixture["assets"][0]["alt"]
            assert image.first.get_attribute("src").startswith("data:image/svg+xml")
        prepare_family(page, family, correct=True)
        submit_and_assert_feedback(page, family in SCORED, True if family in SCORED else None)

        record = progress_record(page, course_id, snapshot["activity"]["activityRevisionId"])
        if family in ("lesson", "flashcard"):
            assert record.get("scored") is False, record
            assert "correct" not in record, record
            non_scored_records[family] = {"scored": record.get("scored"), "hasCorrect": "correct" in record}
        else:
            assert record.get("correct") is True, record

        if family in reload_after:
            expected = reload_after[family]
            page.reload()
            wait_runtime(page)
            page.locator(f'[data-activity-presentation="{expected}"]').wait_for()
            runtime_snapshot(page, expected)
            dom_secret_scan(page, expected)
        elif index < len(FAMILIES) - 1:
            page.locator('[data-served-next-action="true"]').click()

    progress = page.evaluate("async id => await window.__LEARNIT_NEXT_TEST__.getProgress(id)", course_id)
    assert progress["isComplete"] is True and progress["completed"] == 8, progress
    page.locator('[data-served-next-action="true"]').click()
    page.get_by_text("Cours terminé", exact=True).wait_for()
    page.reload()
    wait_runtime(page)
    page.get_by_text("Cours terminé", exact=True).wait_for()
    progress_after = page.evaluate("async id => await window.__LEARNIT_NEXT_TEST__.getProgress(id)", course_id)
    assert progress_after["isComplete"] is True and progress_after["completed"] == 8, progress_after
    assert page.evaluate("() => localStorage.getItem('job05-r1-legacy-sentinel')") == "keep-me"
    assert errors == [], errors
    assert external == [], external
    context.close()
    return {
        "viewport": viewport,
        "completed": progress_after["completed"],
        "reloads": ["after-lesson-non-scored", "after-matching-scored", "after-qcm-scored"],
        "nonScored": non_scored_records,
        "externalRequests": external,
        "pageErrors": errors,
    }


def reset_revision_digests(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.endswith("RevisionDigest"):
                value[key] = ZERO_DIGEST
            else:
                reset_revision_digests(child)
    elif isinstance(value, list):
        for child in value:
            reset_revision_digests(child)


def clone_same_labels(fixture: dict) -> dict:
    text = json.dumps(fixture, ensure_ascii=False).replace("10000000-", "20000000-")
    clone = json.loads(text)
    reset_revision_digests(clone)
    errors = v4.fill_new_digests(clone)
    assert errors == [], errors
    return clone


def hostile_media_payload(fixture: dict, svg: str, prefix: str) -> dict:
    payload = copy.deepcopy(fixture)
    payload["packageRevisionId"] = prefix + payload["packageRevisionId"][8:]
    payload["packageRevisionDigest"] = ZERO_DIGEST
    payload["assets"][0]["data"] = svg
    errors = v4.fill_new_digests(payload)
    assert errors == [], errors
    return payload


def run_media_runtime_attack(browser, url: str, fixture: dict) -> dict:
    context = browser.new_context(viewport={"width": 1365, "height": 768})
    page = context.new_page()
    external: list[str] = []
    origin = url.rsplit("/", 1)[0]
    page.on("request", lambda request: external.append(request.url)
            if request.url.startswith(("http://", "https://")) and not request.url.startswith(origin) else None)
    page.goto(url)
    wait_runtime(page)
    cases = {
        "active": hostile_media_payload(
            fixture,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><script>alert(1)</script></svg>',
            "30000000",
        ),
        "remote": hostile_media_payload(
            fixture,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><image href="https://example.invalid/x.png" width="10" height="10"/></svg>',
            "40000000",
        ),
    }
    evidence = {}
    for name, payload in cases.items():
        page.evaluate("async () => await window.__LEARNIT_NEXT_TEST__.resetNextData()")
        validation = page.evaluate("async payload => await window.__LEARNIT_NEXT_TEST__.validatePackage(payload)", payload)
        serialized = json.dumps(validation, ensure_ascii=False)
        assert validation["ok"] is False, (name, validation)
        assert "unsafe_svg" in serialized, (name, validation)
        assert "digest_mismatch" not in serialized, (name, validation)
        outcome = page.evaluate("""async payload => {
          try {
            await window.__LEARNIT_NEXT_TEST__.importPackage(payload);
            return {rejected:false};
          } catch (error) {
            return {rejected:true, name:error?.name ?? '', message:String(error?.message ?? error)};
          }
        }""", payload)
        assert outcome["rejected"] is True, (name, outcome)
        assert page.evaluate("async () => (await window.__LEARNIT_NEXT_TEST__.listCourses()).length") == 0
        assert page.locator("[data-activity-presentation]").count() == 0
        evidence[name] = {"validationRejected": True, "importRejected": True, "digestMismatch": False}
    assert external == [], external
    context.close()
    return evidence


def run_isolation(browser, url: str, fixture: dict) -> dict:
    context = browser.new_context(viewport={"width": 1365, "height": 768})
    page = context.new_page()
    page.goto(url)
    wait_runtime(page)
    page.evaluate("() => localStorage.setItem('job05-r1-unrelated', 'preserve')")
    page.evaluate("async () => await window.__LEARNIT_NEXT_TEST__.resetNextData()")
    clone = clone_same_labels(fixture)
    first = page.evaluate("async payload => await window.__LEARNIT_NEXT_TEST__.importPackage(payload)", fixture)
    second = page.evaluate("async payload => await window.__LEARNIT_NEXT_TEST__.importPackage(payload)", clone)
    assert first["courses"] and second["courses"]
    courses = page.evaluate("async () => await window.__LEARNIT_NEXT_TEST__.listCourses()")
    assert len(courses) == 2, courses
    assert courses[0]["title"] == courses[1]["title"] == fixture["courses"][0]["title"], courses
    ids = {item["courseInstallId"] for item in courses}
    assert len(ids) == 2, courses
    page.reload()
    wait_runtime(page)
    courses_after = page.evaluate("async () => await window.__LEARNIT_NEXT_TEST__.listCourses()")
    assert len(courses_after) == 2
    assert page.evaluate("() => localStorage.getItem('job05-r1-unrelated')") == "preserve"
    page.evaluate("async () => await window.__LEARNIT_NEXT_TEST__.resetNextData()")
    assert page.evaluate("async () => (await window.__LEARNIT_NEXT_TEST__.listCourses()).length") == 0
    assert page.evaluate("() => localStorage.getItem('job05-r1-unrelated')") == "preserve"
    context.close()
    return {"sameHumanLabelDistinctInstalls": True, "reloadPreserved": True, "cleanReset": True, "unrelatedStatePreserved": True}


def run_atlas_gate(browser, url: str, fixture: dict) -> dict:
    atlas = json.loads(ATLAS_FIXTURE.read_text(encoding="utf-8"))
    types = {activity["type"] for course in atlas["courses"] for activity in course["activities"]}
    assert types <= {"qcm", "fill"}, types
    context = browser.new_context(viewport={"width": 1365, "height": 768})
    page = context.new_page()
    page.goto(url)
    wait_runtime(page)
    page.evaluate("async () => await window.__LEARNIT_NEXT_TEST__.resetNextData()")
    imported = page.evaluate("async payload => await window.__LEARNIT_NEXT_TEST__.importPackage(payload)", atlas)
    assert imported["courses"], imported
    page.reload()
    wait_runtime(page)
    page.locator("[data-atlas-course-install-id]").first.wait_for()
    assert page.locator("[data-atlas-course-install-id]").count() >= 1
    context.close()
    return {"atlasQcmFillAccepted": True, "richV4ClassicProvenByPrimaryJourney": True}


def main() -> int:
    assert ARTIFACT.is_file(), "canonical built artifact is required"
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert [item["type"] for item in fixture["courses"][0]["activities"]] == FAMILIES
    with artifact_server() as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        evidence = {
            "wrongAnswer": run_wrong_answer(browser, url, fixture),
            "desktop": run_full_journey(browser, url, fixture, {"width": 1365, "height": 768}, False),
            "mobile": run_full_journey(browser, url, fixture, {"width": 390, "height": 844}, True),
            "mediaRuntimeNegative": run_media_runtime_attack(browser, url, fixture),
            "persistenceIsolation": run_isolation(browser, url, fixture),
            "atlasGate": run_atlas_gate(browser, url, fixture),
        }
        browser.close()
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    for marker in (
        "JOB05_R1_REAL_SERVED_V4_JOURNEY=PASS",
        "JOB05_R1_ALL_FAMILIES_REAL_PATH=PASS",
        "JOB05_R1_WRONG_ANSWER_SEMANTICS=PASS",
        "JOB05_R1_RELOAD_RESUME=PASS",
        "JOB05_R1_COMPLETION=PASS",
        "JOB05_R1_NON_SCORED_LESSON_FLASHCARD=PASS",
        "JOB05_R1_SECRET_BOUNDARY=PASS",
        "JOB05_R1_MEDIA_SAFE_LOCAL=PASS",
        "JOB05_R1_MEDIA_RUNTIME_FAIL_CLOSED=PASS",
        "JOB05_R1_DESKTOP=PASS",
        "JOB05_R1_MOBILE=PASS",
        "JOB05_R1_ACCESSIBILITY_SMOKE=PASS",
        "JOB05_R1_PERSISTENCE_ISOLATION=PASS",
        "JOB05_R1_ATLAS_GATE=PASS",
    ):
        print(marker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
