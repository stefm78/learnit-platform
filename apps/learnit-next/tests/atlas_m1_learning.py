#!/usr/bin/env python3
"""Deterministic lane tests for Project Atlas M1 ATLAS-LEARNING."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

BASELINE = "58e39e8917006058fdf177a5daa37535f5e2c78d"
ALLOWED_PATHS = {
    "apps/learnit-next/src/core/atlas_evidence.js",
    "apps/learnit-next/src/core/atlas_recommendation.js",
    "apps/learnit-next/src/core/atlas_planner.js",
    "apps/learnit-next/tests/atlas_m1_learning.py",
}
ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "apps" / "learnit-next" / "src" / "core"

NODE_HARNESS = r"""
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {
  AtlasEvidenceError,
  createEmptyObjectiveEvidence,
  interpretObjectiveEvidence,
  normalizeObjectiveEvidence,
  normalizeObjectiveEvidenceSet,
} from './atlas_evidence.mjs';
import {
  ATLAS_CANONICAL_REASON_CODES,
  AtlasRecommendationError,
  normalizeAtlasReasonCodes,
  rankAtlasLearningRecommendations,
  recommendNextAtlasLearningAction,
} from './atlas_recommendation.mjs';
import {
  ATLAS_LEARNING_ENGINE_VERSION,
  AtlasPlannerError,
  createAtlasSessionPlan,
  sha256Hex,
} from './atlas_planner.mjs';

const O1 = '00000000-0000-4000-8000-000000000001';
const O2 = '00000000-0000-4000-8000-000000000002';
const O3 = '00000000-0000-4000-8000-000000000003';
const O4 = '00000000-0000-4000-8000-000000000004';
const O5 = '00000000-0000-4000-8000-000000000005';
const AT = (suffix) => `10000000-0000-4000-8000-${String(suffix).padStart(12, '0')}`;
const NOW = '2026-07-29T12:00:00.000Z';
const clone = (value) => structuredClone(value);

const activity = (id, objectiveId, assessmentRole) => ({
  activityLineageId: id,
  objectiveIds: [objectiveId],
  assessmentRole,
  activityRevisionId: id,
  type: 'qcm',
  difficulty: 'medium',
});

const content = {
  objectives: [O5, O3, O1, O4, O2].map((objectiveId) => ({objectiveId, label: objectiveId})),
  activities: [
    activity(AT(1), O1, 'practice'), activity(AT(2), O1, 'practice'),
    activity(AT(3), O2, 'practice'), activity(AT(4), O2, 'validation'), activity(AT(5), O2, 'validation'),
    activity(AT(6), O3, 'practice'), activity(AT(7), O3, 'practice'), activity(AT(8), O3, 'diagnostic'),
    activity(AT(9), O4, 'validation'), activity(AT(10), O4, 'validation'),
    activity(AT(11), O5, 'practice'), activity(AT(12), O5, 'practice'),
  ].reverse(),
};

const evidence = [
  {
    objectiveId: O4, projectionVersion: 1,
    practiceAttempts: 1, latestPracticeCorrect: true, needsReview: false,
    correctionsCompleted: 0, validationAttempts: 1, latestValidationCorrect: true,
    lastEvidenceAt: '2026-07-29T11:00:00.000Z', state: 'validated-recently', reasons: ['VALIDATED'],
  },
  {
    objectiveId: O1, projectionVersion: 1,
    practiceAttempts: 2, latestPracticeCorrect: false, needsReview: true,
    correctionsCompleted: 0, validationAttempts: 0, latestValidationCorrect: null,
    lastEvidenceAt: '2026-07-29T10:00:00.000Z', state: 'review-needed', reasons: ['PRACTICE_ERROR'],
  },
  {
    objectiveId: O5, projectionVersion: 1,
    practiceAttempts: 1, latestPracticeCorrect: true, needsReview: false,
    correctionsCompleted: 0, validationAttempts: 0, latestValidationCorrect: null,
    lastEvidenceAt: '2026-07-29T09:00:00.000Z', state: 'training', reasons: ['PRACTICE_STARTED'],
  },
  {
    objectiveId: O2, projectionVersion: 1,
    practiceAttempts: 2, latestPracticeCorrect: true, needsReview: false,
    correctionsCompleted: 1, validationAttempts: 1, latestValidationCorrect: false,
    lastEvidenceAt: '2026-07-29T10:30:00.000Z', state: 'ready-for-validation', reasons: ['CORRECTED'],
  },
];

