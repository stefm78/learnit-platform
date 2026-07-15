#!/usr/bin/env python3
"""Keyboard-first visible browser proof for the Learn-it successor slice."""
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
except ImportError:
    Locator, sync_playwright = Any, None

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "contracts" / "fixtures"
VALID_PATH = FIXTURES / "v2-valid-minimal.json"
LEGACY_PATH = FIXTURES / "v2-invalid-legacy.json"
DEFAULT_ARTIFACT = ROOT / "apps" / "learnit-next" / "dist" / "learnit-next.html"
STRICT = os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION") == "1"

IMPORT_NAMES = re.compile(r"importer|import|installer|ajouter|charger|load", re.I)
START_NAMES = re.compile(
    r"commencer|démarrer|ouvrir|start|begin|apprendre|continuer|continue", re.I
)
VALIDATE_NAMES = re.compile(
    r"valider|vérifier|soumettre|check|submit|confirm", re.I
)
NEXT_NAMES = re.compile(r"suivant|continuer|next|continue", re.I)
RESET_NAMES = re.compile(r"réinitialiser|effacer|reset|clear", re.I)
EMPTY_NAMES = re.compile(
    r"bibliothèque.*vide|aucun.*cours|no courses|empty library", re.I
)
SUCCESS_FEEDBACK = (
    r"\bcorrect(?:e|es)?\b|bonne réponse|bravo|réussi|success|exact|\bjuste\b"
)

NEXT_SNAPSHOT = r"""async name => {
  if (typeof indexedDB.databases !== 'function') {
    throw new Error('Chromium indexedDB.databases() is required for non-creating snapshots');
  }
  const names = (await indexedDB.databases()).map(item => item.name).filter(Boolean);
  if (!names.includes(name)) return null;
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open(name);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  const stores = {};
  for (const storeName of Array.from(db.objectStoreNames).sort()) {
    stores[storeName] = await new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readonly');
      const store = tx.objectStore(storeName);
      const keys = store.getAllKeys();
      const records = store.getAll();
      tx.oncomplete = () => resolve({
        keyPath:store.keyPath,
        autoIncrement:store.autoIncrement,
        indexes:Array.from(store.indexNames).sort(),
        keys:keys.result,
        records:records.result
      });
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error || new Error('snapshot transaction aborted'));
    });
  }
  const result = {version:db.version, stores};
  db.close();
  return result;
}"""

START_FEEDBACK_PROBE = r"""config => {
  if (window.__qaFeedbackProbe?.observer) {
    window.__qaFeedbackProbe.observer.disconnect();
  }
  const regex = new RegExp(config.pattern, 'i');
  const text = element => String(
    element.innerText || element.textContent || ''
  ).trim();
  const exposed = element => {
    if (!(element instanceof Element) || element.hidden ||
        element.getAttribute('aria-hidden') === 'true') return false;
    const style = getComputedStyle(element);
    return style.display !== 'none' && style.visibility !== 'hidden';
  };
  const visible = element => {
    if (!exposed(element)) return false;
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };
  const semantic = element => element.matches(
    '[role="alert"],[role="status"],[aria-live]:not([aria-live="off"])'
  );
  const candidatesFrom = node => {
    const root = node.nodeType === Node.ELEMENT_NODE
      ? node : node.parentElement;
    if (!root) return [];
    const found = [];
    const add = element => {
      if (!(element instanceof Element)) return;
      if (semantic(element) && exposed(element)) found.push(element);
      if (!config.semanticOnly && element.children.length === 0 && visible(element)) {
        found.push(element);
      }
    };
    add(root);
    for (const element of root.querySelectorAll(
      '[role="alert"],[role="status"],[aria-live]:not([aria-live="off"]),*'
    )) add(element);
    return Array.from(new Set(found));
  };
  const state = {matched:null, observer:null};
  state.observer = new MutationObserver(records => {
    for (const record of records) {
      const nodes = [record.target, ...Array.from(record.addedNodes || [])];
      for (const node of nodes) {
        for (const element of candidatesFrom(node)) {
          const value = text(element);
          if (value && regex.test(value)) {
            state.matched = {
              text:value,
              semantic:semantic(element),
              announced:semantic(element),
              visible:visible(element)
            };
            return;
          }
        }
      }
    }
  });
  state.observer.observe(document.body, {
    subtree:true,
    childList:true,
    characterData:true
  });
  window.__qaFeedbackProbe = state;
}"""


