    function buildBilanProjection(runtime){
      const last=runtime.appState.state.lastBilan||runtime.session.summary();
      const mastery=runtime.session.mastery();
      const review=(last.review||[]);
      const hasAny=runtime.session.session.status==='completed'||Object.keys(runtime.session.session.answers||{}).length>0||last.done>0;
      const enriched=buildEnrichedBilan(runtime,last,mastery);
      const progress=runtime.appState.courseProgress(runtime.contentStore.activeCourseId);
      const learningModel=window.LearnItRemediationModel;
      const duePlan=(learningModel&&typeof learningModel.buildDuePlan==='function')?learningModel.buildDuePlan(runtime.contentStore.content,progress,{maxItems:8}):{ok:false,queue:[],rows:[],totalDue:0,deferredCount:0};
      const next=review.length?enriched.nextBestStep:(duePlan.ok?`Réviser ${duePlan.queue.length} activité${duePlan.queue.length>1?'s':''} arrivée${duePlan.queue.length>1?'s':''} à échéance.`:(hasAny?'Consolider avec une nouvelle série.':'Faire une première séance.'));
      const reviewRows=mastery.rows.filter(r=>r.review).map(r=>({id:r.id,objective:r.objective}));
      const targetedPlan=buildTargetedReviewPlan(runtime);
      const loopSummary=buildLearningLoopSummary(runtime,last,mastery,enriched);
      const primary=review.length?{action:'start-review-session',label:'Reprendre les points à revoir'}:(duePlan.ok?{action:'start-spaced-review',label:`Réviser maintenant · ${duePlan.queue.length}`}:(hasAny?{action:'new-session',label:'Nouvelle séance'}:{nav:'learn',label:'Retour à l’action'}));
      return {surface:'bilan',intent:SURFACE_OWNERSHIP.bilan.question,hasAny,last,mastery,reviewRows,next,enriched,targetedPlan,duePlan,loopSummary,primary};
    }
    function countMapPush(map,key,value){const k=String(key||'').trim()||'non renseigné';if(!map[k])map[k]=[];map[k].push(value);}
    function summarizeMap(map,limit=6){return Object.entries(map).map(([label,items])=>({label,count:items.length,items})).sort((a,b)=>b.count-a.count||a.label.localeCompare(b.label)).slice(0,limit);}
    function firstNonEmpty(...values){for(const v of values){if(Array.isArray(v)&&v.length)return v;if(typeof v==='string'&&v.trim())return v.trim();}return '';}
    function activityPedagogy(activity){
      const p=normalizePedagogy(activity||{});
      return {
        objective:firstNonEmpty(p.objective,activity&&activity.objective),
        difficulty:firstNonEmpty(p.difficulty),
        phase:firstNonEmpty(p.learning_phase),
        skills:Array.isArray(p.skills)?p.skills:[],
        common_errors:Array.isArray(p.common_errors)?p.common_errors:[],
        remediation:firstNonEmpty(activity&&activity.remediation, p.feedback&&p.feedback.remediation, p.feedback&&p.feedback.error),
        success:firstNonEmpty(activity&&activity.why, p.feedback&&p.feedback.success)
      };
    }
    function buildEnrichedBilan(runtime,last,mastery){
      const answers=runtime.session.session.answers||{};
      const activities=runtime.contentStore.content.activities||[];
      const byId=new Map(activities.map(a=>[a.id,a]));
      const reviewed=(last.review||[]).map(id=>byId.get(id)).filter(Boolean);
      const seen=Object.keys(answers).map(id=>byId.get(id)).filter(Boolean);
      const wrong=reviewed.length?reviewed:seen.filter(a=>answers[a.id]&&!answers[a.id].correct);
      const correct=seen.filter(a=>answers[a.id]&&answers[a.id].correct);
      const objectives={}, phases={}, difficulties={}, typeReview={}, commonErrors=[];
      for(const a of wrong){const meta=activityPedagogy(a);countMapPush(objectives,meta.objective||a.objective||a.question,a);countMapPush(phases,meta.phase,a);countMapPush(difficulties,meta.difficulty,a);countMapPush(typeReview,a.type,a);for(const e of meta.common_errors)if(e)commonErrors.push(String(e));}
      const priorityObjectives=summarizeMap(objectives,4).map(row=>({objective:row.label,count:row.count,ids:row.items.map(a=>a.id),activities:row.items.map(a=>({id:a.id,type:a.type,question:a.question,remediation:activityPedagogy(a).remediation}))}));
      const phaseRows=summarizeMap(phases,5); const difficultyRows=summarizeMap(difficulties,5); const typeRows=summarizeMap(typeReview,5);
      const metadataStats={seen:seen.length,review:wrong.length,withDifficulty:seen.filter(a=>activityPedagogy(a).difficulty).length,withPhase:seen.filter(a=>activityPedagogy(a).phase).length,withCommonErrors:seen.filter(a=>activityPedagogy(a).common_errors.length).length};
      const metadataCoverage=seen.length?Math.round(100*((metadataStats.withDifficulty+metadataStats.withPhase+metadataStats.withCommonErrors)/(seen.length*3))):0;
      let nextBestStep='Reprendre les points à revoir.';
      if(!wrong.length&&seen.length)nextBestStep='Consolider avec une nouvelle série ou passer au parcours suivant.';
      else if(priorityObjectives.length)nextBestStep=`Reprendre d’abord : ${priorityObjectives[0].objective}.`;
      const explanations=[];
      if(priorityObjectives.length)explanations.push(`${priorityObjectives.length} objectif${priorityObjectives.length>1?'s':''} à revoir.`);
      if(difficultyRows.length&&difficultyRows[0].label!=='non renseigné')explanations.push(`Difficulté dominante : ${difficultyRows[0].label}.`);
      if(phaseRows.length&&phaseRows[0].label!=='non renseigné')explanations.push(`Phase à renforcer : ${phaseRows[0].label}.`);
      if(!metadataCoverage&&seen.length)explanations.push('Métadonnées pédagogiques limitées : diagnostic basé sur objectifs, types et remédiations existants.');
      const remediationHints=wrong.map(a=>({id:a.id,objective:activityPedagogy(a).objective||a.objective,remediation:activityPedagogy(a).remediation||a.remediation||'Reprendre la règle puis retenter.',type:a.type})).slice(0,4);
      return {ok:true,nextBestStep,priorityObjectives,phaseRows,difficultyRows,typeRows,commonErrors:[...new Set(commonErrors)].slice(0,6),metadataStats,metadataCoverage,explanations,remediationHints,correctCount:correct.length,reviewCount:wrong.length};
    }
    function renderEnrichedBilanPanel(enriched){
      if(!enriched||!enriched.reviewCount)return '';
      const panels=[];
      const priorities=enriched.priorityObjectives||[];
      if(priorities.length){
        const priorityHtml=`<ul class="bilan-priorities">${priorities.map(p=>`<li><strong>${escapeHtml(p.objective)}</strong><br><span class="tiny">${p.count} activité${p.count>1?'s':''} à reprendre</span>${p.activities&&p.activities[0]&&p.activities[0].remediation?`<br><span class="tiny">Piste : ${escapeHtml(p.activities[0].remediation)}</span>`:''}</li>`).join('')}</ul>`;
        panels.push(`<div class="bilan-panel"><h3>Priorités de reprise</h3>${priorityHtml}</div>`);
      }
      if(enriched.commonErrors&&enriched.commonErrors.length){
        panels.push(`<div class="bilan-panel"><h3>Erreurs probables</h3><ul class="bilan-list">${enriched.commonErrors.map(e=>`<li>${escapeHtml(e)}</li>`).join('')}</ul></div>`);
      }
      // RC157: remédiations déjà affichées dans Priorités de reprise ; ne pas dupliquer côté apprenant.
      return panels.length?`<div class="bilan-enriched">${panels.join('')}</div>`:'';
    }
    function buildTargetedReviewPlan(runtime){
      const last=runtime.appState.state.lastBilan||runtime.session.summary();
      const enriched=buildEnrichedBilan(runtime,last,runtime.session.mastery());
      const activities=runtime.contentStore.content.activities||[];
      const progress=runtime.appState.courseProgress(runtime.contentStore.activeCourseId);
      const model=window.LearnItRemediationModel;
      if(model&&typeof model.buildPlan==='function'){
        const plan=model.buildPlan(runtime.contentStore.content,progress,last,{maxItems:5,maxRounds:2});
        const byId=new Map(activities.map(a=>[a.id,a]));
        const objectives=[];const hints=[];const typeCounts={};
        for(const reason of (plan.reasons||[])){
          const a=byId.get(reason.id);const source=byId.get(reason.sourceId)||a;
          if(a)typeCounts[a.type]=(typeCounts[a.type]||0)+1;
          if(source&&source.objective&&!objectives.some(o=>o.objective===source.objective))objectives.push({objective:source.objective,count:1,ids:[source.id]});
          if(a)hints.push({id:a.id,sourceId:reason.sourceId,kind:reason.kind,objective:(source&&source.objective)||a.objective,remediation:(source&&source.remediation)||a.remediation||'Reprendre la règle puis retenter.',type:a.type});
        }
        return {...plan,objectives,hints,typeCounts,metadataCoverage:enriched.metadataCoverage||0,generatedAt:nowIso(),source:'remediation-model-v1'};
      }
      const valid=new Set(activities.map(a=>a.id));
      const sourceReview=(last.review||[]).filter(id=>valid.has(id));
      const priorityIds=[];
      for(const p of (enriched.priorityObjectives||[])) for(const id of (p.ids||[])) if(valid.has(id)&&!priorityIds.includes(id)) priorityIds.push(id);
      const queue=[...priorityIds, ...sourceReview.filter(id=>!priorityIds.includes(id))];
      const focus=(enriched.priorityObjectives&&enriched.priorityObjectives[0])?enriched.priorityObjectives[0].objective:'';
      const objectives=(enriched.priorityObjectives||[]).map(p=>({objective:p.objective,count:p.count,ids:p.ids||[]}));
      const hints=(enriched.remediationHints||[]).filter(h=>queue.includes(h.id)).map(h=>({id:h.id,objective:h.objective,remediation:h.remediation,type:h.type}));
      const typeCounts={};
      for(const id of queue){const a=activities.find(x=>x.id===id); if(a) typeCounts[a.type]=(typeCounts[a.type]||0)+1;}
      return {ok:queue.length>0,queue,summary:queue.length?`Reprise ciblée sur ${queue.length} activité${queue.length>1?'s':''}`:'Aucun point à reprendre',focus,objectives,hints,typeCounts,metadataCoverage:enriched.metadataCoverage||0,generatedAt:nowIso(),maxRounds:2,source:'legacy-fallback'};
    }
    function buildLearningLoopSummary(runtime,last,mastery,enriched){
      const summary=last||runtime.session.summary();
      const modeModel=window.LearnItSessionModeModel;
      const policy=modeModel&&typeof modeModel.sessionPolicy==='function'?modeModel.sessionPolicy(summary):{id:summary&&summary.mode||'training',label:'Séance'};
      const isTargeted=summary&&summary.mode==='targeted-review';
      const isSpaced=summary&&summary.mode==='spaced-review';
      const visibleMode=['review','validation','diagnostic'].includes(policy.id);
      if(!isTargeted&&!isSpaced&&!visibleMode)return {visible:false};
      const review=(summary.review||[]);
      const plan=isSpaced?(summary.reviewPlan||{}):(isTargeted?(summary.remediation||{}):(summary.modePlan||{}));
      const total=summary.total||plan.queueLength||0;
      const correct=summary.correct||0;
      const focus=plan.focus||((plan.objectives&&plan.objectives[0]&&plan.objectives[0].objective)||(policy.id==='review'?'Consolidation':'Résultat de séance'));
      const done=review.length===0&&total>0;
      const partial=review.length>0;
      const outcome=summary.modeOutcome||(modeModel&&typeof modeModel.outcome==='function'?modeModel.outcome(summary):null);
      const title=outcome&&outcome.title?outcome.title:(done?(isSpaced?'Révision terminée':'Reprise réussie'):(isSpaced?'Révision à consolider':'Reprise à consolider'));
      const detail=outcome&&outcome.detail?outcome.detail:(done?(isSpaced?'Les éléments prévus ont été retravaillés.':'Le point ciblé est maintenant maîtrisé dans cette reprise.'):`${review.length} point${review.length>1?'s':''} reste${review.length>1?'nt':''} à revoir.`);
      const next=done?'Continuer librement ou revenir plus tard.':'Relancer une reprise courte sur les points restants.';
      return {visible:true,ok:done,partial,title,detail,next,focus,total,correct,reviewCount:review.length,mode:policy.id,modeLabel:policy.label,mastered:mastery&&mastery.mastered,review:mastery&&mastery.review,deferred:!!(outcome&&outcome.deferred),recordedInProgress:outcome?outcome.recordedInProgress:true};
    }
    function renderLearningLoopPanel(loop){
      if(!loop||!loop.visible)return '';
      const cls=loop.ok?'loop-panel':'loop-panel warn';
      const action=loop.ok?'<button data-action="new-session">Nouvelle série</button>':'<button class="primary" data-action="start-review-session">Reprendre encore</button>';
      const kicker=loop.modeLabel?`Résultat · ${escapeHtml(loop.modeLabel)}`:'Après reprise';return `<div class="${cls}"><div class="loop-kicker">${kicker}</div><div class="loop-title">${escapeHtml(loop.title)}</div><p class="loop-detail">${escapeHtml(loop.detail)}</p><div class="bilan-chip-row"><span class="loop-chip">${escapeHtml(loop.focus)}</span><span class="loop-chip">${loop.correct}/${loop.total} réussi${loop.correct>1?'s':''}</span></div><p class="loop-detail">${escapeHtml(loop.next)}</p><div class="loop-actions">${action}<button data-nav="library">Choisir un parcours</button></div></div>`;
    }

    function renderRemediationBanner(session,activity){
      const targeted=session.mode==='targeted-review';
      const spaced=session.mode==='spaced-review';
      if(!targeted&&!spaced)return '';
      const plan=targeted?(session.remediation||{}):(session.reviewPlan||{});
      const hint=targeted?(plan.hints||[]).find(h=>activity&&h.id===activity.id):null;
      const focus=plan.focus||(activity&&activity.objective)||(spaced?'Consolidation':'Point à retravailler');
      const piste=hint&&hint.remediation?`<div class="remediation-mini"><strong>Piste</strong><span>${escapeHtml(hint.remediation)}</span></div>`:'';
      const label=spaced?'Révision planifiée':'À retravailler';
      return `<div class="remediation-banner" role="note"><div class="remediation-label">${label}</div><div class="focus">${escapeHtml(focus)}</div>${piste}</div>`;
    }
    function normalizeSurfaceText(text){return String(text||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').trim().split(/\s+/).filter(w=>w.length>3);}
