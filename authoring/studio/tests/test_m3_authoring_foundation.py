#!/usr/bin/env python3
"""Product evidence for ATLAS-WP-009 M3.0 Authoring Foundation."""
from __future__ import annotations

import re
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDIO = ROOT / "authoring/studio"
if str(STUDIO) not in sys.path:
    sys.path.insert(0, str(STUDIO))

from core import (
    AuthoringError,
    NAMESPACE,
    PREVIEW_AUTHORITY,
    apply_edit,
    build_preview,
    create_draft,
    export_draft,
    reimport_export,
    validate_draft,
)
from server import StudioHandler, ThreadingHTTPServer, loopback_host

KITS = (
    ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json",
    ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json",
)
JS_PATH = STUDIO / "web/studio.js"
SERVER_PATH = STUDIO / "server.py"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class UuidSequence:
    def __init__(self, values: list[str]):
        self.values = list(values)
        self.calls = 0

    def __call__(self) -> str:
        if self.calls >= len(self.values):
            raise AssertionError("unexpected revision UUID allocation")
        value = self.values[self.calls]
        self.calls += 1
        return value


def raw(path: Path) -> bytes:
    return path.read_bytes()


def lineage_snapshot(package: dict) -> dict:
    return {
        "package": package["packageLineageId"],
        "courses": [course["courseLineageId"] for course in package["courses"]],
        "objectives": [[objective["objectiveId"] for objective in course["objectives"]] for course in package["courses"]],
        "activities": [[activity["activityLineageId"] for activity in course["activities"]] for course in package["courses"]],
    }


def activity_revision_ids(package: dict) -> list[list[str]]:
    return [[activity["activityRevisionId"] for activity in course["activities"]] for course in package["courses"]]


