'use strict';
const E=require('./atlas_evidence.js');
const DIGEST_RX=/^sha256:[0-9a-f]{64}$/;
function fail(code){const e=new Error(code);e.code=code;throw e;}
function canonicalize(value){return E.canonicalize(value);}
function canonicalJson(value){return E.canonicalJson(value);}
function atlasHash(domain,value){return E.atlasHash(domain,value);}
function assertClosed(value,required,optional=[]){if(!value||typeof value!=='object'||Array.isArray(value))fail('INVALID_OBJECT');const allowed=new Set([...required,...optional]);for(const key of Object.keys(value))if(!allowed.has(key))fail('UNKNOWN_FIELD');for(const key of required)if(!(key in value))fail('MISSING_FIELD');}
function assertNonEmptyString(value,code){if(typeof value!=='string'||value.length===0)fail(code);return value;}
function assertCourseRef(ref){
  if(!ref||typeof ref!=='object'||Array.isArray(ref))fail('INVALID_COURSE_REF');
  try{assertClosed(ref,['packageLineageId','courseLineageId']);}catch(error){if(error.code==='UNKNOWN_FIELD')throw error;fail('INVALID_COURSE_REF');}
  assertNonEmptyString(ref.packageLineageId,'INVALID_COURSE_REF');
  assertNonEmptyString(ref.courseLineageId,'INVALID_COURSE_REF');
  return ref;
}
function assertContentRevisionRef(ref){
  if(!ref||typeof ref!=='object'||Array.isArray(ref))fail('INVALID_CONTENT_REVISION_REF');
  try{assertClosed(ref,['packageLineageId','packageRevisionId','packageDigest']);}catch(error){if(error.code==='UNKNOWN_FIELD')throw error;fail('INVALID_CONTENT_REVISION_REF');}
  assertNonEmptyString(ref.packageLineageId,'INVALID_CONTENT_REVISION_REF');
  assertNonEmptyString(ref.packageRevisionId,'INVALID_CONTENT_REVISION_REF');
  if(typeof ref.packageDigest!=='string'||!DIGEST_RX.test(ref.packageDigest))fail('INVALID_CONTENT_REVISION_REF');
  return ref;
}
function assertObjectiveRef(ref){E.canonicalRefKey(ref);if(!Object.prototype.hasOwnProperty.call(ref,'objectiveId'))fail('INVALID_OBJECTIVE_REF');return ref;}
function assertActivityRef(ref){E.canonicalRefKey(ref);if(!Object.prototype.hasOwnProperty.call(ref,'activityLineageId'))fail('INVALID_ACTIVITY_REF');return ref;}
function sameCourse(left,right){return E.canonicalJson(left.courseRef)===E.canonicalJson(right.courseRef);}
function validateRecommendation(rec){
  assertClosed(rec,['recommendationVersion','objectiveRef','action','eligibleActivityRefs','preferredActivityRef','estimatedMinutes','reasonCodes']);
  if(rec.recommendationVersion!=='atlas.recommendation.v1')fail('INVALID_RECOMMENDATION');
  assertObjectiveRef(rec.objectiveRef);assertActivityRef(rec.preferredActivityRef);E.executionClassForAction(rec.action);
  if(!sameCourse(rec.objectiveRef,rec.preferredActivityRef))fail('PREFERRED_ACTIVITY_COURSE_MISMATCH');
  if(!Array.isArray(rec.eligibleActivityRefs)||!rec.eligibleActivityRefs.length)fail('INVALID_RECOMMENDATION');
  const eligibleKeys=new Set();
  for(const ref of rec.eligibleActivityRefs){
    assertActivityRef(ref);
    if(!sameCourse(rec.objectiveRef,ref))fail('ELIGIBLE_ACTIVITY_COURSE_MISMATCH');
    const key=E.canonicalRefKey(ref);
    if(eligibleKeys.has(key))fail('DUPLICATE_ELIGIBLE_ACTIVITY_REF');
    eligibleKeys.add(key);
  }
  if(!eligibleKeys.has(E.canonicalRefKey(rec.preferredActivityRef)))fail('PREFERRED_ACTIVITY_NOT_ELIGIBLE');
  if(!Number.isInteger(rec.estimatedMinutes)||rec.estimatedMinutes<1||rec.estimatedMinutes>30)fail('INVALID_ESTIMATED_MINUTES');
  if(!Array.isArray(rec.reasonCodes)||new Set(rec.reasonCodes).size!==rec.reasonCodes.length||rec.reasonCodes.some(x=>!E.REASON_CODES.includes(x)))fail('INVALID_REASON_CODES');
  return rec;
}
function validateProvenance(action,provenance){
  const p=provenance||{};
  if(action==='correct-practice'){
    assertClosed(p,['correctsEventId']);if(!/^atlas-event-sha256:[0-9a-f]{64}$/.test(p.correctsEventId))fail('CORRECTS_EVENT_ID_REQUIRED');return p;
  }
  if(['attempt-validation','maintain-recent-validation'].includes(action)){
    assertClosed(p,['validationBasisEventId','independenceClaimId']);
    if(!/^atlas-event-sha256:[0-9a-f]{64}$/.test(p.validationBasisEventId)||!/^atlas-claim-sha256:[0-9a-f]{64}$/.test(p.independenceClaimId))fail('VALIDATION_PROVENANCE_REQUIRED');return p;
  }
  assertClosed(p,[]);return p;
}
function buildPlan(input){
  assertClosed(input,['engineVersion','courseRef','contentRevisionRef','durationMinutes','recommendations'],['itemProvenance']);
  const {engineVersion,courseRef,contentRevisionRef,durationMinutes,recommendations,itemProvenance=[]}=input;
  assertNonEmptyString(engineVersion,'INVALID_ENGINE_VERSION');
  assertCourseRef(courseRef);
  assertContentRevisionRef(contentRevisionRef);
  if(![5,15,30].includes(durationMinutes))fail('INVALID_DURATION');
  if(!Array.isArray(recommendations)||!Array.isArray(itemProvenance))fail('INVALID_PLAN_INPUT');
  const items=[];let total=0;
  for(let index=0;index<recommendations.length;index++){
    const rec=validateRecommendation(recommendations[index]);
    if(rec.estimatedMinutes>durationMinutes-total){if(!items.length)fail('SESSION_TIME_LIMIT');continue;}
    const executionClass=E.executionClassForAction(rec.action);
    const provenance=validateProvenance(rec.action,itemProvenance[index]);
    const item={position:items.length,objectiveRef:rec.objectiveRef,activityRef:rec.preferredActivityRef,action:rec.action,executionClass,estimatedMinutes:rec.estimatedMinutes,...provenance};
    items.push(Object.freeze(item));total+=rec.estimatedMinutes;
  }
  if(itemProvenance.length>recommendations.length)fail('SURPLUS_ITEM_PROVENANCE');
  const payload=Object.freeze({schemaVersion:'atlas.session-plan.v1',engineVersion,courseRef,contentRevisionRef,durationMinutes,items:Object.freeze(items),totalEstimatedMinutes:total,unusedMinutes:durationMinutes-total});
  const hex=atlasHash('learnit.atlas.m1.v0.3/plan-digest',payload);
  return Object.freeze({planId:`atlas-plan-sha256:${hex}`,planDigest:`sha256:${hex}`,payload});
}
module.exports=Object.freeze({canonicalize,canonicalJson,atlasHash,validateRecommendation,buildPlan});
