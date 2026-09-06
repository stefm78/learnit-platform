#!/usr/bin/env python3
import pathlib
import subprocess
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Experience(unittest.TestCase):
    def run_node(self, source: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ['node', '-e', textwrap.dedent(source), str(ROOT)],
            capture_output=True,
            text=True,
            check=False,
        )

    def event_identity_prelude(self) -> str:
        return r'''
          const assert = require('assert');
          const root = process.argv[1];
          const T = require(root + '/src/ui/atlas_today.js');
          const S = require(root + '/src/ui/atlas_session.js');

          const id = (prefix, ch) => prefix + ch.repeat(64);
          const courseRef = {packageLineageId:'p', courseLineageId:'c'};
          const objectiveRef = {courseRef, objectiveId:'o'};
          const otherObjectiveRef = {courseRef, objectiveId:'other'};
          const correctionTarget = id('atlas-event-sha256:','c');
          const attemptExecutionId = id('atlas-execution-sha256:','a');
          const correctedExecutionId = id('atlas-execution-sha256:','b');

          function coreIdentity(event) {
            const identity = {
              eventVersion:event.eventVersion,
              kind:event.kind,
              executionId:event.executionId
            };
            if (event.kind === 'activity-corrected') identity.correctsEventId = event.correctsEventId;
            return identity;
          }

          const coreEventId = event => T.typedHash(
            'atlas-event-sha256:',
            'learnit.atlas.m1.v0.3/event-id',
            coreIdentity(event)
          );
          const legacyEventId = event => T.typedHash(
            'atlas-event-sha256:',
            'learnit.atlas.m1.v0.3/event-id',
            T.without(event, 'eventId')
          );

          const attemptBase = {
            eventVersion:'atlas.learning-event.v1',
            kind:'activity-attempt',
            objectiveRef,
            executionId:attemptExecutionId,
            occurredAt:'2026-01-01T00:00:00.000Z'
          };
          const attemptEvent = {...attemptBase,eventId:coreEventId(attemptBase)};
          const attemptExecution = {executionId:attemptExecutionId};
          const attemptItem = {executionClass:'practice',objectiveRef};

          const correctedBase = {
            eventVersion:'atlas.learning-event.v1',
            kind:'activity-corrected',
            objectiveRef,
            executionId:correctedExecutionId,
            correctsEventId:correctionTarget,
            occurredAt:'2026-01-01T00:00:00.001Z'
          };
          const correctedEvent = {...correctedBase,eventId:coreEventId(correctedBase)};
          const correctedExecution = {executionId:correctedExecutionId};
          const correctedItem = {executionClass:'correction',objectiveRef,correctsEventId:correctionTarget};
        '''

    def test_today_renders_human_action_labels(self):
     script=r"""
const today=require(process.argv[1]);

const courseRef={
  packageLineageId:'package-lineage',
  courseLineageId:'course-lineage'
};

const contentRevisionRef={
  packageLineageId:'package-lineage',
  packageRevisionId:'package-revision',
  packageDigest:'sha256:'+'0'.repeat(64)
};

const objectiveRef={
  courseRef,
  objectiveId:'objective-1'
};

const activityRef={
  courseRef,
  activityLineageId:'activity-1'
};

const actions=[
  'start-practice',
  'continue-practice',
  'correct-practice',
  'attempt-validation',
  'maintain-recent-validation'
];

const html=actions.map(action=>{
  const item={
    position:0,
    objectiveRef,
    activityRef,
    action,
    executionClass:today.ACTION_CLASS[action],
    estimatedMinutes:4
  };

  if(action==='correct-practice'){
    item.correctsEventId=
      'atlas-event-sha256:'+'1'.repeat(64);
  }

  if(
    action==='attempt-validation'
    || action==='maintain-recent-validation'
  ){
    item.validationBasisEventId=
      'atlas-event-sha256:'+'2'.repeat(64);
    item.independenceClaimId=
      'atlas-claim-sha256:'+'3'.repeat(64);
  }

  const recommendation={
    recommendationVersion:'atlas.recommendation.v1',
    objectiveRef,
    action,
    eligibleActivityRefs:[activityRef],
    preferredActivityRef:activityRef,
    estimatedMinutes:4,
    reasonCodes:['NEW_OBJECTIVE']
  };

  const payload={
    schemaVersion:'atlas.session-plan.v1',
    engineVersion:'atlas.m1.v0.3',
    courseRef,
    contentRevisionRef,
    durationMinutes:5,
    items:[item],
    totalEstimatedMinutes:4,
    unusedMinutes:1
  };

  const hex=today.hashHex(
    'learnit.atlas.m1.v0.3/plan-digest',
    payload
  );

  const plan={
    planId:'atlas-plan-sha256:'+hex,
    planDigest:'sha256:'+hex,
    payload
  };

  return today.renderToday({
    recommendation,
    plan
  });
});

process.stdout.write(JSON.stringify(html));
"""

     result=__import__('subprocess').run(
      [
       'node',
       '-e',
       script,
       str(
     __import__('pathlib').Path(__file__).resolve().parents[3]
     /'apps/learnit-next/src/ui/atlas_today.js'
    )
      ],
      check=True,
      capture_output=True,
      text=True
     )

     rendered=__import__('json').loads(result.stdout)

     technical=[
      'start-practice',
      'continue-practice',
      'correct-practice',
      'attempt-validation',
      'maintain-recent-validation'
     ]

     expected=[
      'Entraînement — je m’exerce',
      'Entraînement — je m’exerce',
      'Correction — je corrige une erreur',
      'Validation — je vérifie sans aide',
      'Entretien — je garde un acquis récent actif'
     ]

     self.assertEqual(len(rendered),5)

     for html,label in zip(rendered,expected):
      self.assertIn(label,html)
      for token in technical:
       self.assertNotIn(token,html)

    def test_node_positive_and_v2_regression_matrix(self):
        script = r'''
          const assert = require('assert');
          const crypto = require('crypto');
          const root = process.argv[1];
          const T = require(root + '/src/ui/atlas_today.js');
          const S = require(root + '/src/ui/atlas_session.js');
          const U = require(root + '/src/ui/atlas_summary.js');
          const R = require(root + '/src/ui/atlas_rewards.js');

          const id = (prefix, ch) => prefix + ch.repeat(64);
          const courseRef = {packageLineageId:'p', courseLineageId:'c'};
          const objectiveRef = {courseRef, objectiveId:'o'};
          const activityRef = {courseRef, activityLineageId:'a'};
          const contentRevisionRef = {packageLineageId:'p', packageRevisionId:'r', packageDigest:id('sha256:','3')};
          const item = {
            position:0, objectiveRef, activityRef, action:'correct-practice',
            executionClass:'correction', estimatedMinutes:3,
            correctsEventId:id('atlas-event-sha256:','1')
          };
          const payload = {
            schemaVersion:'atlas.session-plan.v1', engineVersion:'atlas.learning.v1',
            courseRef, contentRevisionRef, durationMinutes:5, items:[item],
            totalEstimatedMinutes:3, unusedMinutes:2
          };
          const planHex = T.hashHex('learnit.atlas.m1.v0.3/plan-digest', payload);
          const expectedPlanHex = crypto.createHash('sha256').update(Buffer.concat([
            Buffer.from('learnit.atlas.m1.v0.3/plan-digest','utf8'), Buffer.from([0]),
            Buffer.from(T.canonicalJson(payload),'utf8')
          ])).digest('hex');
          assert.equal(planHex, expectedPlanHex);
          const plan = {planId:'atlas-plan-sha256:'+planHex, planDigest:'sha256:'+planHex, payload};
          const recommendation = {
            recommendationVersion:'atlas.recommendation.v1', objectiveRef,
            action:'correct-practice', eligibleActivityRefs:[activityRef],
            preferredActivityRef:activityRef, estimatedMinutes:3,
            reasonCodes:['REVIEW_REQUIRED']
          };
          const sessionRef = {sessionId:id('atlas-session-sha256:','9'), planId:plan.planId};
          const initialResume = {
            resumeVersion:'atlas.resume-state.v1', sessionRef, courseRef, contentRevisionRef,
            planDigest:plan.planDigest, nextItemPosition:0,
            focusTarget:'atlas-session-item-0', lifecycleOrdinal:0,
            itemStates:[{itemPosition:0,submissionOrdinal:0,assistance:'none',assistanceUseIds:[]}]
          };

          assert(T.renderToday({recommendation,plan,resumeState:initialResume}).includes('Reprendre la séance'));
          assert(S.renderSession({plan,resumeState:initialResume}).includes('Correction'));
          assert(T.validateRecommendationPlan(recommendation,plan));

          const evidence = {
            evidenceVersion:'atlas.objective-evidence.v1', objectiveRef,
            practiceAttempts:1, correctionsCompleted:0, validationAttempts:1,
            latestPracticeCorrect:true, latestValidationCorrect:true,
            lastValidationAt:'2026-01-01T00:00:00.000Z',
            lastEvidenceAt:'2026-01-01T00:00:00.000Z',
            state:'validated-recently'
          };
          const summaryHtml=U.renderSummary({evidence:[evidence],completed:true});
          assert(summaryHtml.includes('Votre progression après cette séance.'));
          assert(summaryHtml.includes('Acquis récemment'));
          assert(summaryHtml.includes('Rien à faire maintenant.'));
          assert(summaryHtml.includes('course-objective-track'));
          assert(!summaryHtml.includes('Validation autonome récente'));
          assert(!summaryHtml.includes('ni une certification'));
          assert(!summaryHtml.includes('rétention durable'));
          assert.throws(() => U.validateEvidence({...evidence,latestPracticeCorrect:'yes'}), /INVALID_EVIDENCE/);
          assert.throws(() => U.validateEvidence({...evidence,latestValidationCorrect:7}), /INVALID_EVIDENCE/);
          assert.throws(() => U.validateEvidence({...evidence,lastEvidenceAt:'<script>not-a-time<\/script>'}), /INVALID_EVIDENCE/);
          assert.throws(() => U.validateEvidence({...evidence,lastValidationAt:{arbitrary:true}}), /INVALID_EVIDENCE/);
          assert.throws(() => U.validateEvidence({...evidence,latestValidationCorrect:false}), /CONTRADICTION/);
          assert.throws(() => U.validateEvidence({...evidence,lastEvidenceAt:'2025-12-31T23:59:59.999Z'}), /CONTRADICTION/);
          assert.throws(() => U.validateEvidence({...evidence,state:'not-started'}), /CONTRADICTION/);
          assert.throws(() => U.validateEvidence({...evidence,extra:true}), /UNKNOWN_FIELD/);

          assert.throws(() => T.validatePlan({...plan,planId:id('atlas-plan-sha256:','f')}), /PLAN_ID_DIGEST_MISMATCH/);
          assert.throws(() => T.validatePlan({...plan,payload:{...payload,engineVersion:'tampered'}}), /PLAN_ID_DIGEST_MISMATCH/);
          assert.throws(() => T.validatePlan({...plan,payload:{...payload,engineVersion:''}}), /INVALID_SESSION_PLAN/);
          assert.throws(() => T.validatePlan({...plan,payload:{...payload,contentRevisionRef:{...contentRevisionRef,packageDigest:'bad'}}}), /INVALID_CONTENT_REVISION_REF/);
          assert.throws(() => T.validatePlan({...plan,payload:{...payload,unusedMinutes:-1}}), /INVALID_SESSION_PLAN/);
          const missingCorrectionProvenance = {...item}; delete missingCorrectionProvenance.correctsEventId;
          assert.throws(() => T.validatePlan({...plan,payload:{...payload,items:[missingCorrectionProvenance]}}), /INVALID_SESSION_PLAN/);
          const validationItem = {...item,action:'attempt-validation',executionClass:'validation'};
          delete validationItem.correctsEventId;
          assert.throws(() => T.validatePlan({...plan,payload:{...payload,items:[validationItem]}}), /INVALID_SESSION_PLAN/);

          assert.throws(() => T.renderToday({recommendation,plan,resumeState:{nextItemPosition:0}}), /MISSING_FIELD/);
          const foreignResume = {...initialResume,sessionRef:{...sessionRef,planId:id('atlas-plan-sha256:','8')}};
          assert.throws(() => T.renderToday({recommendation,plan,resumeState:foreignResume}), /RESUME_PLAN_MISMATCH/);
          assert.throws(() => T.renderToday({recommendation,plan,resumeState:{...initialResume,planDigest:id('sha256:','8')}}), /RESUME_PLAN_MISMATCH/);
          assert.throws(() => T.renderToday({recommendation,plan,resumeState:{...initialResume,courseRef:{packageLineageId:'other',courseLineageId:'c'}}}), /RESUME_PLAN_MISMATCH/);
          assert.throws(() => T.validateResumeState({...initialResume,nextItemPosition:2},1,{plan,sessionRef}), /INVALID_RESUME_STATE/);
          assert.throws(() => T.validateResumeState({...initialResume,itemStates:[]},1,{plan,sessionRef}), /INVALID_RESUME_STATE/);

          function makeCommitResult(overrides={}) {
            const executionBase = {
              executionVersion:'atlas.scored-execution.v1', sessionRef, courseRef,
              contentRevisionRef, planDigest:plan.planDigest, itemPosition:0,
              submissionOrdinal:1, objectiveRef, activityRef,
              action:'correct-practice', executionClass:'correction',
              responseDigest:id('sha256:','4'), scoringRuleId:'rule-1',
              scoringRuleDigest:id('sha256:','5'), outcome:'correct', assistance:'none',
              assistanceUseIds:[], submittedAt:'2026-01-01T00:00:00.000Z',
              scoredAt:'2026-01-01T00:00:00.001Z'
            };
            const execution = {...executionBase,executionId:T.typedHash('atlas-execution-sha256:','learnit.atlas.m1.v0.3/execution-id',executionBase)};
            const eventBase = {
              eventVersion:'atlas.learning-event.v1', kind:'activity-corrected',
              objectiveRef, executionId:execution.executionId,
              correctsEventId:item.correctsEventId, occurredAt:'2026-01-01T00:00:00.002Z'
            };
            const event = {
              ...eventBase,
              eventId:T.typedHash(
                'atlas-event-sha256:',
                'learnit.atlas.m1.v0.3/event-id',
                S.pedagogicalEventIdentity(eventBase)
              )
            };
            const resumeState = {
              ...initialResume, nextItemPosition:1, focusTarget:'atlas-session-summary',
              lastCommittedEventId:event.eventId,
              itemStates:[{itemPosition:0,submissionOrdinal:1,assistance:'none',assistanceUseIds:[]}]
            };
            return {...{execution,event,resumeState},...overrides};
          }

          let calls = [], focus = [];
          const core = {
            commitActivitySubmission: async (...args) => {calls.push(args); return makeCommitResult();},
            requestAssistance: async (sid,pos,kind) => {
              calls.push([sid,pos,kind]);
              const base = {assistanceVersion:'atlas.assistance-use.v1',sessionRef,itemPosition:pos,assistanceKind:kind,recordedAt:'2026-01-01T00:00:00.000Z'};
              return {committed:true,record:{...base,assistanceUseId:T.typedHash('atlas-assistance-sha256:','learnit.atlas.m1.v0.3/assistance-use-id',base)}};
            }
          };
          const controller = S.createSessionController({core,focus:value=>focus.push(value),plan});
          assert.throws(() => controller.start({sessionId:'s',planId:plan.planId},initialResume), /INVALID_SESSION_REF/);
          assert.throws(() => controller.start(sessionRef,{nextItemPosition:0}), /MISSING_FIELD/);
          assert.throws(() => controller.start(sessionRef,{...initialResume,sessionRef:{...sessionRef,sessionId:id('atlas-session-sha256:','7')}}), /RESUME_SESSION_MISMATCH/);
          assert.deepStrictEqual(controller.start(sessionRef,initialResume).itemPosition,0);

          (async () => {
            const result = await controller.submit({choiceId:'raw'});
            assert.deepStrictEqual(calls[0],[sessionRef.sessionId,0,{choiceId:'raw'}]);
            assert.equal(controller.snapshot().itemPosition,1);
            assert.deepStrictEqual(focus,['atlas-session-item-0','atlas-session-summary']);
            assert(result.execution.executionId);

            const makeController = returned => {
              const c = S.createSessionController({core:{...core,commitActivitySubmission:async()=>returned},plan});
              c.start(sessionRef,initialResume);
              return c;
            };
            const good = makeCommitResult();
            const foreignSessionExecution = {...good.execution,sessionRef:{...sessionRef,sessionId:id('atlas-session-sha256:','6')}};
            assert.rejects(() => makeController({...good,execution:foreignSessionExecution}).submit({}), /SCOPE_MISMATCH|IDENTITY_MISMATCH/);
            assert.rejects(() => makeController({...good,resumeState:{...good.resumeState,nextItemPosition:0}}).submit({}), /RESUME_MISMATCH/);
            assert.rejects(() => makeController({...good,resumeState:{...good.resumeState,lastCommittedEventId:id('atlas-event-sha256:','7')}}).submit({}), /RESUME_MISMATCH/);
            assert.rejects(() => makeController({...good,event:{...good.event,eventId:id('atlas-event-sha256:','7')}}).submit({}), /IDENTITY_MISMATCH/);
            assert.rejects(() => makeController({event:good.event,resumeState:good.resumeState}).submit({}), /MISSING_FIELD/);
            assert.rejects(() => makeController({...good,extra:true}).submit({}), /UNKNOWN_FIELD/);

            const helpController = S.createSessionController({core,plan});
            helpController.start(sessionRef,initialResume);
            const confirmation = await helpController.requestHelp('hint');
            assert.equal(confirmation.committed,true);
            const badHelp = S.createSessionController({core:{...core,requestAssistance:async()=>({committed:false,record:{}})},plan});
            badHelp.start(sessionRef,initialResume);
            await assert.rejects(() => badHelp.requestHelp('hint'), /NOT_PERSISTED/);

            const completed = S.renderSession({plan,resumeState:good.resumeState});
            assert(completed.includes('Séance terminée'));
            assert(!completed.includes('data-atlas-submit'));

            const signal = {
              ruleVersion:'atlas.learning.reward.v1',rewardId:id('atlas-reward-sha256:','4'),
              kind:'validation-reconfirmed',labelCode:'reward.validation_reconfirmed',
              objectiveRef,evidenceEventIds:[id('atlas-event-sha256:','5')],
              occurredAt:'2026-01-01T00:00:00.000Z'
            };
            assert(R.renderRewards([signal]).includes('reconfirmée'));
            assert.throws(() => R.validateSignal({...signal,kind:'transfer-completed'}), /INVALID_REWARD/);
            console.log('ATLAS_EXPERIENCE_V3_NODE_PASS 52/52');
          })().catch(error => {console.error(error); process.exit(1);});
        '''
        completed = self.run_node(script)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('52/52', completed.stdout)

    def test_event_identity_fixed_contract_vectors(self):
        script = self.event_identity_prelude() + r'''
          assert.deepStrictEqual(S.pedagogicalEventIdentity(attemptEvent), {
            eventVersion:'atlas.learning-event.v1',
            kind:'activity-attempt',
            executionId:attemptExecutionId
          });
          assert.deepStrictEqual(S.pedagogicalEventIdentity(correctedEvent), {
            eventVersion:'atlas.learning-event.v1',
            kind:'activity-corrected',
            executionId:correctedExecutionId,
            correctsEventId:correctionTarget
          });
          assert.equal(
            T.canonicalJson(S.pedagogicalEventIdentity(attemptEvent)),
            '{"eventVersion":"atlas.learning-event.v1","executionId":"atlas-execution-sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","kind":"activity-attempt"}'
          );
          assert.equal(
            T.canonicalJson(S.pedagogicalEventIdentity(correctedEvent)),
            '{"correctsEventId":"atlas-event-sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","eventVersion":"atlas.learning-event.v1","executionId":"atlas-execution-sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","kind":"activity-corrected"}'
          );
          assert.equal(attemptEvent.eventId, 'atlas-event-sha256:1012f4383ec8101f37275415f0dd5e3cb07b3d50c9b849e7208b46c8e84509ba');
          assert.equal(correctedEvent.eventId, 'atlas-event-sha256:186542615b69bb6b96054ba2ecc8499b192fd954b9bce41f01e533dfca246e01');
          console.log('ATLAS_EXPERIENCE_EVENT_FIXED_VECTORS_PASS');
        '''
        completed = self.run_node(script)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('FIXED_VECTORS_PASS', completed.stdout)

    def test_event_identity_timestamp_objective_and_permutation_invariance(self):
        script = self.event_identity_prelude() + r'''
          const later = {...attemptEvent,occurredAt:'2026-12-31T23:59:59.999Z'};
          const otherObjective = {...attemptEvent,objectiveRef:otherObjectiveRef};
          const permuted = {
            occurredAt:attemptEvent.occurredAt,
            executionId:attemptEvent.executionId,
            eventId:attemptEvent.eventId,
            objectiveRef:attemptEvent.objectiveRef,
            kind:attemptEvent.kind,
            eventVersion:attemptEvent.eventVersion
          };
          assert.equal(coreEventId(later), attemptEvent.eventId);
          assert.equal(coreEventId(otherObjective), attemptEvent.eventId);
          assert.equal(coreEventId(permuted), attemptEvent.eventId);
          assert.doesNotThrow(() => S.validatePedagogicalEvent(later,attemptExecution,attemptItem));
          assert.doesNotThrow(() => S.validatePedagogicalEvent(permuted,attemptExecution,attemptItem));
          assert.doesNotThrow(() => S.validatePedagogicalEvent(otherObjective,attemptExecution,{executionClass:'practice',objectiveRef:otherObjectiveRef}));
          console.log('ATLAS_EXPERIENCE_EVENT_INVARIANCE_PASS');
        '''
        completed = self.run_node(script)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('INVARIANCE_PASS', completed.stdout)

    def test_core_formula_accepted_and_legacy_expanded_formula_rejected(self):
        script = self.event_identity_prelude() + r'''
          assert.doesNotThrow(() => S.validatePedagogicalEvent(attemptEvent,attemptExecution,attemptItem));
          assert.doesNotThrow(() => S.validatePedagogicalEvent(correctedEvent,correctedExecution,correctedItem));

          const legacyAttempt = {...attemptBase,eventId:legacyEventId(attemptBase)};
          const legacyCorrected = {...correctedBase,eventId:legacyEventId(correctedBase)};
          assert.notEqual(legacyAttempt.eventId, attemptEvent.eventId);
          assert.notEqual(legacyCorrected.eventId, correctedEvent.eventId);
          assert.throws(
            () => S.validatePedagogicalEvent(legacyAttempt,attemptExecution,attemptItem),
            /CORE_COMMIT_IDENTITY_MISMATCH/
          );
          assert.throws(
            () => S.validatePedagogicalEvent(legacyCorrected,correctedExecution,correctedItem),
            /CORE_COMMIT_IDENTITY_MISMATCH/
          );
          console.log('ATLAS_EXPERIENCE_CORE_COMPATIBILITY_PASS');
        '''
        completed = self.run_node(script)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('CORE_COMPATIBILITY_PASS', completed.stdout)

    def test_event_identity_boundaries_and_fail_closed(self):
        script = self.event_identity_prelude() + r'''
          const attemptWithCorrectionTarget = {...attemptEvent,correctsEventId:correctionTarget};
          assert.throws(
            () => S.validatePedagogicalEvent(attemptWithCorrectionTarget,attemptExecution,attemptItem),
            /UNKNOWN_FIELD/
          );

          const correctedWithoutTarget = {...correctedEvent};
          delete correctedWithoutTarget.correctsEventId;
          assert.throws(
            () => S.validatePedagogicalEvent(correctedWithoutTarget,correctedExecution,correctedItem),
            /CORE_COMMIT_EVENT_MISMATCH/
          );

          const foreignTarget = id('atlas-event-sha256:','d');
          const correctedForeignBase = {...correctedBase,correctsEventId:foreignTarget};
          const correctedForeign = {...correctedForeignBase,eventId:coreEventId(correctedForeignBase)};
          assert.throws(
            () => S.validatePedagogicalEvent(correctedForeign,correctedExecution,correctedItem),
            /CORE_COMMIT_EVENT_MISMATCH/
          );

          assert.throws(
            () => S.validatePedagogicalEvent({...attemptEvent,unexpected:true},attemptExecution,attemptItem),
            /UNKNOWN_FIELD/
          );
          assert.throws(
            () => S.validatePedagogicalEvent({...attemptEvent,eventVersion:'atlas.learning-event.v2'},attemptExecution,attemptItem),
            /INVALID_CORE_COMMIT/
          );
          assert.throws(
            () => S.validatePedagogicalEvent({...attemptEvent,executionId:id('atlas-execution-sha256:','f')},attemptExecution,attemptItem),
            /CORE_COMMIT_EVENT_MISMATCH/
          );
          console.log('ATLAS_EXPERIENCE_EVENT_FAIL_CLOSED_PASS');
        '''
        completed = self.run_node(script)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('FAIL_CLOSED_PASS', completed.stdout)

    def test_css_isolated_and_mobile(self):
        css = (ROOT / 'src/atlas.css').read_text(encoding='utf-8')
        self.assertIn('.atlas-m1', css)
        self.assertIn('@media(max-width:520px)', css)
        self.assertNotIn('body{', css)

    def test_no_forbidden_runtime_dependencies(self):
        text = '\n'.join(path.read_text(encoding='utf-8') for path in (ROOT / 'src/ui').glob('atlas_*.js'))
        for token in ('indexedDB', 'localStorage', 'Math.random', 'fetch(', 'Date.now', "require('crypto')", 'WebSocket', 'XMLHttpRequest'):
            self.assertNotIn(token, text)

    def test_javascript_syntax(self):
        for path in (ROOT / 'src/ui').glob('atlas_*.js'):
            completed = subprocess.run(['node', '--check', str(path)], capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)