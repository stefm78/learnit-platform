#!/usr/bin/env python3
"""Extracted-package browser qualification for Student V0.1 JOB07 R2."""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

PREFIX = "student-v01-pilot/"
FAMILIES = ["lesson", "flashcard", "matching", "order", "classify", "qcm", "fill", "constructed"]
FORBIDDEN = {"correctChoiceId", "answers", "acceptedResponses", "matches", "correctOrder", "assignments"}
LEARNER_START_ACTIONS = 6


def safe_extract(package: Path, root: Path) -> Path:
    with zipfile.ZipFile(package) as archive:
        for info in archive.infolist():
            path = Path(info.filename)
            assert not path.is_absolute() and ".." not in path.parts
            assert info.filename.startswith(PREFIX)
        archive.extractall(root)
    return root / "student-v01-pilot"


def choose_file(page, path: Path) -> None:
    with page.expect_file_chooser() as chooser_info:
        page.locator("#kit-file").click()
    chooser_info.value.set_files(str(path.resolve()))


def assert_safe(page, family: str) -> None:
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


def submit(page, scored: bool) -> None:
    page.locator('[data-served-activity-submit="true"]').click()
    feedback = page.locator("[data-served-feedback]")
    feedback.wait_for()
    assert feedback.get_attribute("data-served-feedback") == ("scored" if scored else "non-scored")
    text = feedback.inner_text()
    if scored:
        assert "Réponse correcte" in text, text
    else:
        assert "Activité terminée" in text, text
        assert "Réponse correcte" not in text and "Pas tout à fait" not in text, text


def answer(page, activity: dict) -> None:
    family = activity["type"]
    if family == "lesson":
        assert page.locator("[data-activity-media] img").count() >= 1
        page.locator('[data-activity-continue="lesson"]').click()
        submit(page, False)
    elif family == "flashcard":
        page.locator('[data-flashcard-reveal="true"]').click()
        page.locator('[data-activity-continue="flashcard"]').click()
        submit(page, False)
    elif family == "matching":
        for pair in activity["matches"]:
            page.locator(f'[data-matching-left="{pair["leftItemId"]}"]').click()
            page.locator(f'[data-matching-right="{pair["rightItemId"]}"]').click()
        submit(page, True)
    elif family == "order":
        desired = activity["correctOrder"]
        rows = page.locator("[data-order-item]")
        for target_index, item_id in enumerate(desired):
            for _ in range(len(desired)):
                current = [rows.nth(i).get_attribute("data-order-item") for i in range(rows.count())]
                index = current.index(item_id)
                if index == target_index:
                    break
                assert index > target_index, (desired, current)
                page.locator(f'[data-order-item="{item_id}"] [data-order-move="up"]').click()
            else:
                raise AssertionError("could not establish correct order")
        submit(page, True)
    elif family == "classify":
        for item in activity["assignments"]:
            page.locator(f'[data-classify-select="{item["itemId"]}"]').select_option(item["bucketId"])
        submit(page, True)
    elif family == "qcm":
        page.locator(f'[data-activity-choice="true"][value="{activity["correctChoiceId"]}"]').check()
        submit(page, True)
    elif family == "fill":
        for item in activity["answers"]:
            page.locator(f'[data-activity-slot="{item["slotId"]}"]').select_option(item["tokenId"])
        submit(page, True)
    elif family == "constructed":
        page.locator("[data-constructed-response]").fill(activity["acceptedResponses"][0])
        submit(page, True)
    else:
        raise AssertionError(family)


def open_app_from_start(page, start: Path) -> None:
    page.goto(start.as_uri())
    page.get_by_text("Student V0.1 — démarrer", exact=True).wait_for()
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    page.locator("#open-learnit").click()
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")


