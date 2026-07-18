#!/usr/bin/env python3
"""Strict mode-aware CI gate for the released Learn-it Next artifact."""
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

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
MANIFEST = APP / "source_manifest.json"
REPORT = APP / ".agent-result/run_checks.json"
ARTIFACT = Path("apps/learnit-next/dist/learnit-next.html")
SELF = "apps/learnit-next/source_manifest.json"
SCHEMA = "contracts/learnit-kit-v2.schema.json"
BASE = "b83fa032b262ce41a82f5a3664a7b854e8ab8296"
RELEASE_MERGE = "0604cad79a8ca765148c30090906b9f658af7109"
ACCEPTED_HEAD = "e5ee65a37326f4861d33c3c80221527511a03f24"
EXPECTED_BYTES = 84060
BASELINE_TESTS = 30
VALID_MODES = {"integration-head", "post-merge", "maintenance-pr"}
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
MAINTENANCE_STATUS_PROFILES = [
    {path: "M" for path in CI_ALLOWLIST},
    {
        path: ("A" if path == "apps/learnit-next/tests/build_determinism.py" else "M")
        for path in CI_ALLOWLIST
    },
]
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


class GateError(RuntimeError):
    def __init__(self, message: str, stage: str, classification: str):
        super().__init__(message)
        self.stage = stage
        self.classification = classification


def fail(message: str, stage: str, classification: str) -> None:
    raise GateError(message, stage, classification)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_digest(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def run(
    command: list[str],
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    timeout: int = 1200,
):
    process = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(env or {})},
    )
    return {
        "command": command,
        "returnCode": process.returncode,
        "output": process.stdout,
        "outputSha256": digest(process.stdout.encode()),
    }


def need(result, label: str, stage: str, classification: str) -> None:
    if result["returnCode"]:
        fail(
            f"{label} failed ({result['returnCode']}):\n{result['output']}",
            stage,
            classification,
        )


def git(*args: str) -> str:
    result = run(["git", *args], timeout=120)
    need(result, "git " + " ".join(args), "topology", "TOPOLOGY_FAILURE")
    return result["output"].strip()


def ancestor(older: str, newer: str) -> bool:
    result = run(["git", "merge-base", "--is-ancestor", older, newer], timeout=120)
    if result["returnCode"] in (0, 1):
        return result["returnCode"] == 0
    fail(result["output"], "topology", "TOPOLOGY_FAILURE")


def git_bytes(*args: str) -> bytes:
    process = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode:
        fail(
            process.stderr.decode("utf-8", "replace"),
            "provenance",
            "PROVENANCE_FAILURE",
        )
    return process.stdout


def canonical_self_digest(manifest: dict) -> str:
    clone = json.loads(json.dumps(manifest, ensure_ascii=False))
    hits = [item for item in clone["workingFiles"] if item["path"] == SELF]
    if len(hits) != 1:
        fail("manifest self path is not unique", "provenance", "PROVENANCE_FAILURE")
    hits[0]["fingerprint"]["value"] = None
    encoded = json.dumps(
        clone,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return digest(encoded)


def inventory() -> set[str]:
    paths = {SCHEMA, *INTEGRATOR}
    for owned in ROLE.values():
        paths |= owned
    return paths


def validate_manifest(manifest: dict):
    if (
        manifest.get("acceptedInputs") != INPUTS
        or manifest.get("acceptedReviews") != REVIEWS
    ):
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
        or self_item["fingerprint"]["value"] != canonical_self_digest(manifest)
    ):
        fail("manifest self fingerprint is stale", "provenance", "PROVENANCE_FAILURE")
    return items, by_path


def integration_topology(base_ref: str):
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
    return {
        "parents": parents,
        "changedPaths": sorted(changed),
        "changedPathCount": 5,
    }


