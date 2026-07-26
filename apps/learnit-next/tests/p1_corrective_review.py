#!/usr/bin/env python3
"""Independent contradictory QA for issue #116 / PROD-WP-003 P1 review loop.

Run this file from a temporary worktree checked out at the exact DEV commit, or set
P1_PRODUCT_TREE to such a tree. The QA branch itself contains only this test.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

BASELINE = "41a4268e6c9baf900f892bd6bd9cc54e6c7ec5f9"
DEV_COMMIT = "bf765738d0f7df7be0a267e0c62643c26e4749f8"
EXPECTED_CHANGED_PATHS = {
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/core/session.js",
    "apps/learnit-next/src/main.js",
    "apps/learnit-next/src/ui/render.js",
    "work-packages/PROD-WP-003.json",
}
FORBIDDEN_CHANGED_PREFIXES = (
    ".github/",
    "contracts/",
    "authoring/",
    "apps/player/",
)
ROOT = (Path(os.environ["P1_PRODUCT_TREE"]) if "P1_PRODUCT_TREE" in os.environ else Path(__file__).resolve().parents[3]).resolve()
STRICT = os.environ.get("P1_STRICT", "0") == "1"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
        timeout=120,
    )


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


NODE_HARNESS = r"""
import assert from 'node:assert/strict';
import { deriveReviewQueue, createProgressService } from './progress.mjs';
import { createSessionService, AnswerValidationError } from './session.mjs';

const clone = value => structuredClone(value);
const keyOf = (courseInstallId, activityRevisionId) => `${courseInstallId}::${activityRevisionId}`;

class FakeStorage {
  constructor(courseRecord) {
    this.courses = new Map([[courseRecord.courseInstallId, clone(courseRecord)]]);
    this.progress = new Map();
    this.meta = new Map();
    this.calls = { listProgress: 0, getProgress: 0, putProgress: 0, getMeta: 0, setMeta: 0, deleteMeta: 0 };
    this.order = 'normal';
    this.failures = [];
  }
  arm(method, {afterMutation = false, message = `forced ${method} failure`} = {}) {
    this.failures.push({method, afterMutation, message});
  }
  maybeFail(method, phase) {
    const index = this.failures.findIndex(item => item.method === method && (item.afterMutation ? phase === 'after' : phase === 'before'));
    if (index < 0) return;
    const [failure] = this.failures.splice(index, 1);
    const error = new Error(failure.message);
    error.name = 'QuotaExceededError';
    throw error;
  }
  async getCourse(id) { return clone(this.courses.get(id) ?? null); }
  async listProgress(courseInstallId) {
    this.calls.listProgress += 1;
    this.maybeFail('listProgress', 'before');
    let values = [...this.progress.values()].filter(record => record.courseInstallId === courseInstallId).map(clone);
    if (this.order === 'reverse') values.reverse();
    this.maybeFail('listProgress', 'after');
    return values;
  }
  async getProgress(courseInstallId, activityRevisionId) {
    this.calls.getProgress += 1;
    this.maybeFail('getProgress', 'before');
    const value = clone(this.progress.get(keyOf(courseInstallId, activityRevisionId)) ?? null);
    this.maybeFail('getProgress', 'after');
    return value;
  }
  async putProgress(record) {
    this.calls.putProgress += 1;
    this.maybeFail('putProgress', 'before');
    this.progress.set(keyOf(record.courseInstallId, record.activityRevisionId), clone(record));
    this.maybeFail('putProgress', 'after');
  }
  async getMeta(key) {
    this.calls.getMeta += 1;
    this.maybeFail('getMeta', 'before');
    const value = clone(this.meta.get(key) ?? null);
    this.maybeFail('getMeta', 'after');
    return value;
  }
  async setMeta(key, value) {
    this.calls.setMeta += 1;
    this.maybeFail('setMeta', 'before');
    this.meta.set(key, clone(value));
    this.maybeFail('setMeta', 'after');
  }
  async deleteMeta(key) {
    this.calls.deleteMeta += 1;
    this.maybeFail('deleteMeta', 'before');
    this.meta.delete(key);
    this.maybeFail('deleteMeta', 'after');
  }
}

