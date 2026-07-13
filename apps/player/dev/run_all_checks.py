#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import importlib.metadata
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor

from release_utils import ROOT, load_config, load_manifest, load_registry, rc_slug, sha256_file, utc_now

CHECK_TIMEOUT_SECONDS = 45
PROGRESS_LOG = ROOT / "reports" / "check_progress.log"
MANIFEST_PATH = ROOT / "source_manifest.json"
REGISTRY_PATH = ROOT / "dev" / "checks_registry.json"

for extra in (ROOT / "tests", ROOT):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))


def _terminate_process_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        return


def run_script(script: str) -> dict:
    started = utc_now()
    PROGRESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS_LOG.open("a", encoding="utf-8") as log:
        log.write(f"START {started} {script}\n")
    try:
        with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(mode="w+b") as stderr_file:
            result = subprocess.run(
                ["timeout", "--kill-after=3s", f"{CHECK_TIMEOUT_SECONDS}s", sys.executable, str(ROOT / script)],
                cwd=ROOT, stdout=stdout_file, stderr=stderr_file,
            )
            rc = result.returncode
            stdout_file.seek(0); stderr_file.seek(0)
            stdout = stdout_file.read().decode("utf-8", errors="replace")
            stderr = stderr_file.read().decode("utf-8", errors="replace")
            if rc == 124:
                stderr += f"\nTimed out after {CHECK_TIMEOUT_SECONDS} seconds."
    except Exception:
        rc, stdout, stderr = 1, "", traceback.format_exc()
    ended = utc_now()
    with PROGRESS_LOG.open("a", encoding="utf-8") as log:
        log.write(f"END {ended} {script} rc={rc}\n")
    return {
        "script": script, "startedAt": started, "endedAt": ended, "returncode": rc, "ok": rc == 0,
        "stdoutTail": stdout[-6000:], "stderrTail": stderr[-6000:], "reusedEvidence": False,
    }


def report_path_for_script(script: str) -> Path:
    stem = Path(script).stem
    special = {
        "contract_authoring_alignment": "authoring_alignment_report.json",
        "contract_architecture_inventory": "architecture_inventory.json",
        "contract_runtime_namespace": "runtime_namespace_audit.json",
    }
    if stem in special:
        return ROOT / "reports" / special[stem]
    return ROOT / "reports" / f"{stem}_report.json"


def dependency_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "missing"


def command_version(command: str) -> str:
    path = shutil.which(command)
    if not path:
        return "missing"
    try:
        result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
        return (result.stdout or result.stderr).strip().splitlines()[0]
    except Exception:
        return "unavailable"


def environment_fingerprint() -> dict:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "jsonschema": dependency_version("jsonschema"),
        "playwright": dependency_version("playwright"),
        "chromium": command_version("chromium") if shutil.which("chromium") else command_version("chromium-browser"),
    }


def expected_binding(script: str, artifact: Path) -> dict:
    test_path = ROOT / script
    return {
        "schema": "learnit.evidence_binding.v1",
        "artifactPath": str(artifact.relative_to(ROOT)),
        "artifactSha256": sha256_file(artifact),
        "testPath": script,
        "testSha256": sha256_file(test_path) if test_path.exists() else "",
        "sourceManifestSha256": sha256_file(MANIFEST_PATH),
        "checksRegistrySha256": sha256_file(REGISTRY_PATH),
    }


def binding_matches(actual: dict, expected: dict) -> bool:
    keys = ("artifactPath", "artifactSha256", "testPath", "testSha256", "sourceManifestSha256", "checksRegistrySha256")
    return isinstance(actual, dict) and all(actual.get(key) == expected.get(key) for key in keys)


