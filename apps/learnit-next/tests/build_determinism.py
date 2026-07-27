#!/usr/bin/env python3
"""Contradictory clean-build and three-mode topology regression tests."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
APP_REL = Path("apps/learnit-next")
BUILD_REL = APP_REL / "build.py"
MANIFEST_REL = APP_REL / "source_manifest.json"
ARTIFACT_REL = APP_REL / "dist/learnit-next.html"
FILE_PLAN_REL = Path("docs/architecture/clean-generation/FILE_PLAN_V1.json")
STRICT = os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION") == "1"

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
EXPECTED_INTEGRATION_PATHS = {
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/core/session.js",
    "apps/learnit-next/src/main.js",
    "apps/learnit-next/src/ui/render.js",
    "work-packages/PROD-WP-003.json",
    "apps/learnit-next/tests/p1_corrective_review.py",
    "apps/learnit-next/source_manifest.json",
    "apps/learnit-next/dev/run_checks.py",
    "apps/learnit-next/tests/build_determinism.py",
}
GENERATED_DIRS = (
    APP_REL / "dist",
    APP_REL / "release",
    APP_REL / ".agent-runtime",
    APP_REL / ".agent-result",
)


def require_or_skip(condition, message):
    if condition:
        return
    if STRICT:
        raise RuntimeError(message)
    raise unittest.SkipTest(message)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def iter_string_lists(value):
    if isinstance(value, list):
        if value and all(isinstance(item, str) for item in value):
            yield value
        for item in value:
            yield from iter_string_lists(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_string_lists(item)


def normalise_repo_path(entry):
    value = entry.replace("\\", "/").lstrip("./")
    for candidate in (value, f"apps/learnit-next/{value}"):
        if candidate in PLANNED_BUILD_INPUTS:
            return candidate
    return None


def extract_ordered_sources(manifest):
    candidates = []
    for values in iter_string_lists(manifest):
        normal = [normalise_repo_path(item) for item in values]
        if all(item is not None for item in normal) and set(normal) == PLANNED_BUILD_INPUTS:
            candidates.append(normal)
    if len(candidates) != 1:
        raise AssertionError(
            f"manifest must expose exactly one planned ordered list; found {len(candidates)}"
        )
    if len(candidates[0]) != len(set(candidates[0])):
        raise AssertionError("duplicate manifest source")
    return candidates[0]


def extract_declared_artifact_paths(value):
    output = set()
    for item in iter_strings(value):
        normalized = item.replace("\\", "/").lstrip("./")
        if normalized.endswith("dist/learnit-next.html"):
            output.add(ARTIFACT_REL.as_posix())
    return output


def extract_sha256_values(value):
    output = set()
    for item in iter_strings(value):
        candidate = item.lower()
        candidate = candidate[7:] if candidate.startswith("sha256:") else candidate
        if len(candidate) == 64 and all(char in "0123456789abcdef" for char in candidate):
            output.add(candidate)
    return output


def source_tree_files(root):
    app = root / APP_REL
    output = set()
    for relative in (Path("index.template.html"), Path("src")):
        target = app / relative
        if target.is_file():
            output.add(target.relative_to(root).as_posix())
        elif target.exists():
            output |= {
                path.relative_to(root).as_posix()
                for path in target.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            }
    return output


def assert_planned_source_tree(root):
    actual = source_tree_files(root)
    extra = sorted(actual - PLANNED_BUILD_INPUTS)
    missing = sorted(PLANNED_BUILD_INPUTS - actual)
    if extra or missing:
        raise AssertionError(f"source tree drift: extra={extra}, missing={missing}")


def clean_generated(root):
    for relative in GENERATED_DIRS:
        shutil.rmtree(root / relative, ignore_errors=True)
    for cache in list(root.rglob("__pycache__")) + list(root.rglob(".pytest_cache")):
        shutil.rmtree(cache, ignore_errors=True)


def copy_repository(destination):
    target = destination / "repo"

    def ignore(directory, names):
        ignored = {".git", "__pycache__", ".pytest_cache"} & set(names)
        if Path(directory).name == "learnit-next":
            ignored |= {"dist", "release", ".agent-runtime", ".agent-result"} & set(names)
        return ignored

    shutil.copytree(ROOT, target, ignore=ignore)
    clean_generated(target)
    return target


def build_command(root):
    configured = os.environ.get("LEARNIT_NEXT_BUILD_COMMAND")
    if configured:
        return [part.format(repo=str(root)) for part in shlex.split(configured)]
    return [sys.executable, str(root / BUILD_REL)]


def run_build(root):
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


def declaration_files(root):
    files = [root / MANIFEST_REL]
    for generated in (root / APP_REL / "dist", root / APP_REL / "release"):
        if generated.exists():
            files.extend(path for path in generated.rglob("*.json") if path.is_file())
    return list(dict.fromkeys(path for path in files if path.exists()))


def assert_artifact_declared(root, artifact_hash):
    joint = []
    for path in declaration_files(root):
        try:
            payload = load_json(path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if (
            ARTIFACT_REL.as_posix() in extract_declared_artifact_paths(payload)
            and artifact_hash in extract_sha256_values(payload)
        ):
            joint.append(path)
    if len(joint) != 1:
        raise AssertionError(
            f"exactly one declaration must bind artifact path and SHA-256; found {joint}"
        )


class BuildHarnessOracleTests(unittest.TestCase):
    def test_file_plan_is_exact_and_assigns_the_seven_qa_paths(self):
        plan = load_json(ROOT / FILE_PLAN_REL)
        self.assertEqual(32, plan["workingFileBudget"])
        self.assertEqual(QA_PATHS, set(plan["roles"]["qa-fixture-agent"]["paths"]))
        all_paths = {entry["path"] for entry in plan["frozenSharedFiles"]}
        for role in plan["roles"].values():
            for path in role["paths"]:
                self.assertNotIn(path, all_paths)
                all_paths.add(path)
        self.assertEqual(32, len(all_paths))

    def test_manifest_source_extractor_is_shape_independent_and_order_preserving(self):
        ordered = sorted(PLANNED_BUILD_INPUTS, reverse=True)
        self.assertEqual(ordered, extract_ordered_sources({"arbitrary": {"ordered": ordered}}))

    def test_source_tree_auditor_rejects_an_unplanned_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in PLANNED_BUILD_INPUTS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("planned")
            assert_planned_source_tree(root)
            (root / "apps/learnit-next/src/qa_unplanned_probe.js").write_text("x")
            with self.assertRaisesRegex(AssertionError, "source tree drift"):
                assert_planned_source_tree(root)


class IntegratedBuildDeterminismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_or_skip(
            (ROOT / BUILD_REL).exists() and (ROOT / MANIFEST_REL).exists(),
            "WAITING_FOR_INTEGRATION: build.py and source_manifest.json are integrator-owned",
        )

    def make_copy(self, parent, name):
        destination = parent / name
        destination.mkdir()
        return copy_repository(destination)

    def build(self, root):
        assert_planned_source_tree(root)
        manifest = load_json(root / MANIFEST_REL)
        self.assertEqual(
            PLANNED_BUILD_INPUTS,
            set(extract_ordered_sources(manifest)),
        )
        process = run_build(root)
        self.assertEqual(0, process.returncode, process.stdout)
        artifact = root / ARTIFACT_REL
        self.assertTrue(artifact.is_file())
        data = artifact.read_bytes()
        return data, sha256_bytes(data), process.stdout

    def test_two_clean_builds_and_browser_artifact_are_identical(self):
        proposed = Path(os.environ.get("LEARNIT_NEXT_ARTIFACT", ROOT / ARTIFACT_REL))
        require_or_skip(
            proposed.is_file(),
            f"WAITING_FOR_INTEGRATION: browser artifact absent at {proposed}",
        )
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            first = self.make_copy(parent, "first")
            second = self.make_copy(parent, "second")
            build_a, hash_a, output_a = self.build(first)
            build_b, hash_b, output_b = self.build(second)
            browser = proposed.read_bytes()
            browser_hash = sha256_bytes(browser)
            self.assertEqual(
                build_a,
                build_b,
                f"clean builds differ\n{output_a}\n{output_b}",
            )
            self.assertEqual(hash_a, hash_b)
            self.assertEqual(build_a, browser, "browser-tested/proposed artifact differs from clean builds")
            self.assertEqual(hash_a, browser_hash)
            assert_artifact_declared(first, hash_a)
            assert_artifact_declared(second, hash_b)

    def test_source_manifest_is_coherent_and_declares_the_tested_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(Path(directory), "declaration")
            before = (root / MANIFEST_REL).read_bytes()
            _, artifact_hash, _ = self.build(root)
            self.assertEqual(
                before,
                (root / MANIFEST_REL).read_bytes(),
                "build mutated source manifest",
            )
            assert_artifact_declared(root, artifact_hash)

    def test_build_fails_closed_when_an_unplanned_source_file_appears(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(Path(directory), "unplanned")
            (root / "apps/learnit-next/src/qa_unplanned_probe.js").write_text("throw Error('probe')")
            with self.assertRaisesRegex(AssertionError, "source tree drift"):
                assert_planned_source_tree(root)
            self.assertNotEqual(0, run_build(root).returncode, "build accepted unplanned source")

    def test_build_fails_closed_when_a_manifest_source_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_copy(Path(directory), "missing")
            (root / "apps/learnit-next/src/core/identity.js").unlink()
            with self.assertRaisesRegex(AssertionError, "source tree drift"):
                assert_planned_source_tree(root)
            self.assertNotEqual(0, run_build(root).returncode, "build accepted missing declared source")


def load_ci_gate_module():
    path = ROOT / "apps/learnit-next/dev/run_checks.py"
    spec = importlib.util.spec_from_file_location("learnit_ci_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load CI gate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TopologyModeRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = load_ci_gate_module()

    def git_oracle(self, mapping):
        def fake_git(*args):
            key = tuple(args)
            if key not in mapping:
                raise AssertionError(f"unexpected git call: {key}")
            value = mapping[key]
            if isinstance(value, Exception):
                raise value
            return value

        return fake_git

    def ancestor_oracle(self, mapping):
        def fake_ancestor(older, newer):
            key = (older, newer)
            if key not in mapping:
                raise AssertionError(f"unexpected ancestor call: {key}")
            return mapping[key]

        return fake_ancestor

    def patch(self, git_map, ancestor_map=None):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(self.gate, "git", side_effect=self.git_oracle(git_map)))
        if ancestor_map is not None:
            stack.enter_context(
                mock.patch.object(
                    self.gate,
                    "ancestor",
                    side_effect=self.ancestor_oracle(ancestor_map),
                )
            )
        return stack

    def test_valid_current_integration_topology_passes(self):
        base = "a" * 40
        mapping = {
            ("rev-parse", "origin/main"): base,
            ("merge-base", "origin/main", "HEAD"): base,
            ("diff", "--name-only", "origin/main...HEAD"): "\n".join(
                sorted(EXPECTED_INTEGRATION_PATHS)
            ),
        }
        with self.patch(mapping, {(base, "HEAD"): True}):
            result = self.gate.integration_topology("origin/main")
        self.assertEqual(EXPECTED_INTEGRATION_PATHS, self.gate.INTEGRATION_ALLOWLIST)
        self.assertEqual(base, result["baseCommit"])
        self.assertEqual(sorted(EXPECTED_INTEGRATION_PATHS), result["changedPaths"])
        self.assertEqual(9, result["changedPathCount"])

    def test_integration_base_must_be_an_ancestor(self):
        base = "a" * 40
        with self.patch(
            {("rev-parse", "origin/main"): base},
            {(base, "HEAD"): False},
        ), self.assertRaisesRegex(
            self.gate.GateError,
            "base is not an ancestor",
        ) as caught:
            self.gate.integration_topology("origin/main")
        self.assertEqual("TOPOLOGY_FAILURE", caught.exception.classification)

    def test_integration_merge_base_and_allowlist_fail_closed(self):
        base = "a" * 40
        with self.subTest("merge-base"):
            mapping = {
                ("rev-parse", "origin/main"): base,
                ("merge-base", "origin/main", "HEAD"): "b" * 40,
            }
            with self.patch(mapping, {(base, "HEAD"): True}), self.assertRaisesRegex(
                self.gate.GateError,
                "merge-base differs",
            ) as caught:
                self.gate.integration_topology("origin/main")
            self.assertEqual("TOPOLOGY_FAILURE", caught.exception.classification)

        with self.subTest("allowlist"):
            incomplete = EXPECTED_INTEGRATION_PATHS - {
                "apps/learnit-next/tests/build_determinism.py"
            }
            mapping = {
                ("rev-parse", "origin/main"): base,
                ("merge-base", "origin/main", "HEAD"): base,
                ("diff", "--name-only", "origin/main...HEAD"): "\n".join(sorted(incomplete)),
            }
            with self.patch(mapping, {(base, "HEAD"): True}), self.assertRaisesRegex(
                self.gate.GateError,
                "integration diff differs",
            ) as caught:
                self.gate.integration_topology("origin/main")
            self.assertEqual("PROVENANCE_FAILURE", caught.exception.classification)

    def test_valid_two_parent_post_merge_reaches_provenance(self):
        first = "1" * 40
        accepted = self.gate.ACCEPTED_INTEGRATION_HEAD
        mapping = {
            ("show", "-s", "--format=%P", "HEAD"): f"{first} {accepted}",
            (
                "diff",
                "--name-only",
                accepted,
                "HEAD",
                "--",
                "apps/learnit-next/index.template.html",
                "apps/learnit-next/src",
                "apps/learnit-next/build.py",
                self.gate.SCHEMA,
            ): "",
        }
        with self.patch(mapping, {(self.gate.FROZEN_BASE, first): True}):
            self.assertEqual(
                [],
                self.gate.post_merge_topology(accepted)["executableTreeDivergence"],
            )

    def test_post_merge_first_parent_must_descend_from_frozen_base(self):
        first = "1" * 40
        accepted = self.gate.ACCEPTED_INTEGRATION_HEAD
        mapping = {("show", "-s", "--format=%P", "HEAD"): f"{first} {accepted}"}
        with self.patch(
            mapping,
            {(self.gate.FROZEN_BASE, first): False},
        ), self.assertRaisesRegex(
            self.gate.GateError,
            "does not descend",
        ) as caught:
            self.gate.post_merge_topology(accepted)
        self.assertEqual("TOPOLOGY_FAILURE", caught.exception.classification)

    def test_wrong_accepted_integration_head_fails_closed(self):
        with self.patch(
            {("show", "-s", "--format=%P", "HEAD"): f"{'1' * 40} {'2' * 40}"}
        ), self.assertRaisesRegex(
            self.gate.GateError,
            "wrong accepted integration head",
        ) as caught:
            self.gate.post_merge_topology("3" * 40)
        self.assertEqual("PROVENANCE_FAILURE", caught.exception.classification)

    def test_executable_tree_divergence_fails_closed(self):
        first = "1" * 40
        accepted = self.gate.ACCEPTED_INTEGRATION_HEAD
        key = (
            "diff",
            "--name-only",
            accepted,
            "HEAD",
            "--",
            "apps/learnit-next/index.template.html",
            "apps/learnit-next/src",
            "apps/learnit-next/build.py",
            self.gate.SCHEMA,
        )
        mapping = {
            ("show", "-s", "--format=%P", "HEAD"): f"{first} {accepted}",
            key: "apps/learnit-next/src/main.js",
        }
        with self.patch(
            mapping,
            {(self.gate.FROZEN_BASE, first): True},
        ), self.assertRaisesRegex(
            self.gate.GateError,
            "executable tree divergence",
        ) as caught:
            self.gate.post_merge_topology(accepted)
        self.assertEqual("EXECUTABLE_TREE_DIVERGENCE", caught.exception.classification)

    def test_missing_post_merge_identity_fails_as_configuration(self):
        with self.assertRaisesRegex(
            self.gate.GateError,
            "requires --accepted-integration-head",
        ) as caught:
            self.gate.post_merge_topology("")
        self.assertEqual("CONFIGURATION_FAILURE", caught.exception.classification)

    def maintenance_maps(self, changed=None, statuses=None, base=None):
        base = base or "a" * 40
        changed = sorted(self.gate.CI_ALLOWLIST) if changed is None else changed
        if statuses is None:
            statuses = [
                f'{"A" if path in {"work-packages/CI-WP-002.json", "apps/learnit-next/tests/build_determinism.py"} else "M"}\t{path}'
                for path in changed
            ]
        return base, {
            ("rev-parse", "origin/main"): base,
            ("merge-base", "origin/main", "HEAD"): base,
            ("diff", "--name-only", "origin/main...HEAD"): "\n".join(changed),
            ("diff", "--name-status", "origin/main...HEAD"): "\n".join(statuses),
        }

    def test_valid_maintenance_pr_requires_exact_modified_allowlist(self):
        base, mapping = self.maintenance_maps()
        with self.patch(
            mapping,
            {
                (self.gate.RELEASE_MERGE, base): True,
                (base, "HEAD"): True,
            },
        ):
            result = self.gate.maintenance_topology("origin/main")
        self.assertEqual(sorted(self.gate.CI_ALLOWLIST), result["changedPaths"])
        self.assertEqual({"A", "M"}, set(result["pathStatuses"].values()))

    def test_maintenance_base_must_descend_from_released_baseline(self):
        base, _ = self.maintenance_maps()
        with self.patch(
            {("rev-parse", "origin/main"): base},
            {(self.gate.RELEASE_MERGE, base): False},
        ), self.assertRaisesRegex(
            self.gate.GateError,
            "does not descend",
        ) as caught:
            self.gate.maintenance_topology("origin/main")
        self.assertEqual("MAINTENANCE_TOPOLOGY_FAILURE", caught.exception.classification)

    def test_maintenance_branch_must_be_synchronized_with_base(self):
        base, _ = self.maintenance_maps()
        with self.patch(
            {("rev-parse", "origin/main"): base},
            {
                (self.gate.RELEASE_MERGE, base): True,
                (base, "HEAD"): False,
            },
        ), self.assertRaisesRegex(
            self.gate.GateError,
            "not synchronized",
        ) as caught:
            self.gate.maintenance_topology("origin/main")
        self.assertEqual("MAINTENANCE_TOPOLOGY_FAILURE", caught.exception.classification)

    def test_maintenance_out_of_scope_path_fails_closed(self):
        bad = sorted(self.gate.CI_ALLOWLIST | {"apps/learnit-next/src/main.js"})
        base, mapping = self.maintenance_maps(changed=bad)
        with self.patch(
            mapping,
            {
                (self.gate.RELEASE_MERGE, base): True,
                (base, "HEAD"): True,
            },
        ), self.assertRaisesRegex(
            self.gate.GateError,
            "exact CI allowlist",
        ) as caught:
            self.gate.maintenance_topology("origin/main")
        self.assertEqual("MAINTENANCE_SCOPE_FAILURE", caught.exception.classification)

    def test_maintenance_new_file_fails_closed(self):
        changed = sorted(self.gate.CI_ALLOWLIST)
        statuses = [
            ("A" if index == 0 else "M") + "\t" + path
            for index, path in enumerate(changed)
        ]
        base, mapping = self.maintenance_maps(statuses=statuses)
        with self.patch(
            mapping,
            {
                (self.gate.RELEASE_MERGE, base): True,
                (base, "HEAD"): True,
            },
        ), self.assertRaisesRegex(
            self.gate.GateError,
            "two exact additions",
        ) as caught:
            self.gate.maintenance_topology("origin/main")
        self.assertEqual("MAINTENANCE_SCOPE_FAILURE", caught.exception.classification)

    def test_topology_and_product_failures_have_distinct_classifications(self):
        topology = self.gate.GateError("bad", "topology", "TOPOLOGY_FAILURE")
        product = self.gate.GateError("bad", "product", "PRODUCT_TEST_FAILURE")
        self.assertNotEqual(topology.classification, product.classification)
        self.assertNotEqual(topology.stage, product.stage)

    def test_unknown_and_missing_modes_are_not_valid(self):
        self.assertNotIn(None, self.gate.VALID_MODES)
        self.assertNotIn("automatic", self.gate.VALID_MODES)
        self.assertEqual(
            {"integration-head", "post-merge", "maintenance-pr"},
            self.gate.VALID_MODES,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
