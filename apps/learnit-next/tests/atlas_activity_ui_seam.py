#!/usr/bin/env python3
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
integration = (ROOT / "apps/learnit-next/src/integration/atlas/session.js").read_text(encoding="utf-8")
ui = (ROOT / "apps/learnit-next/src/ui/render.js").read_text(encoding="utf-8")
core = (ROOT / "apps/learnit-next/src/core/session.js").read_text(encoding="utf-8")

assert "from '../../ui/render.js'" in integration
assert "projectAtlasActivityPresentation" in integration
assert "const activityPresentation =" in integration
assert "renderAtlasActivityMarkup(activityPresentation)" in integration
assert "readAtlasActivityResponse(wrapper, activityPresentation)" in integration
assert "renderAtlasActivityMarkup(activity)" not in integration
assert "readAtlasActivityResponse(wrapper, activity)" not in integration
assert "function renderActivity(" not in integration
assert "function readResponse(" not in integration
assert "data-atlas-choice=\"true\"" not in integration
assert "[data-atlas-slot]" not in integration
assert "export function renderAtlasActivityMarkup" in ui
assert "export function readAtlasActivityResponse" in ui
assert "[data-atlas-choice=\"true\"]:checked" in ui
assert "[data-atlas-slot]" in ui
assert "querySelector" not in core
assert "document." not in core

probe = r'''
import assert from 'node:assert/strict';
import { projectAtlasActivityPresentation } from './apps/learnit-next/src/integration/atlas/session.js';

const forbidden = new Set([
  'correctChoiceId',
  'answers',
  'acceptedValues',
  'evaluator',
  'score',
  'scoringRuleId',
]);

function assertNoForbiddenKeys(value) {
  if (Array.isArray(value)) {
    value.forEach(assertNoForbiddenKeys);
    return;
  }
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    assert.equal(forbidden.has(key), false, `forbidden UI key leaked: ${key}`);
    assertNoForbiddenKeys(child);
  }
}

const qcmSource = {
  type: 'qcm',
  prompt: 'QCM prompt',
  correctChoiceId: 'SECRET_QCM',
  answers: { hidden: 'SECRET_ANSWERS' },
  acceptedValues: ['SECRET_ACCEPTED'],
  evaluator: 'SECRET_EVALUATOR',
  score: 'SECRET_SCORE',
  scoringRuleId: 'SECRET_RULE',
  choices: [
    {
      choiceId: 'a',
      label: 'A',
      score: 'NESTED_SECRET_SCORE',
      acceptedValues: ['NESTED_SECRET_ACCEPTED'],
    },
  ],
};
const qcmSafe = projectAtlasActivityPresentation(qcmSource);
assert.deepEqual(qcmSafe, {
  type: 'qcm',
  prompt: 'QCM prompt',
  choices: [{ choiceId: 'a', label: 'A' }],
});
assert.equal(Object.isFrozen(qcmSafe), true);
assert.equal(Object.isFrozen(qcmSafe.choices), true);
assert.equal(Object.isFrozen(qcmSafe.choices[0]), true);
assertNoForbiddenKeys(qcmSafe);

const fillSource = {
  type: 'fill',
  prompt: 'Fill prompt',
  answers: { s1: 'SECRET_FILL_ANSWER' },
  acceptedValues: ['SECRET_FILL_ACCEPTED'],
  evaluator: 'SECRET_FILL_EVALUATOR',
  score: 'SECRET_FILL_SCORE',
  scoringRuleId: 'SECRET_FILL_RULE',
  tokens: [
    {
      tokenId: 't1',
      label: 'Token',
      acceptedValues: ['NESTED_TOKEN_SECRET'],
      score: 'NESTED_TOKEN_SCORE',
    },
  ],
  segments: [
    { text: 'Before ', evaluator: 'NESTED_SEGMENT_SECRET' },
    { slotId: 's1', answers: ['NESTED_SLOT_SECRET'] },
  ],
};
const fillSafe = projectAtlasActivityPresentation(fillSource);
assert.deepEqual(fillSafe, {
  type: 'fill',
  prompt: 'Fill prompt',
  tokens: [{ tokenId: 't1', label: 'Token' }],
  segments: [{ text: 'Before ' }, { slotId: 's1' }],
});
assert.equal(Object.isFrozen(fillSafe), true);
assert.equal(Object.isFrozen(fillSafe.tokens), true);
assert.equal(Object.isFrozen(fillSafe.tokens[0]), true);
assert.equal(Object.isFrozen(fillSafe.segments), true);
assertNoForbiddenKeys(fillSafe);

const serialized = JSON.stringify({ qcmSafe, fillSafe });
for (const sentinel of [
  'SECRET_QCM',
  'SECRET_ANSWERS',
  'SECRET_ACCEPTED',
  'SECRET_EVALUATOR',
  'SECRET_SCORE',
  'SECRET_RULE',
  'NESTED_SECRET_SCORE',
  'NESTED_SECRET_ACCEPTED',
  'SECRET_FILL_ANSWER',
  'SECRET_FILL_ACCEPTED',
  'SECRET_FILL_EVALUATOR',
  'SECRET_FILL_SCORE',
  'SECRET_FILL_RULE',
  'NESTED_TOKEN_SECRET',
  'NESTED_TOKEN_SCORE',
  'NESTED_SEGMENT_SECRET',
  'NESTED_SLOT_SECRET',
]) {
  assert.equal(serialized.includes(sentinel), false, `secret sentinel leaked: ${sentinel}`);
}
console.log('ATLAS_ACTIVITY_UI_SECRET_BOUNDARY_PROVEN');
'''

result = subprocess.run(
    ["node", "--input-type=module", "-e", probe],
    cwd=ROOT,
    check=True,
    text=True,
    capture_output=True,
)
assert "ATLAS_ACTIVITY_UI_SECRET_BOUNDARY_PROVEN" in result.stdout
print("ATLAS_ACTIVITY_UI_SEAM_PASS")
print("UX_SECRET_BOUNDARY_PROVEN")
