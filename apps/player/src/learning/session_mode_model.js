(function(){
  'use strict';

  const SCHEMA='learnit.session_modes.v1';
  const ENTRY_SCHEMA='learnit.session_entry_guidance.rc693.v2';
  const PUBLIC_MODE_IDS=Object.freeze(['discovery','training','review','validation','diagnostic']);
  const ALIASES=Object.freeze({normal:'training',exam:'validation','targeted-review':'review','spaced-review':'review'});
  const POLICIES=Object.freeze({
    discovery:Object.freeze({id:'discovery',label:'Découverte',detail:'Nouveau sujet · apprendre pas à pas',when:'À choisir lorsque le parcours est nouveau.',queueStrategy:'unseen-first',maxItems:8,feedbackTiming:'immediate',allowRetry:true,showHints:true,recordProgress:true,assessment:false,recommended:false}),
    training:Object.freeze({id:'training',label:'Entraînement',detail:'Pratiquer avec correction immédiate',when:'À choisir pour progresser librement après la découverte.',queueStrategy:'authored-balanced',maxItems:10,feedbackTiming:'immediate',allowRetry:true,showHints:true,recordProgress:true,assessment:false,recommended:false}),
    review:Object.freeze({id:'review',label:'Révision',detail:'Revoir les fragilités et échéances',when:'À choisir lorsque des points sont à reprendre.',queueStrategy:'due-and-fragile',maxItems:8,feedbackTiming:'immediate',allowRetry:true,showHints:true,recordProgress:true,assessment:false,recommended:false}),
    validation:Object.freeze({id:'validation',label:'Validation',detail:'Après apprentissage · confirmer le niveau',when:'À choisir après avoir travaillé le parcours.',queueStrategy:'assessment',maxItems:10,feedbackTiming:'deferred',allowRetry:false,showHints:false,recordProgress:true,assessment:true,recommended:false}),
    diagnostic:Object.freeze({id:'diagnostic',label:'Diagnostic',detail:'Déjà des bases · situer le niveau',when:'À choisir au début si le sujet est déjà connu.',queueStrategy:'diagnostic-sample',maxItems:6,feedbackTiming:'deferred',allowRetry:false,showHints:false,recordProgress:false,assessment:true,recommended:false})
  });

  function arr(value){return Array.isArray(value)?value:[];}
  function text(value){return String(value===undefined||value===null?'':value).trim();}
  function clone(value){return JSON.parse(JSON.stringify(value));}
  function uniq(values){const seen=new Set();return arr(values).map(text).filter(value=>value&&!seen.has(value)&&seen.add(value));}
  function canonicalId(mode){const raw=text(mode)||'training';return PUBLIC_MODE_IDS.includes(raw)?raw:(ALIASES[raw]||'training');}
  function resolve(mode){return clone(POLICIES[canonicalId(mode)]);}
  function list(){return PUBLIC_MODE_IDS.map(id=>clone(POLICIES[id]));}
  function progressRow(progress,id){const row=(progress||{})[id];return row&&typeof row==='object'?row:{};}
  function isSeen(row){return !!(row&&(row.seen||Number(row.attemptCount||0)>0||row.lastAt));}
  function isCorrect(row){return !!(row&&row.correct===true);}
  function isFragile(row){return !!(row&&(row.review||row.recurringError||Number(row.failureStreak||0)>0));}
  function eligible(activity,policy){return !!(activity&&text(activity.id)&&!(policy.assessment&&activity.type==='flashcard'));}
  function activities(course,policy){return arr(course&&course.activities).filter(activity=>eligible(activity,policy));}
  function roleRank(activity,mode){const role=text(activity&&activity.assessment_role);const order=mode==='diagnostic'?['diagnostic','validation','practice','remediation']:['validation','diagnostic','practice','remediation'];const rank=order.indexOf(role);return rank<0?order.length:rank;}
  function roleOrderedIds(rows,mode){return rows.map((activity,index)=>({activity,index,rank:roleRank(activity,mode)})).sort((a,b)=>a.rank-b.rank||a.index-b.index).map(row=>text(row.activity.id));}
  function assessmentPool(rows,mode){
    const expected=mode==='diagnostic'?'diagnostic':'validation';
    const strict=rows.filter(activity=>text(activity&&activity.assessment_role)===expected);
    const objectiveCount=new Set(rows.map(objectiveKey).filter(Boolean)).size;
    const minimum=Math.min(2,Math.max(1,objectiveCount));
    if(strict.length>=minimum)return {rows:strict,purity:'strict',expectedRole:expected,strictCount:strict.length,fallbackCount:0,fallbackReason:''};
    const secondary=rows.filter(activity=>!strict.includes(activity)&&['diagnostic','validation'].includes(text(activity&&activity.assessment_role)));
    const practice=rows.filter(activity=>!strict.includes(activity)&&!secondary.includes(activity)&&text(activity&&activity.assessment_role)!=='remediation');
    const fallback=[...strict,...secondary,...practice];
    return {rows:fallback.length?fallback:rows,purity:'explicit-fallback',expectedRole:expected,strictCount:strict.length,fallbackCount:Math.max(0,(fallback.length?fallback:rows).length-strict.length),fallbackReason:strict.length?`only-${strict.length}-${expected}-item${strict.length>1?'s':''}`:`no-${expected}-role`};
  }
  function objectiveKey(activity){return text(activity&&activity.objective||activity&&activity.question).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||text(activity&&activity.id);}
  function adaptiveOrder(rows,ids,options={}){
    const focus=new Set(arr(options.objectiveKeys).map(text).filter(Boolean));
    const assessedStrong=new Set(arr(options.objectiveAssessment).filter(row=>text(row&&row.status)==='strong').map(row=>text(row&&row.key)));
    const byId=new Map(rows.map(activity=>[text(activity.id),activity]));
    return ids.map((id,index)=>{const activity=byId.get(id);const key=objectiveKey(activity);let rank=1;if(focus.has(key))rank=0;else if(assessedStrong.has(key))rank=2;return {id,index,rank};}).sort((a,b)=>a.rank-b.rank||a.index-b.index).map(row=>row.id);
  }
  function dueIds(course,progress,limit,now){const model=window.LearnItRemediationModel;if(!model||typeof model.buildDuePlan!=='function')return [];const plan=model.buildDuePlan(course,progress,{maxItems:limit,now:now===undefined?Date.now():now});return arr(plan&&plan.queue);}
  function diagnosticSample(rows,ids,limit){
    const byId=new Map(rows.map(activity=>[text(activity.id),activity]));const selected=[];const objectives=new Set();const types=new Set();
    for(const id of ids){if(selected.length>=limit)break;const activity=byId.get(id);if(!activity)continue;const objective=text(activity.objective||activity.question).toLowerCase();const type=text(activity.type);if((objective&&!objectives.has(objective))||(type&&!types.has(type))){selected.push(id);if(objective)objectives.add(objective);if(type)types.add(type);}}
    for(const id of ids){if(selected.length>=limit)break;if(!selected.includes(id))selected.push(id);}return selected;
  }
  function buildPlan(course,progress,mode,options={}){
    const policy=resolve(mode);const rows=activities(course,policy);const assessment=policy.assessment?assessmentPool(rows,policy.id):{rows,purity:'not-assessment',expectedRole:'',strictCount:0,fallbackCount:0,fallbackReason:''};const selectedRows=assessment.rows;const all=rows.map(activity=>text(activity.id));const selectedIds=selectedRows.map(activity=>text(activity.id));const limit=Math.max(1,Number(options.maxItems||policy.maxItems));
    const unseen=all.filter(id=>!isSeen(progressRow(progress,id)));const seen=all.filter(id=>isSeen(progressRow(progress,id)));const fragile=all.filter(id=>isFragile(progressRow(progress,id)));const due=policy.id==='review'?dueIds(course,progress,limit,options.now):[];let queue=[];
    if(policy.id==='discovery')queue=uniq([...unseen,...all]);
    else if(policy.id==='training')queue=uniq(all);
    else if(policy.id==='review')queue=uniq([...due,...fragile,...seen,...all]);
    else if(policy.id==='validation')queue=uniq(roleOrderedIds(selectedRows,'validation'));
    else if(policy.id==='diagnostic')queue=diagnosticSample(selectedRows,roleOrderedIds(selectedRows,'diagnostic'),limit);
    if(options.adaptive&&['discovery','training'].includes(policy.id))queue=adaptiveOrder(rows,queue,options);
    queue=queue.slice(0,limit);
    const queueById=new Map(rows.map(activity=>[text(activity.id),activity]));const queueRoleCounts={};for(const id of queue){const role=text(queueById.get(id)&&queueById.get(id).assessment_role)||'unspecified';queueRoleCounts[role]=(queueRoleCounts[role]||0)+1;}
    return {schema:SCHEMA,ok:queue.length>0,mode:policy.id,policy,queue,queueLength:queue.length,eligibleCount:all.length,assessmentCandidateCount:selectedIds.length,unseenCount:unseen.length,fragileCount:fragile.length,maxItems:limit,fallbackUsed:policy.id==='review'&&!fragile.length&&!due.length,excludesFlashcards:policy.assessment,usesAssessmentRole:policy.assessment,assessmentPurity:assessment.purity,expectedAssessmentRole:assessment.expectedRole,strictAssessmentCount:assessment.strictCount,assessmentFallbackCount:assessment.fallbackCount,assessmentFallbackReason:assessment.fallbackReason,queueRoleCounts:Object.freeze(queueRoleCounts),adaptive:!!options.adaptive,adaptiveSource:text(options.sourceRecommendationCode),focusObjectiveKeys:arr(options.objectiveKeys).map(text),deterministic:true,summary:`${policy.label} · ${queue.length} activité${queue.length>1?'s':''}`};
  }
  function sessionPolicy(sessionOrMode){if(sessionOrMode&&typeof sessionOrMode==='object'&&sessionOrMode.modePolicy)return {...resolve(sessionOrMode.modePolicy.id||sessionOrMode.mode),...clone(sessionOrMode.modePolicy)};return resolve(sessionOrMode&&typeof sessionOrMode==='object'?sessionOrMode.mode:sessionOrMode);}
  function isDeferred(sessionOrMode){return sessionPolicy(sessionOrMode).feedbackTiming==='deferred';}
  function canRetry(sessionOrMode){return !!sessionPolicy(sessionOrMode).allowRetry;}
  function recordsProgress(sessionOrMode){return sessionPolicy(sessionOrMode).recordProgress!==false;}
  function evidence(course,progress,session,options={}){
    const rows=activities(course,resolve('training'));const ids=rows.map(activity=>text(activity.id));
    const seen=ids.filter(id=>isSeen(progressRow(progress,id))).length;
    const correct=ids.filter(id=>isCorrect(progressRow(progress,id))).length;
    const review=ids.filter(id=>isFragile(progressRow(progress,id))).length;
    const due=dueIds(course,progress,Math.max(8,ids.length),options.now);
    const active=!!(session&&session.status==='active');
    const currentMode=active?canonicalId(session.mode):'';
    const total=ids.length;const completed=total>0&&seen>=total;const mastery=total?Math.round(correct*100/total):0;
    return {total,seen,correct,reviewCount:review,dueCount:due.length,dueQueue:due,active,currentMode,currentIndex:Math.max(0,Number(session&&session.currentIndex||0)),queueLength:arr(session&&session.queue).length,completed,mastery,hasProgress:seen>0||correct>0||review>0};
  }
  function entryRecommendation(course,progress,session,options={}){
    const nextModel=window.LearnItNextActionModel;if(nextModel&&typeof nextModel.recommend==='function'){const rec=nextModel.recommend(course,progress,session,options.lastBilan,options);return {...rec,primaryLabel:rec.label,boundaryNote:'Diagnostic au début pour situer le niveau · Validation à la fin pour confirmer la maîtrise.',recommended:true};}
    const e=evidence(course,progress,session,options);let state='new';let mode='discovery';let intent='discovery';let headline='Commencez par découvrir le parcours';let reason='Sujet nouveau : avancez pas à pas avec une correction immédiate.';let primaryLabel='Découvrir ce parcours';let secondary={intent:'diagnostic',mode:'diagnostic',label:'Évaluer rapidement mon niveau',detail:'Vous connaissez déjà le sujet ? Un diagnostic court situe vos acquis sans modifier la progression.'};
    if(e.active){const p=resolve(e.currentMode||'training');state='active';mode=p.id;intent='resume';headline='Continuez là où vous en étiez';reason=`Votre séance ${p.label.toLowerCase()} est en cours${e.queueLength?` · activité ${Math.min(e.currentIndex+1,e.queueLength)}/${e.queueLength}`:''}.`;primaryLabel='Reprendre la séance';secondary=null;}
    else if(e.reviewCount>0||e.dueCount>0){state='review';mode='review';intent='review';headline='Reprenez les points fragiles';const count=Math.max(e.reviewCount,e.dueCount);reason=`${count} activité${count>1?'s sont':' est'} à revoir avant de poursuivre.`;primaryLabel='Commencer la révision';secondary={intent:'training',mode:'training',label:'Continuer quand même',detail:'Poursuivre l’entraînement sans être bloqué par les révisions.'};}
    else if(e.hasProgress&&e.completed&&e.mastery>=80){state='ready-to-validate';mode='validation';intent='validation';headline='Vérifiez votre maîtrise';reason='Vous avez vu et réussi l’essentiel. Confirmez votre niveau sans indice.';primaryLabel='Lancer une validation';secondary={intent:'training',mode:'training',label:'Encore m’entraîner',detail:'Refaire une série avec correction immédiate avant la validation.'};}
    else if(e.hasProgress){state='in-progress';mode='training';intent='training';headline='Continuez votre entraînement';reason='Reprenez le parcours avec correction immédiate et droit à l’erreur.';primaryLabel='Continuer le parcours';secondary={intent:'diagnostic',mode:'diagnostic',label:'Faire un diagnostic court',detail:'Mesurer votre niveau actuel sans modifier la progression.'};}
    return {schema:ENTRY_SCHEMA,state,mode,intent,headline,reason,primaryLabel,secondary,evidence:e,boundaryNote:'Diagnostic au début pour situer le niveau · Validation à la fin pour confirmer la maîtrise.',recommended:true};
  }
  function outcome(summary){
    const s=summary||{};const policy=sessionPolicy(s);const total=Math.max(0,Number(s.total||0));const correct=Math.max(0,Number(s.correct||0));const review=arr(s.review);const pct=total?Math.round(correct*100/total):0;const passed=total>0&&review.length===0;const title=policy.id==='diagnostic'?'Diagnostic terminé':policy.id==='validation'?'Validation terminée':`${policy.label} terminée`;const detail=policy.assessment?`${correct}/${total} réponse${total>1?'s':''} correcte${total>1?'s':''} · ${pct}%`:(passed?'Séance consolidée.':`${review.length} point${review.length>1?'s':''} à reprendre.`);
    const objectiveRows=arr(s.objectiveAssessment).map(row=>({key:text(row&&row.key),label:text(row&&row.label)||'Objectif',total:Math.max(0,Number(row&&row.total)||0),correct:Math.max(0,Number(row&&row.correct)||0),incorrect:Math.max(0,Number(row&&row.incorrect)||0),status:text(row&&row.status)||'unverified'}));
    const debrief=objectiveRows.map(row=>({key:row.key,label:row.label,status:row.status,detail:row.incorrect?`${row.incorrect} erreur${row.incorrect>1?'s':''} sur ${row.total}`:`${row.correct}/${row.total} réussi${row.correct>1?'s':''}`,next:row.incorrect?'À reprendre en priorité':'Preuve positive à confirmer dans le temps'}));
    return {schema:SCHEMA,mode:policy.id,label:policy.label,title,detail,total,correct,reviewCount:review.length,pct,passed,deferred:policy.feedbackTiming==='deferred',recordedInProgress:policy.recordProgress,objectiveRows,debrief};
  }
  function selfTest(){
    const course={activities:[{id:'f',type:'flashcard',objective:'Définir',assessment_role:'practice'},{id:'q1',type:'qcm',objective:'Calculer',assessment_role:'validation'},{id:'q2',type:'qcm',objective:'Interpréter',assessment_role:'diagnostic'},{id:'o1',type:'order',objective:'Méthode',assessment_role:'remediation'},{id:'m1',type:'matching',objective:'Associer',assessment_role:'practice'}]};
    const progress={q1:{seen:true,correct:false,review:true,failureStreak:1},q2:{seen:true,correct:true}};
    const discovery=buildPlan(course,progress,'discovery');const review=buildPlan(course,progress,'review',{now:0});const validation=buildPlan(course,progress,'validation');const diagnostic=buildPlan(course,progress,'diagnostic');
    const fresh=entryRecommendation(course,{},{});const fragile=entryRecommendation(course,progress,{});
    const masteredOnce=entryRecommendation(course,Object.fromEntries(course.activities.map(a=>[a.id,{seen:true,correct:true,attempts:1,successCount:1}])),{});
    const consolidatedProgress=Object.fromEntries(course.activities.map((a,index)=>[a.id,{seen:true,correct:true,attempts:2,attemptCount:2,successCount:2,reviewLevel:2,nextReviewAt:'2099-01-01T00:00:00.000Z',attemptHistory:[{correct:true,at:`2026-01-${String(index+1).padStart(2,'0')}T00:00:00.000Z`},{correct:true,at:`2026-01-${String(index+3).padStart(2,'0')}T00:00:00.000Z`}]}]));
    const consolidated=entryRecommendation(course,consolidatedProgress,{}, {now:Date.parse('2026-01-10T00:00:00.000Z')});
    return {ok:list().length===5&&discovery.queue[0]==='f'&&review.queue.includes('q1')&&validation.queue[0]==='q1'&&diagnostic.queue[0]==='q2'&&!validation.queue.includes('f')&&!diagnostic.queue.includes('f')&&isDeferred('validation')&&isDeferred('diagnostic')&&!recordsProgress('diagnostic')&&recordsProgress('validation')&&!canRetry('validation')&&fresh.mode==='discovery'&&fresh.secondary.mode==='diagnostic'&&fragile.mode==='review'&&masteredOnce.mode==='training'&&consolidated.mode==='validation',discovery,review,validation,diagnostic,fresh,fragile,masteredOnce,consolidated};
  }

  window.LearnItSessionModeModel=Object.freeze({SCHEMA,ENTRY_SCHEMA,PUBLIC_MODE_IDS,canonicalId,resolve,list,buildPlan,sessionPolicy,isDeferred,canRetry,recordsProgress,evidence,entryRecommendation,outcome,selfTest});
})();
