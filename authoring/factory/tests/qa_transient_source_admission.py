#!/usr/bin/env python3
"""Independent contradictory oracle for QA-WP-025 / issue #344.

Product paths are read-only. These tests are designed from the issue contract
and public implementation surface, not from the product author's test rationale.
"""
from __future__ import annotations

import ast
import copy
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import handoff
from authoring.factory import reliability
from authoring.factory import release_set
from authoring.factory import source_admission
from authoring.factory import transient_source_admission as transient

SIGNALS = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"
PRODUCT_TRANSIENT = ROOT / "authoring/factory/transient_source_admission.py"
PRODUCT_HANDOFF = ROOT / "authoring/factory/handoff.py"


class NeverRead:
    """Source stand-in proving a policy HOLD occurs before byte ingestion."""

    def __init__(self) -> None:
        self.calls = 0

    def read_bytes(self) -> bytes:
        self.calls += 1
        raise AssertionError("policy-invalid declaration attempted to read source bytes")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def declaration(source_id: str = "private_course", version: str = "qa-v1", **overrides) -> dict:
    value = {
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
    value.update(overrides)
    return value


def semantic_review(context: dict, source_id: str, *, scratchpad=False, active=False) -> dict:
    dimensions = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": source_id,
                "locator": "qa-exact-source",
                "basis": f"Independent QA evidence for {name}.",
            }]
        dimensions[name] = {
            "status": "pass",
            "summary": f"Independent {name} check completed.",
            "evidence": evidence,
        }
    return {
        "schema": factory.REVIEW_SCHEMA,
        "profile": factory.REVIEW_PROFILE,
        "target": handoff.target_from_context(context),
        "independence": {
            "authorScratchpadSeen": scratchpad,
            "authorActiveContextReused": active,
        },
        "dimensions": dimensions,
        "findings": [],
        "limitations": [],
        "verdict": factory.SEMANTIC_PASS,
    }


def archive_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as zf:
        return {info.filename: zf.read(info) for info in zf.infolist()}


def rewrite_consistent_bundle(source: Path, destination: Path, mutate) -> None:
    """Mutate members, then refresh artifact rows + bundleDigest to reach deep checks."""
    members = archive_members(source)
    manifest = json.loads(members["review-handoff.json"].decode("utf-8"))
    mutate(members, manifest)

    artifacts_by_path = {row["path"]: row for row in manifest["artifacts"]}
    for name, row in artifacts_by_path.items():
        if name not in members:
            continue
        row["bytes"] = len(members[name])
        row["sha256"] = handoff.sha(members[name])
    manifest["artifacts"] = sorted(manifest["artifacts"], key=lambda row: row["path"])
    core = {key: value for key, value in manifest.items() if key != "bundleDigest"}
    manifest["bundleDigest"] = handoff.digest(core)
    members["review-handoff.json"] = handoff.canonical(manifest)
    destination.write_bytes(handoff.zip_bytes(members))


class TransientWorkspace:
    def __init__(self, root: Path, source_id: str = "private_course", version: str = "qa-v1"):
        self.root = root
        self.source_id = source_id
        self.version = version
        self.kit = root / "candidate.json"
        self.brief = root / "brief.json"
        self.source = root / "private-source.bin"
        self.admission = root / "transient-admission.json"
        self.bundle = root / "review-handoff.zip"
        self.review = root / "review.json"
        self.run = root / "factory-run.json"
        self.release = root / "qualified-release.zip"

        self.kit.write_bytes(SIGNALS.read_bytes())
        write_json(self.brief, {
            "schema": factory.BRIEF_SCHEMA,
            "audience": "élève ingénieur",
            "goal": "Comprendre et appliquer le cours privé fourni par l'utilisateur",
            "language": "fr",
            "timeBudgetMinutes": 45,
        })
        self.source.write_bytes(
            b"QA-WP-025-PRIVATE-SOURCE-BYTES-9db07a4f8d7e4bd995d5\n"
        )
        record = transient.build_admission(declaration(source_id, version), self.source)
        if record["decision"]["verdict"] != transient.PASS:
            raise AssertionError(record)
        write_json(self.admission, record)

    def prepare(self) -> dict:
        return handoff.prepare_review_bundle(
            self.kit,
            self.brief,
            [f"{self.source_id}={self.source}"],
            [f"{self.source_id}={self.admission}"],
            self.bundle,
        )

    def verify(self) -> dict:
        return handoff.verify_review_bundle(self.bundle)

    def write_review(self, *, scratchpad=False, active=False) -> dict:
        verified = self.verify()
        value = semantic_review(
            verified["context"], self.source_id, scratchpad=scratchpad, active=active
        )
        write_json(self.review, value)
        return value

    def consume(self) -> dict:
        return handoff.consume_review_bundle(self.bundle, self.review, self.run)