const qcm = (id, correct = `${id}-yes`) => ({
  activityLineageId: `${id}-lineage`, activityRevisionId: id, type: 'qcm', prompt: `Prompt ${id}`,
  explanation: `Explanation ${id}`, choices: [{choiceId: `${id}-no`, label: 'No'}, {choiceId: correct, label: 'Yes'}],
  correctChoiceId: correct,
});
const fill = id => ({
  activityLineageId: `${id}-lineage`, activityRevisionId: id, type: 'fill', prompt: `Prompt ${id}`,
  explanation: `Explanation ${id}`,
  segments: [{text: 'x='}, {slotId: `${id}-slot-1`}, {text: '+'}, {slotId: `${id}-slot-2`}],
  tokens: [{tokenId: `${id}-one`, label: '1', maxUses: 1}, {tokenId: `${id}-two`, label: '2', maxUses: 1}],
  answers: [{slotId: `${id}-slot-1`, tokenId: `${id}-one`}, {slotId: `${id}-slot-2`, tokenId: `${id}-two`}],
});
const activities = [qcm('a'), qcm('b'), fill('c')];
const courseRecord = {
  courseInstallId: 'course-install-1', title: 'Canonical', displayLabel: 'Course',
  course: { activities: clone(activities) },
};
const incorrect = activity => activity.type === 'qcm'
  ? {choiceId: `${activity.activityRevisionId}-no`}
  : {[`${activity.activityRevisionId}-slot-1`]: `${activity.activityRevisionId}-two`, [`${activity.activityRevisionId}-slot-2`]: `${activity.activityRevisionId}-one`};
const correct = activity => activity.type === 'qcm'
  ? {choiceId: activity.correctChoiceId}
  : Object.fromEntries(activity.answers.map(item => [item.slotId, item.tokenId]));
const makeRuntime = storage => {
  const progress = createProgressService(storage);
  const sessions = createSessionService(storage, progress);
  return {progress, sessions};
};
const seed = async (storage, activity, {isCorrect = false, attempts = 1, completed = true, updatedAt = '2026-07-26T00:00:00.000Z'} = {}) => {
  storage.progress.set(keyOf(courseRecord.courseInstallId, activity.activityRevisionId), {
    courseInstallId: courseRecord.courseInstallId,
    activityLineageId: activity.activityLineageId,
    activityRevisionId: activity.activityRevisionId,
    attempts,
    lastAnswer: isCorrect ? correct(activity) : incorrect(activity),
    correct: isCorrect,
    completed,
    updatedAt,
  });
};

const results = [];
async function test(name, fn) {
  try { await fn(); results.push({name, status:'PASS'}); }
  catch (error) { results.push({name, status:'FAIL', error: String(error?.stack || error)}); }
}

await test('01 empty queue projection', async () => {
  assert.deepEqual(deriveReviewQueue(courseRecord.course, []), []);
});

await test('02-05 qcm incorrect deduplicated completed then correct removal', async () => {
  const storage = new FakeStorage(courseRecord); const {sessions, progress} = makeRuntime(storage);
  await sessions.startCourse(courseRecord.courseInstallId);
  let result = await sessions.answer('a', incorrect(activities[0]));
  assert.equal(result.correct, false); assert.equal(result.completed, true);
  assert.deepEqual(progress.reviewQueue(courseRecord.course, await progress.getProgress(courseRecord.courseInstallId)).map(x => x.activityRevisionId), ['a']);
  await sessions.startReviewQueue(courseRecord.courseInstallId);
  result = await sessions.answer('a', incorrect(activities[0]));
  assert.equal(result.nextActivity.activityRevisionId, 'a');
  let records = await progress.getProgress(courseRecord.courseInstallId);
  assert.equal(records.length, 1); assert.equal(records[0].attempts, 2); assert.equal(records[0].completed, true);
  result = await sessions.answer('a', correct(activities[0]));
  records = await progress.getProgress(courseRecord.courseInstallId);
  assert.equal(records.length, 1); assert.equal(records[0].attempts, 3); assert.equal(records[0].completed, true);
  assert.equal(result.review.remaining, 0); assert.equal(result.nextActivity, null);
});

