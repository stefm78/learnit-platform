#!/usr/bin/env python3
import pathlib, subprocess, tempfile, textwrap, unittest
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
      assert.deepStrictEqual(E.eligibleActivities(index,objectiveRef,'start-practice').map(x=>x.activityRef.activityLineageId),['z-practice']);
      assert.throws(()=>E.executionClassOf({...rows[0],assessmentRole:'validation'}),/INVALID_ACTIVITY_CLASSIFICATION/);
      const evidence={objectiveRef,state:'review-needed'};
      const rec=R.buildRecommendation({objectiveRef,evidence,index,context:{correctsEventId:'atlas-event-sha256:'+'1'.repeat(64)}});
      assert.equal(rec.preferredActivityRef.activityLineageId,'a-correction'); assert.equal(rec.estimatedMinutes,3);
      const common={engineVersion:'v1',courseRef,contentRevisionRef:{packageLineageId:'pkg',packageRevisionId:'rev',packageDigest:'sha256:'+'2'.repeat(64)},durationMinutes:5,recommendations:[rec]};
      const p1=P.buildPlan(common),p2=P.buildPlan({recommendations:[rec],durationMinutes:5,contentRevisionRef:common.contentRevisionRef,courseRef,engineVersion:'v1'});
      assert.equal(p1.planDigest,p2.planDigest);assert.equal(p1.planId.slice('atlas-plan-'.length),p1.planDigest);
      assert.equal(p1.payload.totalEstimatedMinutes,3);assert.equal(p1.payload.unusedMinutes,2);
      const six={...rec,estimatedMinutes:6};assert.throws(()=>P.buildPlan({...common,recommendations:[six]}),/SESSION_TIME_LIMIT/);
      const validationRec={recommendationVersion:'atlas.recommendation.v1',objectiveRef,action:'attempt-validation',eligibleActivityRefs:[ar('m-validation')],preferredActivityRef:ar('m-validation'),estimatedMinutes:5,reasonCodes:['VALIDATION_AVAILABLE'],validationBasisEventId:'atlas-event-sha256:'+'3'.repeat(64),independenceClaimId:'atlas-claim-sha256:'+'4'.repeat(64)};
      assert.equal(P.buildPlan({...common,recommendations:[validationRec]}).payload.items[0].executionClass,'validation');
      const claim={claimId:validationRec.independenceClaimId,objectiveRef,sourceActivityRef:ar('z-practice'),targetActivityRef:ar('m-validation'),basisCode:'new-instance',sourceStimulusDigest:'sha256:'+'5'.repeat(64),targetStimulusDigest:'sha256:'+'6'.repeat(64)};
      const set={schemaVersion:'atlas.accepted-validation-claims.v1',contentRevisionRef:common.contentRevisionRef,artifactDigest:'sha256:'+'7'.repeat(64),acceptedClaimIds:[claim.claimId]};
      const maint=E.maintenanceEligibility({now:'2026-07-31T10:00:00.000Z',evidence:{objectiveRef,state:'validated-recently'},basisExecution:{outcome:'correct',assistance:'none',scoredAt:'2026-07-30T09:00:00.000Z',eventId:validationRec.validationBasisEventId,activityRef:ar('z-practice')},targetActivity:rows[2],claim,acceptedClaimSet:set,contentRevisionRef:common.contentRevisionRef,artifactDigest:set.artifactDigest});
      assert.equal(maint.eligible,true);
      const facts=[{eventId:'e1',kind:'activity-corrected',occurredAt:'2026-01-01T00:00:00.000Z',outcome:'correct',objectiveRef},{eventId:'e2',kind:'session-resumed',occurredAt:'2026-01-01T00:00:01.000Z'}];
      assert.deepStrictEqual(E.projectRewards(facts).map(x=>x.kind),['correction-completed','resumed-after-interruption']);
      const o2={courseRef,objectiveId:'obj2'}, ranked=R.rankRecommendations([{objectiveRef:o2,evidence:{state:'training'}},{objectiveRef,evidence:{state:'review-needed'}}],[]);assert.equal(ranked[0].objectiveRef.objectiveId,'obj');
      console.log('ATLAS_LEARNING_NODE_PASS 15/15');
    ''')
    cp=subprocess.run(['node','-e',script,str(ROOT)],capture_output=True,text=True)
    self.assertEqual(cp.returncode,0,cp.stderr); self.assertIn('15/15',cp.stdout)
  def test_no_network_llm_or_ambient_randomness(self):
    text='\n'.join(p.read_text() for p in (ROOT/'src/core').glob('atlas_*.js'))
    for forbidden in ('fetch(','XMLHttpRequest','WebSocket','Math.random','Date.now','openai','anthropic'):
      self.assertNotIn(forbidden,text)
if __name__=='__main__': unittest.main(verbosity=2)
