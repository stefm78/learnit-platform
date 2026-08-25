#!/usr/bin/env python3
"""M2 independent-QA head adapter for the refreshed exact product head.

This adapter reuses the already-passing contradictory QA oracle from exact QA
head cfcc3854bd4b18e93a9f8627a89e46d5cc87c3f6, verifies its blob identity,
and changes only the frozen product-head binding from 104b80f... to 4456853....
The M2 artifact bytes are unchanged by the product governance-only commit.
"""
from __future__ import annotations

import pathlib
import subprocess

PREVIOUS_QA_HEAD = "cfcc3854bd4b18e93a9f8627a89e46d5cc87c3f6"
PREVIOUS_QA_BLOB = "a22176b2dfcf65a4195958c17344ca3a2d3e9a69"
QA_PATH = "apps/learnit-next/tests/qa_atlas_m2.py"
OLD_PRODUCT_HEAD = "104b80f2392c9a7593cf8aad8ed1f154487623f0"
NEW_PRODUCT_HEAD = "445685363d431549fd7addfc2cf3e2f4083d339e"
HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[3]


def git(*args: str) -> str:
    run = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if run.returncode:
        raise RuntimeError(
            "ATLAS_M2_QA_LINEAGE_GIT_FAILURE:"
            + " ".join(args)
            + ":"
            + (run.stderr.strip() or run.stdout.strip())
        )
    return run.stdout


actual_blob = git("rev-parse", f"{PREVIOUS_QA_HEAD}:{QA_PATH}").strip()
if actual_blob != PREVIOUS_QA_BLOB:
    raise RuntimeError(
        f"ATLAS_M2_QA_PREVIOUS_BLOB_MISMATCH:{actual_blob}!={PREVIOUS_QA_BLOB}"
    )

source = git("show", f"{PREVIOUS_QA_HEAD}:{QA_PATH}")
if source.count(OLD_PRODUCT_HEAD) != 1:
    raise RuntimeError(
        f"ATLAS_M2_QA_PRODUCT_BINDING_ANCHOR_MISMATCH:{source.count(OLD_PRODUCT_HEAD)}"
    )
source = source.replace(OLD_PRODUCT_HEAD, NEW_PRODUCT_HEAD, 1)

namespace = {
    "__file__": str(HERE),
    "__name__": "__main__",
}
exec(compile(source, str(HERE), "exec"), namespace)
