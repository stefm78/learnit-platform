#!/usr/bin/env python3
"""Ephemeral ATLAS M1 exact-candidate QA evidence adapter.

This support revision intentionally delegates all normal routing and gate logic to
the current main runner, then strengthens only the atlas-support capability with
one exact-candidate strict QA execution. It is evidence infrastructure, not a
product or QA semantic change, and is not intended for autonomous merge.
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
from typing import Any

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
RUNNER_PATH = "apps/learnit-next/dev/run_checks.py"
EXPECTED_ARTIFACT_SHA256 = "40757ff4c44a55d361768491d7117b5e3a783aa2b68d4f65b0fd9300eed2c82e"
PACKAGE_PATH = "authoring/v2/atlas/nombres_complexes_atlas.json"
CORRECT_FIRST_CHOICE = "ea613748-02df-4b7f-bcf0-ce7494de03db"


def _run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
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


def _git(*args: str, cwd: Path = ROOT) -> str:
    return _run(["git", *args], cwd=cwd).stdout.strip()


def _load_main_runner() -> dict[str, Any]:
    source = _git("show", f"origin/main:{RUNNER_PATH}")
    namespace: dict[str, Any] = {
        "__file__": str(HERE),
        "__name__": "atlas_support_main_runner",
    }
    exec(compile(source, str(HERE), "exec"), namespace)
    return namespace


BASE = _load_main_runner()


def _worktree_add(path: Path, commit: str) -> None:
    _run(["git", "worktree", "add", "--detach", str(path), commit])


def _worktree_remove(path: Path) -> None:
    _run(
        ["git", "worktree", "remove", "--force", str(path)],
        check=False,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_qa_adapter(path: Path):
    spec = importlib.util.spec_from_file_location(
        "atlas_qa_exact_candidate_adapter",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("ATLAS_QA_ADAPTER_IMPORT_SPEC_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_chromium() -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "playwright",
        "install",
        "--with-deps",
        "chromium",
    ]
    completed = _run(command)
    return {
        "command": command,
        "exitCode": completed.returncode,
        "stdoutTail": completed.stdout[-2000:],
        "stderrTail": completed.stderr[-2000:],
    }


def strict_candidate_qa() -> dict[str, Any]:
    candidate = BASE["remote"](BASE["INT_BRANCH"])
    qa_head = BASE["remote"](BASE["CORRECTIVE"]["atlas-qa"])

    accepted_atlas = {
        profile: BASE["remote"](BASE["CORRECTIVE"][profile])
        for profile in BASE["PRODUCT_PROFILES"]
    }
    accepted = {
        profile.removeprefix("atlas-"): head
        for profile, head in accepted_atlas.items()
    }

    for profile, head in accepted_atlas.items():
        _git("merge-base", "--is-ancestor", head, candidate)

    browser_install = _install_chromium()

    with tempfile.TemporaryDirectory(prefix="atlas-m1-strict-qa-") as raw:
        temp = Path(raw)
        candidate_tree = temp / "candidate"
        qa_tree = temp / "qa"
        artifact = temp / "learnit-next.html"
        revision_path = temp / "content-revision.json"
        claims_path = temp / "accepted-claims.json"
        provenance_path = temp / "artifact-provenance.json"
        driver_path = temp / "driver.json"

        _worktree_add(candidate_tree, candidate)
        _worktree_add(qa_tree, qa_head)

        try:
            if _git("rev-parse", "HEAD", cwd=candidate_tree) != candidate:
                raise RuntimeError("ATLAS_QA_CANDIDATE_WORKTREE_HEAD_MISMATCH")
            if _git("status", "--porcelain=v1", "--untracked-files=all", cwd=candidate_tree):
                raise RuntimeError("ATLAS_QA_CANDIDATE_WORKTREE_DIRTY")
            if _git("rev-parse", "HEAD", cwd=qa_tree) != qa_head:
                raise RuntimeError("ATLAS_QA_ORACLE_WORKTREE_HEAD_MISMATCH")

            build_command = [
                sys.executable,
                "-B",
                str(candidate_tree / "apps/learnit-next/build.py"),
                "--output",
                str(artifact),
            ]
            blocked = {
                "HTTP_PROXY": "http://127.0.0.1:9",
                "HTTPS_PROXY": "http://127.0.0.1:9",
                "ALL_PROXY": "http://127.0.0.1:9",
                "NO_PROXY": "",
            }
            _run(build_command, cwd=candidate_tree, env=blocked)
            artifact_sha = _sha256(artifact)
            if artifact_sha != EXPECTED_ARTIFACT_SHA256:
                raise RuntimeError(
                    "ATLAS_QA_ARTIFACT_SHA_MISMATCH:"
                    f"{artifact_sha}!={EXPECTED_ARTIFACT_SHA256}"
                )

            package = json.loads(
                (candidate_tree / PACKAGE_PATH).read_text(encoding="utf-8")
            )
            revision = {
                "packageLineageId": package["packageLineageId"],
                "packageRevisionId": package["packageRevisionId"],
                "packageDigest": package["packageRevisionDigest"],
            }
            revision_path.write_text(
                json.dumps(revision, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            qa_script = qa_tree / "apps/learnit-next/tests/qa_atlas_m1.py"
            qa_module = _load_qa_adapter(qa_script)
            frozen = qa_module.FROZEN
            accepted_claim_ids = sorted(
                frozen["claim_ids"](candidate_tree, revision)
            )
            if not accepted_claim_ids:
                raise RuntimeError("ATLAS_QA_ACCEPTED_CLAIMS_EMPTY")

            oracle_version = f"git:{qa_head}"
            claims = {
                "schemaVersion": "atlas.accepted-validation-claims.v1",
                "contentRevisionRef": revision,
                "oracleVersion": oracle_version,
                "artifactDigest": f"sha256:{artifact_sha}",
                "acceptedClaimIds": accepted_claim_ids,
            }
            claims_path.write_text(
                json.dumps(claims, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            provenance = {
                "schemaVersion": "atlas.artifact-provenance.v1",
                "candidateHead": candidate,
                "artifactSha256": artifact_sha,
                "acceptedHeads": accepted,
                "buildCommands": [build_command],
                "cleanCheckout": True,
                "networkBlocked": True,
            }
            provenance_path.write_text(
                json.dumps(provenance, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            package_file = str((candidate_tree / PACKAGE_PATH).resolve())
            driver = {
                "startSelector": "[data-atlas-action=\"start\"]",
                "submitSelector": "[data-atlas-submit]",
                "interruptSelector": "[data-atlas-pause-session]",
                "resumeSelector": "[data-atlas-resume-session=\"true\"]",
                "responseSteps": [
                    {
                        "action": "click",
                        "selector": (
                            "input[name=\"atlas-qcm-choice\"]"
                            f"[value=\"{CORRECT_FIRST_CHOICE}\"]"
                        ),
                    }
                ],
                "waitAfterActionMs": 500,
                "setupSteps": [
                    {"action": "wait", "selector": "#kit-file"},
                    {
                        "action": "upload",
                        "selector": "#kit-file",
                        "value": package_file,
                    },
                    {
                        "action": "wait",
                        "selector": ".import-panel button[type=\"submit\"]:not([disabled])",
                    },
                    {
                        "action": "click",
                        "selector": ".import-panel button[type=\"submit\"]:not([disabled])",
                    },
                    {
                        "action": "wait",
                        "selector": "[data-atlas-duration=\"15\"]",
                    },
                    {
                        "action": "click",
                        "selector": "[data-atlas-duration=\"15\"]",
                    },
                    {
                        "action": "wait",
                        "selector": "[data-atlas-action=\"start\"]",
                    },
                ],
            }
            driver_path.write_text(
                json.dumps(driver, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

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
            completed = _run(
                command,
                cwd=qa_tree,
                env=blocked,
                check=False,
            )
            if completed.returncode:
                raise RuntimeError(
                    "ATLAS_QA_STRICT_FAILED"
                    + "\nSTDOUT:\n"
                    + completed.stdout
                    + "\nSTDERR:\n"
                    + completed.stderr
                )

            try:
                strict_proof = json.loads(completed.stdout)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    "ATLAS_QA_STRICT_OUTPUT_NOT_JSON:\n" + completed.stdout
                ) from error

            if strict_proof.get("verdict") != "PASS_TO_HUMAN_GATE":
                raise RuntimeError(
                    "ATLAS_QA_STRICT_VERDICT_NOT_GREEN:"
                    + json.dumps(strict_proof, sort_keys=True)
                )
            if strict_proof.get("candidateHead") != candidate:
                raise RuntimeError("ATLAS_QA_STRICT_CANDIDATE_BINDING_MISMATCH")
            if strict_proof.get("artifactSha256") != artifact_sha:
                raise RuntimeError("ATLAS_QA_STRICT_ARTIFACT_BINDING_MISMATCH")

            return {
                "schema": "learnit.atlas.m1.strict-candidate-qa-evidence.v1",
                "candidateHead": candidate,
                "qaCorrectiveHead": qa_head,
                "artifactSha256": artifact_sha,
                "acceptedHeads": accepted,
                "acceptedClaimIds": accepted_claim_ids,
                "oracleVersion": oracle_version,
                "browserInstall": browser_install,
                "driverMode": "REAL_PRODUCT_UI_SETUP_THEN_FROZEN_QA_ACTIONS",
                "strictProof": strict_proof,
                "result": "PASS",
                "verdict": "PASS_TO_HUMAN_GATE",
            }
        finally:
            _worktree_remove(qa_tree)
            _worktree_remove(candidate_tree)


def capability() -> dict[str, Any]:
    proof = strict_candidate_qa()
    return {
        "schema": "learnit.atlas.m1.support.strict-qa-capability.v1",
        "purpose": "EVIDENCE_ONLY_DO_NOT_AUTONOMOUSLY_MERGE",
        "routingSelfTest": BASE["matrix"](),
        "strictCandidateQa": proof,
        "failClosed": True,
    }


BASE["capability"] = capability

if __name__ == "__main__":
    raise SystemExit(BASE["main"]())
