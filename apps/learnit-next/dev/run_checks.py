#!/usr/bin/env python3
"""Ephemeral ATLAS M1 exact-candidate QA evidence adapter.

This support revision delegates normal repository policy to the current main
runner, but evaluates the next INT composition in an isolated temporary
worktree. The synthetic candidate is never pushed or promoted: it is used only
to discover whether the superseding accepted CORE head introduces any further
strict-QA defect before the official INT branch is advanced.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
RUNNER_PATH = "apps/learnit-next/dev/run_checks.py"
OLD_INT_HEAD = "6c9ab4a3386c698d6e6a8041df8aca338e68df6d"
COMPOSITION_HEAD = "b36f3470d825de55b9864851c47b13ba8d8a7ffc"
RECOMPOSE_BRANCH = "agent/ATLAS-WP-001-m1-0-3-int-recompose"
OLD_ARTIFACT_SHA256 = "40757ff4c44a55d361768491d7117b5e3a783aa2b68d4f65b0fd9300eed2c82e"
PACKAGE_PATH = "authoring/v2/atlas/nombres_complexes_atlas.json"
CORRECT_FIRST_CHOICE = "ea613748-02df-4b7f-bcf0-ce7494de03db"


def _run(command, *, cwd=ROOT, env=None, check=True):
    completed = subprocess.run(
        command,
        cwd=cwd,
        env={**os.environ, **(env or {}), "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=1800,
        check=False,
    )
    if check and completed.returncode:
        raise RuntimeError(
            "ATLAS_QA_EVIDENCE_COMMAND_FAILED:"
            + " ".join(command)
            + "\nSTDOUT:\n"
            + completed.stdout
            + "\nSTDERR:\n"
            + completed.stderr
        )
    return completed


def _git(*args, cwd=ROOT):
    return _run(["git", *args], cwd=cwd).stdout.strip()


def _load_main_runner():
    source = _git("show", f"origin/main:{RUNNER_PATH}")
    namespace = {"__file__": str(HERE), "__name__": "atlas_support_main_runner"}
    exec(compile(source, str(HERE), "exec"), namespace)
    return namespace


BASE = _load_main_runner()


def _sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _manifest_self_digest(manifest):
    clone = json.loads(json.dumps(manifest, ensure_ascii=False))
    hit = [x for x in clone["workingFiles"] if x["path"] == "apps/learnit-next/source_manifest.json"]
    if len(hit) != 1:
        raise RuntimeError("MANIFEST_SELF_ENTRY_INVALID")
    hit[0]["fingerprint"]["value"] = None
    return hashlib.sha256(_canonical_bytes(clone)).hexdigest()


def _refresh_manifest(candidate_tree: Path, accepted_core: str):
    path = candidate_tree / "apps/learnit-next/source_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["acceptedInputs"]["ATLAS-CORE"] = accepted_core

    core_paths = set(BASE["frozen"]()["ATLAS"]["atlas-core"][1])
    for item in manifest["workingFiles"]:
        rel = item["path"]
        if rel in core_paths:
            data = (candidate_tree / rel).read_bytes()
            item["fingerprint"] = {
                "kind": "git-blob-sha1",
                "value": _git_blob_sha1(data),
            }
            item["provenance"] = f"ATLAS-CORE:{accepted_core}"

    for item in manifest["workingFiles"]:
        if item["path"] == "apps/learnit-next/source_manifest.json":
            item["fingerprint"]["value"] = None
            break
    digest = _manifest_self_digest(manifest)
    for item in manifest["workingFiles"]:
        if item["path"] == "apps/learnit-next/source_manifest.json":
            item["fingerprint"]["value"] = digest
            break

    path.write_bytes(_canonical_bytes(manifest) + b"\n")
    return digest


def _load_qa_adapter(path):
    spec = importlib.util.spec_from_file_location("atlas_qa_candidate_adapter", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("QA_ADAPTER_IMPORT_SPEC_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_chromium():
    c = [sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"]
    r = _run(c)
    return {"exitCode": r.returncode, "stdoutTail": r.stdout[-1000:]}


def _materialize_candidate(temp: Path):
    _run(["git", "fetch", "origin", f"{RECOMPOSE_BRANCH}:refs/remotes/origin/{RECOMPOSE_BRANCH}"])
    head = _git("rev-parse", f"origin/{RECOMPOSE_BRANCH}")
    if head != COMPOSITION_HEAD:
        raise RuntimeError(f"RECOMPOSE_HEAD_MISMATCH:{head}!={COMPOSITION_HEAD}")
    tree = temp / "candidate"
    _run(["git", "worktree", "add", "--detach", str(tree), head])
    accepted_core = BASE["remote"](BASE["CORRECTIVE"]["atlas-core"])
    self_digest = _refresh_manifest(tree, accepted_core)
    _run(["git", "add", "apps/learnit-next/source_manifest.json"], cwd=tree)
    _run([
        "git", "-c", "user.name=Atlas QA", "-c", "user.email=atlas-qa@localhost",
        "commit", "-m", "chore(atlas-int): refresh manifest for strict QA evidence",
    ], cwd=tree)
    candidate = _git("rev-parse", "HEAD", cwd=tree)
    if _git("status", "--porcelain=v1", "--untracked-files=all", cwd=tree):
        raise RuntimeError("SYNTHETIC_CANDIDATE_DIRTY")
    return tree, candidate, accepted_core, self_digest


def _matrix_without_old_int_binding():
    heads = {p: BASE["remote"](b) for p, b in BASE["CORRECTIVE"].items()}
    for p, h in heads.items():
        BASE["bind"](BASE["CORRECTIVE"][p], h)
    return {
        "schema": "learnit.atlas.m1.support.recomposition-routing.v1",
        "officialIntHead": BASE["remote"](BASE["INT_BRANCH"]),
        "expectedOldIntHead": OLD_INT_HEAD,
        "recomposeHead": COMPOSITION_HEAD,
        "laneHeads": heads,
        "result": "PASS_FOR_EVIDENCE_ONLY",
    }


def strict_candidate_qa():
    qa_head = BASE["remote"](BASE["CORRECTIVE"]["atlas-qa"])
    accepted_atlas = {
        p: BASE["remote"](BASE["CORRECTIVE"][p])
        for p in BASE["PRODUCT_PROFILES"]
    }
    accepted = {p.removeprefix("atlas-"): h for p, h in accepted_atlas.items()}
    browser_install = _install_chromium()

    with tempfile.TemporaryDirectory(prefix="atlas-m1-recompose-qa-") as raw:
        temp = Path(raw)
        candidate_tree, candidate, accepted_core, self_digest = _materialize_candidate(temp)
        qa_tree = temp / "qa"
        _run(["git", "worktree", "add", "--detach", str(qa_tree), qa_head])
        try:
            for head in accepted_atlas.values():
                _git("merge-base", "--is-ancestor", head, candidate)

            artifact = temp / "learnit-next.html"
            blocked = {
                "HTTP_PROXY": "http://127.0.0.1:9",
                "HTTPS_PROXY": "http://127.0.0.1:9",
                "ALL_PROXY": "http://127.0.0.1:9",
                "NO_PROXY": "",
            }
            build = [
                sys.executable, "-B", str(candidate_tree / "apps/learnit-next/build.py"),
                "--output", str(artifact),
            ]
            _run(build, cwd=candidate_tree, env=blocked)
            artifact_sha = _sha256(artifact)
            if artifact_sha == OLD_ARTIFACT_SHA256:
                raise RuntimeError("RECOMPOSE_ARTIFACT_DID_NOT_CHANGE")

            package = json.loads((candidate_tree / PACKAGE_PATH).read_text(encoding="utf-8"))
            revision = {
                "packageLineageId": package["packageLineageId"],
                "packageRevisionId": package["packageRevisionId"],
                "packageDigest": package["packageRevisionDigest"],
            }
            revision_path = temp / "revision.json"
            revision_path.write_text(json.dumps(revision, sort_keys=True) + "\n")

            qa_script = qa_tree / "apps/learnit-next/tests/qa_atlas_m1.py"
            qa = _load_qa_adapter(qa_script)
            frozen = qa.FROZEN
            claim_ids = sorted(frozen["claim_ids"](candidate_tree, revision))
            oracle_version = f"git:{qa_head}"

            claims_path = temp / "claims.json"
            claims_path.write_text(json.dumps({
                "schemaVersion": "atlas.accepted-validation-claims.v1",
                "contentRevisionRef": revision,
                "oracleVersion": oracle_version,
                "artifactDigest": f"sha256:{artifact_sha}",
                "acceptedClaimIds": claim_ids,
            }, sort_keys=True) + "\n")

            provenance_path = temp / "provenance.json"
            provenance_path.write_text(json.dumps({
                "schemaVersion": "atlas.artifact-provenance.v1",
                "candidateHead": candidate,
                "artifactSha256": artifact_sha,
                "acceptedHeads": accepted,
                "buildCommands": [build],
                "cleanCheckout": True,
                "networkBlocked": True,
            }, sort_keys=True) + "\n")

            package_file = str((candidate_tree / PACKAGE_PATH).resolve())
            driver = {
                "startSelector": "[data-atlas-action=\"start\"]",
                "submitSelector": "[data-atlas-submit]",
                "interruptSelector": "[data-atlas-pause-session]",
                "resumeSelector": "[data-atlas-resume-session=\"true\"]",
                "responseSteps": [{
                    "action": "click",
                    "selector": "input[name=\"atlas-qcm-choice\"][value=\"%s\"]" % CORRECT_FIRST_CHOICE,
                }],
                "waitAfterActionMs": 500,
                "setupSteps": [
                    {"action": "wait", "selector": "#kit-file"},
                    {"action": "upload", "selector": "#kit-file", "value": package_file},
                    {"action": "wait", "selector": ".import-panel button[type=\"submit\"]:not([disabled])"},
                    {"action": "click", "selector": ".import-panel button[type=\"submit\"]:not([disabled])"},
                    {"action": "wait", "selector": "[data-atlas-duration=\"15\"]"},
                    {"action": "click", "selector": "[data-atlas-duration=\"15\"]"},
                    {"action": "wait", "selector": "[data-atlas-action=\"start\"]"},
                ],
            }
            driver_path = temp / "driver.json"
            driver_path.write_text(json.dumps(driver, sort_keys=True) + "\n")

            command = [
                sys.executable, str(qa_script), "--strict",
                "--candidate-head", candidate,
                "--artifact", str(artifact),
                "--artifact-sha256", artifact_sha,
                "--accepted-head", f"learning={accepted['learning']}",
                "--accepted-head", f"core={accepted['core']}",
                "--accepted-head", f"experience={accepted['experience']}",
                "--accepted-head", f"content={accepted['content']}",
                "--claim-set", str(claims_path),
                "--content-revision", str(revision_path),
                "--oracle-version", oracle_version,
                "--artifact-provenance", str(provenance_path),
                "--repo-root", str(ROOT),
                "--source-root", str(candidate_tree),
                "--driver-config", str(driver_path),
            ]
            done = _run(command, cwd=qa_tree, env=blocked, check=False)
            print("ATLAS_RECOMPOSE_QA_STDOUT_BEGIN", flush=True)
            print(done.stdout, flush=True)
            print(done.stderr, file=sys.stderr, flush=True)
            print("ATLAS_RECOMPOSE_QA_STDOUT_END", flush=True)
            if done.returncode:
                raise RuntimeError(f"RECOMPOSE_STRICT_QA_FAILED:{done.returncode}")
            proof = json.loads(done.stdout)
            if proof.get("verdict") != "PASS_TO_HUMAN_GATE":
                raise RuntimeError("RECOMPOSE_STRICT_QA_NOT_GREEN")
            return {
                "schema": "learnit.atlas.m1.recomposition-evidence.v2",
                "compositionHead": COMPOSITION_HEAD,
                "syntheticCandidateHead": candidate,
                "acceptedCoreHead": accepted_core,
                "manifestSelfSha256": self_digest,
                "formalManifestUtf8": (candidate_tree / "apps/learnit-next/source_manifest.json").read_text(encoding="utf-8"),
                "artifactSha256": artifact_sha,
                "artifactBytes": artifact.stat().st_size,
                "qaHead": qa_head,
                "strictProof": proof,
                "browserInstall": browser_install,
                "result": "PASS",
                "verdict": "PASS_TO_FORMAL_INT_RECOMPOSITION",
            }
        finally:
            _run(["git", "worktree", "remove", "--force", str(qa_tree)], check=False)
            _run(["git", "worktree", "remove", "--force", str(candidate_tree)], check=False)


def capability():
    return {
        "schema": "learnit.atlas.m1.support.recomposition-capability.v2",
        "purpose": "EVIDENCE_ONLY_DO_NOT_AUTONOMOUSLY_MERGE",
        "routingSelfTest": _matrix_without_old_int_binding(),
        "strictCandidateQa": strict_candidate_qa(),
        "failClosed": True,
    }


BASE["matrix"] = _matrix_without_old_int_binding
BASE["capability"] = capability

if __name__ == "__main__":
    raise SystemExit(BASE["main"]())