const results = [];
async function test(name, fn) {
  try {
    await fn();
    results.push({name, status: 'PASS'});
  } catch (error) {
    results.push({name, status: 'FAIL', error: String(error?.stack || error)});
  }
}
function expectCode(fn, ErrorType, code) {
  assert.throws(fn, (error) => error instanceof ErrorType && error.code === code);
}

await test('01 empty evidence is exact contract state', () => {
  assert.deepEqual(createEmptyObjectiveEvidence(O3), {
    objectiveId: O3, projectionVersion: 1,
    practiceAttempts: 0, latestPracticeCorrect: null, needsReview: false,
    correctionsCompleted: 0, validationAttempts: 0, latestValidationCorrect: null,
    lastEvidenceAt: null, state: 'not-started', reasons: [],
  });
});

await test('02 evidence normalization is canonical and pure', () => {
  const input = clone(evidence[0]); input.reasons = ['Z', 'A'];
  const before = JSON.stringify(input);
  const normalized = normalizeObjectiveEvidence(input);
  assert.equal(JSON.stringify(input), before);
  assert.deepEqual(normalized.reasons, ['A', 'Z']);
  assert.notEqual(normalized, input);
});

await test('03 evidence rejects unknown fields and unsupported versions', () => {
  assert.throws(() => normalizeObjectiveEvidence({...evidence[0], extra: true}), AtlasEvidenceError);
  expectCode(
    () => normalizeObjectiveEvidence({...evidence[0], projectionVersion: 2}),
    AtlasEvidenceError,
    'UNSUPPORTED_PROJECTION_VERSION',
  );
});

await test('04 evidence enforces state and correction invariants', () => {
  assert.throws(() => normalizeObjectiveEvidence({...evidence[1], needsReview: false}), AtlasEvidenceError);
  assert.throws(() => normalizeObjectiveEvidence({...evidence[1], correctionsCompleted: 3}), AtlasEvidenceError);
  assert.throws(() => normalizeObjectiveEvidence({...createEmptyObjectiveEvidence(O3), reasons: ['x']}), AtlasEvidenceError);
});

await test('05 interpretation never turns correction into validation', () => {
  const interpretation = interpretObjectiveEvidence(evidence[3]);
  assert.equal(interpretation.correctionCompleted, true);
  assert.equal(interpretation.hasSuccessfulIndependentValidation, false);
  assert.equal(interpretation.missingIndependentValidation, true);
  assert.equal(interpretation.validationAvailable, true);
});

await test('06 evidence sets reject duplicate and unknown objectives', () => {
  expectCode(
    () => normalizeObjectiveEvidenceSet([O1], [evidence[1], evidence[1]]),
    AtlasEvidenceError,
    'DUPLICATE_OBJECTIVE_EVIDENCE',
  );
  expectCode(
    () => normalizeObjectiveEvidenceSet([O1], [evidence[0]]),
    AtlasEvidenceError,
    'UNKNOWN_OBJECTIVE_ID',
  );
});

await test('07 ranking is deterministic and follows versioned priorities', () => {
  const ranked = rankAtlasLearningRecommendations(content, evidence);
  assert.deepEqual(ranked.map((item) => item.objectiveId), [O1, O2, O5, O3, O4]);
  assert.deepEqual(ranked.map((item) => item.priority), [100, 80, 60, 40, 20]);
  assert.deepEqual(ranked.map((item) => item.action), [
    'correct-practice', 'attempt-validation', 'continue-practice',
    'start-practice', 'maintain-recent-validation',
  ]);
  assert.deepEqual(recommendNextAtlasLearningAction(content, evidence), ranked[0]);
});

await test('08 all recommendation reason codes are canonical and ordered', () => {
  const canonical = new Set(ATLAS_CANONICAL_REASON_CODES);
  for (const recommendation of rankAtlasLearningRecommendations(content, evidence)) {
    assert.ok(recommendation.reasonCodes.length > 0);
    for (const code of recommendation.reasonCodes) assert.ok(canonical.has(code));
    assert.deepEqual(normalizeAtlasReasonCodes(recommendation.reasonCodes), recommendation.reasonCodes);
  }
  expectCode(
    () => normalizeAtlasReasonCodes(['NOT_CANONICAL']),
    AtlasRecommendationError,
    'NON_CANONICAL_REASON_CODE',
  );
});

