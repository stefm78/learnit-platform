#!/usr/bin/env python3
"""Independent contradictory oracle for QA-WP-018 / Atlas M3.0 authoring."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDIO = ROOT / "authoring/studio"
QA_WP = ROOT / "work-packages/QA-WP-018.json"
KITS = (
    ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json",
    ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json",
)
PRODUCT_RUNTIME_FILES = (
    ROOT / "authoring/studio/README.md",
    ROOT / "authoring/studio/core.py",
    ROOT / "authoring/studio/server.py",
    ROOT / "authoring/studio/web/index.html",
    ROOT / "authoring/studio/web/studio.css",
    ROOT / "authoring/studio/web/studio.js",
)
STRICT = os.environ.get("ATLAS_M3_QA_STRICT") == "1"

if str(STUDIO) not in sys.path:
    sys.path.insert(0, str(STUDIO))

try:
    from core import AuthoringError, NAMESPACE, apply_edit, build_preview, create_draft, export_draft, validate_draft
    from server import StudioHandler, ThreadingHTTPServer, loopback_host
except Exception as exc:
    if STRICT:
        raise
    AuthoringError = None
    NAMESPACE = "learnit.authoring.m3.v1"
    apply_edit = build_preview = create_draft = export_draft = validate_draft = None
    StudioHandler = ThreadingHTTPServer = loopback_host = None
    PRODUCT_IMPORT_ERROR = exc
else:
    PRODUCT_IMPORT_ERROR = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

QA_PATHS = {
    "work-packages/QA-WP-018.json",
    "authoring/studio/tests/qa_m3_authoring_foundation.py",
    ".github/workflows/atlas-m3-authoring-foundation-qa.yml",
}


def require_product() -> None:
    if PRODUCT_IMPORT_ERROR is not None:
        raise unittest.SkipTest(f"PRODUCT_HEAD_PENDING: {PRODUCT_IMPORT_ERROR}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def dynamic_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def deterministic_source_tar() -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "source.tar"
        subprocess.run(
            [
                "tar", "--sort=name", "--mtime=UTC 1970-01-01", "--owner=0", "--group=0", "--numeric-owner",
                "-cf", str(out),
                *[str(path.relative_to(ROOT)) for path in PRODUCT_RUNTIME_FILES],
            ],
            cwd=ROOT,
            check=True,
        )
        return out.read_bytes()


def lineages(package: dict) -> tuple:
    return (
        package["packageLineageId"],
        tuple(course["courseLineageId"] for course in package["courses"]),
        tuple(tuple(objective["objectiveId"] for objective in course["objectives"]) for course in package["courses"]),
        tuple(tuple(activity["activityLineageId"] for activity in course["activities"]) for course in package["courses"]),
    )


def revision_vector(package: dict) -> tuple:
    return (
        package["packageRevisionId"],
        tuple(course["courseRevisionId"] for course in package["courses"]),
        tuple(tuple(activity["activityRevisionId"] for activity in course["activities"]) for course in package["courses"]),
    )


def diagnostic_codes(draft: dict) -> set[str]:
    return {item.get("code") for item in validate_draft(draft)["diagnostics"]}


class ExactBindingTests(unittest.TestCase):
    def test_01_qa_metadata_and_exact_product_binding(self) -> None:
        qa = load_json(QA_WP)
        self.assertEqual("QA-WP-018", qa["id"])
        if not STRICT:
            self.assertIsNone(qa["baseline"].get("productHead"))
            return
        product = qa["baseline"].get("productHead")
        self.assertRegex(product or "", r"^[0-9a-f]{40}$")
        self.assertEqual(product, os.environ.get("ATLAS_M3_PRODUCT_HEAD"))
        self.assertEqual(product, git("merge-base", product, "HEAD"))
        changed = set(git("diff", "--name-only", f"{product}...HEAD").splitlines())
        self.assertEqual(QA_PATHS, changed)
        self.assertEqual(qa["baseline"]["productArtifactSha256"], os.environ.get("ATLAS_M3_PRODUCT_SOURCE_SHA256"))

    def test_02_product_source_package_identity_is_reconstructed_exactly(self) -> None:
        require_product()
        if not STRICT:
            raise unittest.SkipTest("exact product artifact binding is final-QA only")
        qa = load_json(QA_WP)
        expected = qa["baseline"]["productArtifactSha256"]
        self.assertEqual(expected, sha256(deterministic_source_tar()))


class ContradictoryCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        require_product()

    def test_03_noop_identity_for_both_proof_kits(self) -> None:
        for path in KITS:
            source = path.read_bytes()
            draft = create_draft(source, path.name)
            exported, digest = export_draft(draft)
            self.assertEqual(source, exported)
            self.assertEqual(sha256(source), digest)
            self.assertEqual(exported, export_draft(create_draft(exported, "roundtrip.json"))[0])

    def test_04_qcm_edit_rotates_required_revisions_rewrites_claims_and_is_deterministic(self) -> None:
        source = KITS[0].read_bytes()
        draft = create_draft(source, KITS[0].name)
        before = copy.deepcopy(draft["package"])
        old_claims = copy.deepcopy(before["courses"][0]["atlasValidationIndependenceClaims"])
        edited = apply_edit(draft, ["courses", 0, "activities", 0, "choices", 0, "label"], "2 − 3i (exact)")
        after = edited["package"]
        self.assertEqual(lineages(before), lineages(after))
        before_revs = revision_vector(before)
        after_revs = revision_vector(after)
        self.assertNotEqual(before_revs[0], after_revs[0])
        self.assertNotEqual(before_revs[1][0], after_revs[1][0])
        self.assertNotEqual(before_revs[2][0][0], after_revs[2][0][0])
        self.assertEqual(before_revs[2][0][1:], after_revs[2][0][1:])
        first, digest1 = export_draft(edited)
        second, digest2 = export_draft(edited)
        self.assertEqual(first, second)
        self.assertEqual(digest1, digest2)
        exported = json.loads(first)
        new_claims = exported["courses"][0]["atlasValidationIndependenceClaims"]
        affected = [
            c for c in new_claims
            if c["sourceActivityLineageId"] == after["courses"][0]["activities"][0]["activityLineageId"]
            or c["targetActivityLineageId"] == after["courses"][0]["activities"][0]["activityLineageId"]
        ]
        self.assertTrue(affected)
        self.assertNotEqual(old_claims, new_claims)
        self.assertTrue(validate_draft(create_draft(first, "qcm-edited.json"))["ok"])

    def test_05_fill_edit_rewrites_claim_material_and_survives_reimport(self) -> None:
        source = KITS[1].read_bytes()
        draft = create_draft(source, KITS[1].name)
        before = copy.deepcopy(draft["package"])
        edited = apply_edit(draft, ["courses", 0, "activities", 2, "tokens", 1, "label"], "20 ohms")
        self.assertEqual(lineages(before), lineages(edited["package"]))
        output, _ = export_draft(edited)
        reimported = create_draft(output, "fill-edited.json")
        self.assertTrue(validate_draft(reimported)["ok"])
        self.assertEqual(output, export_draft(reimported)[0])

    def test_06_stale_revision_and_digest_tampering_fail_closed(self) -> None:
        draft = create_draft(KITS[0].read_bytes(), KITS[0].name)
        stale = copy.deepcopy(draft)
        stale["package"]["courses"][0]["activities"][0]["prompt"] += " tampered"
        self.assertIn("STALE_ACTIVITY_REVISION", diagnostic_codes(stale))
        with self.assertRaises(Exception):
            export_draft(stale)

        edited = apply_edit(draft, ["courses", 0, "activities", 0, "prompt"], "Question changée")
        digest_tamper = copy.deepcopy(edited)
        digest_tamper["package"]["courses"][0]["activities"][0]["activityRevisionDigest"] = "sha256:" + "1" * 64
        self.assertIn("DRAFT_DIGEST_TAMPER", diagnostic_codes(digest_tamper))

    def test_07_lineage_structure_and_claim_tampering_fail_closed(self) -> None:
        draft = create_draft(KITS[0].read_bytes(), KITS[0].name)
        cases = []
        lineage = copy.deepcopy(draft)
        lineage["package"]["courses"][0]["activities"][0]["activityLineageId"] = str(uuid.uuid4())
        cases.append((lineage, "LINEAGE_MUTATION"))
        reorder = copy.deepcopy(draft)
        reorder["package"]["courses"][0]["activities"].reverse()
        cases.append((reorder, "LINEAGE_MUTATION"))
        claim = copy.deepcopy(draft)
        claim["package"]["courses"][0]["atlasValidationIndependenceClaims"][0]["claimId"] = "atlas-claim-sha256:" + "0" * 64
        cases.append((claim, "CLAIM_TAMPER"))
        for candidate, expected in cases:
            self.assertIn(expected, diagnostic_codes(candidate))
            with self.assertRaises(Exception):
                export_draft(candidate)

    def test_08_canonical_corruptions_disable_export(self) -> None:
        draft = create_draft(KITS[0].read_bytes(), KITS[0].name)
        invalid_role = apply_edit(draft, ["courses", 0, "activities", 0, "assessmentRole"], "validation")
        self.assertFalse(validate_draft(invalid_role)["exportAvailable"])
        broken_qcm = apply_edit(draft, ["courses", 0, "activities", 0, "correctChoiceId"], str(uuid.uuid4()))
        self.assertFalse(validate_draft(broken_qcm)["exportAvailable"])

        fill = create_draft(KITS[1].read_bytes(), KITS[1].name)
        broken_fill = apply_edit(fill, ["courses", 0, "activities", 2, "answers", 0, "tokenId"], str(uuid.uuid4()))
        self.assertFalse(validate_draft(broken_fill)["exportAvailable"])

    def test_09_duplicate_key_malformed_utf8_and_float_are_rejected(self) -> None:
        for data in (
            b'{"contract":"learnit.kit.v2","contract":"duplicate"}',
            b"\xff\xfe",
            b'{"contract":"learnit.kit.v2","value":1.5}',
        ):
            with self.assertRaises(Exception):
                create_draft(data, "adversarial.json")

    def test_10_changed_exports_pass_both_frozen_validator_authorities(self) -> None:
        v2 = dynamic_module("qa_m3_v2_authority", ROOT / "authoring/v2/validate_kit.py")
        atlas = dynamic_module("qa_m3_atlas_authority", ROOT / "authoring/v2/atlas/validate_atlas_content.py")
        schema = v2.load(ROOT / "contracts/learnit-kit-v2.schema.json")
        for path, edit_path, value in (
            (KITS[0], ["courses", 0, "activities", 0, "prompt"], "QA indépendante : quel est le conjugué de 2 + 3i ?"),
            (KITS[1], ["courses", 0, "activities", 2, "prompt"], "QA indépendante : complète R pour U = 10 V et I = 0,5 A."),
        ):
            draft = create_draft(path.read_bytes(), path.name)
            output, _ = export_draft(apply_edit(draft, edit_path, value))
            package = json.loads(output)
            report = v2.validate(Path("<qa-export>"), package, schema, False)
            self.assertEqual([], report.errors)
            self.assertTrue(atlas.validate_package(package))

    def test_11_preview_has_no_learner_semantic_authority(self) -> None:
        draft = create_draft(KITS[0].read_bytes(), KITS[0].name)
        preview = build_preview(draft, 0, 0)
        self.assertEqual("AUTHOR_PREVIEW_ONLY", preview["authority"])
        serialized = json.dumps(preview, ensure_ascii=False).lower()
        for forbidden in ("learnerstate", "mastered", "certified", "recommendationid"):
            self.assertNotIn(forbidden, serialized)

    def test_12_static_local_only_boundary(self) -> None:
        for host in ("0.0.0.0", "10.0.0.1", "example.com"):
            with self.assertRaises(Exception):
                loopback_host(host)
        sources = "\n".join(path.read_text(encoding="utf-8") for path in PRODUCT_RUNTIME_FILES)
        for token in ("Access-Control-Allow-Origin", "XMLHttpRequest", "WebSocket", "EventSource", "requests.", "httpx.", "aiohttp."):
            self.assertNotIn(token, sources)
        web = (ROOT / "authoring/studio/web/studio.js").read_text(encoding="utf-8")
        self.assertIn("const STORAGE_KEY = 'learnit.authoring.m3.v1';", web)
        self.assertNotIn("indexedDB.open", web)


@unittest.skipUnless(sync_playwright is not None and PRODUCT_IMPORT_ERROR is None, "browser/product dependency unavailable")
class BrowserAdversarialTests(unittest.TestCase):
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

    def setUp(self) -> None:
        self.context = self.browser.new_context(accept_downloads=True)
        self.external: list[str] = []

        def route_handler(route):
            if not route.request.url.startswith(self.url):
                self.external.append(route.request.url)
                route.abort()
            else:
                route.continue_()

        self.context.route("**/*", route_handler)
        self.page = self.context.new_page()
        self.page.goto(self.url, wait_until="domcontentloaded")
        self.page.evaluate("""async () => {
          localStorage.setItem('qa-independent-learner-sentinel','keep');
          await new Promise((resolve,reject) => {
            const req=indexedDB.open('qa-independent-learner-db',1);
            req.onupgradeneeded=()=>req.result.createObjectStore('sentinel');
            req.onsuccess=()=>{req.result.close();resolve();};
            req.onerror=()=>reject(req.error);
          });
        }""")

    def tearDown(self) -> None:
        self.assertEqual([], self.external)
        self.context.close()

    def import_kit(self, path: Path) -> None:
        self.page.locator("#kit-file").set_input_files(str(path))
        self.page.wait_for_function("() => !document.querySelector('#workspace').hidden")
        self.page.wait_for_function("() => !document.querySelector('#export').disabled")

    def test_13_reload_edit_preview_export_reimport_and_storage_isolation(self) -> None:
        self.import_kit(KITS[0])
        self.assertTrue(self.page.evaluate(f"() => Boolean(localStorage.getItem('{NAMESPACE}'))"))
        self.assertEqual("keep", self.page.evaluate("() => localStorage.getItem('qa-independent-learner-sentinel')"))
        self.page.reload(wait_until="domcontentloaded")
        self.page.wait_for_function("() => !document.querySelector('#workspace').hidden")
        prompt = self.page.locator("#activity-fields textarea").first
        prompt.fill("QA navigateur : quel est le conjugué de 2 + 3i ?")
        prompt.blur()
        self.page.wait_for_function("() => !document.querySelector('#export').disabled")
        self.page.locator("#refresh-preview").click()
        self.page.get_by_text("Aperçu auteur uniquement", exact=False).first.wait_for(state="visible")
        with self.page.expect_download() as info:
            self.page.locator("#export").click()
        download = info.value
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            export_path = Path(handle.name)
        try:
            download.save_as(str(export_path))
            exported = export_path.read_bytes()
            self.assertTrue(validate_draft(create_draft(exported, "browser-export.json"))["ok"])
        finally:
            export_path.unlink(missing_ok=True)
        self.assertEqual("keep", self.page.evaluate("() => localStorage.getItem('qa-independent-learner-sentinel')"))
        names = self.page.evaluate("async () => (await indexedDB.databases()).map(x => x.name)")
        self.assertIn("qa-independent-learner-db", names)

    def test_14_fake_green_is_impossible_when_canonical_validation_rejects(self) -> None:
        self.import_kit(KITS[0])
        phase = self.page.locator("#activity-fields select").nth(1)
        phase.select_option("validation")
        self.page.wait_for_function("() => document.querySelector('#export').disabled")
        self.page.get_by_text("Erreur bloquante", exact=False).first.wait_for(state="visible")
        badge = self.page.locator("#validation-badge").inner_text()
        self.assertNotIn("export possible", badge.lower())

    def test_15_discard_clears_only_authoring_state(self) -> None:
        self.import_kit(KITS[1])
        self.page.on("dialog", lambda dialog: dialog.accept())
        self.page.locator("#discard").click()
        self.page.wait_for_function(f"() => !localStorage.getItem('{NAMESPACE}')")
        self.assertEqual("keep", self.page.evaluate("() => localStorage.getItem('qa-independent-learner-sentinel')"))
        names = self.page.evaluate("async () => (await indexedDB.databases()).map(x => x.name)")
        self.assertIn("qa-independent-learner-db", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
