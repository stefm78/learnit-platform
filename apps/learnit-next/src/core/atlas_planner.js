'use strict';
const crypto=require('crypto');
const E=require('./atlas_evidence.js');
function fail(code){const e=new Error(code);e.code=code;throw e;}
function canonicalize(value){
  if(value===null||typeof value==='boolean'||typeof value==='string')return value;
  if(typeof value==='number'){if(!Number.isInteger(value)||Object.is(value,-0))fail('NON_CANONICAL_NUMBER');return value;}
  if(Array.isArray(value))return value.map(canonicalize);
  if(value&&typeof value==='object'){const out={};for(const key of Object.keys(value).sort())if(value[key]!==undefined)out[key]=canonicalize(value[key]);return out;}
  fail('NON_CANONICAL_VALUE');
}
function canonicalJson(value){return JSON.stringify(canonicalize(value));}
function atlasHash(domain,value){return crypto.createHash('sha256').update(Buffer.concat([Buffer.from(domain),Buffer.from([0]),Buffer.from(canonicalJson(value))])).digest('hex');}
function buildPlan({engineVersion,courseRef,contentRevisionRef,durationMinutes,recommendations}){
  if(![5,15,30].includes(durationMinutes))fail('INVALID_DURATION');
  const items=[];let total=0;
  for(const rec of recommendations){
    if(rec.estimatedMinutes>durationMinutes-total){if(!items.length)fail('SESSION_TIME_LIMIT');continue;}
    const executionClass=({'start-practice':'practice','continue-practice':'practice','correct-practice':'correction','attempt-validation':'validation','maintain-recent-validation':'validation'})[rec.action];
    if(!executionClass)fail('UNKNOWN_ACTION');
    const item={position:items.length,objectiveRef:rec.objectiveRef,activityRef:rec.preferredActivityRef,action:rec.action,executionClass,estimatedMinutes:rec.estimatedMinutes};
    if(rec.action==='correct-practice'){if(!rec.correctsEventId)fail('CORRECTS_EVENT_ID_REQUIRED');item.correctsEventId=rec.correctsEventId;}
    if(['attempt-validation','maintain-recent-validation'].includes(rec.action)){if(!rec.validationBasisEventId||!rec.independenceClaimId)fail('VALIDATION_PROVENANCE_REQUIRED');item.validationBasisEventId=rec.validationBasisEventId;item.independenceClaimId=rec.independenceClaimId;}
    items.push(item);total+=rec.estimatedMinutes;
  }
  const payload={schemaVersion:'atlas.session-plan.v1',engineVersion,courseRef,contentRevisionRef,durationMinutes,items,totalEstimatedMinutes:total,unusedMinutes:durationMinutes-total};
  const hex=atlasHash('learnit.atlas.m1.v0.3/plan-digest',payload);
  return Object.freeze({planId:`atlas-plan-sha256:${hex}`,planDigest:`sha256:${hex}`,payload:Object.freeze(payload)});
}
module.exports=Object.freeze({canonicalize,canonicalJson,atlasHash,buildPlan});
