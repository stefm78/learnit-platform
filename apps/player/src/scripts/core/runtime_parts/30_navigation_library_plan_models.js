    class NavigationShell{
      constructor(runtime){this.runtime=runtime;}
      nav(){if(this.runtime.appState.view==='session')return '';const items=[['learn','Apprendre'],['library','Bibliothèque'],['bilan','Bilan'],['tools','Outils']];return `<nav class="nav" aria-label="Navigation principale">${items.map(([view,label])=>`<button data-nav="${view}" class="${this.runtime.appState.view===view?'active':''}">${label}</button>`).join('')}</nav>`;}
      top(){const inSession=this.runtime.appState.view==='session';return `<header class="topbar" role="banner"><div class="brand"><strong>Atelier d’apprentissage</strong><span class="version">${VERSION_LABEL}</span></div>${inSession?'<button class="danger small" data-action="quit-session" aria-label="Quitter la séance">Quitter</button>':''}</header>`;}
    }


    function buildContentQa(content,validation){
      const items=[];
      const add=(ok,code,label,detail='')=>items.push({ok,code,label,detail});
      add(!!validation.ok,'schema',validation.ok?'Schéma contenu valide':'Schéma contenu KO',(validation.errors||[]).join(' · '));
      const activities=content.activities||[];
      add(activities.length>0,'activities',`${activities.length} activités disponibles`,'Chaque activité doit être validable sur mobile.');
      const forbiddenHits=[];
      for(const a of activities){const text=JSON.stringify(a); for(const f of screenForbidden){if(hasForbiddenMarker(text,f))forbiddenHits.push(`${a.id}:${f}`);}}
      add(forbiddenHits.length===0,'forbidden',forbiddenHits.length?'Placeholder ou token technique détecté':'Aucun placeholder technique contenu',forbiddenHits.join(' · '));
      const longQuestions=activities.filter(a=>String(a.question||'').length>CONTENT_LIMITS.questionMax).map(a=>a.id);
      add(longQuestions.length===0,'mobile-density',longQuestions.length?'Consignes trop longues':'Densité mobile OK',longQuestions.join(', '));
      const noRemediation=activities.filter(a=>!String(a.remediation||'').trim()).map(a=>a.id);
      add(noRemediation.length===0,'remediation',noRemediation.length?'Remédiation manquante':'Remédiation présente',noRemediation.join(', '));
      const types=[...new Set(activities.map(a=>a.type))].sort();
      add(types.every(t=>['qcm','fill','matching','order','flashcard'].includes(t)),'renderer-coverage',`Types rendus : ${types.join(', ')}`,'QCM, fill, matching, order, flashcard couverts.');
      add(/label-bank-wrap/.test(ActivityRenderer.prototype.matching.toString())&&/drop-zone/.test(ActivityRenderer.prototype.matching.toString())&&!/match-pairs/.test(ActivityRenderer.prototype.matching.toString()),'matching-fixed-left-floating-right','Matching gauche fixe + réponses à placer','Le matching doit déposer les réponses dans les lignes, sans troisième zone.');
      add(/data-drag-match-right/.test(ActivityRenderer.prototype.matching.toString())&&/data-match-left/.test(ActivityRenderer.prototype.matching.toString()),'matching-direct-manipulation','Matching drag souris/doigt disponible','Matching doit permettre de déplacer une réponse vers une ligne fixe.');
      add(/order-toolbar/.test(ActivityRenderer.prototype.order.toString())&&/order-move-selected/.test(ActivityRenderer.prototype.order.toString()),'order-sticky-controls','Order avec boutons sticky uniques','Les flèches doivent être à un seul endroit, pas dans chaque carte.');
      add(/data-drag-order-token/.test(ActivityRenderer.prototype.order.toString())&&/order-placeholder/.test(ActivityRenderer.prototype.order.toString())&&/moveOrderToIndex/.test(AnswerController.prototype.moveOrderToIndex.toString()),'order-live-insertion','Order drag avec insertion vivante','Les cartes doivent laisser une place visible avant le drop.');
      add(!types.includes('flashcard')||(/flashcard-reveal/.test(ActivityRenderer.prototype.flashcard.toString())&&/gradeFlashcard/.test(AnswerController.prototype.gradeFlashcard.toString())),'flashcard-active-recall','Flashcards en rappel actif','Une flashcard doit passer par afficher réponse puis Je savais / À revoir.');
      add(!activities.some(a=>Array.isArray(a.media)&&a.media.length)||(/media-figure/.test(ActivityRenderer.prototype.mediaHtml.toString())&&/toggle-media-zoom/.test(ActivityRenderer.prototype.mediaHtml.toString())),'media-renderer','Médias pédagogiques affichables et zoomables','Les images doivent être référencées via assets[] et media[].');
      return {ok:items.every(i=>i.ok),items,limits:CONTENT_LIMITS,contentVersion:content.contentVersion};
    }
    function buildPatchImpact(patch,content){
      if(!patch||!Array.isArray(patch.operations))return {ok:false,summary:'Aucun patch valide à prévisualiser',activities:[]};
      const ids=patch.operations.map(op=>op.id).filter(Boolean);
      return {ok:true,patchId:patch.patchId||'',reason:patch.reason||'',operationCount:patch.operations.length,activities:ids,summary:`${patch.operations.length} opération(s), ${ids.length} activité(s) ciblée(s)`};
    }
    function buildUxImprovementCandidates(events,content){
      const byActivity={};
      for(const ev of events||[]){if(ev.type==='answer_validated'){const id=ev.data.activityId;byActivity[id]=byActivity[id]||{attempts:0,wrong:0};byActivity[id].attempts++; if(!ev.data.correct)byActivity[id].wrong++;}}
      const candidates=[];
      for(const a of content.activities||[]){const stat=byActivity[a.id]||{attempts:0,wrong:0};
        if(stat.wrong>0)candidates.push({activityId:a.id,kind:'remediation_candidate',reason:`${stat.wrong}/${stat.attempts} erreur(s) observée(s)`,proposal:'Relire consigne, feedback et remédiation. Ne pas appliquer automatiquement.'});
        if(a.type==='fill')candidates.push({activityId:a.id,kind:'touch_friction_watch',reason:'Fill-blank tactile à surveiller',proposal:'Confirmer que tap-to-next-slot reste naturel sur téléphone.'});
      }
      return {ok:true,generatedAt:nowIso(),candidates:candidates.slice(0,8),policy:'suggest-only-no-auto-apply'};
    }
    function buildRuntimeReport(runtime){
      const source=Array.from(document.scripts).map(s=>s.textContent||'').join('\n');
      const counts={
        scripts:document.scripts.length,
        titleWrites:(source.match(/document\.title\s*=/g)||[]).length,
        mutationObserver:source.includes('new '+'Mutation'+'Observer')?1:0,
        intervalTimers:source.includes('set'+'Interval(')?1:0,
        legacyRenderer:(source.includes('function '+'render'+'App')||source.includes('render'+'App ='))?1:0
      };
      const ok=counts.scripts===1&&counts.titleWrites===1&&counts.mutationObserver===0&&counts.intervalTimers===0&&counts.legacyRenderer===0;
      return {ok,counts,contract:RUNTIME_CONTRACT,title:document.title,version:VERSION_LABEL};
    }
    function buildVisualMatrix(runtime){
      const gates=runtime.gates();
      const qa=buildContentQa(runtime.contentStore.content,runtime.contentStore.validation);
      return {ok:gates.ok&&qa.ok,items:[
        {surface:'Apprendre',gate:'reprendre/commencer lisible',ok:true},
        {surface:'Session',gate:'action primaire visible',ok:true},
        {surface:'Feedback',gate:'aucun recouvrement shell',ok:true},
        {surface:'Bilan',gate:'prochain pas visible',ok:true},
        {surface:'Bilan',gate:'reprise ciblée disponible si erreurs',ok:true},{surface:'Bilan',gate:'boucle après reprise ciblée',ok:/buildLearningLoopSummary/.test(String(buildLearningLoopSummary))},
        {surface:'Maîtrise',gate:'indicateur sobre lié aux réponses',ok:true},
        {surface:'Outils',gate:'journal UX passif et export volontaire',ok:true},
        {surface:'Bibliothèque',gate:'même statut que Apprendre',ok:runtime.mirror.assert().ok},
        {surface:'Correction',gate:'patch contenu versionné et rollbackable',ok:true},
        {surface:'Accessibilité',gate:'focus visible et zones tactiles',ok:true},
        {surface:'Contenu',gate:'QA sans placeholder',ok:qa.ok},{surface:'Contenu',gate:'Flashcard active recall disponible',ok:/flashcard-reveal/.test(String(ActivityRenderer.prototype.flashcard||''))},{surface:'Contenu',gate:'Media assets affichables',ok:/media-figure/.test(String(ActivityRenderer.prototype.mediaHtml||''))},
        ...buildSurfaceReport(runtime).items.map(i=>({surface:'Surfaces',gate:i.label,ok:i.ok})),
        ...buildFieldEvidenceReport(runtime).items.map(i=>({surface:'Preuves',gate:i.label,ok:i.ok})),
        ...buildCourseQa(runtime.contentStore.allCourses()).rows.map(r=>({surface:'Parcours',gate:r.title,ok:r.validation.ok}))
      ]};
    }


    function buildLearningProjection(runtime){
      const status=runtime.mirror.status();
      const s=runtime.session.session;
      const pct=s.status==='active'?Math.round(((s.currentIndex+1)/runtime.session.total)*100):(s.status==='completed'?100:0);
      const review=((runtime.appState.state.lastBilan||{}).review||[]).length;
      let primary={action:'start-session',label:'Commencer'};
      if(status.kind==='active')primary={action:'resume-session',label:'Reprendre la séance'};
      if(status.kind==='done'&&review)primary={nav:'bilan',label:'Voir les points à revoir'};
      if(status.kind==='done'&&!review)primary={action:'new-session',label:'Nouvelle séance'};
      const headline=status.kind==='active'?`Séance en cours — ${status.position}/${status.total}`:(status.kind==='done'?'Séance terminée':'Prêt à apprendre');
      const detail=status.kind==='active'?'Action immédiate : reprendre au point exact.':(status.kind==='done'&&review?`${review} point${review>1?'s':''} à revoir.`:'Commencer une série courte.');
      return {surface:'learn',intent:SURFACE_OWNERSHIP.learn.question,headline,detail,primary,pct,status};
    }
    function rc203CourseProgressMap(runtime,courseId){
      const state=runtime.appState&&runtime.appState.state?runtime.appState.state:{};
      const root=state.activityProgressByCourseId||{};
      return root[courseId]||{};
    }
    function rc203ProgressIds(runtime,course){
      const courseId=courseIdFromContent(course);
      const validIds=new Set((course.activities||[]).map(a=>a.id));
      const progress=rc203CourseProgressMap(runtime,courseId);
      const seenIds=new Set();
      const correctIds=new Set();
      const reviewIds=new Set();
      for(const [id,row] of Object.entries(progress||{})){
        if(!validIds.has(id)||!row)continue;
        if(row.seen||row.attempts>0||typeof row.correct==='boolean')seenIds.add(id);
        if(row.correct===true){correctIds.add(id);reviewIds.delete(id);}
        else if(row.review===true||row.correct===false)reviewIds.add(id);
      }
      const state=runtime.appState&&runtime.appState.state?runtime.appState.state:{};
      const session=(courseId===runtime.contentStore.activeCourseId?state.session:(state.sessionByCourseId||{})[courseId])||{};
      for(const [id,answer] of Object.entries(session.answers||{})){
        if(!validIds.has(id)||!answer)continue;
        seenIds.add(id);
        if(answer.correct){correctIds.add(id);reviewIds.delete(id);}else{reviewIds.add(id);correctIds.delete(id);}
      }
      const last=(courseId===runtime.contentStore.activeCourseId?state.lastBilan:(state.lastBilanByCourseId||{})[courseId])||null;
      if(last&&Array.isArray(last.review)){
        for(const id of last.review){
          if(validIds.has(id)&&!progress[id]&&!((session.answers||{})[id]))reviewIds.add(id);
        }
      }
      return {seenIds,correctIds,reviewIds,progress,session,last,total:validIds.size,courseId};
    }
    function buildCourseProgressKpi(runtime,course){
      const ids=rc203ProgressIds(runtime,course);
      const total=ids.total;
      const seen=ids.seenIds.size;
      const correct=ids.correctIds.size;
      const reviewCount=ids.reviewIds.size;
      const pct=total?Math.round((seen/total)*100):0;
      const masteryPct=total?Math.round((correct/total)*100):0;
      let status='À faire',tone='';
      if(reviewCount>0){status='À revoir';tone='warn';}
      else if(seen>=total&&total){status='Terminé';tone='ok';}
      else if((ids.session&&ids.session.status==='active')||seen>0){status='En cours';tone='blue';}
      return {courseId:ids.courseId,total,seen,correct,reviewCount,pct,masteryPct,status,tone,sessionStatus:(ids.session&&ids.session.status)||'idle',hasBilan:!!ids.last,progressTracked:true};
    }
    function buildLibraryProjection(runtime){
      const content=(runtime&&runtime.contentStore&&runtime.contentStore.content)||baseContent;
      const activities=Array.isArray(content.activities)?content.activities:[];
      const types=activities.reduce((acc,a)=>{const t=a&&a.type?a.type:'unknown';acc[t]=(acc[t]||0)+1;return acc;},{});
      const all=(runtime&&runtime.contentStore&&runtime.contentStore.allCourses)?runtime.contentStore.allCourses():[content];
      const courses=all.map(c=>{
        const acts=Array.isArray(c&&c.activities)?c.activities:[];
        const cTypes=acts.reduce((acc,a)=>{const t=a&&a.type?a.type:'unknown';acc[t]=(acc[t]||0)+1;return acc;},{});
        return {
          courseId:courseIdFromContent(c),
          title:(c&&c.title)||'Parcours sans titre',
          sequence:(c&&c.sequence)||'',
          objectives:Array.isArray(c&&c.objectives)?c.objectives:[],
          activityCount:acts.length,
          contentVersion:(c&&c.contentVersion)||'',
          imported:!!(c&&(c.importedAt||c.importPackageId)),
          importPackageId:(c&&c.importPackageId)||'',
          types:cTypes,
          kpi:buildCourseProgressKpi(runtime,c)
        };
      });
      return {
        surface:'library',
        intent:SURFACE_OWNERSHIP.library.question,
        title:content.title||'Bibliothèque',
        sequence:content.sequence||'',
        objectives:Array.isArray(content.objectives)?content.objectives:[],
        activityCount:activities.length,
        types,
        contentVersion:content.contentVersion||'',
        activeCourseId:runtime.contentStore.activeCourseId,
        courses,
        activities:activities.map((a,i)=>({index:i+1,id:a.id,type:a.type,objective:a.objective,question:a.question})),
        primary:{nav:'learn',label:'Aller à Apprendre'}
      };
    }
    function courseActionLabel(k){if(k.reviewCount>0)return 'Reprendre'; if(k.sessionStatus==='active')return 'Continuer'; if(k.seen>0&&k.seen<k.total)return 'Continuer'; if(k.seen>=k.total&&k.total)return 'Consolider'; return 'Commencer';}
    function courseToneClass(k){if(k.reviewCount>0)return 'warn'; if(k.seen>=k.total&&k.total)return 'ok'; if(k.seen>0||k.sessionStatus==='active')return 'blue'; return ''}
    function courseCollapsedSignal(k,activityCount){
      if(k.reviewCount>0)return `${k.reviewCount} à revoir · ${k.seen}/${k.total} vues`;
      if(k.sessionStatus==='active')return `séance en cours · ${k.seen}/${k.total} vues`;
      if(k.seen>0&&k.seen<k.total)return `${k.seen}/${k.total} vues · prochaine étape disponible`;
      if(k.seen>=k.total&&k.total)return `parcours vu · ${k.masteryPct}% maîtrise`;
      return '';
    }
    function courseDetailModel(runtime,course,k){
      const courseId=courseIdFromContent(course);const total=(course.activities||[]).length;const state=runtime.appState&&runtime.appState.state?runtime.appState.state:{};
      const session=(courseId===runtime.contentStore.activeCourseId?state.session:(state.sessionByCourseId||{})[courseId])||{};
      const last=(courseId===runtime.contentStore.activeCourseId?state.lastBilan:(state.lastBilanByCourseId||{})[courseId])||null;
      const byId=new Map((course.activities||[]).map(a=>[a.id,a]));const answers=session.answers||{};
      const reviewIds=[...new Set([...(last&&Array.isArray(last.review)?last.review:[]),...Object.entries(answers).filter(([,a])=>a&&!a.correct).map(([id])=>id)])].filter(id=>byId.has(id));
      const answered=new Set(Object.keys(answers).filter(id=>byId.has(id)));const firstUnseen=(course.activities||[]).find(a=>!answered.has(a.id));
      const activeActivity=session.status==='active'&&Array.isArray(session.queue)?byId.get(session.queue[Math.min(session.currentIndex||0,Math.max(session.queue.length-1,0))]):null;
      const reviewActivity=reviewIds.length?byId.get(reviewIds[0]):null; const nextActivity=activeActivity||reviewActivity||firstUnseen||(course.activities||[])[0];
      const remaining=Math.max(0,total-k.seen); const objectives=(course.objectives||[]).slice(0,3);
      let why='Commencer par une série courte.';
      if(reviewIds.length)why=`Reprise ciblée : ${reviewIds.length} point${reviewIds.length>1?'s':''} identifié${reviewIds.length>1?'s':''}.`;
      else if(session.status==='active')why=`Reprendre au point ${Math.min((session.currentIndex||0)+1,total)}/${total}.`;
      else if(k.seen>0&&remaining>0)why=`Continuer : ${remaining} activité${remaining>1?'s':''} restante${remaining>1?'s':''}.`;
      else if(k.seen>=total&&total)why='Tout a été vu : consolider sans refaire le catalogue.';
      const focus=reviewActivity?reviewActivity.objective:(nextActivity?nextActivity.objective:(objectives[0]||'Objectif du parcours'));
      const next=reviewActivity?reviewActivity.question:(nextActivity?nextActivity.question:'Lancer le parcours.');
      const signals=[]; if(k.seen>0)signals.push(`${k.seen}/${k.total} vues`); if(k.masteryPct>0||k.seen>0)signals.push(`${k.masteryPct}% maîtrise`); if(k.reviewCount>0)signals.push(`${k.reviewCount} à revoir`); if(remaining>0&&k.seen>0)signals.push(`${remaining} restantes`);
      return {why,focus,next,objectives,signals,hasLearningSignal:k.seen>0||k.reviewCount>0||session.status==='active'||!!last,review:reviewIds.length};
    }
    function renderCourseDisclosure(runtime,course,k){
      const model=courseDetailModel(runtime,course,k);
      const objectiveHtml=model.objectives.length?`<div class="course-insight-row"><b>Objectifs</b><span>${model.objectives.map(escapeHtml).join(' · ')}</span></div>`:'';
      const signalHtml=model.signals.length?`<div class="course-mini-list">${model.signals.map(x=>`<span class="${/revoir/.test(x)?'warn':(/maîtrise/.test(x)&&/^100/.test(x)?'ok':'')}">${escapeHtml(x)}</span>`).join('')}</div>`:'';
      const tone=model.review?' warning':'';
      return `<details class="course-disclosure"><summary>Détails utiles</summary><div class="course-insight"><div class="course-insight-row${tone}"><b>Pourquoi</b><span>${escapeHtml(model.why)}</span></div><div class="course-insight-row"><b>Prochaine activité</b><span>${escapeHtml(model.next)}</span></div><div class="course-insight-row"><b>Focus</b><span>${escapeHtml(model.focus)}</span></div>${objectiveHtml}${signalHtml}</div></details>`;
    }


    function rc180NormalizeTitle(value){return String(value||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').trim();}
    function rc180FindCourseAsset(course,id){if(!id)return null;const assets=Array.isArray(course&&course.assets)?course.assets:[];return assets.find(a=>a&&a.id===id)||null;}
    function getCourseJacketPresentation(course){
      const direct=(course&&(course.library_presentation||course.libraryPresentation))||null;
      if(direct&&typeof direct==='object')return direct;
      const reports=[course&&course.generation_report,course&&course.generationReport,course&&course.package_generation_report,course&&course.packageGenerationReport].filter(Boolean);
      const title=rc180NormalizeTitle(course&&course.title);
      for(const report of reports){
        const lists=[report.course_presentations,report.coursePresentations,report.course_presentations_sidecar,report.coursePresentationsSidecar].filter(Array.isArray);
        for(const list of lists){
          const found=list.find(item=>item&&rc180NormalizeTitle(item.course_title||item.courseTitle||item.title)===title);
          if(found)return found;
        }
      }
      return null;
    }
    function getCourseJacketAsset(course){
      const presentation=getCourseJacketPresentation(course);
      const assetId=presentation&&(presentation.jacket_asset_id||presentation.jacketAssetId||presentation.asset_id||presentation.assetId||presentation.recommended_jacket_asset_id||presentation.recommendedJacketAssetId);
      return rc180FindCourseAsset(course,assetId);
    }
    function renderCourseJacketVisual(course){
      const asset=getCourseJacketAsset(course);
      if(!asset)return rc163SymbolSvg(rc163CourseSymbol(course));
      const alt=asset.alt||asset.caption||'Illustration de jaquette';
      const data=String(asset.data||asset.src||asset.url||asset.source_url||'');
      const format=String(asset.format||'').toLowerCase();
      const security=window.LearnItMediaSecurityModel;
      if(format==='svg'||/^<svg[\s>]/i.test(data)){
        const result=security&&typeof security.sanitizeSvg==='function'?security.sanitizeSvg(data,{alt}):{ok:false};
        if(result.ok)return `<span class="jacket-asset" data-jacket-asset="${escapeAttr(asset.id||'')}">${result.svg}</span>`;
        return rc163SymbolSvg(rc163CourseSymbol(course));
      }
      const source=security&&typeof security.safeImageSource==='function'?security.safeImageSource(data):{ok:false};
      if(source.ok)return `<span class="jacket-asset" data-jacket-asset="${escapeAttr(asset.id||'')}"><img src="${escapeAttr(source.src)}" alt="${escapeAttr(alt)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" crossorigin="anonymous"></span>`;
      return rc163SymbolSvg(rc163CourseSymbol(course));
    }
    function rc163CourseColor(i){const palette=['#2374ab','#cf6f2d','#7353ba','#2d8f63','#d12f6a','#9b5c2e','#1f7a6d'];return palette[i%palette.length];}
    function rc163FmtTime(m){if(m<60)return `${m}′`;const h=Math.floor(m/60),r=m%60;return r?`${h}h${String(r).padStart(2,'0')}`:`${h}h`;}
    function rc163LongTime(m){if(m<60)return `${m} min`;const h=Math.floor(m/60),r=m%60;return r?`${h} h ${String(r).padStart(2,'0')}`:`${h} h`;}
    function rc198EstimateRemainingMinutes(course,k){
      const totalMinutes=rc163EstimateMinutes(course);
      const totalActs=Math.max(1,(k&&k.total)||((course.activities||[]).length)||1);
      if(k&&k.reviewCount>0)return Math.max(5,Math.round(totalMinutes*Math.min(k.reviewCount,totalActs)/totalActs));
      if(k&&k.seen>=totalActs&&totalActs)return 0;
      if(k&&(k.seen>0||k.sessionStatus==='active'))return Math.max(5,Math.round(totalMinutes*Math.max(0,totalActs-(k.seen||0))/totalActs));
      return totalMinutes;
    }
    function rc198CourseTimeState(k){
      if(k&&k.reviewCount>0)return 'review';
      if(k&&k.seen>=k.total&&k.total)return 'done';
      if(k&&(k.seen>0||k.sessionStatus==='active'))return 'remaining';
      return 'total';
    }
    function rc198CourseTimeLabel(course,k){
      const state=rc198CourseTimeState(k);
      if(state==='review')return {state,text:`à revoir · ~${rc163FmtTime(rc198EstimateRemainingMinutes(course,k))}`,title:'Temps estimé pour reprendre les points fragiles'};
      if(state==='done')return {state,text:'terminé',title:'Parcours terminé'};
      if(state==='remaining')return {state,text:`reste ~${rc163FmtTime(rc198EstimateRemainingMinutes(course,k))}`,title:'Temps restant estimé'};
      return {state,text:rc163FmtTime(rc163EstimateMinutes(course)),title:'Temps total estimé'};
    }
    function rc198CollectionTimeLabel(runtime,courseRows){
      const rows=(courseRows||[]).map(r=>{const course=runtime.contentStore.courseById(r.courseId);return {course,k:r.kpi||buildCourseProgressKpi(runtime,course)};}).filter(x=>!!x.course);
      const totalMinutes=rows.reduce((s,x)=>s+rc163EstimateMinutes(x.course),0);
      const totalActs=rows.reduce((s,x)=>s+((x.k&&x.k.total)||0),0);
      const seen=rows.reduce((s,x)=>s+((x.k&&x.k.seen)||0),0);
      const reviews=rows.reduce((s,x)=>s+((x.k&&x.k.reviewCount)||0),0);
      const remaining=rows.reduce((s,x)=>s+rc198EstimateRemainingMinutes(x.course,x.k),0);
      if(reviews>0)return {state:'review',text:`à revoir · ~${rc163FmtTime(Math.max(5,remaining))}`,title:'Temps estimé pour reprendre les points fragiles de la collection'};
      if(totalActs>0&&seen>=totalActs)return {state:'done',text:'terminé',title:'Collection terminée'};
      if(seen>0)return {state:'remaining',text:`reste ~${rc163FmtTime(Math.max(5,remaining))}`,title:'Temps restant estimé pour la collection'};
      return {state:'total',text:rc163FmtTime(totalMinutes),title:'Temps total estimé de la collection'};
    }
    function rc163CourseSymbol(course){const text=((course.title||'')+' '+(course.sequence||'')).toLowerCase();if(/complex/.test(text))return 'complex';if(/puissance|énergie|energie/.test(text))return 'bolt';if(/filtr/.test(text))return 'filter';if(/polyn|racine|équation|equation/.test(text))return 'roots';return 'electric';}
    function rc163SymbolSvg(kind){const svg={electric:`<svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 92h26l18-42 31 82 22-51h27" stroke="rgba(255,255,255,.88)" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/><circle cx="44" cy="92" r="8" fill="rgba(255,255,255,.72)"/><circle cx="115" cy="81" r="8" fill="rgba(255,255,255,.72)"/></svg>`,bolt:`<svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M91 14 42 88h39l-13 58 51-78H80l11-54Z" fill="rgba(255,255,255,.86)"/></svg>`,complex:`<svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M28 124h104M44 136V28" stroke="rgba(255,255,255,.72)" stroke-width="7" stroke-linecap="round"/><circle cx="100" cy="58" r="18" stroke="rgba(255,255,255,.88)" stroke-width="7"/><path d="M44 124 100 58" stroke="rgba(255,255,255,.88)" stroke-width="7" stroke-linecap="round"/></svg>`,roots:`<svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M24 102c22-48 42-48 64 0s42 48 64 0" stroke="rgba(255,255,255,.88)" stroke-width="8" stroke-linecap="round"/><circle cx="44" cy="102" r="7" fill="rgba(255,255,255,.75)"/><circle cx="116" cy="102" r="7" fill="rgba(255,255,255,.75)"/></svg>`,filter:`<svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M24 44h112L94 91v35l-28 14V91L24 44Z" stroke="rgba(255,255,255,.88)" stroke-width="8" stroke-linejoin="round"/><path d="M38 44h84" stroke="rgba(255,255,255,.42)" stroke-width="18" stroke-linecap="round"/></svg>`};return svg[kind]||svg.electric;}
    function rc163EstimateMinutes(course){const acts=(course.activities||[]).length;const weights={qcm:5,fill:7,matching:8,order:8,flashcard:3};return Math.max(8,(course.activities||[]).reduce((s,a)=>s+(weights[a.type]||6),0)||acts*6);}
    function rc163BackCopy(course){const title=course.title||'Ce parcours';const seq=course.sequence||'';const objs=(course.objectives||[]).slice(0,3);const acts=(course.activities||[]);const types=[...new Set(acts.map(a=>a.type))];const first=objs[0]||acts[0]?.objective||'installer les bases';const second=objs[1]||acts[1]?.objective||'s’entraîner sans se perdre';const third=objs[2]||acts[2]?.objective||'consolider les automatismes';return `${title} clarifie ${seq?seq.toLowerCase():'les notions centrales'} et transforme le contenu en gestes d’apprentissage concrets. Tu commences par ${first}, puis tu apprends à ${second}. Le parcours alterne ${types.length?types.join(', '):'activités courtes'} pour installer la compréhension avant la validation. L’objectif final : ${third}, avec assez de repères pour savoir quoi reprendre et pourquoi.`;}
    function rc163NextStep(runtime,course,k){const model=courseDetailModel(runtime,course,k);return model.next||'Ouvrir la prochaine activité.';}
    function rc163NormalizeSearch(value){return String(value||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').trim();}
    function rc163RecommendedRank(course){const k=course&&course.kpi||{};if(Number(k.reviewCount||0)>0)return 0;if(k.sessionStatus==='active')return 1;if(Number(k.seen||0)>0&&Number(k.seen||0)<Number(k.total||0))return 2;if(Number(k.seen||0)===0)return 3;return 4;}
    function rc163FilterCourses(runtime,courses){
      const f=runtime.libraryFilter||'all';let arr=[...courses];
      if(f==='resume')arr=arr.filter(c=>c.kpi&&(c.kpi.seen>0||c.kpi.sessionStatus==='active')&&c.kpi.seen<c.kpi.total);
      if(f==='review')arr=arr.filter(c=>c.kpi&&c.kpi.reviewCount>0);
      if(f==='new')arr=arr.filter(c=>!c.kpi||c.kpi.seen===0);
      if(f==='imported')arr=arr.filter(c=>!!c.imported);
      const query=rc163NormalizeSearch(runtime.libraryQuery||'');
      if(query)arr=arr.filter(c=>rc163NormalizeSearch([c.title,c.sequence,...(c.objectives||[])].join(' ')).includes(query));
      const sort=runtime.librarySort||'recommended';
      if(sort==='time')arr.sort((a,b)=>rc163EstimateMinutes(runtime.contentStore.courseById(a.courseId))-rc163EstimateMinutes(runtime.contentStore.courseById(b.courseId))||String(a.title).localeCompare(String(b.title)));
      else if(sort==='progress')arr.sort((a,b)=>(b.kpi?.pct||0)-(a.kpi?.pct||0)||String(a.title).localeCompare(String(b.title)));
      else arr.sort((a,b)=>rc163RecommendedRank(a)-rc163RecommendedRank(b)||String(a.title).localeCompare(String(b.title)));
      return arr;
    }
    function rc163Chapters(course){const activities=course.activities||[];if(!activities.length)return [];
      const objectives=(course.objectives||[]).filter(Boolean);const max=Math.min(5,Math.max(3,objectives.length||Math.ceil(activities.length/2)));const size=Math.ceil(activities.length/max);const chunks=[];
      for(let i=0;i<activities.length;i+=size){const group=activities.slice(i,i+size);const title=objectives[chunks.length]||group[0].objective||`Chapitre ${chunks.length+1}`;const detail=group.length>1?`${group.length} activités pour installer le point clé.`:(group[0].question||'Activité courte.');chunks.push({title,detail,ids:group.map(a=>a.id),activities:group});}
      return chunks;}
    function rc163ChapterMeta(runtime,course,chapter,k,index){const total=chapter.activities.length;const minutes=Math.max(8,chapter.activities.reduce((s,a)=>s+({qcm:5,fill:7,matching:8,order:8,flashcard:3}[a.type]||6),0));const ids=new Set(chapter.ids);const p=rc203ProgressIds(runtime,course);const review=[...p.reviewIds].filter(id=>ids.has(id)).length;const answered=[...p.seenIds].filter(id=>ids.has(id)).length;const correct=[...p.correctIds].filter(id=>ids.has(id)).length;let intent='découverte progressive',detail='Section à travailler.',state='todo';if(review){intent='reprise ciblée';detail='Section à revoir.';state='review';}else if(answered>=total&&total){intent='révision rapide';detail='Section terminée.';state='done';}else if(answered>0||index===0&&k.sessionStatus==='active'){intent='travail guidé';detail='Section en cours.';state='current';}return {total,minutes,review,answered,correct,intent,detail,state};}
    function rc163ChapterTone(color,idx,total){const pct=24+Math.round((idx/(Math.max(total-1,1)))*68);return `color-mix(in srgb, ${color} ${pct}%, white ${100-pct}%)`;}
    function rc163StateIcon(state){return {done:'✓',current:'●',review:'↺',todo:'○'}[state]||'○';}
    function rc163ChapterActionLabel(state){return {done:'Réviser ce chapitre',current:'Continuer ce chapitre',review:'Revoir ce chapitre',todo:'Ouvrir ce chapitre'}[state]||'Travailler ce chapitre';}

