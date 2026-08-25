#!/usr/bin/env python3
"""Atlas M1 strict-QA focus-semantics adapter.

This revision composes the previously reviewed QA adapter at exact head
658375ce72615dde25edb102b3547e911aa8ecad and changes only the browser focus
observation model. Native radio groups expose one sequential Tab stop per named
group (the checked radio, or the first radio when none is checked); the previous
oracle incorrectly counted every enabled radio as an independent Tab stop.

No product attestation is introduced and all previous strict atomicity,
lifecycle, provenance, claim, network, viewport and overflow checks remain
unchanged.
"""
from __future__ import annotations

import pathlib
import subprocess
import unittest
from typing import Any

PREVIOUS_QA_HEAD = "658375ce72615dde25edb102b3547e911aa8ecad"
PREVIOUS_QA_BLOB = "da262b105997d431194540a3ff248b8078f130ae"
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
            "QA_PREVIOUS_SOURCE_GIT_FAILURE:"
            + " ".join(args)
            + ":"
            + (completed.stderr.strip() or completed.stdout.strip())
        )
    return completed.stdout


def _load_previous() -> dict[str, Any]:
    actual = _git("rev-parse", f"{PREVIOUS_QA_HEAD}:{QA_PATH}").strip()
    if actual != PREVIOUS_QA_BLOB:
        raise RuntimeError(
            f"QA_PREVIOUS_BLOB_MISMATCH:{actual}!={PREVIOUS_QA_BLOB}"
        )
    source = _git("show", f"{PREVIOUS_QA_HEAD}:{QA_PATH}")
    namespace: dict[str, Any] = {
        "__file__": str(HERE),
        "__name__": "atlas_qa_previous_adapter",
    }
    exec(compile(source, str(HERE), "exec"), namespace)
    return namespace


PREVIOUS = _load_previous()
FROZEN = PREVIOUS["FROZEN"]
_ORIGINAL_BROWSER_SCRIPT = PREVIOUS["browser_script"]
_ORIGINAL_RUN_TESTS = PREVIOUS["run_tests"]

OLD_FOCUS = """const s='button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex=\"-1\"])',a=[...r.querySelectorAll(s)].filter(x=>{const z=getComputedStyle(x);return z.visibility!=='hidden'&&z.display!=='none'&&!x.hidden});a.forEach((x,i)=>x.setAttribute('data-qa-focus-order',String(i)));return a.map((_,i)=>String(i))"""

NEW_FOCUS = """const s='button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex=\"-1\"])',all=[...r.querySelectorAll(s)].filter(x=>{const z=getComputedStyle(x);return z.visibility!=='hidden'&&z.display!=='none'&&!x.hidden}),a=all.filter((x,i)=>{if(!(x instanceof HTMLInputElement)||x.type!=='radio'||!x.name)return true;const g=all.filter(y=>y instanceof HTMLInputElement&&y.type==='radio'&&y.name===x.name),checked=g.find(y=>y.checked);return checked?x===checked:x===g[0]});a.forEach((x,i)=>x.setAttribute('data-qa-focus-order',String(i)));return a.map((_,i)=>String(i))"""


def browser_script(artifact: pathlib.Path, driver: dict[str, Any]) -> str:
    script = _ORIGINAL_BROWSER_SCRIPT(artifact, driver)
    count = script.count(OLD_FOCUS)
    if count != 1:
        raise AssertionError(f"QA_FOCUS_ANCHOR_MISMATCH:{count}")
    return script.replace(OLD_FOCUS, NEW_FOCUS, 1)


class FocusAdapterTests(unittest.TestCase):
    def test_radio_groups_are_one_native_tab_stop(self) -> None:
        driver = {
            "startSelector": "#start",
            "submitSelector": "#submit",
            "interruptSelector": "#pause",
            "resumeSelector": "#resume",
            "responseSteps": [{"action": "click", "selector": "#answer"}],
            "waitAfterActionMs": 1,
        }
        script = browser_script(pathlib.Path("/tmp/a.html"), driver)
        self.assertIn("x.type!=='radio'", script)
        self.assertIn("checked=g.find(y=>y.checked)", script)
        self.assertNotIn(OLD_FOCUS, script)
        for forbidden in ("candidateAtomic", "lifecyclePass", "qaScenario"):
            self.assertNotIn(forbidden, script)


def run_tests():
    previous = _ORIGINAL_RUN_TESTS()
    own = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(FocusAdapterTests)
    )

    class Combined:
        testsRun = previous.testsRun + own.testsRun
        def wasSuccessful(self) -> bool:
            return previous.wasSuccessful() and own.wasSuccessful()

    return Combined()


PREVIOUS["browser_script"] = browser_script
PREVIOUS["run_tests"] = run_tests
FROZEN["browser_script"] = browser_script
FROZEN["run_tests"] = run_tests

if __name__ == "__main__":
    raise SystemExit(FROZEN["main"]())
