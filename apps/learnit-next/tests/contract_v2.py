#!/usr/bin/env python3
"""Independent learnit.kit.v2 oracle plus black-box runtime attacks."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import threading
import unicodedata
import unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "contracts" / "fixtures"
SCHEMA = ROOT / "contracts" / "learnit-kit-v2.schema.json"
VALID = FIXTURES / "v2-valid-minimal.json"
LEGACY = FIXTURES / "v2-invalid-legacy.json"
MISMATCH = FIXTURES / "v2-invalid-digest-mismatch.json"
ARTIFACT = ROOT / "apps" / "learnit-next" / "dist" / "learnit-next.html"
UUID4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
DOMAIN_REJECTION = re.compile(
    r"contract|contrat|legacy|schema|invalid|invalide|validation|digest|revision|révision|"
    r"reference|référence|duplicate|doublon|max.?uses|token|slot|choice|choix|"
    r"objective|objectif|uuid|package",
    re.I,
)
STRICT = os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION") == "1"

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
        keyPath: store.keyPath,
        autoIncrement: store.autoIncrement,
        indexes: Array.from(store.indexNames).sort(),
        keys: keys.result,
        records: records.result
      });
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error || new Error('snapshot transaction aborted'));
    });
  }
  const result = {version: db.version, stores};
  db.close();
  return result;
}"""


def require_or_skip(condition: bool, message: str) -> None:
    if condition:
        return
    if STRICT:
        raise RuntimeError(message)
    raise unittest.SkipTest(message)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise TypeError("floats forbidden")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in result:
                raise ValueError("NFC key collision")
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


def digest(obj: dict[str, Any], field: str) -> str:
    payload = {key: value for key, value in obj.items() if key != field}
    return "sha256:" + hashlib.sha256(canonical(payload)).hexdigest()


