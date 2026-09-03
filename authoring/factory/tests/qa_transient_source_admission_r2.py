#!/usr/bin/env python3
"""Independent contradictory QA for QA-WP-026 at frozen product HEAD.

Authority: GitHub issue #346 only. This suite intentionally does not import or
reuse QA-WP-025 QA files. Product suites are regression evidence only and are
run separately by the QA workflow.
"""
from __future__ import annotations

import ast
import copy
import io
import json
from pathlib import Path
import tempfile
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import handoff
from authoring.factory import reliability
from authoring.factory import release_set
from authoring.factory import source_admission as benchmark_admission
from authoring.factory import transient_source_admission as transient

FROZEN_PRODUCT_HEAD = "9e95fc79d84828da264c70b334719c31aa93e792"
PRODUCT_BASE = "e90940130b540f57abb999c56a24015c6b470249"
SIGNALS = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"
ZERO_SHA = "sha256:" + "0" * 64


def write_json(path: Path, value: object) -> None:
    path.write_bytes(factory.canonical_json_bytes(value))


def transient_declaration(source_id: str, version: str = "qa-v1") -> dict:
    return {
        "schema": transient.DECLARATION_SCHEMA,
        "profile": transient.DECLARATION_PROFILE,
        "declarationVersion": transient.DECLARATION_VERSION,
        "sourceId": source_id,
        "version": version,
        "provenance": transient.PROVENANCE,
        "processingContext": transient.PROCESSING_CONTEXT,
        "authorizationBasis": transient.AUTHORIZATION_BASIS,
        "userDeclarationAccepted": True,
        "retention": transient.RETENTION,
        "redistribution": transient.REDISTRIBUTION,
        "legalRightsVerified": False,
    }


def semantic_review(
    context: dict,
    source_id: str,
    *,
    scratchpad_seen: bool = False,
    active_context_reused: bool = False,
) -> dict:
    dimensions = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": source_id,
                "locator": "qa-section-1",
                "basis": f"Independent QA evidence for {name}.",
            }]
        dimensions[name] = {
            "status": "pass",
            "summary": f"Independent contradictory QA {name} assessment.",
            "evidence": evidence,
        }
    verdict = (
        factory.SEMANTIC_HOLD
        if scratchpad_seen or active_context_reused
        else factory.SEMANTIC_PASS
    )
    return {
        "schema": factory.REVIEW_SCHEMA,
        "profile": factory.REVIEW_PROFILE,
        "target": handoff.target_from_context(context),
        "independence": {
            "authorScratchpadSeen": scratchpad_seen,
            "authorActiveContextReused": active_context_reused,
        },
        "dimensions": dimensions,
        "findings": [],
        "limitations": [],
        "verdict": verdict,
    }


class TransientWorkspace:
    def __init__(self, root: Path, source_id: str = "qa.user-private_course.01"):
        self.root = root
        self.source_id = source_id
        self.kit = root / "candidate.json"
        self.brief = root / "brief.json"
        self.source = root / "private-course.pdf"
        self.declaration = root / "declaration.json"
        self.admission = root / "admission.json"
        self.bundle = root / "handoff.zip"
        self.review = root / "review.json"
        self.run = root / "factory-run.json"
        self.release = root / "release.zip"

        self.kit.write_bytes(SIGNALS.read_bytes())
        write_json(self.brief, {
            "schema": factory.BRIEF_SCHEMA,
            "audience": "EPF engineering student",
            "goal": "Exercise the exact private-source handoff boundary",
            "language": "fr",
            "timeBudgetMinutes": 45,
        })
        self.source.write_bytes(b"%PDF-1.7\nindependent QA private source\n")
        self.refresh_admission()

    def refresh_admission(self, version: str = "qa-v1") -> dict:
        declaration = transient_declaration(self.source_id, version)
        write_json(self.declaration, declaration)
        record = transient.build_admission(declaration, self.source)
        write_json(self.admission, record)
        return record

    @property
    def source_specs(self) -> list[str]:
        return [f"{self.source_id}={self.source}"]

    @property
    def admission_specs(self) -> list[str]:
        return [f"{self.source_id}={self.admission}"]

    def prepare(self) -> dict:
        return handoff.prepare_review_bundle(
            self.kit, self.brief, self.source_specs, self.admission_specs, self.bundle
        )

    def verify(self) -> dict:
        return handoff.verify_review_bundle(self.bundle)

    def write_review(self, **kwargs) -> dict:
        context = self.verify()["context"]
        review = semantic_review(context, self.source_id, **kwargs)
        write_json(self.review, review)
        return review

    def consume(self) -> dict:
        return handoff.consume_review_bundle(self.bundle, self.review, self.run)


