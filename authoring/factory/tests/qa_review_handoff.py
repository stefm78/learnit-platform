#!/usr/bin/env python3
"""Independent contradictory QA for ATLAS-WP-019 M3.3 Portable Review Handoff."""
from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import handoff
from authoring.factory import reliability
from authoring.factory import source_admission

NOMBRES = ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json"


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic_review(
    context: dict,
    source_id: str,
    *,
    findings: list[dict] | None = None,
    statuses: dict[str, str] | None = None,
    scratchpad_seen: bool = False,
    active_context_reused: bool = False,
    verdict: str | None = None,
) -> dict:
    findings = copy.deepcopy(findings or [])
    statuses = statuses or {}
    dimensions: dict[str, dict] = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": source_id,
                "locator": "qa-nombres-source",
                "basis": f"Independent QA source evidence for {name}.",
            }]
        dimensions[name] = {
            "status": statuses.get(name, "pass"),
            "summary": f"Independent contradictory QA checked {name}.",
            "evidence": evidence,
        }

    should_pass = (
        not scratchpad_seen
        and not active_context_reused
        and all(row["status"] == "pass" for row in dimensions.values())
        and not any(row["severity"] in {"blocking", "major"} for row in findings)
    )
    if verdict is None:
        verdict = factory.SEMANTIC_PASS if should_pass else factory.SEMANTIC_HOLD

    return {
        "schema": factory.REVIEW_SCHEMA,
        "profile": factory.REVIEW_PROFILE,
        "target": handoff.target_from_context(context),
        "independence": {
            "authorScratchpadSeen": scratchpad_seen,
            "authorActiveContextReused": active_context_reused,
        },
        "dimensions": dimensions,
        "findings": findings,
        "limitations": ["QA fixture uses exact local bytes solely to test M3.3 transport/re-entry."],
        "verdict": verdict,
    }


class Workspace:
    """Independent Nombres-complexes transport fixture with a caller alias."""

    def __init__(self, root: Path):
        self.root = root
        self.kit = root / "candidate.json"
        self.brief = root / "learner-brief.json"
        self.source = root / "source-local.txt"
        self.admission = root / "source-admission.json"
        self.bundle = root / "review-handoff.zip"
        self.review = root / "semantic-review.json"
        self.run = root / "factory-run.json"

        self.kit.write_bytes(NOMBRES.read_bytes())
        write_json(self.brief, {
            "schema": factory.BRIEF_SCHEMA,
            "audience": "étudiant ingénieur",
            "goal": "Comprendre et appliquer les représentations des nombres complexes",
            "language": "fr",
            "timeBudgetMinutes": 45,
        })
        self.source.write_text(
            "Nombres complexes : forme algébrique, module, argument et représentation polaire.\n"
            "Cette source locale exacte sert uniquement à la preuve de transport QA M3.3.\n",
            encoding="utf-8",
        )

        catalog, catalog_sha = source_admission.load_catalog(handoff.CATALOG_PATH)
        self.catalog = catalog
        self.catalog_sha = catalog_sha
        self.catalog_row = next(
            row
            for row in catalog["sources"]
            if row["benchmarkRole"] == "primary"
            and row["rights"]["status"] in {"allowed", "conditional"}
            and row["rights"]["thirdPartyContentStatus"] != "present-unresolved"
            and catalog["defaultUseContext"] in row["rights"]["allowedUseContexts"]
        )
        self.catalog_source_id = self.catalog_row["sourceId"]
        self.source_id = "qa_nombres_source"
        strategy = self.catalog_row["version"]["strategy"]
        version = self.catalog_row["version"]["value"] if strategy == "fixed" else "qa-v1"
        record = source_admission.build_admission(
            catalog,
            catalog_sha,
            self.catalog_source_id,
            catalog["defaultUseContext"],
            self.source,
            list(self.catalog_row["rights"]["conditions"]),
            version,
        )
        if record["decision"]["verdict"] != source_admission.PASS:
            raise AssertionError(record)
        write_json(self.admission, record)

    @property
    def source_specs(self) -> list[str]:
        return [f"{self.source_id}={self.source}"]

    @property
    def admission_specs(self) -> list[str]:
        return [f"{self.source_id}={self.admission}"]

    def prepare(self) -> dict:
        return handoff.prepare_review_bundle(
            self.kit,
            self.brief,
            self.source_specs,
            self.admission_specs,
            self.bundle,
        )

    def verified(self) -> dict:
        return handoff.verify_review_bundle(self.bundle)

    def write_review(self, **kwargs) -> dict:
        context = self.verified()["context"]
        review = semantic_review(context, self.source_id, **kwargs)
        write_json(self.review, review)
        return review

    def consume(self) -> dict:
        return handoff.consume_review_bundle(self.bundle, self.review, self.run)


