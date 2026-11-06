import test from 'node:test';
import assert from 'node:assert/strict';
import { createV6AssistanceService, V6AssistanceError } from '../src/core/v6_assistance.js';
const D = 'sha256:'+'a'.repeat(64); const E = 'sha256:'+'b'.repeat(64);
const UUIDS=['e41026be-146f-4b98-a532-20484884b931','b47750b6-7929-488d-98d7-e6dfec04c1f5','d5d54391-bef7-47ee-8b04-b68b99412c5d','a135be43-4b5d-443e-aa2e-27e7a284f11b'];
const ctx = (v={})=>({contract:'learnit.kit.v6',sessionId:'session_abcd',activityId:'activity_abcd',packageRevisionDigest:D,activityRevisionDigest:E,hints:['Un','Deux','Trois'],parcoursAuthorized:true,...v});
class MemoryCAS {
  entries = new Map(); conflicts = 0; failRead=false; failCommit=false;
  async read(k) {if(this.failRead)throw Error('OFFLINE');const v=this.entries.get(k);return v?structuredClone(v):{version:0,state:null}}
  async compareAndSwap(k, version, state) {if(this.failCommit)throw Error('OFFLINE');if(this.conflicts-- > 0)return false;const old=this.entries.get(k);if((old?.version??0)!==version)return false;this.entries.set(k,structuredClone({version:version+1,state}));return true}
}
const service = (port=new MemoryCAS(),authorization=x=>x.parcoursAuthorized===true) => ({port,svc:createV6AssistanceService(port,{authorize:authorization})});
const denied = async (task,code) => assert.rejects(task,e=>e instanceof V6AssistanceError&&e.code===code);
test('empty journal never exposes hints',async()=>{const {svc}=service();assert.deepEqual((await svc.readAuthorizedView(ctx())).hints,[])});
test('persisted AUTHORIZED is never a revealed hint',async()=>{const{svc}=service();const r=await svc.requestNext(ctx(),UUIDS[0]);assert.equal(r.acknowledged,false);assert.equal((await svc.readAuthorizedView(ctx())).visibleCount,0)});
test('acknowledgement before reveal and reload replay',async()=>{const{port,svc}=service();await svc.requestNext(ctx(),UUIDS[0]);await svc.acknowledge(ctx(),UUIDS[0]);const replay=service(port).svc;assert.deepEqual((await replay.readAuthorizedView(ctx())).hints,['Un']);});
test('duplicate request and acknowledgement idempotent',async()=>{const{port,svc}=service();let a=await svc.requestNext(ctx(),UUIDS[0]);let b=await svc.requestNext(ctx(),UUIDS[0]);assert.deepEqual(a,b);assert.equal(port.entries.values().next().value.state.events.length,1);await svc.acknowledge(ctx(),UUIDS[0]);await svc.acknowledge(ctx(),UUIDS[0]);assert.equal(port.entries.values().next().value.state.events.length,2)});
test('different request cannot pass pending acknowledgement',async()=>{const{svc}=service();await svc.requestNext(ctx(),UUIDS[0]);await denied(()=>svc.requestNext(ctx(),UUIDS[1]),'HINT_PENDING_ACK')});
test('all 3 hints revealed in order; then exhausted',async()=>{const{svc}=service();for(let i=0;i<3;i++){await svc.requestNext(ctx(),UUIDS[i]);await svc.acknowledge(ctx(),UUIDS[i]);assert.equal((await svc.readAuthorizedView(ctx())).visibleCount,i+1)}await denied(()=>svc.requestNext(ctx(),UUIDS[3]),'HINTS_EXHAUSTED')});
test('zero hints cannot be requested',async()=>{const{svc}=service();await denied(()=>svc.requestNext(ctx({hints:[]}),UUIDS[0]),'HINTS_EXHAUSTED')});
test('deny unauthorised Parcours context',async()=>{const{svc}=service();await denied(()=>svc.requestNext(ctx({parcoursAuthorized:false}),UUIDS[0]),'PARCOURS_AUTHORIZATION_DENIED');await denied(()=>svc.readAuthorizedView(ctx({parcoursAuthorized:false})),'PARCOURS_AUTHORIZATION_DENIED')});
test('V5 cannot masquerade as V6',async()=>{const{svc}=service();await denied(()=>svc.requestNext(ctx({contract:'learnit.kit.v5'}),UUIDS[0]),'V6_CONTRACT_REQUIRED')});
test('source digest drift fails closed',async()=>{const{svc}=service();await svc.requestNext(ctx(),UUIDS[0]);await denied(()=>svc.acknowledge(ctx({activityRevisionDigest:D}),UUIDS[0]),'SOURCE_BINDING_CHANGED')});
test('invalid source hint payload fail closed',async()=>{const{svc}=service();await denied(()=>svc.readAuthorizedView(ctx({hints:['x','y','z','w']})),'V6_HINTS_INVALID');await denied(()=>svc.readAuthorizedView(ctx({hints:['ok','   ']})),'V6_HINTS_INVALID')});
test('unknown ACK never creates an event',async()=>{const{svc}=service();await denied(()=>svc.acknowledge(ctx(),UUIDS[1]),'UNKNOWN_REQUEST_ID')});
test('resumes from crash after request before ACK',async()=>{const{port,svc}=service();await svc.requestNext(ctx(),UUIDS[0]);const resumed=service(port).svc;assert.equal((await resumed.requestNext(ctx(),UUIDS[0])).rank,0);assert.equal((await resumed.readAuthorizedView(ctx())).visibleCount,0);await resumed.acknowledge(ctx(),UUIDS[0]);assert.deepEqual((await resumed.readAuthorizedView(ctx())).hints,['Un'])});
test('offline write must never reveal',async()=>{const p=new MemoryCAS(),s=service(p).svc;p.failCommit=true;await assert.rejects(()=>s.requestNext(ctx(),UUIDS[0]),/OFFLINE/);p.failCommit=false;assert.equal((await s.readAuthorizedView(ctx())).visibleCount,0)});
test('bounded CAS conflict retries',async()=>{const p=new MemoryCAS(),s=service(p).svc;p.conflicts=2;await s.requestNext(ctx(),UUIDS[0]);assert.equal((await s.readAuthorizedView(ctx())).hasPendingAuthorization,true)});
test('CAS exhaustion throws without hints',async()=>{const p=new MemoryCAS(),s=service(p).svc;p.conflicts=100;await denied(()=>s.requestNext(ctx(),UUIDS[0]),'CAS_CONFLICT_EXHAUSTED');assert.equal((await s.readAuthorizedView(ctx())).visibleCount,0)});
test('tampered out-of-order journal denied',async()=>{const p=new MemoryCAS(),s=service(p).svc;await s.requestNext(ctx(),UUIDS[0]);const v=p.entries.values().next().value;v.state.events.push({event:'ACKNOWLEDGED',requestId:UUIDS[1],rank:0});await denied(()=>s.readAuthorizedView(ctx()),'JOURNAL_ACK_ORDER_INVALID')});
test('tampered source binding denied',async()=>{const p=new MemoryCAS(),s=service(p).svc;await s.requestNext(ctx(),UUIDS[0]);p.entries.values().next().value.state.binding='tampered';await denied(()=>s.readAuthorizedView(ctx()),'SOURCE_BINDING_CHANGED')});
test('no scoring or maxUses changes are written',async()=>{const p=new MemoryCAS(),s=service(p).svc;await s.requestNext(ctx(),UUIDS[0]);await s.acknowledge(ctx(),UUIDS[0]);let row=p.entries.values().next().value.state;assert.deepEqual(Object.keys(row),['schema','binding','events']);assert(!JSON.stringify(row).includes('Un'));assert(!JSON.stringify(row).includes('maxUses'));assert(!JSON.stringify(row).includes('score'))});
test('parallel duplicate request consumes once',async()=>{const{port,svc}=service();let [x,y]=await Promise.all([svc.requestNext(ctx(),UUIDS[0]),svc.requestNext(ctx(),UUIDS[0])]);assert.equal(x.rank,0);assert.deepEqual(x,y);assert.equal(port.entries.values().next().value.state.events.length,1)});
test('parallel distinct request retains only one pending item',async()=>{const{port,svc}=service();const results=await Promise.allSettled([svc.requestNext(ctx(),UUIDS[0]),svc.requestNext(ctx(),UUIDS[1])]);assert.equal(results.filter(x=>x.status==='fulfilled').length,1);assert.equal(port.entries.values().next().value.state.events.length,1)});

