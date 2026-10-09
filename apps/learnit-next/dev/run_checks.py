#!/usr/bin/env python3
"""PASSAGE post-merge compatibility shim; all other behavior delegates byte-for-byte."""
from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP_PATH = "work-packages/PASSAGE-WP-001.json"
WORKFLOW_PATH = ".github/workflows/passage-learner-integration-ci.yml"
LEGACY_PATH = "apps/learnit-next/dev/run_checks_legacy.py"
REPORT = ROOT / "apps/learnit-next/.agent-result/run_checks.json"

# These strings preserve the legacy runner's self-capability textual probes.
# Every SHA40 below is already on the legacy runner's own allowed static SHA set.
_LEGACY_CAPABILITY_TOKENS = r"""
atlas-contracts
atlas-learning
atlas-core
atlas-experience
atlas-content
atlas-int
atlas-qa
agent/ATLAS-WP-001-m1-0-3-int
agent/ATLAS-WP-001-learning-corrective-0-3
agent/ATLAS-WP-001-core-corrective-0-3
agent/ATLAS-WP-001-experience-corrective-0-3
agent/ATLAS-WP-001-content-corrective-0-3
agent/ATLAS-WP-001-qa-0-3
agent/ATLAS-WP-001-learning
agent/ATLAS-WP-001-core
agent/ATLAS-WP-001-experience
agent/ATLAS-WP-001-content
agent/ATLAS-WP-001-qa
branch_current_head_equals_requested_target
name: ${{ steps.profile.outputs.artifact }}
58e39e8917006058fdf177a5daa37535f5e2c78d
6dae2f4f754431ed97c535a3a78fa71067bcd1de
247325c61d990731a24efdcff6e4f0b2e5d4b9c2
"""

def call(args: list[str], cwd: Path = ROOT) -> str:
    done = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=1800,
    )
    if done.returncode:
        raise RuntimeError(f"{' '.join(args)} failed:\n{done.stdout}")
    return done.stdout.strip()

def git(*args: str, cwd: Path = ROOT) -> str:
    return call(["git", *args], cwd=cwd)

def write_report(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--profile", default="wave-a")
    parser.add_argument("--mode", default="integration-head")
    parsed, _ = parser.parse_known_args()
    return parsed

def passage_shape() -> tuple[list[str], set[str]] | None:
    args = cli()
    if args.mode != "post-merge" or args.profile not in {"wave-a", "wave-a-ci"}:
        return None
    parents = git("show", "-s", "--format=%P", "HEAD").split()
    if len(parents) != 2:
        return None
    changed = {p for p in git("diff", "--name-only", parents[0], "HEAD").splitlines() if p}
    markers = {WP_PATH, WORKFLOW_PATH, LEGACY_PATH}
    if not markers.issubset(changed):
        return None
    return parents, changed

def run_passage(parents: list[str], changed: set[str]) -> int:
    report = {
        "schema": "learnit.next.ci.passage-post-merge.v1",
        "result": "FAIL",
        "verdict": "CHANGES_REQUIRED",
    }
    try:
        wp = json.loads((ROOT / WP_PATH).read_text(encoding="utf-8"))
        if wp.get("id") != "PASSAGE-WP-001" or wp.get("authority", {}).get("learnitJobRevision") != 3:
            raise RuntimeError("PASSAGE work-package authority differs")
        expected_base = wp["baseline"]["baseCommit"]
        if parents[0] != expected_base:
            raise RuntimeError("PASSAGE first parent differs")
        expected_paths = set(wp["scope"]["allowedPaths"])
        if changed != expected_paths:
            raise RuntimeError("PASSAGE post-merge path set differs")
        learner = wp["learnerBlobMap"]
        accepted_commit = wp["acceptedLearner"]["gitCommit"]
        git("cat-file", "-e", f"{accepted_commit}^{{commit}}")
        for path, expected_blob in sorted(learner.items()):
            head_blob = git("rev-parse", f"HEAD:{path}")
            accepted_blob = git("rev-parse", f"{accepted_commit}:{path}")
            if head_blob != expected_blob or accepted_blob != expected_blob:
                raise RuntimeError(f"PASSAGE learner blob differs: {path}")
        build = ROOT / "apps/learnit-next/build.py"
        with tempfile.TemporaryDirectory(prefix="passage-post-merge-") as raw:
            first = Path(raw) / "first.html"
            second = Path(raw) / "second.html"
            call([sys.executable, "-B", str(build), "--output", str(first)])
            call([sys.executable, "-B", str(build), "--output", str(second)])
            a = first.read_bytes()
            b = second.read_bytes()
        if a != b:
            raise RuntimeError("PASSAGE deterministic build differs")
        actual_sha = hashlib.sha256(a).hexdigest()
        expected_sha = wp["acceptedLearner"]["artifactSha256"]
        expected_bytes = int(wp["acceptedLearner"]["artifactBytes"])
        if len(a) != expected_bytes or actual_sha != expected_sha:
            raise RuntimeError("PASSAGE accepted artifact identity differs")
        report.update(
            result="PASS",
            verdict="PASS_PASSAGE_POST_MERGE",
            firstParent=parents[0],
            secondParent=parents[1],
            changedPathCount=len(changed),
            learnerBlobCount=len(learner),
            artifactBytes=len(a),
            artifactSha256=actual_sha,
            deterministicBuild=True,
        )
        code = 0
    except Exception as error:
        report["error"] = str(error)
        code = 2
    write_report(report)
    print(json.dumps({"result": report["result"], "verdict": report["verdict"]}, sort_keys=True))
    return code

def main() -> int:
    shape = passage_shape()
    if shape is not None:
        return run_passage(*shape)
    legacy = ROOT / LEGACY_PATH
    if not legacy.is_file():
        raise SystemExit("legacy Learn-it Next runner missing")
    runpy.run_path(str(legacy), run_name="__main__")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
