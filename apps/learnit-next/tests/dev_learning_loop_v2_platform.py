#!/usr/bin/env python3
"""DEV-PLATFORM checks for PROG-WP-001 / Learning Loop V2 Wave A."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BASELINE = "8ebafee48cc5277b92776982639a0146ae7e76d0"
FROZEN_LEARNING_HEAD = "ae999472418a18a1181b43a07259a4395afbcf7f"
ALLOWED_PATHS = {
    "apps/learnit-next/src/main.js",
    "apps/learnit-next/src/core/session.js",
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/ui/render.js",
    "apps/learnit-next/src/ports/storage.js",
    "apps/learnit-next/src/adapters/indexeddb.js",
    "apps/learnit-next/tests/dev_learning_loop_v2_platform.py",
}
ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
STRICT = os.environ.get("DEV_PLATFORM_STRICT") == "1"
LEARNING_TREE = os.environ.get("DEV_LEARNING_TREE")

LEARNING_PATHS = {
    "objective_progress": "apps/learnit-next/src/core/objective_progress.js",
    "learning_recommendation": "apps/learnit-next/src/core/learning_recommendation.js",
}


def frozen_learning_text(path: str) -> str:
    if LEARNING_TREE:
        return (Path(LEARNING_TREE) / path).read_text(encoding="utf-8")
    if (ROOT / ".git").exists():
        process = subprocess.run(
            ["git", "show", f"{FROZEN_LEARNING_HEAD}:{path}"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )
        if process.returncode == 0:
            return process.stdout
        raise AssertionError(process.stdout)
    candidate = ROOT / path
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8")
    raise AssertionError(f"cannot materialize frozen DEV-LEARNING blob: {path}")


NODE_HARNESS = r"""
import assert from 'node:assert/strict';
import * as objectiveDomain from './src/core/objective_progress.js';
import * as recommendationDomain from './src/core/learning_recommendation.js';
import {
  createLearningLoopV2DomainAdapters,
  createProgressService,
} from './src/core/progress.js';
import { createSessionService, LEARNING_LOOP_V2_SESSION_META_KEY } from './src/core/session.js';

const clone = value => structuredClone(value);
const keyOf = (courseInstallId, activityRevisionId) => `${courseInstallId}::${activityRevisionId}`;
const objectiveKey = (courseInstallId, objectiveId) => `${courseInstallId}::${objectiveId}`;

const objectives = [
  {objectiveId:'o1', label:'Objectif un'},
  {objectiveId:'o2', label:'Objectif deux'},
];
const qcm = (id, objectiveId, assessmentRole='practice') => ({
  activityLineageId:`${id}-lineage`, activityRevisionId:id, objectiveIds:[objectiveId],
  learningPhase:assessmentRole === 'validation' ? 'validation' : 'application', assessmentRole,
  type:'qcm', prompt:`Prompt ${id}`, explanation:`Explanation ${id}`,
  choices:[{choiceId:`${id}-no`, label:'Non'}, {choiceId:`${id}-yes`, label:'Oui'}],
  correctChoiceId:`${id}-yes`,
});
const activities = [qcm('a','o1'), qcm('b','o1','validation'), qcm('c','o2')];
const courseRecord = {
  courseInstallId:'course-1', title:'Canonical', displayLabel:'Cours',
  course:{objectives:clone(objectives), activities:clone(activities)},
};
const answer = (activity, correct) => ({choiceId:`${activity.activityRevisionId}-${correct ? 'yes' : 'no'}`});

