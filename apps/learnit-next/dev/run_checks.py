#!/usr/bin/env python3
"""Evidence-only strict-QA wrapper for the refreshed exact Atlas M1 candidate.

The reviewed evidence adapter is loaded byte-for-byte from the previously green
evidence commit. This wrapper changes only the exact candidate binding and the
human-artifact filename. Product, QA-oracle and normal CI semantics remain owned
by their existing refs.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
RUNNER_PATH = "apps/learnit-next/dev/run_checks.py"
EVIDENCE_SOURCE_COMMIT = "14698568c28107a2e25fd4c17c6fda0c9e16f00e"
EXPECTED_INT_HEAD = "e2c10c8eb5a3e1c4dff5e45b210f327942bafce8"
EXPECTED_ARTIFACT_SHA256 = "6ca39dd107aea45c14cd7bec7c7ff447c36af1fc12e1c8b3f6c1a0fdc066028f"
EXPECTED_ARTIFACT_BYTES = 334194


def _git_show(spec: str) -> str:
    completed = subprocess.run(
        ["git", "show", spec],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=1800,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            "ATLAS_QA_EVIDENCE_SOURCE_UNAVAILABLE:"
            + spec
            + "\n"
            + completed.stderr
        )
    return completed.stdout


source = _git_show(f"{EVIDENCE_SOURCE_COMMIT}:{RUNNER_PATH}")
namespace = {
    "__file__": str(HERE),
    "__name__": "atlas_m1_prior_green_evidence_adapter",
}
exec(compile(source, str(HERE), "exec"), namespace)

if namespace.get("EXPECTED_ARTIFACT_SHA256") != EXPECTED_ARTIFACT_SHA256:
    raise RuntimeError("ATLAS_QA_EVIDENCE_ARTIFACT_SHA_AUTHORITY_MISMATCH")
if namespace.get("EXPECTED_ARTIFACT_BYTES") != EXPECTED_ARTIFACT_BYTES:
    raise RuntimeError("ATLAS_QA_EVIDENCE_ARTIFACT_SIZE_AUTHORITY_MISMATCH")

namespace["EXPECTED_INT_HEAD"] = EXPECTED_INT_HEAD
_original_strict_qa = namespace["strict_official_candidate_qa"]


def _strict_qa_refreshed_candidate():
    proof = _original_strict_qa()
    if proof.get("candidateHead") != EXPECTED_INT_HEAD:
        raise RuntimeError("ATLAS_QA_REFRESHED_CANDIDATE_BINDING_MISMATCH")
    if proof.get("artifactSha256") != EXPECTED_ARTIFACT_SHA256:
        raise RuntimeError("ATLAS_QA_REFRESHED_ARTIFACT_SHA_MISMATCH")
    if proof.get("artifactBytes") != EXPECTED_ARTIFACT_BYTES:
        raise RuntimeError("ATLAS_QA_REFRESHED_ARTIFACT_SIZE_MISMATCH")
    proof["artifactFileName"] = (
        "learnit-next-atlas-m1-" + EXPECTED_INT_HEAD + ".html"
    )
    proof["candidateSupersedes"] = "74788fe041929393c317269423fbbda67637354e"
    proof["humanGateArtifactIdentity"] = "PASS_BYTE_IDENTICAL_TO_PREVIOUSLY_VALIDATED_ARTIFACT"
    return proof


namespace["strict_official_candidate_qa"] = _strict_qa_refreshed_candidate

raise SystemExit(namespace["BASE"]["main"]())
