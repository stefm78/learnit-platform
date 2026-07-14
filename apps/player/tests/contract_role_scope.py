#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from support import ROOT

TOOL = ROOT / "dev/role_scope_report.py"
REPORT = ROOT / "reports/contract_role_scope_report.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("role_scope_report", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def fixture():
    return {
        "roleScopes": {
            "developerWritePaths": ["src/developer.py"],
            "qaWritePaths": ["tests/**"],
            "integratorWritePaths": ["dev/registry.json"],
            "governorWritePaths": ["work-packages/**"],
        }
    }


def main() -> int:
    tool = load_tool()
    checks = []

    def add(code: str, ok: bool, detail: object = "") -> None:
        checks.append({"code": code, "ok": bool(ok), "detail": detail})

    valid_paths = [
        "src/developer.py",
        "tests/contract_example.py",
        "dev/registry.json",
        "work-packages/ARC-WP-999.json",
    ]
    valid = tool.evaluate(fixture(), valid_paths)
    add("valid-four-role-assignment", valid["ok"] and valid["summary"]["ownedExactlyOnce"] == 4, valid)

    exact_overlap = fixture()
    exact_overlap["roleScopes"]["qaWritePaths"] = ["src/developer.py"]
    exact_report = tool.evaluate(exact_overlap, ["src/developer.py"])
    add("reject-exact-overlap", not exact_report["ok"] and len(exact_report["duplicatePatterns"]) == 1, exact_report)

    glob_overlap = fixture()
    glob_overlap["roleScopes"]["developerWritePaths"] = ["src/**"]
    glob_overlap["roleScopes"]["qaWritePaths"] = ["src/developer.py"]
    glob_report = tool.evaluate(glob_overlap, ["src/developer.py"])
    add("reject-glob-overlap", not glob_report["ok"] and len(glob_report["multiplyOwnedPaths"]) == 1, glob_report)

    unowned = tool.evaluate(fixture(), ["unowned/file.txt"])
    add("reject-unowned-path", not unowned["ok"] and unowned["unownedPaths"] == ["unowned/file.txt"], unowned)

    malformed_cases = []
    duplicate = fixture()
    duplicate["roleScopes"]["developerWritePaths"] = ["src/a.py", "src/a.py"]
    malformed_cases.append(("duplicate-pattern", duplicate))
    missing = fixture()
    del missing["roleScopes"]["governorWritePaths"]
    malformed_cases.append(("missing-role", missing))
    empty = fixture()
    empty["roleScopes"]["qaWritePaths"] = []
    malformed_cases.append(("empty-role", empty))
    wrong_type = fixture()
    wrong_type["roleScopes"]["integratorWritePaths"] = "dev/registry.json"
    malformed_cases.append(("wrong-role-type", wrong_type))
    extra = fixture()
    extra["roleScopes"]["observerWritePaths"] = ["docs/**"]
    malformed_cases.append(("unexpected-role", extra))
    for code, work_package in malformed_cases:
        try:
            tool.evaluate(work_package, valid_paths)
            raised = False
        except tool.ScopeError:
            raised = True
        add("reject-" + code, raised)

    invalid_paths = ["", "/absolute/path", "../escape", "src/../escape", "C:/absolute", "src//double"]
    for path in invalid_paths:
        try:
            tool.evaluate(fixture(), [path])
            raised = False
        except tool.ScopeError:
            raised = True
        add("reject-path-" + (path or "empty"), raised)

    reordered = {
        "roleScopes": {
            "governorWritePaths": ["work-packages/**"],
            "integratorWritePaths": ["dev/registry.json"],
            "qaWritePaths": ["tests/**"],
            "developerWritePaths": ["src/developer.py"],
        }
    }
    deterministic_a = tool.canonical_json(tool.evaluate(fixture(), valid_paths))
    deterministic_b = tool.canonical_json(tool.evaluate(reordered, list(reversed(valid_paths))))
    add("deterministic-canonical-output", deterministic_a == deterministic_b)

    with tempfile.TemporaryDirectory() as raw:
        temp = Path(raw)
        wp_path = temp / "work-package.json"
        paths_path = temp / "paths.json"
        output_path = temp / "report.json"
        wp_path.write_text(json.dumps(fixture()), encoding="utf-8")
        paths_path.write_text(json.dumps(valid_paths), encoding="utf-8")
        valid_cli = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--work-package",
                str(wp_path),
                "--paths-json",
                str(paths_path),
                "--output",
                str(output_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        add(
            "cli-valid-and-explicit-output",
            valid_cli.returncode == 0 and output_path.exists() and json.loads(output_path.read_text())["ok"],
            {"returncode": valid_cli.returncode, "stderr": valid_cli.stderr[-500:]},
        )

        no_output = temp / "implicit.json"
        implicit_cli = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--work-package",
                str(wp_path),
                "--path",
                "src/developer.py",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        add("cli-no-implicit-output", implicit_cli.returncode == 0 and not no_output.exists())

        paths_path.write_text(json.dumps(["unowned/file.txt"]), encoding="utf-8")
        invalid_cli = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--work-package",
                str(wp_path),
                "--paths-json",
                str(paths_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        add("cli-invalid-ownership-nonzero", invalid_cli.returncode == 1 and not json.loads(invalid_cli.stdout)["ok"])

        paths_path.write_text(json.dumps(["../escape"]), encoding="utf-8")
        malformed_cli = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--work-package",
                str(wp_path),
                "--paths-json",
                str(paths_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        add("cli-malformed-input-nonzero", malformed_cli.returncode == 2 and '"ok": false' in malformed_cli.stderr)

    ok = all(item["ok"] for item in checks)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {
                "schema": "learnit.stage_d_role_scope_contract.v1",
                "ok": ok,
                "checks": checks,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": ok,
                "passed": sum(item["ok"] for item in checks),
                "total": len(checks),
                "report": str(REPORT.relative_to(ROOT)),
            },
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