class CoreContractTests(unittest.TestCase):
    def test_01_both_canonical_kits_load_and_noop_export_is_byte_identical(self) -> None:
        for path in KITS:
            source = raw(path)
            draft = create_draft(source, path.name)
            self.assertTrue(validate_draft(draft)["ok"], path)
            exported, digest = export_draft(draft)
            self.assertEqual(source, exported, path)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            again, again_digest = export_draft(reimport_export(draft, "again.json"))
            self.assertEqual(exported, again)
            self.assertEqual(digest, again_digest)

    def test_02_qcm_semantic_edit_preserves_lineage_and_rotates_only_required_revisions(self) -> None:
        source = raw(KITS[0])
        draft = create_draft(source, KITS[0].name)
        before = draft["package"]
        before_lineage = lineage_snapshot(before)
        before_activities = activity_revision_ids(before)
        sequence = UuidSequence([
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
            "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2",
            "cccccccc-cccc-4ccc-8ccc-ccccccccccc3",
        ])
        edited = apply_edit(
            draft,
            ["courses", 0, "activities", 0, "prompt"],
            "Quel est le conjugué exact de 2 + 3i ?",
            sequence,
        )
        self.assertEqual(3, sequence.calls)
        after = edited["package"]
        self.assertEqual(before_lineage, lineage_snapshot(after))
        self.assertNotEqual(before["packageRevisionId"], after["packageRevisionId"])
        self.assertNotEqual(before["courses"][0]["courseRevisionId"], after["courses"][0]["courseRevisionId"])
        self.assertNotEqual(before_activities[0][0], after["courses"][0]["activities"][0]["activityRevisionId"])
        self.assertEqual(
            before_activities[0][1:],
            [activity["activityRevisionId"] for activity in after["courses"][0]["activities"][1:]],
        )
        edited2 = apply_edit(
            edited,
            ["courses", 0, "activities", 0, "explanation"],
            "Le conjugué garde la partie réelle et inverse uniquement le signe de la partie imaginaire.",
            UuidSequence([]),
        )
        self.assertEqual(after["packageRevisionId"], edited2["package"]["packageRevisionId"])
        self.assertEqual(after["courses"][0]["courseRevisionId"], edited2["package"]["courses"][0]["courseRevisionId"])
        self.assertEqual(
            after["courses"][0]["activities"][0]["activityRevisionId"],
            edited2["package"]["courses"][0]["activities"][0]["activityRevisionId"],
        )
        self.assertTrue(validate_draft(edited2)["ok"])
        first, first_digest = export_draft(edited2)
        second, second_digest = export_draft(edited2)
        self.assertEqual(first, second)
        self.assertEqual(first_digest, second_digest)
        self.assertNotEqual(source, first)
        reimported = create_draft(first, "edited-qcm.json")
        self.assertTrue(validate_draft(reimported)["ok"])
        self.assertEqual(first, export_draft(reimported)[0])

    def test_03_fill_semantic_edit_preserves_lineage_and_produces_valid_deterministic_export(self) -> None:
        source = raw(KITS[1])
        draft = create_draft(source, KITS[1].name)
        before = draft["package"]
        sequence = UuidSequence([
            "dddddddd-dddd-4ddd-8ddd-ddddddddddd4",
            "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee5",
            "ffffffff-ffff-4fff-8fff-fffffffffff6",
        ])
        edited = apply_edit(
            draft,
            ["courses", 0, "activities", 2, "prompt"],
            "Complète la valeur de la résistance pour U = 10 V et I = 0,5 A.",
            sequence,
        )
        self.assertEqual(lineage_snapshot(before), lineage_snapshot(edited["package"]))
        self.assertTrue(validate_draft(edited)["ok"])
        one = export_draft(edited)
        two = export_draft(edited)
        self.assertEqual(one, two)
        self.assertTrue(validate_draft(create_draft(one[0], "edited-fill.json"))["ok"])

    def test_04_package_course_and_objective_edits_allocate_only_enclosing_revisions(self) -> None:
        draft = create_draft(raw(KITS[0]), KITS[0].name)
        original = draft["package"]
        package_edit = apply_edit(draft, ["title"], original["title"] + " — essai", UuidSequence([
            "10101010-1010-4010-8010-101010101010",
        ]))
        self.assertNotEqual(original["packageRevisionId"], package_edit["package"]["packageRevisionId"])
        self.assertEqual(original["courses"][0]["courseRevisionId"], package_edit["package"]["courses"][0]["courseRevisionId"])
        course_edit = apply_edit(draft, ["courses", 0, "title"], original["courses"][0]["title"] + " — essai", UuidSequence([
            "20202020-2020-4020-8020-202020202020",
            "30303030-3030-4030-8030-303030303030",
        ]))
        self.assertNotEqual(original["courses"][0]["courseRevisionId"], course_edit["package"]["courses"][0]["courseRevisionId"])
        self.assertEqual(activity_revision_ids(original), activity_revision_ids(course_edit["package"]))
        objective_edit = apply_edit(draft, ["courses", 0, "objectives", 0, "label"], "Calculer et expliquer un conjugué", UuidSequence([
            "40404040-4040-4040-8040-404040404040",
            "50505050-5050-4050-8050-505050505050",
        ]))
        self.assertEqual(activity_revision_ids(original), activity_revision_ids(objective_edit["package"]))
        self.assertTrue(validate_draft(objective_edit)["ok"])

    def test_05_blocking_canonical_defects_disable_export(self) -> None:
        draft = create_draft(raw(KITS[0]), KITS[0].name)
        invalid_class = apply_edit(
            draft,
            ["courses", 0, "activities", 0, "learningPhase"],
            "validation",
            UuidSequence([
                "61616161-6161-4161-8161-616161616161",
                "62626262-6262-4262-8262-626262626262",
                "63636363-6363-4363-8363-636363636363",
            ]),
        )
        verdict = validate_draft(invalid_class)
        self.assertFalse(verdict["ok"])
        self.assertFalse(verdict["exportAvailable"])
        with self.assertRaises(AuthoringError):
            export_draft(invalid_class)

        invalid_qcm = apply_edit(
            draft,
            ["courses", 0, "activities", 0, "correctChoiceId"],
            "00000000-0000-4000-8000-000000000000",
            UuidSequence([
                "71717171-7171-4171-8171-717171717171",
                "72727272-7272-4272-8272-727272727272",
                "73737373-7373-4373-8373-737373737373",
            ]),
        )
        self.assertFalse(validate_draft(invalid_qcm)["exportAvailable"])

        fill_draft = create_draft(raw(KITS[1]), KITS[1].name)
        invalid_fill = apply_edit(
            fill_draft,
            ["courses", 0, "activities", 2, "answers", 0, "tokenId"],
            "00000000-0000-4000-8000-000000000000",
            UuidSequence([
                "81818181-8181-4181-8181-818181818181",
                "82828282-8282-4282-8282-828282828282",
                "83838383-8383-4383-8383-838383838383",
            ]),
        )
        self.assertFalse(validate_draft(invalid_fill)["exportAvailable"])

    def test_06_parser_rejects_duplicate_keys_malformed_utf8_floats_and_structural_edits(self) -> None:
        with self.assertRaises(AuthoringError):
            create_draft(b'{"contract":"learnit.kit.v2","contract":"again"}', "duplicate.json")
        with self.assertRaises(AuthoringError):
            create_draft(b"\xff\xfe", "bad-utf8.json")
        with self.assertRaises(AuthoringError):
            create_draft(b'{"contract":"learnit.kit.v2","x":1.25}', "float.json")
        draft = create_draft(raw(KITS[0]), KITS[0].name)
        for path in (
            ["packageLineageId"],
            ["courses", 0, "activities", 0, "activityLineageId"],
            ["courses", 0, "activities", 0, "choices", 0, "choiceId"],
            ["courses", 0, "activities"],
        ):
            with self.assertRaises(AuthoringError, msg=path):
                apply_edit(draft, path, "forbidden")

    def test_07_preview_is_explicitly_author_only(self) -> None:
        draft = create_draft(raw(KITS[0]), KITS[0].name)
        preview = build_preview(draft, 0, 0)
        self.assertEqual(PREVIEW_AUTHORITY, preview["authority"])
        self.assertIn("Aperçu auteur uniquement", preview["disclaimer"])
        self.assertNotIn("recommendation", preview)
        self.assertNotIn("mastery", preview)

    def test_08_server_is_loopback_only_and_no_permissive_cors_or_outbound_client_exists(self) -> None:
        self.assertEqual("127.0.0.1", loopback_host("127.0.0.1"))
        self.assertEqual("::1", loopback_host("::1"))
        for host in ("0.0.0.0", "192.168.1.20", "example.com"):
            with self.assertRaises(Exception, msg=host):
                loopback_host(host)
        server_text = SERVER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("Access-Control-Allow-Origin", server_text)
        self.assertNotRegex(server_text, r"\b(requests|httpx|aiohttp)\b")

    def test_09_web_persistence_is_exactly_the_isolated_authoring_key(self) -> None:
        js = JS_PATH.read_text(encoding="utf-8")
        self.assertIn("const STORAGE_KEY = 'learnit.authoring.m3.v1';", js)
        storage_calls = re.findall(r"localStorage\.(?:getItem|setItem|removeItem)\(([^)]*)\)", js)
        self.assertGreaterEqual(len(storage_calls), 3)
        self.assertTrue(all(call.strip().startswith("STORAGE_KEY") for call in storage_calls), storage_calls)
        self.assertNotIn("indexedDB.open", js)
        self.assertNotIn("learnit_atlas_m1_v2", js)
        self.assertNotIn("learnit_next_v1", js)