class BenchmarkWorkspace:
    def __init__(self, root: Path):
        self.root = root
        self.kit = root / "candidate.json"
        self.brief = root / "brief.json"
        self.source = root / "benchmark.txt"
        self.admission = root / "benchmark-admission.json"
        self.bundle = root / "benchmark-handoff.zip"
        self.binding_id = "qa_benchmark_alias"

        self.kit.write_bytes(SIGNALS.read_bytes())
        write_json(self.brief, {
            "schema": factory.BRIEF_SCHEMA,
            "audience": "benchmark QA learner",
            "goal": "Prove curated benchmark authority is unchanged",
            "language": "fr",
            "timeBudgetMinutes": 45,
        })
        self.source.write_bytes(b"independent benchmark bytes\n")

        catalog, catalog_sha = benchmark_admission.load_catalog(handoff.CATALOG_PATH)
        self.catalog = catalog
        self.catalog_sha = catalog_sha
        self.catalog_row = next(
            row for row in catalog["sources"]
            if row["benchmarkRole"] == "primary"
            and row["rights"]["status"] in {"allowed", "conditional"}
            and row["rights"]["thirdPartyContentStatus"] != "present-unresolved"
            and catalog["defaultUseContext"] in row["rights"]["allowedUseContexts"]
        )
        strategy = self.catalog_row["version"]["strategy"]
        version = (
            self.catalog_row["version"]["value"]
            if strategy == "fixed"
            else "qa-benchmark-v1"
        )
        record = benchmark_admission.build_admission(
            catalog,
            catalog_sha,
            self.catalog_row["sourceId"],
            catalog["defaultUseContext"],
            self.source,
            list(self.catalog_row["rights"]["conditions"]),
            version,
        )
        if record["decision"]["verdict"] != benchmark_admission.PASS:
            raise AssertionError("independent benchmark fixture did not produce PASS")
        write_json(self.admission, record)

    def prepare(self) -> dict:
        return handoff.prepare_review_bundle(
            self.kit,
            self.brief,
            [f"{self.binding_id}={self.source}"],
            [f"{self.binding_id}={self.admission}"],
            self.bundle,
        )


def zip_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as zf:
        return {info.filename: zf.read(info) for info in zf.infolist()}


def rewrite_manifest(members: dict[str, bytes], mutate) -> None:
    manifest = json.loads(members["review-handoff.json"].decode("utf-8"))
    mutate(manifest)
    core = {key: value for key, value in manifest.items() if key != "bundleDigest"}
    manifest["bundleDigest"] = handoff.digest(core)
    members["review-handoff.json"] = handoff.canonical(manifest)


def write_canonical_zip(path: Path, members: dict[str, bytes]) -> None:
    path.write_bytes(handoff.zip_bytes(members))