await test('06-07 multiple activities author order independent of storage order', async () => {
  const storage = new FakeStorage(courseRecord); const {progress} = makeRuntime(storage);
  await seed(storage, activities[2], {updatedAt:'2026-07-26T00:00:01.000Z'});
  await seed(storage, activities[0], {updatedAt:'2026-07-26T00:00:03.000Z'});
  await seed(storage, activities[1], {updatedAt:'2026-07-26T00:00:02.000Z'});
  storage.order = 'normal';
  const first = progress.reviewQueue(courseRecord.course, await progress.getProgress(courseRecord.courseInstallId)).map(x => x.activityRevisionId);
  storage.order = 'reverse';
  const second = progress.reviewQueue(courseRecord.course, await progress.getProgress(courseRecord.courseInstallId)).map(x => x.activityRevisionId);
  assert.deepEqual(first, ['a','b','c']); assert.deepEqual(second, first);
});

await test('08-09 fill incorrect then correct and attempts retained', async () => {
  const storage = new FakeStorage(courseRecord); const {sessions, progress} = makeRuntime(storage);
  await seed(storage, activities[0], {isCorrect:true}); await seed(storage, activities[1], {isCorrect:true});
  await sessions.startCourse(courseRecord.courseInstallId);
  let result = await sessions.answer('c', incorrect(activities[2]));
  assert.equal(result.correct, false); assert.equal(result.completed, true);
  await sessions.startReviewQueue(courseRecord.courseInstallId);
  result = await sessions.answer('c', correct(activities[2]));
  assert.equal(result.correct, true); assert.equal(result.review.remaining, 0);
  const record = (await progress.getProgress(courseRecord.courseInstallId)).find(x => x.activityRevisionId === 'c');
  assert.equal(record.attempts, 2); assert.equal(record.completed, true);
});

await test('10 empty review opening deletes active metadata', async () => {
  const storage = new FakeStorage(courseRecord); const {sessions} = makeRuntime(storage);
  const snapshot = await sessions.startReviewQueue(courseRecord.courseInstallId);
  assert.equal(snapshot.currentActivity, null); assert.equal(snapshot.review.remaining, 0); assert.equal(storage.meta.has('activeCourse'), false);
});

await test('11 one-item review error remains on same item', async () => {
  const storage = new FakeStorage(courseRecord); await seed(storage, activities[0]); const {sessions} = makeRuntime(storage);
  let snapshot = await sessions.startReviewQueue(courseRecord.courseInstallId); assert.equal(snapshot.currentActivity.activityRevisionId, 'a');
  const result = await sessions.answer('a', incorrect(activities[0]));
  assert.equal(result.nextActivity.activityRevisionId, 'a'); assert.equal(result.review.remaining, 1);
});

await test('12-14 multi-item deterministic rotation and success next item', async () => {
  const storage = new FakeStorage(courseRecord); for (const activity of activities) await seed(storage, activity); const {sessions} = makeRuntime(storage);
  let snapshot = await sessions.startReviewQueue(courseRecord.courseInstallId); assert.equal(snapshot.currentActivity.activityRevisionId, 'a');
  let result = await sessions.answer('a', incorrect(activities[0])); assert.equal(result.nextActivity.activityRevisionId, 'b');
  result = await sessions.answer('b', correct(activities[1])); assert.equal(result.nextActivity.activityRevisionId, 'c');
  result = await sessions.answer('c', correct(activities[2])); assert.equal(result.nextActivity.activityRevisionId, 'a');
});

await test('15 exit to normal flow does not clear review queue', async () => {
  const storage = new FakeStorage(courseRecord); await seed(storage, activities[0]); const {sessions, progress} = makeRuntime(storage);
  await sessions.startReviewQueue(courseRecord.courseInstallId);
  const normal = await sessions.startCourse(courseRecord.courseInstallId);
  assert.equal(normal.mode, 'learn');
  const queue = progress.reviewQueue(courseRecord.course, await progress.getProgress(courseRecord.courseInstallId));
  assert.deepEqual(queue.map(x => x.activityRevisionId), ['a']);
});

