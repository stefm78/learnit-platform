#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps" / "learnit-next"
MAIN = APP / "src" / "main.js"
RENDER = APP / "src" / "ui" / "render.js"
SURFACE = APP / "src" / "integration" / "atlas" / "surface.js"
PROJECTION = APP / "src" / "integration" / "atlas" / "activity_projection.js"
FIXTURE = APP / "tests" / "fixtures" / "student_v01_v4_runtime.json"

main = MAIN.read_text(encoding="utf-8")
render = RENDER.read_text(encoding="utf-8")
surface = SURFACE.read_text(encoding="utf-8")
projection = PROJECTION.read_text(encoding="utf-8")
fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

for source in (MAIN, RENDER, SURFACE):
    subprocess.run(["node", "--check", str(source)], cwd=ROOT, check=True)

assert "projectActivityPresentation" in main
assert "projectLearnerActivity" in main
assert "packageAssets ?? []" in main
assert "activityRevisionId: activity.activityRevisionId" in main
assert "presentation: projectActivityPresentation" in main
assert "projectLearnerSession(await sessions.startCourse" in main
assert "projectLearnerSession(await sessions.startReviewQueue" in main
assert "projectLearnerAnswer(await sessions.answer" in main
assert "projectLearnerSession(await sessions.resumeActiveCourse" in main
assert "projectLearnerSession(await sessions.getSession" in main
for field in ("correctChoiceId", "answers", "acceptedResponses", "matches", "correctOrder", "assignments"):
    assert f"activity.{field}" not in main, field

assert "renderActivityPresentation" in render
assert "readActivityResponse" in render
assert "renderServedActivityForm" in render
assert "data-served-activity-submit" in render
session_slice = render[render.index("function renderSessionSnapshot"):render.index("function renderFeedback")]
assert "renderQcmForm(" not in session_slice
assert "renderFillForm(" not in session_slice
assert "renderServedActivityForm(" in session_slice
assert "result.scored === true" in render
assert "Activité terminée" in render
assert "data-served-feedback" in render

assert "ATLAS_SUPPORTED_ACTIVITY_TYPES = new Set(['qcm', 'fill'])" in surface
compat = surface[surface.index("function compatibleAtlasCourse"):surface.index("function learnerObjectiveLabels")]
assert "ATLAS_SUPPORTED_ACTIVITY_TYPES.has(activity.type)" in compat
assert "typeof activity.assessmentRole === 'string'" in compat

families = [item["type"] for item in fixture["courses"][0]["activities"]]
assert families == ["qcm", "fill", "constructed", "lesson", "flashcard", "matching", "order", "classify"]
for family in families:
    assert f"case '{family}'" in projection

