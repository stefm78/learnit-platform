#!/usr/bin/env python3
"""Product evidence for ATLAS-WP-021 M3.4 Qualified Release Set."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import handoff
from authoring.factory import reliability
from authoring.factory import release_set
from authoring.v2 import validate_kit as v2
from authoring.v2.atlas import validate_atlas_content as atlas

SIGNALS = ROOT / "authoring/v2/atlas/signaux_electriques_atlas.json"
ZERO = "sha256:" + "0" * 64
UUID4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def canonical_write(path: Path, value: object) -> None:
    path.write_bytes(factory.canonical_json_bytes(value))


def fake_uuid(seed: str) -> str:
    raw = list(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32])
    raw[12] = "4"
    raw[16] = "8"
    value = "".join(raw)
    return (
        f"{value[:8]}-{value[8:12]}-{value[12:16]}-"
        f"{value[16:20]}-{value[20:32]}"
    )


def clone_kit(base: dict, index: int) -> dict:
    mapping: dict[str, str] = {}

    def walk(value):
        if isinstance(value, str) and UUID4.fullmatch(value):
            if value not in mapping:
                mapping[value] = fake_uuid(f"scale-{index}:{value}")
            return mapping[value]
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        return value

    kit = walk(copy.deepcopy(base))
    kit["title"] = f"Scale fixture {index}"
    kit["versionLabel"] = f"scale-{index}"
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


def semantic_review(context: dict, hold: bool = False) -> dict:
    source_id = context["sources"][0]["sourceId"]
    dimensions = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": source_id,
                "locator": "fixture-section",
                "basis": f"Engineering fixture evidence for {name}.",
            }]
        dimensions[name] = {
            "status": "hold" if hold and name == "answerCorrectness" else "pass",
            "summary": f"Fixture {name} review.",
            "evidence": evidence,
        }
    finding = {
        "id": "RELSET-HOLD-001",
        "severity": "major",
        "dimension": "answerCorrectness",
        "path": "$.courses[0].activities[0]",
        "problem": "Engineering HOLD fixture.",
        "impact": "This run must not enter a release set.",
        "fix": "Use a PASS run.",
        "evidence": [{
            "sourceId": source_id,
            "locator": "fixture-section",
            "basis": "Deliberate engineering HOLD fixture.",
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


class FixtureFactory:
    def __init__(self, root: Path):
        self.root = root
        self.base = json.loads(SIGNALS.read_text(encoding="utf-8"))
        self.source = root / "source.txt"
        self.source.write_text(
            "Engineering source fixture for release-set tests.\n",
            encoding="utf-8",
        )
        self.brief = root / "brief.json"
        self.brief.write_text(json.dumps({
            "schema": factory.BRIEF_SCHEMA,
            "audience": "engineering fixture learner",
            "goal": "Exercise deterministic release-set infrastructure",
            "language": "fr",
            "timeBudgetMinutes": 45,
        }), encoding="utf-8")
        self._template_run = None

    def actual(self, index: int, hold: bool = False) -> tuple[Path, Path]:
        case = self.root / f"actual-{index}-{'hold' if hold else 'pass'}"
        case.mkdir()
        kit = clone_kit(self.base, index)
        kit_path = case / "kit.json"
        canonical_write(kit_path, kit)
        context = factory.build_context(
            kit_path, self.brief, [f"course={self.source}"]
        )
        review_path = case / "review.json"
        canonical_write(review_path, semantic_review(context, hold=hold))
        run = reliability.build_run(
            kit_path,
            self.brief,
            review_path,
            [f"course@fixture-v1={self.source}"],
        )
        run_path = case / "run.json"
        canonical_write(run_path, run)
        return run_path, kit_path

    def template_run(self) -> dict:
        if self._template_run is None:
            run_path, _kit_path = self.actual(900001)
            self._template_run = json.loads(run_path.read_text(encoding="utf-8"))
        return copy.deepcopy(self._template_run)

    def synthetic(self, index: int) -> tuple[Path, Path]:
        case = self.root / f"synthetic-{index}"
        case.mkdir()
        kit = clone_kit(self.base, 1000000 + index)
        kit_path = case / "kit.json"
        canonical_write(kit_path, kit)
        kit_raw = kit_path.read_bytes()

        run = self.template_run()
        kit_sha = factory.sha256_bytes(kit_raw)
        gate = run["evidenceBundle"]["factoryEvidence"]
        context = gate["context"]
        context["kitSha256"] = kit_sha
        context["contextDigest"] = factory.sha256_bytes(factory.canonical_json_bytes({
            "profile": context["profile"],
            "kitSha256": context["kitSha256"],
            "briefSha256": context["briefSha256"],
            "sourceSetDigest": context["sourceSetDigest"],
        }))
        run["factoryContextDigest"] = context["contextDigest"]
        run["evidenceBundle"]["artifacts"]["generatedKit"] = {
            "bytes": len(kit_raw),
            "sha256": kit_sha,
        }
        run["evidenceBundle"]["factoryEvidenceSha256"] = reliability.digest(gate)
        bundle = run["evidenceBundle"]
        bundle_core = {
            key: value for key, value in bundle.items() if key != "bundleSha256"
        }
        bundle["bundleSha256"] = reliability.digest(bundle_core)
        run_core = {key: value for key, value in run.items() if key != "runId"}
        run["runId"] = reliability.digest(run_core)
        reliability.verify_run(copy.deepcopy(run))

        run_path = case / "run.json"
        canonical_write(run_path, run)
        return run_path, kit_path


def specs(rows: list[tuple[Path, Path]]) -> list[str]:
    return [f"{run}={kit}" for run, kit in rows]


class ReleaseSetTests(unittest.TestCase):
    def test_01_build_is_deterministic_order_and_path_independent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixtures = FixtureFactory(root)
            rows = [fixtures.actual(i) for i in range(1, 4)]
            a = root / "a.zip"
            b = root / "b.zip"
            release_set.build_release_archive(specs(rows), a)
            release_set.build_release_archive(specs(list(reversed(rows))), b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            verified = release_set.verify_release_archive(a)
            self.assertEqual(release_set.PASS_VERIFIED, verified["verdict"])
            self.assertEqual(3, verified["metrics"]["packages"])
            self.assertNotIn(str(root).encode(), a.read_bytes())

    def test_02_hold_and_kit_byte_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixtures = FixtureFactory(root)
            hold = fixtures.actual(1, hold=True)
            with self.assertRaisesRegex(release_set.ReleaseSetInputError, "not releasable"):
                release_set.build_release_archive(specs([hold]), root / "hold.zip")

            run_path, kit_path = fixtures.actual(2)
            kit_path.write_bytes(kit_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(release_set.ReleaseSetInputError, "exact kit bytes"):
                release_set.build_release_archive(
                    specs([(run_path, kit_path)]), root / "drift.zip"
                )

    def test_03_duplicate_lineage_and_revision_collision_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixtures = FixtureFactory(root)
            one = fixtures.actual(1)
            with self.assertRaisesRegex(release_set.ReleaseSetInputError, "duplicate"):
                release_set.build_release_archive(specs([one, one]), root / "dup.zip")

            run_a, kit_a = fixtures.actual(2)
            run_b, kit_b = fixtures.actual(3)
            a = json.loads(kit_a.read_text(encoding="utf-8"))
            b = json.loads(kit_b.read_text(encoding="utf-8"))
            b["courses"][0]["activities"][0]["activityRevisionId"] = (
                a["courses"][0]["activities"][0]["activityRevisionId"]
            )
            b["packageRevisionDigest"] = ZERO
            for course in b["courses"]:
                course["courseRevisionDigest"] = ZERO
                for activity in course["activities"]:
                    activity["activityRevisionDigest"] = ZERO
            atlas.rewrite_claims(b)
            errors = v2.fill_new_digests(b)
            self.assertFalse(errors)
            atlas.validate_package(b)
            canonical_write(kit_b, b)

            context = factory.build_context(
                kit_b, fixtures.brief, [f"course={fixtures.source}"]
            )
            review = root / "review-b.json"
            canonical_write(review, semantic_review(context))
            run_value = reliability.build_run(
                kit_b,
                fixtures.brief,
                review,
                [f"course@fixture-v1={fixtures.source}"],
            )
            canonical_write(run_b, run_value)

            with self.assertRaisesRegex(
                release_set.ReleaseSetInputError, "revision digest collision"
            ):
                release_set.build_release_archive(
                    specs([(run_a, kit_a), (run_b, kit_b)]), root / "collision.zip"
                )

    def test_04_archive_tamper_extra_traversal_and_duplicate_members_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixtures = FixtureFactory(root)
            row = fixtures.actual(1)
            release = root / "release.zip"
            release_set.build_release_archive(specs([row]), release)

            with zipfile.ZipFile(release, "r") as zf:
                members = {name: zf.read(name) for name in zf.namelist()}

            extra = dict(members)
            extra["extra.txt"] = b"unexpected"
            extra_path = root / "extra.zip"
            extra_path.write_bytes(handoff.zip_bytes(extra))
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.verify_release_archive(extra_path)

            traversal = root / "traversal.zip"
            with zipfile.ZipFile(traversal, "w", compression=zipfile.ZIP_STORED) as zf:
                for name, data in members.items():
                    zf.writestr(name, data)
                zf.writestr("../escape.txt", b"x")
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.verify_release_archive(traversal)

            duplicate = root / "duplicate.zip"
            with zipfile.ZipFile(duplicate, "w", compression=zipfile.ZIP_STORED) as zf:
                name = sorted(members)[0]
                for member, data in members.items():
                    zf.writestr(member, data)
                zf.writestr(name, members[name])
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.verify_release_archive(duplicate)

    def test_05_manifest_tamper_and_noncanonical_zip_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixtures = FixtureFactory(root)
            row = fixtures.actual(1)
            release = root / "release.zip"
            release_set.build_release_archive(specs([row]), release)
            with zipfile.ZipFile(release, "r") as zf:
                members = {name: zf.read(name) for name in zf.namelist()}

            manifest = json.loads(members["release-set.json"].decode("utf-8"))
            manifest["metrics"]["activities"] += 1
            members["release-set.json"] = factory.canonical_json_bytes(manifest)
            tampered = root / "tampered.zip"
            tampered.write_bytes(handoff.zip_bytes(members))
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.verify_release_archive(tampered)

            with zipfile.ZipFile(release, "r") as zf:
                clean_members = {name: zf.read(name) for name in zf.namelist()}
            noncanonical = root / "noncanonical.zip"
            with zipfile.ZipFile(noncanonical, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for name, data in clean_members.items():
                    zf.writestr(name, data)
            with self.assertRaises(release_set.ReleaseSetInputError):
                release_set.verify_release_archive(noncanonical)

    def test_06_prior_release_remains_verifiable_after_newer_release(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixtures = FixtureFactory(root)
            first = root / "first.zip"
            second = root / "second.zip"
            release_set.build_release_archive(specs([fixtures.actual(1)]), first)
            first_id = release_set.verify_release_archive(first)["releaseSetId"]
            release_set.build_release_archive(
                specs([fixtures.actual(2), fixtures.actual(3)]), second
            )
            self.assertNotEqual(
                first_id, release_set.verify_release_archive(second)["releaseSetId"]
            )
            self.assertEqual(
                first_id, release_set.verify_release_archive(first)["releaseSetId"]
            )

    def _scale(self, count: int):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixtures = FixtureFactory(root)
            rows = [fixtures.synthetic(i) for i in range(count)]
            a = root / f"scale-{count}-a.zip"
            b = root / f"scale-{count}-b.zip"
            result_a = release_set.build_release_archive(specs(rows), a)
            result_b = release_set.build_release_archive(
                specs(list(reversed(rows))), b
            )
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(count, result_a["metrics"]["packages"])
            self.assertEqual(result_a["releaseSetId"], result_b["releaseSetId"])
            verified = release_set.verify_release_archive(a)
            self.assertEqual(count, verified["metrics"]["packages"])
            self.assertEqual(release_set.PASS_VERIFIED, verified["verdict"])

    def test_07_scale_100_engineering_fixture(self):
        self._scale(100)

    def test_08_scale_500_engineering_fixture(self):
        self._scale(500)

    def test_09_no_network_repository_write_or_private_evidence_surface(self):
        source = (ROOT / "authoring/factory/release_set.py").read_text(
            encoding="utf-8"
        )
        forbidden = [
            "urllib",
            "requests",
            "http.client",
            "socket",
            "subprocess",
            "git push",
            "semantic_review.json",
            "source-admission",
            "REVIEW_REQUEST",
            "scratchpad",
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