@unittest.skipUnless(sync_playwright is not None, "Playwright unavailable")
class BrowserIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_10_reload_and_discard_touch_only_authoring_storage_and_no_external_network(self) -> None:
        context = self.browser.new_context()
        external: list[str] = []

        def route_handler(route):
            if not route.request.url.startswith(self.url):
                external.append(route.request.url)
                route.abort()
            else:
                route.continue_()

        context.route("**/*", route_handler)
        page = context.new_page()
        page.goto(self.url, wait_until="domcontentloaded")
        page.evaluate("""async () => {
          localStorage.setItem('qa-learner-sentinel', 'keep');
          await new Promise((resolve, reject) => {
            const request = indexedDB.open('qa-learner-sentinel-db', 1);
            request.onupgradeneeded = () => request.result.createObjectStore('sentinel');
            request.onsuccess = () => { request.result.close(); resolve(); };
            request.onerror = () => reject(request.error);
          });
        }""")
        page.locator("#kit-file").set_input_files(str(KITS[0]))
        page.wait_for_function(f"() => Boolean(localStorage.getItem('{NAMESPACE}'))")
        self.assertEqual("keep", page.evaluate("() => localStorage.getItem('qa-learner-sentinel')"))
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("() => !document.querySelector('#workspace').hidden")
        self.assertTrue(page.evaluate(f"() => Boolean(localStorage.getItem('{NAMESPACE}'))"))
        db_names = page.evaluate("async () => (await indexedDB.databases()).map(item => item.name)")
        self.assertIn("qa-learner-sentinel-db", db_names)
        page.on("dialog", lambda dialog: dialog.accept())
        page.locator("#discard").click()
        page.wait_for_function(f"() => !localStorage.getItem('{NAMESPACE}')")
        self.assertEqual("keep", page.evaluate("() => localStorage.getItem('qa-learner-sentinel')"))
        db_names = page.evaluate("async () => (await indexedDB.databases()).map(item => item.name)")
        self.assertIn("qa-learner-sentinel-db", db_names)
        self.assertEqual([], external)
        context.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
