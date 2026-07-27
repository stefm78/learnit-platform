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
FROZEN_BASE = "b83fa032b262ce41a82f5a3664a7b854e8ab8296"
PRODUCT_BASELINE = "41a4268e6c9baf900f892bd6bd9cc54e6c7ec5f9"
RELEASE_MERGE = "0604cad79a8ca765148c30090906b9f658af7109"
ACCEPTED_HEAD = "e5ee65a37326f4861d33c3c80221527511a03f24"
ACCEPTED_INTEGRATION_HEAD = ACCEPTED_HEAD
BASELINE_TESTS = 30
VALID_MODES = {"integration-head", "post-merge", "maintenance-pr"}
EXPECTED_INPUTS = {
    "runtime": "c5aa1e7c158db33f1e2a56e48c391a7bff21baf4",
    "authoring": "2cff1f7575b509d47095df7130137cf78276e58f",
    "qa": "67c92e6d3fde49f1a83b9e6a7321403d80d80269",
}
EXPECTED_REVIEWS = {"runtime": 5087421021, "authoring": 4704571690, "qa": 5087471471}
P1_TEST = "apps/learnit-next/tests/p1_corrective_review.py"
P1_PRODUCT_PATHS = {
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/core/session.js",
    "apps/learnit-next/src/main.js",
    "apps/learnit-next/src/ui/render.js",
}
WORK_PACKAGE = "work-packages/PROD-WP-003.json"
INTEGRATOR = {
    ".github/workflows/learnit-next-ci.yml",
    "apps/learnit-next/build.py",
    "apps/learnit-next/dev/release.py",
    "apps/learnit-next/dev/run_checks.py",
    SELF,
}
INTEGRATION_ALLOWLIST = {
    *P1_PRODUCT_PATHS,
    WORK_PACKAGE,
    P1_TEST,
    SELF,
    "apps/learnit-next/dev/run_checks.py",
}
CI_ALLOWLIST = {
    "work-packages/CI-WP-002.json",
    "work-packages/OPS-WP-003.json",
    ".github/workflows/learnit-next-ci.yml",
    "apps/learnit-next/dev/run_checks.py",
    "apps/learnit-next/tests/build_determinism.py",
    SELF,
}
MAINTENANCE_STATUS_PROFILES = [
    {path: ("A" if path in {"work-packages/CI-WP-002.json", "apps/learnit-next/tests/build_determinism.py"} else "M") for path in CI_ALLOWLIST},
]
ROLE = {
    "runtime": {
        "apps/learnit-next/README.md", "apps/learnit-next/index.template.html",
        "apps/learnit-next/src/styles.css", "apps/learnit-next/src/main.js",
        "apps/learnit-next/src/core/canonical_json.js", "apps/learnit-next/src/core/identity.js",
        "apps/learnit-next/src/core/contract.js", "apps/learnit-next/src/core/import.js",
        "apps/learnit-next/src/core/library.js", "apps/learnit-next/src/core/session.js",
        "apps/learnit-next/src/core/progress.js", "apps/learnit-next/src/ports/storage.js",
        "apps/learnit-next/src/adapters/indexeddb.js", "apps/learnit-next/src/ui/render.js",
    },
    "authoring": {
        "authoring/v2/README.md", "authoring/v2/generate_ids.py",
        "authoring/v2/validate_kit.py", "authoring/v2/golden/nombres_complexes.json",
        "authoring/v2/golden/signaux_electriques.json",
    },
    "qa": {
        "contracts/fixtures/v2-valid-minimal.json", "contracts/fixtures/v2-invalid-legacy.json",
        "contracts/fixtures/v2-invalid-digest-mismatch.json",
        "apps/learnit-next/tests/contract_v2.py", "apps/learnit-next/tests/storage_isolation.py",
        "apps/learnit-next/tests/browser_vertical_slice.py",
        "apps/learnit-next/tests/build_determinism.py", P1_TEST,
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


def run(command: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None, timeout: int = 1200):
    process = subprocess.run(
        command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=timeout, check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(env or {})},
    )
    return {
        "command": command, "returnCode": process.returncode, "output": process.stdout,
        "outputSha256": digest(process.stdout.encode()),
    }


def need(result, label: str, stage: str, classification: str) -> None:
    if result["returnCode"]:
        fail(f"{label} failed ({result['returnCode']}):\n{result['output']}", stage, classification)


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
    process = subprocess.run(["git", *args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode:
        fail(process.stderr.decode("utf-8", "replace"), "provenance", "PROVENANCE_FAILURE")
    return process.stdout


def canonical_self_digest(manifest: dict) -> str:
    clone = json.loads(json.dumps(manifest, ensure_ascii=False))
    hits = [item for item in clone["workingFiles"] if item["path"] == SELF]
    if len(hits) != 1:
        fail("manifest self path is not unique", "provenance", "PROVENANCE_FAILURE")
    hits[0]["fingerprint"]["value"] = None
    encoded = json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return digest(encoded)


def inventory() -> set[str]:
    paths = {SCHEMA, *INTEGRATOR}
    for owned in ROLE.values():
        paths |= owned
    return paths


def validate_manifest(manifest: dict):
    inputs = manifest.get("acceptedInputs")
    if inputs != EXPECTED_INPUTS:
        fail(f"accepted inputs differ: {inputs}", "provenance", "PROVENANCE_FAILURE")
    if manifest.get("acceptedReviews") != EXPECTED_REVIEWS:
        fail("accepted reviews differ", "provenance", "PROVENANCE_FAILURE")
    if manifest.get("integrationOrder") != ["frozen-contract", "qa", "authoring", "runtime", "integrator"]:
        fail("integration order differs", "provenance", "PROVENANCE_FAILURE")
    items = manifest.get("workingFiles", [])
    paths = [item.get("path") for item in items]
    if manifest.get("fileBudget") != 33 or len(items) != 33 or len(set(paths)) != 33 or set(paths) != inventory():
        fail("exact 33-file inventory differs", "provenance", "PROVENANCE_FAILURE")
    artifact = manifest.get("artifact", {})
    if artifact.get("path") != ARTIFACT.as_posix():
        fail("artifact path differs", "provenance", "PROVENANCE_FAILURE")
    if not re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))):
        fail("artifact SHA-256 is invalid", "provenance", "PROVENANCE_FAILURE")
    if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0:
        fail("artifact byte size is invalid", "provenance", "PROVENANCE_FAILURE")
    by_path = {item["path"]: item for item in items}
    self_item = by_path[SELF]
    if self_item["fingerprint"]["kind"] != "canonical-self-sha256" or self_item["fingerprint"]["value"] != canonical_self_digest(manifest):
        fail("manifest self fingerprint is stale", "provenance", "PROVENANCE_FAILURE")
    return items, by_path, inputs


