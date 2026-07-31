'use strict';
const E=require('./atlas_events.js');
function key(ref){return E.canonicalJson(ref);}
function empty(ref){return {evidenceVersion:'atlas.objective-evidence.v1',objectiveRef:ref,practiceAttempts:0,correctionsCompleted:0,validationAttempts:0,latestPracticeCorrect:null,latestValidationCorrect:null,lastValidationAt:null,lastEvidenceAt:null,state:'not-started'};}
function projectObjectiveEvidence(learningEvents,scoredExecutions,isValidationAdmissible=(execution)=>execution.assistance==='none'&&['attempt-validation','maintain-recent-validation'].includes(execution.action)){
 if(!Array.isArray(learningEvents)||!Array.isArray(scoredExecutions)||typeof isValidationAdmissible!=='function')E.fail('INVALID_PROJECTION_INPUT');
 const executions=new Map();for(const x of scoredExecutions){E.validateScoredExecution(x);if(executions.has(x.executionId))E.fail('DUPLICATE_EXECUTION_ID');executions.set(x.executionId,x);}
 const result=new Map(),latestIncorrect=new Map(),corrected=new Set();
 const pedagogical=learningEvents.filter(e=>e.kind==='activity-attempt'||e.kind==='activity-corrected').map(E.validatePedagogicalEvent).sort((a,b)=>a.occurredAt.localeCompare(b.occurredAt)||a.eventId.localeCompare(b.eventId));
 for(const event of pedagogical){const k=key(event.objectiveRef),row=result.get(k)||empty(event.objectiveRef),execution=executions.get(event.executionId);if(!execution)E.fail('MISSING_EXECUTION');if(key(execution.objectiveRef)!==k)E.fail('EVENT_EXECUTION_OBJECTIVE_MISMATCH');row.lastEvidenceAt=!row.lastEvidenceAt||event.occurredAt>row.lastEvidenceAt?event.occurredAt:row.lastEvidenceAt;
   if(event.kind==='activity-corrected'){if(execution.executionClass!=='correction')E.fail('EVENT_EXECUTION_CLASS_MISMATCH');row.correctionsCompleted++;corrected.add(event.correctsEventId);}
   else if(execution.executionClass==='practice'){row.practiceAttempts++;row.latestPracticeCorrect=execution.outcome==='correct';if(execution.outcome==='incorrect')latestIncorrect.set(k,event.eventId);}
   else if(execution.executionClass==='validation'){row.validationAttempts++;row.latestValidationCorrect=execution.outcome==='correct';const credit=execution.outcome==='correct'&&execution.assistance==='none'&&isValidationAdmissible(execution,event)===true;if(credit){row.lastValidationAt=execution.scoredAt;row.state='validated-recently';}else if(execution.outcome==='incorrect'){row.state='review-needed';}}
   result.set(k,row);
 }
 for(const [k,row] of result){const unresolved=latestIncorrect.get(k)&&!corrected.has(latestIncorrect.get(k));if(unresolved)row.state='review-needed';else if(row.state==='not-started'){if(row.latestPracticeCorrect===true&&row.practiceAttempts>0)row.state='ready-for-validation';else if(row.practiceAttempts||row.correctionsCompleted)row.state='training';}E.deepFreeze(row);}
 return [...result.values()].sort((a,b)=>key(a.objectiveRef).localeCompare(key(b.objectiveRef)));
}
module.exports=Object.freeze({projectObjectiveEvidence});
