#!/usr/bin/env python3
"""Accessible black-box browser tests for the bounded Learn-it successor slice.

Setup and observation may use window.__LEARNIT_NEXT_TEST__, but import, course start,
QCM/fill answers, navigation and reset are exercised through visible controls. The
suite avoids implementation module names and requires accessible roles or explicit
contract identifiers rather than brittle CSS structure.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
import threading
import unicodedata
import unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import Locator, sync_playwright
except ImportError:  # pragma: no cover - dependency finding
    Locator = Any  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "contracts" / "fixtures"
VALID_PATH = FIXTURE_DIR / "v2-valid-minimal.json"
LEGACY_PATH = FIXTURE_DIR / "v2-invalid-legacy.json"
DEFAULT_ARTIFACT = ROOT / "apps" / "learnit-next" / "dist" / "learnit-next.html"

IMPORT_NAMES = re.compile(r"import|installer|ajouter|charger|load", re.I)
START_NAMES = re.compile(r"commencer|démarrer|ouvrir|start|begin|apprendre|continuer|continue", re.I)
VALIDATE_NAMES = re.compile(r"valider|vérifier|soumettre|check|submit|confirm", re.I)
NEXT_NAMES = re.compile(r"suivant|continuer|next|continue", re.I)
RESET_NAMES = re.compile(r"réinitialiser|effacer|reset|clear", re.I)
EMPTY_NAMES = re.compile(r"bibliothèque.*vide|aucun.*cours|no courses|empty library|import", re.I)
BLANK_NAMES = re.compile(r"slot|blanc|blank|vide|position|réponse|answer", re.I)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: Any) -> None:
        return


@contextmanager
def artifact_server(artifact: Path):
    handler = partial(QuietHandler, directory=str(artifact.parent))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/{artifact.name}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalise(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise TypeError("floats are outside the canonical profile")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalise(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalised_key = unicodedata.normalize("NFC", key)
            if normalised_key in result:
                raise ValueError("normalised key collision")
            result[normalised_key] = _normalise(item)
        return result
    raise TypeError(type(value).__name__)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalise(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: dict[str, Any], field: str) -> str:
    payload = {key: item for key, item in value.items() if key != field}
    return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def recompute(package: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(package)
    for course in result["courses"]:
        for activity in course["activities"]:
            activity["activityRevisionDigest"] = digest(activity, "activityRevisionDigest")
        course["courseRevisionDigest"] = digest(course, "courseRevisionDigest")
    result["packageRevisionDigest"] = digest(result, "packageRevisionDigest")
    return result


def reordered_qcm_fixture(valid: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(valid)
    qcm = result["courses"][0]["activities"][0]
    qcm["choices"].reverse()
    qcm["activityRevisionId"] = "44444444-4444-4444-8444-444444444449"
    result["courses"][0]["courseRevisionId"] = "22222222-2222-4222-8222-222222222229"
    result["packageRevisionId"] = "11111111-1111-4111-8111-111111111119"
    result["title"] = "Fixture QCM réordonné"
    return recompute(result)


class BrowserVerticalSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        artifact = Path(os.environ.get("LEARNIT_NEXT_ARTIFACT", DEFAULT_ARTIFACT))
        if not artifact.exists():
            raise unittest.SkipTest(
                f"WAITING_FOR_INTEGRATION: built artifact absent at {artifact}"
            )
        if sync_playwright is None:
            raise unittest.SkipTest("DEPENDENCY: install Playwright for browser evidence")
        cls.valid = load_json(VALID_PATH)
        cls.legacy = load_json(LEGACY_PATH)
        cls.reordered = reordered_qcm_fixture(cls.valid)
        cls._server = artifact_server(artifact)
        cls.url = cls._server.__enter__()
        cls._playwright = sync_playwright().start()
        try:
            cls.browser = cls._playwright.chromium.launch(headless=True)
        except Exception as error:  # pragma: no cover - environment dependent
            cls._playwright.stop()
            cls._server.__exit__(None, None, None)
            raise unittest.SkipTest(f"DEPENDENCY: Chromium unavailable: {error}") from error

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "browser"):
            cls.browser.close()
        if hasattr(cls, "_playwright"):
            cls._playwright.stop()
        if hasattr(cls, "_server"):
            cls._server.__exit__(None, None, None)

    def setUp(self) -> None:
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.open_app()
        self.api("resetNextData")
        self.page.reload(wait_until="domcontentloaded")
        self.wait_api()

    def tearDown(self) -> None:
        self.context.close()

    def open_app(self) -> None:
        self.page.goto(self.url, wait_until="domcontentloaded")
        self.wait_api()

    def wait_api(self) -> None:
        self.page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

    def api(self, operation: str, *args: Any) -> Any:
        return self.page.evaluate(
            """async ({operation,args}) => {
              const api = window.__LEARNIT_NEXT_TEST__;
              if (!api || typeof api[operation] !== 'function') {
                throw new Error(`Missing public test operation: ${operation}`);
              }
              return await api[operation](...args);
            }""",
            {"operation": operation, "args": list(args)},
        )

    def first_visible(self, locator: Locator) -> Locator | None:
        for index in range(locator.count()):
            candidate = locator.nth(index)
            if candidate.is_visible():
                return candidate
        return None

    def click_named_control(self, pattern: re.Pattern[str], required: bool = True) -> bool:
        for role in ("button", "link"):
            control = self.first_visible(self.page.get_by_role(role, name=pattern))
            if control is not None:
                control.click()
                return True
        if required:
            self.fail(f"absence of proof: no visible accessible control named /{pattern.pattern}/")
        return False

    def import_through_visible_ui(self, payload: Any) -> None:
        text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        file_inputs = self.page.locator('input[type="file"]')
        visible_input = self.first_visible(file_inputs)
        if visible_input is not None:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", encoding="utf-8", delete=False
            ) as handle:
                handle.write(text)
                path = Path(handle.name)
            try:
                visible_input.set_input_files(str(path))
            finally:
                path.unlink(missing_ok=True)
            self.click_named_control(IMPORT_NAMES, required=False)
        else:
            textarea = self.first_visible(self.page.locator("textarea"))
            if textarea is None:
                self.click_named_control(IMPORT_NAMES)
                visible_input = self.first_visible(self.page.locator('input[type="file"]'))
                textarea = self.first_visible(self.page.locator("textarea"))
            if visible_input is not None:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", encoding="utf-8", delete=False
                ) as handle:
                    handle.write(text)
                    path = Path(handle.name)
                try:
                    visible_input.set_input_files(str(path))
                finally:
                    path.unlink(missing_ok=True)
                self.click_named_control(IMPORT_NAMES, required=False)
            elif textarea is not None:
                textarea.fill(text)
                self.click_named_control(IMPORT_NAMES)
            else:
                self.fail("absence of proof: import is not available through visible UI")

    def wait_course_count(self, expected: int) -> list[Any]:
        self.page.wait_for_function(
            """async expected => {
              const api = window.__LEARNIT_NEXT_TEST__;
              const courses = await api.listCourses();
              return Array.isArray(courses) && courses.length === expected;
            }""",
            expected,
        )
        courses = self.api("listCourses")
        self.assertEqual(expected, len(courses))
        return courses

    def start_course_visibly(self, course_title: str, first_prompt: str) -> None:
        title_control = None
        for role in ("button", "link"):
            title_control = self.first_visible(
                self.page.get_by_role(role, name=re.compile(re.escape(course_title), re.I))
            )
            if title_control is not None:
                title_control.click()
                break
        self.click_named_control(START_NAMES, required=title_control is None)
        self.page.get_by_text(first_prompt, exact=False).first.wait_for(state="visible")

    def assert_no_qcm_preselection(self) -> None:
        self.assertEqual(0, self.page.locator('input[type="radio"]:checked').count())
        self.assertEqual(0, self.page.locator('[role="radio"][aria-checked="true"]').count())
        self.assertEqual(0, self.page.locator('[aria-pressed="true"][data-choice-id]').count())

    def answer_qcm_visibly(self, label: str) -> None:
        radio = self.first_visible(self.page.get_by_role("radio", name=re.compile(f"^{re.escape(label)}$", re.I)))
        if radio is not None:
            radio.check() if radio.get_attribute("type") == "radio" else radio.click()
        else:
            choice = self.first_visible(
                self.page.get_by_role("button", name=re.compile(f"^{re.escape(label)}$", re.I))
            )
            if choice is None:
                choice = self.first_visible(
                    self.page.locator(f'[data-choice-id]')
                    .filter(has_text=re.compile(f"^{re.escape(label)}$", re.I))
                )
            if choice is None:
                self.fail("absence of proof: QCM choices are not exposed accessibly")
            choice.click()
        self.click_named_control(VALIDATE_NAMES)

    def go_next(self) -> None:
        self.click_named_control(NEXT_NAMES)

    def answer_fill_visibly(self, activity: dict[str, Any]) -> None:
        token = activity["tokens"][0]
        token_label = token["label"]
        slots = [
            segment["slotId"] for segment in activity["segments"] if "slotId" in segment
        ]

        selects = self.page.locator("select")
        visible_selects = [
            selects.nth(index) for index in range(selects.count()) if selects.nth(index).is_visible()
        ]
        if len(visible_selects) >= len(slots):
            for select in visible_selects[: len(slots)]:
                try:
                    select.select_option(value=token["tokenId"])
                except Exception:
                    select.select_option(label=token_label)
            self.click_named_control(VALIDATE_NAMES)
            return

        slot_controls: list[Locator] = []
        for slot_id in slots:
            explicit = self.first_visible(self.page.locator(f'[data-slot-id="{slot_id}"]'))
            if explicit is not None:
                slot_controls.append(explicit)
        if len(slot_controls) < len(slots):
            generic = self.page.get_by_role("button", name=BLANK_NAMES)
            slot_controls = [
                generic.nth(index) for index in range(generic.count()) if generic.nth(index).is_visible()
            ][: len(slots)]
        if len(slot_controls) < len(slots):
            self.fail("absence of proof: fill slots are not exposed as accessible controls")

        for index, slot in enumerate(slot_controls):
            token_control = self.first_visible(
                self.page.get_by_role("button", name=re.compile(f"^{re.escape(token_label)}$", re.I))
            )
            if token_control is None or token_control.is_disabled():
                self.fail(
                    f"maxUses violation: reusable token unavailable before slot {index + 1}"
                )
            try:
                slot.click()
                token_control.click()
            except Exception:
                token_control.click()
                slot.click()
        self.click_named_control(VALIDATE_NAMES)

    def test_empty_state_and_minimum_accessibility(self) -> None:
        self.assertEqual([], self.api("listCourses"))
        self.assertIsNotNone(self.first_visible(self.page.get_by_text(EMPTY_NAMES)))
        self.assertGreaterEqual(self.page.get_by_role("main").count(), 1)
        self.assertGreaterEqual(self.page.get_by_role("heading", level=1).count(), 1)
        unnamed = self.page.locator("button:visible").evaluate_all(
            "els => els.filter(el => !(el.innerText || el.getAttribute('aria-label') || el.title).trim()).length"
        )
        self.assertEqual(0, unnamed, "visible buttons must have accessible names")

    def test_complete_visible_vertical_slice_persists_after_refresh_and_new_page(self) -> None:
        self.import_through_visible_ui(self.valid)
        courses = self.wait_course_count(1)
        course = self.valid["courses"][0]
        self.page.get_by_text(course["title"], exact=False).first.wait_for(state="visible")
        self.start_course_visibly(course["title"], course["activities"][0]["prompt"])

        qcm = course["activities"][0]
        self.assert_no_qcm_preselection()
        correct = next(
            choice["label"] for choice in qcm["choices"]
            if choice["choiceId"] == qcm["correctChoiceId"]
        )
        self.answer_qcm_visibly(correct)
        self.go_next()

        fill = course["activities"][1]
        self.page.get_by_text(fill["prompt"], exact=False).first.wait_for(state="visible")
        self.answer_fill_visibly(fill)

        course_install_id = courses[0].get("courseInstallId")
        self.assertTrue(course_install_id, courses[0])
        progress_before = self.api("getProgress", course_install_id)
        self.assertTrue(progress_before, "progress must be observable after answers")

        self.page.reload(wait_until="domcontentloaded")
        self.wait_api()
        self.assertEqual(1, len(self.api("listCourses")))
        self.assertEqual(progress_before, self.api("getProgress", course_install_id))

        reopened = self.context.new_page()
        reopened.goto(self.url, wait_until="domcontentloaded")
        reopened.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        reopened_progress = reopened.evaluate(
            "async id => await window.__LEARNIT_NEXT_TEST__.getProgress(id)",
            course_install_id,
        )
        self.assertEqual(progress_before, reopened_progress)
        reopened.close()

    def test_legacy_import_is_rejected_visibly_without_partial_library_write(self) -> None:
        self.import_through_visible_ui(self.legacy)
        self.page.wait_for_timeout(250)
        self.assertEqual([], self.api("listCourses"))
        body = self.page.locator("body").inner_text().lower()
        self.assertRegex(body, r"contrat|contract|version|legacy|learnit\.kit\.v2")

    def test_malformed_json_is_rejected_visibly_without_partial_write(self) -> None:
        self.import_through_visible_ui('{"contract":"learnit.kit.v2", invalid-json')
        self.page.wait_for_timeout(250)
        self.assertEqual([], self.api("listCourses"))
        body = self.page.locator("body").inner_text().lower()
        self.assertRegex(body, r"json|syntaxe|syntax|invalide|invalid|parse")

    def test_reordered_qcm_choices_keep_choice_id_correction_semantics(self) -> None:
        self.import_through_visible_ui(self.reordered)
        courses = self.wait_course_count(1)
        course = self.reordered["courses"][0]
        qcm = course["activities"][0]
        self.start_course_visibly(course["title"], qcm["prompt"])
        self.assert_no_qcm_preselection()
        correct_label = next(
            choice["label"] for choice in qcm["choices"]
            if choice["choiceId"] == qcm["correctChoiceId"]
        )
        self.answer_qcm_visibly(correct_label)
        progress = self.api("getProgress", courses[0]["courseInstallId"])
        self.assertRegex(json.dumps(progress).lower(), r"true|correct|completed")

    def test_visible_reset_removes_successor_library_only(self) -> None:
        self.import_through_visible_ui(self.valid)
        self.wait_course_count(1)
        self.click_named_control(RESET_NAMES)
        confirm = self.first_visible(
            self.page.get_by_role("button", name=re.compile(r"confirmer|oui|confirm|yes", re.I))
        )
        if confirm is not None:
            confirm.click()
        self.wait_course_count(0)
        self.assertIsNotNone(self.first_visible(self.page.get_by_text(EMPTY_NAMES)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
