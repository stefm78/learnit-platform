#!/usr/bin/env python3
"""M2 independent-QA adapter for the product head resynchronized onto current main.

This adapter reuses the exact previously-passing QA file from
ac84bbfc6fbe788b7f43b5f3edcdd0a016be8699, verifies its blob identity, and changes only the frozen
product-head binding from 44568536... to ce7cf459....
The M2 product artifact is independently required to remain byte-identical.
"""
from __future__ import annotations

import pathlib
import subprocess

PREVIOUS_QA_HEAD = "ac84bbfc6fbe788b7f43b5f3edcdd0a016be8699"
PREVIOUS_QA_BLOB = "318280de74367677b70283441e4de8d890298173"
QA_PATH = "apps/learnit-next/tests/qa_atlas_m2.py"
OLD_PRODUCT_HEAD = "445685363d431549fd7addfc2cf3e2f4083d339e"
NEW_PRODUCT_HEAD = "ce7cf459902281c44557ae017f92c7667e0393df"
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
