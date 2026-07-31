'use strict';
const {canonicalJson}=require('./atlas_events.js');
function key(ref){return canonicalJson(ref);}
function empty(ref){return {evidenceVersion:'atlas.objective-evidence.v1',objectiveRef:ref,practiceAttempts:0,correctionsCompleted:0,validationAttempts:0,latestPracticeCorrect:null,latestValidationCorrect:null,lastValidationAt:null,lastEvidenceAt:null,state:'not-started'};}
function projectObjectiveEvidence(learningEvents,scoredExecutions){
 const executions=new Map(scoredExecutions.map(x=>[x.executionId,x]));const result=new Map();const latestIncorrect=new Map(),corrected=new Set();
 const pedagogical=learningEvents.filter(e=>e.kind==='activity-attempt'||e.kind==='activity-corrected').sort((a,b)=>a.occurredAt.localeCompare(b.occurredAt)||a.eventId.localeCompare(b.eventId));
 for(const event of pedagogical){const k=key(event.objectiveRef), row=result.get(k)||empty(event.objectiveRef), execution=executions.get(event.executionId);if(!execution)throw Object.assign(new Error('MISSING_EXECUTION'),{code:'MISSING_EXECUTION'});row.lastEvidenceAt=!row.lastEvidenceAt||event.occurredAt>row.lastEvidenceAt?event.occurredAt:row.lastEvidenceAt;
   if(event.kind==='activity-corrected'){row.correctionsCompleted++;corrected.add(event.correctsEventId);}
   else if(execution.executionClass==='practice'){row.practiceAttempts++;row.latestPracticeCorrect=execution.outcome==='correct';if(execution.outcome==='incorrect')latestIncorrect.set(k,event.eventId);}
   else if(execution.executionClass==='validation'){row.validationAttempts++;row.latestValidationCorrect=execution.outcome==='correct';const credit=execution.outcome==='correct'&&execution.assistance==='none'&&execution.validationAdmissible===true;if(credit){row.lastValidationAt=execution.scoredAt;row.state='validated-recently';}else if(execution.outcome==='incorrect'){row.state='review-needed';}}
   result.set(k,row);
 }
 for(const [k,row] of result){const unresolved=latestIncorrect.get(k)&&!corrected.has(latestIncorrect.get(k));if(unresolved)row.state='review-needed';else if(row.state==='not-started'){if(row.latestPracticeCorrect===true&&row.practiceAttempts>0)row.state='ready-for-validation';else if(row.practiceAttempts||row.correctionsCompleted)row.state='training';}Object.freeze(row);}
 return [...result.values()].sort((a,b)=>key(a.objectiveRef).localeCompare(key(b.objectiveRef)));
}
module.exports=Object.freeze({projectObjectiveEvidence});
