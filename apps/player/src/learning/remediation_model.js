(function(){
  'use strict';

  const SCHEMA='learnit.learning_evidence.v2';
  const REVIEW_SCHEMA='learnit.spaced_review.v1';
  const MAX_HISTORY=8;
  const DEFAULT_MAX_ITEMS=5;
  const DEFAULT_MAX_ROUNDS=2;
  const DEFAULT_DUE_LIMIT=8;
  const FAILURE_RETRY_HOURS=8;
  const REVIEW_INTERVAL_HOURS=Object.freeze([24,72,168,336,720]);

  function arr(v){return Array.isArray(v)?v:[];}
  function text(v){return String(v||'').trim();}
  function clone(v){return JSON.parse(JSON.stringify(v));}
  function uniq(values){return [...new Set(arr(values).map(text).filter(Boolean))];}
  function boundedInt(value,min,max,fallback=min){const n=Number(value);return Number.isFinite(n)?Math.min(max,Math.max(min,Math.trunc(n))):fallback;}
  function parseTime(value){const ms=Date.parse(text(value));return Number.isFinite(ms)?ms:null;}
  function isoFrom(base,hours){const ms=parseTime(base);return new Date((ms===null?Date.now():ms)+(Number(hours)||0)*36e5).toISOString();}
  function reviewIntervalHours(level){const safe=boundedInt(level,1,REVIEW_INTERVAL_HOURS.length,1);return REVIEW_INTERVAL_HOURS[safe-1];}
  function normalizeActivity(activity){
    const a=activity||{};
    return {
      id:text(a.id),
      type:text(a.type),
      objective:text(a.objective||a.question),
      commonErrors:uniq(a.common_errors),
      remediation:text(a.remediation),
      difficulty:text(a.difficulty),
      phase:text(a.learning_phase)
    };
  }
  function legacyDueAt(row){
    const last=text(row&&row.lastAt);
    if(!last)return '';
    return isoFrom(last,row&&row.correct?72:FAILURE_RETRY_HOURS);
  }
  function normalizeRow(row){
    const r=row&&typeof row==='object'?row:{};
    const level=boundedInt(r.reviewLevel,0,REVIEW_INTERVAL_HOURS.length,0);
    return {
      ...clone(r),
      attempts:Number(r.attempts||0),
      failureCount:Number(r.failureCount||0),
      successCount:Number(r.successCount||0),
      failureStreak:Number(r.failureStreak||0),
      successStreak:Number(r.successStreak||0),
      remediationRounds:Number(r.remediationRounds||0),
      remediationExhausted:!!r.remediationExhausted,
      attemptHistory:arr(r.attemptHistory).slice(-MAX_HISTORY),
      commonErrors:uniq(r.commonErrors),
      reviewLevel:level,
      nextReviewAt:text(r.nextReviewAt)||legacyDueAt(r),
      lastReviewAt:text(r.lastReviewAt),
      reviewScheduleVersion:text(r.reviewScheduleVersion)||REVIEW_SCHEMA
    };
  }
  function scheduleAfter(previous,correct,mode,at){
    const prev=normalizeRow(previous);
    if(!correct){
      return {
        reviewLevel:0,
        nextReviewAt:isoFrom(at,FAILURE_RETRY_HOURS),
        lastReviewAt:mode==='spaced-review'||mode==='targeted-review'||mode==='review'?at:prev.lastReviewAt,
        reviewScheduleVersion:REVIEW_SCHEMA,
        reviewIntervalHours:FAILURE_RETRY_HOURS
      };
    }
    const level=Math.min(REVIEW_INTERVAL_HOURS.length,Math.max(1,prev.reviewLevel+1));
    const interval=reviewIntervalHours(level);
    return {
      reviewLevel:level,
      nextReviewAt:isoFrom(at,interval),
      lastReviewAt:mode==='spaced-review'||mode==='targeted-review'||mode==='review'?at:prev.lastReviewAt,
      reviewScheduleVersion:REVIEW_SCHEMA,
      reviewIntervalHours:interval
    };
  }
  function recordProgress(previous,result,activity,context={}){
    const prev=normalizeRow(previous);
    const meta=normalizeActivity(activity);
    const correct=!!(result&&result.correct);
    const mode=text(context.mode||'normal')||'normal';
    const targeted=mode==='targeted-review';
    let remediationRounds=prev.remediationRounds;
    if(!targeted&&!correct)remediationRounds=0;
    if(targeted&&!correct)remediationRounds+=1;
    if(targeted&&correct)remediationRounds=0;
    const maxRounds=Math.max(1,Number(context.maxRounds||DEFAULT_MAX_ROUNDS));
    const at=text(context.at)||new Date().toISOString();
    const history=prev.attemptHistory.concat([{correct,mode,at,expected:text(result&&result.expected)}]).slice(-MAX_HISTORY);
    const schedule=scheduleAfter(prev,correct,mode,at);
    return {
      ...prev,
      ...schedule,
      seen:true,
      correct,
      review:!correct,
      attempts:prev.attempts+1,
      failureCount:prev.failureCount+(correct?0:1),
      successCount:prev.successCount+(correct?1:0),
      failureStreak:correct?0:prev.failureStreak+1,
      successStreak:correct?prev.successStreak+1:0,
      recurringError:!correct&&((prev.failureCount+1)>=2||(prev.failureStreak+1)>=2),
      expected:text(result&&result.expected),
      lastAt:at,
      lastMode:mode,
      contentVersion:text(context.contentVersion),
      remediationRounds,
      remediationExhausted:!correct&&targeted&&remediationRounds>=maxRounds,
      commonErrors:uniq(meta.commonErrors.concat(prev.commonErrors)),
      objective:meta.objective,
      activityType:meta.type,
      remediation:meta.remediation,
      attemptHistory:history
    };
  }
  function dueState(row,now=Date.now()){
    const r=normalizeRow(row);
    if(!r.seen)return {due:false,reason:'unseen',dueAt:r.nextReviewAt,overdueHours:0,row:r};
    const dueMs=parseTime(r.nextReviewAt);
    const current=typeof now==='number'?now:(parseTime(now)||Date.now());
    const immediate=!!r.review;
    const scheduled=dueMs!==null&&dueMs<=current;
    return {
      due:immediate||scheduled,
      reason:immediate?'error':(scheduled?'scheduled':'future'),
      dueAt:r.nextReviewAt,
      overdueHours:scheduled?Math.max(0,Math.floor((current-dueMs)/36e5)):0,
      row:r
    };
  }
  function duePriority(state){
    const r=state.row;
    return (state.reason==='error'?1000:0)+(r.recurringError?250:0)+Math.min(240,state.overdueHours)+Math.min(120,r.failureCount*12)+Math.max(0,50-r.reviewLevel*8);
  }
  function buildDuePlan(course,progress,options={}){
    const now=options.now===undefined?Date.now():options.now;
    const limit=Math.max(1,Number(options.maxItems||DEFAULT_DUE_LIMIT));
    const rows=arr(course&&course.activities).map(activity=>{
      const id=text(activity&&activity.id);
      const state=dueState((progress||{})[id],now);
      return {id,activity,state,priority:duePriority(state)};
    }).filter(item=>item.id&&item.state.due);
    rows.sort((a,b)=>b.priority-a.priority||text(a.state.dueAt).localeCompare(text(b.state.dueAt))||a.id.localeCompare(b.id));
    const selected=rows.slice(0,limit);
    const nextFuture=arr(course&&course.activities).map(activity=>{
      const id=text(activity&&activity.id);const state=dueState((progress||{})[id],now);const ms=parseTime(state.dueAt);
      return state.reason==='future'&&ms!==null?{id,dueAt:state.dueAt,ms}:null;
    }).filter(Boolean).sort((a,b)=>a.ms-b.ms)[0]||null;
    return {
      schema:REVIEW_SCHEMA,
      ok:selected.length>0,
      queue:selected.map(item=>item.id),
      rows:selected.map(item=>({
        id:item.id,
        objective:normalizeActivity(item.activity).objective,
        reason:item.state.reason,
        dueAt:item.state.dueAt,
        overdueHours:item.state.overdueHours,
        reviewLevel:item.state.row.reviewLevel,
        recurringError:!!item.state.row.recurringError
      })),
      totalDue:rows.length,
      deferredCount:Math.max(0,rows.length-selected.length),
      maxItems:limit,
      nextDueAt:nextFuture&&nextFuture.dueAt||'',
      summary:selected.length?`Révision courte · ${selected.length} activité${selected.length>1?'s':''}`:'Aucune révision due',
      focus:selected.some(item=>item.state.reason==='error')?'Points fragiles':'Consolidation espacée',
      deterministic:true,
      dailyLoadBounded:true
    };
  }
  function overlap(a,b){
    const set=new Set(uniq(a));
    return uniq(b).filter(v=>set.has(v)).length;
  }
  function sameObjective(a,b){return text(a&&a.objective)&&text(a&&a.objective)===text(b&&b.objective);}
  function score(activity,row,lastReviewSet){
    const r=normalizeRow(row);
    let value=0;
    if(lastReviewSet&&lastReviewSet.has(text(activity&&activity.id)))value+=50;
    if(r.review)value+=40;
    value+=Math.min(30,r.failureCount*8);
    value+=Math.min(20,r.failureStreak*10);
    if(r.recurringError)value+=20;
    if(r.remediationExhausted)value-=200;
    return value;
  }
  function bestAlternative(source,activities,progress,excluded){
    const s=normalizeActivity(source);const variety=window.LearnItVarietyModel;
    const rows=arr(activities).filter(a=>text(a&&a.id)!==s.id&&!excluded.has(text(a&&a.id))).map(a=>{
      const m=normalizeActivity(a);const row=normalizeRow((progress||{})[m.id]);
      const linked=sameObjective(s,m)||overlap(s.commonErrors,m.commonErrors)>0;
      const similarity=variety&&typeof variety.similarity==='function'?variety.similarity(source,a):0;
      const different=variety&&typeof variety.isMeaningfullyDifferent==='function'?variety.isMeaningfullyDifferent(source,a):(s.type!==m.type||text(source&&source.question)!==text(a&&a.question));
      const relation=(sameObjective(s,m)?30:0)+(overlap(s.commonErrors,m.commonErrors)*15)+(s.type!==m.type?10:0);
      const diversity=(different?18:-40)+Math.round((1-similarity)*12);
      const readiness=(row.remediationExhausted?-100:0)-Math.min(20,row.attempts*2)+(row.correct?3:0);
      return {activity:a,linked,different,similarity,relation,diversity,readiness,total:relation+diversity+readiness};
    }).filter(x=>x.linked&&x.different&&!normalizeRow((progress||{})[text(x.activity&&x.activity.id)]).remediationExhausted);
    rows.sort((a,b)=>b.total-a.total||a.similarity-b.similarity||text(a.activity.id).localeCompare(text(b.activity.id)));
    return rows[0]&&rows[0].activity;
  }
  function buildPlan(course,progress,lastBilan,options={}){
    const activities=arr(course&&course.activities);
    const byId=new Map(activities.map(a=>[text(a.id),a]));
    const lastReview=new Set(arr(lastBilan&&lastBilan.review).map(text));
    const failed=activities.filter(a=>{
      const id=text(a.id);const row=normalizeRow((progress||{})[id]);
      return lastReview.has(id)||row.review;
    }).sort((a,b)=>score(b,(progress||{})[text(b.id)],lastReview)-score(a,(progress||{})[text(a.id)],lastReview));
    const maxItems=Math.max(1,Number(options.maxItems||DEFAULT_MAX_ITEMS));
    const maxRounds=Math.max(1,Number(options.maxRounds||DEFAULT_MAX_ROUNDS));
    const queue=[];const reasons=[];const exhausted=[];const used=new Set();
    for(const source of failed){
      if(queue.length>=maxItems)break;
      const id=text(source.id);const row=normalizeRow((progress||{})[id]);
      if(row.remediationExhausted||row.remediationRounds>=maxRounds){exhausted.push(id);continue;}
      const alt=bestAlternative(source,activities,progress,used);
      if(alt&&queue.length<maxItems){const aid=text(alt.id);queue.push(aid);used.add(aid);reasons.push({id:aid,kind:'variant',sourceId:id,objective:text(source.objective),commonErrors:uniq(source.common_errors)});}
      if(!used.has(id)&&queue.length<maxItems){queue.push(id);used.add(id);reasons.push({id,kind:'source',sourceId:id,objective:text(source.objective),commonErrors:uniq(source.common_errors)});}
    }
    const first=queue.length?byId.get((reasons[0]&&reasons[0].sourceId)||queue[0]):null;
    return {
      schema:SCHEMA,
      ok:queue.length>0,
      queue,
      reasons,
      exhausted,
      exhaustedOnly:failed.length>0&&queue.length===0&&exhausted.length>0,
      maxItems,
      maxRounds,
      focus:text(first&&first.objective)||'Points à revoir',
      summary:queue.length?`Reprise ciblée sur ${queue.length} activité${queue.length>1?'s':''}`:(exhausted.length?'Pause recommandée avant une nouvelle reprise':'Aucun point à reprendre'),
      noInfiniteLoop:true
    };
  }
  function feedback(activity,correct){
    const meta=normalizeActivity(activity);
    return {
      commonErrors:correct?[]:meta.commonErrors.slice(0,2),
      remediation:correct?'':meta.remediation,
      objective:meta.objective
    };
  }
  function selfTest(){
    const course={activities:[
      {id:'a',type:'qcm',objective:'Loi O',common_errors:['signe'],remediation:'reprendre'},
      {id:'b',type:'fill',objective:'Loi O',common_errors:['signe'],remediation:'appliquer'},
      {id:'c',type:'qcm',objective:'Autre',common_errors:['unité']}
    ]};
    let row=recordProgress({}, {correct:false,expected:'x'}, course.activities[0], {mode:'normal',at:'2026-01-01T00:00:00Z'});
    row=recordProgress(row, {correct:false,expected:'x'}, course.activities[0], {mode:'targeted-review',maxRounds:2,at:'2026-01-01T01:00:00Z'});
    const plan=buildPlan(course,{a:row},{review:['a']},{maxItems:3,maxRounds:2});
    const row2=recordProgress(row,{correct:false},course.activities[0],{mode:'targeted-review',maxRounds:2,at:'2026-01-01T02:00:00Z'});
    const stopped=buildPlan(course,{a:row2},{review:['a']},{maxItems:3,maxRounds:2});
    const firstSuccess=recordProgress({}, {correct:true}, course.activities[2], {mode:'normal',at:'2026-01-01T00:00:00Z'});
    const dueEarly=buildDuePlan(course,{c:firstSuccess},{now:Date.parse('2026-01-01T12:00:00Z')});
    const dueLater=buildDuePlan(course,{c:firstSuccess},{now:Date.parse('2026-01-02T01:00:00Z')});
    const secondSuccess=recordProgress(firstSuccess,{correct:true},course.activities[2],{mode:'spaced-review',at:'2026-01-02T01:00:00Z'});
    return {
      ok:row.failureCount===2&&row.failureStreak===2&&plan.queue[0]==='b'&&plan.queue.includes('a')&&row2.remediationExhausted&&stopped.exhaustedOnly&&firstSuccess.reviewLevel===1&&!dueEarly.ok&&dueLater.queue[0]==='c'&&secondSuccess.reviewLevel===2&&secondSuccess.reviewIntervalHours===72,
      plan,stopped,row2,firstSuccess,dueEarly,dueLater,secondSuccess
    };
  }

  window.LearnItRemediationModel=Object.freeze({
    SCHEMA,REVIEW_SCHEMA,MAX_HISTORY,DEFAULT_MAX_ITEMS,DEFAULT_MAX_ROUNDS,DEFAULT_DUE_LIMIT,FAILURE_RETRY_HOURS,REVIEW_INTERVAL_HOURS,
    normalizeRow,recordProgress,buildPlan,buildDuePlan,dueState,feedback,selfTest
  });
})();