await test('16 fully completed course can still expose review queue', async () => {
  const storage = new FakeStorage(courseRecord); for (const activity of activities) await seed(storage, activity); const {sessions} = makeRuntime(storage);
  const snapshot = await sessions.startReviewQueue(courseRecord.courseInstallId);
  assert.equal(snapshot.progress.isComplete, true); assert.equal(snapshot.review.remaining, 3); assert.equal(snapshot.currentActivity.activityRevisionId, 'a');
});

await test('17-18 runtime recreation resumes active review', async () => {
  const storage = new FakeStorage(courseRecord); await seed(storage, activities[0]); await seed(storage, activities[1]);
  let runtime = makeRuntime(storage); await runtime.sessions.startReviewQueue(courseRecord.courseInstallId);
  await runtime.sessions.answer('a', incorrect(activities[0]));
  assert.deepEqual(storage.meta.get('activeCourse'), {courseInstallId:courseRecord.courseInstallId, mode:'review', reviewIndex:1});
  runtime = makeRuntime(storage); const resumed = await runtime.sessions.resumeActiveCourse();
  assert.equal(resumed.mode, 'review'); assert.equal(resumed.currentActivity.activityRevisionId, 'b');
});

await test('19 legacy activeCourse metadata without mode resumes learn', async () => {
  const storage = new FakeStorage(courseRecord); storage.meta.set('activeCourse', {courseInstallId:courseRecord.courseInstallId}); const {sessions} = makeRuntime(storage);
  const resumed = await sessions.resumeActiveCourse(); assert.equal(resumed.mode, 'learn'); assert.equal(resumed.currentActivity.activityRevisionId, 'a');
});

await test('20 absent invalid and oversized reviewIndex are normalized', async () => {
  for (const value of [undefined, -1, '1', 999]) {
    const storage = new FakeStorage(courseRecord); await seed(storage, activities[0]); await seed(storage, activities[1]);
    const meta = {courseInstallId:courseRecord.courseInstallId, mode:'review'}; if (value !== undefined) meta.reviewIndex = value;
    storage.meta.set('activeCourse', meta); const {sessions} = makeRuntime(storage); const resumed = await sessions.resumeActiveCourse();
    const expected = value === 999 ? 'b' : 'a'; assert.equal(resumed.currentActivity.activityRevisionId, expected, `reviewIndex=${String(value)}`);
  }
});

await test('21 queue empty before resume deletes stale metadata', async () => {
  const storage = new FakeStorage(courseRecord); storage.meta.set('activeCourse', {courseInstallId:courseRecord.courseInstallId, mode:'review', reviewIndex:2}); const {sessions} = makeRuntime(storage);
  const resumed = await sessions.resumeActiveCourse(); assert.equal(resumed.currentActivity, null); assert.equal(resumed.review.remaining, 0); assert.equal(storage.meta.has('activeCourse'), false);
});

await test('22 unknown and out-of-sequence answers perform no progress write', async () => {
  const storage = new FakeStorage(courseRecord); const {sessions} = makeRuntime(storage); await sessions.startCourse(courseRecord.courseInstallId);
  const before = clone(storage.calls);
  await assert.rejects(() => sessions.answer('b', incorrect(activities[1])), error => error instanceof AnswerValidationError && error.code === 'out_of_sequence');
  await assert.rejects(() => sessions.answer('a', {choiceId:'unknown'}), error => error instanceof AnswerValidationError && error.code === 'unknown_choice');
  assert.equal(storage.calls.putProgress, before.putProgress); assert.equal(storage.progress.size, 0);
});

await test('23 invalid fill performs no progress write', async () => {
  const storage = new FakeStorage(courseRecord); await seed(storage, activities[0], {isCorrect:true}); await seed(storage, activities[1], {isCorrect:true}); const {sessions} = makeRuntime(storage);
  await sessions.startCourse(courseRecord.courseInstallId); const before = storage.calls.putProgress;
  await assert.rejects(() => sessions.answer('c', {[`${activities[2].activityRevisionId}-slot-1`]:`${activities[2].activityRevisionId}-one`}), error => error instanceof AnswerValidationError && error.code === 'incomplete_fill');
  assert.equal(storage.calls.putProgress, before); assert.equal(storage.progress.has(keyOf(courseRecord.courseInstallId,'c')), false);
});

