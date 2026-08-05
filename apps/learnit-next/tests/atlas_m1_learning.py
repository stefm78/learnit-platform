#!/usr/bin/env python3
import os, pathlib, subprocess, textwrap, unittest
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

  def test_v3_permutation_boundary_and_root_closure(self):
    script=textwrap.dedent(r'''
      const assert=require('assert');
      const E=require(process.argv[1]+'/src/core/atlas_evidence.js');
      const R=require(process.argv[1]+'/src/core/atlas_recommendation.js');
      const P=require(process.argv[1]+'/src/core/atlas_planner.js');
      let checks=0;
      const check=fn=>{fn();checks+=1;};
      const rejects=(fn,rx)=>{assert.throws(fn,rx);checks+=1;};
      const courseRef={packageLineageId:'pkg',courseLineageId:'course'};
      const objectiveA={courseRef,objectiveId:'obj-a'};
      const objectiveB={courseRef,objectiveId:'obj-b'};
      const activity=(objectiveRef,id)=>({activityRef:{courseRef,activityLineageId:id},objectiveRef,learningPhase:'consolidation',assessmentRole:'practice',estimatedMinutes:3});
      const activities=[activity(objectiveA,'correction-a'),activity(objectiveB,'correction-b')];
      const links=activities.map(row=>({objectiveRef:row.objectiveRef,activityRef:row.activityRef,authorIndex:0}));
      const index=E.indexActivities(activities,links);
      const recommendationRows=[
        {objectiveRef:objectiveA,evidence:{objectiveRef:objectiveA,state:'review-needed'}},
        {objectiveRef:objectiveB,evidence:{objectiveRef:objectiveB,state:'review-needed'}}
      ];
      const event=(ordinal,objectiveRef)=>({
        kind:'session-started',
        eventId:'atlas-event-sha256:'+ordinal.toString(16).padStart(64,'0'),
        occurredAt:'2026-07-31T12:00:00.000Z',
        selectedItems:[{objectiveRef}]
      });
      const journal=[event(0,objectiveA),...Array.from({length:10},(_,index)=>event(index+1,objectiveB))];
      const contentRevisionRef={packageLineageId:'pkg',packageRevisionId:'rev',packageDigest:'sha256:'+'2'.repeat(64)};
      const provenanceFor=objectiveRef=>({correctsEventId:'atlas-event-sha256:'+(objectiveRef.objectiveId==='obj-a'?'a':'b').repeat(64)});
      const snapshot=events=>{
        const ranked=R.rankRecommendations(recommendationRows,events);
        const recommendations=ranked.map(row=>R.buildRecommendation({objectiveRef:row.objectiveRef,evidence:row.evidence,index}));
        const itemProvenance=ranked.map(row=>provenanceFor(row.objectiveRef));
        const plan=P.buildPlan({engineVersion:'v1',courseRef,contentRevisionRef,durationMinutes:5,recommendations,itemProvenance});
        return {
          statsA:R.lastSelectionStats(objectiveA,events),
          statsB:R.lastSelectionStats(objectiveB,events),
          ranked:ranked.map(row=>row.objectiveRef.objectiveId),
          recommendations:P.canonicalJson(recommendations),
          plan:P.canonicalJson(plan)
        };
      };
      const expected=snapshot(journal);
      check(()=>assert.equal(expected.statsA.recentCount,0));
      check(()=>assert.equal(expected.statsB.recentCount,10));
      check(()=>assert.deepStrictEqual(expected.ranked,['obj-a','obj-b']));
      const permutations=[journal,[...journal].reverse()];
      for(let offset=0;offset<journal.length;offset++)permutations.push(journal.slice(offset).concat(journal.slice(0,offset)));
      for(let left=0;left<journal.length;left++)for(let right=left+1;right<journal.length;right++){
        const swapped=[...journal];[swapped[left],swapped[right]]=[swapped[right],swapped[left]];permutations.push(swapped);
      }
      for(const permutation of permutations)check(()=>assert.deepStrictEqual(snapshot(permutation),expected));

      const ranked=R.rankRecommendations(recommendationRows,journal);
      const recommendations=ranked.map(row=>R.buildRecommendation({objectiveRef:row.objectiveRef,evidence:row.evidence,index}));
      const itemProvenance=ranked.map(row=>provenanceFor(row.objectiveRef));
      const valid={engineVersion:'v1',courseRef,contentRevisionRef,durationMinutes:5,recommendations,itemProvenance};
      check(()=>assert.match(P.buildPlan(valid).planId,/^atlas-plan-sha256:[0-9a-f]{64}$/));
      rejects(()=>P.buildPlan({...valid,engineVersion:''}),/INVALID_ENGINE_VERSION/);
      rejects(()=>P.buildPlan({...valid,courseRef:{}}),/INVALID_COURSE_REF/);
      rejects(()=>P.buildPlan({...valid,contentRevisionRef:{}}),/INVALID_CONTENT_REVISION_REF/);
      rejects(()=>P.buildPlan({...valid,unexpected:true}),/UNKNOWN_FIELD/);
      rejects(()=>P.buildPlan({...valid,courseRef:{...courseRef,unexpected:true}}),/UNKNOWN_FIELD/);
      rejects(()=>P.buildPlan({...valid,contentRevisionRef:{...contentRevisionRef,unexpected:true}}),/UNKNOWN_FIELD/);
      rejects(()=>P.buildPlan({...valid,contentRevisionRef:{...contentRevisionRef,packageDigest:'SHA256:'+'2'.repeat(64)}}),/INVALID_CONTENT_REVISION_REF/);
      rejects(()=>P.buildPlan({...valid,contentRevisionRef:{...contentRevisionRef,packageDigest:'sha256:'+'A'.repeat(64)}}),/INVALID_CONTENT_REVISION_REF/);
      console.log(`ATLAS_LEARNING_V3_NODE_PASS ${checks}/${checks}`);
    ''')
    cp=subprocess.run(['node','-e',script,str(ROOT)],capture_output=True,text=True)
    self.assertEqual(cp.returncode,0,cp.stderr)
    self.assertRegex(cp.stdout,r'ATLAS_LEARNING_V3_NODE_PASS \d+/\d+')

  def test_v4_unicode_code_point_tiebreak(self):
    script=textwrap.dedent(r'''
      const assert=require('assert');
      const E=require(process.argv[1]+'/src/core/atlas_evidence.js');
      const R=require(process.argv[1]+'/src/core/atlas_recommendation.js');
      const P=require(process.argv[1]+'/src/core/atlas_planner.js');
      let checks=0;
      const check=fn=>{fn();checks+=1;};
      const rejects=(fn,rx)=>{assert.throws(fn,rx);checks+=1;};
      const courseRef={packageLineageId:'pkg',courseLineageId:'course'};
      const contentRevisionRef={packageLineageId:'pkg',packageRevisionId:'rev',packageDigest:'sha256:'+'2'.repeat(64)};
      const objective=id=>E.canonicalize({courseRef,objectiveId:id});
      const row=objectiveRef=>({objectiveRef,evidence:{objectiveRef,state:'review-needed'}});
      const sessionEvent=(digit,objectiveRef)=>({
        kind:'session-started',
        eventId:'atlas-event-sha256:'+digit.repeat(64),
        occurredAt:'2026-08-04T06:00:00.000Z',
        selectedItems:[{objectiveRef}]
      });
      const pairSnapshot=(leftId,rightId)=>{
        const left=objective(leftId),right=objective(rightId);
        const activities=[left,right].map((objectiveRef,index)=>({
          activityRef:{courseRef,activityLineageId:`correction-${index}`},
          objectiveRef,
          learningPhase:'consolidation',
          assessmentRole:'practice',
          estimatedMinutes:3
        }));
        const links=activities.map(activity=>({objectiveRef:activity.objectiveRef,activityRef:activity.activityRef,authorIndex:0}));
        const index=E.indexActivities(activities,links);
        const rows=[row(left),row(right)];
        const journal=[sessionEvent('1',left),sessionEvent('2',right)];
        const snapshot=(inputRows,events)=>{
          const ranked=R.rankRecommendations(inputRows,events);
          const recommendations=ranked.map(item=>R.buildRecommendation({objectiveRef:item.objectiveRef,evidence:item.evidence,index}));
          const itemProvenance=ranked.map((_,position)=>({correctsEventId:'atlas-event-sha256:'+(position===0?'a':'b').repeat(64)}));
          const plan=P.buildPlan({engineVersion:'v1',courseRef,contentRevisionRef,durationMinutes:5,recommendations,itemProvenance});
          const lastSelectionStats=[left,right].map(ref=>R.lastSelectionStats(ref,events));
          const ranking=ranked.map(item=>item.objectiveRef.objectiveId);
          const reasonCodes=recommendations.map(item=>item.reasonCodes);
          const selectedActivities=plan.payload.items.map(item=>item.activityRef.activityLineageId);
          return {
            lastSelectionStats,
            ranking,
            recommendations:P.canonicalJson(recommendations),
            reasonCodes,
            selectedActivities,
            sessionPlan:P.canonicalJson(plan),
            planId:plan.planId,
            canonicalSerialization:P.canonicalJson({lastSelectionStats,ranking,recommendations,reasonCodes,selectedActivities,sessionPlan:plan,planId:plan.planId})
          };
        };
        const expected=snapshot(rows,journal);
        for(const inputRows of [rows,[...rows].reverse()]){
          for(const events of [journal,[...journal].reverse()])check(()=>assert.deepStrictEqual(snapshot(inputRows,events),expected));
        }
        return expected;
      };

      const zKey=E.canonicalRefKey(objective('z'));
      const diaeresisKey=E.canonicalRefKey(objective('ä'));
      if(process.env.ATLAS_CHECK_LEGACY==='1'){
        check(()=>assert.notDeepStrictEqual([zKey,diaeresisKey].sort((a,b)=>a.localeCompare(b)),[zKey,diaeresisKey]));
      }

      const originalLocaleCompare=String.prototype.localeCompare;
      String.prototype.localeCompare=function(){throw new Error('localeCompare forbidden');};
      let result;
      try{
        const zDiaeresis=pairSnapshot('z','ä');
        check(()=>assert.deepStrictEqual(zDiaeresis.ranking,['z','ä']));
        const caseOrder=pairSnapshot('a','A');
        check(()=>assert.deepStrictEqual(caseOrder.ranking,['A','a']));
        const supplementary=pairSnapshot('\uE000','\u{10000}');
        check(()=>assert.deepStrictEqual(supplementary.ranking,['\uE000','\u{10000}']));
        const prefix=pairSnapshot('prefix','prefix-more');
        check(()=>assert.deepStrictEqual(prefix.ranking,['prefix','prefix-more']));
        const ascii=pairSnapshot('obj-a','obj-b');
        check(()=>assert.deepStrictEqual(ascii.ranking,['obj-a','obj-b']));

        const composed=objective('é'),decomposed=objective('e\u0301');
        check(()=>assert.equal(E.canonicalRefKey(composed),E.canonicalRefKey(decomposed)));
        check(()=>assert.equal(P.canonicalJson(composed),P.canonicalJson(decomposed)));

        const rawComposed={courseRef,objectiveId:'é'};
        const rawDecomposed={courseRef,objectiveId:'e\u0301'};
        rejects(()=>R.rankRecommendations([row(rawComposed),row(rawDecomposed)]),/NON_CANONICAL_STRING/);
        rejects(()=>R.rankRecommendations([row(objective('ok')),row({courseRef,objectiveId:''})]),/INVALID_OBJECTIVE_REF/);
        rejects(()=>R.rankRecommendations([row(objective('ok')),row({courseRef,objectiveId:'bad',unexpected:true})]),/UNKNOWN_FIELD/);
        rejects(()=>R.rankRecommendations([row(objective('ok')),row({courseRef,objectiveId:'bad',activityLineageId:'also-bad'})]),/UNQUALIFIED_REFERENCE/);

        result={zDiaeresis,caseOrder,supplementary,prefix,ascii,nfcKey:E.canonicalRefKey(composed)};
      }finally{
        String.prototype.localeCompare=originalLocaleCompare;
      }
      console.log('ATLAS_LEARNING_V4_NODE_PASS '+P.canonicalJson(result));
    ''')
    outputs=[]
    for index, locale in enumerate(('C','C.UTF-8','en_US.UTF-8','de_DE.UTF-8')):
      env=os.environ.copy()
      env.update({'LANG':locale,'LC_ALL':locale,'ATLAS_CHECK_LEGACY':'1' if index==0 else '0'})
      cp=subprocess.run(['node','-e',script,str(ROOT)],capture_output=True,text=True,env=env)
      self.assertEqual(cp.returncode,0,f'{locale}: {cp.stderr}')
      self.assertRegex(cp.stdout,r'^ATLAS_LEARNING_V4_NODE_PASS ')
      outputs.append(cp.stdout.strip())
    self.assertTrue(all(output==outputs[0] for output in outputs),outputs)

  def test_v4_static_and_syntax_controls(self):
    path=ROOT/'src/core/atlas_recommendation.js'
    text=path.read_text()
    self.assertNotIn('localeCompare',text)
    self.assertNotIn('Intl.Collator',text)
    cp=subprocess.run(['node','--check',str(path)],capture_output=True,text=True)
    self.assertEqual(cp.returncode,0,cp.stderr)

  def test_no_network_llm_or_ambient_randomness(self):
    text='\n'.join(p.read_text() for p in (ROOT/'src/core').glob('atlas_*.js'))
    for forbidden in ('fetch(','XMLHttpRequest','WebSocket','Math.random','Date.now','openai','anthropic'):
      self.assertNotIn(forbidden,text)
if __name__=='__main__': unittest.main(verbosity=2)