class FakeStorage {
  constructor(record=courseRecord) {
    this.courses = new Map([[record.courseInstallId, clone(record)]]);
    this.progress = new Map();
    this.objectiveProgress = new Map();
    this.meta = new Map();
    this.failures = [];
  }
  arm(method, {key=null, message=`forced ${method} failure`}={}) {
    this.failures.push({method,key,message});
  }
  maybeFail(method, key=null) {
    const index = this.failures.findIndex(item => item.method === method && (item.key === null || item.key === key));
    if (index < 0) return;
    const [failure] = this.failures.splice(index, 1);
    const error = new Error(failure.message);
    error.name = 'QuotaExceededError';
    throw error;
  }
  async getCourse(id) { this.maybeFail('getCourse',id); return clone(this.courses.get(id) ?? null); }
  async listProgress(courseInstallId) {
    this.maybeFail('listProgress',courseInstallId);
    return [...this.progress.values()].filter(x => x.courseInstallId === courseInstallId).map(clone);
  }
  async getProgress(courseInstallId, activityRevisionId) {
    this.maybeFail('getProgress',activityRevisionId);
    return clone(this.progress.get(keyOf(courseInstallId,activityRevisionId)) ?? null);
  }
  async putProgress(record) {
    this.progress.set(keyOf(record.courseInstallId,record.activityRevisionId),clone(record));
    this.maybeFail('putProgress',record.activityRevisionId);
  }
  async listObjectiveProgress(courseInstallId) {
    this.maybeFail('listObjectiveProgress',courseInstallId);
    return [...this.objectiveProgress.values()].filter(x => x.courseInstallId === courseInstallId).map(clone);
  }
  async putObjectiveProgressRecords(records) {
    this.maybeFail('putObjectiveProgressRecords');
    for (const record of records) this.objectiveProgress.set(objectiveKey(record.courseInstallId,record.objectiveId),clone(record));
  }
  async getMeta(key) { this.maybeFail('getMeta',key); return clone(this.meta.get(key) ?? null); }
  async setMeta(key,value) { this.meta.set(key,clone(value)); this.maybeFail('setMeta',key); }
  async deleteMeta(key) { this.meta.delete(key); this.maybeFail('deleteMeta',key); }
}

const integrations = createLearningLoopV2DomainAdapters(objectiveDomain, recommendationDomain);
const makeRuntime = (storage, enabled=true) => {
  const progress = createProgressService(storage, enabled ? integrations : {});
  return {progress, sessions:createSessionService(storage,progress)};
};
const seedFor = (storage, record, activity, correct=false, attempts=1, updatedAt='2026-07-27T00:00:00.000Z') => storage.progress.set(
  keyOf(record.courseInstallId,activity.activityRevisionId),
  {
    courseInstallId:record.courseInstallId,
    activityLineageId:activity.activityLineageId,
    activityRevisionId:activity.activityRevisionId,
    attempts,
    lastAnswer:answer(activity,correct),
    correct,
    completed:true,
    updatedAt,
  },
);
const seed = (storage, activity, correct=false, attempts=1, updatedAt='2026-07-27T00:00:00.000Z') =>
  seedFor(storage, courseRecord, activity, correct, attempts, updatedAt);

const results = [];
async function test(name, fn) {
  try { await fn(); results.push({name,status:'PASS'}); }
  catch (error) { results.push({name,status:'FAIL',error:String(error?.stack || error)}); }
}

await test('frozen module namespaces reproduce the former PLATFORM mismatch', async () => {
  assert.equal(typeof objectiveDomain.reduceObjectiveEvents,'function');
  assert.equal(typeof recommendationDomain.recommendNextObjective,'function');
  assert.equal(objectiveDomain.projectObjectiveProgress,undefined);
  assert.equal(recommendationDomain.recommendLearningAction,undefined);
  assert.throws(
    () => createProgressService(new FakeStorage(), {
      objectiveProgress:objectiveDomain,
      learningRecommendation:recommendationDomain,
    }),
    /projectObjectiveProgress/,
  );
});

await test('PLATFORM adapter composes the exact frozen API and preserves event chronology', async () => {
  const projected = integrations.objectiveProgress.projectObjectiveProgress({
    course:courseRecord.course,
    activityProgress:[
      {
        courseInstallId:'course-1', activityRevisionId:'b', attempts:1,
        correct:true, completed:true, updatedAt:'2026-07-27T01:00:00.000Z',
      },
      {
        courseInstallId:'course-1', activityRevisionId:'a', attempts:2,
        correct:false, completed:true, updatedAt:'2026-07-27T02:00:00.000Z',
      },
    ],
  });
  assert.equal(projected[0].trainingAttempts,2);
  assert.equal(projected[0].validationAttempts,1);
  assert.equal(projected[0].latestValidationCorrect,true);
  assert.equal(projected[0].status,'review-needed');
  const recommendation = integrations.learningRecommendation.recommendLearningAction({
    course:courseRecord.course,
    objectiveProgress:projected,
  });
  assert.equal(recommendation.action,'correct');
  assert.equal(recommendation.objectiveId,'o1');
});