def run_journey(browser, root: Path, kit: dict, viewport: dict[str, int], touch: bool) -> None:
    context = browser.new_context(viewport=viewport, has_touch=touch)
    page = context.new_page()
    external: list[str] = []
    page_errors: list[str] = []
    page.on("request", lambda request: external.append(request.url)
            if request.url.startswith(("http://", "https://")) else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    open_app_from_start(page, root / "START_HERE.html")
    choose_file(page, root / "course.learnit.json")
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_text(kit["courses"][0]["title"], exact=True).wait_for()
    page.get_by_role("button", name="Commencer").click()

    activities = kit["courses"][0]["activities"]
    assert [item["type"] for item in activities] == FAMILIES

    for index, activity in enumerate(activities):
        family = activity["type"]
        page.locator(f'[data-activity-presentation="{family}"]').wait_for()
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        assert_safe(page, family)
        answer(page, activity)

        if family == "lesson":
            page.reload()
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
            page.locator('[data-activity-presentation="flashcard"]').wait_for()
            assert_safe(page, "flashcard")
            continue

        if family == "matching":
            page.locator('[data-served-next-action="true"]').click()
            page.locator('[data-activity-presentation="order"]').wait_for()
            page.get_by_role("button", name="← Bibliothèque").click()
            page.get_by_role("button", name="Reprendre").click()
            page.locator('[data-activity-presentation="order"]').wait_for()
            assert_safe(page, "order")
            continue

        if family == "qcm":
            page.reload()
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
            page.locator('[data-activity-presentation="fill"]').wait_for()
            assert_safe(page, "fill")
            continue

        if index < len(activities) - 1:
            page.locator('[data-served-next-action="true"]').click()

    page.locator('[data-served-next-action="true"]').click()
    page.get_by_text("Cours terminé", exact=True).wait_for()
    page.reload()
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    page.get_by_text("Cours terminé", exact=True).wait_for()
    progress = page.evaluate("async () => (await window.__LEARNIT_NEXT_TEST__.listCourses())[0]?.progress")
    assert progress["isComplete"] is True and progress["completed"] == 8, progress
    assert external == [], external
    assert page_errors == [], page_errors
    context.close()


def run_recovery(browser, root: Path, kit: dict) -> None:
    context = browser.new_context(viewport={"width": 1365, "height": 768})
    page = context.new_page()
    external: list[str] = []
    page.on("request", lambda request: external.append(request.url)
            if request.url.startswith(("http://", "https://")) else None)
    open_app_from_start(page, root / "START_HERE.html")

    with page.expect_file_chooser() as chooser_info:
        page.locator("#kit-file").click()
    chooser_info.value.set_files([])
    assert page.locator("#kit-file").input_value() == ""

    invalid = root.parent / "invalid-job07-r2.json"
    invalid.write_text('{"contract":"learnit.kit.v4"}\n', encoding="utf-8")
    choose_file(page, invalid)
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_role("alert").wait_for()
    assert page.get_by_text(kit["courses"][0]["title"], exact=True).count() == 0

    choose_file(page, root / "course.learnit.json")
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_text(kit["courses"][0]["title"], exact=True).wait_for()

    page.get_by_role("button", name="Réinitialiser les données locales").click()
    page.get_by_role("button", name="Confirmer la réinitialisation").click()
    page.get_by_text("Bibliothèque vide", exact=True).wait_for()

    choose_file(page, root / "course.learnit.json")
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_text(kit["courses"][0]["title"], exact=True).wait_for()
    page.get_by_role("button", name="Commencer").click()
    page.locator('[data-activity-presentation="lesson"]').wait_for()
    assert external == [], external
    context.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temporary:
        root = safe_extract(args.package, Path(temporary))
        manifest = json.loads((root / "pilot_manifest.json").read_text(encoding="utf-8"))
        assert manifest["start"]["mode"] == "DIRECT_FILE"
        kit = json.loads((root / "course.learnit.json").read_text(encoding="utf-8"))

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            run_recovery(browser, root, kit)
            run_journey(browser, root, kit, {"width": 1365, "height": 768}, False)
            run_journey(browser, root, kit, {"width": 390, "height": 844}, True)
            browser.close()

    print("START_MODE=DIRECT_FILE")
    print(f"LEARNER_START_ACTIONS={LEARNER_START_ACTIONS}")
    print("STUDENT_V01_JOB07_R2_RECOVERY=PASS")
    print("STUDENT_V01_JOB07_R2_OFFLINE_NO_REMOTE=PASS")
    print("STUDENT_V01_JOB07_R2_REAL_PACKAGED_V4_JOURNEY=PASS")
    print("STUDENT_V01_JOB07_R2_DESKTOP=PASS")
    print("STUDENT_V01_JOB07_R2_MOBILE=PASS")
    print("STUDENT_V01_JOB07_R2_RELOAD_RESUME=PASS")
    print("STUDENT_V01_JOB07_R2_COMPLETION=PASS")
    print("STUDENT_V01_JOB07_R2_SECRET_BOUNDARY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
