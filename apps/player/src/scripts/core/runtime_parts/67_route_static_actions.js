/* RC455 — static route action controller.
   The route surface is now rendered by RouteViewComposer. This controller keeps
   the composed buttons useful without adding any visible DOM block after paint:
   no DOM observer, no scheduled route enhancement, no late HTML block insertion. */
(function(){
  'use strict';
  const SCHEMA='learnit.rc693.route_static_actions.v2';
  function runtime(){return window.__LEARNIT_TEST__&&window.__LEARNIT_TEST__.runtime;}
  function activities(rt,courseId){try{const course=courseId&&rt&&rt.contentStore&&rt.contentStore.courseById?rt.contentStore.courseById(courseId):rt&&rt.contentStore&&rt.contentStore.content;return course&&Array.isArray(course.activities)?course.activities:[];}catch(e){return [];} }
  function courseProgress(rt,courseId){try{return rt.appState.courseProgress(courseId||rt.contentStore.activeCourseId)||{};}catch(e){return {};}}
  function reviewQueue(rt){const p=courseProgress(rt);return activities(rt).filter(a=>p[a.id]&&p[a.id].review).map(a=>a.id);}
  function unseenQueue(rt){const p=courseProgress(rt);return activities(rt).filter(a=>!p[a.id]).map(a=>a.id);}
  function duePlan(rt,now=Date.now()){
    const model=window.LearnItRemediationModel;
    if(model&&typeof model.buildDuePlan==='function')return model.buildDuePlan(rt.contentStore.content,courseProgress(rt),{now,maxItems:8});
    return {schema:'learnit.spaced_review.v1',ok:false,queue:[],rows:[],totalDue:0,deferredCount:0,maxItems:8};
  }
  function startQueue(rt,queue,summary,focus){
    if(queue&&queue.length)rt.session.startTargetedReview(queue,{summary,focus,queueLength:queue.length});
    else rt.session.start();
    rt.answer.reset();
    rt.go('session');
    if(typeof rt.scrollTop==='function')rt.scrollTop();
  }
  function smartResumeDecision(rt=runtime()){
    const acts=activities(rt);const s=(rt&&rt.session&&rt.session.session)||{};
    const review=rt?reviewQueue(rt):[];const unseen=rt?unseenQueue(rt):[];const due=rt?duePlan(rt):{queue:[],totalDue:0};const active=s.status==='active';
    const complete=acts.length>0&&unseen.length===0&&review.length===0;
    const choices=[];
    if(active)choices.push({kind:'resume-active',label:'Reprendre',primary:true});
    if(review.length)choices.push({kind:'review',label:'Points faibles',primary:!active});
    else if(due.queue.length)choices.push({kind:'spaced-review',label:`Révision · ${due.queue.length}`,primary:!active});
    if(unseen.length)choices.push({kind:'continue-new',label:'Suite',primary:!active&&!review.length&&!due.queue.length});
    choices.push({kind:'new-round',label:complete?'Consolider':'Nouvelle série',primary:choices.length===0});
    return {schema:'learnit.smart_resume.rc565.v1',courseId:rt&&rt.contentStore&&rt.contentStore.activeCourseId,total:acts.length,active,reviewCount:review.length,dueCount:due.totalDue||0,unseenCount:unseen.length,complete,reviewQueue:review,dueQueue:due.queue,unseenQueue:unseen,choices};
  }
  function spacedReviewDue(rt=runtime(),now=Date.now()){
    if(!rt)return {schema:'learnit.spaced_review.v1',ok:false,count:0,queue:[],rows:[],totalDue:0,deferredCount:0};
    const plan=duePlan(rt,now);
    return {...plan,courseId:rt.contentStore.activeCourseId,count:plan.queue.length};
  }
  function nonBlockingPolicy(rt=runtime()){
    const q=rt?reviewQueue(rt):[];
    return {schema:'learnit.non_blocking_review.rc241.v1',courseId:rt&&rt.contentStore&&rt.contentStore.activeCourseId,reviewCount:q.length,reviewQueue:q,blocking:false,guarantee:'Les points à revoir proposent une reprise ciblée mais ne bloquent ni Bibliothèque, ni Apprendre, ni nouvelle série.'};
  }
  function modes(){const model=window.LearnItSessionModeModel;return {schema:model&&model.SCHEMA||'learnit.session_modes.v1',modes:model&&typeof model.list==='function'?model.list():[]};}
  function progressSummary(rt=runtime(),courseId){
    const id=courseId||(rt&&rt.contentStore&&rt.contentStore.activeCourseId);const acts=activities(rt,id),p=rt?courseProgress(rt,id):{};const model=window.LearnItMasteryEvidenceModel;const course=rt&&rt.contentStore&&rt.contentStore.courseById?rt.contentStore.courseById(id):null;
    const rows=acts.map(a=>({id:a.id,objective:a.objective||a.question||a.id,seen:!!p[a.id],correct:!!(p[a.id]&&p[a.id].correct),review:!!(p[a.id]&&p[a.id].review)}));
    const evidence=model&&course&&typeof model.explainCourse==='function'?model.explainCourse(Object.assign({},course,{id}),p):null;
    return {schema:'learnit.progress_export.rc594.v1',courseId:id,total:rows.length,seen:rows.filter(r=>r.seen).length,correct:rows.filter(r=>r.correct).length,review:rows.filter(r=>r.review).length,evidence,rows};
  }
  function downloadJson(rt,name,data){if(rt&&typeof rt.exportJson==='function')rt.exportJson(name,data);}
  function handleSmartResume(kind){const rt=runtime();if(!rt)return;const d=smartResumeDecision(rt);if(kind==='resume-active'){rt.session.resume();rt.answer.reset();rt.go('session');if(rt.scrollTop)rt.scrollTop();return;}if(kind==='review')return startQueue(rt,d.reviewQueue,'Reprise intelligente','points à revoir');if(kind==='spaced-review')return handleSpacedReview();if(kind==='continue-new')return startQueue(rt,d.unseenQueue,'Suite du parcours','activités non vues');rt.session.start();rt.answer.reset();rt.go('session');if(rt.scrollTop)rt.scrollTop();}
  function handleReviewFreedom(kind){const rt=runtime();if(!rt)return;const p=nonBlockingPolicy(rt);if(kind==='review')return startQueue(rt,p.reviewQueue,'Points à revoir non bloquants','reprise libre');rt.session.start();rt.answer.reset();rt.go('session');if(rt.scrollTop)rt.scrollTop();}
  function handleSpacedReview(courseId){const rt=runtime();if(!rt)return;activateCourse(rt,courseId);const d=spacedReviewDue(rt);if(d.queue&&d.queue.length)rt.session.startSpacedReview(d.queue,{...d,source:'spaced-review-v1'});else rt.session.start();rt.answer.reset();rt.go('session');if(typeof rt.scrollTop==='function')rt.scrollTop();}
  function handleTrainingMode(mode){const rt=runtime();if(!rt)return;const plan=rt.session.startMode(mode);rt.answer.reset();rt.go('session');if(typeof rt.scrollTop==='function')rt.scrollTop();return plan;}
  function activateCourse(rt,courseId){if(!rt||!courseId||courseId===rt.contentStore.activeCourseId)return;rt.contentStore.setActiveCourse(courseId);rt.appState.alignWithContent();rt.answer.reset();}
  function handleEntryIntent(intent,mode,courseId){const rt=runtime();if(!rt)return;activateCourse(rt,courseId);const model=window.LearnItSessionModeModel;const selected=String(mode||intent||'training');if(intent==='resume'&&rt.session.session.status==='active'){rt.session.resume();rt.answer.reset();rt.go('session');if(typeof rt.scrollTop==='function')rt.scrollTop();return {mode:rt.session.session.mode,resumed:true};}const target=model&&typeof model.canonicalId==='function'?model.canonicalId(selected):selected;const state=rt.appState&&rt.appState.state||{};const last=(state.lastBilanByCourseId||{})[rt.contentStore.activeCourseId]||state.lastBilan||null;const nextModel=window.LearnItNextActionModel;const rec=nextModel&&typeof nextModel.recommend==='function'?nextModel.recommend(rt.contentStore.content,courseProgress(rt),{status:'idle'},last):null;const options=nextModel&&typeof nextModel.sessionOptions==='function'?nextModel.sessionOptions(rec,last):{};const plan=rt.session.startMode(target,options);rt.answer.reset();rt.go('session');if(typeof rt.scrollTop==='function')rt.scrollTop();return plan;}
  function formatBytes(bytes){const n=Number(bytes||0);if(n<1024)return n+' o';if(n<1024*1024)return Math.round(n/1024)+' Ko';return (n/(1024*1024)).toFixed(1).replace('.',',')+' Mo';}
  function fileLooksJson(file){if(!file)return false;const name=String(file.name||'').toLowerCase();const type=String(file.type||'').toLowerCase();return name.endsWith('.json')||type==='application/json'||type==='text/json';}
  function summarizeJson(text){try{const parsed=JSON.parse(String(text||''));if(parsed&&parsed.kind==='learnit-course-package'){const courses=Array.isArray(parsed.courses)?parsed.courses:[];const activities=courses.reduce((sum,c)=>sum+(Array.isArray(c.activities)?c.activities.length:0),0);return {ok:true,kind:'package',label:`Package Learn-it · ${courses.length} parcours · ${activities} activités`};}if(parsed&&parsed.schemaVersion==='learnit-content-v2'){const activities=Array.isArray(parsed.activities)?parsed.activities.length:0;return {ok:true,kind:'course',label:`Parcours Learn-it · ${activities} activités`};}return {ok:true,kind:'json',label:'JSON valide · format à contrôler avec Vérifier'};}catch(e){return {ok:false,kind:'invalid',label:'JSON illisible : '+(e&&e.message?e.message:e)};}}
  function setStatus(message,level){const el=document.getElementById('importFileStatus');if(!el)return;el.textContent=message;el.dataset.level=level||'info';}
  function syncDraft(text){const rt=runtime();const area=document.getElementById('importDraft');if(!area)return {ok:false,error:'Zone d’import introuvable.'};area.value=String(text||'');area.dispatchEvent(new Event('input',{bubbles:true}));if(rt){rt.contentStore.importDraft=area.value;rt.contentStore.importPreviewConfirmed=false;}return {ok:true};}
  async function readFiles(files){const rt=runtime();const list=Array.from(files||[]);if(!list.length)return {ok:false,error:'Aucun fichier sélectionné.'};const invalid=list.find(file=>!fileLooksJson(file));if(invalid){const warning='Le fichier ne ressemble pas à un JSON : '+(invalid.name||'sans nom');setStatus(warning,'warn');return {ok:false,error:warning};}try{setStatus(`Lecture de ${list.length} fichier${list.length>1?'s':''}…`,'info');const entries=[];for(const file of list)entries.push({name:file.name,text:await file.text(),size:file.size,type:file.type});const summaries=entries.map(e=>summarizeJson(e.text));if(summaries.some(x=>!x.ok)){const bad=summaries.find(x=>!x.ok);setStatus(bad.label,'warn');return {ok:false,error:bad.label};}const draft=list.length===1?entries[0].text:JSON.stringify(rt.contentStore.combineImportTexts(entries),null,2);const sync=syncDraft(draft);if(!sync.ok){setStatus(sync.error,'warn');return sync;}rt.contentStore.importSourceEntries=entries;const total=entries.reduce((n,e)=>n+Number(e.size||0),0);const result={schema:'learnit.import_file_selector.rc612.v2',ok:true,files:entries.map(e=>({name:e.name,size:e.size,type:e.type})),summaries,combined:list.length>1,loadedAt:new Date().toISOString()};window.__LEARNIT_IMPORT_FILE_LAST__=result;setStatus(`${list.length} fichier${list.length>1?'s':''} chargé${list.length>1?'s':''} (${formatBytes(total)}). Prévisualisez les changements avant import.`,'ok');if(rt.render)rt.render();return result;}catch(e){const error='Lecture fichier impossible : '+(e&&e.message?e.message:e);setStatus(error,'warn');return {ok:false,error};}}
  async function readFile(file){return readFiles(file?[file]:[]);}
  function onClick(event){const t=event.target;if(!t||!t.closest)return;const entry=t.closest('[data-rc580-intent]');if(entry){event.preventDefault();event.stopPropagation();handleEntryIntent(entry.dataset.rc580Intent,entry.dataset.mode,entry.dataset.course);return;}const smart=t.closest('[data-rc239-action]');if(smart){event.preventDefault();handleSmartResume(smart.dataset.rc239Action);return;}const review=t.closest('[data-rc241-action]');if(review){event.preventDefault();handleReviewFreedom(review.dataset.rc241Action);return;}const due=t.closest('[data-rc247-action="start-due"]');if(due){event.preventDefault();handleSpacedReview(due.dataset.course);return;}const mode=t.closest('[data-rc248-mode]');if(mode){event.preventDefault();handleTrainingMode(mode.dataset.rc248Mode);return;}const progress=t.closest('[data-rc243-action="export-progress"]');if(progress){event.preventDefault();downloadJson(runtime(),'learnit_progress_summary.json',progressSummary(runtime(),progress.dataset.course));return;}}
  function onChange(event){const input=event.target&&event.target.closest&&event.target.closest('#importFile');if(input){readFiles(input.files);return;}const policy=event.target&&event.target.closest&&event.target.closest('#importCollisionPolicy');if(policy){const rt=runtime();if(rt){rt.contentStore.importCollisionPolicy=policy.value||'rename';rt.contentStore.importPreviewConfirmed=false;rt.contentStore.importPreviewPlan=null;rt.render();}}}
  function onDragOver(event){const panel=event.target&&event.target.closest&&event.target.closest('.import-file-panel');if(!panel)return;event.preventDefault();panel.classList.add('is-dragover');if(event.dataTransfer)event.dataTransfer.dropEffect='copy';}
  function onDragLeave(event){const panel=event.target&&event.target.closest&&event.target.closest('.import-file-panel');if(panel)panel.classList.remove('is-dragover');}
  function onDrop(event){const panel=event.target&&event.target.closest&&event.target.closest('.import-file-panel');if(!panel)return;event.preventDefault();panel.classList.remove('is-dragover');readFiles(event.dataTransfer&&event.dataTransfer.files);}
  if(!window.__LEARNIT_ROUTE_STATIC_ACTIONS_INSTALLED__){
    window.__LEARNIT_ROUTE_STATIC_ACTIONS_INSTALLED__=true;
    document.addEventListener('click',onClick,true);
    document.addEventListener('change',onChange,true);
    document.addEventListener('dragover',onDragOver,true);
    document.addEventListener('dragleave',onDragLeave,true);
    document.addEventListener('drop',onDrop,true);
  }
  window.LearnItSmartResume=Object.freeze({schema:'learnit.smart_resume.rc565.v1',decision:smartResumeDecision});
  window.LearnItNonBlockingReview=Object.freeze({schema:'learnit.non_blocking_review.rc241.v1',policy:nonBlockingPolicy});
  window.LearnItSpacedReview=Object.freeze({schema:'learnit.spaced_review.v1',due:spacedReviewDue});
  window.LearnItTrainingModes=Object.freeze({schema:'learnit.session_modes.v1',modes,handleEntryIntent});
  window.LearnItProgressExport=Object.freeze({schema:'learnit.progress_export.rc594.v1',summary:progressSummary});
  window.LearnItImportFileSelector=Object.freeze({schema:'learnit.import_file_selector.rc612.v2',fileLooksJson,summarizeJson,formatBytes,syncDraft,readFile,readFiles});
  window.LearnItRouteStaticActions=Object.freeze({schema:SCHEMA,smartResumeDecision,nonBlockingPolicy,spacedReviewDue,modes,progressSummary,handleEntryIntent});
})();