def archive_members(path: Path) -> tuple[list[zipfile.ZipInfo], dict[str, bytes]]:
    with zipfile.ZipFile(path, "r") as zf:
        infos = zf.infolist()
        return infos, {info.filename: zf.read(info) for info in infos}


def write_custom_archive(
    destination: Path,
    originals: list[tuple[str, bytes]],
    *,
    reverse: bool = False,
    timestamp_override: bool = False,
    mode_override: bool = False,
    compression_override: bool = False,
    append: tuple[str, bytes] | None = None,
) -> None:
    rows = list(reversed(originals)) if reverse else list(originals)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for index, (name, data) in enumerate(rows):
            dt = (1981, 1, 1, 0, 0, 0) if timestamp_override and index == 0 else handoff.FIXED_ZIP_TIME
            info = zipfile.ZipInfo(name, dt)
            info.compress_type = zipfile.ZIP_DEFLATED if compression_override and index == 0 else zipfile.ZIP_STORED
            info.create_system = 3
            mode = (stat.S_IFREG | 0o600) if mode_override and index == 0 else handoff.FILE_MODE
            info.external_attr = mode << 16
            zf.writestr(info, data)
        if append is not None:
            name, data = append
            info = zipfile.ZipInfo(name, handoff.FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = handoff.FILE_MODE << 16
            zf.writestr(info, data)
    destination.write_bytes(buffer.getvalue())


def reseal_artifact(
    bundle: Path,
    destination: Path,
    artifact_path: str,
    mutated: bytes,
) -> None:
    _, members = archive_members(bundle)
    manifest = json.loads(members["review-handoff.json"].decode("utf-8"))
    row = next(item for item in manifest["artifacts"] if item["path"] == artifact_path)
    members[artifact_path] = mutated
    row["bytes"] = len(mutated)
    row["sha256"] = handoff.sha(mutated)
    core = {key: value for key, value in manifest.items() if key != "bundleDigest"}
    manifest["bundleDigest"] = handoff.digest(core)
    members["review-handoff.json"] = handoff.canonical(manifest)
    destination.write_bytes(handoff.zip_bytes(members))


class PrepareAndIdentityOracle(unittest.TestCase):
    def test_bundle_identity_is_byte_deterministic_across_host_relocation(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            left = Workspace(Path(a))
            right = Workspace(Path(b))
            result_left = left.prepare()
            result_right = right.prepare()
            self.assertEqual(result_left["bundleDigest"], result_right["bundleDigest"])
            self.assertEqual(result_left["bundleSha256"], result_right["bundleSha256"])
            self.assertEqual(left.bundle.read_bytes(), right.bundle.read_bytes())
            self.assertNotIn(str(Path(a)).encode(), left.bundle.read_bytes())
            self.assertNotIn(str(Path(b)).encode(), right.bundle.read_bytes())

    def test_source_admission_alias_is_exact_without_weakening_admission(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            verified = ws.verified()
            manifest = verified["manifest"]
            self.assertEqual([ws.source_id], manifest["reviewEvidenceSourceIds"])
            self.assertEqual(ws.source_id, manifest["resources"][0]["resourceId"])
            admission_path = f"source-admission/{ws.source_id}.json"
            embedded = json.loads(verified["members"][admission_path].decode("utf-8"))
            self.assertEqual(ws.catalog_source_id, embedded["source"]["sourceId"])
            self.assertEqual(source_admission.PASS, embedded["decision"]["verdict"])
            source_member = next(
                name for name in verified["members"] if name.startswith(f"sources/{ws.source_id}.")
            )
            source_bytes = verified["members"][source_member]
            self.assertEqual(
                {"bytes": len(source_bytes), "sha256": handoff.sha(source_bytes)},
                embedded["content"],
            )

    def test_admitted_byte_drift_prevents_packaging(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.source.write_bytes(ws.source.read_bytes() + b"!")
            with self.assertRaises(handoff.HandoffInputError):
                ws.prepare()

    def test_pre_ingestion_or_permission_hold_cannot_enter_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            negative = next(
                row for row in ws.catalog["sources"] if row["benchmarkRole"] == "negative-control"
            )
            strategy = negative["version"]["strategy"]
            version = negative["version"]["value"] if strategy == "fixed" else "qa-v1"
            record = source_admission.build_admission(
                ws.catalog,
                ws.catalog_sha,
                negative["sourceId"],
                ws.catalog["defaultUseContext"],
                ws.source,
                list(negative["rights"]["conditions"]),
                version,
            )
            self.assertNotEqual(source_admission.PASS, record["decision"]["verdict"])
            write_json(ws.admission, record)
            with self.assertRaises(handoff.HandoffInputError):
                ws.prepare()

    def test_exact_reviewer_skill_request_and_private_context_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            verified = ws.verified()
            self.assertEqual(
                handoff.REVIEWER_SKILL_PATH.read_bytes(),
                verified["members"][handoff.ROLE_PATHS["reviewer-skill"]],
            )
            self.assertEqual(
                handoff.REVIEW_REQUEST.encode("utf-8"),
                verified["members"][handoff.ROLE_PATHS["review-request"]],
            )
            member_names = "\n".join(verified["members"]).lower()
            for forbidden in ("scratchpad", "conversation", "chat-log", "author-context", "reasoning-log"):
                self.assertNotIn(forbidden, member_names)
            self.assertNotIn(str(Path(td)).encode(), ws.bundle.read_bytes())

    def test_prepare_inputs_remain_byte_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            paths = [ws.kit, ws.brief, ws.source, ws.admission]
            before = {str(path): sha256(path) for path in paths}
            ws.prepare()
            self.assertEqual(before, {str(path): sha256(path) for path in paths})


class CanonicalArchiveOracle(unittest.TestCase):
    def test_archive_metadata_order_and_declaration_set_are_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            infos, members = archive_members(ws.bundle)
            names = [info.filename for info in infos]
            self.assertEqual(sorted(names), names)
            self.assertEqual(len(names), len(set(names)))
            with zipfile.ZipFile(ws.bundle, "r") as zf:
                self.assertEqual(b"", zf.comment)
            for info in infos:
                self.assertEqual(handoff.FIXED_ZIP_TIME, tuple(info.date_time))
                self.assertEqual(zipfile.ZIP_STORED, info.compress_type)
                self.assertEqual(3, info.create_system)
                self.assertEqual(handoff.FILE_MODE, info.external_attr >> 16)
            manifest = json.loads(members["review-handoff.json"].decode("utf-8"))
            declared = {row["path"] for row in manifest["artifacts"]} | {"review-handoff.json"}
            self.assertEqual(set(names), declared)

    def test_noncanonical_order_timestamp_mode_and_compression_fail_closed(self):
        for mode in ("order", "timestamp", "permissions", "compression"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                ws = Workspace(Path(td))
                ws.prepare()
                infos, members = archive_members(ws.bundle)
                originals = [(info.filename, members[info.filename]) for info in infos]
                mutated = Path(td) / f"{mode}.zip"
                write_custom_archive(
                    mutated,
                    originals,
                    reverse=mode == "order",
                    timestamp_override=mode == "timestamp",
                    mode_override=mode == "permissions",
                    compression_override=mode == "compression",
                )
                with self.assertRaises(handoff.HandoffInputError):
                    handoff.verify_review_bundle(mutated)

    def test_duplicate_traversal_backslash_undeclared_and_digest_tamper_fail_closed(self):
        for mode in ("duplicate", "traversal", "backslash", "undeclared", "digest"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                ws = Workspace(Path(td))
                ws.prepare()
                infos, members = archive_members(ws.bundle)
                originals = [(info.filename, members[info.filename]) for info in infos]
                mutated = Path(td) / f"{mode}.zip"
                if mode == "duplicate":
                    write_custom_archive(mutated, originals, append=originals[0])
                elif mode == "traversal":
                    write_custom_archive(mutated, originals, append=("../escape.txt", b"x"))
                elif mode == "backslash":
                    write_custom_archive(mutated, originals, append=("unsafe\\member.txt", b"x"))
                elif mode == "undeclared":
                    extra = dict(members)
                    extra["extra.txt"] = b"undeclared"
                    mutated.write_bytes(handoff.zip_bytes(extra))
                else:
                    changed = dict(members)
                    changed["candidate.json"] = changed["candidate.json"] + b"\n"
                    mutated.write_bytes(handoff.zip_bytes(changed))
                with self.assertRaises(handoff.HandoffInputError):
                    handoff.verify_review_bundle(mutated)

    def test_resealed_embedded_authority_tampering_fails_closed(self):
        cases = (
            handoff.ROLE_PATHS["source-catalog"],
            f"source-admission/qa_nombres_source.json",
            handoff.ROLE_PATHS["factory-context"],
            handoff.ROLE_PATHS["quality-report"],
            handoff.ROLE_PATHS["reviewer-skill"],
        )
        for artifact_path in cases:
            with self.subTest(artifact_path=artifact_path), tempfile.TemporaryDirectory() as td:
                ws = Workspace(Path(td))
                ws.prepare()
                _, members = archive_members(ws.bundle)
                mutated = Path(td) / "resealed.zip"
                reseal_artifact(
                    ws.bundle,
                    mutated,
                    artifact_path,
                    members[artifact_path] + b"\n",
                )
                with self.assertRaises(handoff.HandoffInputError):
                    handoff.verify_review_bundle(mutated)


class ReviewReentryOracle(unittest.TestCase):
    def assert_rejected_before_factory_run(self, ws: Workspace) -> None:
        with mock.patch.object(
            reliability,
            "build_run",
            side_effect=AssertionError("FactoryRun builder must not run"),
        ) as builder:
            with self.assertRaises(handoff.HandoffInputError):
                ws.consume()
            builder.assert_not_called()
        self.assertFalse(ws.run.exists())

    def test_stale_review_target_fails_before_factory_run_creation(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            review = ws.write_review()
            review["target"]["kitSha256"] = "sha256:" + "0" * 64
            write_json(ws.review, review)
            self.assert_rejected_before_factory_run(ws)

    def test_both_reviewer_independence_violations_fail_before_factory_run(self):
        for field in ("scratchpad_seen", "active_context_reused"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                ws = Workspace(Path(td))
                ws.prepare()
                ws.write_review(**{field: True})
                self.assert_rejected_before_factory_run(ws)

    def test_review_evidence_source_id_injection_fails_before_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            review = ws.write_review()
            review["dimensions"]["sourceFidelity"]["evidence"][0]["sourceId"] = "injected_source"
            write_json(ws.review, review)
            self.assert_rejected_before_factory_run(ws)

    def test_inconsistent_pass_over_hold_fails_before_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            ws.write_review(
                statuses={"sourceFidelity": "hold"},
                verdict=factory.SEMANTIC_PASS,
            )
            self.assert_rejected_before_factory_run(ws)

    def test_semantic_pass_yields_self_verifying_pass_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            ws.write_review()
            result = ws.consume()
            self.assertEqual(handoff.PASS_CONSUMED, result["verdict"])
            run = json.loads(ws.run.read_text(encoding="utf-8"))
            reliability.verify_run(run)
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", run["decision"]["verdict"])

    def test_justified_semantic_hold_yields_self_verifying_hold_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            finding = {
                "id": "QA-M3-3-HOLD-001",
                "severity": "major",
                "dimension": "sourceFidelity",
                "path": "$.courses[0].activities[0]",
                "problem": "Independent QA synthetic major source-fidelity defect.",
                "impact": "The learner could encode a false rule.",
                "fix": "Repair only from the exact supplied source.",
                "evidence": [{
                    "sourceId": ws.source_id,
                    "locator": "qa-nombres-source",
                    "basis": "The exact source contradicts the synthetic finding target.",
                }],
            }
            ws.write_review(
                findings=[finding],
                statuses={"sourceFidelity": "hold"},
            )
            result = ws.consume()
            self.assertEqual(handoff.PASS_CONSUMED, result["verdict"])
            run = json.loads(ws.run.read_text(encoding="utf-8"))
            reliability.verify_run(run)
            self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", run["decision"]["verdict"])
            self.assertTrue(run["decision"]["reasons"])

    def test_minor_only_finding_preserves_existing_pass_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            finding = {
                "id": "QA-M3-3-MINOR-001",
                "severity": "minor",
                "dimension": "ambiguity",
                "path": "$.courses[0].activities[0].prompt",
                "problem": "Small wording issue.",
                "impact": "Small reading overhead only.",
                "fix": "Clarify in a later revision.",
                "evidence": [],
            }
            ws.write_review(findings=[finding])
            ws.consume()
            run = json.loads(ws.run.read_text(encoding="utf-8"))
            reliability.verify_run(run)
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", run["decision"]["verdict"])
            self.assertEqual(
                1,
                run["evidenceBundle"]["factoryEvidence"]["semanticReview"]["counts"]["minor"],
            )

    def test_consume_bundle_and_review_inputs_remain_byte_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            ws.write_review()
            before = {str(path): sha256(path) for path in (ws.bundle, ws.review)}
            ws.consume()
            self.assertEqual(
                before,
                {str(path): sha256(path) for path in (ws.bundle, ws.review)},
            )


class ProductBoundaryOracle(unittest.TestCase):
    def test_no_network_provider_or_source_ingestion_primitive_is_introduced(self):
        source = (ROOT / "authoring/factory/handoff.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(
            imported.isdisjoint({"requests", "httpx", "aiohttp", "urllib", "socket"}),
            imported,
        )
        lower = source.lower()
        for forbidden in (
            "openai(",
            "anthropic(",
            "pypdf",
            "pdfplumber",
            "pymupdf",
            "tesseract",
            "easyocr",
        ):
            self.assertNotIn(forbidden, lower)


if __name__ == "__main__":
    unittest.main(verbosity=2)
