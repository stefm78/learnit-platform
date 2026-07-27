#!/usr/bin/env python3
"""DEV-LEARNING unit tests for PROG-WP-001 Learning Loop V2 Wave A."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASELINE = "8ebafee48cc5277b92776982639a0146ae7e76d0"
EXPECTED_CHANGED_PATHS = {
    "apps/learnit-next/src/core/objective_progress.js",
    "apps/learnit-next/src/core/learning_recommendation.js",
    "apps/learnit-next/tests/dev_learning_loop_v2_learning.py",
}
STRICT = os.environ.get("DEV_LEARNING_STRICT", "0") == "1"

NODE_HARNESS = r"""
import assert from 'node:assert/strict';
import {
  OBJECTIVE_STATUSES,
  ObjectiveProgressError,
  createObjectiveProgress,
  normalizeObjectiveProgress,
  applyObjectiveEvent,
  reduceObjectiveEvents,
} from './objective_progress.mjs';
import {
  LEARNING_RECOMMENDATION_ACTIONS,
  rankLearningRecommendations,
  recommendNextObjective,
} from './learning_recommendation.mjs';

const contractKeys = [
  'objectiveId',
  'trainingAttempts',
  'latestTrainingCorrect',
  'needsReview',
  'validationAttempts',
  'latestValidationCorrect',
  'status',
];
const results = [];
async function test(name, fn) {
  try { await fn(); results.push({name, status: 'PASS'}); }
  catch (error) { results.push({name, status: 'FAIL', error: String(error?.stack || error)}); }
}
const event = (type, objectiveId = 'obj-a', correct) => {
  const value = {type, objectiveId};
  if (correct !== undefined) value.correct = correct;
  return value;
};

await test('01 initial contract is exact and not started', () => {
  const state = createObjectiveProgress('  obj-a  ');
  assert.deepEqual(Object.keys(state), contractKeys);
  assert.deepEqual(state, {
    objectiveId: 'obj-a', trainingAttempts: 0, latestTrainingCorrect: null,
    needsReview: false, validationAttempts: 0, latestValidationCorrect: null,
    status: 'not-started',
  });
});

await test('02 training start is explicit without crediting an attempt', () => {
  const state = applyObjectiveEvent(createObjectiveProgress('obj-a'), event('training-started'));
  assert.equal(state.status, 'training');
  assert.equal(state.trainingAttempts, 0);
  assert.equal(state.validationAttempts, 0);
});

await test('03 incorrect training enters corrective queue only', () => {
  const state = applyObjectiveEvent(createObjectiveProgress('obj-a'), event('training-result', 'obj-a', false));
  assert.equal(state.trainingAttempts, 1);
  assert.equal(state.latestTrainingCorrect, false);
  assert.equal(state.validationAttempts, 0);
  assert.equal(state.latestValidationCorrect, null);
  assert.equal(state.needsReview, true);
  assert.equal(state.status, 'review-needed');
});

await test('04 correct training correction clears review without validation credit', () => {
  let state = applyObjectiveEvent(createObjectiveProgress('obj-a'), event('training-result', 'obj-a', false));
  state = applyObjectiveEvent(state, event('training-result', 'obj-a', true));
  assert.equal(state.trainingAttempts, 2);
  assert.equal(state.latestTrainingCorrect, true);
  assert.equal(state.needsReview, false);
  assert.equal(state.status, 'ready-for-validation');
  assert.equal(state.validationAttempts, 0);
  assert.equal(state.latestValidationCorrect, null);
});

await test('05 incorrect validation is isolated from training', () => {
  const state = applyObjectiveEvent(createObjectiveProgress('obj-a'), event('validation-result', 'obj-a', false));
  assert.equal(state.trainingAttempts, 0);
  assert.equal(state.latestTrainingCorrect, null);
  assert.equal(state.validationAttempts, 1);
  assert.equal(state.latestValidationCorrect, false);
  assert.equal(state.needsReview, true);
  assert.equal(state.status, 'review-needed');
});

