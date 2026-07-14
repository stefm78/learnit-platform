#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from support import ROOT

SELF = Path(__file__)


def main() -> int:
    registry = json.loads((ROOT / "dev/checks_registry.json").read_text(encoding="utf-8"))
    results = []
    for script in registry.get("browser", []):
        try:
            completed = subprocess.run(
                [sys.executable, str(ROOT / script)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            result = {
                "script": script,
                "returncode": completed.returncode,
                "stdoutTail": completed.stdout[-1600:],
                "stderrTail": completed.stderr[-1600:],
            }
        except subprocess.TimeoutExpired as error:
            result = {
                "script": script,
                "returncode": 124,
                "stdoutTail": (error.stdout or "")[-1600:] if isinstance(error.stdout, str) else "",
                "stderrTail": "Timed out after 60 seconds.",
            }
        results.append(result)
    payload = {
        "schema": "learnit.first_storage_seam_browser_observability.v1",
        "failed": [item["script"] for item in results if item["returncode"] != 0],
        "results": results,
    }
    SELF.write_text(
        SELF.read_text(encoding="utf-8")
        + "\n# BROWSER_DIAGNOSTIC="
        + json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# BROWSER_DIAGNOSTIC={"failed":[],"results":[{"returncode":0,"script":"tests/browser_navigation.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 25,\n  \"total\": 25,\n  \"report\": \"reports/browser_navigation_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_product_flow.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 22,\n  \"total\": 22,\n  \"report\": \"reports/browser_product_flow_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_qcm_initial_state.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 17,\n  \"total\": 17,\n  \"report\": \"reports/browser_qcm_initial_state_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_activity_transitions.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 11,\n  \"total\": 11,\n  \"report\": \"reports/browser_activity_transitions_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_context_isolation.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 6,\n  \"total\": 6,\n  \"report\": \"reports/browser_context_isolation_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_bilan_library_ux.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 30,\n  \"total\": 30,\n  \"report\": \"reports/browser_bilan_library_ux_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_scale_progress_import.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 16,\n  \"total\": 16,\n  \"report\": \"reports/browser_scale_progress_import_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_contract_golden_kits.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 16,\n  \"total\": 16,\n  \"report\": \"reports/browser_contract_golden_kits_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_remediation_loop.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 31,\n  \"total\": 31,\n  \"report\": \"reports/browser_remediation_loop_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_performance_scale.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 24,\n  \"total\": 24,\n  \"report\": \"reports/browser_performance_scale_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_entry_guidance.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 19,\n  \"total\": 19,\n  \"report\": \"reports/browser_entry_guidance_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_mobile_feedback.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 19,\n  \"total\": 19,\n  \"report\": \"reports/browser_mobile_feedback_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_library_scroll_reliability.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 23,\n  \"total\": 23,\n  \"report\": \"reports/browser_library_scroll_reliability_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_desktop_scroll_reliability.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 14,\n  \"total\": 14,\n  \"report\": \"reports/browser_desktop_scroll_reliability_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_accessibility_modal.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 12,\n  \"total\": 12,\n  \"report\": \"reports/browser_accessibility_modal_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_pedagogical_truth.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 8,\n  \"total\": 8,\n  \"report\": \"reports/browser_pedagogical_truth_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_media_security.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 10,\n  \"total\": 10,\n  \"report\": \"reports/browser_media_security_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_storage_resilience.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 10,\n  \"total\": 10,\n  \"report\": \"reports/browser_storage_resilience_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_media_scale.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 13,\n  \"total\": 13,\n  \"packageBytes\": 519827,\n  \"report\": \"reports/browser_media_scale_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_next_action_consistency.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 9,\n  \"total\": 9,\n  \"report\": \"reports/browser_next_action_consistency_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_endurance_session.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 6,\n  \"total\": 6,\n  \"report\": \"reports/browser_endurance_session_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_realistic_device_performance.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 8,\n  \"total\": 8,\n  \"report\": \"reports/browser_realistic_device_performance_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_interruption_resilience.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 6,\n  \"total\": 6,\n  \"report\": \"reports/browser_interruption_resilience_report.json\"\n}\n"},{"returncode":0,"script":"tests/browser_library_persistence_naming.py","stderrTail":"","stdoutTail":"{\n  \"ok\": true,\n  \"passed\": 18,\n  \"total\": 18,\n  \"report\": \"reports/browser_library_persistence_naming_report.json\"\n}\n"}],"schema":"learnit.first_storage_seam_browser_observability.v1"}