await test('legacy P1 behavior remains available without Wave A adapters', async () => {
  const storage = new FakeStorage();
  storage.listObjectiveProgress = undefined;
  storage.putObjectiveProgressRecords = undefined;
  const {sessions} = makeRuntime(storage,false);
  const started = await sessions.startCourse('course-1');
  assert.equal(started.currentActivity.activityRevisionId,'a');
  assert.deepEqual(storage.meta.get('activeCourse'),{courseInstallId:'course-1',mode:'learn'});
  assert.equal(storage.meta.has(LEARNING_LOOP_V2_SESSION_META_KEY),false);
  const result = await sessions.answer('a',answer(activities[0],false));
  assert.equal(result.correct,false);
  assert.equal(storage.progress.get(keyOf('course-1','a')).completed,true);
});

await test('additive objective state and exact learn index persist', async () => {
  const storage = new FakeStorage();
  const {sessions} = makeRuntime(storage);
  let snapshot = await sessions.startCourse('course-1');
  assert.equal(snapshot.currentIndex,0);
  assert.deepEqual(snapshot.progress.objectives.map(item => item.status),['not-started','not-started']);
  assert.deepEqual(storage.meta.get('activeCourse'),{courseInstallId:'course-1',mode:'learn'});
  assert.equal(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).currentIndex,0);
  const result = await sessions.answer('a',answer(activities[0],false));
  assert.equal(result.progress.objectives[0].status,'review-needed');
  assert.equal(result.progress.recommendation.action,'correct');
  assert.equal(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).currentIndex,1);
  snapshot = await sessions.getSession();
  assert.equal(snapshot.currentActivity.activityRevisionId,'b');
});

await test('runtime recreation resumes course and authored index', async () => {
  const storage = new FakeStorage();
  let runtime = makeRuntime(storage);
  await runtime.sessions.startCourse('course-1');
  await runtime.sessions.answer('a',answer(activities[0],true));
  runtime = makeRuntime(storage);
  const resumed = await runtime.sessions.resumeActiveCourse();
  assert.equal(resumed.mode,'learn');
  assert.equal(resumed.currentIndex,1);
  assert.equal(resumed.currentActivity.activityRevisionId,'b');
  assert.equal(resumed.progress.objectives[0].status,'ready-for-validation');
});

await test('corrective queue, review index and objective state survive recreation', async () => {
  const storage = new FakeStorage();
  seed(storage,activities[0],false);
  seed(storage,activities[2],false);
  let runtime = makeRuntime(storage);
  let snapshot = await runtime.sessions.startReviewQueue('course-1');
  assert.deepEqual(snapshot.review.activityRevisionIds,['a','c']);
  const result = await runtime.sessions.answer('a',answer(activities[0],false));
  assert.equal(result.nextActivity.activityRevisionId,'c');
  assert.equal(storage.meta.get('activeCourse').reviewIndex,1);
  assert.deepEqual(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).reviewQueueActivityRevisionIds,['a','c']);
  runtime = makeRuntime(storage);
  snapshot = await runtime.sessions.resumeActiveCourse();
  assert.equal(snapshot.currentActivity.activityRevisionId,'c');
});

await test('corrective success delegates status semantics to DEV-LEARNING', async () => {
  const storage = new FakeStorage();
  seed(storage,activities[0],false,1,'2026-07-27T00:00:00.000Z');
  seed(storage,activities[1],true,1,'2026-07-27T00:30:00.000Z');
  const runtime = makeRuntime(storage);
  await runtime.sessions.startReviewQueue('course-1');
  const result = await runtime.sessions.answer('a',answer(activities[0],true));
  assert.equal(result.review.remaining,0);
  assert.equal(result.progress.objectives[0].status,'ready-for-validation');
  assert.equal(result.progress.objectives[0].validationAttempts,1);
  assert.equal(JSON.stringify(result).includes('master'),false);
  assert.equal(JSON.stringify(result).includes('certif'),false);
});

await test('objective persistence failure preserves acknowledged activity progress', async () => {
  const storage = new FakeStorage();
  const runtime = makeRuntime(storage);
  await runtime.sessions.startCourse('course-1');
  storage.arm('putObjectiveProgressRecords',{message:'objective quota'});
  await assert.rejects(
    runtime.sessions.answer('a',answer(activities[0],false)),
    error => error.message === 'objective quota',
  );
  const stored = storage.progress.get(keyOf('course-1','a'));
  assert.equal(stored.completed,true);
  assert.equal(stored.correct,false);
});

