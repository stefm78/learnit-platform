#!/usr/bin/env python3
"""Evidence-only strict QA adapter for the exact formal Atlas M1 INT candidate.

Normal repository routing and policy are delegated to the current main runner.
This support revision performs independent strict QA against the current official
INT branch head without modifying, rebasing, merging, or promoting that branch.
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
INT_BRANCH = "agent/ATLAS-WP-001-m1-0-3-int"
EXPECTED_INT_HEAD = "74788fe041929393c317269423fbbda67637354e"
EXPECTED_ARTIFACT_SHA256 = "6ca39dd107aea45c14cd7bec7c7ff447c36af1fc12e1c8b3f6c1a0fdc066028f"
EXPECTED_ARTIFACT_BYTES = 334194
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
            "ATLAS_OFFICIAL_QA_COMMAND_FAILED:"
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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_qa_adapter(path: Path):
    spec = importlib.util.spec_from_file_location("atlas_qa_official_adapter", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("QA_ADAPTER_IMPORT_SPEC_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_chromium():
    command = [sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"]
    result = _run(command)
    return {"exitCode": result.returncode, "stdoutTail": result.stdout[-1000:]}


def _official_head() -> str:
    _run(["git", "fetch", "--force", "--no-tags", "origin", f"refs/heads/{INT_BRANCH}:refs/remotes/origin/{INT_BRANCH}"])
    actual = _git("rev-parse", f"refs/remotes/origin/{INT_BRANCH}^{{commit}}")
    if actual != EXPECTED_INT_HEAD:
        raise RuntimeError(f"OFFICIAL_INT_HEAD_MOVED:{actual}!={EXPECTED_INT_HEAD}")
    return actual


def _support_matrix():
    official = _official_head()
    heads = {profile: BASE["remote"](branch) for profile, branch in BASE["CORRECTIVE"].items()}
    for profile, head in heads.items():
        BASE["bind"](BASE["CORRECTIVE"][profile], head)
    return {
        "schema": "learnit.atlas.m1.support.official-qa-routing.v1",
        "officialIntBranch": INT_BRANCH,
        "officialIntHead": official,
        "laneHeads": heads,
        "candidateBinding": "PASS_EXACT_OFFICIAL_HEAD",
        "result": "PASS_FOR_EVIDENCE_ONLY",
    }


def strict_official_candidate_qa():
    candidate = _official_head()
    qa_head = BASE["remote"](BASE["CORRECTIVE"]["atlas-qa"])
    accepted_atlas = {
        profile: BASE["remote"](BASE["CORRECTIVE"][profile])
        for profile in BASE["PRODUCT_PROFILES"]
    }
    accepted = {profile.removeprefix("atlas-"): head for profile, head in accepted_atlas.items()}
    browser_install = _install_chromium()

    with tempfile.TemporaryDirectory(prefix="atlas-m1-official-qa-") as raw:
        temp = Path(raw)
        candidate_tree = temp / "candidate"
        qa_tree = temp / "qa"
        _run(["git", "worktree", "add", "--detach", str(candidate_tree), candidate])
        _run(["git", "worktree", "add", "--detach", str(qa_tree), qa_head])
        try:
            if _git("status", "--porcelain=v1", "--untracked-files=all", cwd=candidate_tree):
                raise RuntimeError("OFFICIAL_CANDIDATE_WORKTREE_DIRTY")
            for head in accepted_atlas.values():
                _git("merge-base", "--is-ancestor", head, candidate)

            blocked = {
                "HTTP_PROXY": "http://127.0.0.1:9",
                "HTTPS_PROXY": "http://127.0.0.1:9",
                "ALL_PROXY": "http://127.0.0.1:9",
                "NO_PROXY": "",
            }
            artifact = temp / "learnit-next.html"
            build = [
                sys.executable,
                "-B",
                str(candidate_tree / "apps/learnit-next/build.py"),
                "--output",
                str(artifact),
            ]
            _run(build, cwd=candidate_tree, env=blocked)
            artifact_sha = _sha256(artifact)
            artifact_bytes = artifact.stat().st_size
            if artifact_sha != EXPECTED_ARTIFACT_SHA256:
                raise RuntimeError(
                    f"OFFICIAL_ARTIFACT_SHA_MISMATCH:{artifact_sha}!={EXPECTED_ARTIFACT_SHA256}"
                )
            if artifact_bytes != EXPECTED_ARTIFACT_BYTES:
                raise RuntimeError(
                    f"OFFICIAL_ARTIFACT_BYTES_MISMATCH:{artifact_bytes}!={EXPECTED_ARTIFACT_BYTES}"
                )

            package = json.loads((candidate_tree / PACKAGE_PATH).read_text(encoding="utf-8"))
            revision = {
                "packageLineageId": package["packageLineageId"],
                "packageRevisionId": package["packageRevisionId"],
                "packageDigest": package["packageRevisionDigest"],
            }
            revision_path = temp / "revision.json"
            revision_path.write_text(json.dumps(revision, sort_keys=True) + "\n", encoding="utf-8")

            qa_script = qa_tree / "apps/learnit-next/tests/qa_atlas_m1.py"
            qa = _load_qa_adapter(qa_script)
            claim_ids = sorted(qa.FROZEN["claim_ids"](candidate_tree, revision))
            oracle_version = f"git:{qa_head}"

            claims_path = temp / "claims.json"
            claims_path.write_text(json.dumps({
                "schemaVersion": "atlas.accepted-validation-claims.v1",
                "contentRevisionRef": revision,
                "oracleVersion": oracle_version,
                "artifactDigest": f"sha256:{artifact_sha}",
                "acceptedClaimIds": claim_ids,
            }, sort_keys=True) + "\n", encoding="utf-8")

            provenance_path = temp / "provenance.json"
            provenance_path.write_text(json.dumps({
                "schemaVersion": "atlas.artifact-provenance.v1",
                "candidateHead": candidate,
                "artifactSha256": artifact_sha,
                "acceptedHeads": accepted,
                "buildCommands": [build],
                "cleanCheckout": True,
                "networkBlocked": True,
            }, sort_keys=True) + "\n", encoding="utf-8")

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
            driver_path.write_text(json.dumps(driver, sort_keys=True) + "\n", encoding="utf-8")

            command = [
                sys.executable,
                str(qa_script),
                "--strict",
                "--candidate-head",
                candidate,
                "--artifact",
                str(artifact),
                "--artifact-sha256",
                artifact_sha,
                "--accepted-head",
                f"learning={accepted['learning']}",
                "--accepted-head",
                f"core={accepted['core']}",
                "--accepted-head",
                f"experience={accepted['experience']}",
                "--accepted-head",
                f"content={accepted['content']}",
                "--claim-set",
                str(claims_path),
                "--content-revision",
                str(revision_path),
                "--oracle-version",
                oracle_version,
                "--artifact-provenance",
                str(provenance_path),
                "--repo-root",
                str(ROOT),
                "--source-root",
                str(candidate_tree),
                "--driver-config",
                str(driver_path),
            ]
            done = _run(command, cwd=qa_tree, env=blocked, check=False)
            print("ATLAS_OFFICIAL_QA_STDOUT_BEGIN", flush=True)
            print(done.stdout, flush=True)
            print(done.stderr, file=sys.stderr, flush=True)
            print("ATLAS_OFFICIAL_QA_STDOUT_END", flush=True)
            if done.returncode:
                raise RuntimeError(f"OFFICIAL_STRICT_QA_FAILED:{done.returncode}")
            proof = json.loads(done.stdout)
            if proof.get("verdict") != "PASS_TO_HUMAN_GATE":
                raise RuntimeError("OFFICIAL_STRICT_QA_NOT_GREEN")
            if proof.get("candidateHead") != candidate:
                raise RuntimeError("OFFICIAL_STRICT_QA_CANDIDATE_BINDING_MISMATCH")
            return {
                "schema": "learnit.atlas.m1.official-candidate-qa-evidence.v1",
                "candidateHead": candidate,
                "artifactSha256": artifact_sha,
                "artifactBytes": artifact_bytes,
                "acceptedProductHeads": accepted,
                "qaExecutionHead": qa_head,
                "strictProof": proof,
                "browserInstall": browser_install,
                "result": "PASS",
                "verdict": "PASS_TO_HUMAN_GATE",
            }
        finally:
            _run(["git", "worktree", "remove", "--force", str(qa_tree)], check=False)
            _run(["git", "worktree", "remove", "--force", str(candidate_tree)], check=False)


def capability():
    return {
        "schema": "learnit.atlas.m1.support.official-candidate-qa-capability.v1",
        "purpose": "EVIDENCE_ONLY_DO_NOT_AUTONOMOUSLY_MERGE",
        "routingSelfTest": _support_matrix(),
        "strictOfficialCandidateQa": strict_official_candidate_qa(),
        "failClosed": True,
    }


BASE["matrix"] = _support_matrix
BASE["capability"] = capability

if __name__ == "__main__":
    raise SystemExit(BASE["main"]())
