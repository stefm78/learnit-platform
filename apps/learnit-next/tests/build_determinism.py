#!/usr/bin/env python3
"""Contradictory clean-build, manifest and artifact-identity tests.

No build CLI shape is imposed on the implementation. The harness uses
LEARNIT_NEXT_BUILD_COMMAND when supplied; otherwise it executes the integrator-owned
build.py with the current Python interpreter. Paths and declarations are discovered by
content, not by implementation function names.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]
APP_REL = Path("apps/learnit-next")
BUILD_REL = APP_REL / "build.py"
MANIFEST_REL = APP_REL / "source_manifest.json"
ARTIFACT_REL = APP_REL / "dist/learnit-next.html"
FILE_PLAN_REL = Path("docs/architecture/clean-generation/FILE_PLAN_V1.json")

PLANNED_BUILD_INPUTS = {
    "apps/learnit-next/index.template.html",
    "apps/learnit-next/src/styles.css",
    "apps/learnit-next/src/main.js",
    "apps/learnit-next/src/core/canonical_json.js",
    "apps/learnit-next/src/core/identity.js",
    "apps/learnit-next/src/core/contract.js",
    "apps/learnit-next/src/core/import.js",
    "apps/learnit-next/src/core/library.js",
    "apps/learnit-next/src/core/session.js",
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/ports/storage.js",
    "apps/learnit-next/src/adapters/indexeddb.js",
    "apps/learnit-next/src/ui/render.js",
}
QA_PATHS = {
    "contracts/fixtures/v2-valid-minimal.json",
    "contracts/fixtures/v2-invalid-legacy.json",
    "contracts/fixtures/v2-invalid-digest-mismatch.json",
    "apps/learnit-next/tests/contract_v2.py",
    "apps/learnit-next/tests/storage_isolation.py",
    "apps/learnit-next/tests/browser_vertical_slice.py",
    "apps/learnit-next/tests/build_determinism.py",
}
GENERATED_DIRS = (
    APP_REL / "dist",
    APP_REL / "release",
    APP_REL / ".agent-runtime",
    APP_REL / ".agent-result",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def iter_string_lists(value: Any) -> Iterable[list[str]]:
    if isinstance(value, list):
        if value and all(isinstance(item, str) for item in value):
            yield value
        for item in value:
            yield from iter_string_lists(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_string_lists(item)


def normalise_repo_path(entry: str) -> str | None:
    value = entry.replace("\\", "/").lstrip("./")
    candidates = [value, f"apps/learnit-next/{value}"]
    for candidate in candidates:
        if candidate in PLANNED_BUILD_INPUTS:
            return candidate
    return None


def extract_ordered_sources(manifest: Any) -> list[str]:
    candidates: list[list[str]] = []
    for values in iter_string_lists(manifest):
        normalised = [normalise_repo_path(item) for item in values]
        if all(item is not None for item in normalised):
            source_list = [item for item in normalised if item is not None]
            if set(source_list) == PLANNED_BUILD_INPUTS:
                candidates.append(source_list)
    if len(candidates) != 1:
        raise AssertionError(
            "source manifest must expose exactly one ordered list containing every planned "
            f"build input; found {len(candidates)} candidates"
        )
    sources = candidates[0]
    if len(sources) != len(set(sources)):
        raise AssertionError("source manifest contains duplicate source entries")
    return sources


def extract_declared_artifact_paths(value: Any) -> set[str]:
    result: set[str] = set()
    for text in iter_strings(value):
        normalised = text.replace("\\", "/").lstrip("./")
        if normalised.endswith("apps/learnit-next/dist/learnit-next.html"):
            result.add("apps/learnit-next/dist/learnit-next.html")
        elif normalised.endswith("dist/learnit-next.html"):
            result.add("apps/learnit-next/dist/learnit-next.html")
    return result


def extract_sha256_values(value: Any) -> set[str]:
    result: set[str] = set()
    for text in iter_strings(value):
        candidate = text.lower()
        if candidate.startswith("sha256:"):
            candidate = candidate[7:]
        if len(candidate) == 64 and all(char in "0123456789abcdef" for char in candidate):
            result.add(candidate)
    return result


def source_tree_files(root: Path) -> set[str]:
    app = root / APP_REL
    files: set[str] = set()
    for relative_root in (Path("index.template.html"), Path("src")):
        target = app / relative_root
        if target.is_file():
            files.add(target.relative_to(root).as_posix())
        elif target.exists():
            files.update(
                path.relative_to(root).as_posix()
                for path in target.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            )
    return files


def assert_planned_source_tree(root: Path) -> None:
    actual = source_tree_files(root)
    extra = sorted(actual - PLANNED_BUILD_INPUTS)
    missing = sorted(PLANNED_BUILD_INPUTS - actual)
    if extra or missing:
        raise AssertionError(f"source tree drift: extra={extra}, missing={missing}")


def clean_generated(root: Path) -> None:
    for relative in GENERATED_DIRS:
        shutil.rmtree(root / relative, ignore_errors=True)
    for cache in root.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    for cache in root.rglob(".pytest_cache"):
        shutil.rmtree(cache, ignore_errors=True)


def copy_repository(destination: Path) -> Path:
    target = destination / "repo"

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {".git", "__pycache__", ".pytest_cache"} & set(names)
        directory_path = Path(directory)
        if directory_path.name == "learnit-next":
            ignored |= {"dist", "release", ".agent-runtime", ".agent-result"} & set(names)
        return ignored

    shutil.copytree(ROOT, target, ignore=ignore)
    clean_generated(target)
    return target


def build_command(root: Path) -> list[str]:
    configured = os.environ.get("LEARNIT_NEXT_BUILD_COMMAND")
    if configured:
        return [part.format(repo=str(root)) for part in shlex.split(configured)]
    return [sys.executable, str(root / BUILD_REL)]


def run_build(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        build_command(root),
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=int(os.environ.get("LEARNIT_NEXT_BUILD_TIMEOUT", "120")),
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def declaration_files(root: Path) -> list[Path]:
    app = root / APP_REL
    files = [root / MANIFEST_REL]
    for generated in (app / "dist", app / "release"):
        if generated.exists():
            files.extend(path for path in generated.rglob("*.json") if path.is_file())
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        if path.exists() and path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def assert_artifact_declared(root: Path, artifact_hash: str) -> None:
    path_evidence: list[Path] = []
    hash_evidence: list[Path] = []
    joint_evidence: list[Path] = []
    for path in declaration_files(root):
        try:
            payload = load_json(path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        has_path = ARTIFACT_REL.as_posix() in extract_declared_artifact_paths(payload)
        has_hash = artifact_hash in extract_sha256_values(payload)
        if has_path:
            path_evidence.append(path)
        if has_hash:
            hash_evidence.append(path)
        if has_path and has_hash:
            joint_evidence.append(path)
    if not path_evidence:
        raise AssertionError("absence of proof: no manifest declares the tested artifact path")
    if not hash_evidence:
        raise AssertionError("absence of proof: no generated declaration contains tested SHA-256")
    if not joint_evidence:
        raise AssertionError(
            "artifact path and SHA-256 exist only in separate unbound claims; one declaration "
            "must bind both"
        )


class BuildHarnessOracleTests(unittest.TestCase):
    def test_file_plan_is_exact_and_assigns_the_seven_qa_paths(self) -> None:
        plan = load_json(ROOT / FILE_PLAN_REL)
        self.assertEqual(32, plan["workingFileBudget"])
        self.assertEqual(
            QA_PATHS,
            set(plan["roles"]["qa-fixture-agent"]["paths"]),
        )
        all_paths = {
            entry["path"] for entry in plan["frozenSharedFiles"]
        }
        for role in plan["roles"].values():
            for path in role["paths"]:
                self.assertNotIn(path, all_paths, f"duplicate planned path: {path}")
                all_paths.add(path)
        self.assertEqual(32, len(all_paths))

    def test_manifest_source_extractor_is_shape_independent_and_order_preserving(self) -> None:
        ordered = sorted(PLANNED_BUILD_INPUTS, reverse=True)
        manifest = {"metadata": {"name": "qa"}, "arbitrary": {"ordered": ordered}}
        self.assertEqual(ordered, extract_ordered_sources(manifest))

    def test_source_tree_auditor_rejects_an_unplanned_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in PLANNED_BUILD_INPUTS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("planned", encoding="utf-8")
            assert_planned_source_tree(root)
            probe = root / "apps/learnit-next/src/qa_unplanned_probe.js"
            probe.write_text("unplanned", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "source tree drift"):
                assert_planned_source_tree(root)


class IntegratedBuildDeterminismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (ROOT / BUILD_REL).exists() or not (ROOT / MANIFEST_REL).exists():
            raise unittest.SkipTest(
                "WAITING_FOR_INTEGRATION: build.py and source_manifest.json are integrator-owned"
            )

    def make_clean_copy(self, parent: Path, name: str) -> Path:
        destination = parent / name
        destination.mkdir()
        return copy_repository(destination)

    def assert_build_succeeds(self, root: Path) -> tuple[bytes, str, str]:
        assert_planned_source_tree(root)
        manifest = load_json(root / MANIFEST_REL)
        self.assertEqual(PLANNED_BUILD_INPUTS, set(extract_ordered_sources(manifest)))
        process = run_build(root)
        self.assertEqual(0, process.returncode, process.stdout)
        artifact = root / ARTIFACT_REL
        self.assertTrue(artifact.is_file(), f"build did not create {ARTIFACT_REL}\n{process.stdout}")
        artifact_bytes = artifact.read_bytes()
        artifact_hash = sha256(artifact)
        return artifact_bytes, artifact_hash, process.stdout

    def test_two_clean_builds_produce_identical_bytes_and_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            first = self.make_clean_copy(parent, "first")
            second = self.make_clean_copy(parent, "second")
            first_bytes, first_hash, first_output = self.assert_build_succeeds(first)
            second_bytes, second_hash, second_output = self.assert_build_succeeds(second)
            self.assertEqual(first_bytes, second_bytes, f"build outputs differ\nFIRST\n{first_output}\nSECOND\n{second_output}")
            self.assertEqual(first_hash, second_hash)

    def test_source_manifest_is_coherent_and_declares_the_tested_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_clean_copy(Path(directory), "declaration")
            _artifact_bytes, artifact_hash, _output = self.assert_build_succeeds(root)
            manifest_before = (root / MANIFEST_REL).read_bytes()
            self.assertEqual({ARTIFACT_REL.as_posix()}, extract_declared_artifact_paths(load_json(root / MANIFEST_REL)))
            self.assertEqual(manifest_before, (root / MANIFEST_REL).read_bytes(), "build mutated source manifest")
            assert_artifact_declared(root, artifact_hash)

    def test_build_fails_closed_when_an_unplanned_source_file_appears(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_clean_copy(Path(directory), "unplanned")
            probe = root / "apps/learnit-next/src/qa_unplanned_probe.js"
            probe.write_text("throw new Error('unplanned source probe');\n", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "source tree drift"):
                assert_planned_source_tree(root)
            process = run_build(root)
            self.assertNotEqual(
                0,
                process.returncode,
                "build accepted an unplanned source file; preflight alone is not sufficient\n"
                + process.stdout,
            )

    def test_build_fails_closed_when_a_manifest_source_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_clean_copy(Path(directory), "missing")
            missing = root / "apps/learnit-next/src/core/identity.js"
            missing.unlink()
            with self.assertRaisesRegex(AssertionError, "source tree drift"):
                assert_planned_source_tree(root)
            process = run_build(root)
            self.assertNotEqual(
                0,
                process.returncode,
                "build accepted source drift after a declared input was removed\n" + process.stdout,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
