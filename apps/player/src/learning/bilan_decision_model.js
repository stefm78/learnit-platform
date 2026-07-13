(function(){
  'use strict';
  const schema='learnit.bilan_decision_model.rc693.v2';
  function pct(n,d){return Math.round((Number(n)||0)/Math.max(1,Number(d)||0)*100);}
  function safeArray(v){return Array.isArray(v)?v:[];}
  function activityIds(course){return safeArray(course&&course.activities).map(a=>String(a.id));}
  function courseTitle(course){return String(course&&course.title||'Parcours');}
  function collectionTitle(collection){return String(collection&&collection.title||'Collection');}
  function courseState(state,courseId){
    const id=String(courseId||'');
    const progress=(state&&state.activityProgressByCourseId&&state.activityProgressByCourseId[id])||{};
    const session=(state&&state.activeCourseId===id?state.session:(state&&state.sessionByCourseId&&state.sessionByCourseId[id]))||{};
    const last=(state&&state.activeCourseId===id?state.lastBilan:(state&&state.lastBilanByCourseId&&state.lastBilanByCourseId[id]))||{};
    return {progress,session,last};
  }
  function summarizeCourse(course,state){
    const courseId=String(course&&course.id||'') || (window.LearnItCourseCollectionModel&&window.LearnItCourseCollectionModel.courseId?window.LearnItCourseCollectionModel.courseId(course):String(course&&course.title||'course').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,''));
    const ids=activityIds(course); const total=ids.length; const idSet=new Set(ids);
    const {progress,session,last}=courseState(state,courseId);
    const seenIds=new Set(); const correctIds=new Set(); const reviewIds=new Set();
    Object.entries(progress||{}).forEach(([id,row])=>{if(!idSet.has(String(id)))return; seenIds.add(id); if(row&&row.correct){correctIds.add(id); reviewIds.delete(id);} else if(row&&(row.review||row.correct===false)){reviewIds.add(id); correctIds.delete(id);}});
    Object.entries((session&&session.answers)||{}).forEach(([id,row])=>{if(!idSet.has(String(id)))return; seenIds.add(id); if(row&&row.correct){correctIds.add(id); reviewIds.delete(id);} else {reviewIds.add(id); correctIds.delete(id);}});
    safeArray(last&&last.review).forEach(id=>{id=String(id); if(idSet.has(id)&&!correctIds.has(id))reviewIds.add(id);});
    const seen=seenIds.size, correct=correctIds.size, reviewCount=reviewIds.size;
    const mastery=pct(correct,total); const exposure=pct(seen,total);
    const hasAny=seen>0 || correct>0 || reviewCount>0 || !!(last&&last.done) || session.status==='active' || session.status==='completed';
    const decisionInput={courseId,title:courseTitle(course),total,seen,correct,reviewCount,mastery,exposure,hasAny};const nextModel=window.LearnItNextActionModel;
    const rec=nextModel&&typeof nextModel.recommend==='function'?nextModel.recommend({...course,id:courseId},progress,session,last):nextModel&&typeof nextModel.recommendationFromSummary==='function'?nextModel.recommendationFromSummary(decisionInput):null;
    const action=rec?(rec.action==='discover'?'start':rec.action==='validate'?'exam':rec.action):(reviewCount?'review':(seen>0||session.status==='active'?'continue':'start'));
    const priority=rec?rec.label:(action==='review'?'Revoir':action==='exam'?'Consolider':action==='continue'?'Continuer':'Découvrir');
    const evidenceStatus=String(rec&&rec.evidence&&rec.evidence.status||'');
    return {...decisionInput,priority,action,nextAction:rec,evidenceStatus,consolidated:evidenceStatus==='consolidated',empty:total===0,reviewIds:[...reviewIds],seenIds:[...seenIds],correctIds:[...correctIds],sessionStatus:session.status||'idle'};
  }
  function summarizeChapter(course,state,chapter,index){
    const summary=summarizeCourse(course,state); const ids=safeArray(chapter&&chapter.ids).map(String); const idSet=new Set(ids);
    const seen=summary.seenIds.filter(id=>idSet.has(id)).length;
    const correct=summary.correctIds.filter(id=>idSet.has(id)).length;
    const review=summary.reviewIds.filter(id=>idSet.has(id)).length;
    const total=ids.length;
    let stateName='todo'; let label='À découvrir';
    if(review>0){stateName='review'; label='À revoir';}
    else if(total>0 && seen>=total){stateName='done'; label='Vu';}
    else if(seen>0){stateName='current'; label='En cours';}
    return {index,total,seen,correct,review,state:stateName,label,title:String(chapter&&chapter.title||`Chapitre ${index+1}`),detail:String(chapter&&chapter.detail||'')};
  }
  function summarizeCollection(collection,state){
    const courses=safeArray(collection&&collection.courses).map(course=>summarizeCourse(course,state));
    const totals=courses.reduce((a,c)=>({total:a.total+c.total,seen:a.seen+c.seen,correct:a.correct+c.correct,reviewCount:a.reviewCount+c.reviewCount}),{total:0,seen:0,correct:0,reviewCount:0});
    const priority=totals.reviewCount?'Revoir':(totals.seen?'Continuer':'Découvrir');
    return Object.assign({collectionId:collection&&collection.id,title:collectionTitle(collection),courses,priority},totals,{exposure:pct(totals.seen,totals.total),mastery:pct(totals.correct,totals.total)});
  }
  function buildHierarchy(collections,state){
    return safeArray(collections).map(collection=>Object.assign({},collection,{summary:summarizeCollection(collection,state),courses:safeArray(collection.courses).map(course=>Object.assign({},course,{summary:summarizeCourse(course,state)}))}));
  }
  function visibleBlocks(summary){
    const blocks=[];
    if(!summary||summary.empty)return blocks;
    if(summary.hasAny)blocks.push('progress');
    if(summary.reviewCount>0)blocks.push('review');
    blocks.push('next-action');
    return blocks;
  }
  function actionLabel(action){return ({start:'Commencer',continue:'Continuer',review:'Revoir',exam:'Consolider'})[action]||'Apprendre';}
  function audit(){
    const course={id:'c1',title:'Cours test',activities:[{id:'a1'},{id:'a2'}]};
    const state={activityProgressByCourseId:{c1:{a1:{correct:true}}},lastBilanByCourseId:{c1:{review:['a2','ghost']}}};
    const summary=summarizeCourse(course,state); const blocks=visibleBlocks(summary); const chapter=summarizeChapter(course,state,{title:'Ch',ids:['a1','a2']},0);
    return {schema,ok:summary.reviewCount===1&&summary.mastery===50&&blocks.includes('review')&&!blocks.includes('empty')&&actionLabel(summary.action)==='Revoir'&&chapter.review===1,summary,blocks,chapter};
  }
  window.LearnItBilanDecisionModel=Object.freeze({schema,summarizeCourse,summarizeChapter,summarizeCollection,buildHierarchy,visibleBlocks,actionLabel,audit});
})();