def bind_generated_report(script: str, artifact: Path, step: dict) -> dict:
    report_path = report_path_for_script(script)
    binding = expected_binding(script, artifact)
    step.update({
        "evidenceBinding": binding,
        "evidenceBound": False,
        "testScriptSha256": binding["testSha256"],
        "testedArtifactSha256": binding["artifactSha256"],
        "sourceManifestSha256": binding["sourceManifestSha256"],
        "checksRegistrySha256": binding["checksRegistrySha256"],
    })
    if not report_path.exists():
        step["evidenceBindingError"] = f"missing evidence report: {report_path.relative_to(ROOT)}"
        return step
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        payload["evidenceBinding"] = binding
        payload["evidenceGeneratedAt"] = utc_now()
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        step.update({
            "evidenceReport": str(report_path.relative_to(ROOT)),
            "evidenceSha256": sha256_file(report_path),
            "evidenceBound": True,
        })
    except Exception:
        step["evidenceBindingError"] = traceback.format_exc()
    return step


def load_existing_report(script: str, artifact: Path) -> dict:
    started = utc_now()
    report_path = report_path_for_script(script)
    expected = expected_binding(script, artifact)
    if not report_path.exists():
        return {
            "script": script, "startedAt": started, "endedAt": utc_now(), "returncode": 1, "ok": False,
            "stdoutTail": "", "stderrTail": f"missing evidence report: {report_path.relative_to(ROOT)}",
            "reusedEvidence": True, "evidenceBound": False,
        }
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        fresh = report_path.stat().st_mtime >= artifact.stat().st_mtime
        bound = binding_matches(payload.get("evidenceBinding"), expected)
        ok = bool(payload.get("ok")) and fresh and bound
        return {
            "script": script,
            "startedAt": started,
            "endedAt": utc_now(),
            "returncode": 0 if ok else 1,
            "ok": ok,
            "stdoutTail": json.dumps({
                "evidence": str(report_path.relative_to(ROOT)), "schema": payload.get("schema"),
                "ok": payload.get("ok"), "generatedAfterArtifact": fresh, "bindingMatches": bound,
                "sha256": sha256_file(report_path),
            }, ensure_ascii=False),
            "stderrTail": "" if ok else "evidence missing, stale, failed, or not bound to current bytes",
            "reusedEvidence": True,
            "evidenceReport": str(report_path.relative_to(ROOT)),
            "evidenceSha256": sha256_file(report_path),
            "evidenceBinding": expected,
            "evidenceBound": bound,
            "testScriptSha256": expected["testSha256"],
            "testedArtifactSha256": expected["artifactSha256"],
            "sourceManifestSha256": expected["sourceManifestSha256"],
            "checksRegistrySha256": expected["checksRegistrySha256"],
        }
    except Exception:
        return {
            "script": script, "startedAt": started, "endedAt": utc_now(), "returncode": 1, "ok": False,
            "stdoutTail": "", "stderrTail": traceback.format_exc(), "reusedEvidence": True, "evidenceBound": False,
        }


