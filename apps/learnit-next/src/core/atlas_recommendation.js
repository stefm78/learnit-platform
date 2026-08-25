'use strict';
const E = require('./atlas_evidence.js');
function fail(code){const e=new Error(code);e.code=code;throw e;}
function compareCanonicalCodePoints(a,b){
  if(typeof a!=='string'||typeof b!=='string')fail('INVALID_CANONICAL_STRING');
  if(a.normalize('NFC')!==a||b.normalize('NFC')!==b)fail('NON_CANONICAL_STRING');
  const aa=Array.from(a),bb=Array.from(b),n=Math.min(aa.length,bb.length);
  for(let i=0;i<n;i++){
    const ac=aa[i].codePointAt(0),bc=bb[i].codePointAt(0);
    if(ac!==bc)return ac<bc?-1:1;
  }
  return aa.length===bb.length?0:(aa.length<bb.length?-1:1);
}
function compareStartedEvents(a,b){
  const byTime=compareCanonicalCodePoints(a.occurredAt,b.occurredAt);
  return byTime || compareCanonicalCodePoints(a.eventId,b.eventId);
}
function lastSelectionStats(objectiveRef, startedEvents=[]) {
  const key=E.canonicalRefKey(objectiveRef);
  const accepted=(startedEvents||[])
    .filter(event=>event.kind==='session-started')
    .slice()
    .sort(compareStartedEvents);
  const selectedEvents=accepted.filter(event=>(event.selectedItems||[]).some(item=>E.sameRef(item.objectiveRef,objectiveRef)));
  const recentAccepted=accepted.slice(Math.max(0,accepted.length-10));
  const recentCount=recentAccepted.filter(event=>(event.selectedItems||[]).some(item=>E.sameRef(item.objectiveRef,objectiveRef))).length;
  const lastSelectedAt=selectedEvents.length ? selectedEvents[selectedEvents.length-1].occurredAt : null;
  return {lastSelectedAt,recentCount,key};
}
function rankRecommendations(rows, startedEvents=[]) {
  return [...rows].sort((a,b)=>{
    const unresolvedA=a.evidence.state==='review-needed'?0:1, unresolvedB=b.evidence.state==='review-needed'?0:1;
    if(unresolvedA!==unresolvedB)return unresolvedA-unresolvedB;
    const A=lastSelectionStats(a.objectiveRef,startedEvents),B=lastSelectionStats(b.objectiveRef,startedEvents);
    if(A.lastSelectedAt!==B.lastSelectedAt)return compareCanonicalCodePoints(A.lastSelectedAt||'',B.lastSelectedAt||'');
    if(A.recentCount!==B.recentCount)return A.recentCount-B.recentCount;
    return compareCanonicalCodePoints(A.key,B.key);
  });
}
function actionForEvidence(evidence, context={}) {
  switch(evidence.state){
    case 'not-started': return ['start-practice',['NEW_OBJECTIVE']];
    case 'training': return ['continue-practice',['PRACTICE_IN_PROGRESS']];
    case 'review-needed': return ['correct-practice',['RECENT_ERROR','REVIEW_REQUIRED']];
    case 'ready-for-validation': return context.hasAcceptedValidation ? ['attempt-validation',['VALIDATION_AVAILABLE']] : ['continue-practice',['NO_INDEPENDENT_VALIDATION']];
    case 'validated-recently': return context.maintenanceEligible ? ['maintain-recent-validation',['RECENTLY_VALIDATED','VALIDATION_AVAILABLE']] : ['continue-practice',['RECENTLY_VALIDATED']];
    default: fail('UNKNOWN_EVIDENCE_STATE');
  }
}
function filterAcceptedTargets(eligible, context) {
  if (!Object.prototype.hasOwnProperty.call(context, 'acceptedTargetActivityRefs')) return eligible;
  if (!Array.isArray(context.acceptedTargetActivityRefs)) fail('INVALID_ACCEPTED_TARGETS');
  const acceptedKeys=new Set(context.acceptedTargetActivityRefs.map(ref=>E.canonicalRefKey(ref)));
  return eligible.filter(activity=>acceptedKeys.has(E.canonicalRefKey(activity.activityRef)));
}
function buildRecommendation({objectiveRef,evidence,index,context={}}) {
  const [action,reasonCodes]=actionForEvidence(evidence,context);
  const eligible=filterAcceptedTargets(E.eligibleActivities(index,objectiveRef,action),context);
  if(!eligible.length) fail('NO_ELIGIBLE_ACTIVITY');
  const preferred=eligible[0];
  return Object.freeze({recommendationVersion:'atlas.recommendation.v1',objectiveRef,action,eligibleActivityRefs:Object.freeze(eligible.map(x=>x.activityRef)),preferredActivityRef:preferred.activityRef,estimatedMinutes:preferred.estimatedMinutes,reasonCodes:Object.freeze([...new Set(reasonCodes)])});
}
module.exports=Object.freeze({lastSelectionStats,rankRecommendations,actionForEvidence,filterAcceptedTargets,buildRecommendation});
