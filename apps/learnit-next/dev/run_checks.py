#!/usr/bin/env python3
"""Exact CI routing for historical Wave A and Project Atlas M1 lanes."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT.parents[3] if len(SCRIPT.parents) > 3 else Path.cwd()
ROOT = Path(os.environ.get("LEARNIT_REPO_ROOT", DEFAULT_ROOT)).resolve()
REPORT = ROOT / "apps/learnit-next/.agent-result/run_checks.json"
WAVE_A_BASE = "8ebafee48cc5277b92776982639a0146ae7e76d0"
ATLAS_BASE = "58e39e8917006058fdf177a5daa37535f5e2c78d"
RUNNER_PATH = "apps/learnit-next/dev/run_checks.py"

ATLAS = {
    "atlas-support": (
        "agent/ATLAS-WP-001-support-governance-ci",
        {
            "governance/governor-state.json",
            ".github/workflows/learnit-next-ci.yml",
            RUNNER_PATH,
        },
        (("tools/validate_repository.py",),),
        {},
        "READY_FOR_SUPPORT_REVIEW",
    ),
    "atlas-learning": (
        "agent/ATLAS-WP-001-learning",
        {
            "apps/learnit-next/src/core/atlas_evidence.js",
            "apps/learnit-next/src/core/atlas_recommendation.js",
            "apps/learnit-next/src/core/atlas_planner.js",
            "apps/learnit-next/tests/atlas_m1_learning.py",
        },
        (("apps/learnit-next/tests/atlas_m1_learning.py",),),
        {},
        "READY_FOR_LANE_REVIEW",
    ),
    "atlas-experience": (
        "agent/ATLAS-WP-001-experience",
        {
            "apps/learnit-next/src/ui/atlas_today.js",
            "apps/learnit-next/src/ui/atlas_session.js",
            "apps/learnit-next/src/ui/atlas_summary.js",
            "apps/learnit-next/src/ui/atlas_rewards.js",
            "apps/learnit-next/src/atlas.css",
            "apps/learnit-next/tests/atlas_m1_experience.py",
        },
        (("apps/learnit-next/tests/atlas_m1_experience.py",),),
        {"ATLAS_EXPERIENCE_STRICT": "1"},
        "READY_FOR_LANE_REVIEW",
    ),
    "atlas-core": (
        "agent/ATLAS-WP-001-core",
        {
            "apps/learnit-next/src/core/atlas_events.js",
            "apps/learnit-next/src/core/atlas_projection.js",
            "apps/learnit-next/src/core/atlas_clock.js",
            "apps/learnit-next/src/ports/atlas_storage.js",
            "apps/learnit-next/src/adapters/atlas_indexeddb.js",
            "apps/learnit-next/tests/atlas_m1_core.py",
        },
        (("apps/learnit-next/tests/atlas_m1_core.py",),),
        {},
        "READY_FOR_LANE_REVIEW",
    ),
    "atlas-content": (
        "agent/ATLAS-WP-001-content",
        {
            "authoring/v2/atlas/README.md",
            "authoring/v2/atlas/nombres_complexes_atlas.json",
            "authoring/v2/atlas/signaux_electriques_atlas.json",
            "authoring/v2/atlas/validate_atlas_content.py",
            "apps/learnit-next/tests/atlas_m1_content.py",
        },
        (
            ("authoring/v2/atlas/validate_atlas_content.py",),
            ("apps/learnit-next/tests/atlas_m1_content.py",),
        ),
        {},
        "READY_FOR_LANE_REVIEW",
    ),
    "atlas-qa": (
        "agent/ATLAS-WP-001-qa",
        {
            "apps/learnit-next/tests/qa_atlas_m1.py",
            "contracts/fixtures/atlas-m1-valid-loop.json",
            "contracts/fixtures/atlas-m1-invalid-loop.json",
        },
        (("apps/learnit-next/tests/qa_atlas_m1.py",),),
        {},
        "PRE_CANDIDATE_QA_READY",
    ),
}

ATLAS_BRANCHES = {config[0]: profile for profile, config in ATLAS.items()}
WAVE_A_BRANCHES = {
    "agent/PROG-WP-001-wave-a-learning",
    "agent/PROG-WP-001-wave-a-ux",
    "agent/PROG-WP-001-wave-a-authoring",
    "agent/PROG-WP-001-wave-a-platform",
    "agent/PROG-WP-001-wave-a-qa",
    "agent/PROG-WP-001-wave-a-int",
}


class GateError(RuntimeError):
    pass


def call(command: list[str], env: dict[str, str] | None = None, cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env={**os.environ, **(env or {}), "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=1800,
    )
    if completed.returncode:
        raise GateError(f"{' '.join(command)} failed:\n{completed.stdout}")
    return completed.stdout.strip()


def git(*args: str) -> str:
    return call(["git", *args])


def resolve(branch: str) -> str:
    if branch in ATLAS_BRANCHES:
        return ATLAS_BRANCHES[branch]
    if branch in WAVE_A_BRANCHES:
        return "wave-a"
    raise GateError(f"unrecognized CI branch: {branch}")


def routing_matrix() -> dict[str, object]:
    atlas = {branch: resolve(branch) for branch in sorted(ATLAS_BRANCHES)}
    historical = {branch: resolve(branch) for branch in sorted(WAVE_A_BRANCHES)}
    try:
        resolve("agent/UNKNOWN-WP-999-example")
    except GateError:
        return {"atlas": atlas, "historical": historical, "unknownBranchRejected": True}
    raise GateError("unknown branch routing is not fail-closed")


def atlas_provenance(profile: str, branch: str, base_ref: str) -> dict[str, object]:
    expected_branch, paths, _, _, _ = ATLAS[profile]
    if branch != expected_branch:
        raise GateError(f"Atlas branch/profile mismatch: {branch} != {expected_branch}")
    if base_ref != ATLAS_BASE or git("rev-parse", base_ref) != ATLAS_BASE:
        raise GateError("Atlas support base differs")
    if git("merge-base", ATLAS_BASE, "HEAD") != ATLAS_BASE:
        raise GateError("Atlas branch merge-base differs")
    changed = set(filter(None, git("diff", "--name-only", f"{ATLAS_BASE}...HEAD").splitlines()))
    if changed != paths:
        detail = {"expected": sorted(paths), "actual": sorted(changed)}
        raise GateError("Atlas path set differs: " + json.dumps(detail, sort_keys=True))
    return {
        "base": ATLAS_BASE,
        "branch": branch,
        "head": git("rev-parse", "HEAD"),
        "changedPaths": sorted(changed),
    }


def run_atlas(profile: str, branch: str, base_ref: str) -> int:
    report: dict[str, object] = {
        "schema": "learnit.next.ci.checks.atlas-m1.v1",
        "workPackage": "ATLAS-WP-001",
        "profile": profile,
        "result": "FAIL",
        "verdict": "CHANGES_REQUIRED",
    }
    try:
        report["provenance"] = atlas_provenance(profile, branch, base_ref)
        _, _, commands, environment, verdict = ATLAS[profile]
        if profile == "atlas-support":
            report["routingMatrix"] = routing_matrix()
        outputs = []
        for arguments in commands:
            command = [sys.executable, *arguments]
            outputs.append({"command": command, "output": call(command, environment)})
        report.update(result="PASS", verdict=verdict, tests=outputs)
        code = 0
    except Exception as error:
        report["error"] = str(error)
        code = 2
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "verdict": report["verdict"]}, sort_keys=True))
    return code


def legacy_namespace() -> dict[str, object]:
    """Load the unmodified Wave A gate from the exact Atlas support base."""
    source = git("show", f"{ATLAS_BASE}:{RUNNER_PATH}")
    namespace: dict[str, object] = {
        "__file__": str(ROOT / RUNNER_PATH),
        "__name__": "learnit_wave_a_legacy_gate",
    }
    exec(compile(source, str(namespace["__file__"]), "exec"), namespace)
    return namespace


def load_manifest():
    """Backward-compatible materialization API used by the historical workflow."""
    return legacy_namespace()["load_manifest"]()


def materialize(destination, manifest):
    """Backward-compatible materialization API used by the historical workflow."""
    return legacy_namespace()["materialize"](destination, manifest)


def run_wave_a(args: argparse.Namespace) -> int:
    """Execute the exact historical gate stored at the Atlas support base."""
    namespace = legacy_namespace()
    legacy_argv = [str(namespace["__file__"])]
    if args.strict:
        legacy_argv.append("--strict")
    legacy_argv.extend(["--mode", args.mode, "--base-ref", args.base_ref])
    if args.accepted_integration_head:
        legacy_argv.extend(["--accepted-integration-head", args.accepted_integration_head])
    original = sys.argv
    try:
        sys.argv = legacy_argv
        return int(namespace["main"]())
    finally:
        sys.argv = original


def run_wave_a_ci(args: argparse.Namespace) -> int:
    """Preserve the historical Wave A gate, fixed profiles and exact QA replay."""
    if run_wave_a(args):
        return 2
    result_dir = ROOT / "apps/learnit-next/.agent-result"
    result_dir.mkdir(parents=True, exist_ok=True)
    profiles = ("authoring", "contract", "full", "browser")
    for name in profiles:
        environment = {}
        if name in {"full", "browser"}:
            environment["LLV2_QA_STRICT"] = "1"
        if name == "browser":
            environment["LLV2_QA_BROWSER_STRICT"] = "1"
        call(
            [
                sys.executable,
                "tools/learnit_next_agent.py",
                "--profile",
                f"learnit-next-{name}",
                "--output",
                f"apps/learnit-next/.agent-result/profile-{name}.json",
            ],
            environment,
        )

    artifact = ROOT / "apps/learnit-next/dist/learnit-next.html"
    if not artifact.is_file():
        raise GateError("exact Wave A artifact is absent")
    before = artifact.read_bytes()
    namespace = legacy_namespace()
    import tempfile
    with tempfile.TemporaryDirectory(prefix="wave-a-qa-") as raw:
        product = namespace["materialize"](Path(raw), namespace["load_manifest"]()).resolve()
        qa_path = Path("apps/learnit-next/tests/qa_learning_loop_v2.py")
        expected = git("rev-parse", f"f25da6356528824e84224718013a3bccb2707c49:{qa_path.as_posix()}")
        actual = call(["git", "hash-object", str(product / qa_path)])
        if expected != "514d095b5fa028d12dc6d87ba7d4bd82c64a0cd9" or actual != expected:
            raise GateError("exact QA blob differs")
        environment = {
            "LLV2_PRODUCT_TREE": str(product),
            "LEARNIT_NEXT_ARTIFACT": str(artifact),
            "LLV2_QA_STRICT": "1",
            "LLV2_QA_BROWSER_STRICT": "1",
        }
        log = call([sys.executable, str(qa_path), "-v"], environment, cwd=product)
        (result_dir / "qa-exact.log").write_text(log + "\n", encoding="utf-8")
        if call(["git", "hash-object", str(product / qa_path)]) != expected:
            raise GateError("exact QA blob changed during replay")
    if artifact.read_bytes() != before:
        raise GateError("exact Wave A artifact changed during QA replay")

    reports = {}
    for name in profiles:
        payload = json.loads((result_dir / f"profile-{name}.json").read_text(encoding="utf-8"))
        if payload.get("result") != "PASS":
            raise GateError(f"profile failed: {name}")
        reports[name] = payload
    gate = json.loads(REPORT.read_text(encoding="utf-8"))
    if gate.get("result") != "PASS":
        raise GateError("historical integration gate failed")
    identity = {key: gate["artifact"][key] for key in ("path", "bytes", "sha256")}
    for name in ("full", "browser"):
        if reports[name].get("artifact") != identity:
            raise GateError(f"profile artifact differs: {name}")
    print(json.dumps({"result": "PASS", "verdict": gate["verdict"]}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--mode", default="integration-head")
    parser.add_argument("--base-ref", default=WAVE_A_BASE)
    parser.add_argument("--accepted-integration-head", default="")
    parser.add_argument("--profile", default="wave-a")
    parser.add_argument("--branch-ref", default="")
    parser.add_argument("--resolve-branch", default="")
    args = parser.parse_args()
    if args.resolve_branch:
        try:
            print(resolve(args.resolve_branch))
            return 0
        except GateError as error:
            print(str(error), file=sys.stderr)
            return 2
    if args.profile == "wave-a":
        return run_wave_a(args)
    if args.profile == "wave-a-ci":
        return run_wave_a_ci(args)
    if args.profile not in ATLAS:
        print(f"unsupported Atlas profile: {args.profile}", file=sys.stderr)
        return 2
    return run_atlas(args.profile, args.branch_ref, args.base_ref)


if __name__ == "__main__":
    raise SystemExit(main())