await test('24a putProgress failure rejects and preserves visible queue', async () => {
  const storage = new FakeStorage(courseRecord); await seed(storage, activities[0]); await seed(storage, activities[1]); const {sessions} = makeRuntime(storage);
  await sessions.startReviewQueue(courseRecord.courseInstallId); storage.arm('putProgress');
  await assert.rejects(() => sessions.answer('a', incorrect(activities[0])), /forced putProgress failure/);
  const snapshot = await sessions.getSession(); assert.equal(snapshot.currentActivity.activityRevisionId, 'a');
});

await test('24b metadata write failure must not advance an unacknowledged review', async () => {
  const storage = new FakeStorage(courseRecord); await seed(storage, activities[0]); await seed(storage, activities[1]); const {sessions} = makeRuntime(storage);
  await sessions.startReviewQueue(courseRecord.courseInstallId); storage.arm('setMeta');
  await assert.rejects(() => sessions.answer('a', incorrect(activities[0])), /forced setMeta failure/);
  const snapshot = await sessions.getSession();
  assert.equal(snapshot.currentActivity.activityRevisionId, 'a', 'a rejected answer must not invisibly advance the review cursor');
});

await test('24c transient resume read failure must not delete valid active metadata', async () => {
  const storage = new FakeStorage(courseRecord); await seed(storage, activities[0]); storage.meta.set('activeCourse', {courseInstallId:courseRecord.courseInstallId, mode:'review', reviewIndex:0}); const {sessions} = makeRuntime(storage);
  storage.arm('listProgress'); const resumed = await sessions.resumeActiveCourse();
  assert.equal(resumed, null); assert.equal(storage.meta.has('activeCourse'), true, 'a transient read failure must not destroy resumable metadata');
});

await test('25 two successive reads without writes are stable', async () => {
  const storage = new FakeStorage(courseRecord); await seed(storage, activities[0]); const {sessions} = makeRuntime(storage);
  await sessions.startReviewQueue(courseRecord.courseInstallId); const first = await sessions.getSession(); const meta = clone(storage.meta.get('activeCourse')); const second = await sessions.getSession();
  assert.deepEqual(second, first); assert.deepEqual(storage.meta.get('activeCourse'), meta);
});