await test('09 review recommendation uses practice only', () => {
  const recommendation = rankAtlasLearningRecommendations(content, evidence)[0];
  assert.deepEqual(recommendation.eligibleActivityIds, [AT(1), AT(2)]);
  assert.ok(recommendation.reasonCodes.includes('RECENT_ERROR'));
  assert.ok(recommendation.reasonCodes.includes('REVIEW_REQUIRED'));
  assert.ok(recommendation.reasonCodes.includes('NO_INDEPENDENT_VALIDATION'));
});

await test('10 validation recommendation uses validation only', () => {
  const recommendation = rankAtlasLearningRecommendations(content, evidence)
    .find((item) => item.objectiveId === O2);
  assert.deepEqual(recommendation.eligibleActivityIds, [AT(4), AT(5)]);
  assert.ok(recommendation.reasonCodes.includes('CORRECTION_COMPLETED'));
  assert.ok(recommendation.reasonCodes.includes('NO_INDEPENDENT_VALIDATION'));
  assert.ok(recommendation.reasonCodes.includes('VALIDATION_AVAILABLE'));
  assert.equal(recommendation.reasonCodes.includes('RECENTLY_VALIDATED'), false);
});

await test('11 diagnostic activity is never silently treated as practice', () => {
  const recommendation = rankAtlasLearningRecommendations(content, evidence)
    .find((item) => item.objectiveId === O3);
  assert.deepEqual(recommendation.eligibleActivityIds, [AT(6), AT(7)]);
  assert.equal(recommendation.eligibleActivityIds.includes(AT(8)), false);
});

await test('12 recent validation remains a bounded product state', () => {
  const recommendation = rankAtlasLearningRecommendations(content, evidence)
    .find((item) => item.objectiveId === O4);
  assert.equal(recommendation.action, 'maintain-recent-validation');
  assert.deepEqual(recommendation.reasonCodes, ['RECENTLY_VALIDATED']);
  assert.deepEqual(recommendation.eligibleActivityIds, [AT(9), AT(10)]);
});

await test('13 ranking ignores author array order for identity and tie breaking', () => {
  const reorderedContent = {
    objectives: [...content.objectives].reverse(),
    activities: [...content.activities].reverse(),
  };
  const first = rankAtlasLearningRecommendations(content, evidence);
  const second = rankAtlasLearningRecommendations(reorderedContent, [...evidence].reverse());
  assert.deepEqual(second, first);
});

await test('14 unlinked activities and missing eligible roles fail closed', () => {
  const unlinked = clone(content);
  unlinked.activities[0].objectiveIds = ['unknown-objective'];
  expectCode(
    () => rankAtlasLearningRecommendations(unlinked, evidence),
    AtlasRecommendationError,
    'UNKNOWN_ACTIVITY_OBJECTIVE_ID',
  );
  const practiceOnly = {
    objectives: [{objectiveId: O2}],
    activities: [activity(AT(20), O2, 'practice')],
  };
  expectCode(
    () => rankAtlasLearningRecommendations(practiceOnly, [evidence[3]]),
    AtlasRecommendationError,
    'NO_ELIGIBLE_ACTIVITY',
  );
});

await test('15 recommendation contract contains only frozen fields', () => {
  const keys = Object.keys(rankAtlasLearningRecommendations(content, evidence)[0]).sort();
  assert.deepEqual(keys, [
    'action', 'eligibleActivityIds', 'estimatedMinutes', 'objectiveId',
    'priority', 'reasonCodes', 'recommendationVersion',
  ]);
});

await test('16 SHA-256 implementation matches the platform reference', () => {
  for (const value of ['', 'abc', 'Learn-it Atlas', 'évidence']) {
    const expected = crypto.createHash('sha256').update(value).digest('hex');
    assert.equal(sha256Hex(value), expected);
  }
});

