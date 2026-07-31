'use strict';
const E = require('./atlas_evidence.js');
function fail(code){const e=new Error(code);e.code=code;throw e;}
function lastSelectionStats(objectiveRef, startedEvents) {
  const key=E.canonicalRefKey(objectiveRef); const accepted=(startedEvents||[]).filter(e=>e.kind==='session-started');
  let lastSelectedAt=null; let recentCount=0;
  accepted.forEach((event,index)=>{
    const selected=(event.selectedItems||[]).some(item=>E.sameRef(item.objectiveRef,objectiveRef));
    if(selected){if(!lastSelectedAt || event.occurredAt>lastSelectedAt) lastSelectedAt=event.occurredAt; if(index>=Math.max(0,accepted.length-10)) recentCount++;}
  });
  return {lastSelectedAt,recentCount,key};
}
function rankRecommendations(rows, startedEvents=[]) {
  return [...rows].sort((a,b)=>{
    const unresolvedA=a.evidence.state==='review-needed'?0:1, unresolvedB=b.evidence.state==='review-needed'?0:1;
    if(unresolvedA!==unresolvedB)return unresolvedA-unresolvedB;
    const A=lastSelectionStats(a.objectiveRef,startedEvents),B=lastSelectionStats(b.objectiveRef,startedEvents);
    if(A.lastSelectedAt!==B.lastSelectedAt)return (A.lastSelectedAt||'').localeCompare(B.lastSelectedAt||'');
    if(A.recentCount!==B.recentCount)return A.recentCount-B.recentCount;
    return A.key.localeCompare(B.key);
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
function buildRecommendation({objectiveRef,evidence,index,context={}}) {
  const [action,reasonCodes]=actionForEvidence(evidence,context);
  const eligible=E.eligibleActivities(index,objectiveRef,action);
  if(!eligible.length) fail('NO_ELIGIBLE_ACTIVITY');
  const preferred=eligible[0];
  return Object.freeze({recommendationVersion:'atlas.recommendation.v1',objectiveRef,action,eligibleActivityRefs:Object.freeze(eligible.map(x=>x.activityRef)),preferredActivityRef:preferred.activityRef,estimatedMinutes:preferred.estimatedMinutes,reasonCodes:Object.freeze([...new Set(reasonCodes)])});
}
module.exports=Object.freeze({lastSelectionStats,rankRecommendations,actionForEvidence,buildRecommendation});