def integration_topology(base_ref: str):
    base = git("rev-parse", base_ref)
    if not ancestor(base, "HEAD"):
        fail(f"base is not an ancestor of HEAD: {base}", "topology", "TOPOLOGY_FAILURE")
    if git("merge-base", base_ref, "HEAD") != base:
        fail(f"merge-base differs from resolved base: {base}", "topology", "TOPOLOGY_FAILURE")
    changed = [path for path in git("diff", "--name-only", f"{base_ref}...HEAD").splitlines() if path]
    if len(changed) != 8 or set(changed) != INTEGRATION_ALLOWLIST:
        fail(f"integration diff differs: {changed}", "provenance", "PROVENANCE_FAILURE")
    return {"integrationBaseRef": base_ref, "baseCommit": base, "changedPaths": sorted(changed), "changedPathCount": 8}


def post_merge_topology(expected_head: str):
    if not expected_head:
        fail("post-merge mode requires --accepted-integration-head", "configuration", "CONFIGURATION_FAILURE")
    parents = git("show", "-s", "--format=%P", "HEAD").split()
    if len(parents) != 2:
        fail(f"post-merge commit must have exactly two parents: {parents}", "topology", "TOPOLOGY_FAILURE")
    if parents[1] != expected_head:
        fail(f"wrong accepted integration head: expected={expected_head} actual={parents[1]}", "provenance", "PROVENANCE_FAILURE")
    if not ancestor(FROZEN_BASE, parents[0]):
        fail(f"post-merge first parent does not descend from frozen base: {parents[0]}", "topology", "TOPOLOGY_FAILURE")
    protected = ["apps/learnit-next/index.template.html", "apps/learnit-next/src", "apps/learnit-next/build.py", SCHEMA]
    divergence = [path for path in git("diff", "--name-only", expected_head, "HEAD", "--", *protected).splitlines() if path]
    if divergence:
        fail(f"executable tree divergence from accepted integration head: {divergence}", "provenance", "EXECUTABLE_TREE_DIVERGENCE")
    return {"parents": parents, "acceptedIntegrationHead": expected_head, "baseCommit": parents[0], "firstParent": parents[0], "executableTreeDivergence": []}


