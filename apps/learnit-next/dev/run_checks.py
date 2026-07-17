#!/usr/bin/env python3
"""Mode-aware CI-WP-001 provenance, build and product verification gate."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
MANIFEST = APP / "source_manifest.json"
REPORT = APP / ".agent-result/run_checks.json"
ART = Path("apps/learnit-next/dist/learnit-next.html")
SELF = "apps/learnit-next/source_manifest.json"
BASE = "b83fa032b262ce41a82f5a3664a7b854e8ab8296"
RELEASE_MERGE = "0604cad79a8ca765148c30090906b9f658af7109"
ACCEPTED_INTEGRATION_HEAD = "e5ee65a37326f4861d33c3c80221527511a03f24"
INPUTS = {
    "runtime": "7156749815fd727076786f9939aa4d7d78b8aa6d",
    "authoring": "2cff1f7575b509d47095df7130137cf78276e58f",
    "qa": "09da6c44741fd1421175f6d0feef0cab4b7761b1",
}
REVIEWS = {"runtime": 4713406180, "authoring": 4704571690, "qa": 4711673437}
INTEGRATOR = {
    ".github/workflows/learnit-next-ci.yml",
    "apps/learnit-next/build.py",
    "apps/learnit-next/dev/release.py",
    "apps/learnit-next/dev/run_checks.py",
    SELF,
}
CI_ALLOWLIST = {
    ".github/workflows/learnit-next-ci.yml",
    "apps/learnit-next/dev/run_checks.py",
    "apps/learnit-next/tests/build_determinism.py",
    SELF,
}
ROLE = {
    "runtime": {
        "apps/learnit-next/README.md",
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
    },
    "authoring": {
        "authoring/v2/README.md",
        "authoring/v2/generate_ids.py",
        "authoring/v2/validate_kit.py",
        "authoring/v2/golden/nombres_complexes.json",
        "authoring/v2/golden/signaux_electriques.json",
    },
    "qa": {
        "contracts/fixtures/v2-valid-minimal.json",
        "contracts/fixtures/v2-invalid-legacy.json",
        "contracts/fixtures/v2-invalid-digest-mismatch.json",
        "apps/learnit-next/tests/contract_v2.py",
        "apps/learnit-next/tests/storage_isolation.py",
        "apps/learnit-next/tests/browser_vertical_slice.py",
        "apps/learnit-next/tests/build_determinism.py",
    },
}
SCHEMA = "contracts/learnit-kit-v2.schema.json"
JS = [path for path in ROLE["runtime"] if path.endswith(".js")]
VALID_MODES = {"integration-head", "post-merge"}
BASELINE_PRODUCT_TEST_COUNT = 30


class GateError(RuntimeError):
    def __init__(self, message: str, stage: str, classification: str):
        super().__init__(message)
        self.stage = stage
        self.classification = classification


def fail(message: str, stage: str, classification: str) -> None:
    raise GateError(message, stage, classification)


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bh(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def run(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 1200,
) -> dict[str, Any]:
    process = subprocess.run(
        args,
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(env or {})},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {
        "command": args,
        "returnCode": process.returncode,
        "output": process.stdout,
        "outputSha256": h(process.stdout.encode()),
    }


def need(result: dict[str, Any], label: str, stage: str, classification: str) -> None:
    if result["returnCode"]:
        fail(
            f"{label} failed ({result['returnCode']}):\n{result['output']}",
            stage,
            classification,
        )


def git(*args: str) -> str:
    result = run(["git", *args], ROOT, timeout=120)
    need(result, "git " + " ".join(args), "topology", "TOPOLOGY_FAILURE")
    return result["output"].strip()


def gbytes(*args: str) -> bytes:
    process = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        fail(
            process.stderr.decode("utf-8", "replace"),
            "provenance",
            "PROVENANCE_FAILURE",
        )
    return process.stdout


def self_digest(manifest: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(manifest, ensure_ascii=False))
    hits = [item for item in clone["workingFiles"] if item["path"] == SELF]
    if len(hits) != 1:
        fail("manifest self path is not unique", "provenance", "PROVENANCE_FAILURE")
    hits[0]["fingerprint"]["value"] = None
    return h(
        json.dumps(
            clone,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )


def inventory() -> set[str]:
    output = {SCHEMA, *INTEGRATOR}
    for paths in ROLE.values():
        output |= paths
    return output


def validate_manifest(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if manifest.get("acceptedInputs") != INPUTS or manifest.get("acceptedReviews") != REVIEWS:
        fail("immutable inputs or reviews differ", "provenance", "PROVENANCE_FAILURE")
    if manifest.get("integrationOrder") != [
        "frozen-contract",
        "qa",
        "authoring",
        "runtime",
        "integrator",
    ]:
        fail("integration order differs", "provenance", "PROVENANCE_FAILURE")
    items = manifest.get("workingFiles", [])
    paths = [item.get("path") for item in items]
    if (
        manifest.get("fileBudget") != 32
        or len(items) != 32
        or len(set(paths)) != 32
        or set(paths) != inventory()
    ):
        fail("exact 32-file inventory differs", "provenance", "PROVENANCE_FAILURE")
    by_path = {item["path"]: item for item in items}
    self_item = by_path[SELF]
    if (
        self_item["fingerprint"]["kind"] != "canonical-self-sha256"
        or self_item["fingerprint"]["value"] != self_digest(manifest)
    ):
        fail("manifest self fingerprint is stale", "provenance", "PROVENANCE_FAILURE")
    return items, by_path


def integration_topology(base_ref: str) -> dict[str, Any]:
    if git("rev-parse", base_ref) != BASE:
        fail("frozen base moved", "topology", "TOPOLOGY_FAILURE")
    parents = git("show", "-s", "--format=%P", "HEAD").split()
    expected = [BASE, INPUTS["qa"], INPUTS["authoring"], INPUTS["runtime"]]
    if parents != expected:
        fail(f"parent order differs: {parents}", "topology", "TOPOLOGY_FAILURE")
    if git("merge-base", base_ref, "HEAD") != BASE:
        fail("base is not first-parent merge base", "topology", "TOPOLOGY_FAILURE")
    changed = [
        path
        for path in git("diff", "--name-only", f"{base_ref}...HEAD").splitlines()
        if path
    ]
    if len(changed) != 5 or set(changed) != INTEGRATOR:
        fail(
            f"integrator diff differs: {changed}",
            "provenance",
            "PROVENANCE_FAILURE",
        )
    return {"parents": parents, "changedPaths": sorted(changed), "changedPathCount": 5}


def post_merge_topology(expected_integration_head: str) -> dict[str, Any]:
    if not expected_integration_head:
        fail(
            "post-merge mode requires --accepted-integration-head",
            "configuration",
            "CONFIGURATION_FAILURE",
        )
    parents = git("show", "-s", "--format=%P", "HEAD").split()
    if len(parents) != 2:
        fail(
            f"post-merge commit must have exactly two parents: {parents}",
            "topology",
            "TOPOLOGY_FAILURE",
        )
    if parents[1] != expected_integration_head:
        fail(
            f"wrong accepted integration head: expected={expected_integration_head} actual={parents[1]}",
            "provenance",
            "PROVENANCE_FAILURE",
        )
    if git("merge-base", "--is-ancestor", BASE, parents[0]) != "":
        pass
    divergence = [
        path
        for path in git(
            "diff",
            "--name-only",
            expected_integration_head,
            "HEAD",
            "--",
            "apps/learnit-next/index.template.html",
            "apps/learnit-next/src",
            "apps/learnit-next/build.py",
            SCHEMA,
        ).splitlines()
        if path
    ]
    if divergence:
        fail(
            f"executable tree divergence from accepted integration head: {divergence}",
            "provenance",
            "EXECUTABLE_TREE_DIVERGENCE",
        )
    return {
        "parents": parents,
        "acceptedIntegrationHead": expected_integration_head,
        "firstParent": parents[0],
        "executableTreeDivergence": [],
    }


def provenance(
    manifest: dict[str, Any],
    mode: str,
    base_ref: str,
    expected_integration_head: str,
) -> dict[str, Any]:
    items, by_path = validate_manifest(manifest)
    topology = (
        integration_topology(base_ref)
        if mode == "integration-head"
        else post_merge_topology(expected_integration_head)
    )
    if git("status", "--porcelain"):
        fail("repository dirty before checks", "provenance", "PROVENANCE_FAILURE")
    schema_blob = git("rev-parse", f"{BASE}:{SCHEMA}")
    if by_path[SCHEMA]["fingerprint"]["value"] != schema_blob:
        fail("frozen schema differs", "provenance", "PROVENANCE_FAILURE")
    proof: dict[str, Any] = {}
    for owner, owned in ROLE.items():
        actual = {item["path"] for item in items if item.get("owner") == owner}
        if actual != owned:
            fail(f"{owner} inventory differs", "provenance", "PROVENANCE_FAILURE")
        files: dict[str, Any] = {}
        for path in sorted(owned):
            declared = by_path[path]["fingerprint"]["value"]
            accepted = git("rev-parse", f"{INPUTS[owner]}:{path}")
            accepted_data = gbytes("cat-file", "blob", accepted)
            if bh(accepted_data) != accepted:
                fail(
                    f"{owner} accepted blob cannot be reproduced: {path}",
                    "provenance",
                    "PROVENANCE_FAILURE",
                )
            if path == "apps/learnit-next/tests/build_determinism.py":
                current = git("rev-parse", f"HEAD:{path}")
                if declared != current:
                    fail(
                        f"CI-WP-001 test fingerprint stale: {path}",
                        "provenance",
                        "PROVENANCE_FAILURE",
                    )
                files[path] = {
                    "acceptedBaselineBlobSha1": accepted,
                    "materializedBlobSha1": current,
                    "identicalToAcceptedBaseline": current == accepted,
                    "authorizedOverride": "CI-WP-001",
                }
            else:
                if declared != accepted:
                    fail(
                        f"{owner} blob differs: {path}",
                        "provenance",
                        "PROVENANCE_FAILURE",
                    )
                files[path] = {
                    "acceptedBlobSha1": accepted,
                    "materializedBlobSha1": accepted,
                    "identical": True,
                }
        proof[owner] = {
            "commit": INPUTS[owner],
            "reviewId": REVIEWS[owner],
            "files": files,
        }
    if {item["path"] for item in items if item.get("owner") == "integrator"} != INTEGRATOR:
        fail("integrator inventory differs", "provenance", "PROVENANCE_FAILURE")
    for path in INTEGRATOR - {SELF}:
        if by_path[path]["fingerprint"]["value"] != git("rev-parse", f"HEAD:{path}"):
            fail(
                f"integrator fingerprint stale: {path}",
                "provenance",
                "PROVENANCE_FAILURE",
            )
    return {
        "mode": mode,
        "baseCommit": BASE,
        "sourceCommit": git("rev-parse", "HEAD"),
        **topology,
        "manifestBudget": 32,
        "roleFileCount": 26,
        "roleFiles": proof,
        "schema": {
            "path": SCHEMA,
            "acceptedBlobSha1": schema_blob,
            "materializedBlobSha1": schema_blob,
            "identical": True,
        },
    }


def materialize(dst: Path, manifest: dict[str, Any]) -> Path:
    root = dst / "repo"

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {".git", "__pycache__", ".pytest_cache"} & set(names)
        if Path(directory).name == "learnit-next":
            ignored |= {
                "dist",
                "release",
                ".agent-runtime",
                ".agent-result",
            } & set(names)
        return ignored

    shutil.copytree(ROOT, root, ignore=ignore)
    for item in manifest["workingFiles"]:
        if item.get("owner") in ROLE or item["path"] == SCHEMA:
            data = gbytes("cat-file", "blob", item["fingerprint"]["value"])
            target = root / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    for item in manifest["workingFiles"]:
        path = root / item["path"]
        if not path.is_file():
            fail(
                f"materialized file missing: {item['path']}",
                "build",
                "BUILD_FAILURE",
            )
        if item["path"] != SELF and bh(path.read_bytes()) != item["fingerprint"]["value"]:
            fail(
                f"materialized fingerprint differs: {item['path']}",
                "build",
                "BUILD_FAILURE",
            )
    return root


def build(root: Path) -> dict[str, Any]:
    result = run([sys.executable, "apps/learnit-next/build.py"], root, timeout=300)
    need(result, "build", "build", "BUILD_FAILURE")
    data = (root / ART).read_bytes()
    return {"sha256": h(data), "bytes": len(data), "data": data, "command": result}


def parse_unittest_count(output: str, label: str) -> int:
    match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    if not match:
        fail(
            f"{label} did not report an executed test count:\n{output}",
            "product",
            "PRODUCT_TEST_FAILURE",
        )
    return int(match.group(1))


def checks(report: dict[str, Any], manifest: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory() as raw:
        first = materialize(Path(raw) / "a", manifest)
        second = materialize(Path(raw) / "b", manifest)
        build_a = build(first)
        build_b = build(second)
        if build_a["data"] != build_b["data"]:
            fail("clean builds differ byte-for-byte", "build", "BUILD_FAILURE")
        if build_a["sha256"] != manifest["artifact"]["sha256"]:
            fail("manifest artifact digest differs", "build", "BUILD_FAILURE")
        if build_a["bytes"] != 84060:
            fail(
                f"released artifact size differs: {build_a['bytes']}",
                "build",
                "BUILD_FAILURE",
            )
        report["cleanBuilds"] = {
            "builds": [
                {
                    "name": "clean-1",
                    **{key: value for key, value in build_a.items() if key != "data"},
                },
                {
                    "name": "clean-2",
                    **{key: value for key, value in build_b.items() if key != "data"},
                },
            ],
            "byteForByteIdentical": True,
        }
        output = ROOT / ART
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(build_a["data"])
        tested = h(output.read_bytes())
        usages = {
            key: build_a["sha256"]
            for key in [
                "cleanBuild1",
                "cleanBuild2",
                "manifest",
                "releaseEnvelope",
                "contradictoryQaProposal",
                "governorReviewProposal",
            ]
        }
        usages["browserTests"] = tested
        if len(set(usages.values())) != 1:
            fail("artifact identity chain differs", "build", "BUILD_FAILURE")
        report["artifact"] = {
            "path": ART.as_posix(),
            "sha256": build_a["sha256"],
            "bytes": build_a["bytes"],
            "usages": usages,
        }
        python_paths = [
            "apps/learnit-next/build.py",
            "apps/learnit-next/dev/run_checks.py",
            "apps/learnit-next/dev/release.py",
            "authoring/v2/generate_ids.py",
            "authoring/v2/validate_kit.py",
            "apps/learnit-next/tests/contract_v2.py",
            "apps/learnit-next/tests/storage_isolation.py",
            "apps/learnit-next/tests/browser_vertical_slice.py",
            "apps/learnit-next/tests/build_determinism.py",
        ]
        compilation = run(
            [sys.executable, "-m", "py_compile", *python_paths],
            first,
            timeout=180,
        )
        need(
            compilation,
            "Python compilation",
            "product",
            "PRODUCT_TEST_FAILURE",
        )
        report["compilation"] = compilation
        node_results = []
        for path in sorted(JS):
            result = run(["node", "--check", path], first, timeout=120)
            need(
                result,
                f"Node syntax {path}",
                "product",
                "PRODUCT_TEST_FAILURE",
            )
            node_results.append(result)
        report["nodeSyntax"] = {
            "count": len(node_results),
            "paths": sorted(JS),
            "results": node_results,
        }
        json_paths = [
            SCHEMA,
            "docs/architecture/clean-generation/FILE_PLAN_V1.json",
            SELF,
            "contracts/fixtures/v2-valid-minimal.json",
            "contracts/fixtures/v2-invalid-legacy.json",
            "contracts/fixtures/v2-invalid-digest-mismatch.json",
            "authoring/v2/golden/nombres_complexes.json",
            "authoring/v2/golden/signaux_electriques.json",
        ]
        for path in json_paths:
            json.loads((first / path).read_text(encoding="utf-8"))
        report["jsonParsing"] = {"count": len(json_paths), "paths": json_paths}
        golden = run(
            [
                sys.executable,
                "authoring/v2/validate_kit.py",
                "--schema",
                SCHEMA,
                "--foundation-profile",
                "authoring/v2/golden/nombres_complexes.json",
                "authoring/v2/golden/signaux_electriques.json",
            ],
            first,
            timeout=300,
        )
        need(golden, "golden kits", "product", "PRODUCT_TEST_FAILURE")
        report["goldenKits"] = golden
        test_env = {
            "LEARNIT_NEXT_STRICT_INTEGRATION": "1",
            "LEARNIT_NEXT_ARTIFACT": str(first / ART),
        }
        qa = run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "apps/learnit-next/tests",
                "-p",
                "*.py",
                "-v",
            ],
            first,
            test_env,
            1200,
        )
        need(qa, "strict QA", "product", "PRODUCT_TEST_FAILURE")
        total = parse_unittest_count(qa["output"], "strict QA")
        if total < BASELINE_PRODUCT_TEST_COUNT or re.search(
            r"skipped=|FAILED|ERROR",
            qa["output"],
        ):
            fail(
                "QA did not preserve the baseline 30 tests with zero skip/failure/error:\n"
                + qa["output"],
                "product",
                "PRODUCT_TEST_FAILURE",
            )
        regression_count = total - BASELINE_PRODUCT_TEST_COUNT
        if regression_count <= 0:
            fail(
                "no new topology regression tests were counted",
                "product",
                "PRODUCT_TEST_FAILURE",
            )
        report["qa"] = {
            **qa,
            "executed": total,
            "passed": total,
            "baselineProductTests": BASELINE_PRODUCT_TEST_COUNT,
            "newTopologyRegressionTests": regression_count,
            "skipped": 0,
            "failures": 0,
            "errors": 0,
        }
        node_version = run(["node", "--version"], ROOT, timeout=60)
        need(
            node_version,
            "Node version",
            "product",
            "PRODUCT_TEST_FAILURE",
        )
        chromium = run(
            [
                sys.executable,
                "-c",
                (
                    "from playwright.sync_api import sync_playwright;"
                    "p=sync_playwright().start();"
                    "b=p.chromium.launch(headless=True);"
                    "print(b.version);b.close();p.stop()"
                ),
            ],
            ROOT,
            timeout=180,
        )
        need(
            chromium,
            "Chromium version",
            "product",
            "PRODUCT_TEST_FAILURE",
        )
        report["environment"] = {
            "python": platform.python_version(),
            "jsonschema": importlib.metadata.version("jsonschema"),
            "playwright": importlib.metadata.version("playwright"),
            "node": node_version["output"].strip(),
            "chromium": chromium["output"].strip(),
        }
        report["stages"]["build"] = {"result": "PASS", "classification": "BUILD_PASS"}
        report["stages"]["product"] = {
            "result": "PASS",
            "classification": "PRODUCT_TEST_PASS",
        }
        report["result"] = "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--mode")
    parser.add_argument("--base-ref", default=os.environ.get("LEARNIT_NEXT_BASE_REF", "origin/main"))
    parser.add_argument(
        "--accepted-integration-head",
        default=os.environ.get("LEARNIT_NEXT_ACCEPTED_INTEGRATION_HEAD", ""),
    )
    args = parser.parse_args()
    target = args.report if args.report.is_absolute() else ROOT / args.report
    strict = bool(args.strict or os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION") == "1")
    report: dict[str, Any] = {
        "schema": "learnit.next.ci.checks.v2",
        "workPackage": "CI-WP-001",
        "mode": args.mode,
        "strict": strict,
        "result": "FAIL",
        "stages": {
            "configuration": {"result": "PENDING"},
            "topology": {"result": "PENDING"},
            "provenance": {"result": "PENDING"},
            "build": {"result": "PENDING"},
            "product": {"result": "PENDING"},
        },
    }
    try:
        if not strict:
            fail(
                "strict mode is mandatory",
                "configuration",
                "CONFIGURATION_FAILURE",
            )
        if args.mode not in VALID_MODES:
            fail(
                f"unknown or missing verification mode: {args.mode!r}",
                "configuration",
                "CONFIGURATION_FAILURE",
            )
        report["stages"]["configuration"] = {
            "result": "PASS",
            "classification": "CONFIGURATION_PASS",
        }
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        report["provenance"] = provenance(
            manifest,
            args.mode,
            args.base_ref,
            args.accepted_integration_head,
        )
        report["stages"]["topology"] = {
            "result": "PASS",
            "classification": "TOPOLOGY_PASS",
        }
        report["stages"]["provenance"] = {
            "result": "PASS",
            "classification": "PROVENANCE_PASS",
        }
        checks(report, manifest)
    except GateError as exc:
        report["error"] = {
            "message": str(exc),
            "stage": exc.stage,
            "classification": exc.classification,
        }
        if exc.stage in report["stages"]:
            report["stages"][exc.stage] = {
                "result": "FAIL",
                "classification": exc.classification,
            }
    except Exception as exc:
        report["error"] = {
            "message": str(exc),
            "stage": "internal",
            "classification": "INTERNAL_HARNESS_FAILURE",
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": report["result"],
                "report": target.relative_to(ROOT).as_posix(),
                "mode": args.mode,
                "classification": report.get("error", {}).get("classification"),
                "artifactSha256": report.get("artifact", {}).get("sha256"),
            },
            sort_keys=True,
        )
    )
    if report["result"] != "PASS":
        print(
            report.get("error", {}).get("message", "unknown failure"),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
