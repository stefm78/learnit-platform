#!/usr/bin/env python3
import pathlib, subprocess, textwrap, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class AtlasLearningTests(unittest.TestCase):
  def test_node_contract_matrix(self):
    script=textwrap.dedent(r'''
      const assert=require('assert');
      const E=require(process.argv[1]+'/src/core/atlas_evidence.js');
      const R=require(process.argv[1]+'/src/core/atlas_recommendation.js');
      const P=require(process.argv[1]+'/src/core/atlas_planner.js');
      const courseRef={packageLineageId:'pkg',courseLineageId:'course'};
      const objectiveRef={courseRef,objectiveId:'obj'};
      const ar=id=>({courseRef,activityLineageId:id});
      const rows=[
        {activityRef:ar('z-practice'),objectiveRef,learningPhase:'application',assessmentRole:'practice',estimatedMinutes:4},
        {activityRef:ar('a-correction'),objectiveRef,learningPhase:'consolidation',assessmentRole:'practice',estimatedMinutes:3},
        {activityRef:ar('m-validation'),objectiveRef,learningPhase:'validation',assessmentRole:'validation',estimatedMinutes:5},
        {activityRef:ar('b-transfer'),objectiveRef,learningPhase:'transfer',assessmentRole:'practice',estimatedMinutes:2}
      ];
      const links=rows.map((x,i)=>({objectiveRef,activityRef:x.activityRef,authorIndex:i}));
      const index=E.indexActivities(rows,links);
      assert.deepStrictEqual(E.eligibleActivities(index,objectiveRef,'correct-practice').map(x=>x.activityRef.activityLineageId),['a-correction']);
      const rec=R.buildRecommendation({objectiveRef,evidence:{objectiveRef,state:'review-needed'},index});
      assert.deepStrictEqual(Object.keys(rec).sort(),['action','eligibleActivityRefs','estimatedMinutes','objectiveRef','preferredActivityRef','reasonCodes','recommendationVersion'].sort());
      const correctionProvenance={correctsEventId:'atlas-event-sha256:'+'1'.repeat(64)};
      const common={engineVersion:'v1',courseRef,contentRevisionRef:{packageLineageId:'pkg',packageRevisionId:'rev',packageDigest:'sha256:'+'2'.repeat(64)},durationMinutes:5,recommendations:[rec],itemProvenance:[correctionProvenance]};
      const p1=P.buildPlan(common),p2=P.buildPlan({...common});
      assert.equal(p1.planDigest,p2.planDigest);assert.equal(p1.payload.items[0].correctsEventId,correctionProvenance.correctsEventId);
      assert.throws(()=>P.canonicalize({a:undefined}),/NON_CANONICAL_VALUE/);
      assert.equal(P.canonicalJson({s:'e\u0301'}),P.canonicalJson({s:'é'}));
      const validationRec={recommendationVersion:'atlas.recommendation.v1',objectiveRef,action:'attempt-validation',eligibleActivityRefs:[ar('m-validation')],preferredActivityRef:ar('m-validation'),estimatedMinutes:5,reasonCodes:['VALIDATION_AVAILABLE']};
      const validationProvenance={validationBasisEventId:'atlas-event-sha256:'+'3'.repeat(64),independenceClaimId:'atlas-claim-sha256:'+'4'.repeat(64)};
      assert.equal(P.buildPlan({...common,recommendations:[validationRec],itemProvenance:[validationProvenance]}).payload.items[0].executionClass,'validation');
      const claimBase={claimVersion:'atlas.independence.v1',objectiveRef,sourceActivityRef:ar('z-practice'),targetActivityRef:ar('m-validation'),basisCode:'new-instance',sourceStimulusDigest:'sha256:'+'5'.repeat(64),targetStimulusDigest:'sha256:'+'6'.repeat(64)};
      const claim={...claimBase,claimId:'atlas-claim-sha256:'+E.atlasHash('learnit.atlas.m1.v0.3/validation-claim-id',claimBase)};
      const set={schemaVersion:'atlas.accepted-validation-claims.v1',contentRevisionRef:common.contentRevisionRef,oracleVersion:'atlas.qa.oracle.v1',artifactDigest:'sha256:'+'7'.repeat(64),acceptedClaimIds:[claim.claimId]};
      assert.equal(E.claimIsAccepted({claim,acceptedClaimSet:set,contentRevisionRef:common.contentRevisionRef,artifactDigest:set.artifactDigest,oracleVersion:set.oracleVersion,sourceActivityRef:claim.sourceActivityRef,targetActivityRef:claim.targetActivityRef,objectiveRef}),true);
      assert.equal(E.claimIsAccepted({claim:{...claim,claimVersion:undefined},acceptedClaimSet:set,contentRevisionRef:common.contentRevisionRef,artifactDigest:set.artifactDigest,oracleVersion:set.oracleVersion,sourceActivityRef:claim.sourceActivityRef,targetActivityRef:claim.targetActivityRef,objectiveRef}),false);
      assert.equal(E.claimIsAccepted({claim,acceptedClaimSet:{...set,oracleVersion:undefined},contentRevisionRef:common.contentRevisionRef,artifactDigest:set.artifactDigest,oracleVersion:set.oracleVersion,sourceActivityRef:claim.sourceActivityRef,targetActivityRef:claim.targetActivityRef,objectiveRef}),false);
      const maint=E.maintenanceEligibility({now:'2026-07-31T10:00:00.000Z',evidence:{objectiveRef,state:'validated-recently'},basisExecution:{outcome:'correct',assistance:'none',scoredAt:'2026-07-30T09:00:00.000Z',eventId:validationProvenance.validationBasisEventId,activityRef:ar('z-practice')},targetActivity:rows[2],claim,acceptedClaimSet:set,contentRevisionRef:common.contentRevisionRef,artifactDigest:set.artifactDigest,oracleVersion:set.oracleVersion});
      assert.equal(maint.eligible,true);
      const executionBase=(id,overrides={})=>({executionVersion:'atlas.scored-execution.v1',executionId:'atlas-execution-sha256:'+id.repeat(64),sessionRef:{sessionId:'atlas-session-sha256:'+'a'.repeat(64),planId:p1.planId},courseRef,contentRevisionRef:common.contentRevisionRef,planDigest:p1.planDigest,itemPosition:0,submissionOrdinal:1,objectiveRef,activityRef:ar('z-practice'),action:'start-practice',executionClass:'practice',responseDigest:'sha256:'+'b'.repeat(64),scoringRuleId:'qcm.v1',scoringRuleDigest:'sha256:'+'c'.repeat(64),outcome:'correct',assistance:'none',assistanceUseIds:[],submittedAt:'2026-01-01T00:00:00.000Z',scoredAt:'2026-01-01T00:00:00.000Z',...overrides});
      const e1=executionBase('d');
      const event1={eventVersion:'atlas.learning-event.v1',eventId:'atlas-event-sha256:'+'e'.repeat(64),kind:'activity-attempt',objectiveRef,executionId:e1.executionId,occurredAt:'2026-01-01T00:00:00.000Z'};
      const rewards=E.projectRewards({learningEvents:[event1],scoredExecutions:[e1]});
      assert.equal(rewards[0].kind,'independent-success');assert.match(rewards[0].rewardId,/^atlas-reward-sha256:[0-9a-f]{64}$/);
      assert.throws(()=>E.projectRewards({learningEvents:[event1],scoredExecutions:[{...e1,validation:true}]}),/UNKNOWN_FIELD/);
      console.log('ATLAS_LEARNING_NODE_PASS 24/24');
    ''')
    cp=subprocess.run(['node','-e',script,str(ROOT)],capture_output=True,text=True)
    self.assertEqual(cp.returncode,0,cp.stderr); self.assertIn('24/24',cp.stdout)
  def test_no_network_llm_or_ambient_randomness(self):
    text='\n'.join(p.read_text() for p in (ROOT/'src/core').glob('atlas_*.js'))
    for forbidden in ('fetch(','XMLHttpRequest','WebSocket','Math.random','Date.now','openai','anthropic'):
      self.assertNotIn(forbidden,text)
if __name__=='__main__': unittest.main(verbosity=2)