class FalsePassAndPreIngestionTests(unittest.TestCase):
    def test_01_upload_presence_without_declaration_never_passes_or_reads(self):
        source = NeverRead()
        with self.assertRaises(transient.TransientSourceAdmissionError):
            transient.build_admission(None, source)  # type: ignore[arg-type]
        self.assertEqual(0, source.calls)

    def test_02_policy_invalid_matrix_holds_before_source_read(self):
        cases = [
            ("declaration-false", {"userDeclarationAccepted": False}, transient.HOLD_DECLARATION),
            ("provenance", {"provenance": "repository-provided"}, transient.HOLD_DECLARATION),
            ("authorization", {"authorizationBasis": "upload-presence"}, transient.HOLD_DECLARATION),
            ("context", {"processingContext": "public-publication"}, transient.HOLD_CONTEXT),
            ("retention", {"retention": "persistent"}, transient.HOLD_RETENTION),
            ("redistribution-allowed", {"redistribution": "allowed"}, transient.HOLD_REDISTRIBUTION),
            ("redistribution-requested", {"redistribution": "requested"}, transient.HOLD_REDISTRIBUTION),
            ("legal-rights", {"legalRightsVerified": True}, transient.HOLD_LEGAL_CLAIM),
        ]
        for name, overrides, expected in cases:
            with self.subTest(name=name):
                source = NeverRead()
                record = transient.build_admission(declaration(**overrides), source)  # type: ignore[arg-type]
                self.assertEqual(expected, record["decision"]["verdict"])
                self.assertTrue(record["preIngestionHold"])
                self.assertIsNone(record["content"])
                self.assertEqual(0, source.calls)
                transient.verify_admission(record)

    def test_03_invalid_policy_holds_with_absent_source_path(self):
        missing = Path("/definitely/not/present/qa-wp-025-private-source")
        record = transient.build_admission(
            declaration(retention="persistent"),
            missing,
        )
        self.assertEqual(transient.HOLD_RETENTION, record["decision"]["verdict"])
        self.assertIsNone(record["content"])
        self.assertTrue(record["preIngestionHold"])

    def test_04_malformed_or_missing_identity_and_version_never_reads_bytes(self):
        cases = []
        for key in ("sourceId", "version"):
            missing = declaration()
            del missing[key]
            cases.append((f"missing-{key}", missing))
        cases.extend([
            ("empty-sourceId", declaration(source_id="")),
            ("space-sourceId", declaration(source_id="bad source")),
            ("empty-version", declaration(version="")),
            ("slash-version", declaration(version="bad/version")),
        ])
        for name, value in cases:
            with self.subTest(name=name):
                source = NeverRead()
                with self.assertRaises(transient.TransientSourceAdmissionError):
                    transient.build_admission(value, source)  # type: ignore[arg-type]
                self.assertEqual(0, source.calls)

    def test_05_boolean_claims_are_type_strict(self):
        for key, bad in (("userDeclarationAccepted", 1), ("legalRightsVerified", 0)):
            with self.subTest(key=key):
                with self.assertRaises(transient.TransientSourceAdmissionError):
                    transient.build_admission(declaration(**{key: bad}), None)

    def test_06_policy_valid_declaration_without_bytes_is_hold(self):
        record = transient.build_admission(declaration(), None)
        self.assertEqual(transient.HOLD_BYTES, record["decision"]["verdict"])
        self.assertTrue(record["preIngestionHold"])
        self.assertIsNone(record["content"])
        transient.verify_admission(record)


