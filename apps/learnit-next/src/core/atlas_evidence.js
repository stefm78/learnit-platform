'use strict';

const REASON_CODES = Object.freeze([
  'NEW_OBJECTIVE','PRACTICE_IN_PROGRESS','RECENT_ERROR','REVIEW_REQUIRED',
  'CORRECTION_COMPLETED','NO_INDEPENDENT_VALIDATION','VALIDATION_AVAILABLE',
  'RECENTLY_VALIDATED','SESSION_TIME_LIMIT'
]);
const REWARD_PRIORITY = Object.freeze([
  'validation-reconfirmed','validation-completed','correction-completed',
  'independent-success','resumed-after-interruption'
]);

function fail(code, detail='') { const error = new Error(detail ? `${code}: ${detail}` : code); error.code = code; throw error; }
function isObject(value) { return value && typeof value === 'object' && !Array.isArray(value); }
function assertClosed(value, required, optional=[], code='INVALID_OBJECT') {
  if (!isObject(value)) fail(code);
  const allowed = new Set([...required, ...optional]);
  for (const key of Object.keys(value)) if (!allowed.has(key)) fail('UNKNOWN_FIELD', key);
  for (const key of required) if (!(key in value)) fail('MISSING_FIELD', key);
}
function canonicalRefKey(ref) {
  assertClosed(ref, ['courseRef'], ['objectiveId','activityLineageId']);
  assertClosed(ref.courseRef, ['packageLineageId','courseLineageId']);
  const suffix = ref.objectiveId ? `objective:${ref.objectiveId}` : ref.activityLineageId ? `activity:${ref.activityLineageId}` : fail('UNQUALIFIED_REFERENCE');
  return `${ref.courseRef.packageLineageId}\u0000${ref.courseRef.courseLineageId}\u0000${suffix}`;
}
function sameRef(a,b) { return canonicalRefKey(a) === canonicalRefKey(b); }
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
    byActivity.set(key, {...activity, executionClass: executionClassOf(activity)});
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
    rows.push({...activity, authorIndex: link.authorIndex}); byObjective.set(objectiveKey, rows);
  }
  for (const rows of byObjective.values()) {
    rows.sort((a,b)=>a.authorIndex-b.authorIndex || canonicalRefKey(a.activityRef).localeCompare(canonicalRefKey(b.activityRef)));
    rows.forEach((row,index)=>{ if (row.authorIndex !== index) fail('NON_CONTIGUOUS_AUTHOR_INDEX'); });
  }
  return Object.freeze({byActivity, byObjective});
}
function eligibleActivities(index, objectiveRef, action) {
  const desired = ({'start-practice':'practice','continue-practice':'practice','correct-practice':'correction','attempt-validation':'validation','maintain-recent-validation':'validation'})[action];
  if (!desired) fail('UNKNOWN_ACTION');
  return (index.byObjective.get(canonicalRefKey(objectiveRef)) || []).filter(a=>a.executionClass===desired);
}
function claimIsAccepted({claim, acceptedClaimSet, contentRevisionRef, artifactDigest, sourceActivityRef, targetActivityRef, objectiveRef}) {
  if (!claim || !acceptedClaimSet) return false;
  try {
    assertClosed(claim,['claimId','objectiveRef','sourceActivityRef','targetActivityRef','basisCode','sourceStimulusDigest','targetStimulusDigest']);
    if (!['new-instance','new-context','alternate-representation'].includes(claim.basisCode)) return false;
    if (!sameRef(claim.objectiveRef, objectiveRef) || !sameRef(claim.sourceActivityRef, sourceActivityRef) || !sameRef(claim.targetActivityRef,targetActivityRef)) return false;
    if (sameRef(sourceActivityRef,targetActivityRef) || claim.sourceStimulusDigest===claim.targetStimulusDigest) return false;
    if (acceptedClaimSet.schemaVersion !== 'atlas.accepted-validation-claims.v1') return false;
    if (acceptedClaimSet.artifactDigest !== artifactDigest) return false;
    if (JSON.stringify(acceptedClaimSet.contentRevisionRef) !== JSON.stringify(contentRevisionRef)) return false;
    return Array.isArray(acceptedClaimSet.acceptedClaimIds) && acceptedClaimSet.acceptedClaimIds.includes(claim.claimId);
  } catch (_) { return false; }
}
function maintenanceEligibility({now, evidence, basisExecution, targetActivity, claim, acceptedClaimSet, contentRevisionRef, artifactDigest}) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(now)) fail('NON_CANONICAL_TIMESTAMP');
  if (!evidence || evidence.state !== 'validated-recently' || !basisExecution || basisExecution.outcome !== 'correct' || basisExecution.assistance !== 'none') return {eligible:false, reason:'NO_INDEPENDENT_VALIDATION'};
  const elapsed = Date.parse(now)-Date.parse(basisExecution.scoredAt);
  if (!Number.isFinite(elapsed) || elapsed < 24*60*60*1000) return {eligible:false, reason:'RECENTLY_VALIDATED'};
  const accepted = claimIsAccepted({claim,acceptedClaimSet,contentRevisionRef,artifactDigest,sourceActivityRef:basisExecution.activityRef,targetActivityRef:targetActivity.activityRef,objectiveRef:evidence.objectiveRef});
  return accepted ? {eligible:true, claimId:claim.claimId, validationBasisEventId:basisExecution.eventId} : {eligible:false, reason:'NO_INDEPENDENT_VALIDATION'};
}
function projectRewards(facts, ruleVersion='atlas.learning.reward.v1') {
  if (!Array.isArray(facts)) fail('INVALID_FACTS');
  const allocated = new Set(); const output=[];
  const candidates=[];
  for (const fact of facts) {
    assertClosed(fact,['eventId','kind','occurredAt'],['objectiveRef','outcome','assistance','isMaintenance','isCorrection','isResume','validation']);
    let kind=null;
    if (fact.kind==='activity-attempt' && fact.outcome==='correct' && fact.assistance==='none') kind=fact.isMaintenance?'validation-reconfirmed':fact.isCorrection?null:(fact.objectiveRef && fact.validation===true?'validation-completed':'independent-success');
    if (fact.kind==='activity-corrected' && fact.outcome==='correct') kind='correction-completed';
    if (fact.kind==='session-resumed') kind='resumed-after-interruption';
    if (kind) candidates.push({fact,kind,priority:REWARD_PRIORITY.indexOf(kind)});
  }
  candidates.sort((a,b)=>a.priority-b.priority || a.fact.occurredAt.localeCompare(b.fact.occurredAt) || a.fact.eventId.localeCompare(b.fact.eventId));
  for (const {fact,kind} of candidates) {
    if (allocated.has(fact.eventId)) continue; allocated.add(fact.eventId);
    output.push(Object.freeze({ruleVersion,rewardId:`pending:${kind}:${fact.eventId}`,kind,labelCode:`reward.${kind.replaceAll('-','_')}`,objectiveRef:fact.objectiveRef||null,evidenceEventIds:[fact.eventId],occurredAt:fact.occurredAt}));
  }
  return Object.freeze(output);
}

module.exports = Object.freeze({REASON_CODES,REWARD_PRIORITY,canonicalRefKey,sameRef,executionClassOf,indexActivities,eligibleActivities,claimIsAccepted,maintenanceEligibility,projectRewards});
