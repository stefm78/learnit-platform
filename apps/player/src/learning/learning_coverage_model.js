(function(global){
  'use strict';

  const schema='learnit.learning_coverage_model.rc698.v1';
  const LEVELS=Object.freeze(['recall','comprehension','application','transfer']);
  const LEVEL_LABELS=Object.freeze({recall:'Rappel',comprehension:'Compréhension',application:'Application',transfer:'Transfert'});
  const PHASE_TO_LEVEL=Object.freeze({
    activation:'recall',
    comprehension:'comprehension',
    application:'application',
    consolidation:'application',
    remediation:'application',
    diagnostic:'application',
    validation:'application',
    transfer:'transfer'
  });
  const ASSESSMENT_ROLES=Object.freeze(['diagnostic','validation']);

  function arr(value){return Array.isArray(value)?value:[];}
  function text(value){return String(value===undefined||value===null?'':value).trim();}
  function normalize(value){return text(value).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'objectif';}
  function count(rows,key){return rows.reduce((out,row)=>{const value=text(row&&row[key])||'unspecified';out[value]=(out[value]||0)+1;return out;},{});}
  function frozenObject(value){return Object.freeze({...value});}
  function levelFor(activity){
    const phase=text(activity&&activity.learning_phase||activity&&activity.learningPhase).toLowerCase();
    if(activity&&activity.transfer_probe===true)return 'transfer';
    return PHASE_TO_LEVEL[phase]||'';
  }
  function isAssessment(activity){return ASSESSMENT_ROLES.includes(text(activity&&activity.assessment_role||activity&&activity.assessmentRole).toLowerCase());}
  function isTransferProbe(activity){return levelFor(activity)==='transfer'&&(activity&&activity.transfer_probe===true||text(activity&&activity.learning_phase).toLowerCase()==='transfer');}
  function transferStrength(activity){
    if(!isTransferProbe(activity))return 'none';
    const distance=text(activity&&activity.transfer_distance).toLowerCase();
    if(distance==='far')return 'far';
    if(distance==='near')return 'near';
    return 'declared';
  }
  function objectiveRows(course){
    const groups=new Map();
    for(const activity of arr(course&&course.activities)){
      const label=text(activity&&activity.objective||activity&&activity.question)||'Objectif non renseigné';
      const key=normalize(label);
      if(!groups.has(key))groups.set(key,{key,label,activities:[]});
      groups.get(key).activities.push(activity);
    }
    return [...groups.values()].sort((a,b)=>a.key.localeCompare(b.key,'fr'));
  }
  function objectiveCoverage(group){
    const activities=arr(group&&group.activities);
    const levels={recall:0,comprehension:0,application:0,transfer:0};
    const assessedLevels={recall:0,comprehension:0,application:0,transfer:0};
    for(const activity of activities){const level=levelFor(activity);if(level){levels[level]+=1;if(isAssessment(activity))assessedLevels[level]+=1;}}
    const transferRows=activities.filter(isTransferProbe);
    const farTransfer=transferRows.filter(activity=>transferStrength(activity)==='far').length;
    const nearTransfer=transferRows.filter(activity=>transferStrength(activity)==='near').length;
    const declaredTransfer=transferRows.length-farTransfer-nearTransfer;
    const roles=count(activities,'assessment_role');
    const phases=count(activities,'learning_phase');
    const types=count(activities,'type');
    const gaps=[];
    if(!levels.recall&&!levels.comprehension)gaps.push('foundation-evidence-missing');
    if(!levels.application)gaps.push('application-evidence-missing');
    if(!levels.transfer)gaps.push('transfer-evidence-missing');
    if(!assessedLevels.application&&!assessedLevels.transfer)gaps.push('higher-order-assessment-missing');
    if(!roles.diagnostic)gaps.push('diagnostic-role-missing');
    if(!roles.validation)gaps.push('validation-role-missing');
    if(levels.transfer&&!farTransfer)gaps.push('far-transfer-probe-missing');
    const status=gaps.length===0?'complete':(levels.application&&levels.transfer?'partial':'insufficient');
    const highestLevel=LEVELS.slice().reverse().find(level=>levels[level]>0)||'none';
    return Object.freeze({
      schema,
      key:text(group&&group.key)||normalize(group&&group.label),
      label:text(group&&group.label)||'Objectif',
      activityCount:activities.length,
      levels:frozenObject(levels),
      assessedLevels:frozenObject(assessedLevels),
      phases:frozenObject(phases),
      assessmentRoles:frozenObject(roles),
      activityTypes:frozenObject(types),
      transfer:Object.freeze({total:transferRows.length,near:nearTransfer,far:farTransfer,declared:declaredTransfer}),
      highestLevel,
      status,
      gaps:Object.freeze(gaps),
      activityIds:Object.freeze(activities.map(activity=>text(activity&&activity.id)).filter(Boolean))
    });
  }
  function courseCoverage(course){
    const objectives=objectiveRows(course).map(objectiveCoverage);
    const gapCounts={};for(const row of objectives)for(const gap of row.gaps)gapCounts[gap]=(gapCounts[gap]||0)+1;
    const complete=objectives.filter(row=>row.status==='complete').length;
    const partial=objectives.filter(row=>row.status==='partial').length;
    const insufficient=objectives.filter(row=>row.status==='insufficient').length;
    const transferProbes=arr(course&&course.activities).filter(isTransferProbe);
    return Object.freeze({
      schema,
      courseId:text(course&&course.id||course&&course.contentVersion||course&&course.title)||'course',
      title:text(course&&course.title)||'Parcours',
      objectiveCount:objectives.length,
      objectives:Object.freeze(objectives),
      statuses:Object.freeze({complete,partial,insufficient}),
      transfer:Object.freeze({total:transferProbes.length,near:transferProbes.filter(a=>transferStrength(a)==='near').length,far:transferProbes.filter(a=>transferStrength(a)==='far').length,declared:transferProbes.filter(a=>transferStrength(a)==='declared').length}),
      gapCounts:frozenObject(gapCounts),
      readyForHumanTransferProbe:objectives.length>0&&insufficient===0&&objectives.every(row=>row.levels.transfer>0&&row.assessmentRoles.validation>0),
      completeForAuthoring:objectives.length>0&&complete===objectives.length
    });
  }
  function packageCoverage(payload){
    const courses=arr(payload&&payload.courses).length?arr(payload.courses):[payload];
    const rows=courses.filter(Boolean).map(courseCoverage);
    return Object.freeze({schema,courseCount:rows.length,courses:Object.freeze(rows),readyForHumanTransferProbe:rows.length>0&&rows.every(row=>row.readyForHumanTransferProbe),completeForAuthoring:rows.length>0&&rows.every(row=>row.completeForAuthoring)});
  }
  function audit(){
    const course={title:'Audit',activities:[
      {id:'r',type:'flashcard',objective:'Résoudre',learning_phase:'activation',assessment_role:'practice'},
      {id:'c',type:'qcm',objective:'Résoudre',learning_phase:'comprehension',assessment_role:'diagnostic'},
      {id:'a',type:'fill',objective:'Résoudre',learning_phase:'application',assessment_role:'practice'},
      {id:'t',type:'qcm',objective:'Résoudre',learning_phase:'transfer',assessment_role:'validation',transfer_probe:true,transfer_distance:'far',variant_of:'a'}
    ]};
    const report=courseCoverage(course);const row=report.objectives[0];
    return {schema,ok:report.completeForAuthoring&&report.readyForHumanTransferProbe&&row.highestLevel==='transfer'&&row.transfer.far===1&&row.gaps.length===0,report};
  }

  const api=Object.freeze({schema,LEVELS,LEVEL_LABELS,PHASE_TO_LEVEL,levelFor,isAssessment,isTransferProbe,transferStrength,objectiveRows,objectiveCoverage,courseCoverage,packageCoverage,audit});
  global.LearnItLearningCoverageModel=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
