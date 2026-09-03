#!/usr/bin/env python3
"""Product evidence for ATLAS-WP-019 M3.3 portable review handoff."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import handoff
from authoring.factory import reliability
from authoring.factory import source_admission
from authoring.factory import transient_source_admission as transient

SIGNALS = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def transient_declaration(source_id: str, version: str = "epf-v1") -> dict:
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
    findings: list[dict] | None = None,
    dimension_status: dict[str, str] | None = None,
    scratchpad_seen: bool = False,
    active_context_reused: bool = False,
    verdict: str | None = None,
) -> dict:
    findings = copy.deepcopy(findings or [])
    dimension_status = dimension_status or {}
    dimensions = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": source_id,
                "locator": "source-section-1",
                "basis": f"Independent source evidence for {name}.",
            }]
        dimensions[name] = {
            "status": dimension_status.get(name, "pass"),
            "summary": f"Independent {name} review completed.",
            "evidence": evidence,
        }
    would_pass = (
        not scratchpad_seen
        and not active_context_reused
        and all(row["status"] == "pass" for row in dimensions.values())
        and not any(row["severity"] in {"blocking", "major"} for row in findings)
    )
    if verdict is None:
        verdict = factory.SEMANTIC_PASS if would_pass else factory.SEMANTIC_HOLD
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
        "limitations": [],
        "verdict": verdict,
    }


class Workspace:
    def __init__(self, root: Path):
        self.root = root
        self.kit = root / "candidate.json"
        self.brief = root / "brief.json"
        self.source = root / "source.bin"
        self.admission = root / "admission.json"
        self.bundle = root / "review.zip"
        self.review = root / "review.json"
        self.run = root / "factory-run.json"

        self.kit.write_bytes(SIGNALS.read_bytes())
        write_json(self.brief, {
            "schema": factory.BRIEF_SCHEMA,
            "audience": "élève ingénieur",
            "goal": "Comprendre et appliquer les relations du cours",
            "language": "fr",
            "timeBudgetMinutes": 45,
        })
        self.source.write_text(
            "Source locale exacte utilisée uniquement pour la preuve de transport M3.3.\n",
            encoding="utf-8",
        )

        catalog, catalog_sha = source_admission.load_catalog(handoff.CATALOG_PATH)
        self.catalog = catalog
        self.catalog_sha = catalog_sha
        self.source_row = next(
            row
            for row in catalog["sources"]
            if row["benchmarkRole"] == "primary"
            and row["rights"]["status"] in {"allowed", "conditional"}
            and row["rights"]["thirdPartyContentStatus"] != "present-unresolved"
            and catalog["defaultUseContext"] in row["rights"]["allowedUseContexts"]
        )
        self.catalog_source_id = self.source_row["sourceId"]
        self.source_id = "handoff_source"
        strategy = self.source_row["version"]["strategy"]
        version = self.source_row["version"]["value"] if strategy == "fixed" else "test-v1"
        accepted = list(self.source_row["rights"]["conditions"])
        record = source_admission.build_admission(
            catalog,
            catalog_sha,
            self.catalog_source_id,
            catalog["defaultUseContext"],
            self.source,
            accepted,
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
        verified = self.verified()
        review = semantic_review(verified["context"], self.source_id, **kwargs)
        write_json(self.review, review)
        return review

    def consume(self) -> dict:
        return handoff.consume_review_bundle(self.bundle, self.review, self.run)


def hash_paths(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


class PrepareReviewTests(unittest.TestCase):
    def test_deterministic_bundle_is_path_independent(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ws_a = Workspace(Path(a))
            ws_b = Workspace(Path(b))
            result_a = ws_a.prepare()
            result_b = ws_b.prepare()
            self.assertEqual(result_a["bundleDigest"], result_b["bundleDigest"])
            self.assertEqual(result_a["bundleSha256"], result_b["bundleSha256"])
            self.assertEqual(ws_a.bundle.read_bytes(), ws_b.bundle.read_bytes())
            self.assertNotIn(str(Path(a)), ws_a.bundle.read_bytes().decode("latin1"))
            self.assertNotIn(str(Path(b)), ws_b.bundle.read_bytes().decode("latin1"))

    def test_bundle_contains_exact_skill_request_and_no_author_context_surface(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            verified = ws.verified()
            members = verified["members"]
            self.assertEqual(
                handoff.REVIEWER_SKILL_PATH.read_bytes(),
                members[handoff.ROLE_PATHS["reviewer-skill"]],
            )
            self.assertEqual(
                handoff.REVIEW_REQUEST.encode("utf-8"),
                members[handoff.ROLE_PATHS["review-request"]],
            )
            forbidden = {"scratchpad", "conversation", "chat", "author-context", "reasoning", "logs"}
            names = "\n".join(members).lower()
            self.assertFalse(any(token in names for token in forbidden))
            self.assertEqual([ws.source_id], verified["manifest"]["reviewEvidenceSourceIds"])

    def test_source_drift_after_admission_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.source.write_text("drifted bytes\n", encoding="utf-8")
            with self.assertRaises(handoff.HandoffInputError):
                ws.prepare()

    def test_source_admission_hold_prevents_packaging(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            negative = next(
                row for row in ws.catalog["sources"] if row["benchmarkRole"] == "negative-control"
            )
            ws.catalog_source_id = negative["sourceId"]
            ws.source_id = "negative_control"
            strategy = negative["version"]["strategy"]
            version = negative["version"]["value"] if strategy == "fixed" else "test-v1"
            record = source_admission.build_admission(
                ws.catalog,
                ws.catalog_sha,
                ws.catalog_source_id,
                ws.catalog["defaultUseContext"],
                ws.source,
                list(negative["rights"]["conditions"]),
                version,
            )
            self.assertNotEqual(source_admission.PASS, record["decision"]["verdict"])
            write_json(ws.admission, record)
            with self.assertRaises(handoff.HandoffInputError):
                handoff.prepare_review_bundle(
                    ws.kit,
                    ws.brief,
                    [f"{ws.source_id}={ws.source}"],
                    [f"{ws.source_id}={ws.admission}"],
                    ws.bundle,
                )

    def test_prepare_never_mutates_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            paths = [ws.kit, ws.brief, ws.source, ws.admission]
            before = hash_paths(paths)
            ws.prepare()
            self.assertEqual(before, hash_paths(paths))


class TransientWorkspace(Workspace):
    def __init__(self, root: Path):
        super().__init__(root)
        self.source_id = "private_user_source"
        record = transient.build_admission(
            transient_declaration(self.source_id),
            self.source,
        )
        if record["decision"]["verdict"] != transient.PASS:
            raise AssertionError(record)
        write_json(self.admission, record)


class TransientPrepareReviewTests(unittest.TestCase):
    def test_transient_bundle_is_deterministic_and_has_no_benchmark_catalog(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ws_a = TransientWorkspace(Path(a))
            ws_b = TransientWorkspace(Path(b))
            result_a = ws_a.prepare()
            result_b = ws_b.prepare()
            self.assertEqual(result_a["bundleDigest"], result_b["bundleDigest"])
            self.assertEqual(result_a["bundleSha256"], result_b["bundleSha256"])
            self.assertEqual(ws_a.bundle.read_bytes(), ws_b.bundle.read_bytes())

            verified = ws_a.verified()
            self.assertNotIn(
                handoff.OPTIONAL_ROLE_PATHS["source-catalog"],
                verified["members"],
            )
            admission = json.loads(
                verified["members"][
                    f"source-admission/{ws_a.source_id}.json"
                ].decode("utf-8")
            )
            self.assertEqual(transient.ADMISSION_SCHEMA, admission["schema"])
            self.assertFalse(admission["declaration"]["legalRightsVerified"])

    def test_transient_source_drift_after_admission_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td))
            ws.source.write_text("drifted bytes\n", encoding="utf-8")
            with self.assertRaises(handoff.HandoffInputError):
                ws.prepare()

    def test_transient_factory_compatible_source_id_crosses_m3_3_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td))
            ws.source_id = "user.private-course_01"
            record = transient.build_admission(
                transient_declaration(ws.source_id),
                ws.source,
            )
            self.assertEqual(transient.PASS, record["decision"]["verdict"])
            write_json(ws.admission, record)
            result = ws.prepare()
            self.assertEqual(handoff.PASS_PREPARED, result["verdict"])
            verified = ws.verified()
            self.assertEqual(
                [ws.source_id],
                verified["manifest"]["reviewEvidenceSourceIds"],
            )

    def test_transient_bundle_consumes_normal_independent_review(self):
        with tempfile.TemporaryDirectory() as td:
            ws = TransientWorkspace(Path(td))
            ws.prepare()
            ws.write_review()
            result = ws.consume()
            self.assertEqual(handoff.PASS_CONSUMED, result["verdict"])
            run = json.loads(ws.run.read_text(encoding="utf-8"))
            reliability.verify_run(run)
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", run["decision"]["verdict"])

    def test_benchmark_bundle_still_carries_exact_benchmark_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            verified = ws.verified()
            catalog_path = handoff.OPTIONAL_ROLE_PATHS["source-catalog"]
            self.assertEqual(
                handoff.CATALOG_PATH.read_bytes(),
                verified["members"][catalog_path],
            )


class ArchiveAdversarialTests(unittest.TestCase):
    def rewrite_bundle(self, source: Path, destination: Path, mutate) -> None:
        with zipfile.ZipFile(source, "r") as zin:
            members = {info.filename: zin.read(info) for info in zin.infolist()}
        mutate(members)
        destination.write_bytes(handoff.zip_bytes(members))

    def test_tampered_candidate_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            tampered = Path(td) / "tampered.zip"
            self.rewrite_bundle(
                ws.bundle,
                tampered,
                lambda members: members.__setitem__(
                    "candidate.json", members["candidate.json"] + b"\n"
                ),
            )
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(tampered)

    def test_undeclared_extra_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            extra = Path(td) / "extra.zip"
            self.rewrite_bundle(
                ws.bundle,
                extra,
                lambda members: members.__setitem__("extra.txt", b"not declared"),
            )
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(extra)

    def test_duplicate_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            duplicate = Path(td) / "duplicate.zip"
            raw = io.BytesIO()
            with zipfile.ZipFile(ws.bundle, "r") as zin:
                originals = [(info.filename, zin.read(info)) for info in zin.infolist()]
            with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_STORED) as zout:
                for name, data in originals:
                    info = zipfile.ZipInfo(name, handoff.FIXED_ZIP_TIME)
                    info.compress_type = zipfile.ZIP_STORED
                    info.create_system = 3
                    info.external_attr = handoff.FILE_MODE << 16
                    zout.writestr(info, data)
                name, data = originals[0]
                info = zipfile.ZipInfo(name, handoff.FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = handoff.FILE_MODE << 16
                zout.writestr(info, data)
            duplicate.write_bytes(raw.getvalue())
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(duplicate)

    def test_path_traversal_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            unsafe = Path(td) / "unsafe.zip"
            with zipfile.ZipFile(ws.bundle, "r") as zin:
                originals = [(info.filename, zin.read(info)) for info in zin.infolist()]
            raw = io.BytesIO()
            with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_STORED) as zout:
                for name, data in originals:
                    info = zipfile.ZipInfo(name, handoff.FIXED_ZIP_TIME)
                    info.compress_type = zipfile.ZIP_STORED
                    info.create_system = 3
                    info.external_attr = handoff.FILE_MODE << 16
                    zout.writestr(info, data)
                info = zipfile.ZipInfo("../escape.txt", handoff.FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = handoff.FILE_MODE << 16
                zout.writestr(info, b"x")
            unsafe.write_bytes(raw.getvalue())
            with self.assertRaises(handoff.HandoffInputError):
                handoff.verify_review_bundle(unsafe)


class ConsumeReviewTests(unittest.TestCase):
    def test_pass_review_builds_self_verifying_pass_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            ws.write_review()
            result = ws.consume()
            self.assertEqual(handoff.PASS_CONSUMED, result["verdict"])
            run = json.loads(ws.run.read_text(encoding="utf-8"))
            reliability.verify_run(run)
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", run["decision"]["verdict"])

    def test_major_finding_builds_self_verifying_hold_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            finding = {
                "id": "T-HOLD-001",
                "severity": "major",
                "dimension": "sourceFidelity",
                "path": "$.courses[0].activities[0]",
                "problem": "Source fidelity defect.",
                "impact": "The learner could encode a false rule.",
                "fix": "Repair only from the supplied source.",
                "evidence": [{
                    "sourceId": ws.source_id,
                    "locator": "source-section-1",
                    "basis": "The exact source contradicts the activity.",
                }],
            }
            ws.write_review(
                findings=[finding],
                dimension_status={"sourceFidelity": "hold"},
            )
            result = ws.consume()
            run = json.loads(ws.run.read_text(encoding="utf-8"))
            reliability.verify_run(run)
            self.assertEqual(handoff.PASS_CONSUMED, result["verdict"])
            self.assertEqual("HOLD_FACTORY_SEMANTIC_REVIEW", run["decision"]["verdict"])
            self.assertTrue(run["decision"]["reasons"])

    def test_minor_finding_preserves_existing_pass_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            finding = {
                "id": "T-MINOR-001",
                "severity": "minor",
                "dimension": "ambiguity",
                "path": "$.courses[0].activities[0].prompt",
                "problem": "Small wording issue.",
                "impact": "Small reading overhead.",
                "fix": "Clarify in a later revision.",
                "evidence": [],
            }
            ws.write_review(findings=[finding])
            ws.consume()
            run = json.loads(ws.run.read_text(encoding="utf-8"))
            self.assertEqual("PASS_AI_KIT_FACTORY_V1", run["decision"]["verdict"])
            self.assertEqual(
                1,
                run["evidenceBundle"]["factoryEvidence"]["semanticReview"]["counts"]["minor"],
            )

    def test_stale_review_target_is_rejected_before_factory_run(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            review = ws.write_review()
            review["target"]["kitSha256"] = "sha256:" + "0" * 64
            write_json(ws.review, review)
            with self.assertRaises(handoff.HandoffInputError):
                ws.consume()
            self.assertFalse(ws.run.exists())

    def test_independence_declaration_true_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            ws.write_review(scratchpad_seen=True)
            with self.assertRaises(handoff.HandoffInputError):
                ws.consume()
            self.assertFalse(ws.run.exists())

    def test_unknown_evidence_source_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            review = ws.write_review()
            review["dimensions"]["sourceFidelity"]["evidence"][0]["sourceId"] = "other-source"
            write_json(ws.review, review)
            with self.assertRaises(handoff.HandoffInputError):
                ws.consume()

    def test_consume_does_not_mutate_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            ws.prepare()
            ws.write_review()
            inputs = [ws.bundle, ws.review]
            before = hash_paths(inputs)
            ws.consume()
            self.assertEqual(before, hash_paths(inputs))


class CliBoundaryTests(unittest.TestCase):
    def test_cli_prepare_verify_consume(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(Path(td))
            prepare = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "authoring/factory/handoff.py"),
                    "prepare-review",
                    "--kit",
                    str(ws.kit),
                    "--brief",
                    str(ws.brief),
                    "--source",
                    f"{ws.source_id}={ws.source}",
                    "--admission",
                    f"{ws.source_id}={ws.admission}",
                    "--out",
                    str(ws.bundle),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, prepare.returncode, prepare.stdout + prepare.stderr)
            self.assertEqual(handoff.PASS_PREPARED, json.loads(prepare.stdout)["verdict"])

            verify = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "authoring/factory/handoff.py"),
                    "verify-review",
                    "--handoff",
                    str(ws.bundle),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)

            ws.write_review()
            consume = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "authoring/factory/handoff.py"),
                    "consume-review",
                    "--handoff",
                    str(ws.bundle),
                    "--review",
                    str(ws.review),
                    "--run-out",
                    str(ws.run),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, consume.returncode, consume.stdout + consume.stderr)
            self.assertEqual(handoff.PASS_CONSUMED, json.loads(consume.stdout)["verdict"])
            reliability.verify_run(json.loads(ws.run.read_text(encoding="utf-8")))

    def test_handoff_contains_no_network_or_provider_primitive(self):
        source = (ROOT / "authoring/factory/handoff.py").read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "httpx",
            "aiohttp",
            "urllib.request",
            "socket.",
            "OpenAI",
            "Anthropic",
            "api_key",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
