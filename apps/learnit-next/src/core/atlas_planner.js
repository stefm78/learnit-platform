'use strict';
const E=require('./atlas_evidence.js');
function fail(code){const e=new Error(code);e.code=code;throw e;}
function canonicalize(value){return E.canonicalize(value);}
function canonicalJson(value){return E.canonicalJson(value);}
function atlasHash(domain,value){return E.atlasHash(domain,value);}
function assertClosed(value,required,optional=[]){if(!value||typeof value!=='object'||Array.isArray(value))fail('INVALID_OBJECT');const allowed=new Set([...required,...optional]);for(const key of Object.keys(value))if(!allowed.has(key))fail('UNKNOWN_FIELD');for(const key of required)if(!(key in value))fail('MISSING_FIELD');}
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
function buildPlan({engineVersion,courseRef,contentRevisionRef,durationMinutes,recommendations,itemProvenance=[]}){
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