await test('post-progress session metadata failure restores in-memory review index', async () => {
  const storage = new FakeStorage();
  seed(storage,activities[0],false);
  seed(storage,activities[2],false);
  const runtime = makeRuntime(storage);
  await runtime.sessions.startReviewQueue('course-1');
  storage.arm('setMeta',{key:LEARNING_LOOP_V2_SESSION_META_KEY,message:'session quota'});
  await assert.rejects(
    runtime.sessions.answer('a',answer(activities[0],false)),
    error => error.message === 'session quota',
  );
  assert.equal(storage.progress.get(keyOf('course-1','a')).attempts,2);
  const current = await runtime.sessions.getSession();
  assert.equal(current.currentActivity.activityRevisionId,'a');
});

await test('session provenance v2 captures immutable baselines and derives 0->1 across reload', async () => {
  const storage = new FakeStorage();
  seed(storage, activities[2], true, 3);
  let runtime = makeRuntime(storage);
  const started = await runtime.sessions.startCourse('course-1');
  const metaAtStart = clone(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY));
  assert.equal(metaAtStart.schemaVersion, 2);
  assert.deepEqual(metaAtStart.sessionProvenance.baselineActivityAttempts, {a:0,b:0,c:3});
  assert.deepEqual(Object.keys(metaAtStart.sessionProvenance.beforeObjectiveStates), ['o1','o2']);
  assert.equal(started.sessionDelta.available, true);
  assert.deepEqual(started.sessionDelta.workedObjectiveIds, []);
  assert.deepEqual(started.sessionDelta.changedObjectiveIds, []);
  assert.equal(JSON.stringify(metaAtStart).includes('workedObjectiveIds'), false);
  const baseline = clone(metaAtStart.sessionProvenance);
  const result = await runtime.sessions.answer('a', answer(activities[0], true));
  assert.equal(storage.progress.get(keyOf('course-1','a')).attempts, 1);
  assert.equal(storage.progress.get(keyOf('course-1','c')).attempts, 3);
  assert.deepEqual(result.sessionDelta.workedObjectiveIds, ['o1']);
  assert.deepEqual(result.sessionDelta.changedObjectiveIds, ['o1']);
  assert.deepEqual(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).sessionProvenance, baseline);
  assert.equal(JSON.stringify(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY)).includes('workedObjectiveIds'), false);
  runtime = makeRuntime(storage);
  const resumed = await runtime.sessions.resumeActiveCourse();
  assert.equal(resumed.sessionDelta.available, true);
  assert.deepEqual(resumed.sessionDelta.workedObjectiveIds, ['o1']);
  assert.deepEqual(resumed.sessionDelta.changedObjectiveIds, ['o1']);
  assert.deepEqual(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).sessionProvenance, baseline);
});

await test('review mode derives 3->4 and repeated attempts without duplicate worked objectives', async () => {
  const storage = new FakeStorage();
  seed(storage, activities[0], false, 3);
  const runtime = makeRuntime(storage);
  let snapshot = await runtime.sessions.startReviewQueue('course-1');
  const baseline = clone(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).sessionProvenance);
  assert.equal(baseline.baselineActivityAttempts.a, 3);
  assert.equal(snapshot.sessionDelta.available, true);
  let result = await runtime.sessions.answer('a', answer(activities[0], false));
  assert.equal(storage.progress.get(keyOf('course-1','a')).attempts, 4);
  assert.deepEqual(result.sessionDelta.workedObjectiveIds, ['o1']);
  assert.deepEqual(result.sessionDelta.changedObjectiveIds, []);
  result = await runtime.sessions.answer('a', answer(activities[0], false));
  assert.equal(storage.progress.get(keyOf('course-1','a')).attempts, 5);
  assert.deepEqual(result.sessionDelta.workedObjectiveIds, ['o1']);
  assert.deepEqual(result.sessionDelta.changedObjectiveIds, []);
  assert.deepEqual(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).sessionProvenance, baseline);
});

await test('multi-objective activity derives authored-order worked and changed objective ids', async () => {
  const multi = {...qcm('multi','o1'), objectiveIds:['o1','o2']};
  const record = {
    courseInstallId:'course-multi', title:'Canonical', displayLabel:'Multi',
    course:{objectives:clone(objectives), activities:[multi]},
  };
  const storage = new FakeStorage(record);
  const runtime = makeRuntime(storage);
  await runtime.sessions.startCourse(record.courseInstallId);
  const result = await runtime.sessions.answer('multi', answer(multi, true));
  assert.deepEqual(result.sessionDelta.workedObjectiveIds, ['o1','o2']);
  assert.deepEqual(result.sessionDelta.changedObjectiveIds, ['o1','o2']);
});