def maintenance_topology(base_ref: str):
    base = git("rev-parse", base_ref)
    if not ancestor(RELEASE_MERGE, base):
        fail(f"maintenance base does not descend from released baseline: {base}", "topology", "MAINTENANCE_TOPOLOGY_FAILURE")
    if not ancestor(base, "HEAD") or git("merge-base", base_ref, "HEAD") != base:
        fail(f"maintenance branch is not synchronized with reviewed base: {base}", "topology", "MAINTENANCE_TOPOLOGY_FAILURE")
    changed = [path for path in git("diff", "--name-only", f"{base_ref}...HEAD").splitlines() if path]
    if len(changed) != 6 or set(changed) != CI_ALLOWLIST:
        fail(f"maintenance diff differs from exact CI allowlist: {changed}", "provenance", "MAINTENANCE_SCOPE_FAILURE")
    statuses: dict[str, str] = {}
    for line in filter(None, git("diff", "--name-status", f"{base_ref}...HEAD").splitlines()):
        parts = line.split("\t")
        if len(parts) != 2:
            fail(f"unsupported maintenance diff status line: {line}", "provenance", "MAINTENANCE_SCOPE_FAILURE")
        statuses[parts[1]] = parts[0]
    if statuses not in MAINTENANCE_STATUS_PROFILES:
        fail(
            f"maintenance paths must be four modifications plus the two exact additions; statuses differ: expected={MAINTENANCE_STATUS_PROFILES} actual={statuses}",
            "provenance", "MAINTENANCE_SCOPE_FAILURE",
        )
    return {
        "maintenanceBaseRef": base_ref, "maintenanceBaseCommit": base,
        "releasedBaseline": RELEASE_MERGE, "baseCommit": base, "changedPaths": sorted(changed),
        "changedPathCount": 6, "pathStatuses": dict(sorted(statuses.items())),
    }


def verify_input_deltas(inputs: dict[str, str]) -> dict:
    runtime_changed = set(filter(None, git("diff", "--name-only", f"{PRODUCT_BASELINE}..{inputs['runtime']}").splitlines()))
    expected_runtime = {*P1_PRODUCT_PATHS, WORK_PACKAGE}
    if runtime_changed != expected_runtime or git("merge-base", PRODUCT_BASELINE, inputs["runtime"]) != PRODUCT_BASELINE:
        fail(f"runtime accepted-head delta differs: {sorted(runtime_changed)}", "provenance", "PROVENANCE_FAILURE")
    qa_changed = set(filter(None, git("diff", "--name-only", f"{PRODUCT_BASELINE}..{inputs['qa']}").splitlines()))
    if qa_changed != {P1_TEST} or git("merge-base", PRODUCT_BASELINE, inputs["qa"]) != PRODUCT_BASELINE:
        fail(f"QA accepted-head delta differs: {sorted(qa_changed)}", "provenance", "PROVENANCE_FAILURE")
    return {
        "runtime": {"commit": inputs["runtime"], "changedPaths": sorted(runtime_changed)},
        "qa": {"commit": inputs["qa"], "changedPaths": sorted(qa_changed)},
    }


