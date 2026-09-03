#!/usr/bin/env python3
"""QA-WP-028 fresh contradictory QA. Authority: issue #350 only."""
from __future__ import annotations

import ast
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import handoff
from authoring.factory import release_set
from authoring.factory import source_admission
from authoring.factory import transient_source_admission as transient

FROZEN = "5fd3667d3042963b1c0108c7c84e27bd14d4f7f6"
SIGNALS = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"
PDF = b"%PDF-1.7\nQA-WP-028 exact transient source\n"
ZIPISH = b"PK\x03\x04QA-WP-028 deterministic zip signature"
TEXT = b"QA-WP-028 UTF-8 exact source\n"
BINARY = b"\xff\xfe\x00QA-WP-028-binary"


def write_json(path: Path, value: object) -> None:
    path.write_bytes(factory.canonical_json_bytes(value))


def declaration(source_id: str, version: str = "qa-r4-v1", **patch: object) -> dict:
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
    value.update(patch)
    return value


def review(context: dict, source_id: str, **patch: object) -> dict:
    evidence_source = patch.pop("evidence_source_id", source_id)
    dims = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": evidence_source,
                "locator": "qa-wp-028:source-1",
                "basis": f"Independent contradictory evidence for {name}.",
            }]
        dims[name] = {
            "status": "pass",
            "summary": f"QA-WP-028 {name}.",
            "evidence": evidence,
        }
    target = handoff.target_from_context(context)
    target.update(patch.pop("target_patch", {}) or {})
    return {
        "schema": factory.REVIEW_SCHEMA,
        "profile": factory.REVIEW_PROFILE,
        "target": target,
        "independence": {
            "authorScratchpadSeen": patch.pop("scratchpad_seen", False),
            "authorActiveContextReused": patch.pop("active_context_reused", False),
        },
        "dimensions": dims,
        "findings": [],
        "limitations": [],
        "verdict": factory.SEMANTIC_PASS,
    }


class WS:
    def __init__(self, root: Path, sources: dict[str, bytes]):
        self.root = root
        self.kit = root / "candidate.json"
        self.brief = root / "brief.json"
        self.bundle = root / "handoff.zip"
        self.review = root / "review.json"
        self.run = root / "factory-run.json"
        self.release = root / "release.zip"
        self.kit.write_bytes(SIGNALS.read_bytes())
        write_json(self.brief, {
            "schema": factory.BRIEF_SCHEMA,
            "audience": "eleve ingenieur",
            "goal": "QA-WP-028 portability",
            "language": "fr",
            "timeBudgetMinutes": 45,
        })
        self.sources = {}
        self.admissions = {}
        for i, (sid, data) in enumerate(sources.items()):
            source = root / f"input-{i}.dat"
            source.write_bytes(data)
            admission = transient.build_admission(declaration(sid), source)
            if admission["decision"]["verdict"] != transient.PASS:
                raise AssertionError(admission)
            admission_path = root / f"admission-{i}.json"
            write_json(admission_path, admission)
            self.sources[sid] = source
            self.admissions[sid] = admission_path

    def prepare(self):
        return handoff.prepare_review_bundle(
            self.kit,
            self.brief,
            [f"{sid}={self.sources[sid]}" for sid in self.sources],
            [f"{sid}={self.admissions[sid]}" for sid in self.admissions],
            self.bundle,
        )

    def verify(self):
        return handoff.verify_review_bundle(self.bundle)

    def write_review(self, source_id: str | None = None, **patch: object):
        verified = self.verify()
        sid = source_id or sorted(self.sources)[0]
        value = review(verified["context"], sid, **patch)
        write_json(self.review, value)
        return value

    def consume(self):
        return handoff.consume_review_bundle(self.bundle, self.review, self.run)


def allowed_benchmark_row(catalog: dict) -> dict:
    return next(
        row for row in catalog["sources"]
        if row["benchmarkRole"] == "primary"
        and row["rights"]["status"] in {"allowed", "conditional"}
        and row["rights"]["thirdPartyContentStatus"] != "present-unresolved"
        and catalog["defaultUseContext"] in row["rights"]["allowedUseContexts"]
    )


