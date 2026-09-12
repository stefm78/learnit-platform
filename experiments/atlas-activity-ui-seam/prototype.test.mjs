import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  QCM_FIXTURE,
  FILL_FIXTURE,
  MATH_E1,
  VOCAB_E2,
  activityPresentation,
  activityResponse,
  assertLearnerSafe,
  assertValidationSupportPolicy,
  evaluateLearning,
  activityEvaluation,
} from './prototype.mjs';

async function importR14CoreEvaluator() {
  const path = new URL('../../apps/learnit-next/src/core/session.js', import.meta.url);
  const source = await readFile(path, 'utf8');
  const encoded = Buffer.from(source, 'utf8').toString('base64');
  const module = await import(`data:text/javascript;base64,${encoded}`);
  return module.evaluateAnswer;
}

const productEvaluateAnswer = await importR14CoreEvaluator();

function response(activity, value) {
  return activityResponse(activityPresentation(activity), value);
}

function json(value) {
  return JSON.stringify(value);
}

test('QCM presentation is learner-safe and does not expose correctChoiceId', () => {
  const presentation = activityPresentation(QCM_FIXTURE);
  assert.equal(assertLearnerSafe(presentation), true);
  assert.equal(json(presentation).includes('correctChoiceId'), false);
  assert.deepEqual(presentation.responseSpec, {
    kind: 'qcm',
    choices: [{ choiceId: 'c1', label: '3' }, { choiceId: 'c2', label: '4' }],
  });
});

test('fill presentation is learner-safe and does not expose answers', () => {
  const presentation = activityPresentation(FILL_FIXTURE);
  assert.equal(assertLearnerSafe(presentation), true);
  assert.equal(Object.hasOwn(presentation, 'answers'), false);
  assert.equal(json(presentation).includes('"answers"'), false);
});

test('constructed presentation does not expose acceptedValues or evaluator', () => {
  const presentation = activityPresentation(MATH_E1.validation);
  assert.equal(assertLearnerSafe(presentation), true);
  assert.equal(json(presentation).includes('acceptedValues'), false);
  assert.equal(json(presentation).includes('evaluator'), false);
});

test('QCM raw response is evaluated by the actual R14 core authority', () => {
  const evaluated = evaluateLearning(QCM_FIXTURE, response(QCM_FIXTURE, { choiceId: 'c2' }), productEvaluateAnswer);
  assert.deepEqual(evaluated.normalized, { choiceId: 'c2' });
  assert.equal(evaluated.correct, true);
  assert.equal(evaluateLearning(QCM_FIXTURE, response(QCM_FIXTURE, { choiceId: 'c1' }), productEvaluateAnswer).correct, false);
});

test('fill raw response is evaluated by the actual R14 core authority', () => {
  const evaluated = evaluateLearning(FILL_FIXTURE, response(FILL_FIXTURE, { s1: 't1' }), productEvaluateAnswer);
  assert.deepEqual(evaluated.normalized, { s1: 't1' });
  assert.equal(evaluated.correct, true);
});

test('R14 QCM unknown-choice validation behavior is preserved', () => {
  assert.throws(
    () => evaluateLearning(QCM_FIXTURE, response(QCM_FIXTURE, { choiceId: 'missing' }), productEvaluateAnswer),
    (error) => error?.code === 'unknown_choice',
  );
});

test('R14 fill incomplete validation behavior is preserved', () => {
  assert.throws(
    () => evaluateLearning(FILL_FIXTURE, response(FILL_FIXTURE, {}), productEvaluateAnswer),
    (error) => error?.code === 'incomplete_fill',
  );
});

test('E1 constructed validation scores a complete correct production', () => {
  const evaluated = evaluateLearning(MATH_E1.validation, response(MATH_E1.validation, {
    fields: { method: 'Algébrique', root1: '3 + 2i', root2: '-3 - 2i' },
  }), productEvaluateAnswer);
  assert.equal(evaluated.correct, true);
});

test('E1 constructed incomplete response is rejected deterministically', () => {
  assert.throws(
    () => evaluateLearning(MATH_E1.validation, response(MATH_E1.validation, {
      fields: { method: 'algébrique', root1: '3+2i' },
    }), productEvaluateAnswer),
    /CONSTRUCTED_RESPONSE_INCOMPLETE/,
  );
});

test('E1 constructed wrong component yields binary incorrect without partial score', () => {
  const evaluated = evaluateLearning(MATH_E1.validation, response(MATH_E1.validation, {
    fields: { method: 'algébrique', root1: '3+2i', root2: '3+2i' },
  }), productEvaluateAnswer);
  assert.equal(evaluated.correct, false);
  assert.equal(evaluated.fieldResults.root2, false);
  assert.equal(Object.hasOwn(evaluated, 'score'), false);
});