const failed = results.filter(item => item.status === 'FAIL');
console.log(JSON.stringify({total:results.length, passed:results.length-failed.length, failed:failed.length, results}, null, 2));
if (failed.length) process.exitCode = 1;
"""


class P1CorrectiveReviewQA(unittest.TestCase):
    maxDiff = None

    def test_00_exact_scope_contract_and_isolation(self) -> None:
        if not (ROOT / ".git").exists():
            if STRICT:
                self.fail(f"P1_PRODUCT_TREE is not a Git worktree: {ROOT}")
            self.skipTest("static provenance check requires the exact Git worktree")
        for commit in (BASELINE, DEV_COMMIT):
            result = git("cat-file", "-e", f"{commit}^{{commit}}", check=False)
            if result.returncode:
                self.fail(f"required commit unavailable: {commit}\n{result.stdout}")
        changed = set(filter(None, git("diff", "--name-only", f"{BASELINE}..{DEV_COMMIT}").stdout.splitlines()))
        self.assertEqual(EXPECTED_CHANGED_PATHS, changed)
        self.assertFalse(any(path.startswith(FORBIDDEN_CHANGED_PREFIXES) for path in changed), changed)
        self.assertNotIn("apps/learnit-next/src/adapters/indexeddb.js", changed)
        self.assertNotIn("apps/learnit-next/src/ports/storage.js", changed)
        self.assertNotIn("apps/learnit-next/source_manifest.json", changed)
        self.assertNotIn("contracts/learnit-kit-v2.schema.json", changed)
        # Frozen paths may be referenced through the accepted-input manifest rather
        # than materialized on this role branch. When a path exists at both commits,
        # its blob identity must be unchanged; in all cases it must not appear in the diff.
        for frozen in (
            "contracts/learnit-kit-v2.schema.json",
            "apps/learnit-next/source_manifest.json",
            "apps/learnit-next/src/ports/storage.js",
            "apps/learnit-next/src/adapters/indexeddb.js",
        ):
            before = git("rev-parse", f"{BASELINE}:{frozen}", check=False)
            after = git("rev-parse", f"{DEV_COMMIT}:{frozen}", check=False)
            self.assertEqual(before.returncode, after.returncode, frozen)
            if before.returncode == 0:
                self.assertEqual(before.stdout.strip(), after.stdout.strip(), frozen)
        patch = git("diff", "--unified=0", f"{BASELINE}..{DEV_COMMIT}").stdout
        for protected in (
            "learnit_clean_state_v2",
            "learnit_durable_library_v1",
            "learnit_active_course_v1",
            "learnit_imported_courses_v1",
            "indexedDB.open",
            "createObjectStore",
            "NEXT_INDEXED_DB_NAME",
            "NEXT_INDEXED_DB_VERSION",
            "NEXT_STORES",
        ):
            self.assertNotIn(protected, patch)

    def test_01_public_runtime_review_and_reset_contract_is_present(self) -> None:
        main = ROOT / "apps/learnit-next/src/main.js"
        if not main.exists():
            if STRICT:
                self.fail("apply this QA test to the exact DEV worktree before execution")
            self.skipTest("DEV main.js is absent from this QA-only worktree")
        main_text = main.read_text(encoding="utf-8")
        for operation in ("startCourse", "answer", "getProgress", "resetNextData", "storageReport"):
            self.assertIn(operation, main_text)
        for operation in ("startReviewQueue", "getReviewQueue"):
            self.assertIn(operation, main_text)
        reset_start = main_text.index("async resetNextData()")
        reset_end = main_text.index("storageReport:", reset_start)
        reset_block = main_text[reset_start:reset_end]
        self.assertLess(reset_block.index("sessions.clearActiveSession()"), reset_block.index("await storage.resetNextData()"))
        self.assertIn("return storage.storageReport()", reset_block)

    def test_02_public_ui_review_contract_is_present(self) -> None:
        render = ROOT / "apps/learnit-next/src/ui/render.js"
        if not render.exists():
            if STRICT:
                self.fail("apply this QA test to the exact DEV worktree before execution")
            self.skipTest("DEV render.js is absent from this QA-only worktree")
        render_text = render.read_text(encoding="utf-8")
        for label in ("Ouvrir À revoir", "Revenir au parcours", "La file À revoir est vide"):
            self.assertIn(label, render_text)
        self.assertIn("focusAfterRender", render_text)
        self.assertIn("aria-live", render_text)
        self.assertIn("role: 'status'", render_text)

    def test_03_domain_persistence_failure_matrix(self) -> None:
        progress = ROOT / "apps/learnit-next/src/core/progress.js"
        session = ROOT / "apps/learnit-next/src/core/session.js"
        if not progress.exists() or not session.exists():
            self.fail(
                "DEV core files are absent. Run from a detached/worktree copy at "
                f"{DEV_COMMIT} with this QA test applied, or set P1_PRODUCT_TREE."
            )
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required")
        with tempfile.TemporaryDirectory(prefix="p1-qa-") as directory:
            temp = Path(directory)
            shutil.copy2(progress, temp / "progress.mjs")
            shutil.copy2(session, temp / "session.mjs")
            (temp / "harness.mjs").write_text(NODE_HARNESS, encoding="utf-8")
            result = subprocess.run(
                [node, str(temp / "harness.mjs")],
                cwd=temp,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
                check=False,
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(f"Node harness did not emit JSON (exit={result.returncode}):\n{result.stdout}")
        failures = [item for item in payload["results"] if item["status"] == "FAIL"]
        self.assertEqual(0, result.returncode, json.dumps(failures, indent=2, ensure_ascii=False))
        self.assertEqual(19, payload["total"], payload)
        self.assertEqual(0, payload["failed"], json.dumps(failures, indent=2, ensure_ascii=False))
        self.assertEqual(19, payload["passed"], payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
