#!/usr/bin/env python3
"""Independent contradictory QA oracle for QA-WP-024-R2 / Atlas M3.4 release sets.

Authority: issue #331.
Frozen product HEAD: 870d69800dcb07fcfff9f1d232dd143c8eaa6486.

This file is QA-only. It does not repair product code and intentionally contains
assertions that fail if the frozen product accepts adversarial inputs that #328
requires to fail closed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import unittest
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import handoff
from authoring.factory import reliability
from authoring.factory import release_set
from authoring.v2 import validate_kit as v2
from authoring.v2.atlas import validate_atlas_content as atlas

EXPECTED_PRODUCT_HEAD = "870d69800dcb07fcfff9f1d232dd143c8eaa6486"
SIGNALS = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"
README = ROOT / "authoring/factory/README.md"
PRODUCT_SOURCE = ROOT / "authoring/factory/release_set.py"
PRODUCT_TESTS = ROOT / "authoring/factory/tests/test_release_set.py"
ZERO = "sha256:" + "0" * 64
UUID4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def canonical_write(path: Path, value: object) -> None:
    path.write_bytes(factory.canonical_json_bytes(value))


def deterministic_uuid(seed: str) -> str:
    raw = bytearray(hashlib.sha256(seed.encode("utf-8")).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


def _remap_uuids(value: object, seed: str, mapping: dict[str, str]) -> object:
    if isinstance(value, str) and UUID4.fullmatch(value):
        if value not in mapping:
            mapping[value] = deterministic_uuid(seed + ":" + value)
        return mapping[value]
    if isinstance(value, list):
        return [_remap_uuids(item, seed, mapping) for item in value]
    if isinstance(value, dict):
        return {
            key: _remap_uuids(item, seed, mapping)
            for key, item in value.items()
        }
    return value


def refresh_digests(kit: dict) -> dict:
    kit["packageRevisionDigest"] = ZERO
    for course in kit["courses"]:
        course["courseRevisionDigest"] = ZERO
        for activity in course["activities"]:
            activity["activityRevisionDigest"] = ZERO
    atlas.rewrite_claims(kit)
    errors = v2.fill_new_digests(kit)
    if errors:
        raise AssertionError(errors)
    atlas.validate_package(kit)
    return kit


def make_kit(index: int, *, title: str | None = None) -> dict:
    base = json.loads(SIGNALS.read_text(encoding="utf-8"))
    kit = _remap_uuids(copy.deepcopy(base), f"qa-wp-024-r2-{index}", {})
    assert isinstance(kit, dict)
    kit["title"] = title if title is not None else f"QA release fixture {index}"
    kit["versionLabel"] = f"qa-{index}"
    return refresh_digests(kit)


def semantic_review(context: dict, *, hold: bool = False) -> dict:
    source_id = context["sources"][0]["sourceId"]
    dimensions = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": source_id,
                "locator": "qa-fixture",
                "basis": f"Independent QA fixture evidence for {name}.",
            }]
        dimensions[name] = {
            "status": "hold" if hold and name == "answerCorrectness" else "pass",
            "summary": f"Independent QA fixture {name}.",
            "evidence": evidence,
        }
    finding = {
        "id": "QA-WP-024-R2-HOLD-SEMANTIC",
        "severity": "major",
        "dimension": "answerCorrectness",
        "path": "$.courses[0].activities[0]",
        "problem": "Deliberate semantic HOLD fixture.",
        "impact": "The corresponding FactoryRun must not be releasable.",
        "fix": "Use a genuinely PASS semantic review.",
        "evidence": [{
            "sourceId": source_id,
            "locator": "qa-fixture",
            "basis": "Deliberate contradictory QA HOLD evidence.",
        }],
    }
    return {
        "schema": factory.REVIEW_SCHEMA,
        "profile": factory.REVIEW_PROFILE,
        "target": {
            "contextDigest": context["contextDigest"],
            "kitSha256": context["kitSha256"],
            "sourceSetDigest": context["sourceSetDigest"],
            "briefSha256": context["briefSha256"],
        },
        "independence": {
            "authorScratchpadSeen": False,
            "authorActiveContextReused": False,
        },
        "dimensions": dimensions,
        "findings": [finding] if hold else [],
        "limitations": [],
        "verdict": factory.SEMANTIC_HOLD if hold else factory.SEMANTIC_PASS,
    }


def rehash_run(run: dict) -> dict:
    bundle = run["evidenceBundle"]
    gate = bundle["factoryEvidence"]
    bundle["factoryEvidenceSha256"] = reliability.digest(gate)
    bundle_core = {key: value for key, value in bundle.items() if key != "bundleSha256"}
    bundle["bundleSha256"] = reliability.digest(bundle_core)
    run_core = {key: value for key, value in run.items() if key != "runId"}
    run["runId"] = reliability.digest(run_core)
    return run


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.source = root / "source.txt"
        self.source.write_text(
            "Independent QA engineering source fixture.\n",
            encoding="utf-8",
        )
        self.brief = root / "brief.json"
        canonical_write(self.brief, {
            "schema": factory.BRIEF_SCHEMA,
            "audience": "independent QA engineering fixture learner",
            "goal": "Exercise contradictory release-set admission and verification",
            "language": "fr",
            "timeBudgetMinutes": 45,
        })
        self._template_run: dict | None = None

    def materialize(
        self,
        kit: dict,
        tag: str,
        *,
        hold: bool = False,
    ) -> tuple[Path, Path]:
        case = self.root / tag
        case.mkdir(parents=True, exist_ok=True)
        kit_path = case / "candidate.json"
        canonical_write(kit_path, kit)
        context = factory.build_context(
            kit_path,
            self.brief,
            [f"course={self.source}"],
        )
        review_path = case / "review.json"
        canonical_write(review_path, semantic_review(context, hold=hold))
        run = reliability.build_run(
            kit_path,
            self.brief,
            review_path,
            [f"course@qa-fixture-v1={self.source}"],
        )
        run_path = case / "factory-run.json"
        canonical_write(run_path, run)
        return run_path, kit_path

    def actual(
        self,
        index: int,
        *,
        hold: bool = False,
        title: str | None = None,
    ) -> tuple[Path, Path]:
        return self.materialize(
            make_kit(index, title=title),
            f"case-{index}-{'hold' if hold else 'pass'}",
            hold=hold,
        )

    def template_run(self) -> dict:
        if self._template_run is None:
            run_path, _ = self.actual(900000)
            self._template_run = json.loads(run_path.read_text(encoding="utf-8"))
        return copy.deepcopy(self._template_run)

    def synthetic(self, index: int) -> tuple[Path, Path]:
        """Fast engineering-only self-verifying row for Scale-100/500 mechanics."""
        case = self.root / f"synthetic-{index}"
        case.mkdir(parents=True, exist_ok=True)
        kit = make_kit(index)
        kit_path = case / "candidate.json"
        canonical_write(kit_path, kit)
        kit_raw = kit_path.read_bytes()

        run = self.template_run()
        kit_sha = factory.sha256_bytes(kit_raw)
        gate = run["evidenceBundle"]["factoryEvidence"]
        context = gate["context"]
        context["kitSha256"] = kit_sha
        context["contextDigest"] = factory.sha256_bytes(
            factory.canonical_json_bytes({
                "profile": context["profile"],
                "kitSha256": context["kitSha256"],
                "briefSha256": context["briefSha256"],
                "sourceSetDigest": context["sourceSetDigest"],
            })
        )
        run["factoryContextDigest"] = context["contextDigest"]
        run["evidenceBundle"]["artifacts"]["generatedKit"] = {
            "bytes": len(kit_raw),
            "sha256": kit_sha,
        }
        rehash_run(run)
        reliability.verify_run(copy.deepcopy(run))
        run_path = case / "factory-run.json"
        canonical_write(run_path, run)
        return run_path, kit_path


def specs(rows: list[tuple[Path, Path]]) -> list[str]:
    return [f"{run}={kit}" for run, kit in rows]


def zip_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as zf:
        return {name: zf.read(name) for name in zf.namelist()}


def write_custom_zip(
    path: Path,
    members: dict[str, bytes],
    *,
    compression: int = zipfile.ZIP_STORED,
    mutate_info=None,
) -> None:
    with zipfile.ZipFile(path, "w", compression=compression) as zf:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = compression
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            if mutate_info is not None:
                mutate_info(info)
            zf.writestr(info, members[name])


class QualifiedReleaseSetContradictoryQA(unittest.TestCase):
    maxDiff = None

    def test_00_oracle_is_bound_to_exact_product_head(self):
        self.assertEqual(
            EXPECTED_PRODUCT_HEAD,
            os.environ.get("QA_EXPECTED_PRODUCT_HEAD", EXPECTED_PRODUCT_HEAD),
        )

    def test_01_hold_factory_run_injection_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            row = fixture.actual(1, hold=True)
            with self.assertRaisesRegex(release_set.ReleaseSetInputError, "not releasable"):
                release_set.build_release_archive(specs([row]), root / "release.zip")

    def test_02_tampered_run_runid_and_generated_kit_hash_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            run_path, kit_path = fixture.actual(2)

            original = json.loads(run_path.read_text(encoding="utf-8"))
            variants = []

            tampered = copy.deepcopy(original)
            tampered["evidenceBundle"]["artifacts"]["generatedKit"]["bytes"] += 1
            variants.append(("tampered FactoryRun", tampered))

            bad_run_id = copy.deepcopy(original)
            bad_run_id["runId"] = "sha256:" + "f" * 64
            variants.append(("inconsistent runId", bad_run_id))

            bad_kit_hash = copy.deepcopy(original)
            bad_kit_hash["evidenceBundle"]["artifacts"]["generatedKit"]["sha256"] = (
                "sha256:" + "e" * 64
            )
            variants.append(("inconsistent generatedKit.sha256", bad_kit_hash))

            for index, (label, value) in enumerate(variants):
                with self.subTest(label=label):
                    path = root / f"tampered-{index}.json"
                    canonical_write(path, value)
                    with self.assertRaises(release_set.ReleaseSetInputError):
                        release_set.build_release_archive(
                            specs([(path, kit_path)]),
                            root / f"tampered-{index}.zip",
                        )

    def test_03_forged_pass_must_not_override_embedded_semantic_hold(self):
        """Attack #3: a self-rehashed PASS must not contradict its own HOLD evidence."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            hold_run_path, kit_path = fixture.actual(3, hold=True)
            forged = json.loads(hold_run_path.read_text(encoding="utf-8"))

            gate = forged["evidenceBundle"]["factoryEvidence"]
            self.assertEqual(factory.SEMANTIC_HOLD, gate["semanticReview"]["verdict"])
            self.assertNotEqual("PASS_AI_KIT_FACTORY_V1", gate["verdict"])

            gate["verdict"] = "PASS_AI_KIT_FACTORY_V1"
            gate["reasons"] = []
            forged_decision = {
                "verdict": "PASS_AI_KIT_FACTORY_V1",
                "reasons": [],
            }
            forged["decision"] = copy.deepcopy(forged_decision)
            forged["evidenceBundle"]["finalDecision"] = copy.deepcopy(forged_decision)
            rehash_run(forged)

            # Sanity: this is a deliberately adversarial, internally rehashed object.
            reliability.verify_run(copy.deepcopy(forged))
            forged_path = root / "forged-pass.json"
            canonical_write(forged_path, forged)

            with self.assertRaises(
                release_set.ReleaseSetInputError,
                msg=(
                    "QA-WP-024-R2 attack #3: release_set accepted a forged PASS whose "
                    "embedded semanticReview verdict is HOLD"
                ),
            ):
                release_set.build_release_archive(
                    specs([(forged_path, kit_path)]),
                    root / "forged-pass-release.zip",
                )

    def test_03b_forged_semantic_pass_with_major_count_is_rejected(self):
        """R2 regression: PASS summary still fails closed when major findings remain."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            hold_run_path, kit_path = fixture.actual(303, hold=True)
            forged = json.loads(hold_run_path.read_text(encoding="utf-8"))

            gate = forged["evidenceBundle"]["factoryEvidence"]
            self.assertEqual(factory.SEMANTIC_HOLD, gate["semanticReview"]["verdict"])
            self.assertGreater(gate["semanticReview"]["counts"]["major"], 0)

            gate["verdict"] = "PASS_AI_KIT_FACTORY_V1"
            gate["reasons"] = []
            gate["semanticReview"]["verdict"] = factory.SEMANTIC_PASS
            forged["evidenceBundle"]["validators"]["semanticReview"] = copy.deepcopy(
                gate["semanticReview"]
            )
            forged_decision = {
                "verdict": "PASS_AI_KIT_FACTORY_V1",
                "reasons": [],
            }
            forged["decision"] = copy.deepcopy(forged_decision)
            forged["evidenceBundle"]["finalDecision"] = copy.deepcopy(forged_decision)
            rehash_run(forged)

            reliability.verify_run(copy.deepcopy(forged))
            forged_path = root / "forged-semantic-pass-major.json"
            canonical_write(forged_path, forged)

            with self.assertRaisesRegex(
                release_set.ReleaseSetInputError,
                "semantic findings do not support PASS",
            ):
                release_set.build_release_archive(
                    specs([(forged_path, kit_path)]),
                    root / "forged-semantic-pass-major-release.zip",
                )

    def test_04_exact_kit_binding_drift_and_wrong_pair_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            run_a, kit_a = fixture.actual(4)
            _run_b, kit_b = fixture.actual(5)

            drift = root / "drift.json"
            drift.write_bytes(kit_a.read_bytes() + b"\n")
            with self.assertRaisesRegex(release_set.ReleaseSetInputError, "exact kit bytes"):
                release_set.build_release_archive(
                    specs([(run_a, drift)]),
                    root / "drift.zip",
                )

            with self.assertRaisesRegex(release_set.ReleaseSetInputError, "exact kit bytes"):
                release_set.build_release_archive(
                    specs([(run_a, kit_b)]),
                    root / "wrong-kit.zip",
                )

    def test_05_package_identity_collision_classes_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            a = make_kit(6)
            b = make_kit(7)

            # Reused package revision ID with a different digest/exact kit.
            b["packageRevisionId"] = a["packageRevisionId"]
            refresh_digests(b)
            row_a = fixture.materialize(a, "pkg-a")
            row_b = fixture.materialize(b, "pkg-b")
            with self.assertRaisesRegex(
                release_set.ReleaseSetInputError,
                "package revision exact-byte collision|revision digest collision",
            ):
                release_set.build_release_archive(
                    specs([row_a, row_b]),
                    root / "package-revision-collision.zip",
                )

            # Duplicate package lineage with a distinct package revision.
            c = make_kit(8)
            d = make_kit(9)
            d["packageLineageId"] = c["packageLineageId"]
            refresh_digests(d)
            row_c = fixture.materialize(c, "lineage-c")
            row_d = fixture.materialize(d, "lineage-d")
            with self.assertRaisesRegex(release_set.ReleaseSetInputError, "duplicate packageLineageId"):
                release_set.build_release_archive(
                    specs([row_c, row_d]),
                    root / "duplicate-lineage.zip",
                )

    def test_06_course_and_activity_revision_conflicts_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)

            a = make_kit(10)
            b = make_kit(11)
            b["courses"][0]["courseRevisionId"] = a["courses"][0]["courseRevisionId"]
            refresh_digests(b)
            row_a = fixture.materialize(a, "course-a")
            row_b = fixture.materialize(b, "course-b")
            with self.assertRaisesRegex(release_set.ReleaseSetInputError, "revision digest collision"):
                release_set.build_release_archive(
                    specs([row_a, row_b]),
                    root / "course-collision.zip",
                )

            c = make_kit(12)
            d = make_kit(13)
            d["courses"][0]["activities"][0]["activityRevisionId"] = (
                c["courses"][0]["activities"][0]["activityRevisionId"]
            )
            refresh_digests(d)
            row_c = fixture.materialize(c, "activity-c")
            row_d = fixture.materialize(d, "activity-d")
            with self.assertRaisesRegex(release_set.ReleaseSetInputError, "revision digest collision"):
                release_set.build_release_archive(
                    specs([row_c, row_d]),
                    root / "activity-collision.zip",
                )

    def test_07_ambiguous_revision_digest_and_duplicate_inputs_are_not_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)

            kit = make_kit(14)
            kit["packageRevisionDigest"] = "sha256:" + "1" * 64
            invalid_kit = root / "invalid-digest.json"
            canonical_write(invalid_kit, kit)
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.validate_kit_value(
                    json.loads(invalid_kit.read_text(encoding="utf-8")),
                    "ambiguous-digest",
                )

            row = fixture.actual(15)
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.build_release_archive(
                    specs([row, row]),
                    root / "duplicate-exact-input.zip",
                )

            copied_run = root / "copied-run.json"
            copied_kit = root / "copied-kit.json"
            shutil.copyfile(row[0], copied_run)
            shutil.copyfile(row[1], copied_kit)
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.build_release_archive(
                    specs([row, (copied_run, copied_kit)]),
                    root / "duplicate-logical-input.zip",
                )

    def test_08_archive_path_member_and_metadata_attacks_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            row = fixture.actual(16)
            release = root / "release.zip"
            release_set.build_release_archive(specs([row]), release)
            members = zip_members(release)

            attacks: list[tuple[str, Path]] = []

            for label, name in (
                ("traversal", "../escape.txt"),
                ("backslash", "kits\\escape.txt"),
                ("absolute", "/absolute.txt"),
            ):
                path = root / f"{label}.zip"
                tampered = dict(members)
                tampered[name] = b"x"
                # Unsafe names cannot be produced by handoff.zip_bytes, so use zipfile directly.
                with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
                    for member, data in members.items():
                        zf.writestr(member, data)
                    zf.writestr(name, b"x")
                attacks.append((label, path))

            duplicate = root / "duplicate-member.zip"
            with zipfile.ZipFile(duplicate, "w", compression=zipfile.ZIP_STORED) as zf:
                for member, data in members.items():
                    zf.writestr(member, data)
                first = sorted(members)[0]
                zf.writestr(first, members[first])
            attacks.append(("duplicate member", duplicate))

            extra = root / "extra-member.zip"
            extra_members = dict(members)
            extra_members["extra.txt"] = b"x"
            extra.write_bytes(handoff.zip_bytes(extra_members))
            attacks.append(("extra undeclared member", extra))

            missing = root / "missing-member.zip"
            missing_members = dict(members)
            kit_name = next(name for name in missing_members if name.startswith("kits/"))
            missing_members.pop(kit_name)
            missing.write_bytes(handoff.zip_bytes(missing_members))
            attacks.append(("missing declared member", missing))

            renamed = root / "renamed-member.zip"
            renamed_members = dict(members)
            kit_name = next(name for name in renamed_members if name.startswith("kits/"))
            payload = renamed_members.pop(kit_name)
            renamed_members[kit_name + ".renamed"] = payload
            renamed.write_bytes(handoff.zip_bytes(renamed_members))
            attacks.append(("renamed member", renamed))

            noncanonical = root / "deflated.zip"
            write_custom_zip(noncanonical, members, compression=zipfile.ZIP_DEFLATED)
            attacks.append(("changed compression", noncanonical))

            metadata = root / "metadata.zip"
            def mutate_timestamp(info):
                info.date_time = (2026, 1, 2, 3, 4, 6)
            write_custom_zip(metadata, members, mutate_info=mutate_timestamp)
            attacks.append(("changed metadata", metadata))

            symlink = root / "symlink.zip"
            def mutate_symlink(info):
                if info.filename != "release-set.json":
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
            write_custom_zip(symlink, members, mutate_info=mutate_symlink)
            attacks.append(("non-regular member", symlink))

            for label, path in attacks:
                with self.subTest(label=label):
                    with self.assertRaises(release_set.ReleaseSetInputError):
                        release_set.verify_release_archive(path)

    def test_09_semantic_manifest_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            row = fixture.actual(17)
            release = root / "release.zip"
            release_set.build_release_archive(specs([row]), release)
            members = zip_members(release)
            manifest = json.loads(members["release-set.json"].decode("utf-8"))
            manifest["metrics"]["activities"] += 1
            members["release-set.json"] = factory.canonical_json_bytes(manifest)
            tampered = root / "tampered-manifest.zip"
            tampered.write_bytes(handoff.zip_bytes(members))
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.verify_release_archive(tampered)

    def test_10_manifest_representation_tamper_must_fail_closed(self):
        """Attack #25/#30: same JSON object, different manifest bytes must not verify."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            row = fixture.actual(18)
            original = root / "release.zip"
            built = release_set.build_release_archive(specs([row]), original)
            members = zip_members(original)
            manifest = json.loads(members["release-set.json"].decode("utf-8"))

            pretty = (json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=False,
                indent=2,
            ) + "\n").encode("utf-8")
            self.assertNotEqual(members["release-set.json"], pretty)

            tampered_members = dict(members)
            tampered_members["release-set.json"] = pretty
            tampered = root / "representation-tampered.zip"
            tampered.write_bytes(handoff.zip_bytes(tampered_members))
            self.assertNotEqual(original.read_bytes(), tampered.read_bytes())

            with self.assertRaises(
                release_set.ReleaseSetInputError,
                msg=(
                    "QA-WP-024-R2 attack #25/#30: verifier accepted noncanonical "
                    "release-set.json bytes, allowing different ZIP bytes under the "
                    f"same releaseSetId {built['releaseSetId']}"
                ),
            ):
                release_set.verify_release_archive(tampered)

    def test_11_determinism_order_relocation_rebuild_and_homonymous_titles(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            rows = [
                fixture.actual(19, title="Même titre"),
                fixture.actual(20, title="Même titre"),
                fixture.actual(21),
            ]

            a = root / "a.zip"
            b = root / "b.zip"
            c = root / "c.zip"
            result_a = release_set.build_release_archive(specs(rows), a)
            result_b = release_set.build_release_archive(specs(list(reversed(rows))), b)
            result_c = release_set.build_release_archive(specs(rows), c)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(a.read_bytes(), c.read_bytes())
            self.assertEqual(result_a["releaseSetId"], result_b["releaseSetId"])
            self.assertEqual(result_a["releaseSetId"], result_c["releaseSetId"])
            self.assertEqual(3, result_a["metrics"]["packages"])

            moved = root / "moved"
            moved.mkdir()
            moved_rows = []
            for index, (run, kit) in enumerate(rows):
                run_copy = moved / f"renamed-run-{index}.json"
                kit_copy = moved / f"renamed-kit-{index}.json"
                shutil.copyfile(run, run_copy)
                shutil.copyfile(kit, kit_copy)
                moved_rows.append((run_copy, kit_copy))
            relocated = root / "relocated.zip"
            result_relocated = release_set.build_release_archive(
                specs(moved_rows),
                relocated,
            )
            self.assertEqual(a.read_bytes(), relocated.read_bytes())
            self.assertEqual(result_a["releaseSetId"], result_relocated["releaseSetId"])

    def test_12_prior_release_remains_independently_verifiable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            first = root / "first.zip"
            second = root / "second.zip"
            first_result = release_set.build_release_archive(
                specs([fixture.actual(22)]),
                first,
            )
            release_set.build_release_archive(
                specs([fixture.actual(23), fixture.actual(24)]),
                second,
            )
            first_verify = release_set.verify_release_archive(first)
            self.assertEqual(first_result["releaseSetId"], first_verify["releaseSetId"])

    def _scale(self, count: int):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            # Engineering-only synthetic rows: release mechanics, not semantic qualification.
            rows = [fixture.synthetic(10000 + i) for i in range(count)]
            a = root / f"scale-{count}-a.zip"
            b = root / f"scale-{count}-b.zip"
            result_a = release_set.build_release_archive(specs(rows), a)
            result_b = release_set.build_release_archive(specs(list(reversed(rows))), b)
            self.assertEqual(count, result_a["metrics"]["packages"])
            self.assertEqual(result_a["releaseSetId"], result_b["releaseSetId"])
            self.assertEqual(a.read_bytes(), b.read_bytes())
            verified = release_set.verify_release_archive(a)
            self.assertEqual(count, verified["metrics"]["packages"])

    def test_13_scale_100_engineering_only(self):
        self._scale(100)

    def test_14_scale_500_engineering_only(self):
        self._scale(500)

    def test_15_static_complexity_security_scope_and_trust_boundary(self):
        source = PRODUCT_SOURCE.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        product_tests = PRODUCT_TESTS.read_text(encoding="utf-8")

        # No subprocess-per-kit, obvious quadratic/exponential helper, network,
        # GitHub/repository push, provider/model, learner-runtime or publication surface.
        forbidden_source = (
            "subprocess",
            "requests",
            "urllib",
            "http.client",
            "socket",
            "git push",
            "github",
            "openai",
            "apps/",
            "publish_release",
        )
        for token in forbidden_source:
            with self.subTest(token=token):
                self.assertNotIn(token, source.lower())

        self.assertNotIn("itertools.product", source)
        self.assertNotIn("itertools.combinations", source)
        collision_body = source.split("def collision_check", 1)[1].split("def metrics", 1)[0]
        self.assertEqual(1, collision_body.count("for entry, _kit, revisions in rows:"))

        # Scale fixtures are explicitly engineering-only.
        self.assertIn("engineering fixtures only", readme.lower())
        self.assertIn("not semantic qualification", readme.lower())
        self.assertIn("scale_100_engineering_fixture", product_tests)
        self.assertIn("scale_500_engineering_fixture", product_tests)

        # Trust boundary required by #328.
        self.assertIn("deterministic internal integrity", readme.lower())
        self.assertIn("exact binding", readme.lower())
        self.assertIn("not cryptographically signed", readme.lower())
        self.assertIn("does not authenticate", readme.lower())
        self.assertIn("remote-distribution trust model requires a separate gate", readme.lower())

    def test_16_release_zip_contains_only_manifest_kits_and_factory_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Fixture(root)
            release = root / "release.zip"
            release_set.build_release_archive(
                specs([fixture.actual(25), fixture.actual(26)]),
                release,
            )
            names = set(zip_members(release))
            self.assertIn("release-set.json", names)
            for name in names - {"release-set.json"}:
                self.assertTrue(
                    name.startswith("kits/") or name.startswith("factory-runs/"),
                    name,
                )
            forbidden_fragments = (
                "source",
                "learner-brief",
                "semantic-review",
                "review-handoff",
                "scratchpad",
                "review_request",
                "skill_atlas",
            )
            for name in names:
                lowered = name.lower()
                for fragment in forbidden_fragments:
                    self.assertNotIn(fragment, lowered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