await test('lesson and flashcard are worked without inventing objective-state change', async () => {
  const lesson = {
    activityLineageId:'lesson-lineage', activityRevisionId:'lesson',
    objectiveIds:['o1'], learningPhase:'explanation', type:'lesson', prompt:'Lesson',
  };
  const flashcard = {
    activityLineageId:'flash-lineage', activityRevisionId:'flash',
    objectiveIds:['o2'], learningPhase:'explanation', type:'flashcard', prompt:'Flashcard',
  };
  const record = {
    courseInstallId:'course-nonscored', title:'Canonical', displayLabel:'Non scored',
    course:{objectives:clone(objectives), activities:[lesson,flashcard]},
  };
  const storage = new FakeStorage(record);
  const runtime = makeRuntime(storage);
  await runtime.sessions.startCourse(record.courseInstallId);
  let result = await runtime.sessions.answer('lesson', {acknowledged:true});
  assert.equal(result.scored, false);
  assert.deepEqual(result.sessionDelta.workedObjectiveIds, ['o1']);
  assert.deepEqual(result.sessionDelta.changedObjectiveIds, []);
  result = await runtime.sessions.answer('flash', {revealed:true});
  assert.equal(result.scored, false);
  assert.deepEqual(result.sessionDelta.workedObjectiveIds, ['o1','o2']);
  assert.deepEqual(result.sessionDelta.changedObjectiveIds, []);
});

await test('objective state drift without attempts does not become worked or changed and ignores updatedAt', async () => {
  const storage = new FakeStorage();
  seed(storage, activities[2], false, 3, '2026-07-27T00:00:00.000Z');
  const runtime = makeRuntime(storage);
  const started = await runtime.sessions.startCourse('course-1');
  const before = started.sessionDelta.beforeObjectiveStates.o2;
  const stored = clone(storage.progress.get(keyOf('course-1','c')));
  stored.correct = true;
  stored.updatedAt = '2099-01-01T00:00:00.000Z';
  storage.progress.set(keyOf('course-1','c'), stored);
  const current = await runtime.sessions.getSession();
  assert.notEqual(current.sessionDelta.afterObjectiveStates.o2, before);
  assert.deepEqual(current.sessionDelta.workedObjectiveIds, []);
  assert.deepEqual(current.sessionDelta.changedObjectiveIds, []);
  assert.equal(current.sessionDelta.available, true);
});

await test('post-progress meta failure recovers worked fact from immutable baseline and persisted attempts', async () => {
  const storage = new FakeStorage();
  let runtime = makeRuntime(storage);
  await runtime.sessions.startCourse('course-1');
  const baseline = clone(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).sessionProvenance);
  const originalSetMeta = storage.setMeta.bind(storage);
  let failSessionWrite = true;
  storage.setMeta = async (key, value) => {
    if (failSessionWrite && key === LEARNING_LOOP_V2_SESSION_META_KEY) {
      failSessionWrite = false;
      throw new Error('session quota before meta write');
    }
    return originalSetMeta(key, value);
  };
  await assert.rejects(
    runtime.sessions.answer('a', answer(activities[0], false)),
    /session quota before meta write/,
  );
  assert.equal(storage.progress.get(keyOf('course-1','a')).attempts, 1);
  assert.deepEqual(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).sessionProvenance, baseline);
  storage.setMeta = originalSetMeta;
  runtime = makeRuntime(storage);
  const resumed = await runtime.sessions.resumeActiveCourse();
  assert.equal(resumed.sessionDelta.available, true);
  assert.deepEqual(resumed.sessionDelta.workedObjectiveIds, ['o1']);
  assert.deepEqual(resumed.sessionDelta.changedObjectiveIds, ['o1']);
  assert.deepEqual(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).sessionProvenance, baseline);
});

