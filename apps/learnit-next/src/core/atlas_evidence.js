'use strict';

const crypto = require('crypto');

const REASON_CODES = Object.freeze([
  'NEW_OBJECTIVE','PRACTICE_IN_PROGRESS','RECENT_ERROR','REVIEW_REQUIRED',
  'CORRECTION_COMPLETED','NO_INDEPENDENT_VALIDATION','VALIDATION_AVAILABLE',
  'RECENTLY_VALIDATED','TRANSFER_AVAILABLE','SESSION_TIME_LIMIT'
]);
const REWARD_PRIORITY = Object.freeze([
  'validation-reconfirmed','validation-completed','correction-completed',
  'independent-success','resumed-after-interruption'
]);
const LABEL_BY_REWARD = Object.freeze({
  'validation-reconfirmed':'reward.validation_reconfirmed',
  'validation-completed':'reward.validation_completed',
  'correction-completed':'reward.correction_completed',
  'independent-success':'reward.independent_success',
  'resumed-after-interruption':'reward.resumed_after_interruption'
});
const ACTION_EXECUTION_CLASS = Object.freeze({
  'start-practice':'practice',
  'continue-practice':'practice',
  'correct-practice':'correction',
  'attempt-validation':'validation',
  'maintain-recent-validation':'validation',
  'attempt-transfer':'transfer'
});
const TS_RX = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
const DIGEST_RX = /^sha256:[0-9a-f]{64}$/;
const CLAIM_ID_RX = /^atlas-claim-sha256:[0-9a-f]{64}$/;
const EVENT_ID_RX = /^atlas-event-sha256:[0-9a-f]{64}$/;
const EXECUTION_ID_RX = /^atlas-execution-sha256:[0-9a-f]{64}$/;