def write_raw_entries(path: Path, entries: list[tuple[str, bytes]]) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
        for name, data in sorted(entries, key=lambda item: item[0]):
            info = zipfile.ZipInfo(name, handoff.FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = handoff.FILE_MODE << 16
            info.flag_bits = 0
            zf.writestr(info, data)
    path.write_bytes(buffer.getvalue())


class F01RepairAndIdentityBoundaryTests(unittest.TestCase):
    def test_f01_colon_identity_is_rejected_at_declaration_before_bytes(self):
        declaration = transient_declaration("user:private-course")
        self.assertIsNone(factory.SOURCE_ID.fullmatch(declaration["sourceId"]))
        missing = Path("/definitely/not/read/by/pre-ingestion/source.pdf")
        with self.assertRaisesRegex(transient.TransientSourceAdmissionError, "invalid sourceId"):
            transient.build_admission(declaration, missing)

    def test_transient_uses_exact_promoted_m3_2_m3_3_identity_authority(self):
        self.assertIs(transient.SOURCE_ID, factory.SOURCE_ID)
        self.assertEqual(r"^[A-Za-z0-9._-]+$", factory.SOURCE_ID.pattern)
        self.assertIs(handoff.factory.SOURCE_ID, factory.SOURCE_ID)
        self.assertIs(reliability.factory.SOURCE_ID, factory.SOURCE_ID)

    def test_nontrivial_dot_dash_underscore_identity_crosses_prepare_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td), "user.private-course_01")
            record = json.loads(ws.admission.read_text(encoding="utf-8"))
            self.assertEqual(transient.PASS, record["decision"]["verdict"])
            prepared = ws.prepare()
            self.assertEqual(handoff.PASS_PREPARED, prepared["verdict"])
            verified = ws.verify()
            self.assertEqual([ws.source_id], verified["manifest"]["reviewEvidenceSourceIds"])

    def test_edge_identities_admitted_by_grammar_cross_m3_3(self):
        for source_id in [".", "..", "-", "_", "._-", "a.", "a-", "a_", "A0._-"]:
            with self.subTest(source_id=source_id), tempfile.TemporaryDirectory() as td:
                ws = TransientWorkspace(Path(td), source_id)
                record = json.loads(ws.admission.read_text(encoding="utf-8"))
                self.assertEqual(transient.PASS, record["decision"]["verdict"])
                self.assertEqual(handoff.PASS_PREPARED, ws.prepare()["verdict"])
                ws.verify()

    def test_every_accepted_identity_must_be_portable_across_m3_3_long_component(self):
        source_id = "a" * 300
        self.assertIsNotNone(transient.SOURCE_ID.fullmatch(source_id))
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td), source_id)
            record = json.loads(ws.admission.read_text(encoding="utf-8"))
            self.assertEqual(transient.PASS, record["decision"]["verdict"])
            factory.parse_sources(ws.source_specs)
            handoff.parse_bindings(ws.source_specs, "source")
            try:
                prepared = ws.prepare()
            except OSError as exc:
                self.fail(
                    "accepted transient sourceId cannot cross M3.3 filesystem materialization: "
                    f"{exc}"
                )
            self.assertEqual(handoff.PASS_PREPARED, prepared["verdict"])
            ws.verify()