test('hint text tampering under unchanged revision digest is rejected',async()=>{
  const {svc}=service();await svc.requestNext(ctx(),UUIDS[0]);
  await denied(()=>svc.readAuthorizedView(ctx({hints:['changed','Deux','Trois']})),'SOURCE_BINDING_CHANGED');
});
test('invalid resumed journal with erased state and incremented version fails closed',async()=>{
  const p=new MemoryCAS(),s=service(p).svc;await s.requestNext(ctx(),UUIDS[0]);
  p.entries.values().next().value.state=null;
  await denied(()=>s.readAuthorizedView(ctx()),'JOURNAL_MISSING_AFTER_COMMIT');
});

test('crash after persisted AUTHORIZE exposes pending request ID only, never text',async()=>{
  const {svc,port}=service();await svc.requestNext(ctx(),UUIDS[0]);
  const recovered=service(port).svc;const v=await recovered.readAuthorizedView(ctx());
  assert.equal(v.pendingRequestId,UUIDS[0]);assert.deepEqual(v.hints,[]);
  await recovered.acknowledge(ctx(),v.pendingRequestId);
  assert.deepEqual((await recovered.readAuthorizedView(ctx())).hints,['Un']);
});

import { createSessionService } from '../src/core/session.js';
test('V6 Parcours session UUID survives reload, rotates on new start; V5 remains untouched', async () => {
  const records = new Map();
  const course = {courseInstallId:'course-v6-0001',contract:'learnit.kit.v6',displayLabel:'Fixture',
    course:{activities:[{activityRevisionId:'activity-v6-0001',type:'lesson'}],objectives:[]}};
  const storage={
    getCourse: async id => id===course.courseInstallId ? course : null,
    setMeta: async (key,value)=>{records.set(key,structuredClone(value))},
    getMeta: async key=>records.get(key)??null,
    deleteMeta: async key=>{records.delete(key)}
  };
  const progress={
    learningLoopV2Enabled:false,
    getProgress:async()=>[],
    getCourseProgress:async()=>({total:1,completed:0,isComplete:false}),
    reviewQueue:()=>course.course.activities
  };
  const a=createSessionService(storage,progress);
  const started=await a.startCourse(course.courseInstallId);
  assert.match(started.v6AssistanceSessionId,/^[0-9a-f]{8}-[0-9a-f-]{27}$/i);
  assert.equal(records.get('activeCourse').v6AssistanceSessionId,started.v6AssistanceSessionId);
  const b=createSessionService(storage,progress);
  const resumed=await b.resumeActiveCourse();
  assert.equal(resumed.v6AssistanceSessionId,started.v6AssistanceSessionId);
  const again=await b.startCourse(course.courseInstallId);
  assert.notEqual(again.v6AssistanceSessionId,started.v6AssistanceSessionId);
});

