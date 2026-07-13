(function(){
  'use strict';
  const schema='learnit.action_intent_model.rc693.v2';
  function normalizeSummary(summary){
    const s=summary||{};
    return {action:String(s.action||''),reviewCount:Number(s.reviewCount||0),hasAny:!!s.hasAny,seen:Number(s.seen||0),total:Number(s.total||0),mastery:Number(s.mastery||0),exposure:Number(s.exposure||0),evidenceStatus:String(s.evidenceStatus||''),consolidated:s.consolidated===true,nextAction:s.nextAction&&typeof s.nextAction==='object'?s.nextAction:null};
  }
  function courseAction(summary){
    const s=normalizeSummary(summary);const model=window.LearnItNextActionModel;const rec=s.nextAction||(model&&typeof model.recommendationFromSummary==='function'?model.recommendationFromSummary(s):null);
    if(rec){return {kind:rec.action==='discover'?'start':rec.action,mode:rec.mode,primaryLabel:rec.label,secondaryMode:rec.secondary&&rec.secondary.mode,secondaryLabel:rec.secondary&&rec.secondary.label,signal:s.reviewCount?`${s.reviewCount} à revoir`:(!s.hasAny?'Non commencé':`${s.seen}/${Math.max(1,s.total)} vues`),headline:rec.headline,userText:rec.reason,reasonCode:rec.reasonCode};}
    if(s.reviewCount>0)return {kind:'review',mode:'review',primaryLabel:'Commencer la révision',signal:`${s.reviewCount} à revoir`,headline:'Reprenez les points fragiles',userText:`${s.reviewCount} activité${s.reviewCount>1?'s sont':' est'} à revoir avant de poursuivre.`};
    if(!s.hasAny)return {kind:'start',mode:'discovery',primaryLabel:'Découvrir ce parcours',secondaryMode:'diagnostic',secondaryLabel:'Évaluer mon niveau',signal:'Non commencé',headline:'Commencez par découvrir le parcours',userText:'Sujet nouveau : découvrez pas à pas. Vous le connaissez déjà : commencez par un diagnostic court.'};
    if(s.total>0&&s.exposure>=100&&s.mastery>=80)return {kind:'validate',mode:'validation',primaryLabel:'Lancer une validation',signal:`${s.mastery}%`,headline:'Vérifiez votre maîtrise',userText:'Vous avez vu et réussi l’essentiel ; confirmez votre niveau sans indice.'};
    return {kind:'continue',mode:'training',primaryLabel:'Continuer le parcours',signal:`${s.seen}/${Math.max(1,s.total)} vues`,headline:'Continuez votre entraînement',userText:'Reprenez avec correction immédiate et droit à l’erreur.'};
  }
  function exportLabel(type){return ({content:'Contenu',imports:'Imports',bilan:'Bilan',remediation:'Reprise ciblée',history:'Historique import'})[type]||'Exporter';}
  function audit(){
    const a=courseAction({reviewCount:2,hasAny:true,total:4,seen:2,mastery:50,exposure:50});
    const b=courseAction({reviewCount:0,hasAny:false,total:4,seen:0,mastery:0,exposure:0});
    const c=courseAction({reviewCount:0,hasAny:true,total:4,seen:4,mastery:100,exposure:100});
    const d=courseAction({reviewCount:0,hasAny:true,total:4,seen:4,mastery:100,exposure:100,evidenceStatus:'consolidated'});
    return {schema,ok:a.mode==='review'&&b.mode==='discovery'&&b.secondaryMode==='diagnostic'&&c.mode==='training'&&d.mode==='validation'&&exportLabel('history')==='Historique import',samples:[a,b,c,d]};
  }
  window.LearnItActionIntentModel=Object.freeze({schema,courseAction,exportLabel,audit});
})();
