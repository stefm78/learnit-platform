#!/usr/bin/env python3
"""Browser qualification of the exact V5 learner package. Machine smoke only."""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

FORBIDDEN = {"correctChoiceId", "answers", "acceptedResponses", "matches", "correctOrder", "assignments"}

def safe_extract(package: Path, root: Path) -> Path:
    with zipfile.ZipFile(package) as archive:
        for info in archive.infolist():
            p = Path(info.filename)
            assert not p.is_absolute() and ".." not in p.parts
        archive.extractall(root)
    return root

def choose_file(page, path: Path) -> None:
    page.locator("#kit-file").set_input_files(str(path.resolve()))

def assert_no_secret_projection(page) -> None:
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
      return {keys: activity ? Object.keys(activity).sort() : [], hits};
    }""", sorted(FORBIDDEN))
    assert snapshot["keys"] == ["activityRevisionId", "presentation"], snapshot
    assert snapshot["hits"] == [], snapshot

def submit(page, scored: bool) -> None:
    page.locator('[data-served-activity-submit="true"]').click()
    feedback = page.locator("[data-served-feedback]")
    feedback.wait_for()
    assert feedback.get_attribute("data-served-feedback") == ("scored" if scored else "non-scored")

def answer(page, activity: dict) -> None:
    family = activity["type"]
    if family == "lesson":
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
            for _ in range(len(desired) + 1):
                current = [rows.nth(i).get_attribute("data-order-item") for i in range(rows.count())]
                index = current.index(item_id)
                if index == target_index:
                    break
                assert index > target_index, (desired, current)
                page.locator(f'[data-order-item="{item_id}"] [data-order-move="up"]').click()
            else:
                raise AssertionError("could not establish order")
        submit(page, True)
    elif family == "qcm":
        page.locator(f'[data-activity-choice="true"][value="{activity["correctChoiceId"]}"]').check()
        submit(page, True)
    else:
        raise AssertionError(f"unexpected V5 pilot activity family {family}")

def open_start(page, root: Path) -> None:
    page.goto((root / "START_HERE.html").as_uri())
    page.get_by_text("Démarrer le cours", exact=True).wait_for()
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    page.locator("#open-learnit").click()
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

def run_import_start(browser, root: Path, kit: dict, viewport: dict[str,int], touch: bool) -> None:
    context = browser.new_context(viewport=viewport, has_touch=touch)
    page = context.new_page()
    external: list[str] = []
    errors: list[str] = []
    page.on("request", lambda request: external.append(request.url) if request.url.startswith(("http://","https://")) else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    open_start(page, root)
    assert page.locator("#kit-file").input_value() == ""
    choose_file(page, root / "course.learnit.json")
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_text(kit["courses"][0]["title"], exact=True).wait_for()
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("button", name="Commencer").click()
    page.locator('[data-activity-presentation="lesson"]').wait_for()
    assert_no_secret_projection(page)
    assert external == [], external
    assert errors == [], errors
    context.close()

def run_recovery(browser, root: Path, kit: dict) -> None:
    context = browser.new_context(viewport={"width":1365,"height":768})
    page = context.new_page()
    external: list[str] = []
    page.on("request", lambda request: external.append(request.url) if request.url.startswith(("http://","https://")) else None)
    open_start(page, root)
    choose_file(page, root / "course.learnit.json")
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_text(kit["courses"][0]["title"], exact=True).wait_for()
    page.get_by_text("Gérer la bibliothèque", exact=True).click()
    page.get_by_role("button", name="Réinitialiser les données locales").click()
    page.get_by_role("button", name="Confirmer la réinitialisation").click()
    page.get_by_text("Importer votre premier cours", exact=True).wait_for()
    choose_file(page, root / "course.learnit.json")
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_text(kit["courses"][0]["title"], exact=True).wait_for()
    page.get_by_role("button", name="Commencer").click()
    page.locator('[data-activity-presentation="lesson"]').wait_for()
    assert external == [], external
    context.close()

def run_full_journey(browser, root: Path, kit: dict) -> None:
    context = browser.new_context(viewport={"width":1365,"height":768})
    page = context.new_page()
    external: list[str] = []
    errors: list[str] = []
    page.on("request", lambda request: external.append(request.url) if request.url.startswith(("http://","https://")) else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    open_start(page, root)
    choose_file(page, root / "course.learnit.json")
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_text(kit["courses"][0]["title"], exact=True).wait_for()
    page.get_by_role("button", name="Commencer").click()
    activities = kit["courses"][0]["activities"]
    assert len(activities) == 10
    for index, activity in enumerate(activities):
        page.locator(f'[data-activity-presentation="{activity["type"]}"]').wait_for()
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        assert_no_secret_projection(page)
        answer(page, activity)
        if index < len(activities)-1:
            page.locator('[data-served-next-action="true"]').click()
    page.locator('[data-served-next-action="true"]').click()
    page.get_by_text("Cours terminé", exact=True).wait_for()
    assert external == [], external
    assert errors == [], errors
    context.close()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learner-package", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as td:
        root = safe_extract(args.learner_package, Path(td))
        kit = json.loads((root / "course.learnit.json").read_text(encoding="utf-8"))
        assert kit["contract"] == "learnit.kit.v5"
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            run_import_start(browser, root, kit, {"width":1365,"height":768}, False)
            run_import_start(browser, root, kit, {"width":390,"height":844}, True)
            run_recovery(browser, root, kit)
            run_full_journey(browser, root, kit)
            browser.close()
    print("V5_PACKAGE_IMPORT=PASS")
    print("DESKTOP_START=PASS")
    print("MOBILE_390x844_START=PASS")
    print("RECOVERY_RESET=PASS")
    print("NO_HORIZONTAL_OVERFLOW=PASS")
    print("NO_REMOTE_NETWORK=PASS")
    print("LEARNER_SECRET_PROJECTION=PASS")
    print("MACHINE_SMOKE_ONLY_NOT_A_REAL_STUDENT_SESSION")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