NODE = r"""
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';

const root = process.env.SERVED_V4_ROOT;
const fixture = JSON.parse(fs.readFileSync(process.env.SERVED_V4_FIXTURE, 'utf8'));
const {createLearnitRuntime} = await import(pathToFileURL(root + '/apps/learnit-next/src/main.js').href);
const clone = value => structuredClone(value);
const key = (courseInstallId, activityRevisionId) => courseInstallId + '::' + activityRevisionId;

class MemoryStorage {
  constructor() {
    this.courses = new Map();
    this.progress = new Map();
    this.meta = new Map();
    this.revisions = new Map();
  }
  async commitImport(payload) {
    for (const course of payload.courses ?? []) this.courses.set(course.courseInstallId, clone(course));
    for (const revision of payload.revisions ?? []) this.revisions.set(revision.revisionId, revision.digest);
    for (const entry of payload.meta ?? []) this.meta.set(entry.key, clone(entry.value));
  }
  async getRevisionDigestIndex() { return new Map(this.revisions); }
  async listCourses() { return [...this.courses.values()].map(clone); }
  async getCourse(courseInstallId) { return clone(this.courses.get(courseInstallId) ?? null); }
  async setCourseDisplayLabel(courseInstallId, label) { this.courses.get(courseInstallId).displayLabel = label; }
  async listProgress(courseInstallId) {
    return [...this.progress.values()].filter(item => item.courseInstallId === courseInstallId).map(clone);
  }
  async getProgress(courseInstallId, activityRevisionId) {
    return clone(this.progress.get(key(courseInstallId, activityRevisionId)) ?? null);
  }
  async putProgress(record) {
    this.progress.set(key(record.courseInstallId, record.activityRevisionId), clone(record));
  }
  async getMeta(name) { return clone(this.meta.get(name) ?? null); }
  async setMeta(name, value) { this.meta.set(name, clone(value)); }
  async deleteMeta(name) { this.meta.delete(name); }
  async resetNextData() { this.courses.clear(); this.progress.clear(); this.meta.clear(); this.revisions.clear(); }
  async storageReport() { return {courses: this.courses.size, progress: this.progress.size}; }
}

const forbidden = new Set(['correctChoiceId', 'answers', 'acceptedResponses', 'matches', 'correctOrder', 'assignments']);
function forbiddenHits(value, out = []) {
  if (value == null || typeof value !== 'object') return out;
  for (const [name, child] of Object.entries(value)) {
    if (forbidden.has(name)) out.push(name);
    forbiddenHits(child, out);
  }
  return out;
}
function assertSafeActivity(activity, expectedType) {
  assert.ok(activity);
  assert.deepEqual(Object.keys(activity).sort(), ['activityRevisionId', 'presentation']);
  assert.equal(activity.presentation.type, expectedType);
  assert.deepEqual(forbiddenHits(activity), []);
  for (const name of forbidden) assert.equal(JSON.stringify(activity).includes('"' + name + '"'), false);
}
function responseFor(activity) {
  switch (activity.type) {
    case 'qcm':
      return {choiceId: activity.correctChoiceId};
    case 'fill':
      return Object.fromEntries(activity.answers.map(entry => [entry.slotId, entry.tokenId]));
    case 'constructed':
      return {text: activity.acceptedResponses[0]};
    case 'lesson':
      return {acknowledged: true};
    case 'flashcard':
      return {revealed: true};
    case 'matching':
      return {associations: activity.matches.map(clone)};
    case 'order':
      return {orderedItemIds: [...activity.correctOrder]};
    case 'classify':
      return {assignments: activity.assignments.map(clone)};
    default:
      throw new Error('unsupported family ' + activity.type);
  }
}

const runtime = createLearnitRuntime(new MemoryStorage(), {});
const imported = await runtime.importPackage(fixture);
const courseInstallId = imported.courses[0].courseInstallId;
const sourceActivities = fixture.courses[0].activities;
const familyOrder = sourceActivities.map(activity => activity.type);
const scoredFamilies = new Set(['qcm', 'fill', 'constructed', 'matching', 'order', 'classify']);

let session = await runtime.startCourse(courseInstallId);
assertSafeActivity(session.currentActivity, familyOrder[0]);

for (let index = 0; index < sourceActivities.length; index += 1) {
  const source = sourceActivities[index];
  assertSafeActivity(session.currentActivity, source.type);
  if (source.type === 'constructed') {
    const media = session.currentActivity.presentation.media;
    assert.equal(media.length, 1);
    assert.equal(media[0].assetId, fixture.assets[0].assetId);
    assert.equal(media[0].data, fixture.assets[0].data);
    assert.equal(media[0].alt, fixture.assets[0].alt);
  }

  const response = responseFor(source);
  const result = await runtime.answer(source.activityRevisionId, response);
  assert.deepEqual(result.answer, response);

  if (scoredFamilies.has(source.type)) {
    assert.equal(result.scored, true);
    assert.equal(result.correct, true);
  } else {
    assert.equal(result.scored, false);
    assert.equal(Object.hasOwn(result, 'correct'), false);
  }

  if (index < sourceActivities.length - 1) {
    assertSafeActivity(result.nextActivity, familyOrder[index + 1]);
  } else {
    assert.equal(result.nextActivity, null);
  }

  session = await runtime.getSession();
  if (index < sourceActivities.length - 1) {
    assertSafeActivity(session.currentActivity, familyOrder[index + 1]);
  } else {
    assert.equal(session.currentActivity, null);
    assert.equal(session.progress.isComplete, true);
  }
}

const surfaceSource = fs.readFileSync(root + '/apps/learnit-next/src/integration/atlas/surface.js', 'utf8');
const setMatch = surfaceSource.match(/const ATLAS_SUPPORTED_ACTIVITY_TYPES = new Set\(\[[^\n]+\]\);/);
assert.ok(setMatch);
const functionStart = surfaceSource.indexOf('function compatibleAtlasCourse');
const functionEnd = surfaceSource.indexOf('\n}\n\nfunction learnerObjectiveLabels', functionStart);
assert.ok(functionStart >= 0 && functionEnd > functionStart);
const compatibilityModule = setMatch[0] + '\n' + surfaceSource.slice(functionStart, functionEnd + 2) + '\nexport { compatibleAtlasCourse };';
const {compatibleAtlasCourse} = await import('data:text/javascript;base64,' + Buffer.from(compatibilityModule).toString('base64'));
const atlasRuntime = {modules: {claimAuthority: {contextAccepted: () => true}}};
const baseActivity = {
  objectiveIds: ['objective-1'],
  learningPhase: 'application',
  assessmentRole: 'practice',
  estimatedMinutes: 5,
};
const qcmFillContext = {
  course: {
    objectives: [{objectiveId: 'objective-1'}],
    activities: [
      {...baseActivity, type: 'qcm'},
      {...baseActivity, type: 'fill'},
    ],
  },
};
const richContext = {
  course: {
    objectives: [{objectiveId: 'objective-1'}],
    activities: [
      {...baseActivity, type: 'qcm'},
      {...baseActivity, type: 'constructed'},
    ],
  },
};
assert.equal(compatibleAtlasCourse(qcmFillContext, atlasRuntime), true);
assert.equal(compatibleAtlasCourse(richContext, atlasRuntime), false);

console.log(JSON.stringify({
  ok: true,
  families: familyOrder,
  atlasQcmFillAccepted: true,
  atlasRichRejected: true,
  complete: session.progress.isComplete,
}));
"""

