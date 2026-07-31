#!/usr/bin/env python3
"""Fail-closed CI router for historical Wave A and Atlas 0.3 corrective lanes."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT.parents[3] if len(SCRIPT.parents) > 3 else Path.cwd()
ROOT = Path(os.environ.get("LEARNIT_REPO_ROOT", DEFAULT_ROOT)).resolve()
RUNNER_PATH = "apps/learnit-next/dev/run_checks.py"
WORKFLOW_PATH = ".github/workflows/learnit-next-ci.yml"
WAVE_A_BASE = "8ebafee48cc5277b92776982639a0146ae7e76d0"
CONTRACT_EVIDENCE_BASE = "58e39e8917006058fdf177a5daa37535f5e2c78d"
CORRECTIVE_COMMON_BASELINE = "6dae2f4f754431ed97c535a3a78fa71067bcd1de"
CONTRACT_HEAD = "f41de5043a22f8559a3b6a0d71654fbd542b5ec6"
CONTRACT_BRANCH = "agent/ATLAS-WP-001-contracts-0-3"
SUPPORT_BRANCH = "agent/ATLAS-WP-001-support-governance-ci"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

CORRECTIVE = {
    "atlas-learning": ("agent/ATLAS-WP-001-learning-corrective-0-3", "0db8d3b929c74b605cbcfea2135fda40fbd72fdd"),
    "atlas-core": ("agent/ATLAS-WP-001-core-corrective-0-3", "7aca506a7b243f6a6ee64dbda634dad0f98dc01a"),
    "atlas-experience": ("agent/ATLAS-WP-001-experience-corrective-0-3", "aecae5700867c3f9a918c5b86acf3bda9d13b7ce"),
    "atlas-content": ("agent/ATLAS-WP-001-content-corrective-0-3", "8a00e8bc1179c94ed3e0bd110d5a19794768e86c"),
    "atlas-qa": ("agent/ATLAS-WP-001-qa-0-3", "4109b1fd7e89d62c14d074b67f64aad65991ca7b"),
}
HISTORICAL = {
    "agent/ATLAS-WP-001-learning": "atlas-learning",
    "agent/ATLAS-WP-001-core": "atlas-core",
    "agent/ATLAS-WP-001-experience": "atlas-experience",
    "agent/ATLAS-WP-001-content": "atlas-content",
    "agent/ATLAS-WP-001-qa": "atlas-qa",
}
WAVE_A_BRANCHES = {
    "agent/PROG-WP-001-wave-a-learning", "agent/PROG-WP-001-wave-a-ux",
    "agent/PROG-WP-001-wave-a-authoring", "agent/PROG-WP-001-wave-a-platform",
    "agent/PROG-WP-001-wave-a-qa", "agent/PROG-WP-001-wave-a-int",
}
CORRECTIVE_BY_BRANCH = {branch: profile for profile, (branch, _) in CORRECTIVE.items()}
ATLAS_BRANCHES = {CONTRACT_BRANCH: "atlas-contracts", SUPPORT_BRANCH: "atlas-support", **HISTORICAL, **CORRECTIVE_BY_BRANCH}


class RoutingError(RuntimeError):
    pass


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=1800)
    if result.returncode:
        raise RoutingError(f"git {' '.join(args)} failed:\n{result.stdout}")
    return result.stdout.strip()


def resolve(branch: str) -> str:
    if branch in ATLAS_BRANCHES:
        return ATLAS_BRANCHES[branch]
    if branch in WAVE_A_BRANCHES:
        return "wave-a"
    raise RoutingError(f"unrecognized CI branch: {branch}")


def baseline(branch: str) -> str:
    if branch == CONTRACT_BRANCH or branch in HISTORICAL:
        return CONTRACT_EVIDENCE_BASE
    if branch == SUPPORT_BRANCH or branch in CORRECTIVE_BY_BRANCH:
        return CORRECTIVE_COMMON_BASELINE
    if branch in WAVE_A_BRANCHES:
        return WAVE_A_BASE
    raise RoutingError(f"no baseline for CI branch: {branch}")


def reject(callback: Any, fragment: str) -> str:
    try:
        callback()
    except RoutingError as error:
        if fragment in str(error):
            return "PASS_REJECTED"
        raise
    raise RoutingError(f"expected rejection: {fragment}")


def profile_branch(profile: str, branch: str) -> None:
    routed = resolve(branch)
    if routed != profile:
        raise RoutingError(f"Atlas branch/profile mismatch: {branch} routes to {routed}, not {profile}")


def exact_paths(actual: set[str], expected: set[str]) -> None:
    if actual != expected:
        raise RoutingError("Atlas path set differs: " + json.dumps({"actual": sorted(actual), "expected": sorted(expected)}))


def frozen() -> dict[str, Any]:
    if not SHA40.fullmatch(CORRECTIVE_COMMON_BASELINE):
        raise RoutingError("corrective baseline is not an exact SHA")
    source = git("show", f"{CORRECTIVE_COMMON_BASELINE}:{RUNNER_PATH}")
    namespace: dict[str, Any] = {"__file__": str(ROOT / RUNNER_PATH), "__name__": "learnit_frozen_runner"}
    exec(compile(source, str(namespace["__file__"]), "exec"), namespace)
    if namespace.get("CONTRACT_HEAD") != CONTRACT_HEAD:
        raise RoutingError("frozen runner contract head differs")
    return namespace


def matrix() -> dict[str, Any]:
    namespace = frozen()
    old_atlas = namespace["ATLAS"]
    corrective, heads = {}, {}
    for profile, (branch, expected_head) in sorted(CORRECTIVE.items()):
        if resolve(branch) != profile or baseline(branch) != CORRECTIVE_COMMON_BASELINE:
            raise RoutingError(f"corrective route differs: {branch}")
        actual = git("rev-parse", f"refs/remotes/origin/{branch}")
        if actual != expected_head:
            raise RoutingError(f"corrective head moved: {branch}: {actual} != {expected_head}")
        corrective[branch] = {"profile": profile, "base": CORRECTIVE_COMMON_BASELINE}
        heads[branch] = actual
    historical = {branch: {"profile": profile, "base": baseline(branch)} for branch, profile in sorted(HISTORICAL.items())}
    if baseline(CONTRACT_BRANCH) != CONTRACT_EVIDENCE_BASE:
        raise RoutingError("atlas-contracts baseline differs")
    learning_paths = set(old_atlas["atlas-learning"][1])
    negatives = {
        "unknownBranchRejected": reject(lambda: resolve("agent/UNKNOWN-WP-999-example"), "unrecognized CI branch"),
        "profileBranchMismatchRejected": reject(lambda: profile_branch("atlas-core", CORRECTIVE["atlas-learning"][0]), "branch/profile mismatch"),
        "allowlistExcessRejected": reject(lambda: exact_paths(learning_paths | {"unexpected/path"}, learning_paths), "path set differs"),
        "allowlistDeficitRejected": reject(lambda: exact_paths(set(sorted(learning_paths)[1:]), learning_paths), "path set differs"),
    }
    return {"contract": {CONTRACT_BRANCH: {"profile": "atlas-contracts", "base": CONTRACT_EVIDENCE_BASE}},
            "corrective": corrective, "historical": historical,
            "waveA": {branch: "wave-a" for branch in sorted(WAVE_A_BRANCHES)},
            "negativeTests": negatives, "preservedLaneHeads": heads}


def capability() -> dict[str, Any]:
    workflow = (ROOT / WORKFLOW_PATH).read_text(encoding="utf-8")
    runner = (ROOT / RUNNER_PATH).read_text(encoding="utf-8")
    tokens = {"atlas-contracts", "atlas-learning", "atlas-core", "atlas-experience", "atlas-content", "atlas-qa",
              CONTRACT_EVIDENCE_BASE, CORRECTIVE_COMMON_BASELINE,
              "learnit-next-${{ steps.profile.outputs.name }}-${{ steps.target.outputs.target }}",
              *CORRECTIVE_BY_BRANCH, *HISTORICAL}
    missing = [f"workflow:{token}" for token in tokens if token not in workflow]
    missing += [f"runner:{token}" for token in {CONTRACT_EVIDENCE_BASE, CORRECTIVE_COMMON_BASELINE, *CORRECTIVE_BY_BRANCH, *HISTORICAL} if token not in runner]
    if missing:
        raise RoutingError("corrective CI capability incomplete: " + json.dumps(sorted(missing)))
    return {"contractEvidenceBase": CONTRACT_EVIDENCE_BASE, "correctiveCommonBaseline": CORRECTIVE_COMMON_BASELINE,
            "contractHead": CONTRACT_HEAD, "dispatchProfiles": sorted(CORRECTIVE),
            "routingSelfTest": matrix(), "failClosed": True}


def patch(namespace: dict[str, Any], profile: str) -> None:
    namespace["ATLAS_BASE"] = CORRECTIVE_COMMON_BASELINE
    atlas = namespace["ATLAS"]
    current = atlas[profile]
    branch = SUPPORT_BRANCH if profile == "atlas-support" else CORRECTIVE[profile][0]
    if profile == "atlas-support":
        paths = {WORKFLOW_PATH, RUNNER_PATH}
    elif profile == "atlas-qa":
        paths = {"apps/learnit-next/tests/qa_atlas_m1.py"}
    else:
        paths = set(current[1])
    atlas[profile] = (branch, paths, current[2], current[3], current[4])
    namespace["ATLAS_BRANCHES"] = {item[0]: name for name, item in atlas.items()}
    if profile == "atlas-support":
        namespace["routing_matrix"] = matrix
        namespace["support_contract_capability"] = capability


def run_atlas(args: argparse.Namespace) -> int:
    try:
        if not args.branch_ref:
            raise RoutingError("Atlas profile requires --branch-ref")
        profile_branch(args.profile, args.branch_ref)
        expected = baseline(args.branch_ref)
        if args.base_ref != expected:
            raise RoutingError(f"baseline mismatch: {args.base_ref} != {expected}")
        namespace = frozen()
        if args.branch_ref == SUPPORT_BRANCH or args.branch_ref in CORRECTIVE_BY_BRANCH:
            patch(namespace, args.profile)
        return int(namespace["run_atlas"](args.profile, args.branch_ref, args.base_ref))
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--mode", default="integration-head")
    parser.add_argument("--base-ref", default=WAVE_A_BASE)
    parser.add_argument("--accepted-integration-head", default="")
    parser.add_argument("--profile", default="wave-a")
    parser.add_argument("--branch-ref", default="")
    parser.add_argument("--resolve-branch", default="")
    parser.add_argument("--routing-self-test", action="store_true")
    args = parser.parse_args()
    if args.resolve_branch:
        try:
            print(resolve(args.resolve_branch)); return 0
        except RoutingError as error:
            print(str(error), file=sys.stderr); return 2
    if args.routing_self_test:
        try:
            print(json.dumps(matrix(), indent=2, sort_keys=True)); return 0
        except RoutingError as error:
            print(str(error), file=sys.stderr); return 2
    if args.profile in {"wave-a", "wave-a-ci"}:
        return int(frozen()["main"]())
    if args.profile not in {"atlas-support", "atlas-contracts", *CORRECTIVE}:
        print(f"unsupported Atlas profile: {args.profile}", file=sys.stderr); return 2
    return run_atlas(args)


if __name__ == "__main__":
    raise SystemExit(main())
