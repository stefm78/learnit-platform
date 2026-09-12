import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MATH_E1,
  VOCAB_E2,
  evaluate,
  visibleStimulus,
  responseSpec,
  evaluatorSpec,
  scoredExecutionLike,
} from './prototype.mjs';

test('E1 and E2 use the same response/evaluator grammar', () => {
  const math = MATH_E1.validation;
  const vocab = VOCAB_E2[0].validation;
  assert.equal(responseSpec(math).kind, 'fields');
  assert.equal(responseSpec(vocab).kind, 'fields');
  assert.equal(evaluatorSpec(math).kind, 'exact-fields');
  assert.equal(evaluatorSpec(vocab).kind, 'exact-fields');
});

test('E1 practice accepts exact structured production and records authored support separately', () => {
  const activity = MATH_E1.practice;
  const result = evaluate(activity, {
    method: 'Exponentielle',
    root1: '2e^{iπ/6}',
    root2: '-2e^{iπ/6}',
  });
  assert.equal(result.correct, true);
  assert.ok(visibleStimulus(activity).support);
  const execution = scoredExecutionLike(activity, result.normalized);
  assert.equal(execution.outcome, 'correct');
  assert.equal(execution.assistance, 'none');
  assert.equal(execution.evidenceEligibleForIndependentValidation, false);
});

test('E1 independent validation has no authored support and can be evidence-eligible', () => {
  const activity = MATH_E1.validation;
  const execution = scoredExecutionLike(activity, {
    method: 'algebrique',
    root1: '3 + 2i',
    root2: '-3 - 2i',
  });
  assert.equal(execution.outcome, 'correct');
  assert.equal(visibleStimulus(activity).support, null);
  assert.equal(execution.evidenceEligibleForIndependentValidation, true);
});

test('E1 validation fails if one component is wrong', () => {
  const result = evaluate(MATH_E1.validation, {
    method: 'algébrique',
    root1: '3+2i',
    root2: '3+2i',
  });
  assert.equal(result.correct, false);
  assert.equal(result.fieldResults.root2, false);
});

test('E2 covers exactly 20 lexical targets in four evidence-coherent objectives', () => {
  const labels = VOCAB_E2.flatMap(({ validation }) => validation.response.fields.map((field) => field.label));
  assert.equal(labels.length, 20);
  assert.equal(new Set(labels).size, 20);
  assert.equal(VOCAB_E2.length, 4);
  for (const group of VOCAB_E2) assert.equal(group.validation.response.fields.length, 5);
});

test('E2 exact evaluator preserves accents while ignoring case', () => {
  const group3 = VOCAB_E2[2].validation;
  const correct = evaluate(group3, {
    word1: 'ÁRBOL',
    word2: 'noche',
    word3: 'mano',
    word4: 'amigo',
    word5: 'familia',
  });
  assert.equal(correct.correct, true);
  const wrongAccent = evaluate(group3, {
    word1: 'arbol',
    word2: 'noche',
    word3: 'mano',
    word4: 'amigo',
    word5: 'familia',
  });
  assert.equal(wrongAccent.correct, false);
  assert.equal(wrongAccent.fieldResults.word1, false);
});

test('on-demand assistance and authored support remain distinct', () => {
  const activity = MATH_E1.validation;
  const execution = scoredExecutionLike(activity, {
    method: 'algébrique', root1: '3+2i', root2: '-3-2i'
  }, { assistance: 'used' });
  assert.equal(activity.support, null);
  assert.equal(execution.assistance, 'used');
  assert.equal(execution.evidenceEligibleForIndependentValidation, false);
});

test('visible stimulus, response spec, and evaluator have separate digests', () => {
  const activity = MATH_E1.validation;
  const execution = scoredExecutionLike(activity, {
    method: 'algébrique', root1: '3+2i', root2: '-3-2i'
  });
  assert.match(execution.responseDigest, /^sha256:[0-9a-f]{64}$/);
  assert.match(execution.scoringRuleDigest, /^sha256:[0-9a-f]{64}$/);
  assert.notDeepEqual(visibleStimulus(activity), evaluatorSpec(activity));
});