class FalsePassAndPreIngestionTests(unittest.TestCase):
    def test_policy_false_pass_mutants_hold_without_reading_source_bytes(self):
        mutants = [
            ({"provenance": "platform-catalog"}, transient.HOLD_DECLARATION),
            ({"authorizationBasis": "implicit"}, transient.HOLD_DECLARATION),
            ({"userDeclarationAccepted": False}, transient.HOLD_DECLARATION),
            ({"processingContext": "public-demo"}, transient.HOLD_CONTEXT),
            ({"retention": "persistent"}, transient.HOLD_RETENTION),
            ({"redistribution": "allowed"}, transient.HOLD_REDISTRIBUTION),
            ({"legalRightsVerified": True}, transient.HOLD_LEGAL_CLAIM),
        ]
        for patch, expected in mutants:
            with self.subTest(patch=patch):
                declaration = transient_declaration("qa_policy")
                declaration.update(patch)
                missing = Path("/definitely/not/read/by/pre-ingestion/payload.bin")
                record = transient.build_admission(declaration, missing)
                self.assertEqual(expected, record["decision"]["verdict"])
                self.assertTrue(record["preIngestionHold"])
                self.assertIsNone(record["content"])
                transient.verify_admission(record)

    def test_valid_declaration_without_bytes_is_a_pre_ingestion_hold(self):
        record = transient.build_admission(transient_declaration("qa_missing_bytes"), None)
        self.assertEqual(transient.HOLD_BYTES, record["decision"]["verdict"])
        self.assertTrue(record["preIngestionHold"])
        self.assertIsNone(record["content"])

    def test_source_byte_drift_fails_replay(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.bin"
            source.write_bytes(b"original")
            record = transient.build_admission(transient_declaration("qa_drift"), source)
            source.write_bytes(b"changed")
            with self.assertRaisesRegex(transient.TransientSourceAdmissionError, "not reproducible"):
                transient.reproduce_admission(record, source)

    def test_declaration_source_id_and_version_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.bin"
            source.write_bytes(b"stable")
            baseline = transient.build_admission(transient_declaration("qa_decl", "v1"), source)
            for key, value in [("sourceId", "qa_decl_changed"), ("version", "v2")]:
                mutant = copy.deepcopy(baseline)
                mutant["declaration"][key] = value
                with self.subTest(key=key):
                    with self.assertRaises(transient.TransientSourceAdmissionError):
                        transient.verify_admission(mutant)

    def test_host_path_relocation_is_deterministic_for_admission_and_handoff(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            left = TransientWorkspace(Path(a), "qa.relocated-source_01")
            right = TransientWorkspace(Path(b), "qa.relocated-source_01")
            self.assertEqual(left.admission.read_bytes(), right.admission.read_bytes())
            left.prepare(); right.prepare()
            self.assertEqual(left.bundle.read_bytes(), right.bundle.read_bytes())


class AuthoritySeparationTests(unittest.TestCase):
    def test_benchmark_authority_still_passes_and_embeds_exact_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            ws = BenchmarkWorkspace(Path(td))
            ws.prepare()
            verified = handoff.verify_review_bundle(ws.bundle)
            catalog_path = handoff.OPTIONAL_ROLE_PATHS["source-catalog"]
            self.assertIn(catalog_path, verified["members"])
            self.assertEqual(handoff.CATALOG_PATH.read_bytes(), verified["members"][catalog_path])

    def test_benchmark_admission_without_catalog_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = BenchmarkWorkspace(root)
            ws.prepare()
            members = zip_members(ws.bundle)
            catalog_path = handoff.OPTIONAL_ROLE_PATHS["source-catalog"]
            del members[catalog_path]
            rewrite_manifest(
                members,
                lambda manifest: manifest.__setitem__(
                    "artifacts",
                    [row for row in manifest["artifacts"] if row["role"] != "source-catalog"],
                ),
            )
            broken = root / "benchmark-no-catalog.zip"
            write_canonical_zip(broken, members)
            with self.assertRaisesRegex(handoff.HandoffInputError, "requires embedded source catalog"):
                handoff.verify_review_bundle(broken)

    def test_transient_only_bundle_excludes_and_rejects_benchmark_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = TransientWorkspace(root)
            ws.prepare()
            verified = ws.verify()
            catalog_path = handoff.OPTIONAL_ROLE_PATHS["source-catalog"]
            self.assertNotIn(catalog_path, verified["members"])

            members = zip_members(ws.bundle)
            catalog_bytes = handoff.CATALOG_PATH.read_bytes()
            members[catalog_path] = catalog_bytes
            def add_catalog(manifest: dict) -> None:
                manifest["artifacts"].append(
                    handoff.artifact("source-catalog", catalog_path, catalog_bytes)
                )
                manifest["artifacts"].sort(key=lambda row: row["path"])
            rewrite_manifest(members, add_catalog)
            injected = root / "transient-with-catalog.zip"
            write_canonical_zip(injected, members)
            with self.assertRaisesRegex(handoff.HandoffInputError, "forbidden when no benchmark"):
                handoff.verify_review_bundle(injected)

    def test_unknown_or_confused_admission_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = TransientWorkspace(root)
            record = json.loads(ws.admission.read_text(encoding="utf-8"))
            record["schema"] = "learnit.atlas.source_admission.confused.v1"
            write_json(ws.admission, record)
            with self.assertRaisesRegex(handoff.HandoffInputError, "unsupported admission schema"):
                ws.prepare()


class ArchiveContradictionTests(unittest.TestCase):
    def _valid(self, root: Path) -> TransientWorkspace:
        ws = TransientWorkspace(root)
        ws.prepare()
        ws.verify()
        return ws

    def test_tampered_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); ws = self._valid(root)
            members = zip_members(ws.bundle)
            members[handoff.ROLE_PATHS["candidate"]] += b"\n"
            bad = root / "tampered.zip"
            write_canonical_zip(bad, members)
            with self.assertRaisesRegex(handoff.HandoffInputError, "artifact digest mismatch"):
                handoff.verify_review_bundle(bad)

    def test_undeclared_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); ws = self._valid(root)
            members = zip_members(ws.bundle)
            members["undeclared.bin"] = b"x"
            bad = root / "extra.zip"
            write_canonical_zip(bad, members)
            with self.assertRaisesRegex(handoff.HandoffInputError, "archive members mismatch"):
                handoff.verify_review_bundle(bad)

    def test_duplicate_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); ws = self._valid(root)
            members = zip_members(ws.bundle)
            duplicate_name = handoff.ROLE_PATHS["candidate"]
            entries = list(members.items()) + [(duplicate_name, members[duplicate_name])]
            bad = root / "duplicate.zip"
            write_raw_entries(bad, entries)
            with self.assertRaisesRegex(handoff.HandoffInputError, "duplicate members"):
                handoff.verify_review_bundle(bad)

    def test_unsafe_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); ws = self._valid(root)
            members = zip_members(ws.bundle)
            entries = list(members.items()) + [("../escape", b"x")]
            bad = root / "unsafe.zip"
            write_raw_entries(bad, entries)
            with self.assertRaisesRegex(handoff.HandoffInputError, "unsafe archive path"):
                handoff.verify_review_bundle(bad)