def provenance(manifest: dict, mode: str, base_ref: str, expected_head: str):
    items, by_path, inputs = validate_manifest(manifest)
    if mode == "integration-head":
        topology = integration_topology(base_ref)
    elif mode == "post-merge":
        topology = post_merge_topology(expected_head)
    else:
        topology = maintenance_topology(base_ref)
    if git("status", "--porcelain"):
        fail("repository dirty before checks", "provenance", "PROVENANCE_FAILURE")
    schema_blob = git("rev-parse", f"{FROZEN_BASE}:{SCHEMA}")
    if by_path[SCHEMA]["fingerprint"]["value"] != schema_blob:
        fail("frozen schema differs", "provenance", "PROVENANCE_FAILURE")
    input_deltas = verify_input_deltas(inputs)
    proof = {}
    for owner, owned in ROLE.items():
        if {item["path"] for item in items if item.get("owner") == owner} != owned:
            fail(f"{owner} inventory differs", "provenance", "PROVENANCE_FAILURE")
        files = {}
        for path in sorted(owned):
            declared = by_path[path]["fingerprint"]["value"]
            if blob_digest(git_bytes("cat-file", "blob", declared)) != declared:
                fail(f"declared blob cannot be reproduced: {path}", "provenance", "PROVENANCE_FAILURE")
            accepted = None
            if owner == "runtime" and path in P1_PRODUCT_PATHS:
                accepted = git("rev-parse", f"{inputs['runtime']}:{path}")
            elif owner == "qa" and path == P1_TEST:
                accepted = git("rev-parse", f"{inputs['qa']}:{path}")
            elif owner == "authoring":
                accepted = git("rev-parse", f"{inputs['authoring']}:{path}")
            if accepted is not None and declared != accepted:
                fail(f"{owner} accepted-head blob differs: {path}", "provenance", "PROVENANCE_FAILURE")
            if path in P1_PRODUCT_PATHS or path == P1_TEST:
                current = git("rev-parse", f"HEAD:{path}")
                if current != declared:
                    fail(f"integrated accepted blob differs: {path}", "provenance", "PROVENANCE_FAILURE")
            files[path] = {
                "declaredBlobSha1": declared,
                **({"acceptedHeadBlobSha1": accepted, "identical": True} if accepted is not None else {"preserved": True}),
            }
        proof[owner] = {"commit": inputs[owner], "reviewId": manifest["acceptedReviews"][owner], "files": files}
    accepted_wp = git("rev-parse", f"{inputs['runtime']}:{WORK_PACKAGE}")
    current_wp = git("rev-parse", f"HEAD:{WORK_PACKAGE}")
    if accepted_wp != current_wp:
        fail("integrated work-package blob differs from accepted runtime head", "provenance", "PROVENANCE_FAILURE")
    if {item["path"] for item in items if item.get("owner") == "integrator"} != INTEGRATOR:
        fail("integrator inventory differs", "provenance", "PROVENANCE_FAILURE")
    for path in INTEGRATOR - {SELF}:
        if by_path[path]["fingerprint"]["value"] != git("rev-parse", f"HEAD:{path}"):
            fail(f"integrator fingerprint stale: {path}", "provenance", "PROVENANCE_FAILURE")
    return {
        "mode": mode, "sourceCommit": git("rev-parse", "HEAD"), **topology,
        "manifestBudget": 33, "roleFileCount": 27, "roleFiles": proof,
        "acceptedInputDeltas": input_deltas,
        "workPackage": {"path": WORK_PACKAGE, "acceptedBlobSha1": accepted_wp, "materializedBlobSha1": current_wp, "identical": True},
        "schema": {"path": SCHEMA, "acceptedBlobSha1": schema_blob, "materializedBlobSha1": schema_blob, "identical": True},
    }


