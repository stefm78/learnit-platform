#!/usr/bin/env python3
"""Atlas M1 strict-QA focus-semantics and diagnostic adapter.

This revision composes the previously reviewed QA adapter at exact head
658375ce72615dde25edb102b3547e911aa8ecad. It preserves all strict gates while:

1. excluding controls that are not actually rendered/focusable because an
   ancestor hides them, using client-rect presence in addition to CSS flags;
2. modelling native radio groups as one sequential Tab stop per named group;
3. preserving the frozen focus acceptance rules but surfacing the exact expected,
   forward, reverse and boundary traces on failure.

The diagnostic detail changes no acceptance condition and introduces no product
self-attestation.
"""
from __future__ import annotations

import json
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

NEW_FOCUS = """const s='button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex=\"-1\"])',all=[...r.querySelectorAll(s)].filter(x=>{const z=getComputedStyle(x),b=x.getBoundingClientRect();return z.visibility!=='hidden'&&z.display!=='none'&&!x.hidden&&x.getClientRects().length>0&&b.width>0&&b.height>0}),a=all.filter((x,i)=>{if(!(x instanceof HTMLInputElement)||x.type!=='radio'||!x.name)return true;const g=all.filter(y=>y instanceof HTMLInputElement&&y.type==='radio'&&y.name===x.name),checked=g.find(y=>y.checked);return checked?x===checked:x===g[0]});a.forEach((x,i)=>x.setAttribute('data-qa-focus-order',String(i)));return a.map((_,i)=>String(i))"""


def browser_script(artifact: pathlib.Path, driver: dict[str, Any]) -> str:
    script = _ORIGINAL_BROWSER_SCRIPT(artifact, driver)
    count = script.count(OLD_FOCUS)
    if count != 1:
        raise AssertionError(f"QA_FOCUS_ANCHOR_MISMATCH:{count}")
    return script.replace(OLD_FOCUS, NEW_FOCUS, 1)


def focus_trace(
    expected: list[str],
    forward: list[str | None],
    reverse: list[str | None],
    forward_boundary: str | None,
    reverse_boundary: str | None,
) -> bool:
    detail = json.dumps(
        {
            "expected": expected,
            "forward": forward,
            "reverse": reverse,
            "forwardBoundary": forward_boundary,
            "reverseBoundary": reverse_boundary,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    if not expected or len(expected) != len(set(expected)):
        raise AssertionError("FOCUS_EXPECTED_INVALID:" + detail)
    if forward != expected:
        raise AssertionError("FOCUS_FORWARD_ORDER_INVALID:" + detail)
    if reverse != list(reversed(expected)):
        raise AssertionError("FOCUS_REVERSE_ORDER_INVALID:" + detail)
    if forward_boundary != expected[0]:
        raise AssertionError("FOCUS_FORWARD_BOUNDARY_INVALID:" + detail)
    if reverse_boundary != expected[-1]:
        raise AssertionError("FOCUS_REVERSE_BOUNDARY_INVALID:" + detail)
    return True


class FocusAdapterTests(unittest.TestCase):
    def _driver(self) -> dict[str, Any]:
        return {
            "startSelector": "#start",
            "submitSelector": "#submit",
            "interruptSelector": "#pause",
            "resumeSelector": "#resume",
            "responseSteps": [{"action": "click", "selector": "#answer"}],
            "waitAfterActionMs": 1,
        }

    def test_browser_focus_set_is_rendered_and_native(self) -> None:
        script = browser_script(pathlib.Path("/tmp/a.html"), self._driver())
        self.assertIn("x.getClientRects().length>0", script)
        self.assertIn("b.width>0&&b.height>0", script)
        self.assertIn("x.type!=='radio'", script)
        self.assertIn("checked=g.find(y=>y.checked)", script)
        self.assertNotIn(OLD_FOCUS, script)
        for forbidden in ("candidateAtomic", "lifecyclePass", "qaScenario"):
            self.assertNotIn(forbidden, script)

    def test_diagnostic_focus_trace_preserves_frozen_semantics(self) -> None:
        expected = ["0", "1", "2"]
        self.assertTrue(
            focus_trace(expected, expected, ["2", "1", "0"], "0", "2")
        )
        with self.assertRaisesRegex(
            AssertionError,
            r'FOCUS_FORWARD_ORDER_INVALID:.*"forward":\["0",null,"2"\]',
        ):
            focus_trace(expected, ["0", None, "2"], ["2", "1", "0"], "0", "2")


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
PREVIOUS["focus_trace"] = focus_trace
FROZEN["browser_script"] = browser_script
FROZEN["run_tests"] = run_tests
FROZEN["focus_trace"] = focus_trace

if __name__ == "__main__":
    raise SystemExit(FROZEN["main"]())
