(function(){
  'use strict';
  const schema='learnit.bilan_information_architecture.rc696.v1';
  function arr(value){return Array.isArray(value)?value:[];}
  function obj(value){return value&&typeof value==='object'&&!Array.isArray(value)?value:{};}
  function plan(evidence,recommendation,lastBilan){
    const e=obj(evidence);const rec=obj(recommendation);const last=obj(lastBilan);const assessmentMode=String(last.mode||last.modePolicy&&last.modePolicy.id||'');const hasAssessment=['diagnostic','validation'].includes(assessmentMode)&&!!(last.modeOutcome||last.total);
    const primaryMetrics=e.status==='not-started'?['status']:['status','exposure','success','fragility'];
    const secondaryMetrics=['exposure','success','fragility','status','due','export'];
    const visibleSections=['next-action'];if(hasAssessment)visibleSections.unshift('assessment-outcome');visibleSections.push('course-navigation','evidence-summary');if(e.status==='fragile')visibleSections.push('evidence-structure');
    return Object.freeze({schema,primaryActionCount:1,secondaryActionCount:rec.secondary?1:0,showAssessmentOutcome:hasAssessment,showBoundary:e.status==='not-started',openStructure:e.status==='fragile',primaryMetrics:Object.freeze(primaryMetrics),secondaryMetrics:Object.freeze(secondaryMetrics),visibleSections:Object.freeze(visibleSections),collapsedSections:Object.freeze(['evidence-structure','secondary-evidence-options'].filter(section=>section!=='evidence-structure'||e.status!=='fragile')),decisionFirst:true,duplicatePrimaryActions:false});
  }
  function audit(value){const p=obj(value);const visible=arr(p.visibleSections);return {schema,ok:p.primaryActionCount===1&&p.secondaryActionCount<=1&&visible[0]&&['assessment-outcome','next-action'].includes(visible[0])&&p.duplicatePrimaryActions===false,checks:{onePrimary:p.primaryActionCount===1,oneSecondaryMaximum:p.secondaryActionCount<=1,decisionFirst:p.decisionFirst===true,noDuplicatePrimary:p.duplicatePrimaryActions===false}};}
  function selfTest(){const a=plan({status:'not-started'},{secondary:{mode:'diagnostic'}},null);const b=plan({status:'fragile'},{secondary:null},{mode:'validation',total:2,modeOutcome:{}});return {schema,ok:a.showBoundary&&a.secondaryActionCount===1&&!a.openStructure&&b.showAssessmentOutcome&&b.openStructure&&audit(b).ok,samples:{a,b}};}
  window.LearnItBilanInformationArchitecture=Object.freeze({schema,plan,audit,selfTest});
})();
