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
          assert(U.renderSummary({evidence:[evidence],completed:true}).includes('ni une certification'));
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
            const event = {...eventBase,eventId:T.typedHash('atlas-event-sha256:','learnit.atlas.m1.v0.3/event-id',eventBase)};
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
            console.log('ATLAS_EXPERIENCE_V2_NODE_PASS 52/52');
          })().catch(error => {console.error(error); process.exit(1);});
        '''
        completed = self.run_node(script)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('52/52', completed.stdout)

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