def require_or_skip(condition: bool, message: str) -> None:
    if condition:
        return
    if STRICT:
        raise RuntimeError(message)
    raise unittest.SkipTest(message)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return


@contextmanager
def artifact_server(artifact: Path):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(artifact.parent))
    )
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


def normalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise TypeError("floats are outside the canonical profile")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in result:
                raise ValueError("normalized key collision")
            result[normalized_key] = normalize(item)
        return result
    raise TypeError(type(value).__name__)


def canonical(value: Any) -> bytes:
    return json.dumps(
        normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value: dict[str, Any], field: str) -> str:
    payload = {key: item for key, item in value.items() if key != field}
    return "sha256:" + hashlib.sha256(canonical(payload)).hexdigest()


def recompute(package: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(package)
    for course in result["courses"]:
        for activity in course["activities"]:
            activity["activityRevisionDigest"] = digest(
                activity, "activityRevisionDigest"
            )
        course["courseRevisionDigest"] = digest(course, "courseRevisionDigest")
    result["packageRevisionDigest"] = digest(result, "packageRevisionDigest")
    return result


def reordered_qcm_fixture(valid: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(valid)
    qcm = result["courses"][0]["activities"][0]
    qcm["choices"].reverse()
    qcm["activityRevisionId"] = "44444444-4444-4444-8444-444444444449"
    result["courses"][0]["courseRevisionId"] = (
        "22222222-2222-4222-8222-222222222229"
    )
    result["packageRevisionId"] = "11111111-1111-4111-8111-111111111119"
    result["title"] = "Fixture QCM réordonné"
    return recompute(result)


def find_activity_record(value: Any, activity_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("activityRevisionId") == activity_id:
            return value
        for item in value.values():
            found = find_activity_record(item, activity_id)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_activity_record(item, activity_id)
            if found is not None:
                return found
    return None


def slot_mapping(record: dict[str, Any]) -> dict[str, str] | None:
    observed = (
        record.get("answers")
        or record.get("slotAnswers")
        or record.get("responses")
    )
    if isinstance(observed, dict):
        return {str(key): str(value) for key, value in observed.items()}
    if not isinstance(observed, list):
        return None
    result: dict[str, str] = {}
    for item in observed:
        if not isinstance(item, dict):
            return None
        slot_id, token_id = item.get("slotId"), item.get("tokenId")
        if not isinstance(slot_id, str) or not isinstance(token_id, str):
            return None
        if slot_id in result:
            return None
        result[slot_id] = token_id
    return result


class BrowserVerticalSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        artifact = Path(os.environ.get("LEARNIT_NEXT_ARTIFACT", DEFAULT_ARTIFACT))
        require_or_skip(
            artifact.exists(),
            f"WAITING_FOR_INTEGRATION: built artifact absent at {artifact}",
        )
        require_or_skip(sync_playwright is not None, "DEPENDENCY: install Playwright")
        cls.valid = load_json(VALID_PATH)
        cls.legacy = load_json(LEGACY_PATH)
        cls.reordered = reordered_qcm_fixture(cls.valid)
        cls.server = artifact_server(artifact)
        cls.url = cls.server.__enter__()
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except Exception as error:
            cls.playwright.stop()
            cls.server.__exit__(None, None, None)
            require_or_skip(False, f"DEPENDENCY: Chromium unavailable: {error}")

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "browser"):
            cls.browser.close()
        if hasattr(cls, "playwright"):
            cls.playwright.stop()
        if hasattr(cls, "server"):
            cls.server.__exit__(None, None, None)

    def setUp(self) -> None:
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.goto(self.url, wait_until="domcontentloaded")
        self.wait_api()
        self.api("resetNextData")
        self.page.reload(wait_until="domcontentloaded")
        self.wait_api()

    def tearDown(self) -> None:
        self.context.close()

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

    def snapshot_next(self) -> Any:
        return self.page.evaluate(NEXT_SNAPSHOT, "learnit_next_v1")

    def first_visible(self, locator: Locator) -> Locator | None:
        for index in range(locator.count()):
            candidate = locator.nth(index)
            if candidate.is_visible():
                return candidate
        return None

    def visible_controls(self, locator: Locator) -> list[Locator]:
        return [
            locator.nth(index)
            for index in range(locator.count())
            if locator.nth(index).is_visible()
        ]

    def assert_focused(self, control: Locator) -> None:
        self.assertTrue(
            control.evaluate(
                "element => element === document.activeElement || "
                "element.contains(document.activeElement)"
            ),
            "keyboard proof requires focus on the activated control",
        )

    def activate(self, control: Locator, key: str = "Enter") -> None:
        control.focus()
        self.assert_focused(control)
        self.page.keyboard.press(key)

    def activate_named(self, pattern: re.Pattern[str]) -> Locator:
        for role in ("button", "link"):
            control = self.first_visible(self.page.get_by_role(role, name=pattern))
            if control is not None:
                self.activate(control)
                return control
        self.fail(f"no accessible visible control named /{pattern.pattern}/")

    def start_feedback_probe(
        self, pattern: str, *, semantic_only: bool = False
    ) -> None:
        self.page.evaluate(
            START_FEEDBACK_PROBE,
            {"pattern": pattern, "semanticOnly": semantic_only},
        )

    def wait_feedback(self, *, require_semantic: bool = False) -> str:
        self.page.wait_for_function(
            """requireSemantic => {
              const result = window.__qaFeedbackProbe?.matched;
              if (!result || (!result.visible && !result.announced)) return false;
              if (requireSemantic && !result.semantic) return false;
              const exposed = element => {
                if (element.hidden || element.getAttribute('aria-hidden') === 'true') return false;
                const style = getComputedStyle(element);
                return style.display !== 'none' && style.visibility !== 'hidden';
              };
              return !Array.from(document.querySelectorAll('[aria-busy="true"]'))
                .some(exposed);
            }""",
            require_semantic,
        )
        matched = self.page.evaluate(
            """() => {
              const probe = window.__qaFeedbackProbe;
              const result = probe.matched;
              probe.observer.disconnect();
              return result;
            }"""
        )
        if require_semantic:
            self.assertTrue(matched["semantic"], matched)
        self.assertTrue(matched["visible"] or matched["announced"], matched)
        return matched["text"]

    def import_trigger(self) -> Locator:
        trigger = self.first_visible(self.page.get_by_role("button", name=IMPORT_NAMES))
        if trigger is None:
            self.fail("import trigger lacks an accessible button")
        return trigger

    def wait_import_idle(self) -> None:
        trigger = self.import_trigger()
        self.page.wait_for_function(
            "element => !element.disabled && "
            "element.getAttribute('aria-disabled') !== 'true'",
            trigger.element_handle(),
        )

    def import_through_keyboard(self, payload: Any) -> None:
        text = payload if isinstance(payload, str) else json.dumps(
            payload, ensure_ascii=False
        )
        trigger = self.import_trigger()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        ) as handle:
            handle.write(text)
            path = Path(handle.name)
        try:
            trigger.focus()
            self.assert_focused(trigger)
            trigger.evaluate("element => { window.__qaImportTrigger = element; }")
            with self.page.expect_file_chooser() as event:
                self.page.keyboard.press("Enter")
            event.value.set_files(str(path))
            self.page.wait_for_function(
                """async pattern => {
                  if ((await window.__LEARNIT_NEXT_TEST__.listCourses()).length > 0) return true;
                  if (window.__qaFeedbackProbe?.matched) return true;
                  const regex = new RegExp(pattern, 'i');
                  return Array.from(document.querySelectorAll('button')).some(button => {
                    if (button === window.__qaImportTrigger || button.hidden || button.disabled ||
                        button.getAttribute('aria-disabled') === 'true') return false;
                    const style = getComputedStyle(button);
                    if (style.display === 'none' || style.visibility === 'hidden') return false;
                    const name = button.getAttribute('aria-label') || button.innerText || '';
                    return regex.test(name);
                  });
                }""",
                f"{IMPORT_NAMES.pattern}|{VALIDATE_NAMES.pattern}",
            )
            confirmation = None
            for pattern in (IMPORT_NAMES, VALIDATE_NAMES):
                for candidate in self.visible_controls(
                    self.page.get_by_role("button", name=pattern)
                ):
                    if candidate.evaluate(
                        "element => element !== window.__qaImportTrigger"
                    ) and not candidate.is_disabled():
                        confirmation = candidate
                        break
                if confirmation is not None:
                    break
            if confirmation is not None:
                self.activate(confirmation)
        finally:
            path.unlink(missing_ok=True)

    def wait_courses(self, expected: int) -> list[Any]:
        self.page.wait_for_function(
            "async expected => (await window.__LEARNIT_NEXT_TEST__.listCourses()).length === expected",
            expected,
        )
        courses = self.api("listCourses")
        self.assertEqual(expected, len(courses))
        return courses

    def start_course(self, title: str, first_prompt: str) -> None:
        title_control = None
        for role in ("button", "link"):
            title_control = self.first_visible(
                self.page.get_by_role(role, name=re.compile(re.escape(title), re.I))
            )
            if title_control is not None:
                break
        if title_control is not None:
            self.activate(title_control)
        else:
            self.activate_named(START_NAMES)
        self.page.get_by_text(first_prompt, exact=False).first.wait_for(state="visible")

    def assert_no_qcm_preselection(self, activity: dict[str, Any]) -> None:
        for choice in activity["choices"]:
            label = re.compile(f"^{re.escape(choice['label'])}$", re.I)
            control = self.first_visible(self.page.get_by_role("radio", name=label))
            if control is None:
                control = self.first_visible(self.page.get_by_role("button", name=label))
            if control is None:
                self.fail(f"choice {choice['choiceId']} lacks accessible role/name")
            if control.get_attribute("type") == "radio":
                self.assertFalse(control.is_checked())
            self.assertNotEqual("true", control.get_attribute("aria-checked"))
            self.assertNotEqual("true", control.get_attribute("aria-pressed"))
        if self.page.evaluate(
            "() => typeof window.__LEARNIT_NEXT_TEST__.getCurrentProgress === 'function'"
        ):
            self.assertIsNone(
                find_activity_record(
                    self.api("getCurrentProgress"), activity["activityRevisionId"]
                )
            )

    def answer_qcm_with_keyboard(self, label: str) -> None:
        exact = re.compile(f"^{re.escape(label)}$", re.I)
        control = self.first_visible(self.page.get_by_role("radio", name=exact))
        if control is None:
            control = self.first_visible(self.page.get_by_role("button", name=exact))
        if control is None:
            self.fail("QCM choice lacks accessible radio/button role and name")
        self.activate(control, "Space")
        self.activate_named(VALIDATE_NAMES)

    def choose_option_with_keyboard(
        self, control: Locator, token_id: str, token_label: str
    ) -> None:
        tag_name = control.evaluate("element => element.tagName.toLowerCase()")
        if tag_name == "select":
            options = control.evaluate(
                "element => Array.from(element.options).map(option => "
                "({value:option.value,label:option.textContent.trim()}))"
            )
            target = next(
                (
                    index
                    for index, option in enumerate(options)
                    if option["value"] == token_id or option["label"] == token_label
                ),
                None,
            )
            self.assertIsNotNone(target, f"token {token_id} absent from options")
            control.focus()
            self.assert_focused(control)
            self.page.keyboard.press("Home")
            for _ in range(int(target)):
                self.page.keyboard.press("ArrowDown")
            self.page.keyboard.press("Enter")
            selected = control.evaluate(
                "element => ({value:element.value,"
                "label:element.options[element.selectedIndex].textContent.trim()})"
            )
            self.assertTrue(
                selected["value"] == token_id or selected["label"] == token_label,
                selected,
            )
            return
        control.focus()
        self.assert_focused(control)
        self.page.keyboard.press("Enter")
        self.page.keyboard.type(token_label)
        self.page.keyboard.press("Enter")
        selected = control.evaluate(
            "element => String(element.value || element.innerText || "
            "element.textContent || '').trim()"
        )
        self.assertIn(token_label, selected)

    def answer_fill_with_keyboard(self, activity: dict[str, Any]) -> None:
        slots = [
            segment["slotId"]
            for segment in activity["segments"]
            if "slotId" in segment
        ]
        controls = self.visible_controls(
            self.page.get_by_role("combobox", name=re.compile(r".+"))
        )
        self.assertEqual(len(slots), len(controls), "one named combobox per slot")
        token = activity["tokens"][0]
        for control in controls:
            self.choose_option_with_keyboard(
                control, token["tokenId"], token["label"]
            )
        self.activate_named(VALIDATE_NAMES)

    def assert_activity_success(
        self,
        progress: Any,
        activity: dict[str, Any],
        *,
        selected: str | None = None,
        expected_slots: dict[str, str] | None = None,
    ) -> None:
        record = find_activity_record(progress, activity["activityRevisionId"])
        self.assertIsNotNone(record, progress)
        assert record is not None
        self.assertIs(record.get("correct"), True, record)
        self.assertIs(record.get("completed"), True, record)
        if selected is not None:
            self.assertEqual(selected, record.get("selectedChoiceId"), record)
        if expected_slots is not None:
            self.assertEqual(expected_slots, slot_mapping(record), record)

    def assert_rejection_without_storage_change(
        self, payload: Any, pattern: str
    ) -> str:
        before = self.snapshot_next()
        self.start_feedback_probe(pattern, semantic_only=True)
        self.import_through_keyboard(payload)
        feedback = self.wait_feedback(require_semantic=True)
        self.wait_import_idle()
        self.wait_courses(0)
        self.assertEqual(
            before,
            self.snapshot_next(),
            "rejected visible import left packages/courses/progress/meta records",
        )
        return feedback

    def reset_visible_state(self) -> None:
        self.api("resetNextData")
        self.page.reload(wait_until="domcontentloaded")
        self.wait_api()

    def test_empty_state_and_minimum_accessibility(self) -> None:
        self.assertEqual([], self.api("listCourses"))
        self.assertIsNotNone(self.first_visible(self.page.get_by_text(EMPTY_NAMES)))
        self.assertGreaterEqual(self.page.get_by_role("main").count(), 1)
        self.assertGreaterEqual(self.page.get_by_role("heading", level=1).count(), 1)
        unnamed = self.page.locator("button:visible").evaluate_all(
            "elements => elements.filter(element => "
            "!((element.innerText || element.getAttribute('aria-label') || "
            "element.getAttribute('aria-labelledby') || element.title || '').trim())).length"
        )
        self.assertEqual(0, unnamed)

    def test_complete_visible_vertical_slice_persists_after_refresh_and_new_page(
        self,
    ) -> None:
        self.import_through_keyboard(self.valid)
        courses = self.wait_courses(1)
        course = self.valid["courses"][0]
        self.page.get_by_text(course["title"], exact=False).first.wait_for(
            state="visible"
        )
        self.start_course(course["title"], course["activities"][0]["prompt"])

        qcm = course["activities"][0]
        self.assert_no_qcm_preselection(qcm)
        correct_label = next(
            choice["label"]
            for choice in qcm["choices"]
            if choice["choiceId"] == qcm["correctChoiceId"]
        )
        self.start_feedback_probe(SUCCESS_FEEDBACK)
        self.answer_qcm_with_keyboard(correct_label)
        self.assertRegex(
            self.wait_feedback(), re.compile(SUCCESS_FEEDBACK, re.I)
        )
        self.activate_named(NEXT_NAMES)

        fill = course["activities"][1]
        self.page.get_by_text(fill["prompt"], exact=False).first.wait_for(
            state="visible"
        )
        self.start_feedback_probe(SUCCESS_FEEDBACK)
        self.answer_fill_with_keyboard(fill)
        self.assertRegex(
            self.wait_feedback(), re.compile(SUCCESS_FEEDBACK, re.I)
        )

        course_install_id = courses[0]["courseInstallId"]
        progress = self.api("getProgress", course_install_id)
        self.assert_activity_success(
            progress, qcm, selected=qcm["correctChoiceId"]
        )
        expected_slots = {
            answer["slotId"]: answer["tokenId"] for answer in fill["answers"]
        }
        self.assert_activity_success(
            progress, fill, expected_slots=expected_slots
        )

        self.page.reload(wait_until="domcontentloaded")
        self.wait_api()
        self.assertEqual(progress, self.api("getProgress", course_install_id))
        reopened = self.context.new_page()
        reopened.goto(self.url, wait_until="domcontentloaded")
        reopened.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        reopened_progress = reopened.evaluate(
            "async id => await window.__LEARNIT_NEXT_TEST__.getProgress(id)",
            course_install_id,
        )
        self.assertEqual(progress, reopened_progress)
        reopened.close()

    def test_legacy_and_malformed_rejection_reach_new_terminal_state_without_write(
        self,
    ) -> None:
        cases = (
            (self.legacy, r"contrat|contract|version|legacy|learnit\.kit\.v2"),
            (
                '{"contract":"learnit.kit.v2", invalid-json',
                r"json|syntaxe|syntax|invalide|invalid|parse",
            ),
        )
        for index, (payload, pattern) in enumerate(cases):
            if index:
                self.reset_visible_state()
            feedback = self.assert_rejection_without_storage_change(
                payload, pattern
            )
            self.assertRegex(feedback, re.compile(pattern, re.I))

    def test_reordered_qcm_choices_keep_choice_id_correction_semantics(self) -> None:
        self.import_through_keyboard(self.reordered)
        courses = self.wait_courses(1)
        course = self.reordered["courses"][0]
        qcm = course["activities"][0]
        self.start_course(course["title"], qcm["prompt"])
        self.assert_no_qcm_preselection(qcm)
        correct_label = next(
            choice["label"]
            for choice in qcm["choices"]
            if choice["choiceId"] == qcm["correctChoiceId"]
        )
        self.start_feedback_probe(SUCCESS_FEEDBACK)
        self.answer_qcm_with_keyboard(correct_label)
        self.assertRegex(
            self.wait_feedback(), re.compile(SUCCESS_FEEDBACK, re.I)
        )
        self.assert_activity_success(
            self.api("getProgress", courses[0]["courseInstallId"]),
            qcm,
            selected=qcm["correctChoiceId"],
        )

    def test_fill_maxuses_one_is_rejected_without_progress_or_storage_mutation(
        self,
    ) -> None:
        invalid = copy.deepcopy(self.valid)
        invalid["courses"][0]["activities"][1]["tokens"][0]["maxUses"] = 1
        invalid = recompute(invalid)
        pattern = r"max.?uses|utilisation|réutilis|token|invalide|invalid"
        feedback = self.assert_rejection_without_storage_change(invalid, pattern)
        self.assertRegex(feedback, re.compile(pattern, re.I))

    def test_visible_reset_removes_successor_library_only(self) -> None:
        self.import_through_keyboard(self.valid)
        self.wait_courses(1)
        self.activate_named(RESET_NAMES)
        confirm = self.first_visible(
            self.page.get_by_role(
                "button", name=re.compile(r"confirmer|oui|confirm|yes", re.I)
            )
        )
        if confirm is not None:
            self.activate(confirm)
        self.wait_courses(0)
        self.assertIsNotNone(self.first_visible(self.page.get_by_text(EMPTY_NAMES)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