node = shutil.which("node")
assert node, "node is required for served runtime integration proof"
with tempfile.TemporaryDirectory(prefix="served-v4-runtime-") as temp_dir:
    harness = Path(temp_dir) / "served-v4-runtime.mjs"
    harness.write_text(NODE, encoding="utf-8")
    env = {
        **os.environ,
        "SERVED_V4_ROOT": str(ROOT),
        "SERVED_V4_FIXTURE": str(FIXTURE),
    }
    result = subprocess.run(
        [node, str(harness)],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
assert result.returncode == 0, result.stdout
runtime_result = json.loads(result.stdout.strip().splitlines()[-1])
assert runtime_result["ok"] is True
assert runtime_result["families"] == families
assert runtime_result["atlasQcmFillAccepted"] is True
assert runtime_result["atlasRichRejected"] is True
assert runtime_result["complete"] is True

print("STUDENT_V01_SERVED_V4_STATIC_PASS")
print("SERVED_RUNTIME_PROJECTION_BOUNDARY=PASS")
print("CURRENT_NEXT_LEARNER_SAFE=PASS")
print("FORBIDDEN_SECRET_KEYS_RECURSIVE=PASS")
print("ALL_EIGHT_RESPONSE_SHAPES=PASS")
print("SCORED_FAMILIES_RUNTIME=PASS")
print("NON_SCORED_RESULT_SHAPE=PASS")
print("TRUSTED_MEDIA_PROJECTION=PASS")
print("SERVED_GENERIC_PRESENTER_WIRING=PASS")
print("ATLAS_EXPLICIT_QCM_FILL_GATE=PASS")
print("ATLAS_QCM_FILL_ACCEPTED=PASS")
print("ATLAS_RICH_REJECTED=PASS")