await test('06 training correction after failed validation preserves validation evidence', () => {
  let state = applyObjectiveEvent(createObjectiveProgress('obj-a'), event('validation-result', 'obj-a', false));
  state = applyObjectiveEvent(state, event('training-result', 'obj-a', true));
  assert.equal(state.trainingAttempts, 1);
  assert.equal(state.latestTrainingCorrect, true);
  assert.equal(state.validationAttempts, 1);
  assert.equal(state.latestValidationCorrect, false);
  assert.equal(state.needsReview, false);
  assert.equal(state.status, 'ready-for-validation');
});

await test('07 correct validation is recent only', () => {
  const state = applyObjectiveEvent(createObjectiveProgress('obj-a'), event('validation-result', 'obj-a', true));
  assert.equal(state.validationAttempts, 1);
  assert.equal(state.latestValidationCorrect, true);
  assert.equal(state.needsReview, false);
  assert.equal(state.status, 'validated-recently');
  assert.equal(OBJECTIVE_STATUSES.includes('mastered'), false);
});

await test('08 later training error reopens review after recent validation', () => {
  let state = applyObjectiveEvent(createObjectiveProgress('obj-a'), event('validation-result', 'obj-a', true));
  state = applyObjectiveEvent(state, event('training-result', 'obj-a', false));
  assert.equal(state.validationAttempts, 1);
  assert.equal(state.latestValidationCorrect, true);
  assert.equal(state.trainingAttempts, 1);
  assert.equal(state.needsReview, true);
  assert.equal(state.status, 'review-needed');
});

await test('09 training start cannot hide an unresolved correction', () => {
  let state = applyObjectiveEvent(createObjectiveProgress('obj-a'), event('training-result', 'obj-a', false));
  state = applyObjectiveEvent(state, event('training-started'));
  assert.equal(state.status, 'review-needed');
  assert.equal(state.needsReview, true);
});

await test('10 reducer is deterministic and does not mutate inputs', () => {
  const events = [
    event('training-started'),
    event('training-result', 'obj-a', false),
    event('training-result', 'obj-a', true),
    event('validation-result', 'obj-a', true),
  ];
  const snapshot = structuredClone(events);
  const first = reduceObjectiveEvents('obj-a', events);
  const second = reduceObjectiveEvents('obj-a', events);
  assert.deepEqual(first, second);
  assert.deepEqual(events, snapshot);
  assert.equal(first.trainingAttempts, 2);
  assert.equal(first.validationAttempts, 1);
  assert.equal(first.status, 'validated-recently');
});

await test('11 incomplete and ambiguous events fail closed', () => {
  const initial = createObjectiveProgress('obj-a');
  for (const invalid of [
    {},
    {type: 'training-result', objectiveId: 'obj-a'},
    {type: 'training-result', objectiveId: 'obj-a', correct: 1},
    {type: 'validation-result', objectiveId: '', correct: true},
    {type: 'training-started', objectiveId: 'obj-a', correct: false},
    {type: 'training-result', objectiveId: 'obj-a', correct: true, extra: 1},
    {type: 'other', objectiveId: 'obj-a', correct: true},
  ]) {
    assert.throws(() => applyObjectiveEvent(initial, invalid), ObjectiveProgressError);
  }
});

await test('12 mismatched objectives fail closed', () => {
  assert.throws(
    () => applyObjectiveEvent(createObjectiveProgress('obj-a'), event('training-result', 'obj-b', true)),
    error => error instanceof ObjectiveProgressError && error.code === 'OBJECTIVE_ID_MISMATCH',
  );
});

await test('13 malformed progress fails closed', () => {
  const valid = createObjectiveProgress('obj-a');
  assert.throws(() => normalizeObjectiveProgress({...valid, status: 'mastered'}), ObjectiveProgressError);
  assert.throws(() => normalizeObjectiveProgress({...valid, extra: true}), ObjectiveProgressError);
  assert.throws(() => normalizeObjectiveProgress({...valid, trainingAttempts: 1}), ObjectiveProgressError);
});

