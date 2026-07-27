#!/usr/bin/env python3
"""Run fixed Learn-it Next analysis and validation profiles on a materialized tree."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "apps/learnit-next/source_manifest.json"
RUN_CHECKS = ROOT / "apps/learnit-next/dev/run_checks.py"
ARTIFACT = Path("apps/learnit-next/dist/learnit-next.html")
PROFILES = {
    "learnit-next-snapshot",
    "learnit-next-fast",
    "learnit-next-full",
    "learnit-next-browser",
    "learnit-next-authoring",
    "learnit-next-contract",
}
IMPORT_RE = re.compile(
    r"\b(?:import|export)\s+(?:(?:[^'\";]*?)\s+from\s+)?['\"](?P<spec>[^'\"]+)['\"]"
)


class ProfileError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_run_checks():
    spec = importlib.util.spec_from_file_location("learnit_next_run_checks", RUN_CHECKS)
    if spec is None or spec.loader is None:
        raise ProfileError("cannot load apps/learnit-next/dev/run_checks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(command: list[str], cwd: Path, env: dict[str, str], timeout: int = 1200) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env={**os.environ, **env, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    return {
        "command": command,
        "returnCode": completed.returncode,
        "output": completed.stdout,
        "outputSha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
    }


def snapshot(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    source_root = root / "apps/learnit-next/src"
    modules = sorted(source_root.rglob("*.js"))
    edges: list[dict[str, str]] = []
    module_records = []
    for path in modules:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        imports = []
        for match in IMPORT_RE.finditer(text):
            spec = match.group("spec")
            imports.append(spec)
            edges.append({"from": rel, "specifier": spec})
        module_records.append(
            {
                "path": rel,
                "bytes": path.stat().st_size,
                "lines": text.count("\n") + 1,
                "imports": imports,
            }
        )
    tests = []
    for path in sorted((root / "apps/learnit-next/tests").glob("*.py")):
        tests.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
            }
        )
    owners: dict[str, list[str]] = {}
    for item in manifest.get("workingFiles", []):
        owners.setdefault(str(item.get("owner", "unknown")), []).append(str(item["path"]))
    return {
        "schema": "learnit.next.agent.snapshot.v1",
        "moduleCount": len(module_records),
        "modules": module_records,
        "dependencyEdges": edges,
        "tests": tests,
        "workingFileCount": len(manifest.get("workingFiles", [])),
        "owners": {key: sorted(value) for key, value in sorted(owners.items())},
        "compositionPoints": [
            path
            for path in (
                "apps/learnit-next/src/main.js",
                "apps/learnit-next/src/core/session.js",
                "apps/learnit-next/src/core/progress.js",
                "apps/learnit-next/src/ui/render.js",
                "apps/learnit-next/build.py",
                "apps/learnit-next/source_manifest.json",
            )
            if (root / path).is_file()
        ],
        "declaredArtifact": manifest.get("artifact"),
    }


def profile_commands(profile: str, root: Path) -> list[list[str]]:
    python = sys.executable
    build = [python, "apps/learnit-next/build.py"]
    contract = [python, "apps/learnit-next/tests/contract_v2.py", "-v"]
    storage = [python, "apps/learnit-next/tests/storage_isolation.py", "-v"]
    p1 = [python, "apps/learnit-next/tests/p1_corrective_review.py", "-v"]
    browser = [python, "apps/learnit-next/tests/browser_vertical_slice.py", "-v"]
    authoring = [
        python,
        "authoring/v2/validate_kit.py",
        "authoring/v2/golden/nombres_complexes.json",
        "authoring/v2/golden/signaux_electriques.json",
        "--foundation-profile",
        "--format",
        "json",
    ]
    if profile == "learnit-next-fast":
        return [build, contract, storage, p1]
    if profile == "learnit-next-full":
        return [
            build,
            [
                python,
                "-m",
                "unittest",
                "discover",
                "-s",
                "apps/learnit-next/tests",
                "-p",
                "*.py",
                "-v",
            ],
        ]
    if profile == "learnit-next-browser":
        return [build, browser, p1]
    if profile == "learnit-next-authoring":
        return [authoring]
    if profile == "learnit-next-contract":
        return [contract]
    if profile == "learnit-next-snapshot":
        return []
    raise ProfileError(f"unsupported profile: {profile}")


def execute(profile: str, output: Path) -> dict[str, Any]:
    if profile not in PROFILES:
        raise ProfileError(f"unsupported profile: {profile}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    run_checks = load_run_checks()
    report: dict[str, Any] = {
        "schema": "learnit.next.agent.profile.v1",
        "profile": profile,
        "result": "FAIL",
        "commands": [],
    }
    with tempfile.TemporaryDirectory(prefix="learnit-next-agent-") as raw:
        root = run_checks.materialize(Path(raw), manifest)
        report["snapshot"] = snapshot(root, manifest)
        env = {
            "LEARNIT_NEXT_ARTIFACT": str(root / ARTIFACT),
            "P1_PRODUCT_TREE": str(root),
            "P1_STRICT": "1",
        }
        for command in profile_commands(profile, root):
            result = run(command, root, env)
            report["commands"].append(result)
            if result["returnCode"] != 0:
                report["failure"] = {
                    "command": command,
                    "returnCode": result["returnCode"],
                }
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                return report
        built = root / ARTIFACT
        if built.is_file():
            destination = ROOT / ARTIFACT
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(built, destination)
            report["artifact"] = {
                "path": ARTIFACT.as_posix(),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        report["result"] = "PASS"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        report = execute(args.profile, output)
        print(json.dumps({"profile": args.profile, "result": report["result"], "report": output.relative_to(ROOT).as_posix()}, sort_keys=True))
        return 0 if report["result"] == "PASS" else 1
    except Exception as exc:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "schema": "learnit.next.agent.profile.v1",
                    "profile": args.profile,
                    "result": "FAIL",
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"LEARNIT_NEXT_PROFILE_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
