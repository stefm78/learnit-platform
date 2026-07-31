'use strict';
const T=require('./atlas_today.js');
function fail(code){const e=new Error(code);e.code=code;throw e;}
function validateResumeState(resumeState,itemCount){
 if(!resumeState||typeof resumeState!=='object'||Array.isArray(resumeState))fail('INVALID_RESUME_STATE');
 const required=['nextItemPosition'],optional=['focusTarget','sessionRef','courseRef','contentRevisionRef','planDigest','lastCommittedEventId','responseDraft','lifecycleOrdinal','itemStates','resumeVersion'];const allowed=new Set([...required,...optional]);for(const key of Object.keys(resumeState))if(!allowed.has(key))fail('UNKNOWN_FIELD');
 if(!Number.isInteger(resumeState.nextItemPosition)||resumeState.nextItemPosition<0||resumeState.nextItemPosition>itemCount)fail('INVALID_RESUME_STATE');if('focusTarget'in resumeState&&typeof resumeState.focusTarget!=='string')fail('INVALID_RESUME_STATE');return resumeState;
}
function createSessionController({core,focus}){if(!core||typeof core.commitActivitySubmission!=='function'||typeof core.requestAssistance!=='function')throw new Error('CORE_PORT_REQUIRED');let state={sessionId:null,itemPosition:0,committed:null,help:null};return Object.freeze({
 start(sessionRef,resumeState){if(!sessionRef||typeof sessionRef.sessionId!=='string')fail('INVALID_SESSION_REF');const next=resumeState?.nextItemPosition??0;if(!Number.isInteger(next)||next<0)fail('INVALID_RESUME_STATE');state={sessionId:sessionRef.sessionId,itemPosition:next,committed:null,help:null};if(resumeState?.focusTarget)focus?.(resumeState.focusTarget);return {...state};},
 async submit(rawResponse){const result=await core.commitActivitySubmission(state.sessionId,state.itemPosition,rawResponse);if(!result||!result.event||!result.resumeState)throw new Error('CORE_COMMIT_NOT_CONFIRMED');state.committed=result;state.itemPosition=result.resumeState.nextItemPosition;if(result.resumeState.focusTarget)focus?.(result.resumeState.focusTarget);return result;},
 async requestHelp(kind){const confirmation=await core.requestAssistance(state.sessionId,state.itemPosition,kind);if(!confirmation||confirmation.committed!==true)throw new Error('ASSISTANCE_NOT_PERSISTED');state.help=confirmation.record;return confirmation;},
 snapshot(){return structuredClone(state);}
 });}
function renderSession({plan,resumeState,activityHtml='',feedbackHtml=''}){
 T.validatePlan(plan);validateResumeState(resumeState||{nextItemPosition:0},plan.payload.items.length);const pos=resumeState?.nextItemPosition??0;
 if(!plan.payload.items.length)return '<section class="atlas-m1"><h1>Aucune séance en cours</h1></section>';
 if(pos===plan.payload.items.length)return '<section class="atlas-m1 atlas-session atlas-session-complete" aria-labelledby="atlas-session-title"><h1 id="atlas-session-title" tabindex="-1">Séance terminée</h1><p>Les réponses ont été enregistrées. Consultez le bilan des preuves.</p><div class="atlas-actions"><button class="atlas-primary" type="button" data-atlas-summary>Voir le bilan</button></div></section>';
 const item=plan.payload.items[pos],labels={practice:'Entraînement',correction:'Correction',validation:item.action==='maintain-recent-validation'?'Reconfirmation':'Validation'};
 return `<section class="atlas-m1 atlas-session" aria-labelledby="atlas-session-title"><header><p>${T.esc(labels[item.executionClass]||'Activité')}</p><h1 id="atlas-session-title">Étape ${item.position+1} sur ${plan.payload.items.length}</h1></header><div class="atlas-activity" id="atlas-session-item-${item.position}">${activityHtml}</div>${feedbackHtml}<div class="atlas-actions"><button type="button" data-atlas-help="hint">Indice</button><button class="atlas-primary" type="button" data-atlas-submit>Valider la réponse</button></div></section>`;
}
module.exports=Object.freeze({validateResumeState,createSessionController,renderSession});
