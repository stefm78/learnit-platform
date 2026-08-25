#!/usr/bin/env python3
import pathlib
import subprocess
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AtlasM2MemoryTests(unittest.TestCase):
    def run_node(self, body: str) -> str:
        script = textwrap.dedent(body)
        completed = subprocess.run(
            ["node", "-e", script, str(ROOT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return completed.stdout

    def test_memory_policy_claim_authority_and_recommendation(self):
        output = self.run_node(r'''
          const assert = require('assert');
          const root = process.argv[1];
          const E = require(root + '/src/core/atlas_evidence.js');
          const A = require(root + '/src/core/atlas_claim_authority.js');
          const M = require(root + '/src/core/atlas_memory.js');
          const R = require(root + '/src/core/atlas_recommendation.js');
          const I = require(root + '/src/adapters/atlas_indexeddb.js');
          let checks = 0;
          const check = fn => { fn(); checks += 1; };

          check(() => assert.equal(A.ORACLE_VERSION, 'git:67d70e7307402242dbc1939d6cabfd87af617d74'));
          check(() => assert.equal(A.EVIDENCE_ARTIFACT_DIGEST, 'sha256:6ca39dd107aea45c14cd7bec7c7ff447c36af1fc12e1c8b3f6c1a0fdc066028f'));
          check(() => assert.equal(A.CLAIMS.length, 4));
          check(() => assert.deepStrictEqual(A.ACCEPTED_CLAIM_IDS, [...A.ACCEPTED_CLAIM_IDS].sort()));

          const context = {
            packageLineageId: A.CONTENT_REVISION_REF.packageLineageId,
            packageRevisionId: A.CONTENT_REVISION_REF.packageRevisionId,
            packageDigest: A.CONTENT_REVISION_REF.packageDigest,
            course: {courseLineageId: A.COURSE_REF.courseLineageId},
          };
          check(() => assert.equal(A.contextAccepted(context), true));
          check(() => assert.equal(A.contextAccepted({...context, packageRevisionId: 'wrong'}), false));
          check(() => assert.equal(A.claimsForContext({...context, packageDigest: 'sha256:' + '0'.repeat(64)}).length, 0));

          const claim = A.CLAIMS[0];
          const details = {
            objectiveRef: claim.objectiveRef,
            sourceActivityRef: claim.sourceActivityRef,
            targetActivityRef: claim.targetActivityRef,
            contentRevisionRef: A.CONTENT_REVISION_REF,
            independenceClaimId: claim.claimId,
          };
          check(() => assert.equal(A.validateRuntimeClaim({independenceClaimId: claim.claimId}, details), true));
          check(() => assert.equal(A.validateRuntimeClaim({independenceClaimId: 'atlas-claim-sha256:' + '0'.repeat(64)}, details), false));
          check(() => assert.equal(A.validateRuntimeClaim({independenceClaimId: claim.claimId}, {...details, targetActivityRef: claim.sourceActivityRef}), false));
          check(() => assert.equal(A.validateRuntimeClaim({independenceClaimId: claim.claimId}, {...details, contentRevisionRef: {...A.CONTENT_REVISION_REF, packageRevisionId: 'wrong'}}), false));

          const permissive = I.runtimeRegistry({activity: () => ({}), validateClaim: () => true});
          check(() => assert.equal(permissive.validateClaim({independenceClaimId: claim.claimId}, details), true));
          check(() => assert.equal(permissive.validateClaim(
            {independenceClaimId: claim.claimId},
            {...details, contentRevisionRef: {...A.CONTENT_REVISION_REF, packageRevisionId: 'wrong'}},
          ), false));

          const objective = claim.objectiveRef;
          const execution = (id, action, at, overrides = {}) => ({
            executionId: 'atlas-execution-sha256:' + id.repeat(64),
            objectiveRef: objective,
            executionClass: 'validation',
            action,
            outcome: 'correct',
            assistance: 'none',
            scoredAt: at,
            ...overrides,
          });
          const e0 = execution('1', 'attempt-validation', '2026-08-01T10:00:00.000Z');
          const ids0 = new Set([e0.executionId]);
          const before = M.status({now:'2026-08-02T09:59:59.999Z', executions:[e0], objectiveRef:objective, admissibleExecutionIds:ids0, evidenceModule:E});
          const boundary = M.status({now:'2026-08-02T10:00:00.000Z', executions:[e0], objectiveRef:objective, admissibleExecutionIds:ids0, evidenceModule:E});
          check(() => assert.equal(before.due, false));
          check(() => assert.equal(boundary.due, true));
          check(() => assert.equal(boundary.intervalDays, 1));

          const e1 = execution('2', 'maintain-recent-validation', '2026-08-02T10:00:00.000Z');
          const e2 = execution('3', 'maintain-recent-validation', '2026-08-05T10:00:00.000Z');
          const e3 = execution('4', 'maintain-recent-validation', '2026-08-12T10:00:00.000Z');
          const e4 = execution('5', 'maintain-recent-validation', '2026-09-02T10:00:00.000Z');
          const chain = [e0,e1,e2,e3,e4];
          const ids = new Set(chain.map(item => item.executionId));
          const after1 = M.status({now:'2026-08-02T10:00:00.000Z', executions:[e0,e1], objectiveRef:objective, admissibleExecutionIds:ids, evidenceModule:E});
          const after2 = M.status({now:'2026-08-05T10:00:00.000Z', executions:[e0,e1,e2], objectiveRef:objective, admissibleExecutionIds:ids, evidenceModule:E});
          const after3 = M.status({now:'2026-08-12T10:00:00.000Z', executions:[e0,e1,e2,e3], objectiveRef:objective, admissibleExecutionIds:ids, evidenceModule:E});
          const after4 = M.status({now:'2026-09-02T10:00:00.000Z', executions:chain, objectiveRef:objective, admissibleExecutionIds:ids, evidenceModule:E});
          check(() => assert.equal(after1.intervalDays, 3));
          check(() => assert.equal(after1.dueAt, '2026-08-05T10:00:00.000Z'));
          check(() => assert.equal(after2.intervalDays, 7));
          check(() => assert.equal(after2.dueAt, '2026-08-12T10:00:00.000Z'));
          check(() => assert.equal(after3.intervalDays, 21));
          check(() => assert.equal(after3.dueAt, '2026-09-02T10:00:00.000Z'));
          check(() => assert.equal(after4.intervalDays, 21));
          check(() => assert.equal(after4.dueAt, '2026-09-23T10:00:00.000Z'));

          const assisted = execution('6', 'attempt-validation', '2026-08-01T10:00:00.000Z', {assistance:'used'});
          const assistedStatus = M.status({now:'2026-08-10T10:00:00.000Z', executions:[assisted], objectiveRef:objective, admissibleExecutionIds:new Set([assisted.executionId]), evidenceModule:E});
          check(() => assert.equal(assistedStatus.hasIndependentValidation, false));

          const target1 = A.CLAIMS[0].targetActivityRef;
          const target2 = A.CLAIMS[1].targetActivityRef;
          const rows = [
            {activityRef:claim.sourceActivityRef, objectiveRef:objective, learningPhase:'application', assessmentRole:'practice', estimatedMinutes:4},
            {activityRef:target1, objectiveRef:objective, learningPhase:'validation', assessmentRole:'validation', estimatedMinutes:5},
            {activityRef:target2, objectiveRef:objective, learningPhase:'validation', assessmentRole:'validation', estimatedMinutes:5},
          ];
          const links = rows.map((row, authorIndex) => ({objectiveRef:objective, activityRef:row.activityRef, authorIndex}));
          const index = E.indexActivities(rows, links);
          const rec = R.buildRecommendation({
            objectiveRef: objective,
            evidence: {objectiveRef:objective, state:'ready-for-validation'},
            index,
            context: {hasAcceptedValidation:true, acceptedTargetActivityRefs:[target2]},
          });
          check(() => assert.equal(rec.action, 'attempt-validation'));
          check(() => assert.equal(E.sameRef(rec.preferredActivityRef, target2), true));
          check(() => assert.equal(rec.eligibleActivityRefs.length, 1));

          const review = {objectiveRef:objective, state:'review-needed'};
          check(() => assert.equal(R.actionForEvidence(review, {hasCorrectablePracticeError:true})[0], 'correct-practice'));
          check(() => assert.equal(R.actionForEvidence(review, {hasCorrectablePracticeError:false})[0], 'continue-practice'));
          check(() => assert.deepStrictEqual(R.actionForEvidence(review, {hasCorrectablePracticeError:false})[1], ['RECENT_ERROR','REVIEW_REQUIRED']));

          const otherObjective = A.CLAIMS[2].objectiveRef;
          const ranked = R.rankRecommendations([
            {objectiveRef:objective, evidence:{objectiveRef:objective, state:'validated-recently'}},
            {objectiveRef:otherObjective, evidence:{objectiveRef:otherObjective, state:'review-needed'}},
          ]);
          check(() => assert.equal(ranked[0].evidence.state, 'review-needed'));

          console.log(`ATLAS_M2_MEMORY_NODE_PASS ${checks}/${checks}`);
        ''')
        self.assertRegex(output, r"ATLAS_M2_MEMORY_NODE_PASS \d+/\d+")

    def test_failed_validation_recovery_requires_fresh_validation(self):
        output = self.run_node(r'''
          const assert = require('assert');
          const root = process.argv[1];
          const E = require(root + '/src/core/atlas_events.js');
          const P = require(root + '/src/core/atlas_projection.js');
          const M = require(root + '/src/core/atlas_memory.js');

          const courseRef = {packageLineageId:'pkg', courseLineageId:'course'};
          const objectiveRef = {courseRef, objectiveId:'objective'};
          const contentRevisionRef = {
            packageLineageId:'pkg',
            packageRevisionId:'revision',
            packageDigest:'sha256:' + 'a'.repeat(64),
          };
          const sessionRef = {
            sessionId:'atlas-session-sha256:' + 'b'.repeat(64),
            planId:'atlas-plan-sha256:' + 'c'.repeat(64),
          };

          function execution(action, outcome, at, ordinal, activityLineageId) {
            const executionClass = ['attempt-validation','maintain-recent-validation'].includes(action)
              ? 'validation' : 'practice';
            const base = {
              executionVersion:'atlas.scored-execution.v1',
              sessionRef,
              courseRef,
              contentRevisionRef,
              planDigest:'sha256:' + 'd'.repeat(64),
              itemPosition:0,
              submissionOrdinal:ordinal,
              objectiveRef,
              activityRef:{courseRef,activityLineageId},
              action,
              executionClass,
              responseDigest:'sha256:' + 'e'.repeat(64),
              scoringRuleId:'qcm.v1',
              scoringRuleDigest:'sha256:' + 'f'.repeat(64),
              outcome,
              assistance:'none',
              assistanceUseIds:[],
              submittedAt:at,
              scoredAt:at,
            };
            return {...base, executionId:E.executionId(base)};
          }

          function event(execution) {
            const identity = {
              eventVersion:'atlas.learning-event.v1',
              kind:'activity-attempt',
              executionId:execution.executionId,
            };
            return {
              ...identity,
              eventId:E.eventId(identity),
              objectiveRef,
              occurredAt:execution.scoredAt,
            };
          }

          const initial = execution(
            'attempt-validation','correct','2026-08-01T10:00:00.000Z',1,'validation-a',
          );
          const failedMaintenance = execution(
            'maintain-recent-validation','incorrect','2026-08-02T10:00:00.000Z',2,'validation-b',
          );
          const recoveryPractice = execution(
            'continue-practice','correct','2026-08-02T10:01:00.000Z',3,'practice-a',
          );

          const first = P.projectObjectiveEvidence(
            [event(initial), event(failedMaintenance)],
            [initial, failedMaintenance],
            execution => execution.executionId === initial.executionId,
          )[0];
          assert.equal(first.state, 'review-needed');
          assert.equal(first.lastValidationAt, initial.scoredAt);
          assert.equal(first.latestValidationCorrect, false);

          const recovered = P.projectObjectiveEvidence(
            [event(initial), event(failedMaintenance), event(recoveryPractice)],
            [initial, failedMaintenance, recoveryPractice],
            execution => execution.executionId === initial.executionId,
          )[0];
          assert.equal(recovered.state, 'ready-for-validation');
          assert.equal(recovered.lastValidationAt, initial.scoredAt);
          assert.equal(recovered.latestValidationCorrect, false);
          assert.equal(recovered.latestPracticeCorrect, true);

          const historyBeforeFreshValidation = M.status({
            now:'2026-08-03T10:01:00.000Z',
            executions:[initial, failedMaintenance, recoveryPractice],
            objectiveRef,
            admissibleExecutionIds:new Set([initial.executionId, failedMaintenance.executionId]),
            evidenceModule:E,
          });
          assert.equal(historyBeforeFreshValidation.hasIndependentValidation, true);
          assert.equal(historyBeforeFreshValidation.basisExecution.executionId, initial.executionId);

          const freshValidation = execution(
            'attempt-validation','correct','2026-08-03T10:02:00.000Z',4,'validation-c',
          );
          const fresh = P.projectObjectiveEvidence(
            [event(initial), event(failedMaintenance), event(recoveryPractice), event(freshValidation)],
            [initial, failedMaintenance, recoveryPractice, freshValidation],
            execution => [initial.executionId, freshValidation.executionId].includes(execution.executionId),
          )[0];
          assert.equal(fresh.state, 'validated-recently');
          assert.equal(fresh.lastValidationAt, freshValidation.scoredAt);

          const restarted = M.status({
            now:'2026-08-03T10:02:00.000Z',
            executions:[initial, failedMaintenance, recoveryPractice, freshValidation],
            objectiveRef,
            admissibleExecutionIds:new Set([
              initial.executionId,
              failedMaintenance.executionId,
              freshValidation.executionId,
            ]),
            evidenceModule:E,
          });
          assert.equal(restarted.reconfirmationCount, 0);
          assert.equal(restarted.intervalDays, 1);
          assert.equal(restarted.basisExecution.executionId, freshValidation.executionId);
          console.log('ATLAS_M2_FAILED_VALIDATION_RECOVERY_PASS');
        ''')
        self.assertIn("ATLAS_M2_FAILED_VALIDATION_RECOVERY_PASS", output)

    def test_visible_surface_routes_review_by_actual_practice_error(self):
        surface = (ROOT / "src/integration/atlas/surface.js").read_text(encoding="utf-8")
        self.assertIn("function correctionTarget", surface)
        self.assertIn("hasCorrectablePracticeError", surface)
        self.assertIn("ATLAS_SESSION_START_WIRED", surface)
        self.assertIn("ATLAS_M2_MEMORY_PROOF_LOOP_WIRED", surface)


if __name__ == "__main__":
    unittest.main(verbosity=2)