await test('final activity returns final delta before normal active-session cleanup', async () => {
  const finalActivity = qcm('final','o1');
  const record = {
    courseInstallId:'course-final', title:'Canonical', displayLabel:'Final',
    course:{objectives:[clone(objectives[0])], activities:[finalActivity]},
  };
  const storage = new FakeStorage(record);
  const runtime = makeRuntime(storage);
  await runtime.sessions.startCourse(record.courseInstallId);
  const result = await runtime.sessions.answer('final', answer(finalActivity, true));
  assert.equal(result.sessionDelta.available, true);
  assert.deepEqual(result.sessionDelta.workedObjectiveIds, ['o1']);
  assert.deepEqual(result.sessionDelta.changedObjectiveIds, ['o1']);
  assert.equal(storage.meta.has(LEARNING_LOOP_V2_SESSION_META_KEY), false);
  assert.equal(storage.meta.has('activeCourse'), false);
});

await test('legacy v1 resumes navigation without inventing delta and explicit restart creates v2', async () => {
  const storage = new FakeStorage();
  storage.meta.set('activeCourse', {courseInstallId:'course-1',mode:'learn'});
  storage.meta.set(LEARNING_LOOP_V2_SESSION_META_KEY, {
    schemaVersion:1, courseInstallId:'course-1', mode:'learn',
    currentIndex:0, reviewIndex:0, currentActivityRevisionId:'a',
    reviewQueueActivityRevisionIds:[],
  });
  let runtime = makeRuntime(storage);
  const resumed = await runtime.sessions.resumeActiveCourse();
  assert.equal(resumed.currentActivity.activityRevisionId, 'a');
  assert.equal(resumed.sessionDelta.available, false);
  assert.equal(resumed.sessionDelta.reason, 'LEGACY_SESSION_PROVENANCE_UNAVAILABLE');
  assert.equal(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).schemaVersion, 1);
  const restarted = await runtime.sessions.startCourse('course-1');
  assert.equal(restarted.sessionDelta.available, true);
  assert.equal(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY).schemaVersion, 2);
});

await test('invalid v2 provenance fails closed for delta while preserving safe navigation resume', async () => {
  const storage = new FakeStorage();
  storage.meta.set('activeCourse', {courseInstallId:'course-1',mode:'learn'});
  const invalid = {
    schemaVersion:2, courseInstallId:'course-1', mode:'learn',
    currentIndex:0, reviewIndex:0, currentActivityRevisionId:'a',
    reviewQueueActivityRevisionIds:[],
    sessionProvenance:{
      available:true,
      beforeObjectiveStates:{o1:'unknown-state',o2:'not-started'},
      baselineActivityAttempts:{a:0,b:0,c:0},
    },
  };
  storage.meta.set(LEARNING_LOOP_V2_SESSION_META_KEY, clone(invalid));
  const runtime = makeRuntime(storage);
  const resumed = await runtime.sessions.resumeActiveCourse();
  assert.equal(resumed.currentActivity.activityRevisionId, 'a');
  assert.equal(resumed.sessionDelta.available, false);
  assert.equal(resumed.sessionDelta.reason, 'INVALID_SESSION_PROVENANCE');
  assert.deepEqual(storage.meta.get(LEARNING_LOOP_V2_SESSION_META_KEY), invalid);
});

await test('invalid domain output fails after retaining the activity record', async () => {
  const storage = new FakeStorage();
  const invalidProgress = {projectObjectiveProgress:() => [{objectiveId:'unknown'}]};
  const broken = createProgressService(storage,{objectiveProgress:invalidProgress});
  await assert.rejects(broken.recordAttempt({
    courseInstallId:'course-1', course:courseRecord.course, activity:activities[0],
    answer:answer(activities[0],false), correct:false,
  }));
  assert.equal(storage.progress.has(keyOf('course-1','a')),true);
});

await test('malformed frozen API or progress data fails closed', async () => {
  assert.throws(
    () => createLearningLoopV2DomainAdapters(
      {projectObjectiveProgress() {}},
      {recommendLearningAction() {}},
    ),
    /reduceObjectiveEvents/,
  );
  assert.throws(
    () => integrations.objectiveProgress.projectObjectiveProgress({
      course:courseRecord.course,
      activityProgress:[{
        activityRevisionId:'a', attempts:1, correct:'false', completed:true,
        updatedAt:'2026-07-27T00:00:00.000Z',
      }],
    }),
    /invalid correct/,
  );
});

