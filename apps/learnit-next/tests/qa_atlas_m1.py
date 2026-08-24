#!/usr/bin/env python3
"""Candidate-execution adapter for the frozen independent Atlas M1 QA oracle.

This revision deliberately does not rewrite the pre-candidate oracle. It loads the
exact preserved QA oracle at eef4b7e3bfb6211e08104b838a7ff4bcf35df5fc,
verifies its exact Git blob identity, and adds one bounded capability only:
real-product setup actions before the already frozen browser start action.

The setup adapter exists because the exact integrated candidate starts from an
empty local library in every fresh browser profile. Strict QA therefore has to
import an Atlas kit and materialize a plan through the real UI before it can
exercise the frozen start/submit/interruption/resume observations.

No candidate self-attestation is accepted. The frozen atomicity, lifecycle,
reward, claim, provenance, no-network, focus and viewport assertions remain the
authority and execute unchanged.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest
from typing import Any

FROZEN_QA_HEAD = "eef4b7e3bfb6211e08104b838a7ff4bcf35df5fc"
FROZEN_QA_BLOB = "f091313ffc0e2bd5d67c2fc50e224dc27f09a7cb"
QA_PATH = "apps/learnit-next/tests/qa_atlas_m1.py"
HERE = pathlib.Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            "QA_FROZEN_SOURCE_GIT_FAILURE:"
            + " ".join(args)
            + ":"
            + (completed.stderr.strip() or completed.stdout.strip())
        )
    return completed.stdout


def _load_frozen_oracle() -> dict[str, Any]:
    actual_blob = _git("rev-parse", f"{FROZEN_QA_HEAD}:{QA_PATH}").strip()
    if actual_blob != FROZEN_QA_BLOB:
        raise RuntimeError(
            f"QA_FROZEN_BLOB_MISMATCH:{actual_blob}!={FROZEN_QA_BLOB}"
        )

    source = _git("show", f"{FROZEN_QA_HEAD}:{QA_PATH}")
    namespace: dict[str, Any] = {
        "__file__": str(HERE),
        "__name__": "atlas_qa_frozen_pre_candidate",
    }
    exec(compile(source, str(HERE), "exec"), namespace)
    return namespace


FROZEN = _load_frozen_oracle()
_ORIGINAL_VALIDATE_DRIVER = FROZEN["validate_driver"]
_ORIGINAL_BROWSER_SCRIPT = FROZEN["browser_script"]


def _validate_setup_step(step: Any) -> dict[str, Any]:
    if not isinstance(step, dict):
        raise AssertionError("DRIVER_SETUP_STEP_INVALID")

    action = step.get("action")
    if action == "upload":
        if set(step) != {"action", "selector", "value"}:
            raise AssertionError("DRIVER_SETUP_STEP_NOT_CLOSED")
        if not isinstance(step["selector"], str) or not step["selector"]:
            raise AssertionError("DRIVER_SETUP_SELECTOR_REQUIRED")
        if not isinstance(step["value"], str) or not step["value"]:
            raise AssertionError("DRIVER_SETUP_FILE_REQUIRED")
    elif action in {"click", "wait"}:
        if set(step) != {"action", "selector"}:
            raise AssertionError("DRIVER_SETUP_STEP_NOT_CLOSED")
        if not isinstance(step["selector"], str) or not step["selector"]:
            raise AssertionError("DRIVER_SETUP_SELECTOR_REQUIRED")
    else:
        raise AssertionError("DRIVER_SETUP_ACTION_INVALID")

    return dict(step)


def validate_driver(driver: Any) -> dict[str, Any]:
    if not isinstance(driver, dict):
        return _ORIGINAL_VALIDATE_DRIVER(driver)

    has_setup = "setupSteps" in driver
    setup = driver.get("setupSteps", [])
    base = {key: value for key, value in driver.items() if key != "setupSteps"}
    validated = _ORIGINAL_VALIDATE_DRIVER(base)

    if not has_setup:
        return validated
    if not isinstance(setup, list) or not setup:
        raise AssertionError("DRIVER_SETUP_REQUIRED")

    checked = [_validate_setup_step(step) for step in setup]
    return {**validated, "setupSteps": checked}


def browser_script(artifact: pathlib.Path, driver: dict[str, Any]) -> str:
    checked = validate_driver(driver)
    setup_steps = checked.get("setupSteps", [])
    base_driver = {
        key: value for key, value in checked.items() if key != "setupSteps"
    }
    script = _ORIGINAL_BROWSER_SCRIPT(artifact, base_driver)

    anchor = "def act(q,s):\n"
    if script.count(anchor) != 1:
        raise AssertionError("QA_SETUP_ACT_ANCHOR_MISMATCH")

    encoded_setup = repr(json.dumps(setup_steps, ensure_ascii=False))
    adapter = (
        f"setup_steps=json.loads({encoded_setup})\n"
        "def setup(q):\n"
        " for a in setup_steps:\n"
        "  s=a['selector'];x=q.locator(s)\n"
        "  if a['action']=='wait':\n"
        "   x.wait_for(state='visible');assert x.count()==1,'SETUP_ACTION_PATH_NOT_EXACT:'+s\n"
        "  else:\n"
        "   assert x.count()==1,'SETUP_ACTION_PATH_NOT_EXACT:'+s\n"
        "   x.set_input_files(a['value']) if a['action']=='upload' else x.click()\n"
        "   q.wait_for_timeout(driver['waitAfterActionMs'])\n"
    )
    script = script.replace(anchor, adapter + anchor, 1)

    start = "c,q=open_c(p,d,j,v);act(q,driver['startSelector'])"
    if script.count(start) != 3:
        raise AssertionError(
            f"QA_SETUP_START_ANCHOR_MISMATCH:{script.count(start)}"
        )
    script = script.replace(
        start,
        "c,q=open_c(p,d,j,v);setup(q);act(q,driver['startSelector'])",
    )
    return script


class AdapterTests(unittest.TestCase):
    def _base(self) -> dict[str, Any]:
        return {
            "startSelector": "#start",
            "submitSelector": "#submit",
            "interruptSelector": "#pause",
            "resumeSelector": "#resume",
            "responseSteps": [{"action": "click", "selector": "#answer"}],
            "waitAfterActionMs": 1,
        }

    def test_real_product_setup_adapter(self) -> None:
        driver = {
            **self._base(),
            "setupSteps": [
                {"action": "upload", "selector": "#kit-file", "value": "/tmp/kit.json"},
                {"action": "wait", "selector": "button:not([disabled])"},
                {"action": "click", "selector": "button:not([disabled])"},
            ],
        }
        self.assertEqual(validate_driver(driver), driver)
        script = browser_script(pathlib.Path("/tmp/a.html"), driver)
        self.assertIn("set_input_files", script)
        self.assertEqual(
            script.count("setup(q);act(q,driver['startSelector'])"),
            3,
        )
        for forbidden in ("candidateAtomic", "lifecyclePass", "qaScenario"):
            self.assertNotIn(forbidden, script)

    def test_setup_is_optional_for_frozen_preflight(self) -> None:
        driver = self._base()
        self.assertEqual(validate_driver(driver), driver)

    def test_setup_actions_fail_closed(self) -> None:
        base = self._base()
        cases = [
            ([{"action": "script", "selector": "#x"}], "ACTION_INVALID"),
            ([{"action": "upload", "selector": "#x"}], "STEP_NOT_CLOSED"),
            ([{"action": "click", "selector": "#x", "value": "bad"}], "STEP_NOT_CLOSED"),
            ([{"action": "wait", "selector": ""}], "SELECTOR_REQUIRED"),
        ]
        for setup, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                AssertionError, message
            ):
                validate_driver({**base, "setupSteps": setup})


def run_tests():
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.defaultTestLoader.loadTestsFromTestCase(FROZEN["Tests"])
    )
    suite.addTests(
        unittest.defaultTestLoader.loadTestsFromTestCase(AdapterTests)
    )
    return unittest.TextTestRunner(verbosity=2).run(suite)


FROZEN["validate_driver"] = validate_driver
FROZEN["browser_script"] = browser_script
FROZEN["run_tests"] = run_tests

if __name__ == "__main__":
    raise SystemExit(FROZEN["main"]())
