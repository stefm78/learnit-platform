(function(){
  'use strict';

  const schema='learnit.mastery_evidence_model.rc675.v1';
  const STATUS=Object.freeze({
    NOT_STARTED:'not-started',
    DISCOVERED:'discovered',
    IN_PROGRESS:'in-progress',
    FRAGILE:'fragile',
    CONSOLIDATED:'consolidated'
  });
  const STATUS_LABELS=Object.freeze({
    [STATUS.NOT_STARTED]:'Non commencé',
    [STATUS.DISCOVERED]:'Découvert',
    [STATUS.IN_PROGRESS]:'En cours',
    [STATUS.FRAGILE]:'Fragile',
    [STATUS.CONSOLIDATED]:'Consolidé'
  });

  function arr(value){return Array.isArray(value)?value:[];}
  function obj(value){return value&&typeof value==='object'?value:{};}
  function text(value){return String(value||'').trim();}
  function number(value,fallback=0){const n=Number(value);return Number.isFinite(n)?n:fallback;}
  function parseTime(value){const ms=Date.parse(text(value));return Number.isFinite(ms)?ms:null;}
  function nowMs(value){if(typeof value==='number'&&Number.isFinite(value))return value;return parseTime(value)||Date.now();}
  function normalizeObjective(value){
    return text(value||'Objectif non renseigné').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').trim()||'objectif non renseigne';
  }
  function courseId(course){
    const collectionModel=typeof window!=='undefined'&&window.LearnItCourseCollectionModel;
    return text(course&&course.id)||(collectionModel&&collectionModel.courseId?collectionModel.courseId(course):text(course&&course.title||'course').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,''));
  }
  function progressFor(stateOrProgress,id){
    const root=obj(stateOrProgress);
    if(root.activityProgressByCourseId)return obj(root.activityProgressByCourseId[id]);
    return root;
  }
  function historyOf(row){
    const source=arr(row&&row.attemptHistory);
    if(source.length)return source.map(item=>({correct:!!item.correct,at:text(item.at),mode:text(item.mode)}));
    if(row&&(row.seen||number(row.attempts)>0||typeof row.correct==='boolean'))return [{correct:!!row.correct,at:text(row.lastAt),mode:text(row.lastMode)}];
    return [];
  }
  function successfulTiming(history){
    const times=arr(history).filter(item=>item&&item.correct).map(item=>parseTime(item.at)).filter(ms=>ms!==null).sort((a,b)=>a-b);
    const days=new Set(times.map(ms=>new Date(ms).toISOString().slice(0,10)));
    const spanHours=times.length>=2?Math.max(0,(times[times.length-1]-times[0])/36e5):0;
    return {days:days.size,count:times.length,spanHours:Math.round(spanHours*10)/10};
  }
  function dueEvidence(row,current){
    const dueAt=text(row&&row.nextReviewAt);
    const dueMs=parseTime(dueAt);
    const immediate=!!(row&&row.review);
    const scheduled=dueMs!==null&&dueMs<=current;
    return {due:immediate||scheduled,reason:immediate?'error':(scheduled?'scheduled':(dueAt?'future':'none')),dueAt,overdueHours:scheduled?Math.max(0,Math.floor((current-dueMs)/36e5)):0};
  }
  function activityEvidence(activity,row,now){
    const r=obj(row);const history=historyOf(r);const current=nowMs(now);
    const attempts=Math.max(number(r.attempts),history.length);
    const successes=Math.max(number(r.successCount),history.filter(item=>item.correct).length,(!history.length&&r.correct===true)?1:0);
    const failures=Math.max(number(r.failureCount),history.filter(item=>!item.correct).length,(!history.length&&r.correct===false&&attempts)?1:0);
    const seen=!!(r.seen||attempts>0||history.length||typeof r.correct==='boolean');
    const timing=successfulTiming(history);
    const successDays=timing.days;
    const successfulSpanHours=timing.spanHours;
    const spacingThresholdHours=24;
    const reviewLevel=Math.max(0,number(r.reviewLevel));
    const due=dueEvidence(r,current);
    const fragile=seen&&!!(r.review||r.recurringError||number(r.failureStreak)>0||r.correct===false||(failures>=2&&failures>=successes));
    const repeatedSuccess=successes>=2;
    const spacedSuccess=timing.count>=2&&successDays>=2&&successfulSpanHours>=spacingThresholdHours;
    const spacingReason=spacedSuccess?'two-success-days-and-24h-span':(timing.count<2?'insufficient-timestamped-successes':(successDays<2?'same-day-successes':(successfulSpanHours<spacingThresholdHours?'span-under-24h':'not-spaced')));
    let status=STATUS.NOT_STARTED;
    if(seen){
      if(fragile)status=STATUS.FRAGILE;
      else if(repeatedSuccess&&spacedSuccess&&!due.due)status=STATUS.CONSOLIDATED;
      else if(successes>0)status=STATUS.IN_PROGRESS;
      else status=STATUS.DISCOVERED;
    }
    const evidence=Object.freeze({
      exposure:seen,
      attempts,
      successes,
      failures,
      successDays,
      repeatedSuccess,
      spacedSuccess,
      successfulSpanHours,
      spacingThresholdHours,
      spacingReason,
      reviewLevel,
      due:due.due,
      dueReason:due.reason,
      dueAt:due.dueAt,
      overdueHours:due.overdueHours,
      fragile,
      status,
      statusLabel:STATUS_LABELS[status],
      lastAt:text(r.lastAt),
      objective:text(activity&&activity.objective||activity&&activity.question||'Objectif non renseigné')
    });
    return evidence;
  }
  function aggregateStatus(rows){
    const values=arr(rows);
    if(!values.length||values.every(row=>row.status===STATUS.NOT_STARTED))return STATUS.NOT_STARTED;
    if(values.some(row=>row.status===STATUS.FRAGILE))return STATUS.FRAGILE;
    const exposed=values.filter(row=>row.status!==STATUS.NOT_STARTED);
    if(exposed.length===values.length&&values.every(row=>row.status===STATUS.CONSOLIDATED))return STATUS.CONSOLIDATED;
    if(values.some(row=>row.successes>0||row.status===STATUS.IN_PROGRESS||row.status===STATUS.CONSOLIDATED))return STATUS.IN_PROGRESS;
    return STATUS.DISCOVERED;
  }
  function summarizeRows(rows){
    const values=arr(rows);const status=aggregateStatus(values);
    return Object.freeze({
      status,
      statusLabel:STATUS_LABELS[status],
      total:values.length,
      exposed:values.filter(row=>row.exposure).length,
      attempted:values.filter(row=>row.attempts>0).length,
      succeeded:values.filter(row=>row.successes>0).length,
      fragile:values.filter(row=>row.fragile).length,
      due:values.filter(row=>row.due).length,
      consolidated:values.filter(row=>row.status===STATUS.CONSOLIDATED).length,
      attempts:values.reduce((sum,row)=>sum+row.attempts,0),
      successes:values.reduce((sum,row)=>sum+row.successes,0),
      failures:values.reduce((sum,row)=>sum+row.failures,0)
    });
  }
  function objectiveEvidence(course,stateOrProgress,now){
    const id=courseId(course);const progress=progressFor(stateOrProgress,id);const groups=new Map();
    for(const activity of arr(course&&course.activities)){
      const key=normalizeObjective(activity&&activity.objective||activity&&activity.question);
      if(!groups.has(key))groups.set(key,{key,label:text(activity&&activity.objective||activity&&activity.question||'Objectif non renseigné'),activityIds:[],rows:[]});
      const group=groups.get(key);group.activityIds.push(text(activity&&activity.id));group.rows.push(activityEvidence(activity,progress[text(activity&&activity.id)],now));
    }
    return [...groups.values()].map(group=>Object.freeze({key:group.key,label:group.label,activityIds:Object.freeze(group.activityIds.slice()),...summarizeRows(group.rows),activities:Object.freeze(group.rows.slice())})).sort((a,b)=>a.key.localeCompare(b.key,'fr'));
  }
  function chapterDefinitions(course){
    const activities=arr(course&&course.activities);const explicit=arr(course&&course.chapters);
    if(explicit.length)return explicit.map((chapter,index)=>({id:text(chapter&&chapter.id)||`chapter-${index+1}`,title:text(chapter&&chapter.title)||`Chapitre ${index+1}`,ids:arr(chapter&&chapter.ids||chapter&&chapter.activityIds).map(text).filter(Boolean)}));
    const labelled=activities.filter(activity=>text(activity&&activity.chapter||activity&&activity.section));
    if(labelled.length){
      const groups=new Map();
      for(const activity of activities){
        const label=text(activity&&activity.chapter||activity&&activity.section)||'Autres activités';
        if(!groups.has(label))groups.set(label,[]);
        groups.get(label).push(text(activity&&activity.id));
      }
      return [...groups.entries()].map(([title,ids],index)=>({id:`chapter-${index+1}`,title,ids}));
    }
    if(!activities.length)return [];
    const objectives=arr(course&&course.objectives).filter(Boolean);
    const count=Math.min(5,Math.max(3,objectives.length||Math.ceil(activities.length/2)));
    const size=Math.ceil(activities.length/count);const chapters=[];
    for(let index=0;index<activities.length;index+=size){
      const group=activities.slice(index,index+size);const chapterIndex=chapters.length;
      chapters.push({id:`chapter-${chapterIndex+1}`,title:text(objectives[chapterIndex]||group[0]&&group[0].objective)||`Chapitre ${chapterIndex+1}`,ids:group.map(activity=>text(activity&&activity.id)).filter(Boolean)});
    }
    return chapters;
  }
  function chapterEvidence(course,stateOrProgress,now){
    const id=courseId(course);const progress=progressFor(stateOrProgress,id);const byId=new Map(arr(course&&course.activities).map(activity=>[text(activity&&activity.id),activity]));
    return chapterDefinitions(course).map(chapter=>{
      const rows=chapter.ids.map(activityId=>byId.get(activityId)).filter(Boolean).map(activity=>activityEvidence(activity,progress[text(activity.id)],now));
      return Object.freeze({id:chapter.id,title:chapter.title,activityIds:Object.freeze(chapter.ids.slice()),...summarizeRows(rows)});
    });
  }
  function courseEvidence(course,stateOrProgress,now){
    const id=courseId(course);const progress=progressFor(stateOrProgress,id);const rows=arr(course&&course.activities).map(activity=>activityEvidence(activity,progress[text(activity&&activity.id)],now));
    const objectives=objectiveEvidence(course,stateOrProgress,now);const chapters=chapterEvidence(course,stateOrProgress,now);const summary=summarizeRows(rows);
    return Object.freeze({courseId:id,title:text(course&&course.title)||'Parcours',...summary,objectives:Object.freeze(objectives),chapters:Object.freeze(chapters),activities:Object.freeze(rows)});
  }
  function recommendation(courseSummary){
    const summary=obj(courseSummary);const objectives=arr(summary.objectives);
    const fragile=objectives.filter(row=>row.status===STATUS.FRAGILE);const due=objectives.filter(row=>row.due>0);const unseen=objectives.filter(row=>row.status===STATUS.NOT_STARTED);const active=objectives.filter(row=>row.status===STATUS.IN_PROGRESS||row.status===STATUS.DISCOVERED);
    if(fragile.length)return Object.freeze({action:'review',label:'Revoir les points fragiles',reasonCode:'fragile-objectives',reason:`${fragile.length} objectif${fragile.length>1?'s':''} présente${fragile.length>1?'nt':''} des erreurs ou une réussite instable.`,objectiveKeys:Object.freeze(fragile.map(row=>row.key))});
    if(due.length)return Object.freeze({action:'review',label:'Commencer la révision',reasonCode:'scheduled-review-due',reason:`${due.length} objectif${due.length>1?'s sont':' est'} arrivé${due.length>1?'s':''} à échéance de révision.`,objectiveKeys:Object.freeze(due.map(row=>row.key))});
    if(summary.status===STATUS.NOT_STARTED)return Object.freeze({action:'discover',label:'Découvrir ce parcours',reasonCode:'no-evidence-yet',reason:'Aucune preuve d’exposition ou de réussite n’est encore enregistrée.',objectiveKeys:Object.freeze(unseen.map(row=>row.key))});
    if(active.length||unseen.length)return Object.freeze({action:'continue',label:'Continuer l’entraînement',reasonCode:'evidence-in-progress',reason:`${summary.succeeded||0} activité${summary.succeeded>1?'s':''} réussie${summary.succeeded>1?'s':''}, mais les preuves ne sont pas encore suffisamment répétées et espacées.`,objectiveKeys:Object.freeze(active.concat(unseen).map(row=>row.key))});
    return Object.freeze({action:'validate',label:'Vérifier la consolidation',reasonCode:'all-objectives-consolidated',reason:'Tous les objectifs disposent de réussites répétées et espacées, sans fragilité active.',objectiveKeys:Object.freeze(objectives.map(row=>row.key))});
  }
  function explainCourse(course,stateOrProgress,now){const summary=courseEvidence(course,stateOrProgress,now);return Object.freeze({...summary,recommendation:recommendation(summary)});}
  function statusLabel(status){return STATUS_LABELS[status]||STATUS_LABELS[STATUS.NOT_STARTED];}
  function audit(){
    const course={id:'c1',title:'Test',sequence:'Séquence',activities:[{id:'a1',objective:'Comprendre U'},{id:'a2',objective:'Comprendre U'},{id:'a3',objective:'Mesurer I'}]};
    const progress={a1:{seen:true,correct:true,attempts:2,successCount:2,reviewLevel:2,nextReviewAt:'2099-01-01T00:00:00Z',attemptHistory:[{correct:true,at:'2026-01-01T00:00:00Z'},{correct:true,at:'2026-01-03T00:00:00Z'}]},a2:{seen:true,correct:false,review:true,attempts:2,failureCount:2,attemptHistory:[{correct:false,at:'2026-01-02T00:00:00Z'}]}};
    const summary=explainCourse(course,progress,'2026-01-04T00:00:00Z');
    return {schema,ok:summary.objectives.length===2&&summary.status===STATUS.FRAGILE&&summary.recommendation.reasonCode==='fragile-objectives'&&summary.chapters.length===3,summary};
  }

  window.LearnItMasteryEvidenceModel=Object.freeze({schema,STATUS,statusLabel,normalizeObjective,activityEvidence,objectiveEvidence,chapterDefinitions,chapterEvidence,courseEvidence,recommendation,explainCourse,audit});
})();
