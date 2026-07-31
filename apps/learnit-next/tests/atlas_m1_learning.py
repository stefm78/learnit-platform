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
      let checks=0;
      const check=fn=>{fn();checks+=1;};
      const rejects=(fn,rx)=>{assert.throws(fn,rx);checks+=1;};
      const courseRef={packageLineageId:'pkg',courseLineageId:'course'};
      const otherCourseRef={packageLineageId:'pkg',courseLineageId:'other-course'};
      const objectiveRef={courseRef,objectiveId:'obj'};
      const otherObjectiveRef={courseRef:otherCourseRef,objectiveId:'obj'};
      const ar=id=>({courseRef,activityLineageId:id});
      const rows=[
        {activityRef:ar('z-practice'),objectiveRef,learningPhase:'application',assessmentRole:'practice',estimatedMinutes:4},
        {activityRef:ar('a-correction'),objectiveRef,learningPhase:'consolidation',assessmentRole:'practice',estimatedMinutes:3},
        {activityRef:ar('m-validation'),objectiveRef,learningPhase:'validation',assessmentRole:'validation',estimatedMinutes:5},
        {activityRef:ar('n-validation'),objectiveRef,learningPhase:'validation',assessmentRole:'validation',estimatedMinutes:5},
        {activityRef:ar('b-transfer'),objectiveRef,learningPhase:'transfer',assessmentRole:'practice',estimatedMinutes:2}
      ];
      const links=rows.map((x,i)=>({objectiveRef,activityRef:x.activityRef,authorIndex:i}));
      const index=E.indexActivities(rows,links);
      check(()=>assert.deepStrictEqual(E.eligibleActivities(index,objectiveRef,'correct-practice').map(x=>x.activityRef.activityLineageId),['a-correction']));
      check(()=>assert.deepStrictEqual(E.eligibleActivities(index,objectiveRef,'attempt-validation').map(x=>x.activityRef.activityLineageId),['m-validation','n-validation']));
      rejects(()=>E.eligibleActivities(index,objectiveRef,'invented-action'),/UNKNOWN_ACTION/);
      const rec=R.buildRecommendation({objectiveRef,evidence:{objectiveRef,state:'review-needed'},index});
      check(()=>assert.deepStrictEqual(Object.keys(rec).sort(),['action','eligibleActivityRefs','estimatedMinutes','objectiveRef','preferredActivityRef','reasonCodes','recommendationVersion'].sort()));
      check(()=>assert.equal(rec.preferredActivityRef.activityLineageId,'a-correction'));
      const correctionProvenance={correctsEventId:'atlas-event-sha256:'+'1'.repeat(64)};
      const contentRevisionRef={packageLineageId:'pkg',packageRevisionId:'rev',packageDigest:'sha256:'+'2'.repeat(64)};
      const common={engineVersion:'v1',courseRef,contentRevisionRef,durationMinutes:5,recommendations:[rec],itemProvenance:[correctionProvenance]};
      const p1=P.buildPlan(common),p2=P.buildPlan({...common});
      check(()=>assert.equal(p1.planDigest,p2.planDigest));
      check(()=>assert.equal(p1.payload.items[0].correctsEventId,correctionProvenance.correctsEventId));
      check(()=>assert.equal(p1.payload.items[0].executionClass,'correction'));

      // LEARNING-V2-04: canonical key collisions fail and ordering occurs after NFC normalization.
      rejects(()=>P.canonicalize({a:undefined}),/NON_CANONICAL_VALUE/);
      check(()=>assert.equal(P.canonicalJson({s:'e\u0301'}),P.canonicalJson({s:'é'})));
      rejects(()=>P.canonicalJson({'é':1,'e\u0301':2}),/CANONICAL_KEY_COLLISION/);
      check(()=>assert.equal(P.canonicalJson({'e\u0301':1,f:2}),'{"f":2,"é":1}'));

      // LEARNING-V2-05: every eligible activity is qualified, same-course and unique.
      const validationRec={recommendationVersion:'atlas.recommendation.v1',objectiveRef,action:'attempt-validation',eligibleActivityRefs:[ar('m-validation'),ar('n-validation')],preferredActivityRef:ar('m-validation'),estimatedMinutes:5,reasonCodes:['VALIDATION_AVAILABLE']};
      const validationProvenance={validationBasisEventId:'atlas-event-sha256:'+'3'.repeat(64),independenceClaimId:'atlas-claim-sha256:'+'4'.repeat(64)};
      check(()=>assert.equal(P.buildPlan({...common,recommendations:[validationRec],itemProvenance:[validationProvenance]}).payload.items[0].executionClass,'validation'));
      rejects(()=>P.validateRecommendation({...validationRec,eligibleActivityRefs:[ar('m-validation'),ar('m-validation')]}),/DUPLICATE_ELIGIBLE_ACTIVITY_REF/);
      rejects(()=>P.validateRecommendation({...validationRec,eligibleActivityRefs:[ar('m-validation'),{courseRef,objectiveId:'not-an-activity'}]}),/INVALID_ACTIVITY_REF/);
      rejects(()=>P.validateRecommendation({...validationRec,eligibleActivityRefs:[ar('m-validation'),{courseRef,activityLineageId:''}]}),/INVALID_ACTIVITY_REF/);
      rejects(()=>P.validateRecommendation({...validationRec,eligibleActivityRefs:[{courseRef:otherCourseRef,activityLineageId:'foreign'}],preferredActivityRef:{courseRef:otherCourseRef,activityLineageId:'foreign'}}),/PREFERRED_ACTIVITY_COURSE_MISMATCH/);
      rejects(()=>P.validateRecommendation({...validationRec,preferredActivityRef:ar('absent')}),/PREFERRED_ACTIVITY_NOT_ELIGIBLE/);
      rejects(()=>P.validateRecommendation({...validationRec,action:'invented-action'}),/UNKNOWN_ACTION/);
      rejects(()=>P.validateRecommendation({...validationRec,objectiveRef:ar('not-objective')}),/INVALID_OBJECTIVE_REF/);

      const claimBase={claimVersion:'atlas.independence.v1',objectiveRef,sourceActivityRef:ar('m-validation'),targetActivityRef:ar('n-validation'),basisCode:'new-instance',sourceStimulusDigest:'sha256:'+'5'.repeat(64),targetStimulusDigest:'sha256:'+'6'.repeat(64)};
      const claim={...claimBase,claimId:'atlas-claim-sha256:'+E.atlasHash('learnit.atlas.m1.v0.3/validation-claim-id',claimBase)};
      const set={schemaVersion:'atlas.accepted-validation-claims.v1',contentRevisionRef,oracleVersion:'atlas.qa.oracle.v1',artifactDigest:'sha256:'+'7'.repeat(64),acceptedClaimIds:[claim.claimId]};
      check(()=>assert.equal(E.claimIsAccepted({claim,acceptedClaimSet:set,contentRevisionRef,artifactDigest:set.artifactDigest,oracleVersion:set.oracleVersion,sourceActivityRef:claim.sourceActivityRef,targetActivityRef:claim.targetActivityRef,objectiveRef}),true));
      check(()=>assert.equal(E.claimIsAccepted({claim:{...claim,claimVersion:undefined},acceptedClaimSet:set,contentRevisionRef,artifactDigest:set.artifactDigest,oracleVersion:set.oracleVersion,sourceActivityRef:claim.sourceActivityRef,targetActivityRef:claim.targetActivityRef,objectiveRef}),false));
      check(()=>assert.equal(E.claimIsAccepted({claim,acceptedClaimSet:{...set,oracleVersion:undefined},contentRevisionRef,artifactDigest:set.artifactDigest,oracleVersion:set.oracleVersion,sourceActivityRef:claim.sourceActivityRef,targetActivityRef:claim.targetActivityRef,objectiveRef}),false));

      const executionBase=(id,overrides={})=>({executionVersion:'atlas.scored-execution.v1',executionId:'atlas-execution-sha256:'+id.repeat(64),sessionRef:{sessionId:'atlas-session-sha256:'+'a'.repeat(64),planId:p1.planId},courseRef,contentRevisionRef,planDigest:p1.planDigest,itemPosition:0,submissionOrdinal:1,objectiveRef,activityRef:ar('z-practice'),action:'start-practice',executionClass:'practice',responseDigest:'sha256:'+'b'.repeat(64),scoringRuleId:'qcm.v1',scoringRuleDigest:'sha256:'+'c'.repeat(64),outcome:'correct',assistance:'none',assistanceUseIds:[],submittedAt:'2026-01-01T00:00:00.000Z',scoredAt:'2026-01-01T00:00:00.000Z',...overrides});

      // LEARNING-V2-03: maintenance provenance uses a separate closed pedagogical event.
      const basisExecution=executionBase('8',{activityRef:ar('m-validation'),action:'attempt-validation',executionClass:'validation',submittedAt:'2026-07-30T09:00:00.000Z',scoredAt:'2026-07-30T09:00:00.000Z'});
      const basisEvent={eventVersion:'atlas.learning-event.v1',eventId:'atlas-event-sha256:'+'9'.repeat(64),kind:'activity-attempt',objectiveRef,executionId:basisExecution.executionId,occurredAt:basisExecution.scoredAt};
      const maintenanceArgs={now:'2026-07-31T10:00:00.000Z',evidence:{objectiveRef,state:'validated-recently'},basisExecution,basisEvent,targetActivity:rows[3],claim,acceptedClaimSet:set,contentRevisionRef,artifactDigest:set.artifactDigest,oracleVersion:set.oracleVersion};
      const maint=E.maintenanceEligibility(maintenanceArgs);
      check(()=>assert.equal(maint.eligible,true));
      check(()=>assert.equal(maint.validationBasisEventId,basisEvent.eventId));
      rejects(()=>E.maintenanceEligibility({...maintenanceArgs,basisExecution:{...basisExecution,eventId:basisEvent.eventId}}),/UNKNOWN_FIELD/);
      check(()=>assert.equal(E.maintenanceEligibility({...maintenanceArgs,basisEvent:null}).eligible,false));
      rejects(()=>E.maintenanceEligibility({...maintenanceArgs,basisEvent:{...basisEvent,executionId:'atlas-execution-sha256:'+'f'.repeat(64)}}),/MAINTENANCE_BASIS_EXECUTION_MISMATCH/);
      rejects(()=>E.maintenanceEligibility({...maintenanceArgs,basisEvent:{...basisEvent,objectiveRef:otherObjectiveRef}}),/MAINTENANCE_BASIS_OBJECTIVE_MISMATCH/);
      rejects(()=>E.maintenanceEligibility({...maintenanceArgs,basisEvent:{...basisEvent,occurredAt:'2026-07-30T09:00:01.000Z'}}),/MAINTENANCE_BASIS_TIME_MISMATCH/);
      const correctedBasisEvent={eventVersion:'atlas.learning-event.v1',eventId:basisEvent.eventId,kind:'activity-corrected',objectiveRef,executionId:basisExecution.executionId,correctsEventId:'atlas-event-sha256:'+'1'.repeat(64),occurredAt:basisExecution.scoredAt};
      rejects(()=>E.maintenanceEligibility({...maintenanceArgs,basisEvent:correctedBasisEvent}),/INVALID_MAINTENANCE_BASIS_EVENT/);
      check(()=>assert.equal(E.maintenanceEligibility({...maintenanceArgs,now:'2026-07-30T10:00:00.000Z'}).reason,'RECENTLY_VALIDATED'));
      check(()=>assert.equal(E.maintenanceEligibility({...maintenanceArgs,basisExecution:executionBase('7')}).eligible,false));

      // Positive reward projection and LEARNING-V2-01 action/class fail-closed behavior.
      const e1=executionBase('d');
      const event1={eventVersion:'atlas.learning-event.v1',eventId:'atlas-event-sha256:'+'e'.repeat(64),kind:'activity-attempt',objectiveRef,executionId:e1.executionId,occurredAt:e1.scoredAt};
      const rewards=E.projectRewards({learningEvents:[event1],scoredExecutions:[e1]});
      check(()=>assert.equal(rewards[0].kind,'independent-success'));
      check(()=>assert.match(rewards[0].rewardId,/^atlas-reward-sha256:[0-9a-f]{64}$/));
      rejects(()=>E.projectRewards({learningEvents:[event1],scoredExecutions:[{...e1,executionClass:'validation'}]}),/ACTION_EXECUTION_CLASS_MISMATCH/);
      rejects(()=>E.projectRewards({learningEvents:[event1],scoredExecutions:[{...e1,action:'attempt-validation'}]}),/ACTION_EXECUTION_CLASS_MISMATCH/);
      rejects(()=>E.projectRewards({learningEvents:[event1],scoredExecutions:[{...e1,action:'invented-action'}]}),/UNKNOWN_ACTION/);
      rejects(()=>E.projectRewards({learningEvents:[event1],scoredExecutions:[{...e1,validation:true}]}),/UNKNOWN_FIELD/);
      const validationExecution=executionBase('6',{activityRef:ar('m-validation'),action:'attempt-validation',executionClass:'validation'});
      const validationEvent={...event1,eventId:'atlas-event-sha256:'+'6'.repeat(64),executionId:validationExecution.executionId};
      check(()=>assert.equal(E.projectRewards({learningEvents:[validationEvent],scoredExecutions:[validationExecution]})[0].kind,'validation-completed'));
      const reconfirmExecution=executionBase('5',{activityRef:ar('n-validation'),action:'maintain-recent-validation',executionClass:'validation'});
      const reconfirmEvent={...event1,eventId:'atlas-event-sha256:'+'5'.repeat(64),executionId:reconfirmExecution.executionId};
      check(()=>assert.equal(E.projectRewards({learningEvents:[reconfirmEvent],scoredExecutions:[reconfirmExecution]})[0].kind,'validation-reconfirmed'));

      // LEARNING-V2-02: duplicate and conflicting event identities are both rejected.
      rejects(()=>E.projectRewards({learningEvents:[event1,event1],scoredExecutions:[e1]}),/DUPLICATE_EVENT_ID/);
      const conflict={...event1,executionId:'atlas-execution-sha256:'+'f'.repeat(64)};
      rejects(()=>E.projectRewards({learningEvents:[event1,conflict],scoredExecutions:[e1]}),/DUPLICATE_EVENT_ID/);
      rejects(()=>E.projectRewards({learningEvents:[event1],scoredExecutions:[e1,e1]}),/DUPLICATE_EXECUTION_ID/);

      console.log(`ATLAS_LEARNING_NODE_PASS ${checks}/${checks}`);
    ''')
    cp=subprocess.run(['node','-e',script,str(ROOT)],capture_output=True,text=True)
    self.assertEqual(cp.returncode,0,cp.stderr)
    self.assertRegex(cp.stdout,r'ATLAS_LEARNING_NODE_PASS \d+/\d+')
  def test_no_network_llm_or_ambient_randomness(self):
    text='\n'.join(p.read_text() for p in (ROOT/'src/core').glob('atlas_*.js'))
    for forbidden in ('fetch(','XMLHttpRequest','WebSocket','Math.random','Date.now','openai','anthropic'):
      self.assertNotIn(forbidden,text)
if __name__=='__main__': unittest.main(verbosity=2)