def materialize(destination: Path, manifest: dict) -> Path:
    root = destination / "repo"

    def ignore(directory: str, names: list[str]):
        ignored = {".git", "__pycache__", ".pytest_cache"} & set(names)
        if Path(directory).name == "learnit-next":
            ignored |= {"dist", "release", ".agent-runtime", ".agent-result"} & set(names)
        return ignored

    shutil.copytree(ROOT, root, ignore=ignore)
    for item in manifest["workingFiles"]:
        if item.get("owner") in ROLE or item["path"] == SCHEMA:
            target = root / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git_bytes("cat-file", "blob", item["fingerprint"]["value"]))

    # build.py remains frozen on the canonical 32-file build plan. The additional
    # P1 QA file is excluded only from this temporary clean-build projection.
    projected = json.loads(json.dumps(manifest, ensure_ascii=False))
    projected["workingFiles"] = [item for item in projected["workingFiles"] if item["path"] != P1_TEST]
    projected["fileBudget"] = 32
    self_item = next(item for item in projected["workingFiles"] if item["path"] == SELF)
    self_item["fingerprint"]["value"] = None
    self_item["fingerprint"]["value"] = canonical_self_digest(projected)
    (root / SELF).write_text(
        json.dumps(projected, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return root


def build(root: Path):
    result = run([sys.executable, "apps/learnit-next/build.py"], root, timeout=300)
    need(result, "build", "build", "BUILD_FAILURE")
    data = (root / ARTIFACT).read_bytes()
    return {"sha256": digest(data), "bytes": len(data), "data": data, "command": result}


def test_count(output: str) -> int:
    matches = re.findall(r"Ran\s+(\d+)\s+tests?", output)
    if not matches:
        fail(f"strict QA did not report a test count:\n{output}", "product", "PRODUCT_TEST_FAILURE")
    return int(matches[-1])


def p1_browser_smoke(root: Path, artifact: Path) -> dict:
    script = r'''
import json
import sys
from pathlib import Path
root = Path(sys.argv[1])
artifact = Path(sys.argv[2])
sys.path.insert(0, str(root / "apps/learnit-next/tests"))
from browser_vertical_slice import artifact_server, sync_playwright
fixture = json.loads((root / "contracts/fixtures/v2-valid-minimal.json").read_text(encoding="utf-8"))
qcm = fixture["courses"][0]["activities"][0]
wrong = next(choice["choiceId"] for choice in qcm["choices"] if choice["choiceId"] != qcm["correctChoiceId"])
call = """async ({operation,args}) => await window.__LEARNIT_NEXT_TEST__[operation](...args)"""
with artifact_server(artifact) as url:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
        def api(operation, *args):
            return page.evaluate(call, {"operation": operation, "args": list(args)})
        api("resetNextData")
        api("importPackage", fixture)
        course = api("listCourses")[0]
        course_id = course["courseInstallId"]
        session = api("startCourse", course_id)
        assert session["currentActivity"]["activityRevisionId"] == qcm["activityRevisionId"]
        result = api("answer", qcm["activityRevisionId"], {"choiceId": wrong})
        assert result["correct"] is False and result["completed"] is True
        queue = api("getReviewQueue", course_id)
        assert queue["total"] == 1 and queue["activityRevisionIds"] == [qcm["activityRevisionId"]]
        review = api("startReviewQueue", course_id)
        assert review["mode"] == "review" and review["currentActivity"]["activityRevisionId"] == qcm["activityRevisionId"]
        result = api("answer", qcm["activityRevisionId"], {"choiceId": qcm["correctChoiceId"]})
        assert result["correct"] is True and result["review"]["remaining"] == 0
        assert api("getReviewQueue", course_id)["total"] == 0
        browser.close()
print(json.dumps({"result":"PASS","engine":"chromium","scenario":"incorrect-review-correct-removal"}, sort_keys=True))
'''
    with tempfile.TemporaryDirectory(prefix="p1-browser-") as raw:
        smoke = Path(raw) / "smoke.py"
        smoke.write_text(script, encoding="utf-8")
        result = run([sys.executable, str(smoke), str(root), str(artifact)], root, timeout=300)
    need(result, "P1 Chromium smoke", "product", "PRODUCT_TEST_FAILURE")
    return {**result, "engine": "chromium", "scenario": "incorrect-review-correct-removal", "result": "PASS"}


def checks(report: dict, manifest: dict) -> None:
    with tempfile.TemporaryDirectory() as raw:
        first = materialize(Path(raw) / "first", manifest)
        second = materialize(Path(raw) / "second", manifest)
        build_a, build_b = build(first), build(second)
        if build_a["data"] != build_b["data"]:
            fail("clean builds differ byte-for-byte", "build", "BUILD_FAILURE")
        expected_sha = manifest["artifact"]["sha256"]
        expected_bytes = manifest["artifact"]["bytes"]
        if build_a["sha256"] != expected_sha or build_a["bytes"] != expected_bytes:
            fail(
                "released artifact identity differs: "
                f"expected_sha256={expected_sha} actual_sha256={build_a['sha256']} "
                f"expected_bytes={expected_bytes} actual_bytes={build_a['bytes']}",
                "build", "BUILD_FAILURE",
            )
        report["cleanBuilds"] = {
            "builds": [
                {"name": "clean-1", **{k: v for k, v in build_a.items() if k != "data"}},
                {"name": "clean-2", **{k: v for k, v in build_b.items() if k != "data"}},
            ], "byteForByteIdentical": True, "integratedManifestBudget": 33, "buildProjectionBudget": 32,
        }
        output = ROOT / ARTIFACT
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(build_a["data"])
        report["artifact"] = {"path": ARTIFACT.as_posix(), "sha256": build_a["sha256"], "bytes": build_a["bytes"]}

        syntax = []
        for path in sorted(P1_PRODUCT_PATHS):
            result = run(["node", "--check", path], first, timeout=120)
            need(result, f"node --check {path}", "product", "PRODUCT_TEST_FAILURE")
            syntax.append({"path": path, **result, "result": "PASS"})
        report["nodeCheck"] = {"executed": 4, "passed": 4, "files": syntax}

        env = {
            "LEARNIT_NEXT_STRICT_INTEGRATION": "1",
            "LEARNIT_NEXT_ARTIFACT": str(first / ARTIFACT),
            "P1_PRODUCT_TREE": str(ROOT),
            "P1_STRICT": "1",
        }
        p1 = run([sys.executable, P1_TEST, "-v"], first, env, 300)
        need(p1, "P1 contradictory matrix", "product", "PRODUCT_TEST_FAILURE")
        if test_count(p1["output"]) != 4 or re.search(r"skipped=|FAILED(?:\s|\()|errors?=", p1["output"], re.I):
            fail("P1 contradictory test wrapper did not pass all four tests:\n" + p1["output"], "product", "PRODUCT_TEST_FAILURE")
        report["p1Matrix"] = {**p1, "matrixExecuted": 19, "matrixPassed": 19, "matrixFailed": 0, "wrapperTests": 4}

        browser = run([sys.executable, "apps/learnit-next/tests/browser_vertical_slice.py", "-v"], first, env, 1200)
        need(browser, "browser vertical slice", "product", "PRODUCT_TEST_FAILURE")
        if re.search(r"skipped=|FAILED(?:\s|\()|errors?=", browser["output"], re.I):
            fail("browser vertical slice reported skip/failure/error:\n" + browser["output"], "product", "PRODUCT_TEST_FAILURE")
        report["browserVerticalSlice"] = {**browser, "result": "PASS", "engine": "chromium"}
        report["p1ChromiumSmoke"] = p1_browser_smoke(first, first / ARTIFACT)

        qa = run([sys.executable, "-m", "unittest", "discover", "-s", "apps/learnit-next/tests", "-p", "*.py", "-v"], first, env, 1200)
        need(qa, "strict QA", "product", "PRODUCT_TEST_FAILURE")
        total = test_count(qa["output"])
        if total < BASELINE_TESTS or re.search(r"skipped=|FAILED(?:\s|\()|errors?=", qa["output"], re.I):
            fail("QA did not preserve the baseline tests with zero skip/failure/error:\n" + qa["output"], "product", "PRODUCT_TEST_FAILURE")
        added = total - BASELINE_TESTS
        if added <= 0:
            fail("no P1 regression tests were counted", "product", "PRODUCT_TEST_FAILURE")
        report["qa"] = {**qa, "executed": total, "passed": total, "baselineProductTests": BASELINE_TESTS, "newP1RegressionTests": added, "skipped": 0, "failures": 0, "errors": 0}
        report["environment"] = {
            "python": platform.python_version(),
            "jsonschema": importlib.metadata.version("jsonschema"),
            "playwright": importlib.metadata.version("playwright"),
        }
        report["stages"]["build"] = {"result": "PASS", "classification": "BUILD_PASS"}
        report["stages"]["product"] = {"result": "PASS", "classification": "PRODUCT_TEST_PASS"}
        report["result"] = "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--mode")
    parser.add_argument("--base-ref", default=os.environ.get("LEARNIT_NEXT_BASE_REF", "origin/main"))
    parser.add_argument("--accepted-integration-head", default=os.environ.get("LEARNIT_NEXT_ACCEPTED_INTEGRATION_HEAD", ""))
    args = parser.parse_args()
    target = args.report if args.report.is_absolute() else ROOT / args.report
    strict = bool(args.strict or os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION") == "1")
    report = {
        "schema": "learnit.next.ci.checks.v3", "workPackage": "PROD-WP-003",
        "mode": args.mode, "strict": strict, "result": "FAIL",
        "stages": {name: {"result": "PENDING"} for name in ("configuration", "topology", "provenance", "build", "product")},
    }
    try:
        if not strict:
            fail("strict mode is mandatory", "configuration", "CONFIGURATION_FAILURE")
        if args.mode not in VALID_MODES:
            fail(f"unknown or missing verification mode: {args.mode!r}", "configuration", "CONFIGURATION_FAILURE")
        report["stages"]["configuration"] = {"result": "PASS", "classification": "CONFIGURATION_PASS"}
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        report["provenance"] = provenance(manifest, args.mode, args.base_ref, args.accepted_integration_head)
        report["stages"]["topology"] = {"result": "PASS", "classification": "TOPOLOGY_PASS"}
        report["stages"]["provenance"] = {"result": "PASS", "classification": "PROVENANCE_PASS"}
        checks(report, manifest)
    except GateError as error:
        report["error"] = {"message": str(error), "stage": error.stage, "classification": error.classification}
        if error.stage in report["stages"]:
            report["stages"][error.stage] = {"result": "FAIL", "classification": error.classification}
    except Exception as error:
        report["error"] = {"message": str(error), "stage": "internal", "classification": "INTERNAL_HARNESS_FAILURE"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "report": target.relative_to(ROOT).as_posix(), "mode": args.mode, "classification": report.get("error", {}).get("classification"), "artifactSha256": report.get("artifact", {}).get("sha256")}, sort_keys=True))
    if report["result"] != "PASS":
        print(report.get("error", {}).get("message", "unknown failure"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
