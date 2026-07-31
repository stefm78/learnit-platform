'use strict';
const crypto=require('crypto');
const {assertCanonicalTimestamp}=require('./atlas_clock.js');
function fail(code,detail=''){const e=new Error(detail?`${code}: ${detail}`:code);e.code=code;throw e;}
function canonical(value){if(value===null||typeof value==='string'||typeof value==='boolean')return value;if(typeof value==='number'){if(!Number.isInteger(value)||Object.is(value,-0))fail('NON_CANONICAL_NUMBER');return value;}if(Array.isArray(value))return value.map(canonical);if(value&&typeof value==='object'){const o={};for(const k of Object.keys(value).sort()){if(value[k]===undefined)continue;o[k]=canonical(value[k]);}return o;}fail('NON_CANONICAL_VALUE');}
function canonicalJson(value){return JSON.stringify(canonical(value));}
function hash(domain,value){return crypto.createHash('sha256').update(Buffer.concat([Buffer.from(domain),Buffer.from([0]),Buffer.from(canonicalJson(value))])).digest('hex');}
function typed(prefix,domain,value){return `${prefix}${hash(domain,value)}`;}
function deepFreeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.freeze(value);Object.values(value).forEach(deepFreeze);}return value;}
function assertCourseRef(v){if(!v||Object.keys(v).sort().join(',')!=='courseLineageId,packageLineageId'||!v.packageLineageId||!v.courseLineageId)fail('INVALID_COURSE_REF');return v;}
function assertObjectiveRef(v){if(!v||Object.keys(v).sort().join(',')!=='courseRef,objectiveId'||!v.objectiveId)fail('INVALID_OBJECTIVE_REF');assertCourseRef(v.courseRef);return v;}
function assertActivityRef(v){if(!v||Object.keys(v).sort().join(',')!=='activityLineageId,courseRef'||!v.activityLineageId)fail('INVALID_ACTIVITY_REF');assertCourseRef(v.courseRef);return v;}
function validatePlan(plan){if(!plan||typeof plan!=='object'||!plan.payload)fail('INVALID_PLAN');const hex=hash('learnit.atlas.m1.v0.3/plan-digest',plan.payload);if(plan.planDigest!==`sha256:${hex}`||plan.planId!==`atlas-plan-sha256:${hex}`)fail('PLAN_ID_DIGEST_MISMATCH');if(![5,15,30].includes(plan.payload.durationMinutes))fail('INVALID_DURATION');let total=0;plan.payload.items.forEach((item,i)=>{if(item.position!==i)fail('INVALID_PLAN_POSITION');assertObjectiveRef(item.objectiveRef);assertActivityRef(item.activityRef);if(!Number.isInteger(item.estimatedMinutes)||item.estimatedMinutes<1||item.estimatedMinutes>30)fail('INVALID_ESTIMATED_MINUTES');total+=item.estimatedMinutes;});if(total!==plan.payload.totalEstimatedMinutes||total+plan.payload.unusedMinutes!==plan.payload.durationMinutes)fail('PLAN_BUDGET_MISMATCH');return plan;}
function eventId(payload){return typed('atlas-event-sha256:','learnit.atlas.m1.v0.3/event-id',payload);}
function executionId(payload){return typed('atlas-execution-sha256:','learnit.atlas.m1.v0.3/execution-id',payload);}
function assistanceUseId(payload){return typed('atlas-assistance-sha256:','learnit.atlas.m1.v0.3/assistance-use-id',payload);}
function startRequestId(payload){return typed('atlas-start-sha256:','learnit.atlas.m1.v0.3/start-request-id',payload);}
function sessionId(payload){return typed('atlas-session-sha256:','learnit.atlas.m1.v0.3/session-id',payload);}
function responseDigest(raw){return `sha256:${hash('learnit.atlas.m1.v0.3/response-digest',raw)}`;}
function scoringRuleDigest(rule){return `sha256:${hash('learnit.atlas.m1.v0.3/scoring-rule-digest',rule)}`;}
function validatePedagogicalEvent(event){assertObjectiveRef(event.objectiveRef);assertCanonicalTimestamp(event.occurredAt);if(!['activity-attempt','activity-corrected'].includes(event.kind))fail('UNKNOWN_EVENT_KIND');if(event.kind==='activity-corrected'&&!event.correctsEventId)fail('CORRECTS_EVENT_ID_REQUIRED');if(event.kind==='activity-attempt'&&event.correctsEventId)fail('NON_APPLICABLE_IDENTIFIER');return event;}
module.exports=Object.freeze({fail,canonical,canonicalJson,hash,typed,deepFreeze,assertCourseRef,assertObjectiveRef,assertActivityRef,validatePlan,eventId,executionId,assistanceUseId,startRequestId,sessionId,responseDigest,scoringRuleDigest,validatePedagogicalEvent});