def repack_members(bundle: Path, mutate) -> None:
    with zipfile.ZipFile(bundle, "r") as zf:
        members = {n: zf.read(n) for n in zf.namelist()}
    mutate(members)
    bundle.write_bytes(handoff.zip_bytes(members))


def repack_manifest(bundle: Path, mutate) -> None:
    with zipfile.ZipFile(bundle, "r") as zf:
        members = {n: zf.read(n) for n in zf.namelist()}
    manifest = json.loads(members["review-handoff.json"].decode("utf-8"))
    mutate(manifest, members)
    core = {k: v for k, v in manifest.items() if k != "bundleDigest"}
    manifest["bundleDigest"] = handoff.digest(core)
    members["review-handoff.json"] = handoff.canonical(manifest)
    bundle.write_bytes(handoff.zip_bytes(members))


class AdmissionAndPortability(unittest.TestCase):
    def test_invalid_character_empty_and_length_boundaries(self):
        missing = Path(tempfile.gettempdir()) / "qa-wp-028-missing"
        for sid in ("", "user:private-course"):
            with self.subTest(sid=sid):
                with self.assertRaises(transient.TransientSourceAdmissionError):
                    transient.build_admission(declaration(sid), missing)
        for n in (161, 254, 255, 256, 300, 512):
            with self.subTest(length=n):
                with self.assertRaises(transient.TransientSourceAdmissionError):
                    transient.build_admission(declaration("A" * n), missing)

    def test_lengths_1_159_160_cross_actual_m3_3(self):
        for n in (1, 159, 160):
            with self.subTest(length=n), tempfile.TemporaryDirectory() as td:
                ws = WS(Path(td), {"A" * n: PDF})
                self.assertEqual(handoff.PASS_PREPARED, ws.prepare()["verdict"])
                self.assertTrue(ws.verify()["manifest"])
                ws.write_review()
                self.assertEqual(handoff.PASS_CONSUMED, ws.consume()["verdict"])

    def test_dot_dash_underscore_cross_actual_m3_3(self):
        with tempfile.TemporaryDirectory() as td:
            ws = WS(Path(td), {"A.course-v1_part_2": TEXT})
            ws.prepare()
            self.assertTrue(ws.verify()["manifest"])
            ws.write_review()
            self.assertEqual(handoff.PASS_CONSUMED, ws.consume()["verdict"])

    def test_policy_matrix_holds_before_source_read(self):
        missing = Path(tempfile.gettempdir()) / "qa-wp-028-never-created"
        cases = [
            ({"userDeclarationAccepted": False}, transient.HOLD_DECLARATION),
            ({"provenance": "benchmark"}, transient.HOLD_DECLARATION),
            ({"authorizationBasis": "licence"}, transient.HOLD_DECLARATION),
            ({"processingContext": "public"}, transient.HOLD_CONTEXT),
            ({"retention": "persistent"}, transient.HOLD_RETENTION),
            ({"redistribution": "allowed"}, transient.HOLD_REDISTRIBUTION),
            ({"legalRightsVerified": True}, transient.HOLD_LEGAL_CLAIM),
        ]
        for patch, expected in cases:
            with self.subTest(patch=patch):
                result = transient.build_admission(declaration("Policy", **patch), missing)
                self.assertEqual(expected, result["decision"]["verdict"])
                self.assertTrue(result["preIngestionHold"])
                self.assertIsNone(result["content"])

    def test_missing_malformed_declaration_sourceid_version(self):
        missing = Path(tempfile.gettempdir()) / "qa-wp-028-malformed"
        value = declaration("Malformed")
        del value["provenance"]
        with self.assertRaises(transient.TransientSourceAdmissionError):
            transient.build_admission(value, missing)
        with self.assertRaises(transient.TransientSourceAdmissionError):
            transient.build_admission("not-object", missing)
        for version in ("", "bad version", "::"):
            with self.subTest(version=version):
                with self.assertRaises(transient.TransientSourceAdmissionError):
                    transient.build_admission(declaration("BadVersion", version), missing)

    def test_reserved_windows_names_and_nearby_legal_names(self):
        missing = Path(tempfile.gettempdir()) / "qa-wp-028-reserved"
        reserved = (
            "CON", "con.pdf", "PRN", "AUX", "NUL",
            "COM1", "COM9", "com1.txt", "LPT1", "LPT9", "lpt9.pdf",
        )
        for sid in reserved:
            with self.subTest(reserved=sid):
                with self.assertRaisesRegex(
                    transient.TransientSourceAdmissionError, "portable on Windows"
                ):
                    transient.build_admission(declaration(sid), missing)
        for sid in ("COM10", "LPT10", "CON-1", "AUX_1"):
            with self.subTest(legal=sid), tempfile.TemporaryDirectory() as td:
                ws = WS(Path(td), {sid: PDF})
                ws.prepare()
                ws.verify()
                ws.write_review()
                self.assertEqual(handoff.PASS_CONSUMED, ws.consume()["verdict"])

    def test_other_windows_filename_conditions(self):
        missing = Path(tempfile.gettempdir()) / "qa-wp-028-win-invalid"
        for ch in '<>:"/\\|?* ':
            with self.subTest(ch=repr(ch)):
                with self.assertRaises(transient.TransientSourceAdmissionError):
                    transient.build_admission(declaration(f"A{ch}B"), missing)
        # A trailing dot in sourceId is safe only because all actual materialized
        # components append a deterministic suffix. Exercise on Windows CI too.
        with tempfile.TemporaryDirectory() as td:
            ws = WS(Path(td), {"Course.": PDF})
            ws.prepare()
            ws.verify()
            ws.write_review()
            self.assertEqual(handoff.PASS_CONSUMED, ws.consume()["verdict"])

    def test_casefold_collisions_rejected_before_path_read(self):
        missing = Path(tempfile.gettempdir()) / "qa-wp-028-no-materialization"
        pairs = [
            ("CourseA", "coursea"),
            ("Course.A", "course.a"),
            ("Course-A", "course-a"),
            ("Course_A", "course_a"),
        ]
        for left, right in pairs:
            with self.subTest(left=left, right=right):
                with self.assertRaisesRegex(
                    handoff.HandoffInputError, "case-insensitive filesystems"
                ):
                    handoff.parse_bindings(
                        [f"{left}={missing}", f"{right}={missing}"], "source"
                    )

    def test_extension_like_ids_prepare_verify_and_must_consume(self):
        # Historical F01 re-attack, plus deterministic suffix interactions.
        variants = [
            ("Course.pdf", PDF, PDF),
            ("Course.zip", ZIPISH, PDF),
            ("Course.txt", TEXT, BINARY),
            ("Course.bin", BINARY, TEXT),
        ]
        for child, base_bytes, child_bytes in variants:
            with self.subTest(child=child), tempfile.TemporaryDirectory() as td:
                ws = WS(Path(td), {"Course": base_bytes, child: child_bytes})
                self.assertEqual(handoff.PASS_PREPARED, ws.prepare()["verdict"])
                verified = ws.verify()
                self.assertEqual(
                    ["Course", child], verified["manifest"]["reviewEvidenceSourceIds"]
                )
                paths = [
                    row["path"] for row in verified["manifest"]["artifacts"]
                    if row["role"] == "source"
                ]
                self.assertEqual(len(paths), len(set(paths)))
                ws.write_review("Course")
                # A source identity accepted by admission and verified by M3.3
                # must remain usable by M3.3 consume-review.
                self.assertEqual(handoff.PASS_CONSUMED, ws.consume()["verdict"])


