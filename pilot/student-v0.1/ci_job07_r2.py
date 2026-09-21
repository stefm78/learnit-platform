#!/usr/bin/env python3
"""Exact-head CI driver for Student V0.1 JOB07 R2."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "7c13d67a76705b4452304c0f6a882504bc7701a7"
REPAIRED = "bdb66bffefd6738e3cb4004d304159e9d3d048ce"
GENERATOR_BLOB = "85debca78c3ec342d9e4e7ed63a033fd0968e72e"
REJECTED_FIXTURE_BLOB = "943944eaee6944529810acffc06e61affc71f909"
APP_SHA = "85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e"
APP_BYTES = 478657
BRANCH = "student-v01/wave2-pilot-package-r2"

ALLOWED_EXACT = {
    "work-packages/ATLAS-WP-040.json",
    "docs/programs/student-v0.1/jobs/JOB_07_R2_PILOT_PACKAGING_UX.md",
    ".github/workflows/learnit-next-ci.yml",
    "qualification/STUDENT_V01_JOB07_R2_PILOT_RESULT.md",
}

def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=capture)

def output(command: list[str]) -> str:
    return run(command, capture=True).stdout.strip()

def allowed(path: str) -> bool:
    return path in ALLOWED_EXACT or path.startswith("pilot/student-v0.1/")

def main() -> int:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        raise SystemExit("JOB07 R2 exact route requires pull_request")
    if os.environ.get("JOB07_R2_BRANCH") != BRANCH:
        raise SystemExit("JOB07 R2 branch routing mismatch")
    target = os.environ.get("JOB07_R2_TARGET", "")
    pr_base = os.environ.get("JOB07_R2_PR_BASE_SHA", "")
    if pr_base != BASE:
        raise SystemExit(f"PR base drift: {pr_base}")
    if output(["git", "rev-parse", "HEAD"]) != target:
        raise SystemExit("checked out target differs from routed target")
    if output(["git", "merge-base", BASE, target]) != BASE:
        raise SystemExit("exact R2 base is no longer merge base")
    run(["git", "merge-base", "--is-ancestor", REPAIRED, target])
    remote = output(["git", "ls-remote", "--exit-code", "--heads", "origin", BRANCH]).split()[0]
    if remote != target:
        raise SystemExit(f"remote branch head {remote} differs from target {target}")

    changed = output(["git", "diff", "--name-only", BASE, target]).splitlines()
    forbidden = [path for path in changed if path and not allowed(path)]
    if forbidden:
        raise SystemExit(f"scope violation: {forbidden}")

    if output(["git", "rev-parse", "HEAD:authoring/v4/tests/test_validate_v4.py"]) != GENERATOR_BLOB:
        raise SystemExit("canonical generator blob drift")
    if output(["git", "rev-parse", "HEAD:apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json"]) != REJECTED_FIXTURE_BLOB:
        raise SystemExit("historical rejected fixture blob drift")

    r1 = subprocess.run(
        [sys.executable, "-B", "authoring/v4/validate_kit.py", "apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json", "--format=json"],
        cwd=ROOT, text=True, capture_output=True,
    )
    if r1.returncode == 0 or "lesson body is too small to be substantive learner-facing exposition" not in (r1.stdout + r1.stderr):
        raise SystemExit("R1 input contradiction did not reproduce specifically")
    print("STUDENT_V01_JOB07_R2_R1_INPUT_CONTRADICTION=PASS")

    run([sys.executable, "-B", "authoring/v4/tests/test_validate_v4.py", "-v"])

    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        kit = temp / "canonical-v4.json"
        mat = run([sys.executable, "-B", "pilot/student-v0.1/materialize_qualification_kit.py", "--output", str(kit)], capture=True)
        print(mat.stdout, end="")
        run([sys.executable, "-B", "authoring/v4/validate_kit.py", str(kit), "--format=json"])
        print("STUDENT_V01_JOB07_R2_GENERATED_KIT_CANONICAL=PASS")

        first = temp / "first.html"
        second = temp / "second.html"
        run([sys.executable, "-B", "apps/learnit-next/build.py", "--output", str(first)])
        run([sys.executable, "-B", "apps/learnit-next/build.py", "--output", str(second)])
        first_bytes = first.read_bytes()
        second_bytes = second.read_bytes()
        if first_bytes != second_bytes:
            raise SystemExit("canonical app double build is not byte-identical")
        if len(first_bytes) != APP_BYTES or hashlib.sha256(first_bytes).hexdigest() != APP_SHA:
            raise SystemExit("repaired app identity drift")
        print("STUDENT_V01_JOB07_R2_REPAIRED_APP_IDENTITY=PASS")

        run([sys.executable, "-B", "apps/learnit-next/build.py"])
        run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"])
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            chromium = Path(pw.chromium.executable_path)
        if not chromium.is_file():
            raise SystemExit("Playwright Chromium executable missing")
        run(["sudo", "ln", "-sf", str(chromium), "/usr/bin/chromium"])

        run([sys.executable, "-B", "pilot/student-v0.1/browser_generated_v4_probe.py", "--kit", str(kit)])

        run([sys.executable, "-B", "pilot/student-v0.1/test_pilot_package.py",
             "--app", "apps/learnit-next/dist/learnit-next.html", "--kit", str(kit)])
        package = temp / "pilot.zip"
        built = run([sys.executable, "-B", "pilot/student-v0.1/build_pilot_package.py",
                     "--app", "apps/learnit-next/dist/learnit-next.html", "--kit", str(kit), "--output", str(package)],
                    capture=True)
        print(built.stdout, end="")
        run([sys.executable, "-B", "pilot/student-v0.1/browser_pilot_package.py", "--package", str(package)])

        checks = [
            [sys.executable, "-B", "apps/learnit-next/tests/student_v01_served_v4_integration.py"],
            [sys.executable, "-B", "apps/learnit-next/tests/browser_student_v01_served_v4_integration.py"],
            [sys.executable, "-B", "apps/learnit-next/tests/student_v01_learning_runtime.py", "-v"],
            [sys.executable, "-B", "apps/learnit-next/tests/student_v01_activity_presentation.py"],
            [sys.executable, "-B", "apps/learnit-next/tests/browser_student_v01_activity_presentation.py"],
            [sys.executable, "-B", "apps/learnit-next/tests/student_v01_fanin_a.py"],
            [sys.executable, "-B", "authoring/v4/tests/test_validate_v4.py", "-v"],
            [sys.executable, "-B", "authoring/v2/atlas/tests/test_pedagogical_quality.py", "-v"],
            [sys.executable, "-B", "authoring/factory/tests/test_student_v01_v4.py", "-v"],
            [sys.executable, "-B", "apps/learnit-next/tests/atlas_m1_int.py", "-v"],
            [sys.executable, "-B", "apps/learnit-next/tests/atlas_m2_ux_clarity.py", "-v"],
        ]
        for check in checks:
            run(check)

    print("STUDENT_V01_JOB07_R2_REPAIRED_PRODUCT_REGRESSION=PASS")
    print("STUDENT_V01_JOB07_R2_SCOPE=PASS")
    print("STUDENT_V01_JOB07_R2_EXACT_ROUTE=PASS")
    print(f"STUDENT_V01_JOB07_R2_TARGET={target}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