const failed = results.filter(item => item.status === 'FAIL');
console.log(JSON.stringify({ok:failed.length === 0,results},null,2));
if (failed.length) process.exit(1);
"""


class PlatformWaveATests(unittest.TestCase):
    maxDiff = None

    def test_exact_frozen_learning_api_and_platform_adapter(self) -> None:
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required")
        with tempfile.TemporaryDirectory(prefix="learnit-wave-a-platform-") as tmp:
            target = Path(tmp)
            (target / "src/core").mkdir(parents=True)
            (target / "src/ports").mkdir(parents=True)
            shutil.copy2(APP / "src/core/progress.js", target / "src/core/progress.js")
            shutil.copy2(APP / "src/core/session.js", target / "src/core/session.js")
            shutil.copy2(APP / "src/core/activity_semantics.js", target / "src/core/activity_semantics.js")
            shutil.copy2(APP / "src/ports/storage.js", target / "src/ports/storage.js")
            for key, path in LEARNING_PATHS.items():
                (target / "src/core" / f"{key}.js").write_text(
                    frozen_learning_text(path), encoding="utf-8"
                )
            (target / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
            (target / "harness.mjs").write_text(NODE_HARNESS, encoding="utf-8")
            process = subprocess.run(
                [node, "harness.mjs"],
                cwd=target,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
                check=False,
            )
            self.assertEqual(process.returncode, 0, process.stdout)
            report = json.loads(process.stdout)
            self.assertTrue(report["ok"], process.stdout)
            self.assertEqual(len(report["results"]), 20)

    def test_additive_storage_contract(self) -> None:
        storage = (APP / "src/ports/storage.js").read_text(encoding="utf-8")
        indexeddb = (APP / "src/adapters/indexeddb.js").read_text(encoding="utf-8")
        self.assertIn("NEXT_LOCAL_STORAGE_PREFIX = 'learnit.next.v1.'", storage)
        self.assertIn("NEXT_INDEXED_DB_NAME = 'learnit_next_v1'", storage)
        self.assertIn("NEXT_INDEXED_DB_VERSION = 2", storage)
        self.assertIn("NEXT_OBJECTIVE_PROGRESS_STORE = 'objectiveProgress'", storage)
        self.assertIn("keyPath: ['courseInstallId', 'objectiveId']", indexeddb)
        self.assertIn("putObjectiveProgressRecords", indexeddb)
        self.assertNotIn("deleteObjectStore", indexeddb)

    def test_explicit_parallel_lane_composition_uses_actual_exports(self) -> None:
        main = (APP / "src/main.js").read_text(encoding="utf-8")
        render = (APP / "src/ui/render.js").read_text(encoding="utf-8")
        objective_ui = (APP / "src/ui/objective_progress.js").read_text(encoding="utf-8")
        progress = (APP / "src/core/progress.js").read_text(encoding="utf-8")
        self.assertIn("from './core/objective_progress.js'", main)
        self.assertIn("from './core/learning_recommendation.js'", main)
        self.assertIn("from './ui/objective_progress.js'", main)
        self.assertIn("createLearningLoopV2DomainAdapters", main)
        self.assertIn("'reduceObjectiveEvents'", main)
        self.assertIn("'normalizeObjectiveProgress'", main)
        self.assertIn("'recommendNextObjective'", main)
        self.assertIn("'renderObjectiveProgressPanel'", main)
        self.assertIn("reduceObjectiveEvents(objectiveId, events)", progress)
        self.assertIn("recommendNextObjective(authored.objectiveIds, records)", progress)
        self.assertIn("objectiveUi.renderObjectiveProgress", render)
        self.assertIn("'validated-recently': Object.freeze({", objective_ui)
        self.assertIn("label: 'Acquis récemment'", objective_ui)
        self.assertIn("data.recommendation?.objectiveId", objective_ui)
        self.assertNotIn("renderObjectiveBuckets", render)
        self.assertNotIn("mastery", render.lower())
        self.assertNotIn("certification", render.lower())

    @unittest.skipUnless(STRICT, "set DEV_PLATFORM_STRICT=1 for lane topology checks")
    def test_exact_platform_branch_delta(self) -> None:
        self.assertTrue((ROOT / ".git").exists(), "git metadata is required in strict mode")
        process = subprocess.run(
            ["git", "diff", "--name-only", f"{BASELINE}...HEAD"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stdout)
        changed = {line for line in process.stdout.splitlines() if line}
        self.assertTrue(changed, "lane must contain a product delta")
        self.assertTrue(changed <= ALLOWED_PATHS, f"out-of-scope paths: {sorted(changed - ALLOWED_PATHS)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