function fail(code, detail='') { const error = new Error(detail ? `${code}: ${detail}` : code); error.code = code; throw error; }
function isObject(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function assertClosed(value, required, optional=[], code='INVALID_OBJECT') {
  if (!isObject(value)) fail(code);
  const allowed = new Set([...required, ...optional]);
  for (const key of Object.keys(value)) if (!allowed.has(key)) fail('UNKNOWN_FIELD', key);
  for (const key of required) if (!(key in value)) fail('MISSING_FIELD', key);
}
function assertNonEmptyString(value, code='INVALID_STRING') { if (typeof value !== 'string' || value.length === 0) fail(code); return value; }
function assertCanonicalTimestamp(value) {
  if (typeof value !== 'string' || !TS_RX.test(value)) fail('NON_CANONICAL_TIMESTAMP');
  const millis = Date.parse(value);
  if (!Number.isFinite(millis) || new Date(millis).toISOString() !== value) fail('NON_CANONICAL_TIMESTAMP');
  return value;
}
function compareCodePoints(a,b) {
  const aa=Array.from(a), bb=Array.from(b), n=Math.min(aa.length,bb.length);
  for(let i=0;i<n;i++){const da=aa[i].codePointAt(0),db=bb[i].codePointAt(0);if(da!==db)return da-db;}
  return aa.length-bb.length;
}
function canonicalize(value, stack=new WeakSet()) {
  if (value === undefined || typeof value === 'function' || typeof value === 'symbol' || typeof value === 'bigint') fail('NON_CANONICAL_VALUE');
  if (value === null || typeof value === 'boolean') return value;
  if (typeof value === 'string') return value.normalize('NFC');
  if (typeof value === 'number') {
    if (!Number.isInteger(value) || !Number.isFinite(value) || Object.is(value,-0)) fail('NON_CANONICAL_NUMBER');
    return value;
  }
  if (!value || typeof value !== 'object') fail('NON_CANONICAL_VALUE');
  if (stack.has(value)) fail('CANONICAL_CYCLE');
  stack.add(value);
  let out;
  if (Array.isArray(value)) out=value.map(item=>canonicalize(item,stack));
  else {
    out={};
    const normalizedKeys=[];
    const seenKeys=new Set();
    for (const originalKey of Object.keys(value)) {
      const normalizedKey=originalKey.normalize('NFC');
      if(seenKeys.has(normalizedKey))fail('CANONICAL_KEY_COLLISION',normalizedKey);
      seenKeys.add(normalizedKey);
      normalizedKeys.push({normalizedKey,originalKey});
    }
    normalizedKeys.sort((a,b)=>compareCodePoints(a.normalizedKey,b.normalizedKey));
    for (const {normalizedKey,originalKey} of normalizedKeys) {
      if (value[originalKey] === undefined) fail('NON_CANONICAL_VALUE');
      out[normalizedKey]=canonicalize(value[originalKey],stack);
    }
  }
  stack.delete(value);
  return out;
}
function canonicalJson(value){return JSON.stringify(canonicalize(value));}
function atlasHash(domain,value){return crypto.createHash('sha256').update(Buffer.concat([Buffer.from(domain,'utf8'),Buffer.from([0]),Buffer.from(canonicalJson(value),'utf8')])).digest('hex');}
function withoutIdentity(value,field){const copy={};for(const [key,item] of Object.entries(value))if(key!==field)copy[key]=item;return copy;}
function sortedUnique(values, validator=()=>true) {
  if (!Array.isArray(values) || values.some(v=>!validator(v))) return false;
  if (values.some((v,i)=>i>0 && compareCodePoints(values[i-1],v)>=0)) return false;
  return new Set(values).size===values.length;
}
function canonicalRefKey(ref) {
  assertClosed(ref, ['courseRef'], ['objectiveId','activityLineageId']);
  assertClosed(ref.courseRef, ['packageLineageId','courseLineageId']);
  assertNonEmptyString(ref.courseRef.packageLineageId,'INVALID_COURSE_REF');
  assertNonEmptyString(ref.courseRef.courseLineageId,'INVALID_COURSE_REF');
  const hasObjective=Object.prototype.hasOwnProperty.call(ref,'objectiveId');
  const hasActivity=Object.prototype.hasOwnProperty.call(ref,'activityLineageId');
  if (hasObjective===hasActivity) fail('UNQUALIFIED_REFERENCE');
  const suffix = hasObjective ? `objective:${assertNonEmptyString(ref.objectiveId,'INVALID_OBJECTIVE_REF')}` : `activity:${assertNonEmptyString(ref.activityLineageId,'INVALID_ACTIVITY_REF')}`;
  return `${ref.courseRef.packageLineageId}\u0000${ref.courseRef.courseLineageId}\u0000${suffix}`;
}
function sameRef(a,b) { return canonicalRefKey(a) === canonicalRefKey(b); }
function sameRevision(a,b){return canonicalJson(a)===canonicalJson(b);}
function executionClassForAction(action){
  const executionClass=ACTION_EXECUTION_CLASS[action];
  if(!executionClass)fail('UNKNOWN_ACTION');
  return executionClass;
}
function assertContentRevisionRef(ref){
  assertClosed(ref,['packageLineageId','packageRevisionId','packageDigest']);
  assertNonEmptyString(ref.packageLineageId,'INVALID_CONTENT_REVISION_REF');
  assertNonEmptyString(ref.packageRevisionId,'INVALID_CONTENT_REVISION_REF');
  if(!DIGEST_RX.test(ref.packageDigest))fail('INVALID_CONTENT_REVISION_REF');
  return ref;
}
function executionClassOf(activity) {
  assertClosed(activity,
    ['activityRef','objectiveRef','learningPhase','assessmentRole','estimatedMinutes'],
    ['authorIndex','stimulusDigest']);
  canonicalRefKey(activity.activityRef); canonicalRefKey(activity.objectiveRef);
  if (!Number.isInteger(activity.estimatedMinutes) || activity.estimatedMinutes < 1 || activity.estimatedMinutes > 30) fail('INVALID_ESTIMATED_MINUTES');
  const key = `${activity.learningPhase}|${activity.assessmentRole}`;
  if (['activation|practice','comprehension|practice','application|practice'].includes(key)) return 'practice';
  if (key === 'consolidation|practice') return 'correction';
  if (key === 'validation|validation') return 'validation';
  if (key === 'transfer|practice') return 'transfer';
  if (key === 'diagnostic|diagnostic') return 'diagnostic';
  fail('INVALID_ACTIVITY_CLASSIFICATION', key);
}
function indexActivities(activities, links) {
  if (!Array.isArray(activities) || !Array.isArray(links)) fail('INVALID_CONTENT_REGISTRY');
  const byActivity = new Map();
  for (const activity of activities) {
    const key = canonicalRefKey(activity.activityRef);
    if (byActivity.has(key)) fail('DUPLICATE_ACTIVITY_REF');
    byActivity.set(key, Object.freeze({...activity, executionClass: executionClassOf(activity)}));
  }
  const byObjective = new Map();
  for (const link of links) {
    assertClosed(link, ['objectiveRef','activityRef','authorIndex']);
    if (!Number.isInteger(link.authorIndex) || link.authorIndex < 0) fail('INVALID_AUTHOR_INDEX');
    const activityKey = canonicalRefKey(link.activityRef);
    const activity = byActivity.get(activityKey); if (!activity) fail('UNKNOWN_ACTIVITY_REF');
    if (!sameRef(link.objectiveRef, activity.objectiveRef)) fail('OBJECTIVE_ACTIVITY_MISMATCH');
    const objectiveKey = canonicalRefKey(link.objectiveRef);
    const rows = byObjective.get(objectiveKey) || [];
    rows.push(Object.freeze({...activity, authorIndex: link.authorIndex})); byObjective.set(objectiveKey, rows);
  }
  for (const rows of byObjective.values()) {
    rows.sort((a,b)=>a.authorIndex-b.authorIndex || compareCodePoints(canonicalRefKey(a.activityRef),canonicalRefKey(b.activityRef)));
    rows.forEach((row,index)=>{ if (row.authorIndex !== index) fail('NON_CONTIGUOUS_AUTHOR_INDEX'); });
    Object.freeze(rows);
  }
  return Object.freeze({byActivity, byObjective});
}
function eligibleActivities(index, objectiveRef, action) {
  const desired=executionClassForAction(action);
  return Object.freeze((index.byObjective.get(canonicalRefKey(objectiveRef)) || []).filter(a=>a.executionClass===desired));
}
function assertClaim(claim){
  assertClosed(claim,['claimVersion','claimId','objectiveRef','sourceActivityRef','targetActivityRef','basisCode','sourceStimulusDigest','targetStimulusDigest']);
  if(claim.claimVersion!=='atlas.independence.v1'||!CLAIM_ID_RX.test(claim.claimId))fail('INVALID_CLAIM');
  canonicalRefKey(claim.objectiveRef);canonicalRefKey(claim.sourceActivityRef);canonicalRefKey(claim.targetActivityRef);
  if(!['new-instance','new-context','alternate-representation'].includes(claim.basisCode))fail('INVALID_CLAIM');
  if(!DIGEST_RX.test(claim.sourceStimulusDigest)||!DIGEST_RX.test(claim.targetStimulusDigest))fail('INVALID_CLAIM');
  const expected=`atlas-claim-sha256:${atlasHash('learnit.atlas.m1.v0.3/validation-claim-id',withoutIdentity(claim,'claimId'))}`;
  if(claim.claimId!==expected)fail('CLAIM_ID_INVALID');
  return claim;
}
function assertAcceptedClaimSet(set,{contentRevisionRef,artifactDigest,oracleVersion}){
  assertClosed(set,['schemaVersion','contentRevisionRef','oracleVersion','artifactDigest','acceptedClaimIds']);
  if(set.schemaVersion!=='atlas.accepted-validation-claims.v1')fail('INVALID_ACCEPTED_CLAIM_SET');
  assertContentRevisionRef(set.contentRevisionRef);assertContentRevisionRef(contentRevisionRef);
  if(!sameRevision(set.contentRevisionRef,contentRevisionRef))fail('CLAIM_SET_REVISION_MISMATCH');
  if(typeof oracleVersion!=='string'||oracleVersion.length===0||set.oracleVersion!==oracleVersion)fail('CLAIM_SET_ORACLE_MISMATCH');
  if(!DIGEST_RX.test(artifactDigest)||set.artifactDigest!==artifactDigest)fail('CLAIM_SET_ARTIFACT_MISMATCH');
  if(!sortedUnique(set.acceptedClaimIds,id=>CLAIM_ID_RX.test(id)))fail('CLAIM_SET_NOT_SORTED_UNIQUE');
  return set;
}
function claimIsAccepted({claim, acceptedClaimSet, contentRevisionRef, artifactDigest, oracleVersion, sourceActivityRef, targetActivityRef, objectiveRef}) {
  if (!claim || !acceptedClaimSet) return false;
  try {
    assertClaim(claim);
    assertAcceptedClaimSet(acceptedClaimSet,{contentRevisionRef,artifactDigest,oracleVersion});
    if (!sameRef(claim.objectiveRef, objectiveRef) || !sameRef(claim.sourceActivityRef, sourceActivityRef) || !sameRef(claim.targetActivityRef,targetActivityRef)) return false;
    if (!sameRef(claim.objectiveRef,{courseRef:claim.sourceActivityRef.courseRef,objectiveId:claim.objectiveRef.objectiveId})) return false;
    if (canonicalJson(claim.sourceActivityRef.courseRef)!==canonicalJson(claim.objectiveRef.courseRef)||canonicalJson(claim.targetActivityRef.courseRef)!==canonicalJson(claim.objectiveRef.courseRef)) return false;
    if (sameRef(sourceActivityRef,targetActivityRef) || claim.sourceStimulusDigest===claim.targetStimulusDigest) return false;
    return acceptedClaimSet.acceptedClaimIds.includes(claim.claimId);
  } catch (_) { return false; }
}
function assertExecution(execution){
  assertClosed(execution,['executionVersion','executionId','sessionRef','courseRef','contentRevisionRef','planDigest','itemPosition','submissionOrdinal','objectiveRef','activityRef','action','executionClass','responseDigest','scoringRuleId','scoringRuleDigest','outcome','assistance','assistanceUseIds','submittedAt','scoredAt']);
  if(execution.executionVersion!=='atlas.scored-execution.v1'||!EXECUTION_ID_RX.test(execution.executionId))fail('INVALID_EXECUTION');
  if(!['practice','correction','validation','transfer','diagnostic'].includes(execution.executionClass)||!['correct','incorrect'].includes(execution.outcome)||!['none','used','unknown'].includes(execution.assistance))fail('INVALID_EXECUTION');
  const expectedExecutionClass=executionClassForAction(execution.action);
  if(execution.executionClass!==expectedExecutionClass)fail('ACTION_EXECUTION_CLASS_MISMATCH');
  assertCanonicalTimestamp(execution.submittedAt);assertCanonicalTimestamp(execution.scoredAt);canonicalRefKey(execution.objectiveRef);canonicalRefKey(execution.activityRef);
  return execution;
}
function assertRewardEvent(event){
  if(!isObject(event)||typeof event.kind!=='string')fail('INVALID_REWARD_EVENT');
  if(event.kind==='session-resumed'){
    assertClosed(event,['eventVersion','eventId','eventOrdinal','kind','sessionRef','occurredAt']);
  }else if(event.kind==='activity-attempt'){
    assertClosed(event,['eventVersion','eventId','kind','objectiveRef','executionId','occurredAt']);
    canonicalRefKey(event.objectiveRef);if(!EXECUTION_ID_RX.test(event.executionId))fail('INVALID_REWARD_EVENT');
  }else if(event.kind==='activity-corrected'){
    assertClosed(event,['eventVersion','eventId','kind','objectiveRef','executionId','correctsEventId','occurredAt']);
    canonicalRefKey(event.objectiveRef);if(!EXECUTION_ID_RX.test(event.executionId)||!EVENT_ID_RX.test(event.correctsEventId))fail('INVALID_REWARD_EVENT');
  }else fail('INVALID_REWARD_EVENT');
  if(event.eventVersion!=='atlas.learning-event.v1'||!EVENT_ID_RX.test(event.eventId))fail('INVALID_REWARD_EVENT');
  assertCanonicalTimestamp(event.occurredAt);return event;
}
function maintenanceEligibility({now, evidence, basisExecution, basisEvent, targetActivity, claim, acceptedClaimSet, contentRevisionRef, artifactDigest, oracleVersion}) {
  assertCanonicalTimestamp(now);
  if (!evidence || evidence.state !== 'validated-recently' || !basisExecution || !basisEvent) return {eligible:false, reason:'NO_INDEPENDENT_VALIDATION'};
  assertExecution(basisExecution);
  assertRewardEvent(basisEvent);
  if (basisExecution.executionClass !== 'validation' || basisExecution.outcome !== 'correct' || basisExecution.assistance !== 'none') return {eligible:false, reason:'NO_INDEPENDENT_VALIDATION'};
  if (basisEvent.kind !== 'activity-attempt') fail('INVALID_MAINTENANCE_BASIS_EVENT');
  if (basisEvent.executionId !== basisExecution.executionId) fail('MAINTENANCE_BASIS_EXECUTION_MISMATCH');
  if (!sameRef(basisEvent.objectiveRef,basisExecution.objectiveRef) || !sameRef(evidence.objectiveRef,basisExecution.objectiveRef)) fail('MAINTENANCE_BASIS_OBJECTIVE_MISMATCH');
  if (basisEvent.occurredAt !== basisExecution.scoredAt) fail('MAINTENANCE_BASIS_TIME_MISMATCH');
  const elapsed = Date.parse(now)-Date.parse(basisExecution.scoredAt);
  if (!Number.isFinite(elapsed) || elapsed < 24*60*60*1000) return {eligible:false, reason:'RECENTLY_VALIDATED'};
  const accepted = claimIsAccepted({claim,acceptedClaimSet,contentRevisionRef,artifactDigest,oracleVersion,sourceActivityRef:basisExecution.activityRef,targetActivityRef:targetActivity.activityRef,objectiveRef:evidence.objectiveRef});
  return accepted ? {eligible:true, claimId:claim.claimId, validationBasisEventId:basisEvent.eventId} : {eligible:false, reason:'NO_INDEPENDENT_VALIDATION'};
}
function projectRewards({learningEvents,scoredExecutions}, ruleVersion='atlas.learning.reward.v1') {
  if (!Array.isArray(learningEvents)||!Array.isArray(scoredExecutions)||typeof ruleVersion!=='string'||!ruleVersion) fail('INVALID_FACTS');
  const executions=new Map();
  for(const execution of scoredExecutions){assertExecution(execution);if(executions.has(execution.executionId))fail('DUPLICATE_EXECUTION_ID');executions.set(execution.executionId,execution);}
  const candidates=[];
  const eventIds=new Set();
  for(const event of learningEvents){
    assertRewardEvent(event);
    if(eventIds.has(event.eventId))fail('DUPLICATE_EVENT_ID');
    eventIds.add(event.eventId);
    let kind=null,objectiveRef=null;
    if(event.kind==='session-resumed')kind='resumed-after-interruption';
    else {
      const execution=executions.get(event.executionId);if(!execution)fail('MISSING_EXECUTION');
      if(canonicalJson(execution.objectiveRef)!==canonicalJson(event.objectiveRef))fail('EVENT_EXECUTION_OBJECTIVE_MISMATCH');
      objectiveRef=event.objectiveRef;
      if(event.kind==='activity-corrected'){
        if(execution.executionClass!=='correction'||execution.outcome!=='correct')continue;
        kind='correction-completed';
      }else if(execution.executionClass==='validation'&&execution.outcome==='correct'&&execution.assistance==='none'){
        kind=execution.action==='maintain-recent-validation'?'validation-reconfirmed':'validation-completed';
      }else if(execution.executionClass==='practice'&&execution.outcome==='correct'&&execution.assistance==='none')kind='independent-success';
    }
    if(kind)candidates.push({event,kind,objectiveRef,priority:REWARD_PRIORITY.indexOf(kind)});
  }
  candidates.sort((a,b)=>a.priority-b.priority||compareCodePoints(a.event.occurredAt,b.event.occurredAt)||compareCodePoints(a.event.eventId,b.event.eventId));
  const output=[];
  for(const {event,kind,objectiveRef} of candidates){
    const payload={ruleVersion,kind,labelCode:LABEL_BY_REWARD[kind],objectiveRef:objectiveRef||null,evidenceEventIds:[event.eventId],occurredAt:event.occurredAt};
    const rewardId=`atlas-reward-sha256:${atlasHash('learnit.atlas.m1.v0.3/reward-id',payload)}`;
    output.push(Object.freeze({ruleVersion,rewardId,...payload}));
  }
  return Object.freeze(output);
}

module.exports = Object.freeze({REASON_CODES,REWARD_PRIORITY,ACTION_EXECUTION_CLASS,canonicalize,canonicalJson,atlasHash,canonicalRefKey,sameRef,executionClassForAction,executionClassOf,indexActivities,eligibleActivities,assertClaim,assertAcceptedClaimSet,claimIsAccepted,maintenanceEligibility,projectRewards});
