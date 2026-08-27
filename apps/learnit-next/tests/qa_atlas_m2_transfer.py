#!/usr/bin/env python3
import pathlib
import subprocess
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AtlasM2TransferContradictoryQA(unittest.TestCase):
    def run_node(self, body: str) -> str:
        completed = subprocess.run(
            ["node", "-e", textwrap.dedent(body), str(ROOT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return completed.stdout

    def test_transfer_adversarial_contract(self):
        output = self.run_node(r"""
          const assert = require('assert');
          const root = process.argv[1];
          const V = require(root + '/src/core/atlas_events.js');
          const E = require(root + '/src/core/atlas_evidence.js');
          const M = require(root + '/src/core/atlas_memory.js');
          const T = require(root + '/src/core/atlas_transfer.js');
          const R = require(root + '/src/core/atlas_recommendation.js');
          const P = require(root + '/src/core/atlas_projection.js');
          const Planner = require(root + '/src/core/atlas_planner.js');
          const Today = require(root + '/src/ui/atlas_today.js');

          const courseRef = {packageLineageId:'qa-pkg',courseLineageId:'qa-course'};
          const objectiveRef = {courseRef,objectiveId:'qa-objective'};
          const practiceRef = {courseRef,activityLineageId:'qa-practice'};
          const validationRef = {courseRef,activityLineageId:'qa-validation'};
          const transferRef = {courseRef,activityLineageId:'qa-transfer'};
          const contentRevisionRef = {
            packageLineageId:'qa-pkg',
            packageRevisionId:'qa-revision',
            packageDigest:'sha256:' + 'f'.repeat(64),
          };
          const sessionRef = {
            sessionId:'atlas-session-sha256:' + '9'.repeat(64),
            planId:'atlas-plan-sha256:' + '8'.repeat(64),
          };

          let ordinal = 0;
          function execution(action, activityRef, at, outcome='correct', assistance='none') {
            ordinal += 1;
            const digit = String((ordinal + 2) % 10);
            const record = {
              executionVersion:'atlas.scored-execution.v1',
              sessionRef,
              courseRef,
              contentRevisionRef,
              planDigest:'sha256:' + '7'.repeat(64),
              itemPosition:ordinal - 1,
              submissionOrdinal:1,
              objectiveRef,
              activityRef,
              action,
              executionClass:V.actionClass(action),
              responseDigest:'sha256:' + digit.repeat(64),
              scoringRuleId:'qa-rule-' + ordinal,
              scoringRuleDigest:'sha256:' + String((ordinal + 3) % 10).repeat(64),
              outcome,
              assistance,
              assistanceUseIds:assistance === 'used'
                ? ['atlas-assistance-sha256:' + '6'.repeat(64)]
                : [],
              submittedAt:at,
              scoredAt:at,
            };
            return Object.freeze({...record,executionId:V.executionId(record)});
          }
          function attemptEvent(execution) {
            const identity = {
              eventVersion:'atlas.learning-event.v1',
              kind:'activity-attempt',
              executionId:execution.executionId,
            };
            return Object.freeze({
              ...identity,
              eventId:V.eventId(identity),
              objectiveRef,
              occurredAt:execution.scoredAt,
            });
          }

          const v0 = execution(
            'attempt-validation',validationRef,'2026-07-04T08:00:00.000Z'
          );
          const ids0 = new Set([v0.executionId]);
          const noReconfirm = T.status({
            learningEvents:[attemptEvent(v0)],
            scoredExecutions:[v0],
            objectiveRef,
            admissibleExecutionIds:ids0,
            evidenceModule:E,
          });
          assert.equal(noReconfirm.eligible,false);

          const m1 = execution(
            'maintain-recent-validation',validationRef,'2026-07-05T08:00:00.000Z'
          );
          const ids1 = new Set([v0.executionId,m1.executionId]);
          const firstUnlock = T.status({
            learningEvents:[attemptEvent(v0),attemptEvent(m1)],
            scoredExecutions:[v0,m1],
            objectiveRef,
            admissibleExecutionIds:ids1,
            evidenceModule:E,
          });
          assert.equal(firstUnlock.eligible,true);

          const t1 = execution(
            'attempt-transfer',transferRef,'2026-07-05T08:10:00.000Z','correct','none'
          );
          const afterOne = T.status({
            learningEvents:[attemptEvent(v0),attemptEvent(m1),attemptEvent(t1)],
            scoredExecutions:[v0,m1,t1],
            objectiveRef,
            admissibleExecutionIds:ids1,
            evidenceModule:E,
          });
          assert.equal(afterOne.eligible,false);
          assert.equal(afterOne.transferEvidence.independentSuccesses,1);

          const memoryA = M.status({
            now:'2026-07-06T08:00:00.000Z',
            executions:[v0,m1],
            objectiveRef,
            admissibleExecutionIds:ids1,
            evidenceModule:E,
          });
          const memoryB = M.status({
            now:'2026-07-06T08:00:00.000Z',
            executions:[v0,m1,t1],
            objectiveRef,
            admissibleExecutionIds:ids1,
            evidenceModule:E,
          });
          assert.deepStrictEqual(
            {
              count:memoryB.reconfirmationCount,
              interval:memoryB.intervalDays,
              dueAt:memoryB.dueAt,
            },
            {
              count:memoryA.reconfirmationCount,
              interval:memoryA.intervalDays,
              dueAt:memoryA.dueAt,
            },
          );

          const m2 = execution(
            'maintain-recent-validation',validationRef,'2026-07-08T08:00:00.000Z'
          );
          const ids2 = new Set([...ids1,m2.executionId]);
          const secondUnlock = T.status({
            learningEvents:[
              attemptEvent(v0),attemptEvent(m1),attemptEvent(t1),attemptEvent(m2)
            ],
            scoredExecutions:[v0,m1,t1,m2],
            objectiveRef,
            admissibleExecutionIds:ids2,
            evidenceModule:E,
          });
          assert.equal(secondUnlock.eligible,true);

          const t2 = execution(
            'attempt-transfer',transferRef,'2026-07-08T08:05:00.000Z','correct','used'
          );
          const assisted = T.status({
            learningEvents:[
              attemptEvent(v0),attemptEvent(m1),attemptEvent(t1),attemptEvent(m2),
              attemptEvent(t2)
            ],
            scoredExecutions:[v0,m1,t1,m2,t2],
            objectiveRef,
            admissibleExecutionIds:ids2,
            evidenceModule:E,
          });
          assert.equal(assisted.transferEvidence.attempts,2);
          assert.equal(assisted.transferEvidence.independentSuccesses,1);
          assert.equal(assisted.eligible,false);

          const m3 = execution(
            'maintain-recent-validation',validationRef,'2026-07-15T08:00:00.000Z'
          );
          const ids3 = new Set([...ids2,m3.executionId]);
          const t3 = execution(
            'attempt-transfer',transferRef,'2026-07-15T08:03:00.000Z','incorrect','none'
          );
          const failed = T.status({
            learningEvents:[
              attemptEvent(v0),attemptEvent(m1),attemptEvent(t1),attemptEvent(m2),
              attemptEvent(t2),attemptEvent(m3),attemptEvent(t3)
            ],
            scoredExecutions:[v0,m1,t1,m2,t2,m3,t3],
            objectiveRef,
            admissibleExecutionIds:ids3,
            evidenceModule:E,
          });
          assert.equal(failed.transferEvidence.attempts,3);
          assert.equal(failed.transferEvidence.independentSuccesses,1);
          assert.equal(failed.eligible,false);

          const projection = P.projectObjectiveEvidence(
            [
              attemptEvent(v0),attemptEvent(m1),attemptEvent(t1),
              attemptEvent(m2),attemptEvent(t2),attemptEvent(m3),attemptEvent(t3)
            ],
            [v0,m1,t1,m2,t2,m3,t3],
            execution => ids3.has(execution.executionId),
          );
          assert.equal(projection[0].state,'validated-recently');
          assert.equal(projection[0].validationAttempts,4);
          assert.equal(projection[0].lastValidationAt,m3.scoredAt);
          assert.equal(projection[0].lastEvidenceAt,t3.scoredAt);

          assert.equal(
            R.actionForEvidence(
              {objectiveRef,state:'validated-recently'},
              {maintenanceEligible:true,transferEligible:true},
            )[0],
            'maintain-recent-validation',
          );
          assert.equal(
            R.actionForEvidence(
              {objectiveRef,state:'validated-recently'},
              {maintenanceEligible:false,transferEligible:true},
            )[0],
            'attempt-transfer',
          );
          assert.notEqual(
            R.actionForEvidence(
              {objectiveRef,state:'review-needed'},
              {maintenanceEligible:false,transferEligible:true,hasCorrectablePracticeError:true},
            )[0],
            'attempt-transfer',
          );

          const transferOnlyIndex = E.indexActivities([
            {
              activityRef:transferRef,objectiveRef,
              learningPhase:'transfer',assessmentRole:'practice',estimatedMinutes:4,
            },
          ],[
            {objectiveRef,activityRef:transferRef,authorIndex:0},
          ]);
          const rec = R.buildRecommendation({
            objectiveRef,
            evidence:{objectiveRef,state:'validated-recently'},
            index:transferOnlyIndex,
            context:{maintenanceEligible:false,transferEligible:true},
          });
          assert.equal(rec.action,'attempt-transfer');
          assert.deepStrictEqual(rec.reasonCodes,['TRANSFER_AVAILABLE']);
          assert.equal(rec.eligibleActivityRefs.length,1);

          const noTransferIndex = E.indexActivities([
            {
              activityRef:practiceRef,objectiveRef,
              learningPhase:'application',assessmentRole:'practice',estimatedMinutes:4,
            },
          ],[
            {objectiveRef,activityRef:practiceRef,authorIndex:0},
          ]);
          assert.throws(
            () => R.buildRecommendation({
              objectiveRef,
              evidence:{objectiveRef,state:'validated-recently'},
              index:noTransferIndex,
              context:{maintenanceEligible:false,transferEligible:true},
            }),
            error => error && error.code === 'NO_ELIGIBLE_ACTIVITY',
          );

          const plan = Planner.buildPlan({
            engineVersion:'qa.transfer.v1',
            courseRef,
            contentRevisionRef,
            durationMinutes:5,
            recommendations:[rec],
            itemProvenance:[{}],
          });
          assert.equal(plan.payload.items[0].executionClass,'transfer');
          assert.equal(plan.payload.items[0].action,'attempt-transfer');
          assert.equal('validationBasisEventId' in plan.payload.items[0],false);

          assert.throws(
            () => V.validatePlanItem({
              ...plan.payload.items[0],
              validationBasisEventId:'atlas-event-sha256:' + '1'.repeat(64),
            },0),
            error => error && error.code === 'UNKNOWN_FIELD',
          );
          assert.throws(() => V.actionClass('transfer-completed'), /UNKNOWN_ACTION/);
          assert.equal(E.REASON_CODES.includes('TRANSFER_AVAILABLE'),true);
          assert.equal(E.REASON_CODES.includes('TRANSFER_COMPLETED'),false);

          const html = Today.renderToday({recommendation:rec,plan});
          assert.match(html,/Défi de transfert/);
          assert.match(html,/autre contexte/);
          assert.doesNotMatch(html,/maîtrise|certification|durable/i);

          assert.throws(
            () => T.projectTransferEvidence({
              learningEvents:[],
              scoredExecutions:[t1],
              evidenceModule:E,
            }),
            error => error && error.code === 'MISSING_TRANSFER_EVENT',
          );

          const duplicate = attemptEvent(t1);
          assert.throws(
            () => T.projectTransferEvidence({
              learningEvents:[duplicate,duplicate],
              scoredExecutions:[t1],
              evidenceModule:E,
            }),
            error => error && error.code === 'DUPLICATE_TRANSFER_EVENT',
          );

          console.log('PASS_QA_M2_TRANSFER_ADVERSARIAL_CONTRACT');
        """)
        self.assertIn("PASS_QA_M2_TRANSFER_ADVERSARIAL_CONTRACT", output)


if __name__ == "__main__":
    unittest.main()