def redigest(package: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(package)
    for course in result["courses"]:
        for activity in course["activities"]:
            activity["activityRevisionDigest"] = digest(
                activity, "activityRevisionDigest"
            )
        course["courseRevisionDigest"] = digest(course, "courseRevisionDigest")
    result["packageRevisionDigest"] = digest(result, "packageRevisionDigest")
    return result


def duplicates(values: Any) -> set[Any]:
    seen: set[Any] = set()
    repeated: set[Any] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def semantic_errors(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if package.get("contract") != "learnit.kit.v2":
        return ["contract"]

    for key in ("courseLineageId", "courseRevisionId"):
        if duplicates(course[key] for course in package["courses"]):
            errors.append(f"duplicate {key}")

    activity_lineages: list[str] = []
    activity_revisions: list[str] = []
    for course in package["courses"]:
        objective_ids = [item["objectiveId"] for item in course["objectives"]]
        if duplicates(objective_ids):
            errors.append("duplicate objectiveId")

        activity_lineages.extend(
            activity["activityLineageId"] for activity in course["activities"]
        )
        activity_revisions.extend(
            activity["activityRevisionId"] for activity in course["activities"]
        )

        for activity in course["activities"]:
            if any(
                objective_id not in objective_ids
                for objective_id in activity["objectiveIds"]
            ):
                errors.append("missing objective")

            if activity["type"] == "qcm":
                choice_ids = [choice["choiceId"] for choice in activity["choices"]]
                if duplicates(choice_ids):
                    errors.append("duplicate choice")
                if activity["correctChoiceId"] not in choice_ids:
                    errors.append("missing choice")
                continue

            slot_ids = [
                segment["slotId"]
                for segment in activity["segments"]
                if "slotId" in segment
            ]
            token_ids = [token["tokenId"] for token in activity["tokens"]]
            answer_slot_ids = [answer["slotId"] for answer in activity["answers"]]
            if duplicates(slot_ids):
                errors.append("duplicate slot")
            if duplicates(token_ids):
                errors.append("duplicate token")
            if duplicates(answer_slot_ids):
                errors.append("duplicate answer")
            if set(answer_slot_ids) != set(slot_ids):
                errors.append("slot reference")

            token_limits = {
                token["tokenId"]: token["maxUses"] for token in activity["tokens"]
            }
            uses: dict[str, int] = {}
            for answer in activity["answers"]:
                token_id = answer["tokenId"]
                if token_id not in token_limits:
                    errors.append("token reference")
                uses[token_id] = uses.get(token_id, 0) + 1
            if any(
                count > token_limits.get(token_id, -1)
                for token_id, count in uses.items()
            ):
                errors.append("maxUses")

    if duplicates(activity_lineages):
        errors.append("duplicate activityLineageId")
    if duplicates(activity_revisions):
        errors.append("duplicate activityRevisionId")
    return errors


def digest_errors(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for course in package["courses"]:
        for activity in course["activities"]:
            if activity["activityRevisionDigest"] != digest(
                activity, "activityRevisionDigest"
            ):
                errors.append("activity")
        if course["courseRevisionDigest"] != digest(
            course, "courseRevisionDigest"
        ):
            errors.append("course")
    if package["packageRevisionDigest"] != digest(
        package, "packageRevisionDigest"
    ):
        errors.append("package")
    return errors


def identity_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("Id") and isinstance(item, str):
                yield item
            yield from identity_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from identity_values(item)


def fresh_uuid(index: int) -> str:
    return f"{index:08x}-9abc-4def-8abc-{index:012x}"


def append_fresh_course(
    package: dict[str, Any],
    *,
    duplicate_lineage: bool = False,
    duplicate_revision: bool = False,
) -> None:
    source = package["courses"][0]
    clone = copy.deepcopy(source)
    counter = 100

    clone["courseLineageId"] = (
        source["courseLineageId"] if duplicate_lineage else fresh_uuid(counter)
    )
    counter += 1
    clone["courseRevisionId"] = (
        source["courseRevisionId"] if duplicate_revision else fresh_uuid(counter)
    )
    counter += 1

    objective_map: dict[str, str] = {}
    for objective in clone["objectives"]:
        old = objective["objectiveId"]
        objective["objectiveId"] = fresh_uuid(counter)
        counter += 1
        objective_map[old] = objective["objectiveId"]

    for activity in clone["activities"]:
        activity["activityLineageId"] = fresh_uuid(counter)
        counter += 1
        activity["activityRevisionId"] = fresh_uuid(counter)
        counter += 1
        activity["objectiveIds"] = [
            objective_map[item] for item in activity["objectiveIds"]
        ]
        if activity["type"] == "qcm":
            choice_map: dict[str, str] = {}
            for choice in activity["choices"]:
                old = choice["choiceId"]
                choice["choiceId"] = fresh_uuid(counter)
                counter += 1
                choice_map[old] = choice["choiceId"]
            activity["correctChoiceId"] = choice_map[activity["correctChoiceId"]]
        else:
            slot_map: dict[str, str] = {}
            for segment in activity["segments"]:
                if "slotId" in segment:
                    old = segment["slotId"]
                    segment["slotId"] = fresh_uuid(counter)
                    counter += 1
                    slot_map[old] = segment["slotId"]
            token_map: dict[str, str] = {}
            for token in activity["tokens"]:
                old = token["tokenId"]
                token["tokenId"] = fresh_uuid(counter)
                counter += 1
                token_map[old] = token["tokenId"]
            for answer in activity["answers"]:
                answer["slotId"] = slot_map[answer["slotId"]]
                answer["tokenId"] = token_map[answer["tokenId"]]
    package["courses"].append(clone)


def append_activity_duplicate(
    package: dict[str, Any],
    *,
    duplicate_lineage: bool = False,
    duplicate_revision: bool = False,
) -> None:
    source = package["courses"][0]["activities"][0]
    clone = copy.deepcopy(source)
    if not duplicate_lineage:
        clone["activityLineageId"] = fresh_uuid(700)
    if not duplicate_revision:
        clone["activityRevisionId"] = fresh_uuid(701)

    choice_map: dict[str, str] = {}
    for index, choice in enumerate(clone["choices"], start=710):
        old = choice["choiceId"]
        choice["choiceId"] = fresh_uuid(index)
        choice_map[old] = choice["choiceId"]
    clone["correctChoiceId"] = choice_map[clone["correctChoiceId"]]
    package["courses"][0]["activities"].append(clone)


Mutation = Callable[[dict[str, Any]], None]


def runtime_attack_cases(valid: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    cases: list[tuple[str, Mutation]] = [
        ("unknown root property", lambda p: p.__setitem__("unknown", True)),
        (
            "unknown course property",
            lambda p: p["courses"][0].__setitem__("unknown", True),
        ),
        (
            "unknown activity property",
            lambda p: p["courses"][0]["activities"][0].__setitem__(
                "unknown", True
            ),
        ),
        (
            "unknown choice property",
            lambda p: p["courses"][0]["activities"][0]["choices"][0].__setitem__(
                "unknown", True
            ),
        ),
        (
            "unknown token property",
            lambda p: p["courses"][0]["activities"][1]["tokens"][0].__setitem__(
                "unknown", True
            ),
        ),
        (
            "uppercase root UUID",
            lambda p: p.__setitem__(
                "packageLineageId", "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
            ),
        ),
        (
            "invalid activity UUID",
            lambda p: p["courses"][0]["activities"][0].__setitem__(
                "activityRevisionId", "not-a-uuid"
            ),
        ),
        (
            "invalid choice UUID",
            lambda p: p["courses"][0]["activities"][0]["choices"][0].__setitem__(
                "choiceId", "not-a-uuid"
            ),
        ),
        (
            "invalid slot UUID",
            lambda p: next(
                item
                for item in p["courses"][0]["activities"][1]["segments"]
                if "slotId" in item
            ).__setitem__("slotId", "not-a-uuid"),
        ),
        (
            "invalid token UUID",
            lambda p: p["courses"][0]["activities"][1]["tokens"][0].__setitem__(
                "tokenId", "not-a-uuid"
            ),
        ),
        (
            "duplicate courseLineageId",
            lambda p: append_fresh_course(p, duplicate_lineage=True),
        ),
        (
            "duplicate courseRevisionId",
            lambda p: append_fresh_course(p, duplicate_revision=True),
        ),
        (
            "duplicate activityLineageId",
            lambda p: append_activity_duplicate(p, duplicate_lineage=True),
        ),
        (
            "duplicate activityRevisionId",
            lambda p: append_activity_duplicate(p, duplicate_revision=True),
        ),
        (
            "duplicate objectiveId",
            lambda p: p["courses"][0]["objectives"].append(
                copy.deepcopy(p["courses"][0]["objectives"][0])
            ),
        ),
        (
            "duplicate choiceId",
            lambda p: p["courses"][0]["activities"][0]["choices"][1].__setitem__(
                "choiceId",
                p["courses"][0]["activities"][0]["choices"][0]["choiceId"],
            ),
        ),
        (
            "duplicate slotId",
            lambda p: p["courses"][0]["activities"][1]["segments"].append(
                copy.deepcopy(
                    next(
                        item
                        for item in p["courses"][0]["activities"][1]["segments"]
                        if "slotId" in item
                    )
                )
            ),
        ),
        (
            "duplicate tokenId",
            lambda p: p["courses"][0]["activities"][1]["tokens"].append(
                copy.deepcopy(p["courses"][0]["activities"][1]["tokens"][0])
            ),
        ),
        (
            "duplicate answers slotId",
            lambda p: p["courses"][0]["activities"][1]["answers"].append(
                copy.deepcopy(p["courses"][0]["activities"][1]["answers"][0])
            ),
        ),
        (
            "slot without answer",
            lambda p: p["courses"][0]["activities"][1]["answers"].pop(),
        ),
        (
            "answer references absent slot",
            lambda p: p["courses"][0]["activities"][1]["answers"][0].__setitem__(
                "slotId", fresh_uuid(900)
            ),
        ),
        (
            "missing objective reference",
            lambda p: p["courses"][0]["activities"][0].__setitem__(
                "objectiveIds", [fresh_uuid(901)]
            ),
        ),
        (
            "missing correct choice",
            lambda p: p["courses"][0]["activities"][0].__setitem__(
                "correctChoiceId", fresh_uuid(902)
            ),
        ),
        (
            "missing token reference",
            lambda p: p["courses"][0]["activities"][1]["answers"][0].__setitem__(
                "tokenId", fresh_uuid(903)
            ),
        ),
        (
            "maxUses overflow",
            lambda p: p["courses"][0]["activities"][1]["tokens"][0].__setitem__(
                "maxUses", 1
            ),
        ),
    ]

    result: list[tuple[str, dict[str, Any]]] = []
    for name, mutate in cases:
        package = copy.deepcopy(valid)
        mutate(package)
        result.append((name, redigest(package)))
    return result


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return


@contextmanager
def serve(path: Path):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Quiet, directory=str(path.parent))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/{path.name}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def negative(result: Any) -> bool:
    if result is False:
        return True
    if not isinstance(result, dict):
        return False
    return any(
        result.get(key) is False
        for key in ("ok", "valid", "accepted", "imported", "success")
    ) or str(result.get("status", "")).lower() in {"error", "invalid", "rejected"}


class FixtureOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        require_or_skip(Draft202012Validator is not None, "DEPENDENCY: jsonschema")
        cls.schema = load(SCHEMA)
        cls.valid = load(VALID)
        cls.legacy = load(LEGACY)
        cls.mismatch = load(MISMATCH)
        cls.validator = Draft202012Validator(cls.schema)

    def test_schema_and_valid_fixture(self) -> None:
        self.assertEqual(
            "learnit.kit.v2", self.schema["properties"]["contract"]["const"]
        )
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(
            [], [error.message for error in self.validator.iter_errors(self.valid)]
        )

    def test_uuid_v4_lowercase_and_digest_shapes(self) -> None:
        for value in identity_values(self.valid):
            self.assertRegex(value, UUID4)
        digests = [self.valid["packageRevisionDigest"]]
        for course in self.valid["courses"]:
            digests.append(course["courseRevisionDigest"])
            digests.extend(
                activity["activityRevisionDigest"]
                for activity in course["activities"]
            )
        for value in digests:
            self.assertRegex(value, SHA256)

    def test_valid_semantics_and_sha256(self) -> None:
        self.assertEqual([], semantic_errors(self.valid))
        self.assertEqual([], digest_errors(self.valid))

    def test_unknown_properties_and_nested_uuid_are_rejected(self) -> None:
        schema_case_names = {
            "unknown root property",
            "unknown course property",
            "unknown activity property",
            "unknown choice property",
            "unknown token property",
            "uppercase root UUID",
            "invalid activity UUID",
            "invalid choice UUID",
            "invalid slot UUID",
            "invalid token UUID",
        }
        for name, attack in runtime_attack_cases(self.valid):
            if name in schema_case_names:
                self.assertTrue(
                    list(self.validator.iter_errors(attack)),
                    f"schema accepted {name}",
                )

    def test_semantic_attack_matrix(self) -> None:
        semantic_case_names = {
            "duplicate courseLineageId",
            "duplicate courseRevisionId",
            "duplicate activityLineageId",
            "duplicate activityRevisionId",
            "duplicate objectiveId",
            "duplicate choiceId",
            "duplicate slotId",
            "duplicate tokenId",
            "duplicate answers slotId",
            "slot without answer",
            "answer references absent slot",
            "missing objective reference",
            "missing correct choice",
            "missing token reference",
            "maxUses overflow",
        }
        attacks = dict(runtime_attack_cases(self.valid))
        for name in semantic_case_names:
            self.assertTrue(semantic_errors(attacks[name]), name)

    def test_canonical_json_profile(self) -> None:
        self.assertEqual(
            b'{"a":[true,null,3],"z":"\xc3\xa9","\xc3\xa9":"ok"}',
            canonical({"z": "e\u0301", "a": [True, None, 3], "é": "ok"}),
        )
        with self.assertRaises(TypeError):
            canonical({"x": 1.5})
        with self.assertRaises(ValueError):
            canonical({"é": 1, "e\u0301": 2})

    def test_legacy_and_digest_mismatch_fixtures(self) -> None:
        self.assertEqual("learnit.import.v1.1", self.legacy["schema_version"])
        self.assertTrue(list(self.validator.iter_errors(self.legacy)))
        self.assertEqual(
            [],
            [error.message for error in self.validator.iter_errors(self.mismatch)],
        )
        self.assertEqual(
            self.valid["courses"][0]["activities"][0]["activityRevisionId"],
            self.mismatch["courses"][0]["activities"][0]["activityRevisionId"],
        )
        self.assertTrue(digest_errors(self.mismatch))

    def test_qcm_reordering_keeps_choice_id_semantics(self) -> None:
        package = copy.deepcopy(self.valid)
        qcm = package["courses"][0]["activities"][0]
        old_digest = qcm["activityRevisionDigest"]
        qcm["choices"].reverse()
        self.assertIn(
            qcm["correctChoiceId"],
            [choice["choiceId"] for choice in qcm["choices"]],
        )
        self.assertNotEqual(old_digest, digest(qcm, "activityRevisionDigest"))


class RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path(os.environ.get("LEARNIT_NEXT_ARTIFACT", ARTIFACT))
        require_or_skip(path.exists(), f"WAITING_FOR_INTEGRATION: {path}")
        require_or_skip(sync_playwright is not None, "DEPENDENCY: Playwright")
        cls.valid = load(VALID)
        cls.legacy = load(LEGACY)
        cls.mismatch = load(MISMATCH)
        cls.server = serve(path)
        cls.url = cls.server.__enter__()
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except Exception as error:
            cls.playwright.stop()
            cls.server.__exit__(None, None, None)
            require_or_skip(False, f"DEPENDENCY: Chromium: {error}")

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
        self.page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        self.call("resetNextData")

    def tearDown(self) -> None:
        self.context.close()

    def invoke(self, operation: str, *args: Any) -> dict[str, Any]:
        return self.page.evaluate(
            """async ({operation,args}) => {
              const api = window.__LEARNIT_NEXT_TEST__;
              if (!api || typeof api[operation] !== 'function') {
                return {kind:'harness', message:`missing ${operation}`};
              }
              try {
                return {kind:'return', value:await api[operation](...args)};
              } catch (error) {
                return {
                  kind:'throw',
                  name:String(error && error.name || ''),
                  message:String(error && error.message || error || '')
                };
              }
            }""",
            {"operation": operation, "args": list(args)},
        )

    def call(self, operation: str, *args: Any) -> Any:
        result = self.invoke(operation, *args)
        self.assertEqual("return", result.get("kind"), result)
        return result.get("value")

    def reject(self, operation: str, payload: Any) -> dict[str, Any]:
        result = self.invoke(operation, payload)
        self.assertNotEqual("harness", result.get("kind"), result)
        if result.get("kind") == "return":
            self.assertTrue(negative(result.get("value")), result)
        else:
            self.assertEqual("throw", result.get("kind"), result)
            evidence = f"{result.get('name', '')}: {result.get('message', '')}"
            self.assertRegex(evidence, DOMAIN_REJECTION)
        return result

    def courses(self) -> list[Any]:
        courses = self.call("listCourses")
        self.assertIsInstance(courses, list, courses)
        return courses

    def snapshot_next(self) -> Any:
        return self.page.evaluate(NEXT_SNAPSHOT, "learnit_next_v1")

    def assert_rejected_without_write(
        self, operation: str, payload: Any, label: str
    ) -> None:
        before = self.snapshot_next()
        self.reject(operation, payload)
        after = self.snapshot_next()
        self.assertEqual(before, after, f"partial successor write for {label}")

    def test_contract_version_and_valid_import(self) -> None:
        self.assertEqual(
            "learnit.kit.v2",
            self.page.evaluate("() => window.__LEARNIT_NEXT_TEST__.contractVersion"),
        )
        validation = self.invoke("validatePackage", self.valid)
        self.assertEqual("return", validation.get("kind"), validation)
        self.assertFalse(negative(validation.get("value")), validation)
        imported = self.invoke("importPackage", self.valid)
        self.assertEqual("return", imported.get("kind"), imported)
        self.assertFalse(negative(imported.get("value")), imported)
        self.assertEqual(1, len(self.courses()))

    def test_schema_uuid_unknown_duplicate_and_reference_attacks(self) -> None:
        for name, attack in runtime_attack_cases(self.valid):
            self.assert_rejected_without_write(
                "validatePackage", attack, f"validate: {name}"
            )
            self.assert_rejected_without_write(
                "importPackage", attack, f"import: {name}"
            )
            self.assertEqual([], self.courses(), name)

    def test_digest_mismatch_same_revision_conflict_and_legacy_are_atomic(
        self,
    ) -> None:
        for label, payload in (
            ("legacy contract", self.legacy),
            ("digest mismatch", self.mismatch),
        ):
            self.assert_rejected_without_write("importPackage", payload, label)
            self.assertEqual([], self.courses(), label)

        imported = self.invoke("importPackage", self.valid)
        self.assertEqual("return", imported.get("kind"), imported)
        self.assertFalse(negative(imported.get("value")), imported)
        before = self.snapshot_next()

        conflict = copy.deepcopy(self.valid)
        conflict["courses"][0]["activities"][0]["prompt"] += " changed"
        conflict = redigest(conflict)
        self.reject("importPackage", conflict)
        self.assertEqual(
            before,
            self.snapshot_next(),
            "revision conflict left partial packages/courses/progress/meta",
        )
        self.assertEqual(1, len(self.courses()))

    def test_qcm_choice_reordering_does_not_change_correction(self) -> None:
        package = copy.deepcopy(self.valid)
        qcm = package["courses"][0]["activities"][0]
        qcm["choices"].reverse()
        qcm["activityRevisionId"] = fresh_uuid(950)
        package["courses"][0]["courseRevisionId"] = fresh_uuid(951)
        package["packageRevisionId"] = fresh_uuid(952)
        package = redigest(package)

        imported = self.invoke("importPackage", package)
        self.assertEqual("return", imported.get("kind"), imported)
        self.assertFalse(negative(imported.get("value")), imported)
        course = self.courses()[0]
        self.call("startCourse", course["courseInstallId"])
        result = self.call(
            "answer", qcm["activityRevisionId"], qcm["correctChoiceId"]
        )
        self.assertIsInstance(result, dict, result)
        self.assertIs(result.get("correct"), True, result)
        self.assertIs(result.get("completed"), True, result)
        self.assertEqual(qcm["correctChoiceId"], result.get("selectedChoiceId"), result)
        self.assertEqual(
            qcm["activityRevisionId"], result.get("activityRevisionId"), result
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