await test('17 plans for 5, 15 and 30 minutes never exceed the budget', () => {
  for (const durationMinutes of [5, 15, 30]) {
    const plan = createAtlasSessionPlan({content, evidence, durationMinutes, generatedAt: NOW});
    const total = plan.items.reduce((sum, item) => sum + item.estimatedMinutes, 0);
    assert.ok(total <= durationMinutes);
    assert.equal(total + plan.unusedMinutes, durationMinutes);
    assert.equal(plan.items.length, durationMinutes / 5);
    assert.deepEqual(plan.items.map((item) => item.position),
      Array.from({length: plan.items.length}, (_, index) => index + 1));
  }
});

await test('18 planner uses deterministic round-robin diversity', () => {
  const plan = createAtlasSessionPlan({content, evidence, durationMinutes: 30, generatedAt: NOW});
  assert.deepEqual(plan.items.slice(0, 5).map((item) => item.objectiveId), [O1, O2, O5, O3, O4]);
  assert.equal(plan.items[5].objectiveId, O1);
  assert.equal(new Set(plan.items.map((item) => item.activityLineageId)).size, plan.items.length);
});

await test('19 session time limit is explicit when candidates are truncated', () => {
  const plan = createAtlasSessionPlan({content, evidence, durationMinutes: 5, generatedAt: NOW});
  assert.equal(plan.items.length, 1);
  assert.ok(plan.items[0].reasonCodes.includes('SESSION_TIME_LIMIT'));
});

await test('20 identical normalized inputs produce identical plan and planId', () => {
  const first = createAtlasSessionPlan({content, evidence, durationMinutes: 15, generatedAt: NOW});
  const second = createAtlasSessionPlan({
    content: {objectives: [...content.objectives].reverse(), activities: [...content.activities].reverse()},
    evidence: [...evidence].reverse(),
    durationMinutes: 15,
    generatedAt: NOW,
  });
  assert.deepEqual(second, first);
  assert.match(first.planId, /^sha256:[0-9a-f]{64}$/);
});

await test('21 controlled clock and engine version are explicit digest inputs', () => {
  const base = createAtlasSessionPlan({content, evidence, durationMinutes: 15, generatedAt: NOW});
  const later = createAtlasSessionPlan({
    content, evidence, durationMinutes: 15, generatedAt: '2026-07-29T12:00:01.000Z',
  });
  const nextEngine = createAtlasSessionPlan({
    content, evidence, durationMinutes: 15, generatedAt: NOW,
    engineVersion: `${ATLAS_LEARNING_ENGINE_VERSION}-next`,
  });
  assert.notEqual(later.planId, base.planId);
  assert.notEqual(nextEngine.planId, base.planId);
  assert.deepEqual(later.items, base.items);
  assert.deepEqual(nextEngine.items, base.items);
});

await test('22 plan contract is serializable and excludes execution identity', () => {
  const plan = createAtlasSessionPlan({content, evidence, durationMinutes: 15, generatedAt: NOW});
  assert.deepEqual(JSON.parse(JSON.stringify(plan)), plan);
  assert.equal(Object.hasOwn(plan, 'sessionId'), false);
  assert.deepEqual(Object.keys(plan).sort(), [
    'durationMinutes', 'generatedAt', 'items', 'planId', 'planVersion', 'unusedMinutes',
  ]);
  assert.deepEqual(Object.keys(plan.items[0]).sort(), [
    'action', 'activityLineageId', 'estimatedMinutes', 'objectiveId',
    'position', 'reasonCodes',
  ]);
});

await test('23 planner rejects ambient or unsupported time choices', () => {
  expectCode(
    () => createAtlasSessionPlan({content, evidence, durationMinutes: 10, generatedAt: NOW}),
    AtlasPlannerError,
    'UNSUPPORTED_SESSION_DURATION',
  );
  assert.throws(
    () => createAtlasSessionPlan({content, evidence, durationMinutes: 5, generatedAt: 'today'}),
    AtlasPlannerError,
  );
  assert.throws(
    () => createAtlasSessionPlan({content, evidence, durationMinutes: 5}),
    AtlasPlannerError,
  );
});

await test('24 planner does not mutate content or evidence', () => {
  const sourceContent = clone(content); const sourceEvidence = clone(evidence);
  const contentBefore = JSON.stringify(sourceContent); const evidenceBefore = JSON.stringify(sourceEvidence);
  createAtlasSessionPlan({content: sourceContent, evidence: sourceEvidence, durationMinutes: 30, generatedAt: NOW});
  assert.equal(JSON.stringify(sourceContent), contentBefore);
  assert.equal(JSON.stringify(sourceEvidence), evidenceBefore);
});