class ExactBindingTests(unittest.TestCase):
    def test_07_valid_declaration_and_exact_bytes_pass(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.bin"
            source.write_bytes(b"exact private bytes\n")
            record = transient.build_admission(declaration(), source)
            self.assertEqual(transient.PASS, record["decision"]["verdict"])
            self.assertFalse(record["preIngestionHold"])
            self.assertEqual(len(source.read_bytes()), record["content"]["bytes"])
            self.assertEqual(factory.sha256_bytes(source.read_bytes()), record["content"]["sha256"])
            transient.verify_admission(record)
            transient.reproduce_admission(record, source)

    def test_08_one_byte_source_drift_fails_reproduction(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.bin"
            source.write_bytes(b"abc")
            record = transient.build_admission(declaration(), source)
            source.write_bytes(b"abd")
            with self.assertRaises(transient.TransientSourceAdmissionError):
                transient.reproduce_admission(record, source)

    def test_09_declaration_policy_drift_cannot_forge_pass_even_after_digest_recompute(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.bin"
            source.write_bytes(b"source")
            record = transient.build_admission(declaration(), source)
            forged = copy.deepcopy(record)
            forged["declaration"]["redistribution"] = "allowed"
            forged["declarationDigest"] = transient.digest(forged["declaration"])
            core = {key: value for key, value in forged.items() if key != "admissionId"}
            forged["admissionId"] = transient.digest(core)
            with self.assertRaises(transient.TransientSourceAdmissionError):
                transient.verify_admission(forged)

    def test_10_source_id_and_version_drift_break_frozen_admission(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.bin"
            source.write_bytes(b"source")
            original = transient.build_admission(declaration(), source)
            for key, changed in (("sourceId", "other_source"), ("version", "qa-v2")):
                with self.subTest(key=key):
                    tampered = copy.deepcopy(original)
                    tampered["declaration"][key] = changed
                    with self.assertRaises(transient.TransientSourceAdmissionError):
                        transient.verify_admission(tampered)

    def test_11_host_path_relocation_and_replay_are_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = Path(a) / "source-one.pdf"
            second = Path(b) / "renamed-anything.bin"
            payload = b"same exact bytes\n"
            first.write_bytes(payload)
            second.write_bytes(payload)
            decl = declaration()
            one = transient.build_admission(decl, first)
            two = transient.build_admission(copy.deepcopy(decl), second)
            three = transient.build_admission(copy.deepcopy(decl), first)
            self.assertEqual(one, two)
            self.assertEqual(one, three)
            self.assertEqual(one["admissionId"], two["admissionId"])

    def test_12_transient_pass_source_identity_must_cross_m3_3_boundary(self):
        """A transient PASS must not authorize an identity M3.3 cannot bind."""
        source_id = "user:private-course"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.bin"
            source.write_bytes(b"private course bytes\n")
            admission = root / "admission.json"
            record = transient.build_admission(declaration(source_id=source_id), source)
            self.assertEqual(
                transient.PASS,
                record["decision"]["verdict"],
                "precondition: transient authority must currently regard the identity as valid",
            )
            write_json(admission, record)

            try:
                handoff.prepare_review_bundle(
                    root / "unused-kit.json",
                    root / "unused-brief.json",
                    [f"{source_id}={source}"],
                    [f"{source_id}={admission}"],
                    root / "out.zip",
                )
            except handoff.HandoffInputError as exc:
                self.fail(
                    "QA-WP-025-F01: PASS_TRANSIENT_SOURCE_ADMISSION_V1 accepted "
                    f"sourceId={source_id!r}, but the mandated M3.3 handoff rejects that "
                    f"same identity: {exc}"
                )


class AuthorityAndHandoffTests(unittest.TestCase):
    def _benchmark_workspace(self, root: Path) -> tuple[Path, Path, Path, Path, Path, str]:
        kit = root / "candidate.json"
        brief = root / "brief.json"
        source = root / "benchmark-source.bin"
        admission_path = root / "benchmark-admission.json"
        bundle = root / "benchmark-handoff.zip"
        logical_id = "benchmark_qa"
        kit.write_bytes(SIGNALS.read_bytes())
        write_json(brief, {
            "schema": factory.BRIEF_SCHEMA,
            "audience": "élève ingénieur",
            "goal": "QA benchmark handoff",
            "language": "fr",
            "timeBudgetMinutes": 45,
        })
        source.write_bytes(b"benchmark bytes for transport regression\n")
        catalog, catalog_sha = source_admission.load_catalog(handoff.CATALOG_PATH)
        source_id = "eu:pm2-v3.1"
        row = source_admission.source_by_id(catalog, source_id)
        strategy = row["version"]["strategy"]
        version = row["version"]["value"] if strategy == "fixed" else "qa-v1"
        record = source_admission.build_admission(
            catalog,
            catalog_sha,
            source_id,
            catalog["defaultUseContext"],
            source,
            list(row["rights"]["conditions"]),
            version,
        )
        self.assertEqual(source_admission.PASS, record["decision"]["verdict"])
        write_json(admission_path, record)
        return kit, brief, source, admission_path, bundle, logical_id

    def test_13_transient_source_admission_binding_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = TransientWorkspace(root, source_id="declared_source")
            with self.assertRaises(handoff.HandoffInputError):
                handoff.prepare_review_bundle(
                    ws.kit,
                    ws.brief,
                    [f"bound_source={ws.source}"],
                    [f"bound_source={ws.admission}"],
                    ws.bundle,
                )

    def test_14_schema_masquerade_fails_both_directions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.bin"
            source.write_bytes(b"x")
            transient_record = transient.build_admission(declaration(), source)

            fake_benchmark = copy.deepcopy(transient_record)
            fake_benchmark["schema"] = source_admission.ADMISSION_SCHEMA
            with self.assertRaises(source_admission.SourceAdmissionError):
                source_admission.verify_admission(fake_benchmark)

            catalog, catalog_sha = source_admission.load_catalog(handoff.CATALOG_PATH)
            benchmark_id = "eu:pm2-v3.1"
            row = source_admission.source_by_id(catalog, benchmark_id)
            benchmark = source_admission.build_admission(
                catalog,
                catalog_sha,
                benchmark_id,
                catalog["defaultUseContext"],
                source,
                list(row["rights"]["conditions"]),
                row["version"]["value"],
            )
            fake_transient = copy.deepcopy(benchmark)
            fake_transient["schema"] = transient.ADMISSION_SCHEMA
            with self.assertRaises(transient.TransientSourceAdmissionError):
                transient.verify_admission(fake_transient)

    def test_15_transient_bundle_omits_catalog_and_injected_catalog_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = TransientWorkspace(root)
            ws.prepare()
            verified = ws.verify()
            catalog_member = handoff.OPTIONAL_ROLE_PATHS["source-catalog"]
            self.assertNotIn(catalog_member, verified["members"])

            injected = root / "catalog-injected.zip"

            def mutate(members, manifest):
                catalog_raw = handoff.CATALOG_PATH.read_bytes()
                members[catalog_member] = catalog_raw
                manifest["artifacts"].append(
                    handoff.artifact("source-catalog", catalog_member, catalog_raw)
                )

            rewrite_consistent_bundle(ws.bundle, injected, mutate)
            with self.assertRaisesRegex(
                handoff.HandoffInputError,
                "forbidden when no benchmark SourceAdmission",
            ):
                handoff.verify_review_bundle(injected)

    def test_16_benchmark_path_still_requires_and_verifies_exact_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            kit, brief, source, admission, bundle, logical_id = self._benchmark_workspace(root)
            handoff.prepare_review_bundle(
                kit,
                brief,
                [f"{logical_id}={source}"],
                [f"{logical_id}={admission}"],
                bundle,
            )
            verified = handoff.verify_review_bundle(bundle)
            catalog_member = handoff.OPTIONAL_ROLE_PATHS["source-catalog"]
            self.assertEqual(handoff.CATALOG_PATH.read_bytes(), verified["members"][catalog_member])

            tampered = root / "catalog-tampered.zip"

            def mutate(members, manifest):
                members[catalog_member] = members[catalog_member] + b"\n"

            rewrite_consistent_bundle(bundle, tampered, mutate)
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(tampered)

    def test_17_malformed_or_tampered_transient_admission_in_bundle_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = TransientWorkspace(root)
            ws.prepare()
            admission_member = f"source-admission/{ws.source_id}.json"
            tampered = root / "tampered-admission.zip"

            def mutate(members, manifest):
                value = json.loads(members[admission_member].decode("utf-8"))
                del value["declarationDigest"]
                members[admission_member] = handoff.canonical(value)

            rewrite_consistent_bundle(ws.bundle, tampered, mutate)
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(tampered)

    def test_18_archive_duplicate_undeclared_and_unsafe_members_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = TransientWorkspace(root)
            ws.prepare()
            with zipfile.ZipFile(ws.bundle, "r") as zin:
                originals = [(info.filename, zin.read(info)) for info in zin.infolist()]

            extra = root / "extra.zip"
            members = dict(originals)
            members["undeclared.txt"] = b"x"
            extra.write_bytes(handoff.zip_bytes(members))
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(extra)

            duplicate = root / "duplicate.zip"
            raw = io.BytesIO()
            with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_STORED) as zout:
                for name, data in originals + [originals[0]]:
                    info = zipfile.ZipInfo(name, handoff.FIXED_ZIP_TIME)
                    info.compress_type = zipfile.ZIP_STORED
                    info.create_system = 3
                    info.external_attr = handoff.FILE_MODE << 16
                    zout.writestr(info, data)
            duplicate.write_bytes(raw.getvalue())
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(duplicate)

            unsafe = root / "unsafe.zip"
            raw = io.BytesIO()
            with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_STORED) as zout:
                for name, data in originals:
                    info = zipfile.ZipInfo(name, handoff.FIXED_ZIP_TIME)
                    info.compress_type = zipfile.ZIP_STORED
                    info.create_system = 3
                    info.external_attr = handoff.FILE_MODE << 16
                    zout.writestr(info, data)
                info = zipfile.ZipInfo("../escape", handoff.FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                zout.writestr(info, b"x")
            unsafe.write_bytes(raw.getvalue())
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(unsafe)

    def test_19_coherently_rehashed_target_drift_fails_against_embedded_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = TransientWorkspace(root)
            ws.prepare()
            drifted = root / "target-drift.zip"

            def mutate(members, manifest):
                manifest["target"]["contextDigest"] = "sha256:" + "0" * 64

            rewrite_consistent_bundle(ws.bundle, drifted, mutate)
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(drifted)

    def test_20_stale_review_and_evidence_source_injection_fail_before_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = TransientWorkspace(root)
            ws.prepare()

            stale = ws.write_review()
            stale["target"]["kitSha256"] = "sha256:" + "0" * 64
            write_json(ws.review, stale)
            with self.assertRaises(handoff.HandoffInputError):
                ws.consume()
            self.assertFalse(ws.run.exists())

            fresh = semantic_review(ws.verify()["context"], ws.source_id)
            fresh["dimensions"]["sourceFidelity"]["evidence"][0]["sourceId"] = "injected_source"
            write_json(ws.review, fresh)
            with self.assertRaises(handoff.HandoffInputError):
                ws.consume()
            self.assertFalse(ws.run.exists())

    def test_21_reviewer_independence_flags_fail_closed(self):
        for scratchpad, active in ((True, False), (False, True)):
            with self.subTest(scratchpad=scratchpad, active=active):
                with tempfile.TemporaryDirectory() as td:
                    ws = TransientWorkspace(Path(td))
                    ws.prepare()
                    ws.write_review(scratchpad=scratchpad, active=active)
                    with self.assertRaises(handoff.HandoffInputError):
                        ws.consume()
                    self.assertFalse(ws.run.exists())

    def test_22_exact_source_is_in_handoff_but_never_enters_qualified_release_set(self):
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td))
            ws.prepare()
            verified = ws.verify()
            source_members = [
                name for name in verified["members"] if name.startswith(f"sources/{ws.source_id}.")
            ]
            self.assertEqual(1, len(source_members))
            source_raw = ws.source.read_bytes()
            self.assertEqual(source_raw, verified["members"][source_members[0]])

            ws.write_review()
            consumed = ws.consume()
            self.assertEqual(handoff.PASS_CONSUMED, consumed["verdict"])
            reliability.verify_run(json.loads(ws.run.read_text(encoding="utf-8")))

            built = release_set.build_release_archive(
                [f"{ws.run}={ws.kit}"],
                ws.release,
            )
            self.assertEqual(release_set.PASS_BUILT, built["verdict"])
            release_set.verify_release_archive(ws.release)
            release_members = archive_members(ws.release)
            for name in release_members:
                self.assertTrue(
                    name == "release-set.json"
                    or name.startswith("kits/")
                    or name.startswith("factory-runs/"),
                    name,
                )
                self.assertNotEqual(source_raw, release_members[name])
            self.assertNotIn(source_raw, ws.release.read_bytes())


class ScopeAndRegressionSurfaceTests(unittest.TestCase):
    def test_23_transient_module_has_no_network_provider_or_persistent_store_imports(self):
        tree = ast.parse(PRODUCT_TRANSIENT.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        forbidden = {
            "requests", "httpx", "aiohttp", "urllib", "socket",
            "openai", "anthropic", "sqlite3", "sqlalchemy", "boto3",
        }
        self.assertFalse(imported & forbidden, imported & forbidden)

        source = PRODUCT_TRANSIENT.read_text(encoding="utf-8")
        for write_primitive in ("write_bytes(", "write_text(", "sqlite3.connect(", "shelve.open("):
            self.assertNotIn(write_primitive, source)

    def test_24_handoff_source_has_no_provider_or_network_client_imports(self):
        tree = ast.parse(PRODUCT_HANDOFF.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertFalse(
            imported & {"requests", "httpx", "aiohttp", "urllib", "socket", "openai", "anthropic"}
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