test('intent-aware Parcours mock refuses new hint after submitted answer but preserves acknowledged view', async()=>{
  let submitted=false;
  const p=new MemoryCAS();
  const s=createV6AssistanceService(p,{authorize:(x,purpose)=>
    x.parcoursAuthorized===true&&(purpose==='read'||!submitted)});
  await s.requestNext(ctx(),UUIDS[0]);await s.acknowledge(ctx(),UUIDS[0]);
  submitted=true;
  assert.deepEqual((await s.readAuthorizedView(ctx())).hints,['Un']);
  await denied(()=>s.requestNext(ctx(),UUIDS[1]),'PARCOURS_AUTHORIZATION_DENIED');
  assert.equal(p.entries.values().next().value.state.events.length,2);
});
test('pending authorization must not acknowledge after answer submission',async()=>{
  let submitted=false;
  const p=new MemoryCAS(),s=createV6AssistanceService(p,{authorize:(x,purpose)=>purpose==='read'||!submitted});
  await s.requestNext(ctx(),UUIDS[0]);submitted=true;
  await denied(()=>s.acknowledge(ctx(),UUIDS[0]),'PARCOURS_AUTHORIZATION_DENIED');
  const v=await s.readAuthorizedView(ctx());
  assert.equal(v.visibleCount,0);assert.deepEqual(v.hints,[]);
  assert.equal(v.hasPendingAuthorization,true);
});
test('fresh session has zero hints; old journal remains retained',async()=>{
  const p=new MemoryCAS(),s=createV6AssistanceService(p,{authorize:()=>true});
  await s.requestNext(ctx(),UUIDS[0]);await s.acknowledge(ctx(),UUIDS[0]);
  const newer=ctx({sessionId:'session_new_12345'});
  assert.deepEqual((await s.readAuthorizedView(newer)).hints,[]);
  assert.deepEqual((await s.readAuthorizedView(ctx())).hints,['Un']);
  assert.equal(p.entries.size,1);
});
test('assisted success classification is separate from scoring',async()=>{
  const {svc}=service();
  await svc.requestNext(ctx(),UUIDS[0]);await svc.acknowledge(ctx(),UUIDS[0]);
  const autonomy=(await svc.readAuthorizedView(ctx())).visibleCount===0;
  const scoredResponse={scored:true,correct:true,score:1,maxUses:20};
  assert.equal(autonomy,false);
  assert.deepEqual(scoredResponse,{scored:true,correct:true,score:1,maxUses:20});
});
