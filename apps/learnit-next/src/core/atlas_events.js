'use strict';
const crypto=require('crypto');
const {assertCanonicalTimestamp}=require('./atlas_clock.js');
const SHA=/^sha256:[0-9a-f]{64}$/;
const IDS=Object.freeze({
 event:/^atlas-event-sha256:[0-9a-f]{64}$/,
 execution:/^atlas-execution-sha256:[0-9a-f]{64}$/,
 plan:/^atlas-plan-sha256:[0-9a-f]{64}$/,
 session:/^atlas-session-sha256:[0-9a-f]{64}$/,
 start:/^atlas-start-sha256:[0-9a-f]{64}$/,
 assistance:/^atlas-assistance-sha256:[0-9a-f]{64}$/,
 claim:/^atlas-claim-sha256:[0-9a-f]{64}$/
});
function fail(code,detail=''){const e=new Error(detail?`${code}: ${detail}`:code);e.code=code;throw e;}
function isObject(value){return value!==null&&typeof value==='object'&&!Array.isArray(value);}
function assertClosed(value,required,optional=[],code='INVALID_OBJECT'){if(!isObject(value))fail(code);const allowed=new Set([...required,...optional]);for(const key of Object.keys(value))if(!allowed.has(key))fail('UNKNOWN_FIELD',key);for(const key of required)if(!(key in value))fail('MISSING_FIELD',key);return value;}
function compareCodePoints(a,b){const aa=Array.from(a),bb=Array.from(b),n=Math.min(aa.length,bb.length);for(let i=0;i<n;i++){const d=aa[i].codePointAt(0)-bb[i].codePointAt(0);if(d)return d;}return aa.length-bb.length;}
function canonical(value,stack=new WeakSet()){
 if(value===undefined||typeof value==='function'||typeof value==='symbol'||typeof value==='bigint')fail('NON_CANONICAL_VALUE');
 if(value===null||typeof value==='boolean')return value;
 if(typeof value==='string')return value.normalize('NFC');
 if(typeof value==='number'){if(!Number.isInteger(value)||!Number.isFinite(value)||Object.is(value,-0))fail('NON_CANONICAL_NUMBER');return value;}
 if(!value||typeof value!=='object')fail('NON_CANONICAL_VALUE');if(stack.has(value))fail('CANONICAL_CYCLE');stack.add(value);let out;
 if(Array.isArray(value))out=value.map(x=>canonical(x,stack));else{out={};for(const k of Object.keys(value).sort(compareCodePoints)){if(value[k]===undefined)fail('NON_CANONICAL_VALUE');out[k.normalize('NFC')]=canonical(value[k],stack);}}
 stack.delete(value);return out;
}
function canonicalJson(value){return JSON.stringify(canonical(value));}
function hash(domain,value){return crypto.createHash('sha256').update(Buffer.concat([Buffer.from(domain,'utf8'),Buffer.from([0]),Buffer.from(canonicalJson(value),'utf8')])).digest('hex');}
function typed(prefix,domain,value){return `${prefix}${hash(domain,value)}`;}
function without(value,field){const out={};for(const [k,v] of Object.entries(value))if(k!==field)out[k]=v;return out;}
function deepFreeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.freeze(value);Object.values(value).forEach(deepFreeze);}return value;}
function nonEmpty(value,code){if(typeof value!=='string'||!value)fail(code);return value;}
function assertCourseRef(v){assertClosed(v,['packageLineageId','courseLineageId'],[],'INVALID_COURSE_REF');nonEmpty(v.packageLineageId,'INVALID_COURSE_REF');nonEmpty(v.courseLineageId,'INVALID_COURSE_REF');return v;}
function assertObjectiveRef(v){assertClosed(v,['courseRef','objectiveId'],[],'INVALID_OBJECTIVE_REF');nonEmpty(v.objectiveId,'INVALID_OBJECTIVE_REF');assertCourseRef(v.courseRef);return v;}
function assertActivityRef(v){assertClosed(v,['courseRef','activityLineageId'],[],'INVALID_ACTIVITY_REF');nonEmpty(v.activityLineageId,'INVALID_ACTIVITY_REF');assertCourseRef(v.courseRef);return v;}
function assertContentRevisionRef(v){assertClosed(v,['packageLineageId','packageRevisionId','packageDigest'],[],'INVALID_CONTENT_REVISION_REF');nonEmpty(v.packageLineageId,'INVALID_CONTENT_REVISION_REF');nonEmpty(v.packageRevisionId,'INVALID_CONTENT_REVISION_REF');if(!SHA.test(v.packageDigest))fail('INVALID_CONTENT_REVISION_REF');return v;}
function assertSessionRef(v){assertClosed(v,['sessionId','planId'],[],'INVALID_SESSION_REF');if(!IDS.session.test(v.sessionId)||!IDS.plan.test(v.planId))fail('INVALID_SESSION_REF');return v;}
function actionClass(action){return ({'start-practice':'practice','continue-practice':'practice','correct-practice':'correction','attempt-validation':'validation','maintain-recent-validation':'validation'})[action]||fail('UNKNOWN_ACTION');}
function validatePlanItem(item,index){
 const base=['position','objectiveRef','activityRef','action','executionClass','estimatedMinutes'];let optional=[];
 if(item.action==='correct-practice')optional=['correctsEventId'];
 if(['attempt-validation','maintain-recent-validation'].includes(item.action))optional=['validationBasisEventId','independenceClaimId'];
 assertClosed(item,base,optional,'INVALID_PLAN_ITEM');if(item.position!==index)fail('INVALID_PLAN_POSITION');assertObjectiveRef(item.objectiveRef);assertActivityRef(item.activityRef);
 if(canonicalJson(item.objectiveRef.courseRef)!==canonicalJson(item.activityRef.courseRef))fail('PLAN_SCOPE_MISMATCH');
 if(actionClass(item.action)!==item.executionClass)fail('PLAN_ACTION_CLASS_MISMATCH');
 if(!Number.isInteger(item.estimatedMinutes)||item.estimatedMinutes<1||item.estimatedMinutes>30)fail('INVALID_ESTIMATED_MINUTES');
 if(item.action==='correct-practice'&&!IDS.event.test(item.correctsEventId||''))fail('CORRECTS_EVENT_ID_REQUIRED');
 if(['attempt-validation','maintain-recent-validation'].includes(item.action)&&(!IDS.event.test(item.validationBasisEventId||'')||!IDS.claim.test(item.independenceClaimId||'')))fail('VALIDATION_PROVENANCE_REQUIRED');
 return item;
}
function validatePlan(plan){
 assertClosed(plan,['planId','planDigest','payload'],[],'INVALID_PLAN');
 assertClosed(plan.payload,['schemaVersion','engineVersion','courseRef','contentRevisionRef','durationMinutes','items','totalEstimatedMinutes','unusedMinutes'],[],'INVALID_PLAN_PAYLOAD');
 if(plan.payload.schemaVersion!=='atlas.session-plan.v1'||typeof plan.payload.engineVersion!=='string'||!plan.payload.engineVersion)fail('INVALID_PLAN');
 assertCourseRef(plan.payload.courseRef);assertContentRevisionRef(plan.payload.contentRevisionRef);if(![5,15,30].includes(plan.payload.durationMinutes)||!Array.isArray(plan.payload.items))fail('INVALID_DURATION');
 let total=0;plan.payload.items.forEach((item,i)=>{validatePlanItem(item,i);if(canonicalJson(item.objectiveRef.courseRef)!==canonicalJson(plan.payload.courseRef))fail('PLAN_SCOPE_MISMATCH');total+=item.estimatedMinutes;});
 if(!Number.isInteger(plan.payload.totalEstimatedMinutes)||!Number.isInteger(plan.payload.unusedMinutes)||total!==plan.payload.totalEstimatedMinutes||total+plan.payload.unusedMinutes!==plan.payload.durationMinutes)fail('PLAN_BUDGET_MISMATCH');
 const hex=hash('learnit.atlas.m1.v0.3/plan-digest',plan.payload);if(plan.planDigest!==`sha256:${hex}`||plan.planId!==`atlas-plan-sha256:${hex}`)fail('PLAN_ID_DIGEST_MISMATCH');return plan;
}
function eventId(payload){return typed('atlas-event-sha256:','learnit.atlas.m1.v0.3/event-id',payload);}
function executionId(payload){return typed('atlas-execution-sha256:','learnit.atlas.m1.v0.3/execution-id',payload);}
function assistanceUseId(payload){return typed('atlas-assistance-sha256:','learnit.atlas.m1.v0.3/assistance-use-id',payload);}
function startRequestId(payload){return typed('atlas-start-sha256:','learnit.atlas.m1.v0.3/start-request-id',payload);}
function sessionId(payload){return typed('atlas-session-sha256:','learnit.atlas.m1.v0.3/session-id',payload);}
function responseDigest(raw){return `sha256:${hash('learnit.atlas.m1.v0.3/response-digest',raw)}`;}
function scoringRuleDigest(rule){return `sha256:${hash('learnit.atlas.m1.v0.3/scoring-rule-digest',rule)}`;}
function validatePedagogicalEvent(event){
 const required=['eventVersion','eventId','kind','objectiveRef','executionId','occurredAt'];const optional=event&&event.kind==='activity-corrected'?['correctsEventId']:[];assertClosed(event,required,optional,'INVALID_PEDAGOGICAL_EVENT');
 if(event.eventVersion!=='atlas.learning-event.v1'||!IDS.event.test(event.eventId)||!IDS.execution.test(event.executionId))fail('INVALID_PEDAGOGICAL_EVENT');assertObjectiveRef(event.objectiveRef);assertCanonicalTimestamp(event.occurredAt);
 if(!['activity-attempt','activity-corrected'].includes(event.kind))fail('UNKNOWN_EVENT_KIND');if(event.kind==='activity-corrected'&&!IDS.event.test(event.correctsEventId||''))fail('CORRECTS_EVENT_ID_REQUIRED');
 const expected=eventId(without(event,'eventId'));if(event.eventId!==expected)fail('EVENT_ID_INVALID');return event;
}
function validateScoredExecution(record){
 assertClosed(record,['executionVersion','executionId','sessionRef','courseRef','contentRevisionRef','planDigest','itemPosition','submissionOrdinal','objectiveRef','activityRef','action','executionClass','responseDigest','scoringRuleId','scoringRuleDigest','outcome','assistance','assistanceUseIds','submittedAt','scoredAt'],[],'INVALID_SCORED_EXECUTION');
 if(record.executionVersion!=='atlas.scored-execution.v1'||!IDS.execution.test(record.executionId)||!SHA.test(record.planDigest)||!SHA.test(record.responseDigest)||!SHA.test(record.scoringRuleDigest))fail('INVALID_SCORED_EXECUTION');
 assertSessionRef(record.sessionRef);assertCourseRef(record.courseRef);assertContentRevisionRef(record.contentRevisionRef);assertObjectiveRef(record.objectiveRef);assertActivityRef(record.activityRef);
 if(canonicalJson(record.courseRef)!==canonicalJson(record.objectiveRef.courseRef)||canonicalJson(record.courseRef)!==canonicalJson(record.activityRef.courseRef))fail('EXECUTION_SCOPE_MISMATCH');
 if(!Number.isInteger(record.itemPosition)||record.itemPosition<0||!Number.isInteger(record.submissionOrdinal)||record.submissionOrdinal<1||actionClass(record.action)!==record.executionClass)fail('INVALID_SCORED_EXECUTION');
 if(!['correct','incorrect'].includes(record.outcome)||!['none','used','unknown'].includes(record.assistance)||!Array.isArray(record.assistanceUseIds)||new Set(record.assistanceUseIds).size!==record.assistanceUseIds.length||record.assistanceUseIds.some(x=>!IDS.assistance.test(x)))fail('INVALID_SCORED_EXECUTION');
 assertCanonicalTimestamp(record.submittedAt);assertCanonicalTimestamp(record.scoredAt);const expected=executionId(without(record,'executionId'));if(record.executionId!==expected)fail('EXECUTION_ID_INVALID');return record;
}
function validateResumeState(resume){
 assertClosed(resume,['resumeVersion','sessionRef','courseRef','contentRevisionRef','planDigest','nextItemPosition','focusTarget','lifecycleOrdinal','itemStates'],['lastCommittedEventId','responseDraft'],'INVALID_RESUME_STATE');
 if(resume.resumeVersion!=='atlas.resume-state.v1'||!SHA.test(resume.planDigest)||!Number.isInteger(resume.nextItemPosition)||resume.nextItemPosition<0||!Number.isInteger(resume.lifecycleOrdinal)||resume.lifecycleOrdinal<0||typeof resume.focusTarget!=='string'||!Array.isArray(resume.itemStates))fail('INVALID_RESUME_STATE');
 assertSessionRef(resume.sessionRef);assertCourseRef(resume.courseRef);assertContentRevisionRef(resume.contentRevisionRef);if(resume.lastCommittedEventId&&!IDS.event.test(resume.lastCommittedEventId))fail('INVALID_RESUME_STATE');
 const positions=new Set();for(const item of resume.itemStates){assertClosed(item,['itemPosition','submissionOrdinal','assistance','assistanceUseIds']);if(!Number.isInteger(item.itemPosition)||item.itemPosition<0||positions.has(item.itemPosition)||!Number.isInteger(item.submissionOrdinal)||item.submissionOrdinal<0||!['none','used','unknown'].includes(item.assistance)||!Array.isArray(item.assistanceUseIds)||item.assistanceUseIds.some(x=>!IDS.assistance.test(x)))fail('INVALID_RESUME_STATE');positions.add(item.itemPosition);}return resume;
}
module.exports=Object.freeze({fail,isObject,assertClosed,canonical,canonicalJson,hash,typed,deepFreeze,assertCourseRef,assertObjectiveRef,assertActivityRef,assertContentRevisionRef,assertSessionRef,actionClass,validatePlan,validatePlanItem,eventId,executionId,assistanceUseId,startRequestId,sessionId,responseDigest,scoringRuleDigest,validatePedagogicalEvent,validateScoredExecution,validateResumeState,IDS,SHA});
