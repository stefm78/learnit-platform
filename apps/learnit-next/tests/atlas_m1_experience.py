#!/usr/bin/env python3
import pathlib,subprocess,textwrap,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Experience(unittest.TestCase):
 def test_node_matrix(self):
  js=textwrap.dedent(r'''
   const assert=require('assert');const T=require(process.argv[1]+'/src/ui/atlas_today.js'),S=require(process.argv[1]+'/src/ui/atlas_session.js'),U=require(process.argv[1]+'/src/ui/atlas_summary.js'),R=require(process.argv[1]+'/src/ui/atlas_rewards.js');
   const courseRef={packageLineageId:'p',courseLineageId:'c'},objectiveRef={courseRef,objectiveId:'o'},activityRef={courseRef,activityLineageId:'a'};
   const rec={recommendationVersion:'atlas.recommendation.v1',objectiveRef,action:'correct-practice',eligibleActivityRefs:[activityRef],preferredActivityRef:activityRef,estimatedMinutes:3,reasonCodes:['REVIEW_REQUIRED']};
   const item={position:0,objectiveRef,activityRef,action:'correct-practice',executionClass:'correction',estimatedMinutes:3,correctsEventId:'atlas-event-sha256:'+'1'.repeat(64)};
   const plan={planId:'atlas-plan-sha256:'+'2'.repeat(64),planDigest:'sha256:'+'2'.repeat(64),payload:{schemaVersion:'atlas.session-plan.v1',engineVersion:'v',courseRef,contentRevisionRef:{packageLineageId:'p',packageRevisionId:'r',packageDigest:'sha256:'+'3'.repeat(64)},durationMinutes:5,items:[item],totalEstimatedMinutes:3,unusedMinutes:2}};
   assert(T.renderToday({recommendation:rec,plan}).includes('correction ciblée'));assert.throws(()=>T.validateRecommendation({...rec,reasonCodes:['FREE_TEXT']}),/INVALID_RECOMMENDATION/);assert.throws(()=>T.validateRecommendation({...rec,unknown:true}),/UNKNOWN_FIELD/);
   const otherCourse={packageLineageId:'other',courseLineageId:'c'},badRec={...rec,objectiveRef:{courseRef:otherCourse,objectiveId:'o'},preferredActivityRef:{courseRef:otherCourse,activityLineageId:'a'},eligibleActivityRefs:[{courseRef:otherCourse,activityLineageId:'a'}]};assert.throws(()=>T.validateRecommendationPlan(badRec,plan),/MISMATCH/);
   let calls=[],focus=[];const core={commitActivitySubmission:async(...a)=>{calls.push(a);return{event:{eventId:'e'},resumeState:{nextItemPosition:1,focusTarget:'atlas-session-summary'}}},requestAssistance:async(...a)=>{calls.push(a);return{committed:true,record:{assistanceUseId:'h'}}}};const c=S.createSessionController({core,focus:x=>focus.push(x)});c.start({sessionId:'s'},{nextItemPosition:0,focusTarget:'first'});
   (async()=>{await c.submit({choiceId:'raw'});assert.deepStrictEqual(calls[0],['s',0,{choiceId:'raw'}]);assert.deepStrictEqual(focus,['first','atlas-session-summary']);await c.requestHelp('hint');assert.equal(c.snapshot().help.assistanceUseId,'h');const bad=S.createSessionController({core:{...core,requestAssistance:async()=>({committed:false})}});bad.start({sessionId:'s'},{});await assert.rejects(()=>bad.requestHelp('hint'),/NOT_PERSISTED/);
   assert(S.renderSession({plan,resumeState:{nextItemPosition:0}}).includes('Correction'));const completed=S.renderSession({plan,resumeState:{nextItemPosition:1}});assert(completed.includes('Séance terminée'));assert(!completed.includes('data-atlas-submit'));
   const e={evidenceVersion:'atlas.objective-evidence.v1',objectiveRef,state:'validated-recently',lastEvidenceAt:'2026-01-01T00:00:00.000Z',lastValidationAt:'2026-01-01T00:00:00.000Z',practiceAttempts:1,correctionsCompleted:0,validationAttempts:1,latestPracticeCorrect:true,latestValidationCorrect:true};assert(U.renderSummary({evidence:[e],completed:true}).includes('ni une certification'));
   const signal={ruleVersion:'atlas.learning.reward.v1',rewardId:'atlas-reward-sha256:'+'4'.repeat(64),kind:'validation-reconfirmed',labelCode:'reward.validation_reconfirmed',objectiveRef,evidenceEventIds:['atlas-event-sha256:'+'5'.repeat(64)],occurredAt:'2026-01-01T00:00:00.000Z'};assert(R.renderRewards([signal]).includes('reconfirmée'));assert.throws(()=>R.validateSignal({...signal,kind:'transfer-completed'}),/INVALID_REWARD/);assert.throws(()=>R.validateSignal({...signal,extra:true}),/UNKNOWN_FIELD/);
   const injection={...signal,rewardId:'atlas-reward-sha256:'+'6'.repeat(64)+'" onmouseover="x',occurredAt:'2026-01-01T00:00:00.000Z<script>'};assert.throws(()=>R.renderRewards([injection]),/INVALID_REWARD/);
   console.log('ATLAS_EXPERIENCE_NODE_PASS 24/24');})().catch(e=>{console.error(e);process.exit(1)});
  ''')
  cp=subprocess.run(['node','-e',js,str(ROOT)],capture_output=True,text=True);self.assertEqual(cp.returncode,0,cp.stderr);self.assertIn('24/24',cp.stdout)
 def test_css_isolated_and_mobile(self):
  css=(ROOT/'src/atlas.css').read_text();self.assertIn('.atlas-m1',css);self.assertIn('@media(max-width:520px)',css);self.assertNotIn('body{',css)
 def test_no_semantic_owners(self):
  text='\n'.join(p.read_text() for p in (ROOT/'src/ui').glob('atlas_*.js'))
  for x in ('indexedDB','localStorage','Math.random','fetch(','Date.now','createHash'):
   self.assertNotIn(x,text)
if __name__=='__main__':unittest.main(verbosity=2)