class DriftAuthorityArchiveReviewRelease(unittest.TestCase):
    def test_source_declaration_sourceid_version_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.dat"
            source.write_bytes(TEXT)
            record = transient.build_admission(declaration("Drift", "v1"), source)
            source.write_bytes(TEXT + b"x")
            with self.assertRaises(transient.TransientSourceAdmissionError):
                transient.reproduce_admission(record, source)
            source.write_bytes(TEXT)
            for key, value in (("sourceId", "Other"), ("version", "v2")):
                tampered = copy.deepcopy(record)
                tampered["declaration"][key] = value
                with self.subTest(key=key):
                    with self.assertRaises(transient.TransientSourceAdmissionError):
                        transient.verify_admission(tampered)

    def test_host_path_relocation_deterministic_replay(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            left = WS(Path(a), {"Relocate": PDF})
            right = WS(Path(b), {"Relocate": PDF})
            self.assertEqual(
                json.loads(left.admissions["Relocate"].read_text("utf-8")),
                json.loads(right.admissions["Relocate"].read_text("utf-8")),
            )
            l = left.prepare()
            r = right.prepare()
            self.assertEqual(l["bundleDigest"], r["bundleDigest"])
            self.assertEqual(left.bundle.read_bytes(), right.bundle.read_bytes())

    def test_transient_bundle_catalog_absence_and_catalog_injection(self):
        with tempfile.TemporaryDirectory() as td:
            ws = WS(Path(td), {"NoCatalog": PDF})
            ws.prepare()
            self.assertNotIn("source-catalog.json", ws.verify()["members"])
            repack_members(
                ws.bundle,
                lambda members: members.__setitem__(
                    "source-catalog.json", handoff.CATALOG_PATH.read_bytes()
                ),
            )
            with self.assertRaises(handoff.HandoffInputError):
                ws.verify()

    def test_benchmark_catalog_exactness_and_benchmark_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            kit = root / "candidate.json"; kit.write_bytes(SIGNALS.read_bytes())
            brief = root / "brief.json"
            write_json(brief, {
                "schema": factory.BRIEF_SCHEMA,
                "audience": "eleve ingenieur",
                "goal": "benchmark regression",
                "language": "fr",
                "timeBudgetMinutes": 45,
            })
            source = root / "source.dat"; source.write_bytes(TEXT)
            admission = root / "admission.json"
            bundle = root / "benchmark.zip"
            catalog, catalog_sha = source_admission.load_catalog(handoff.CATALOG_PATH)
            row = allowed_benchmark_row(catalog)
            version = (
                row["version"]["value"]
                if row["version"]["strategy"] == "fixed"
                else "qa-r4-v1"
            )
            record = source_admission.build_admission(
                catalog, catalog_sha, row["sourceId"], catalog["defaultUseContext"],
                source, list(row["rights"]["conditions"]), version,
            )
            self.assertEqual(source_admission.PASS, record["decision"]["verdict"])
            write_json(admission, record)
            handoff.prepare_review_bundle(
                kit, brief, [f"BenchmarkQA={source}"],
                [f"BenchmarkQA={admission}"], bundle,
            )
            verified = handoff.verify_review_bundle(bundle)
            self.assertEqual(
                handoff.CATALOG_PATH.read_bytes(),
                verified["members"]["source-catalog.json"],
            )

    def test_transient_cannot_masquerade_as_benchmark(self):
        with tempfile.TemporaryDirectory() as td:
            ws = WS(Path(td), {"Masquerade": PDF})
            value = json.loads(ws.admissions["Masquerade"].read_text("utf-8"))
            value["schema"] = source_admission.ADMISSION_SCHEMA
            write_json(ws.admissions["Masquerade"], value)
            with self.assertRaises(handoff.HandoffInputError):
                ws.prepare()

    def test_benchmark_admission_without_catalog_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            kit = root / "candidate.json"; kit.write_bytes(SIGNALS.read_bytes())
            brief = root / "brief.json"
            write_json(brief, {
                "schema": factory.BRIEF_SCHEMA,
                "audience": "eleve ingenieur",
                "goal": "benchmark no catalog",
                "language": "fr",
                "timeBudgetMinutes": 45,
            })
            source = root / "source.dat"; source.write_bytes(TEXT)
            admission = root / "admission.json"
            bundle = root / "benchmark.zip"
            catalog, catalog_sha = source_admission.load_catalog(handoff.CATALOG_PATH)
            row = allowed_benchmark_row(catalog)
            version = (
                row["version"]["value"]
                if row["version"]["strategy"] == "fixed"
                else "qa-r4-v1"
            )
            record = source_admission.build_admission(
                catalog, catalog_sha, row["sourceId"], catalog["defaultUseContext"],
                source, list(row["rights"]["conditions"]), version,
            )
            write_json(admission, record)
            handoff.prepare_review_bundle(
                kit, brief, [f"BenchmarkNoCatalog={source}"],
                [f"BenchmarkNoCatalog={admission}"], bundle,
            )

            def mutate(manifest, members):
                members.pop("source-catalog.json")
                manifest["artifacts"] = [
                    row for row in manifest["artifacts"]
                    if row["role"] != "source-catalog"
                ]

            repack_manifest(bundle, mutate)
            with self.assertRaisesRegex(
                handoff.HandoffInputError, "requires embedded source catalog"
            ):
                handoff.verify_review_bundle(bundle)

    def test_archive_tamper_duplicate_unsafe_undeclared(self):
        def tamper(m): m.__setitem__("candidate.json", m["candidate.json"] + b" ")
        def extra(m): m.__setitem__("extra.txt", b"x")
        def unsafe(m): m.__setitem__("../escape.txt", b"x")

        for name, mutator in (("tamper", tamper), ("undeclared", extra)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td:
                ws = WS(Path(td), {"Archive": PDF})
                ws.prepare()
                repack_members(ws.bundle, mutator)
                with self.assertRaises(handoff.HandoffInputError):
                    ws.verify()

        with tempfile.TemporaryDirectory() as td:
            ws = WS(Path(td), {"Unsafe": PDF})
            ws.prepare()
            with self.assertRaises(handoff.HandoffInputError):
                repack_members(ws.bundle, unsafe)

        with tempfile.TemporaryDirectory() as td:
            ws = WS(Path(td), {"Duplicate": PDF})
            ws.prepare()
            with zipfile.ZipFile(ws.bundle, "r") as zf:
                entries = [(info, zf.read(info.filename)) for info in zf.infolist()]
            out = io.BytesIO()
            with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as zf:
                for i, (info, data) in enumerate(entries):
                    zf.writestr(info, data)
                    if i == 0:
                        zf.writestr(info, data)
            ws.bundle.write_bytes(out.getvalue())
            with self.assertRaisesRegex(handoff.HandoffInputError, "duplicate"):
                ws.verify()

    def test_stale_review_injected_source_and_independence_fail_closed(self):
        cases = [
            {"target_patch": {"contextDigest": "sha256:" + "0" * 64}},
            {"evidence_source_id": "InjectedSource"},
            {"scratchpad_seen": True},
            {"active_context_reused": True},
        ]
        for patch in cases:
            with self.subTest(patch=patch), tempfile.TemporaryDirectory() as td:
                ws = WS(Path(td), {"ReviewSource": PDF})
                ws.prepare()
                ws.write_review("ReviewSource", **patch)
                with self.assertRaises(handoff.HandoffInputError):
                    ws.consume()

    def test_exact_source_visible_to_reviewer_absent_from_qrs(self):
        with tempfile.TemporaryDirectory() as td:
            ws = WS(Path(td), {"ReleaseOnly": PDF})
            ws.prepare()
            verified = ws.verify()
            source_name = next(
                n for n in verified["members"] if n.startswith("sources/ReleaseOnly.")
            )
            self.assertEqual(PDF, verified["members"][source_name])
            ws.write_review("ReleaseOnly")
            self.assertEqual(handoff.PASS_CONSUMED, ws.consume()["verdict"])
            built = release_set.build_release_archive(
                [f"{ws.run}={ws.kit}"], ws.release
            )
            self.assertEqual(release_set.PASS_BUILT, built["verdict"])
            release_set.verify_release_archive(ws.release)
            with zipfile.ZipFile(ws.release, "r") as zf:
                names = zf.namelist()
                members = [zf.read(n) for n in names]
            self.assertFalse(any("source" in n.lower() for n in names))
            self.assertFalse(any(PDF in data for data in members))


class StaticIsolation(unittest.TestCase):
    def test_no_network_provider_or_persistent_source_store(self):
        forbidden = {
            "requests", "urllib", "http", "socket", "aiohttp", "openai",
            "anthropic", "boto3", "google", "azure",
        }
        for rel in (
            "authoring/factory/transient_source_admission.py",
            "authoring/factory/handoff.py",
        ):
            tree = ast.parse((ROOT / rel).read_text("utf-8"), filename=rel)
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".", 1)[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".", 1)[0])
            self.assertFalse(imported & forbidden, (rel, imported & forbidden))
        code = (ROOT / "authoring/factory/transient_source_admission.py").read_text("utf-8")
        for primitive in ("write_bytes(", "write_text(", "sqlite3", "shelve", "urlopen("):
            self.assertNotIn(primitive, code)

    def test_frozen_head_binding_constant(self):
        self.assertEqual(
            "5fd3667d3042963b1c0108c7c84e27bd14d4f7f6", FROZEN
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