def post_merge_topology(expected_head: str):
    if not expected_head:
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
    if parents[1] != expected_head:
        fail(
            f"wrong accepted integration head: expected={expected_head} actual={parents[1]}",
            "provenance",
            "PROVENANCE_FAILURE",
        )
    if not ancestor(BASE, parents[0]):
        fail(
            f"post-merge first parent does not descend from frozen base: {parents[0]}",
            "topology",
            "TOPOLOGY_FAILURE",
        )
    protected = [
        "apps/learnit-next/index.template.html",
        "apps/learnit-next/src",
        "apps/learnit-next/build.py",
        SCHEMA,
    ]
    divergence = [
        path
        for path in git(
            "diff",
            "--name-only",
            expected_head,
            "HEAD",
            "--",
            *protected,
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
        "acceptedIntegrationHead": expected_head,
        "firstParent": parents[0],
        "executableTreeDivergence": [],
    }


def maintenance_topology(base_ref: str):
    base = git("rev-parse", base_ref)
    if not ancestor(RELEASE_MERGE, base):
        fail(
            f"maintenance base does not descend from released baseline: {base}",
            "topology",
            "MAINTENANCE_TOPOLOGY_FAILURE",
        )
    if (
        not ancestor(base, "HEAD")
        or git("merge-base", base_ref, "HEAD") != base
    ):
        fail(
            f"maintenance branch is not synchronized with reviewed base: {base}",
            "topology",
            "MAINTENANCE_TOPOLOGY_FAILURE",
        )
    changed = [
        path
        for path in git("diff", "--name-only", f"{base_ref}...HEAD").splitlines()
        if path
    ]
    if len(changed) != 4 or set(changed) != CI_ALLOWLIST:
        fail(
            f"maintenance diff differs from exact CI allowlist: {changed}",
            "provenance",
            "MAINTENANCE_SCOPE_FAILURE",
        )
    statuses: dict[str, str] = {}
    for line in filter(
        None,
        git("diff", "--name-status", f"{base_ref}...HEAD").splitlines(),
    ):
        parts = line.split("\t")
        if len(parts) != 2:
            fail(
                f"unsupported maintenance diff status line: {line}",
                "provenance",
                "MAINTENANCE_SCOPE_FAILURE",
            )
        statuses[parts[1]] = parts[0]
    if statuses not in MAINTENANCE_STATUS_PROFILES:
        fail(
            "maintenance path statuses differ from authorized profiles: "
            f"expected={MAINTENANCE_STATUS_PROFILES} actual={statuses}",
            "provenance",
            "MAINTENANCE_SCOPE_FAILURE",
        )
    return {
        "maintenanceBaseRef": base_ref,
        "maintenanceBaseCommit": base,
        "releasedBaseline": RELEASE_MERGE,
        "changedPaths": sorted(changed),
        "changedPathCount": 4,
        "pathStatuses": dict(sorted(statuses.items())),
    }


def provenance(
    manifest: dict,
    mode: str,
    base_ref: str,
    expected_head: str,
):
    items, by_path = validate_manifest(manifest)
    if mode == "integration-head":
        topology = integration_topology(base_ref)
    elif mode == "post-merge":
        topology = post_merge_topology(expected_head)
    else:
        topology = maintenance_topology(base_ref)
    if git("status", "--porcelain"):
        fail("repository dirty before checks", "provenance", "PROVENANCE_FAILURE")
    schema_blob = git("rev-parse", f"{BASE}:{SCHEMA}")
    if by_path[SCHEMA]["fingerprint"]["value"] != schema_blob:
        fail("frozen schema differs", "provenance", "PROVENANCE_FAILURE")
    proof = {}
    for owner, owned in ROLE.items():
        if {
            item["path"]
            for item in items
            if item.get("owner") == owner
        } != owned:
            fail(
                f"{owner} inventory differs",
                "provenance",
                "PROVENANCE_FAILURE",
            )
        files = {}
        for path in sorted(owned):
            declared = by_path[path]["fingerprint"]["value"]
            accepted = git("rev-parse", f"{INPUTS[owner]}:{path}")
            if blob_digest(git_bytes("cat-file", "blob", accepted)) != accepted:
                fail(
                    f"accepted blob cannot be reproduced: {path}",
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
    if {
        item["path"]
        for item in items
        if item.get("owner") == "integrator"
    } != INTEGRATOR:
        fail("integrator inventory differs", "provenance", "PROVENANCE_FAILURE")
    for path in INTEGRATOR - {SELF}:
        if by_path[path]["fingerprint"]["value"] != git(
            "rev-parse",
            f"HEAD:{path}",
        ):
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


def materialize(destination: Path, manifest: dict) -> Path:
    root = destination / "repo"

    def ignore(directory: str, names: list[str]):
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
            target = root / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                git_bytes(
                    "cat-file",
                    "blob",
                    item["fingerprint"]["value"],
                )
            )
    return root


def build(root: Path):
    result = run(
        [sys.executable, "apps/learnit-next/build.py"],
        root,
        timeout=300,
    )
    need(result, "build", "build", "BUILD_FAILURE")
    data = (root / ARTIFACT).read_bytes()
    return {
        "sha256": digest(data),
        "bytes": len(data),
        "data": data,
        "command": result,
    }


def test_count(output: str) -> int:
    match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    if not match:
        fail(
            f"strict QA did not report a test count:\n{output}",
            "product",
            "PRODUCT_TEST_FAILURE",
        )
    return int(match.group(1))


def checks(report: dict, manifest: dict) -> None:
    with tempfile.TemporaryDirectory() as raw:
        first = materialize(Path(raw) / "first", manifest)
        second = materialize(Path(raw) / "second", manifest)
        build_a = build(first)
        build_b = build(second)
        if build_a["data"] != build_b["data"]:
            fail(
                "clean builds differ byte-for-byte",
                "build",
                "BUILD_FAILURE",
            )
        if (
            build_a["sha256"] != manifest["artifact"]["sha256"]
            or build_a["bytes"] != EXPECTED_BYTES
        ):
            fail(
                "released artifact identity differs",
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
        output = ROOT / ARTIFACT
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(build_a["data"])
        report["artifact"] = {
            "path": ARTIFACT.as_posix(),
            "sha256": build_a["sha256"],
            "bytes": build_a["bytes"],
        }
        env = {
            "LEARNIT_NEXT_STRICT_INTEGRATION": "1",
            "LEARNIT_NEXT_ARTIFACT": str(first / ARTIFACT),
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
            env,
            1200,
        )
        need(qa, "strict QA", "product", "PRODUCT_TEST_FAILURE")
        total = test_count(qa["output"])
        if total < BASELINE_TESTS or re.search(
            r"skipped=|FAILED(?:\s|\()|errors?=",
            qa["output"],
            re.I,
        ):
            fail(
                "QA did not preserve the baseline tests with zero skip/failure/error:\n"
                + qa["output"],
                "product",
                "PRODUCT_TEST_FAILURE",
            )
        added = total - BASELINE_TESTS
        if added <= 0:
            fail(
                "no topology regression tests were counted",
                "product",
                "PRODUCT_TEST_FAILURE",
            )
        report["qa"] = {
            **qa,
            "executed": total,
            "passed": total,
            "baselineProductTests": BASELINE_TESTS,
            "newTopologyRegressionTests": added,
            "skipped": 0,
            "failures": 0,
            "errors": 0,
        }
        report["environment"] = {
            "python": platform.python_version(),
            "jsonschema": importlib.metadata.version("jsonschema"),
            "playwright": importlib.metadata.version("playwright"),
        }
        report["stages"]["build"] = {
            "result": "PASS",
            "classification": "BUILD_PASS",
        }
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
    parser.add_argument(
        "--base-ref",
        default=os.environ.get("LEARNIT_NEXT_BASE_REF", "origin/main"),
    )
    parser.add_argument(
        "--accepted-integration-head",
        default=os.environ.get("LEARNIT_NEXT_ACCEPTED_INTEGRATION_HEAD", ""),
    )
    args = parser.parse_args()
    target = args.report if args.report.is_absolute() else ROOT / args.report
    strict = bool(
        args.strict
        or os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION") == "1"
    )
    report = {
        "schema": "learnit.next.ci.checks.v3",
        "workPackage": "CI-WP-001",
        "mode": args.mode,
        "strict": strict,
        "result": "FAIL",
        "stages": {
            name: {"result": "PENDING"}
            for name in (
                "configuration",
                "topology",
                "provenance",
                "build",
                "product",
            )
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
    except GateError as error:
        report["error"] = {
            "message": str(error),
            "stage": error.stage,
            "classification": error.classification,
        }
        if error.stage in report["stages"]:
            report["stages"][error.stage] = {
                "result": "FAIL",
                "classification": error.classification,
            }
    except Exception as error:
        report["error"] = {
            "message": str(error),
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