const failed = results.filter((result) => result.status !== 'PASS');
console.log(JSON.stringify({
  suite: 'ATLAS_M1_LEARNING',
  engineVersion: ATLAS_LEARNING_ENGINE_VERSION,
  total: results.length,
  passed: results.length - failed.length,
  failed: failed.length,
  results,
}, null, 2));
if (failed.length > 0) process.exit(1);
"""


def run(*args: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=check,
    )


def git_available() -> bool:
    return (ROOT / ".git").exists() and shutil.which("git") is not None


class AtlasM1LearningTests(unittest.TestCase):
    maxDiff = None

    def test_01_lane_scope_is_exact(self) -> None:
        if not git_available() or os.environ.get("ATLAS_SKIP_SCOPE") == "1":
            self.skipTest("scope check requires a Git worktree")
        ancestor = run("git", "cat-file", "-e", f"{BASELINE}^{{commit}}", check=False)
        if ancestor.returncode != 0:
            self.skipTest("exact baseline commit is unavailable in this checkout")
        changed = set(filter(None, run("git", "diff", "--name-only", BASELINE).stdout.splitlines()))
        status = run("git", "status", "--porcelain").stdout.splitlines()
        for line in status:
            if line.startswith("?? "):
                changed.add(line[3:])
        self.assertEqual(changed, ALLOWED_PATHS)

    def test_02_no_runtime_network_or_llm_surface(self) -> None:
        forbidden = (
            "fetch(",
            "XMLHttpRequest",
            "WebSocket",
            "EventSource",
            "sendBeacon",
            "openai",
            "anthropic",
            "remote api",
        )
        for path in sorted(CORE.glob("atlas_*.js")):
            if path.name not in {"atlas_evidence.js", "atlas_recommendation.js", "atlas_planner.js"}:
                continue
            source = path.read_text(encoding="utf-8")
            lowered = source.lower()
            for token in forbidden:
                self.assertNotIn(token.lower(), lowered, f"forbidden runtime surface in {path.name}: {token}")
            self.assertNotIn("Math.random", source)
            self.assertNotIn("Date.now", source)

    def test_03_node_contract_matrix(self) -> None:
        if shutil.which("node") is None:
            self.fail("Node.js is required for ATLAS-LEARNING deterministic tests")
        with tempfile.TemporaryDirectory(prefix="atlas-m1-learning-") as directory:
            temp = Path(directory)
            evidence_source = (CORE / "atlas_evidence.js").read_text(encoding="utf-8")
            recommendation_source = (CORE / "atlas_recommendation.js").read_text(encoding="utf-8")
            planner_source = (CORE / "atlas_planner.js").read_text(encoding="utf-8")
            (temp / "atlas_evidence.mjs").write_text(evidence_source, encoding="utf-8")
            (temp / "atlas_recommendation.mjs").write_text(
                recommendation_source.replace("'./atlas_evidence.js'", "'./atlas_evidence.mjs'"),
                encoding="utf-8",
            )
            (temp / "atlas_planner.mjs").write_text(
                planner_source
                .replace("'./atlas_evidence.js'", "'./atlas_evidence.mjs'")
                .replace("'./atlas_recommendation.js'", "'./atlas_recommendation.mjs'"),
                encoding="utf-8",
            )
            harness = temp / "harness.mjs"
            harness.write_text(textwrap.dedent(NODE_HARNESS), encoding="utf-8")
            completed = run("node", str(harness), cwd=temp, check=False)
            try:
                report = json.loads(completed.stdout)
            except json.JSONDecodeError as error:
                self.fail(f"Node harness did not emit JSON: {error}\n{completed.stdout}")
            failures = [item for item in report.get("results", []) if item.get("status") != "PASS"]
            self.assertEqual(completed.returncode, 0, json.dumps(failures, indent=2))
            self.assertEqual(report["suite"], "ATLAS_M1_LEARNING")
            self.assertEqual(report["total"], 24)
            self.assertEqual(report["passed"], 24)
            self.assertEqual(report["failed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
