'use strict';
const {esc,assertClosed,objectiveKey}=require('./atlas_today.js');
const LABELS=Object.freeze({'correction-completed':'Correction effectuée','independent-success':'Réussite autonome','validation-completed':'Validation autonome enregistrée','validation-reconfirmed':'Validation autonome reconfirmée','resumed-after-interruption':'Séance reprise'});
const LABEL_CODES=Object.freeze({'correction-completed':'reward.correction_completed','independent-success':'reward.independent_success','validation-completed':'reward.validation_completed','validation-reconfirmed':'reward.validation_reconfirmed','resumed-after-interruption':'reward.resumed_after_interruption'});
const TS=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
function validateSignal(signal){
 assertClosed(signal,['ruleVersion','rewardId','kind','labelCode','objectiveRef','evidenceEventIds','occurredAt']);
 if(typeof signal.ruleVersion!=='string'||!signal.ruleVersion||!/^atlas-reward-sha256:[0-9a-f]{64}$/.test(signal.rewardId)||!LABELS[signal.kind]||signal.labelCode!==LABEL_CODES[signal.kind]||!TS.test(signal.occurredAt)||new Date(Date.parse(signal.occurredAt)).toISOString()!==signal.occurredAt)throw new Error('INVALID_REWARD_SIGNAL');
 if(signal.objectiveRef===null){if(signal.kind!=='resumed-after-interruption')throw new Error('INVALID_REWARD_SIGNAL');}else objectiveKey(signal.objectiveRef);
 if(!Array.isArray(signal.evidenceEventIds)||!signal.evidenceEventIds.length||signal.evidenceEventIds.some(x=>!/^atlas-event-sha256:[0-9a-f]{64}$/.test(x))||signal.evidenceEventIds.some((x,i)=>i>0&&signal.evidenceEventIds[i-1]>=x)||new Set(signal.evidenceEventIds).size!==signal.evidenceEventIds.length)throw new Error('INVALID_REWARD_SIGNAL');return signal;
}
function renderRewards(signals){if(!Array.isArray(signals))throw new Error('INVALID_REWARD_SIGNALS');return `<section class="atlas-m1 atlas-rewards" aria-label="Repères pédagogiques"><ul>${signals.map(s=>{validateSignal(s);return `<li data-reward-id="${esc(s.rewardId)}"><strong>${esc(LABELS[s.kind])}</strong><span>${esc(s.occurredAt)}</span></li>`;}).join('')}</ul></section>`;}
module.exports=Object.freeze({LABELS,LABEL_CODES,validateSignal,renderRewards});
