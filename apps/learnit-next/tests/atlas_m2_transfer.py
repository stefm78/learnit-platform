#!/usr/bin/env python3
import pathlib
import subprocess
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AtlasM2TransferTests(unittest.TestCase):
    def run_node(self, body: str) -> str:
        completed = subprocess.run(
            ["node", "-e", textwrap.dedent(body), str(ROOT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return completed.stdout

    def test_transfer_contract_eligibility_priority_and_projection(self):
        output = self.run_node(r"""
          const assert = require('assert');
          const root = process.argv[1];
          const V = require(root + '/src/core/atlas_events.js');
          const E = require(root + '/src/core/atlas_evidence.js');
          const M = require(root + '/src/core/atlas_memory.js');
          const T = require(root + '/src/core/atlas_transfer.js');
          const R = require(root + '/src/core/atlas_recommendation.js');
          const P = require(root + '/src/core/atlas_projection.js');

          const courseRef = {packageLineageId:'pkg',courseLineageId:'course'};
          const objectiveRef = {courseRef,objectiveId:'objective'};
          const practiceRef = {courseRef,activityLineageId:'practice'};
          const validationRef = {courseRef,activityLineageId:'validation'};
          const transferRef = {courseRef,activityLineageId:'transfer'};
          const contentRevisionRef = {
            packageLineageId:'pkg',
            packageRevisionId:'revision',
            packageDigest:'sha256:' + 'a'.repeat(64),
          };
          const sessionRef = {
            sessionId:'atlas-session-sha256:' + 'b'.repeat(64),
            planId:'atlas-plan-sha256:' + 'c'.repeat(64),
          };

          let ordinal = 0;
          function execution(action, activityRef, at, outcome='correct', assistance='none') {
            ordinal += 1;
            const record = {
              executionVersion:'atlas.scored-execution.v1',
              sessionRef,
              courseRef,
              contentRevisionRef,
              planDigest:'sha256:' + 'd'.repeat(64),
              itemPosition:ordinal - 1,
              submissionOrdinal:1,
              objectiveRef,
              activityRef,
              action,
              executionClass:V.actionClass(action),
              responseDigest:'sha256:' + String(ordinal % 10).repeat(64),
              scoringRuleId:'rule-' + ordinal,
              scoringRuleDigest:'sha256:' + String((ordinal + 1) % 10).repeat(64),
              outcome,
              assistance,
              assistanceUseIds:assistance === 'used'
                ? ['atlas-assistance-sha256:' + 'e'.repeat(64)]
                : [],
              submittedAt:at,
              scoredAt:at,
            };
            return Object.freeze({...record, executionId:V.executionId(record)});
          }
          function event(execution) {
            const payload = {
              eventVersion:'atlas.learning-event.v1',
              kind:'activity-attempt',
              objectiveRef,
              executionId:execution.executionId,
              occurredAt:execution.scoredAt,
            };
            return Object.freeze({...payload, eventId:V.eventId(payload)});
          }

          const initial = execution(
            'attempt-validation', validationRef, '2026-08-01T10:00:00.000Z'
          );
          const reconfirm1 = execution(
            'maintain-recent-validation', validationRef, '2026-08-02T10:00:00.000Z'
          );
          const ids1 = new Set([initial.executionId, reconfirm1.executionId]);

          const before = T.status({
            learningEvents:[event(initial)],
            scoredExecutions:[initial],
            objectiveRef,
            admissibleExecutionIds:new Set([initial.executionId]),
            evidenceModule:E,
          });
          assert.equal(before.eligible, false);
          assert.equal(before.reconfirmationCount, 0);

          const unlocked = T.status({
            learningEvents:[event(initial),event(reconfirm1)],
            scoredExecutions:[initial,reconfirm1],
            objectiveRef,
            admissibleExecutionIds:ids1,
            evidenceModule:E,
          });
          assert.equal(unlocked.eligible, true);
          assert.equal(unlocked.reconfirmationCount, 1);
          assert.equal(unlocked.basisExecution.executionId, reconfirm1.executionId);

          const memoryBefore = M.status({
            now:'2026-08-03T10:00:00.000Z',
            executions:[initial,reconfirm1],
            objectiveRef,
            admissibleExecutionIds:ids1,
            evidenceModule:E,
          });

          const failedTransfer = execution(
            'attempt-transfer', transferRef, '2026-08-02T10:05:00.000Z', 'incorrect'
          );
          const afterFailed = T.status({
            learningEvents:[event(initial),event(reconfirm1),event(failedTransfer)],
            scoredExecutions:[initial,reconfirm1,failedTransfer],
            objectiveRef,
            admissibleExecutionIds:ids1,
            evidenceModule:E,
          });
          assert.equal(afterFailed.eligible, false);
          assert.equal(afterFailed.transferEvidence.attempts, 1);
          assert.equal(afterFailed.transferEvidence.independentSuccesses, 0);

          const memoryAfter = M.status({
            now:'2026-08-03T10:00:00.000Z',
            executions:[initial,reconfirm1,failedTransfer],
            objectiveRef,
            admissibleExecutionIds:ids1,
            evidenceModule:E,
          });
          assert.equal(memoryAfter.reconfirmationCount, memoryBefore.reconfirmationCount);
          assert.equal(memoryAfter.intervalDays, memoryBefore.intervalDays);
          assert.equal(memoryAfter.dueAt, memoryBefore.dueAt);

          const reconfirm2 = execution(
            'maintain-recent-validation', validationRef, '2026-08-05T10:00:00.000Z'
          );
          const ids2 = new Set([...ids1,reconfirm2.executionId]);
          const unlockedAgain = T.status({
            learningEvents:[
              event(initial),event(reconfirm1),event(failedTransfer),event(reconfirm2)
            ],
            scoredExecutions:[initial,reconfirm1,failedTransfer,reconfirm2],
            objectiveRef,
            admissibleExecutionIds:ids2,
            evidenceModule:E,
          });
          assert.equal(unlockedAgain.eligible, true);
          assert.equal(unlockedAgain.reconfirmationCount, 2);

          const assistedTransfer = execution(
            'attempt-transfer', transferRef, '2026-08-05T10:05:00.000Z', 'correct', 'used'
          );
          const assisted = T.status({
            learningEvents:[
              event(initial),event(reconfirm1),event(failedTransfer),event(reconfirm2),
              event(assistedTransfer)
            ],
            scoredExecutions:[
              initial,reconfirm1,failedTransfer,reconfirm2,assistedTransfer
            ],
            objectiveRef,
            admissibleExecutionIds:ids2,
            evidenceModule:E,
          });
          assert.equal(assisted.eligible, false);
          assert.equal(assisted.transferEvidence.attempts, 2);
          assert.equal(assisted.transferEvidence.independentSuccesses, 0);

          const reconfirm3 = execution(
            'maintain-recent-validation', validationRef, '2026-08-12T10:00:00.000Z'
          );
          const ids3 = new Set([...ids2,reconfirm3.executionId]);
          const successTransfer = execution(
            'attempt-transfer', transferRef, '2026-08-12T10:05:00.000Z', 'correct', 'none'
          );
          const success = T.status({
            learningEvents:[
              event(initial),event(reconfirm1),event(failedTransfer),event(reconfirm2),
              event(assistedTransfer),event(reconfirm3),event(successTransfer)
            ],
            scoredExecutions:[
              initial,reconfirm1,failedTransfer,reconfirm2,assistedTransfer,reconfirm3,
              successTransfer
            ],
            objectiveRef,
            admissibleExecutionIds:ids3,
            evidenceModule:E,
          });
          assert.equal(success.eligible, false);
          assert.equal(success.transferEvidence.attempts, 3);
          assert.equal(success.transferEvidence.independentSuccesses, 1);
          assert.equal(
            success.transferEvidence.lastIndependentSuccessAt,
            successTransfer.scoredAt,
          );

          assert.equal(E.executionClassForAction('attempt-transfer'), 'transfer');
          assert.equal(V.actionClass('attempt-transfer'), 'transfer');
          assert.throws(() => V.actionClass('transfer-completed'), /UNKNOWN_ACTION/);

          const index = E.indexActivities([
            {
              activityRef:practiceRef, objectiveRef,
              learningPhase:'application', assessmentRole:'practice', estimatedMinutes:4,
            },
            {
              activityRef:transferRef, objectiveRef,
              learningPhase:'transfer', assessmentRole:'practice', estimatedMinutes:4,
            },
          ],[
            {objectiveRef,activityRef:practiceRef,authorIndex:0},
            {objectiveRef,activityRef:transferRef,authorIndex:1},
          ]);
          const eligibleTransfer = E.eligibleActivities(
            index, objectiveRef, 'attempt-transfer'
          );
          assert.equal(eligibleTransfer.length, 1);
          assert.equal(
            E.canonicalRefKey(eligibleTransfer[0].activityRef),
            E.canonicalRefKey(transferRef),
          );

          const validated = {objectiveRef,state:'validated-recently'};
          assert.equal(
            R.actionForEvidence(validated,{maintenanceEligible:true,transferEligible:true})[0],
            'maintain-recent-validation',
          );
          assert.equal(
            R.actionForEvidence(validated,{maintenanceEligible:false,transferEligible:true})[0],
            'attempt-transfer',
          );
          assert.deepStrictEqual(
            R.actionForEvidence(validated,{maintenanceEligible:false,transferEligible:true})[1],
            ['TRANSFER_AVAILABLE'],
          );
          assert.equal(
            R.actionForEvidence(
              {objectiveRef,state:'review-needed'},
              {hasCorrectablePracticeError:true,transferEligible:true},
            )[0],
            'correct-practice',
          );

          const projection = P.projectObjectiveEvidence(
            [
              event(initial),
              event(reconfirm1),
              event(failedTransfer),
            ],
            [initial,reconfirm1,failedTransfer],
            execution => ids1.has(execution.executionId),
          );
          assert.equal(projection.length, 1);
          assert.equal(projection[0].state, 'validated-recently');
          assert.equal(projection[0].validationAttempts, 2);
          assert.equal(projection[0].lastValidationAt, reconfirm1.scoredAt);
          assert.equal(projection[0].lastEvidenceAt, failedTransfer.scoredAt);

          assert.throws(
            () => P.projectObjectiveEvidence(
              [event(failedTransfer)],
              [failedTransfer],
              () => false,
            ),
            error => error && error.code === 'TRANSFER_WITHOUT_CURRENT_VALIDATION',
          );

          console.log('PASS_ATLAS_M2_TRANSFER_DEVELOPER_CONTRACT');
        """)
        self.assertIn("PASS_ATLAS_M2_TRANSFER_DEVELOPER_CONTRACT", output)


if __name__ == "__main__":
    unittest.main()
