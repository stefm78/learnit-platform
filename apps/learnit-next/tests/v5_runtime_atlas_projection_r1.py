#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]

def git_blob_sha1(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()

FROZEN = {
    "contracts/learnit-kit-v5.schema.json": "15e708f9b57ea1b35ff50ad3b3854bd49d5cadc7",
    "authoring/v5/validate_kit.py": "0b93925eb22058878f13bc86554126846d2923d1",
    "authoring/v5/tests/test_validate_v5.py": "61cc3f77e5efb89d350fb4569808f58fd3ecd912",
    "contracts/learnit-kit-v4.schema.json": "e141bd5fafa75dda88a49e8a2094e4589bb4306e",
    "authoring/v4/validate_kit.py": "4ef561dfc1137aa436b4d8c8820db421ab6e1861",
    "authoring/v4/tests/test_validate_v4.py": "85debca78c3ec342d9e4e7ed63a033fd0968e72e",
    "apps/learnit-next/src/core/activity_semantics.js": "07c4595332419da1da0473a9715f09894620f6bd",
    "apps/learnit-next/src/adapters/atlas_indexeddb.js": "c8b6f27326ba6aa4b7caf16ab6ef178f0812312f",
    "apps/learnit-next/src/ports/atlas_storage.js": "8def176ac7b96748a2384af97f23183016a4a4be",
    "apps/learnit-next/src/ui/atlas_session.js": "712c378a8e7675b6656c84efb6ba23a866fc5292",
    "apps/learnit-next/src/ui/activity_presenters.js": "fe38702b97f2f243101bfd0ae894b43aaeb2fbaf",
    "apps/learnit-next/src/ui/media.js": "1c84d5da04025cf372e3496fb7d25c088d1a0650",
}
for path, expected in FROZEN.items():
    actual = git_blob_sha1(path)
    assert actual == expected, f"frozen blob drift: {path}: {actual}"

probe = r'''
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
globalThis.crypto ??= webcrypto;

import {
  sha256Canonical,
  validatePackageObject,
} from './apps/learnit-next/src/core/contract.js';
import {
  buildInstallationPlan,
} from './apps/learnit-next/src/core/import.js';
import {
  projectActivityPresentation,
  projectFeedbackMedia,
} from './apps/learnit-next/src/integration/atlas/activity_projection.js';
import {
  reconstructAtlasHintPrefix,
  requestNextAtlasV5Hint,
} from './apps/learnit-next/src/integration/atlas/session.js';

const Z = 'sha256:' + '0'.repeat(64);
const ids = {
  packageLineage: '11111111-1111-4111-8111-111111111111',
  packageRevision: '22222222-2222-4222-8222-222222222222',
  courseLineage: '33333333-3333-4333-8333-333333333333',
  courseRevision: '44444444-4444-4444-8444-444444444444',
  objective: '55555555-5555-4555-8555-555555555555',
  activityLineage: '66666666-6666-4666-8666-666666666666',
  activityRevision: '77777777-7777-4777-8777-777777777777',
  choiceA: '88888888-8888-4888-8888-888888888888',
  choiceB: '99999999-9999-4999-8999-999999999999',
  promptAsset: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  feedbackAsset: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
};

function basePackage(contract = 'learnit.kit.v5') {
  return {
    contract,
    packageLineageId: ids.packageLineage,
    packageRevisionId: ids.packageRevision,
    packageRevisionDigest: Z,
    title: 'Runtime V5 probe',
    versionLabel: 'r1',
    language: 'fr',
    assets: [
      {
        assetId: ids.promptAsset,
        type: 'image',
        format: 'svg',
        alt: 'Prompt image',
        pedagogicalRole: 'question_stimulus',
        data: '<svg xmlns="http://www.w3.org/2000/svg"><text>PROMPT_MEDIA</text></svg>',
      },
      {
        assetId: ids.feedbackAsset,
        type: 'image',
        format: 'svg',
        alt: 'Feedback image',
        pedagogicalRole: 'misconception_fix',
        data: '<svg xmlns="http://www.w3.org/2000/svg"><text>FEEDBACK_MEDIA_SECRET</text></svg>',
      },
    ],
    courses: [{
      courseLineageId: ids.courseLineage,
      courseRevisionId: ids.courseRevision,
      courseRevisionDigest: Z,
      title: 'Course',
      estimatedMinutes: 5,
      objectives: [{ objectiveId: ids.objective, label: 'Objectif' }],
      activities: [{
        activityLineageId: ids.activityLineage,
        activityRevisionId: ids.activityRevision,
        activityRevisionDigest: Z,
        objectiveIds: [ids.objective],
        type: 'qcm',
        prompt: 'Question ?',
        explanation: 'Explanation',
        difficulty: 'easy',
        learningPhase: 'application',
        assessmentRole: 'practice',
        choices: [
          { choiceId: ids.choiceA, label: 'A' },
          { choiceId: ids.choiceB, label: 'B' },
        ],
        correctChoiceId: ids.choiceA,
        media: [
          { assetId: ids.promptAsset, placement: 'prompt' },
          { assetId: ids.feedbackAsset, placement: 'feedback' },
        ],
        hints: ['HINT_SECRET_1', 'HINT_SECRET_2', 'HINT_SECRET_3'],
        references: [{
          url: 'https://example.org/reference',
          label: 'Reference label',
          hook: 'Reference hook',
        }],
      }],
    }],
  };
}

async function fillDigests(pkg) {
  for (const course of pkg.courses) {
    for (const activity of course.activities) {
      activity.activityRevisionDigest = await sha256Canonical(
        activity,
        { omitRootKey: 'activityRevisionDigest' },
      );
    }
    course.courseRevisionDigest = await sha256Canonical(
      course,
      { omitRootKey: 'courseRevisionDigest' },
    );
  }
  pkg.packageRevisionDigest = await sha256Canonical(
    pkg,
    { omitRootKey: 'packageRevisionDigest' },
  );
  return pkg;
}

const v5 = await fillDigests(basePackage());
const v5Result = await validatePackageObject(v5);
assert.equal(v5Result.ok, true, JSON.stringify(v5Result.errors));

const v4 = structuredClone(v5);
v4.contract = 'learnit.kit.v4';
delete v4.courses[0].activities[0].hints;
delete v4.courses[0].activities[0].references;
await fillDigests(v4);
const v4Result = await validatePackageObject(v4);
assert.equal(v4Result.ok, true, JSON.stringify(v4Result.errors));

const widenedV4 = structuredClone(v4);
widenedV4.courses[0].activities[0].hints = ['must remain forbidden'];
const widenedV4Result = await validatePackageObject(widenedV4);
assert.equal(widenedV4Result.ok, false);
assert.equal(
  widenedV4Result.errors.some(error => (
    error.code === 'additional_property'
    && error.path.endsWith('.hints')
  )),
  true,
);

const plan = buildInstallationPlan(v5, new Date('2026-09-24T20:00:00.000Z'));
assert.equal(plan.package.contract, 'learnit.kit.v5');
assert.equal(plan.courses[0].contract, 'learnit.kit.v5');
assert.deepEqual(plan.courses[0].packageAssets, v5.assets);

let fetchCalls = 0;
globalThis.fetch = async () => {
  fetchCalls += 1;
  throw new Error('NETWORK_FORBIDDEN');
};

const activity = v5.courses[0].activities[0];
const initial = projectActivityPresentation(activity, {
  assets: v5.assets,
  contract: 'learnit.kit.v5',
});
const initialSerialized = JSON.stringify(initial);
assert.equal(Object.hasOwn(initial, 'hints'), false);
assert.equal(initialSerialized.includes('HINT_SECRET_1'), false);
assert.equal(initialSerialized.includes('HINT_SECRET_2'), false);
assert.equal(initialSerialized.includes('HINT_SECRET_3'), false);
assert.equal(initial.media.length, 1);
assert.equal(initial.media[0].assetId, ids.promptAsset);
assert.equal(initialSerialized.includes(ids.feedbackAsset), false);
assert.equal(initialSerialized.includes('FEEDBACK_MEDIA_SECRET'), false);
assert.deepEqual(initial.references, [{
  url: 'https://example.org/reference',
  label: 'Reference label',
  hook: 'Reference hook',
}]);
assert.equal(fetchCalls, 0);

assert.throws(
  () => projectFeedbackMedia(activity, {
    assets: v5.assets,
    contract: 'learnit.kit.v5',
  }),
  /V5_FEEDBACK_MEDIA_TRANSITION_REQUIRED/,
);
const feedback = projectFeedbackMedia(activity, {
  assets: v5.assets,
  contract: 'learnit.kit.v5',
  transitionAuthorized: true,
});
assert.equal(feedback.length, 1);
assert.equal(feedback[0].assetId, ids.feedbackAsset);
assert.equal(fetchCalls, 0);

const sessionRef = { sessionId: 'session-1', planId: 'plan-1' };
const contentRevisionRef = {
  packageLineageId: ids.packageLineage,
  packageRevisionId: ids.packageRevision,
  packageDigest: v5.packageRevisionDigest,
};
const state = {
  resumeStates: [{
    sessionRef,
    contentRevisionRef,
    nextItemPosition: 0,
    itemStates: [{
      itemPosition: 0,
      assistance: 'none',
      assistanceUseIds: [],
    }],
  }],
  atlasMeta: { assistanceUses: {} },
};
const itemState = state.resumeStates[0].itemStates[0];
let assistanceCalls = 0;
function persist(kind) {
  assistanceCalls += 1;
  const id = `assist-${assistanceCalls}`;
  const record = {
    assistanceUseId: id,
    sessionRef,
    itemPosition: 0,
    assistanceKind: kind,
  };
  state.atlasMeta.assistanceUses[id] = record;
  itemState.assistance = 'used';
  itemState.assistanceUseIds.push(id);
  return { committed: true, record };
}

// Non-hint assistance is durable but must not advance hint rank.
persist('guided-step');
let prefix = reconstructAtlasHintPrefix(state, {
  sessionRef,
  itemPosition: 0,
  contentRevisionRef,
  hints: activity.hints,
});
assert.equal(prefix.count, 0);

let revealed = await requestNextAtlasV5Hint({
  readState: () => state,
  requestHelp: async kind => persist(kind),
  sessionRef,
  itemPosition: 0,
  contentRevisionRef,
  hints: activity.hints,
});
assert.equal(revealed.status, 'revealed');
assert.equal(revealed.index, 0);
assert.equal(revealed.text, 'HINT_SECRET_1');
prefix = reconstructAtlasHintPrefix(state, {
  sessionRef,
  itemPosition: 0,
  contentRevisionRef,
  hints: activity.hints,
});
assert.deepEqual(prefix.revealed, ['HINT_SECRET_1']);

// Commit succeeded but rendering can crash: resume derives the committed prefix.
const afterCrashResume = reconstructAtlasHintPrefix(state, {
  sessionRef,
  itemPosition: 0,
  contentRevisionRef,
  hints: activity.hints,
});
assert.deepEqual(afterCrashResume.revealed, ['HINT_SECRET_1']);

revealed = await requestNextAtlasV5Hint({
  readState: () => state,
  requestHelp: async kind => persist(kind),
  sessionRef,
  itemPosition: 0,
  contentRevisionRef,
  hints: activity.hints,
});
assert.equal(revealed.index, 1);
assert.equal(revealed.text, 'HINT_SECRET_2');
assert.deepEqual(revealed.prefix.revealed, ['HINT_SECRET_1', 'HINT_SECRET_2']);

revealed = await requestNextAtlasV5Hint({
  readState: () => state,
  requestHelp: async kind => persist(kind),
  sessionRef,
  itemPosition: 0,
  contentRevisionRef,
  hints: activity.hints,
});
assert.equal(revealed.index, 2);
assert.equal(revealed.text, 'HINT_SECRET_3');
assert.deepEqual(
  revealed.prefix.revealed,
  ['HINT_SECRET_1', 'HINT_SECRET_2', 'HINT_SECRET_3'],
);

const callsBeforeExhausted = assistanceCalls;
const exhausted = await requestNextAtlasV5Hint({
  readState: () => state,
  requestHelp: async kind => persist(kind),
  sessionRef,
  itemPosition: 0,
  contentRevisionRef,
  hints: activity.hints,
});
assert.equal(exhausted.status, 'exhausted');
assert.equal(assistanceCalls, callsBeforeExhausted);

const failureState = structuredClone({
  resumeStates: [{
    sessionRef,
    contentRevisionRef,
    nextItemPosition: 0,
    itemStates: [{
      itemPosition: 0,
      assistance: 'none',
      assistanceUseIds: [],
    }],
  }],
  atlasMeta: { assistanceUses: {} },
});
await assert.rejects(
  requestNextAtlasV5Hint({
    readState: () => failureState,
    requestHelp: async () => { throw new Error('PERSISTENCE_FAILED'); },
    sessionRef,
    itemPosition: 0,
    contentRevisionRef,
    hints: activity.hints,
  }),
  /PERSISTENCE_FAILED/,
);
assert.equal(
  reconstructAtlasHintPrefix(failureState, {
    sessionRef,
    itemPosition: 0,
    contentRevisionRef,
    hints: activity.hints,
  }).count,
  0,
);

let mismatchCalls = 0;
await assert.rejects(
  requestNextAtlasV5Hint({
    readState: () => failureState,
    requestHelp: async () => {
      mismatchCalls += 1;
      return { committed: true, record: {} };
    },
    sessionRef,
    itemPosition: 0,
    contentRevisionRef: {
      ...contentRevisionRef,
      packageRevisionId: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    },
    hints: activity.hints,
  }),
  /ATLAS_V5_CONTENT_REVISION_MISMATCH/,
);
assert.equal(mismatchCalls, 0);

const concurrentState = structuredClone(failureState);
let releaseFirst;
const gate = new Promise(resolve => { releaseFirst = resolve; });
let concurrentCalls = 0;
async function delayedPersist(kind) {
  concurrentCalls += 1;
  await gate;
  const id = 'concurrent-hint-1';
  const record = {
    assistanceUseId: id,
    sessionRef,
    itemPosition: 0,
    assistanceKind: kind,
  };
  concurrentState.atlasMeta.assistanceUses[id] = record;
  concurrentState.resumeStates[0].itemStates[0].assistance = 'used';
  concurrentState.resumeStates[0].itemStates[0].assistanceUseIds.push(id);
  return { committed: true, record };
}
const first = requestNextAtlasV5Hint({
  readState: () => concurrentState,
  requestHelp: delayedPersist,
  sessionRef,
  itemPosition: 0,
  contentRevisionRef,
  hints: activity.hints,
});
const second = await requestNextAtlasV5Hint({
  readState: () => concurrentState,
  requestHelp: delayedPersist,
  sessionRef,
  itemPosition: 0,
  contentRevisionRef,
  hints: activity.hints,
});
assert.equal(second.status, 'in-flight');
assert.equal(concurrentCalls, 1);
releaseFirst();
const firstResult = await first;
assert.equal(firstResult.index, 0);
assert.equal(concurrentCalls, 1);

assert.equal(fetchCalls, 0);
console.log('V5_RUNTIME_ATLAS_PROJECTION_CAUSAL_PASS');
'''

result = subprocess.run(
    ["node", "--input-type=module", "-e", probe],
    cwd=ROOT,
    check=True,
    text=True,
    capture_output=True,
)
assert "V5_RUNTIME_ATLAS_PROJECTION_CAUSAL_PASS" in result.stdout
print("V5_RUNTIME_ATLAS_PROJECTION_R1_PASS")
print("REFERENCES_RUNTIME_FETCH_NONE")
print("NEW_ATLAS_PERSISTENCE_SCHEMA_NONE")
