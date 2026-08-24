#!/usr/bin/env python3
"""Candidate-execution adapter for the frozen independent Atlas M1 QA oracle.

This revision deliberately does not rewrite the pre-candidate oracle. It loads the
exact preserved QA oracle at eef4b7e3bfb6211e08104b838a7ff4bcf35df5fc,
verifies its exact Git blob identity, and applies two bounded corrections only:

1. real-product setup actions before the already frozen browser start action;
2. `atlas.stimulus.v1` fill-token hashing aligned to the frozen 0.3 contract,
   which includes visible token values needed to answer and excludes non-visible
   token metadata such as technical IDs and `maxUses`.

The setup adapter exists because the exact integrated candidate starts from an
empty local library in every fresh browser profile. Strict QA therefore has to
import an Atlas kit and materialize a plan through the real UI before it can
exercise the frozen start/submit/interruption/resume observations.

No candidate self-attestation is accepted. The frozen atomicity, lifecycle,
reward, claim, provenance, no-network, focus and viewport assertions remain the
authority and execute unchanged except for the contract-aligned stimulus digest
payload described above.
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


def stimulus(activity: dict[str, Any]) -> str:
    """Contract-aligned atlas.stimulus.v1 digest.

    The frozen contract includes visible choices/tokens needed to answer and
    excludes technical/non-visible metadata. We still validate token IDs and
    maxUses because they constrain a well-formed fill activity, but neither is
    serialized into the stimulus payload.
    """

    visible = FROZEN["visible"]
    closed = FROZEN["closed"]
    cj = FROZEN["cj"]
    dh = FROZEN["dh"]

    base: dict[str, Any] = {
        "type": activity.get("type"),
        "prompt": visible(activity.get("prompt")),
    }

    if activity.get("type") == "qcm":
        choices = activity.get("choices")
        by: dict[str, str] = {}
        if not isinstance(choices, list) or not choices:
            raise AssertionError("QCM_CHOICES_REQUIRED")
        for choice in choices:
            closed(choice, ("choiceId", "label"))
            choice_id = choice["choiceId"]
            if (
                not isinstance(choice_id, str)
                or not choice_id
                or choice_id in by
            ):
                raise AssertionError("QCM_CHOICE_COLLISION")
            by[choice_id] = visible(choice["label"])

        if activity.get("correctChoiceId") not in by:
            raise AssertionError("QCM_OPERATION_INVALID")
        labels = sorted(by.values())
        if len(labels) != len(set(labels)):
            raise AssertionError("QCM_VISIBLE_CHOICE_COLLISION")
        base.update(
            choices=labels,
            answerOperation={
                "kind": "select-one",
                "correctValue": by[activity["correctChoiceId"]],
            },
        )

    elif activity.get("type") == "fill":
        tokens = activity.get("tokens")
        token_by_id: dict[str, dict[str, Any]] = {}
        if not isinstance(tokens, list) or not tokens:
            raise AssertionError("FILL_TOKENS_REQUIRED")
        for token in tokens:
            closed(token, ("tokenId", "label", "maxUses"))
            token_id = token["tokenId"]
            max_uses = token["maxUses"]
            if (
                not isinstance(token_id, str)
                or not token_id
                or token_id in token_by_id
                or not isinstance(max_uses, int)
                or isinstance(max_uses, bool)
                or max_uses < 1
            ):
                raise AssertionError("FILL_TOKEN_INVALID")
            token_by_id[token_id] = {
                "label": visible(token["label"]),
                "maxUses": max_uses,
            }

        slots: list[str] = []
        segments: list[dict[str, Any]] = []
        for segment in activity.get("segments", []):
            if set(segment) == {"text"}:
                segments.append({"text": visible(segment["text"])})
            elif (
                set(segment) == {"slotId"}
                and isinstance(segment["slotId"], str)
                and segment["slotId"]
                and segment["slotId"] not in slots
            ):
                slots.append(segment["slotId"])
                segments.append({"blank": len(slots) - 1})
            else:
                raise AssertionError("FILL_SEGMENT_INVALID")

        answers: dict[str, str] = {}
        for answer in activity.get("answers", []):
            closed(answer, ("slotId", "tokenId"))
            if answer["slotId"] in answers:
                raise AssertionError("FILL_ANSWER_MAPPING_INVALID")
            answers[answer["slotId"]] = answer["tokenId"]
        if set(answers) != set(slots):
            raise AssertionError("FILL_ANSWER_MAPPING_INVALID")

        used = {key: 0 for key in token_by_id}
        correct_values: list[str] = []
        for slot in slots:
            token_id = answers[slot]
            if token_id not in token_by_id:
                raise AssertionError("FILL_ANSWER_TOKEN_UNKNOWN")
            used[token_id] += 1
            if used[token_id] > token_by_id[token_id]["maxUses"]:
                raise AssertionError("FILL_MAX_USES_EXCEEDED")
            correct_values.append(token_by_id[token_id]["label"])

        # Frozen contract 0.3: visible tokens needed to answer are hashed;
        # technical IDs and non-visible authoring constraints are excluded.
        visible_tokens = sorted(
            row["label"] for row in token_by_id.values()
        )
        base.update(
            segments=segments,
            tokens=visible_tokens,
            answerOperation={
                "kind": "fill-blanks",
                "correctValues": correct_values,
            },
        )
    else:
        raise AssertionError("ATLAS_ACTIVITY_TYPE_UNSUPPORTED")

    return "sha256:" + dh(
        "learnit.atlas.m1.v0.3/stimulus-digest/atlas.stimulus.v1",
        base,
    )


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

    def test_contract_visible_fill_token_digest(self) -> None:
        activity = {
            "type": "fill",
            "prompt": "Complète le conjugué de −1 − 4i.",
            "segments": [
                {"text": "Le conjugué vaut "},
                {"slotId": "slot"},
                {"text": "."},
            ],
            "tokens": [
                {"tokenId": "a", "label": "−1 + 4i", "maxUses": 1},
                {"tokenId": "b", "label": "1 − 4i", "maxUses": 1},
                {"tokenId": "c", "label": "−1 − 4i", "maxUses": 1},
            ],
            "answers": [{"slotId": "slot", "tokenId": "a"}],
        }
        expected = "sha256:bd24eff3e978c4d59e4e40747fd3a65024517e172f8be3f19b7f7d5d6e0ff1d8"
        self.assertEqual(stimulus(activity), expected)
        activity["tokens"][0]["maxUses"] = 2
        self.assertEqual(stimulus(activity), expected)

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


FROZEN["stimulus"] = stimulus
FROZEN["validate_driver"] = validate_driver
FROZEN["browser_script"] = browser_script
FROZEN["run_tests"] = run_tests

if __name__ == "__main__":
    raise SystemExit(FROZEN["main"]())