await test('14 recommendation prioritizes correction then validation', () => {
  const review = applyObjectiveEvent(createObjectiveProgress('obj-c'), event('training-result', 'obj-c', false));
  const ready = applyObjectiveEvent(createObjectiveProgress('obj-b'), event('training-result', 'obj-b', true));
  const ranked = rankLearningRecommendations(['obj-a', 'obj-b', 'obj-c'], [ready, review]);
  assert.deepEqual(ranked.map(item => item.objectiveId), ['obj-c', 'obj-b', 'obj-a']);
  assert.deepEqual(ranked.map(item => item.action), ['correct', 'validate', 'start-training']);
});

await test('15 recommendation keeps author order for equal priorities', () => {
  const ranked = rankLearningRecommendations(['obj-z', 'obj-a', 'obj-m']);
  assert.deepEqual(ranked.map(item => item.objectiveId), ['obj-z', 'obj-a', 'obj-m']);
});

await test('16 validated recently is explicitly non-durable and last priority', () => {
  const recent = applyObjectiveEvent(createObjectiveProgress('obj-a'), event('validation-result', 'obj-a', true));
  const next = recommendNextObjective(['obj-a', 'obj-b'], [recent]);
  assert.deepEqual(next, {
    objectiveId: 'obj-b', status: 'not-started', needsReview: false,
    action: 'start-training', reason: 'not-started',
  });
  const only = recommendNextObjective(['obj-a'], [recent]);
  assert.equal(only.action, 'revisit-later');
  assert.equal(only.reason, 'validated-recently-not-durable');
  assert.equal(LEARNING_RECOMMENDATION_ACTIONS.includes('mastered'), false);
});

await test('17 recommendation inputs reject duplicates and unknown progress', () => {
  const progress = createObjectiveProgress('obj-a');
  assert.throws(() => rankLearningRecommendations(['obj-a', 'obj-a']), ObjectiveProgressError);
  assert.throws(() => rankLearningRecommendations(['obj-b'], [progress]), ObjectiveProgressError);
  assert.throws(() => rankLearningRecommendations(['obj-a'], [progress, progress]), ObjectiveProgressError);
});

if (results.some(item => item.status === 'FAIL')) {
  console.error(JSON.stringify({result: 'FAIL', tests: results}, null, 2));
  process.exit(1);
}
console.log(JSON.stringify({result: 'PASS', passed: results.length, tests: results}, null, 2));
"""


class DevLearningLoopV2LearningTests(unittest.TestCase):
    maxDiff = None

    def test_pure_modules(self) -> None:
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required")
        objective = ROOT / "apps/learnit-next/src/core/objective_progress.js"
        recommendation = ROOT / "apps/learnit-next/src/core/learning_recommendation.js"
        with tempfile.TemporaryDirectory(prefix="dev-learning-loop-v2-") as raw:
            work = Path(raw)
            shutil.copyfile(objective, work / "objective_progress.mjs")
            text = recommendation.read_text(encoding="utf-8").replace(
                "'./objective_progress.js'", "'./objective_progress.mjs'"
            )
            (work / "learning_recommendation.mjs").write_text(text, encoding="utf-8")
            (work / "harness.mjs").write_text(NODE_HARNESS, encoding="utf-8")
            result = subprocess.run(
                [node, "harness.mjs"],
                cwd=work,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], 17)

    def test_data_only_boundaries(self) -> None:
        paths = [
            ROOT / "apps/learnit-next/src/core/objective_progress.js",
            ROOT / "apps/learnit-next/src/core/learning_recommendation.js",
        ]
        forbidden = ("document.", "window.", "indexedDB", "localStorage", "sessionStorage", "Date(")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path}: runtime dependency {token}")

    @unittest.skipUnless(STRICT, "set DEV_LEARNING_STRICT=1 for topology and allowlist checks")
    def test_exact_branch_delta(self) -> None:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{BASELINE}...HEAD"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        changed = {line for line in result.stdout.splitlines() if line}
        self.assertEqual(changed, EXPECTED_CHANGED_PATHS)


if __name__ == "__main__":
    unittest.main()