test('E2 remains four evidence-coherent objectives of five produced words', () => {
  assert.equal(VOCAB_E2.length, 4);
  const objectiveIds = new Set();
  for (const group of VOCAB_E2) {
    objectiveIds.add(group.validation.objectiveId);
    assert.equal(group.validation.fields.length, 5);
  }
  assert.equal(objectiveIds.size, 4);
});

test('E2 exact-fields normalization accepts case variance and Unicode NFC', () => {
  const activity = VOCAB_E2[2].validation;
  const decomposed = 'A\u0301RBOL';
  const evaluated = evaluateLearning(activity, response(activity, {
    fields: { word1: decomposed, word2: 'NOCHE', word3: 'mano', word4: 'amigo', word5: 'familia' },
  }), productEvaluateAnswer);
  assert.equal(evaluated.correct, true);
});

test('E2 accents remain significant', () => {
  const activity = VOCAB_E2[2].validation;
  const evaluated = evaluateLearning(activity, response(activity, {
    fields: { word1: 'arbol', word2: 'noche', word3: 'mano', word4: 'amigo', word5: 'familia' },
  }), productEvaluateAnswer);
  assert.equal(evaluated.correct, false);
  assert.equal(evaluated.fieldResults.word1, false);
});

test('authored practice support does not become learner-requested assistance', () => {
  const evaluation = activityEvaluation(MATH_E1.practice, response(MATH_E1.practice, {
    fields: { method: 'exponentielle', root1: '2e^{iπ/6}', root2: '-2e^{iπ/6}' },
  }), productEvaluateAnswer);
  assert.ok(activityPresentation(MATH_E1.practice).preResponseSupport);
  assert.equal(evaluation.assistance, 'none');
});

test('revealing authored support is forbidden for constructed validation fixture', () => {
  const invalid = {
    ...MATH_E1.validation,
    preResponseSupport: { revealing: true, content: 'La réponse est 3+2i et -3-2i.' },
  };
  assert.throws(() => assertValidationSupportPolicy(invalid), /VALIDATION_REVEALING_SUPPORT_FORBIDDEN/);
});

test('constructed evaluation does not require planner input or planner mutation', () => {
  const evaluation = activityEvaluation(MATH_E1.validation, response(MATH_E1.validation, {
    fields: { method: 'algébrique', root1: '3+2i', root2: '-3-2i' },
  }), productEvaluateAnswer);
  assert.equal(evaluation.outcome, 'correct');
  assert.equal(Object.hasOwn(evaluation, 'plan'), false);
  assert.equal(Object.hasOwn(evaluation, 'recommendation'), false);
});

test('evaluation emits evidence-facing primitives without a new ObjectiveEvidence model', () => {
  const evaluation = activityEvaluation(MATH_E1.validation, response(MATH_E1.validation, {
    fields: { method: 'algébrique', root1: '3+2i', root2: '-3-2i' },
  }), productEvaluateAnswer);
  assert.match(evaluation.responseDigest, /^sha256:[0-9a-f]{64}$/);
  assert.equal(evaluation.scoringRuleId, 'learnit.kit.v2.constructed.exact-fields.v1');
  assert.match(evaluation.scoringRuleDigest, /^sha256:[0-9a-f]{64}$/);
  assert.equal(evaluation.outcome, 'correct');
  assert.equal(evaluation.assistance, 'none');
  assert.equal(Object.hasOwn(evaluation, 'objectiveEvidence'), false);
});

test('evaluation does not introduce a new execution class', () => {
  const evaluation = activityEvaluation(MATH_E1.validation, response(MATH_E1.validation, {
    fields: { method: 'algébrique', root1: '3+2i', root2: '-3-2i' },
  }), productEvaluateAnswer);
  assert.equal(Object.hasOwn(evaluation, 'executionClass'), false);
});

test('recursive learner-safety guard rejects hidden nested scoring secrets', () => {
  assert.throws(
    () => assertLearnerSafe({ responseSpec: { meta: { acceptedValues: ['secret'] } } }),
    /LEARNER_SECRET_EXPOSED/,
  );
});

test('QCM and fill keep their native compact response grammars', () => {
  const qcm = activityPresentation(QCM_FIXTURE).responseSpec;
  const fill = activityPresentation(FILL_FIXTURE).responseSpec;
  assert.equal(qcm.kind, 'qcm');
  assert.equal(Object.hasOwn(qcm, 'fields'), false);
  assert.equal(fill.kind, 'fill');
  assert.equal(Object.hasOwn(fill, 'fields'), false);
});

test('experimental seam remains DOM-free and framework-free', async () => {
  const source = await readFile(new URL('./prototype.mjs', import.meta.url), 'utf8');
  for (const forbidden of ['querySelector(', 'document.', 'createElement(', 'capabilityRegistry', 'pluginRegistry']) {
    assert.equal(source.includes(forbidden), false, `unexpected ${forbidden}`);
  }
});