class ReviewIsolationTests(unittest.TestCase):
    def test_stale_target_is_rejected_before_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td)); ws.prepare()
            review = ws.write_review()
            review["target"]["contextDigest"] = ZERO_SHA
            write_json(ws.review, review)
            with self.assertRaisesRegex(handoff.HandoffInputError, "target mismatch"):
                ws.consume()
            self.assertFalse(ws.run.exists())

    def test_reviewer_evidence_source_id_injection_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td)); ws.prepare()
            review = ws.write_review()
            review["dimensions"]["sourceFidelity"]["evidence"][0]["sourceId"] = "injected"
            write_json(ws.review, review)
            with self.assertRaises(handoff.HandoffInputError):
                ws.consume()
            self.assertFalse(ws.run.exists())

    def test_author_scratchpad_seen_true_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td)); ws.prepare()
            ws.write_review(scratchpad_seen=True)
            with self.assertRaisesRegex(handoff.HandoffInputError, "authorScratchpadSeen=true"):
                ws.consume()

    def test_author_active_context_reused_true_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td)); ws.prepare()
            ws.write_review(active_context_reused=True)
            with self.assertRaisesRegex(handoff.HandoffInputError, "authorActiveContextReused=true"):
                ws.consume()


class DownstreamReleaseBoundaryTests(unittest.TestCase):
    def test_reviewer_has_source_but_qualified_release_set_excludes_source_material(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = TransientWorkspace(root, "qa.release-source_01")
            ws.prepare()
            handoff_members = ws.verify()["members"]
            self.assertTrue(any(name.startswith("sources/") for name in handoff_members))
            self.assertTrue(any(name.startswith("source-admission/") for name in handoff_members))

            ws.write_review()
            consumed = ws.consume()
            self.assertEqual(handoff.PASS_CONSUMED, consumed["verdict"])
            run = json.loads(ws.run.read_text(encoding="utf-8"))
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", run["decision"]["verdict"])
            reliability.verify_run(copy.deepcopy(run))

            result = release_set.build_release_archive(
                [f"{ws.run}={ws.kit}"], ws.release
            )
            self.assertEqual(release_set.PASS_BUILT, result["verdict"])
            verified_release = release_set.verify_release_archive(ws.release)
            self.assertEqual(release_set.PASS_VERIFIED, verified_release["verdict"])
            with zipfile.ZipFile(ws.release, "r") as zf:
                names = zf.namelist()
            self.assertFalse(any(name.startswith("sources/") for name in names))
            self.assertFalse(any(name.startswith("source-admission/") for name in names))
            self.assertNotIn("source-catalog.json", names)


class NoExpansionStaticTests(unittest.TestCase):
    def test_transient_authority_has_no_network_provider_or_persistent_write_surface(self):
        source_path = ROOT / "authoring/factory/transient_source_admission.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        persistent_calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"write_bytes", "write_text", "mkdir"}:
                    persistent_calls.append(node.func.attr)
        self.assertTrue(imports.isdisjoint({"requests", "urllib", "httpx", "aiohttp", "socket"}))
        self.assertEqual([], persistent_calls)

    def test_benchmark_source_id_authority_remains_distinct_from_factory_binding_grammar(self):
        self.assertEqual(
            r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$",
            benchmark_admission.SOURCE_ID.pattern,
        )
        catalog, _ = benchmark_admission.load_catalog(handoff.CATALOG_PATH)
        self.assertTrue(any(":" in row["sourceId"] for row in catalog["sources"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
