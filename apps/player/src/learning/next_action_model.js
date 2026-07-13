(function(){
  'use strict';

  const schema='learnit.next_action_model.rc693.v1';
  const ACTIONS=Object.freeze({
    discovery:Object.freeze({action:'discover',mode:'discovery',intent:'discovery',label:'Découvrir ce parcours',headline:'Commencez par les bases'}),
    training:Object.freeze({action:'continue',mode:'training',intent:'training',label:'Continuer le parcours',headline:'Continuez votre entraînement'}),
    review:Object.freeze({action:'review',mode:'review',intent:'review',label:'Commencer la révision',headline:'Reprenez les points fragiles'}),
    validation:Object.freeze({action:'validate',mode:'validation',intent:'validation',label:'Lancer une validation',headline:'Vérifiez votre maîtrise'}),
    diagnostic:Object.freeze({action:'diagnose',mode:'diagnostic',intent:'diagnostic',label:'Évaluer rapidement mon niveau',headline:'Situez votre niveau'}),
    resume:Object.freeze({action:'resume',mode:'training',intent:'resume',label:'Reprendre la séance',headline:'Continuez là où vous en étiez'})
  });

  function arr(value){return Array.isArray(value)?value:[];}
  function obj(value){return value&&typeof value==='object'&&!Array.isArray(value)?value:{};}
  function text(value){return String(value===undefined||value===null?'':value).trim();}
  function clone(value){return JSON.parse(JSON.stringify(value));}
  function courseId(course){return text(course&&course.id)||text(course&&course.title).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'course';}
  function progressFor(progressOrState,id){const root=obj(progressOrState);if(root.activityProgressByCourseId)return obj(root.activityProgressByCourseId[id]);return root;}
  function activeSession(session){return !!(session&&session.status==='active');}
  function assessment(lastBilan){
    const last=obj(lastBilan);const mode=text(last.mode||last.modePolicy&&last.modePolicy.id);if(!['diagnostic','validation'].includes(mode))return null;
    const outcome=obj(last.modeOutcome);const total=Math.max(0,Number(outcome.total!==undefined?outcome.total:last.total)||0);const correct=Math.max(0,Number(outcome.correct!==undefined?outcome.correct:last.correct)||0);const reviewCount=Math.max(0,Number(outcome.reviewCount!==undefined?outcome.reviewCount:arr(last.review).length)||0);const pct=total?Math.round(correct*100/total):0;
    const rows=arr(last.assessmentEvidence).map(row=>({id:text(row.id),objective:text(row.objective)||'Objectif',objectiveKey:text(row.objectiveKey)||text(row.objective).toLowerCase(),correct:!!row.correct,role:text(row.role),type:text(row.type)}));
    const objectiveRows=arr(last.objectiveAssessment).map(row=>({key:text(row.key),label:text(row.label)||'Objectif',total:Math.max(0,Number(row.total)||0),correct:Math.max(0,Number(row.correct)||0),incorrect:Math.max(0,Number(row.incorrect)||0),status:text(row.status)}));
    return {mode,total,correct,reviewCount,pct,passed:total>0&&reviewCount===0,rows,objectiveRows,completedAt:text(last.completedAt),contentVersion:text(last.contentVersion)};
  }
  function evidence(course,progress,now){
    const model=window.LearnItMasteryEvidenceModel;const id=courseId(course);const p=progressFor(progress,id);
    if(model&&typeof model.explainCourse==='function')return model.explainCourse({...obj(course),id},p,now);
    const activities=arr(course&&course.activities);const rows=activities.map(activity=>obj(p[text(activity.id)]));const exposed=rows.filter(row=>row.seen||row.attempts).length;const succeeded=rows.filter(row=>row.correct).length;const fragile=rows.filter(row=>row.review||row.correct===false).length;const total=activities.length;const status=fragile?'fragile':(exposed?(exposed>=total&&succeeded>=total?'consolidated':'in-progress'):'not-started');
    return {courseId:id,title:text(course&&course.title)||'Parcours',status,total,exposed,succeeded,fragile,due:fragile,objectives:[],recommendation:null};
  }
  function base(kind,overrides={}){return Object.freeze({...clone(ACTIONS[kind]||ACTIONS.training),schema,state:kind,reasonCode:`${kind}-default`,reason:'',secondary:null,confidence:'medium',objectiveKeys:Object.freeze([]),assessment:null,evidence:null,...overrides});}
  function secondary(kind,label,detail){const a=ACTIONS[kind]||ACTIONS.training;return Object.freeze({intent:a.intent,mode:a.mode,label:label||a.label,detail:detail||''});}
  function recommendationFromSummary(summary){
    const s=obj(summary);if(s.nextAction&&typeof s.nextAction==='object')return s.nextAction;
    const reviewCount=Math.max(0,Number(s.reviewCount)||0);const total=Math.max(0,Number(s.total)||0);const seen=Math.max(0,Number(s.seen)||0);const hasAny=!!s.hasAny;const consolidated=s.consolidated===true||text(s.evidenceStatus)==='consolidated'||text(s.status)==='consolidated';
    if(reviewCount>0)return base('review',{state:'review',reasonCode:'fragile-activities',reason:`${reviewCount} activité${reviewCount>1?'s sont':' est'} à reprendre.`,confidence:'high'});
    if(!hasAny)return base('discovery',{state:'new',reasonCode:'no-evidence-yet',reason:'Aucune activité n’est encore enregistrée.',secondary:secondary('diagnostic','Évaluer rapidement mon niveau','À choisir si le sujet est déjà familier.'),confidence:'high'});
    if(total>0&&consolidated)return base('validation',{state:'ready-to-validate',reasonCode:'all-objectives-consolidated',reason:'Les preuves disponibles sont répétées et espacées.',secondary:secondary('training','Encore m’entraîner','Refaire une série avec correction immédiate.'),confidence:'high'});
    return base('training',{state:'in-progress',reasonCode:'evidence-in-progress',reason:`${seen}/${Math.max(1,total)} activité${total>1?'s':''} vue${seen>1?'s':''}, mais les preuves doivent encore être répétées et espacées.`,secondary:secondary('diagnostic','Faire un diagnostic court','Mesurer le niveau actuel sans modifier la progression.'),confidence:'medium'});
  }
  function recommend(course,progress,session,lastBilan,options={}){
    const id=courseId(course);const p=progressFor(progress,id);const e=evidence(course,p,options.now);const assess=assessment(lastBilan);
    if(activeSession(session)){
      const currentMode=text(session.mode)||'training';const policy=window.LearnItSessionModeModel&&window.LearnItSessionModeModel.resolve?window.LearnItSessionModeModel.resolve(currentMode):{id:currentMode,label:'séance'};const total=arr(session.queue).length;const index=Math.max(0,Number(session.currentIndex)||0);
      return base('resume',{mode:policy.id||currentMode,state:'active',reasonCode:'active-session',reason:`Votre séance ${text(policy.label).toLowerCase()||'en cours'} est en cours${total?` · activité ${Math.min(index+1,total)}/${total}`:''}.`,confidence:'high',assessment:assess,evidence:e});
    }
    if(assess&&assess.mode==='diagnostic'){
      const weakKeys=assess.objectiveRows.filter(row=>row.status!=='strong').map(row=>row.key);
      if(assess.total>0&&assess.pct>=80&&assess.reviewCount===0){return base('training',{state:'diagnostic-strong',label:'Approfondir directement',headline:'Votre diagnostic montre des bases solides',reasonCode:'diagnostic-strong',reason:`${assess.correct}/${assess.total} réponses correctes. Commencez par les objectifs non encore vérifiés ou les activités d’application.`,secondary:secondary('discovery','Revoir les bases','Parcourir malgré tout la découverte guidée.'),confidence:'high',objectiveKeys:Object.freeze(weakKeys),assessment:assess,evidence:e,adaptive:true});}
      if(assess.total>0&&assess.pct>=50){return base('training',{state:'diagnostic-mixed',label:'Travailler les points ciblés',headline:'Votre diagnostic révèle un niveau intermédiaire',reasonCode:'diagnostic-mixed',reason:`${assess.correct}/${assess.total} réponses correctes. La suite cible d’abord les objectifs fragiles ou non évalués.`,secondary:secondary('discovery','Reprendre pas à pas','Revenir à une découverte complète.'),confidence:'high',objectiveKeys:Object.freeze(weakKeys),assessment:assess,evidence:e,adaptive:true});}
      if(assess.total>0){return base('discovery',{state:'diagnostic-foundations',label:'Découvrir les bases',headline:'Commencez par consolider les fondations',reasonCode:'diagnostic-foundations',reason:`${assess.correct}/${assess.total} réponses correctes. Une découverte guidée est recommandée avant l’entraînement.`,secondary:secondary('training','M’entraîner quand même','Commencer directement une série avec correction immédiate.'),confidence:'high',objectiveKeys:Object.freeze(weakKeys),assessment:assess,evidence:e,adaptive:true});}
    }
    if(assess&&assess.mode==='validation'){
      if(!assess.passed)return base('review',{state:'validation-fragile',reasonCode:'validation-errors',reason:`La validation laisse ${assess.reviewCount} point${assess.reviewCount>1?'s':''} à reprendre.`,secondary:secondary('training','Continuer l’entraînement','Pratiquer librement avant une nouvelle validation.'),confidence:'high',objectiveKeys:Object.freeze(assess.objectiveRows.filter(row=>row.incorrect>0).map(row=>row.key)),assessment:assess,evidence:e});
      return base('training',{state:'validation-passed',label:'Consolider dans le temps',headline:'Validation réussie',reasonCode:'validation-passed',reason:`${assess.correct}/${assess.total} réponses correctes. Continuez par une nouvelle série ou revenez lors de la prochaine échéance de révision.`,secondary:null,confidence:'high',assessment:assess,evidence:e});
    }
    const fragileObjectives=arr(e.objectives).filter(row=>row.status==='fragile');const dueObjectives=arr(e.objectives).filter(row=>Number(row.due||0)>0);
    if(fragileObjectives.length||Number(e.fragile||0)>0)return base('review',{state:'review',reasonCode:'fragile-objectives',reason:`${fragileObjectives.length||Number(e.fragile||0)} objectif${(fragileObjectives.length||Number(e.fragile||0))>1?'s présentent':' présente'} des erreurs ou une réussite instable.`,secondary:secondary('training','Continuer quand même','Poursuivre sans être bloqué par les révisions.'),confidence:'high',objectiveKeys:Object.freeze(fragileObjectives.map(row=>row.key)),assessment:assess,evidence:e});
    if(dueObjectives.length||Number(e.due||0)>0)return base('review',{state:'review-due',reasonCode:'scheduled-review-due',reason:`${dueObjectives.length||Number(e.due||0)} objectif${(dueObjectives.length||Number(e.due||0))>1?'s sont':' est'} arrivé${(dueObjectives.length||Number(e.due||0))>1?'s':''} à échéance de révision.`,secondary:secondary('training','Continuer quand même','Poursuivre sans attendre la révision.'),confidence:'high',objectiveKeys:Object.freeze(dueObjectives.map(row=>row.key)),assessment:assess,evidence:e});
    if(e.status==='not-started')return base('discovery',{state:'new',reasonCode:'no-evidence-yet',reason:'Aucune preuve d’exposition ou de réussite n’est encore enregistrée.',secondary:secondary('diagnostic','Évaluer rapidement mon niveau','À choisir si le sujet est déjà familier ; la progression reste inchangée.'),confidence:'high',objectiveKeys:Object.freeze(arr(e.objectives).map(row=>row.key)),assessment:assess,evidence:e});
    if(e.status==='consolidated')return base('validation',{state:'ready-to-validate',reasonCode:'all-objectives-consolidated',reason:'Tous les objectifs disposent de réussites répétées et espacées, sans fragilité active.',secondary:secondary('training','Encore m’entraîner','Refaire une série avec correction immédiate.'),confidence:'high',objectiveKeys:Object.freeze(arr(e.objectives).map(row=>row.key)),assessment:assess,evidence:e});
    return base('training',{state:'in-progress',reasonCode:'evidence-in-progress',reason:`${Number(e.succeeded||0)} activité${Number(e.succeeded||0)>1?'s':''} réussie${Number(e.succeeded||0)>1?'s':''}, mais les preuves doivent encore être répétées et espacées.`,secondary:secondary('diagnostic','Faire un diagnostic court','Mesurer votre niveau actuel sans modifier la progression.'),confidence:'medium',objectiveKeys:Object.freeze(arr(e.objectives).filter(row=>row.status!=='consolidated').map(row=>row.key)),assessment:assess,evidence:e});
  }
  function sessionOptions(recommendation,lastBilan){const rec=obj(recommendation);const assess=assessment(lastBilan);return {sourceRecommendationCode:text(rec.reasonCode),adaptive:!!rec.adaptive,objectiveKeys:arr(rec.objectiveKeys),assessmentEvidence:assess?assess.rows:[],objectiveAssessment:assess?assess.objectiveRows:[]};}
  function audit(){
    const course={id:'c',title:'Cours',activities:[{id:'a1',objective:'O1'},{id:'a2',objective:'O2'}]};
    const fresh=recommend(course,{},null,null);const active=recommend(course,{}, {status:'active',mode:'training',currentIndex:0,queue:['a1']},null);const diagnostic=recommend(course,{},null,{mode:'diagnostic',total:2,correct:1,review:['a2'],assessmentEvidence:[{id:'a1',objective:'O1',correct:true},{id:'a2',objective:'O2',correct:false}],objectiveAssessment:[{key:'o1',label:'O1',total:1,correct:1,incorrect:0,status:'strong'},{key:'o2',label:'O2',total:1,correct:0,incorrect:1,status:'fragile'}]});
    return {schema,ok:fresh.reasonCode==='no-evidence-yet'&&fresh.secondary&&fresh.secondary.mode==='diagnostic'&&active.reasonCode==='active-session'&&diagnostic.reasonCode==='diagnostic-mixed'&&diagnostic.objectiveKeys.includes('o2'),samples:{fresh,active,diagnostic}};
  }

  window.LearnItNextActionModel=Object.freeze({schema,ACTIONS,assessment,evidence,recommend,recommendationFromSummary,sessionOptions,audit});
})();