def main() -> int:
    parser = ArgumentParser(description="Run the active Learn-it evidence registry.")
    parser.add_argument("--include-browser", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--artifact", default="dist/learnit.html")
    parser.add_argument("--reuse-browser-evidence", action="store_true", help="Reuse only reports cryptographically bound to the current artifact, test, manifest and registry.")
    parser.add_argument("--reuse-mandatory-evidence", action="store_true", help="Reuse only reports cryptographically bound to the current artifact, test, manifest and registry.")
    args = parser.parse_args()

    if PROGRESS_LOG.exists():
        PROGRESS_LOG.unlink()
    manifest = load_manifest()
    registry = load_registry()
    slug = rc_slug(manifest["rc"])
    artifact = Path(args.artifact)
    if not artifact.is_absolute():
        artifact = ROOT / artifact

    steps: list[dict] = []
    if not args.skip_build:
        steps.append(run_script(registry["build"]))
    if not artifact.exists():
        raise FileNotFoundError(f"tested artifact does not exist: {artifact}")

    before = {"path": str(artifact.relative_to(ROOT)), "bytes": artifact.stat().st_size, "sha256": sha256_file(artifact)}
    mandatory_scripts = registry.get("mandatory", [])
    if args.reuse_mandatory_evidence:
        mandatory = [load_existing_report(script, artifact) for script in mandatory_scripts]
    else:
        mandatory = [bind_generated_report(script, artifact, run_script(script)) for script in mandatory_scripts]

    browser_scripts = registry.get("browser", []) if args.include_browser else []
    if browser_scripts and args.reuse_browser_evidence:
        browser = [load_existing_report(script, artifact) for script in browser_scripts]
    elif browser_scripts:
        raw_browser = [run_script(script) for script in browser_scripts]
        browser = [bind_generated_report(step["script"], artifact, step) for step in raw_browser]
    else:
        browser = []

    steps.extend(mandatory + browser)
    after = {"path": before["path"], "bytes": artifact.stat().st_size, "sha256": sha256_file(artifact)}
    unchanged = before == after
    steps.append({
        "script": "tested-artifact-unchanged", "ok": unchanged, "returncode": 0 if unchanged else 1,
        "stdoutTail": json.dumps({"before": before, "after": after}), "stderrTail": "" if unchanged else "artifact changed during tests",
    })

    all_check_steps = mandatory + browser
    all_evidence_bound = all(step.get("evidenceBound") for step in all_check_steps)
    mandatory_ok = all(step["ok"] for step in mandatory) and unchanged and all(step.get("evidenceBound") for step in mandatory)
    browser_ok = all(step["ok"] and step.get("evidenceBound") for step in browser) if browser else None
    release_ready = mandatory_ok and all_evidence_bound and (browser_ok is True if registry.get("release_requires_browser") else browser_ok is not False)
    human_validation = load_config().get("human_validation", {})
    human_gate_required = bool(human_validation.get("required"))
    human_gate_status = str(human_validation.get("status") or "not-required")
    human_gate_passed = (not human_gate_required) or human_gate_status.lower().startswith(("pass", "validated", "complete"))
    promotion_ready = release_ready and human_gate_passed

    source_tree_report = ROOT / "reports" / "contract_source_tree_report.json"
    if source_tree_report.exists():
        metrics = json.loads(source_tree_report.read_text(encoding="utf-8"))
        metrics.update({"schema": f"learnit.{slug}.source_tree_metrics.v1", "generatedAt": utc_now()})
        target = ROOT / registry["reports"]["cleanliness"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": f"learnit.{slug}.aggregate_report.v1",
        "ok": mandatory_ok and browser_ok is not False,
        "releaseReady": release_ready,
        "automationReady": release_ready,
        "releaseReadyMeaning": "automated-evidence-and-package-candidate-only",
        "humanGateRequired": human_gate_required,
        "humanGateStatus": human_gate_status,
        "humanGatePassed": human_gate_passed,
        "promotionReady": promotion_ready,
        "mandatoryOk": mandatory_ok,
        "browserExecuted": bool(browser),
        "browserOk": browser_ok,
        "allEvidenceBound": all_evidence_bound,
        "evidencePolicy": "fresh-or-exact-binding-v1",
        "environment": environment_fingerprint(),
        "generatedAt": utc_now(),
        "registry": registry,
        "testedArtifact": after,
        "testedArtifactUnchanged": unchanged,
        "sourceManifestSha256": sha256_file(MANIFEST_PATH),
        "checksRegistrySha256": sha256_file(REGISTRY_PATH),
        "buildReport": json.loads((ROOT / "reports" / "build_report.json").read_text(encoding="utf-8")),
        "steps": steps,
        "summary": {
            "mandatory": {"total": len(mandatory) + 1, "passed": sum(s["ok"] and s.get("evidenceBound") for s in mandatory) + int(unchanged)},
            "browser": {"total": len(browser), "passed": sum(s["ok"] and s.get("evidenceBound") for s in browser)},
            "evidenceBound": {"total": len(all_check_steps), "passed": sum(bool(s.get("evidenceBound")) for s in all_check_steps)},
        },
    }
    out = ROOT / registry["reports"]["aggregate"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": report["ok"], "releaseReady": release_ready, "automationReady": release_ready, "promotionReady": promotion_ready, "allEvidenceBound": all_evidence_bound,
        "report": str(out.relative_to(ROOT)), "testedArtifact": after, "summary": report["summary"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
