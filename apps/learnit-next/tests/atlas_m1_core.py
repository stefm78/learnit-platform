#!/usr/bin/env python3
import pathlib,subprocess,textwrap,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Core(unittest.TestCase):
 def test_node_matrix(self):
  js=textwrap.dedent(r'''
   const assert=require('assert');
   const C=require(process.argv[1]+'/src/core/atlas_clock.js'),E=require(process.argv[1]+'/src/core/atlas_events.js'),S=require(process.argv[1]+'/src/ports/atlas_storage.js'),I=require(process.argv[1]+'/src/adapters/atlas_indexeddb.js');
   assert.throws(()=>C.assertCanonicalTimestamp('2026-01-01T00:00:00+00:00'),/NON_CANONICAL/);const clock=new C.ControlledAtlasClock('2026-01-01T00:00:00.000Z');
   assert.throws(()=>E.canonical({required:'ok',forbiddenUndefined:undefined}),/NON_CANONICAL_VALUE/);
   const courseRef={packageLineageId:'p',courseLineageId:'c'},objectiveRef={courseRef,objectiveId:'o'},a=id=>({courseRef,activityLineageId:id}),contentRevisionRef={packageLineageId:'p',packageRevisionId:'r',packageDigest:'sha256:'+'a'.repeat(64)};
   const payload={schemaVersion:'atlas.session-plan.v1',engineVersion:'v',courseRef,contentRevisionRef,durationMinutes:5,items:[{position:0,objectiveRef,activityRef:a('practice'),action:'start-practice',executionClass:'practice',estimatedMinutes:2}],totalEstimatedMinutes:2,unusedMinutes:3};
   const hex=E.hash('learnit.atlas.m1.v0.3/plan-digest',payload),plan={planId:'atlas-plan-sha256:'+hex,planDigest:'sha256:'+hex,payload};E.validatePlan(plan);assert.throws(()=>E.validatePlan({...plan,extra:true}),/UNKNOWN_FIELD/);
   const activities=new Map([['practice',{type:'qcm',answer:'A',scoringRuleId:'qcm.v1',score:r=>r==='A'}]]),registry={activity:ref=>activities.get(ref.activityLineageId),validateClaim:()=>true};const storage=new S.InMemoryAtlasStorage(),core=new S.AtlasCoreService({storage,clock,registry});
   const req=core.prepareStartRequest(plan.planDigest),s1=core.startSession(req.startRequestId,plan),s2=core.startSession(req.startRequestId,plan);assert.deepStrictEqual(s1,s2);assert.equal(storage.learningEvents.filter(x=>x.kind==='session-started').length,1);
   const bad=core.commitActivitySubmission(s1.sessionId,0,'B');assert.equal(bad.execution.outcome,'incorrect');assert.equal(Object.prototype.hasOwnProperty.call(bad.execution,'validationAdmissible'),false);assert.equal(core.evidence()[0].state,'review-needed');
   core.requestAssistance(s1.sessionId,0,'hint');const assisted=core.commitActivitySubmission(s1.sessionId,0,'A');assert.equal(assisted.execution.assistance,'used');
   const before=JSON.stringify(core.evidence());core.lifecycle(s1.sessionId,'session-interrupted');core.lifecycle(s1.sessionId,'session-resumed');assert.equal(JSON.stringify(core.evidence()),before);
   storage.injectFailure();const counts=[storage.scoredExecutions.length,storage.learningEvents.length,storage.resumeStates[0].itemStates[0].submissionOrdinal];assert.throws(()=>core.commitActivitySubmission(s1.sessionId,0,'A'),/FAULT_INJECTED/);assert.deepStrictEqual([storage.scoredExecutions.length,storage.learningEvents.length,storage.resumeStates[0].itemStates[0].submissionOrdinal],counts);
   const exported=core.exportState();assert.equal(exported.namespace,'learnit.atlas.m1.v2');assert.throws(()=>core.importState({atlasStateVersion:'0.2',namespace:'learnit.atlas.m1.v1'}),/UNSUPPORTED/);
   const malformed=structuredClone(exported);malformed.learningEvents='not-an-array';assert.throws(()=>core.importState(malformed),/INVALID_IMPORT/);
   const unknown=structuredClone(exported);unknown.scoredExecutions[0].garbage=true;assert.throws(()=>core.importState(unknown),/UNKNOWN_FIELD/);
   const storage2=new S.InMemoryAtlasStorage(),core2=new S.AtlasCoreService({storage:storage2,clock,registry});assert.equal(core2.importState(exported),true);assert.equal(storage2.learningEvents.length,storage.learningEvents.length);
   assert.deepStrictEqual(I.STORE_KEY_PATHS,{learningEvents:'eventId',scoredExecutions:'executionId',resumeStates:'sessionRef.sessionId',atlasMeta:'key'});
   let created={};const fake={open(){const req={result:{objectStoreNames:{contains:()=>false},createObjectStore:(n,o)=>{created[n]=o.keyPath}}};queueMicrotask(()=>{req.onupgradeneeded();req.onsuccess()});return req;}};I.openAtlasIndexedDb(fake).then(()=>{assert.deepStrictEqual(created,I.STORE_KEY_PATHS);console.log('ATLAS_CORE_NODE_PASS 28/28')}).catch(e=>{console.error(e);process.exit(1)});
  ''')
  cp=subprocess.run(['node','-e',js,str(ROOT)],capture_output=True,text=True);self.assertEqual(cp.returncode,0,cp.stderr);self.assertIn('28/28',cp.stdout)
 def test_forbidden_dependencies(self):
  text='\n'.join(p.read_text() for p in ROOT.rglob('atlas_*.js'))
  for x in ('fetch(','WebSocket','XMLHttpRequest','Math.random','learnit_atlas_m1_v1'):
   self.assertNotIn(x,text)
if __name__=='__main__':unittest.main(verbosity=2)
