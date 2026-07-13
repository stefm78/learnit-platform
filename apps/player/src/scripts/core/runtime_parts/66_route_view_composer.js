    /* RC463 — RouteViewComposer owns final route surfaces.
       Route UI must be composed with its final classes and route-local CSS before paint;
       no visible block may wait for body.view-* or post-paint enhancement.

       RC459 — native RouteViewComposer with stable route(routeName) API.
       Future route UI changes must be added through this composer API; the carousel calls
       it directly, without temporarily mutating appState.view.

       RC455 — native RouteViewComposer, static-route surface owner.
       Purpose: route presentation is now composed once, synchronously, by a
       source-owned view composer. No prototype wrapping, no string patching of
       older route HTML, and no post-paint DOM insertion for visible route
       objects. Enhancement scripts can still install event handlers and reports,
       but the visible Apprendre/Bibliothèque/Bilan/Outils objects are emitted
       here before runtime boot. */
    window.__LEARNIT_ROUTE_PRESENTATION_FLATTENED__ = true;
    window.__LEARNIT_ROUTE_VIEW_COMPOSER__ = true;
    window.__LEARNIT_ROUTE_STATIC_SURFACES__ = true;
    window.__LEARNIT_ROUTE_SURFACE_CONTRACT_RC463__ = true;
    window.__LEARNIT_ROUTE_PAINT_CONTRACT_RC465__ = true;
    window.__LEARNIT_LIBRARY_NAV_SHELL_CONTRACT_RC468__ = true;

    const RouteViewComposer = (()=>{
      const esc = value => escapeHtml(value==null?'':value);
      const attr = value => escapeAttr(value==null?'':value);

      function activities(runtime){
        return (runtime&&runtime.contentStore&&runtime.contentStore.content&&runtime.contentStore.content.activities)||[];
      }
      function progress(runtime){
        try{return runtime.appState.courseProgress(runtime.contentStore.activeCourseId)||{};}catch(e){return {};}
      }
      function lastBilan(runtime,courseId){
        const state=runtime&&runtime.appState&&runtime.appState.state||{};const id=courseId||runtime&&runtime.contentStore&&runtime.contentStore.activeCourseId;return (state.lastBilanByCourseId||{})[id]||(id===state.activeCourseId?state.lastBilan:null)||null;
      }
      function nextAction(runtime,course){
        const target=course||runtime.contentStore.content||{};const id=courseIdFromContent(target);const model=window.LearnItNextActionModel;const p=runtime.appState.courseProgress(id)||{};const session=id===runtime.contentStore.activeCourseId?(runtime.session&&runtime.session.session||{}):((runtime.appState.state.sessionByCourseId||{})[id]||{});
        if(model&&typeof model.recommend==='function')return model.recommend(Object.assign({},target,{id}),p,session,lastBilan(runtime,id));
        const evidence=explainableEvidence(runtime,target);return evidence.recommendation||{action:'continue',mode:'training',intent:'training',label:'Continuer l’entraînement',headline:'Continuez votre entraînement',reasonCode:'evidence-in-progress',reason:'Les preuves disponibles doivent encore être répétées et espacées.',secondary:null};
      }
      function kpis(runtime){
        const rows=buildLibraryProjection(runtime).courses||[];
        const total=rows.length;
        const started=rows.filter(r=>r.kpi&&r.kpi.seen>0&&r.kpi.seen<r.kpi.total).length;
        const review=rows.filter(r=>r.kpi&&r.kpi.reviewCount>0).length;
        const completed=rows.filter(r=>r.kpi&&r.kpi.total&&r.kpi.seen>=r.kpi.total&&r.kpi.reviewCount===0).length;
        const avg=total?Math.round(rows.reduce((sum,r)=>sum+((r.kpi&&r.kpi.pct)||0),0)/total):0;
        return {total,started,review,completed,averageProgress:avg,rows};
      }
      function libraryKpiStrip(runtime){
        const d=kpis(runtime);
        return `<div class="library-kpi-strip" data-rc228-library-kpi="true" data-route-composer-owned="true" data-rc454-composed="true" data-rc455-static-route="true" role="status" aria-label="Indicateurs de progression des parcours"><span><b>${d.total}</b><em>parcours</em></span><span><b>${d.started}</b><em>entamés</em></span><span class="${d.review?'warn':''}"><b>${d.review}</b><em>à revoir</em></span><span class="${d.completed?'ok':''}"><b>${d.completed}</b><em>terminés</em></span><span><b>${d.averageProgress}%</b><em>avancement moyen</em></span></div>`;
      }
      function smartResume(runtime){
        const acts=activities(runtime), p=progress(runtime), s=(runtime.session&&runtime.session.session)||{};
        const active=s.status==='active';
        const review=acts.filter(a=>p[a.id]&&p[a.id].review).map(a=>a.id);
        const unseen=acts.filter(a=>!p[a.id]).map(a=>a.id);
        const complete=acts.length>0&&unseen.length===0&&review.length===0;
        const choices=[];
        if(active)choices.push({kind:'resume-active',label:'Reprendre',detail:`Position ${Number(s.currentIndex||0)+1}/${(s.queue||acts).length}`,primary:true});
        if(review.length)choices.push({kind:'review',label:'Points faibles',detail:`${review.length} activité(s)`,primary:!active});
        if(unseen.length)choices.push({kind:'continue-new',label:'Suite',detail:`${unseen.length} non vue(s)`,primary:!active&&!review.length});
        choices.push({kind:'new-round',label:complete?'Consolider':'Nouvelle série',detail:complete?'Parcours terminé':'Série complète',primary:choices.length===0});
        return {choices,reviewQueue:review,unseenQueue:unseen,complete,active,reviewCount:review.length,unseenCount:unseen.length};
      }
      function explainableEvidence(runtime,course,chapters){
        const target=course||runtime.contentStore.content||{};const id=courseIdFromContent(target);const p=runtime.appState.courseProgress(id)||{};const model=window.LearnItMasteryEvidenceModel;
        const shaped=Object.assign({},target,{id});
        if(Array.isArray(chapters))shaped.chapters=chapters.map((chapter,index)=>({id:chapter.id||`chapter-${index+1}`,title:chapter.title||`Chapitre ${index+1}`,ids:Array.isArray(chapter.ids)?chapter.ids:[]}));
        if(model&&typeof model.explainCourse==='function')return model.explainCourse(shaped,p);
        const rows=(target.activities||[]).map(a=>p[a.id]||{});const exposed=rows.filter(row=>row.seen||row.attempts).length;const succeeded=rows.filter(row=>row.correct).length;const fragile=rows.filter(row=>row.review||row.correct===false).length;const status=fragile?'fragile':(exposed?(succeeded?'in-progress':'discovered'):'not-started');
        return {courseId:id,title:target.title||'Parcours',status,statusLabel:{'not-started':'Non commencé','discovered':'Découvert','in-progress':'En cours','fragile':'Fragile','consolidated':'Consolidé'}[status],total:rows.length,exposed,attempted:exposed,succeeded,fragile,due:fragile,consolidated:0,objectives:[],chapters:[],recommendation:fragile?{action:'review',label:'Revoir les points fragiles',reasonCode:'fragile-objectives',reason:'Des erreurs ou réussites instables demandent une reprise ciblée.'}:(!exposed?{action:'discover',label:'Découvrir ce parcours',reasonCode:'no-evidence-yet',reason:'Aucune preuve d’exposition ou de réussite n’est encore enregistrée.'}:{action:'continue',label:'Continuer l’entraînement',reasonCode:'evidence-in-progress',reason:'Les preuves disponibles doivent encore être répétées et espacées.'})};
      }
      function evidenceTone(status){return status==='fragile'?'warn':(status==='consolidated'?'ok':(status==='in-progress'||status==='discovered'?'blue':''));}
      function evidenceMode(recommendation){if(recommendation&&recommendation.mode)return {intent:recommendation.intent||recommendation.mode,mode:recommendation.mode};const action=recommendation&&recommendation.action||'continue';return {review:{intent:'review',mode:'review'},discover:{intent:'discovery',mode:'discovery'},continue:{intent:'training',mode:'training'},validate:{intent:'validation',mode:'validation'},resume:{intent:'resume',mode:'training'}}[action]||{intent:'training',mode:'training'};}
      function evidenceActionAttrs(recommendation,courseId){if(recommendation&&recommendation.reasonCode==='scheduled-review-due')return `data-rc247-action="start-due" data-course="${attr(courseId)}"`;const mode=evidenceMode(recommendation);return `data-rc580-intent="${attr(mode.intent)}" data-mode="${attr(mode.mode)}" data-course="${attr(courseId)}"`;}
      function evidenceDetail(row){
        if(!row)return '';
        if(row.status==='not-started')return `${row.total||0} activité${Number(row.total||0)>1?'s':''} à découvrir`;
        if(row.status==='fragile')return `${row.fragile||0} fragile${Number(row.fragile||0)>1?'s':''} · ${row.succeeded||0} réussie${Number(row.succeeded||0)>1?'s':''}`;
        if(row.status==='consolidated')return `${row.consolidated||0}/${row.total||0} preuve${Number(row.total||0)>1?'s':''} stabilisée${Number(row.total||0)>1?'s':''}`;
        return `${row.exposed||0}/${row.total||0} vue${Number(row.exposed||0)>1?'s':''} · ${row.succeeded||0} réussie${Number(row.succeeded||0)>1?'s':''}`;
      }
      function score(runtime){
        const e=explainableEvidence(runtime,runtime.contentStore.content);const total=Math.max(Number(e.total||0),1);return {total:Number(e.total||0),seen:Number(e.exposed||0),correct:Number(e.succeeded||0),review:Number(e.fragile||0),due:Number(e.due||0),exposure:Math.round(100*Number(e.exposed||0)/total),status:e.status,label:e.statusLabel||'Non commencé',evidence:e};
      }
      function due(runtime,now=Date.now()){
        const acts=activities(runtime), p=progress(runtime);
        const rows=acts.map(a=>{const row=p[a.id]||{};const last=row.lastAt?Date.parse(row.lastAt):0;const ageH=last?Math.max(0,(now-last)/36e5):9999;const interval=row.correct?72:8;const isDue=!!row.seen&&(row.review||ageH>=interval);return {id:a.id,objective:a.objective||a.question||a.id,seen:!!row.seen,correct:!!row.correct,review:!!row.review,ageHours:Math.round(ageH),due:isDue};}).filter(x=>x.due);
        return {count:rows.length,queue:rows.map(x=>x.id),rows};
      }
      function reviewPolicy(runtime){
        const acts=activities(runtime), p=progress(runtime);
        const q=acts.filter(a=>p[a.id]&&p[a.id].review).map(a=>a.id);
        return {reviewCount:q.length,reviewQueue:q,guarantee:'Les points à revoir proposent une reprise ciblée mais ne bloquent ni Bibliothèque, ni Apprendre, ni nouvelle série.'};
      }
      function remediation(runtime){
        const acts=activities(runtime), p=progress(runtime);
        const rows=acts.filter(a=>p[a.id]&&p[a.id].review).map(a=>({id:a.id,objective:a.objective||a.question||a.id,remediation:a.remediation||'Reprendre la notion puis refaire une activité proche.'}));
        return {count:rows.length,rows};
      }
      function learnExtension(runtime){
        const s=score(runtime);const modeModel=window.LearnItSessionModeModel;const modes=modeModel&&typeof modeModel.list==='function'?modeModel.list():[];
        const entry=nextAction(runtime,runtime.contentStore.content);const primaryLabel=entry.primaryLabel||entry.label||'Commencer';
        const shown=new Set([entry.mode,entry.secondary&&entry.secondary.mode].filter(Boolean));const otherModes=modes.filter(mode=>!shown.has(mode.id));
        const secondary=entry.secondary?`<button type="button" class="entry-alternative" data-entry-role="alternative" data-rc580-intent="${attr(entry.secondary.intent)}" data-mode="${attr(entry.secondary.mode)}"><span class="entry-alternative-prefix">Autre possibilité</span><strong>${esc(entry.secondary.label)}</strong><span>${esc(entry.secondary.detail)}</span></button>`:'';
        const other=otherModes.map(mode=>`<button type="button" class="rc248-mode" data-rc580-intent="${attr(mode.id)}" data-mode="${attr(mode.id)}"><strong>${esc(mode.label)}</strong><span class="tiny">${esc(mode.detail)}</span></button>`).join('');
        const primaryDetail=modeModel&&modeModel.resolve?modeModel.resolve(entry.mode).detail:'Séance recommandée';
        return `<section class="rc580-course-entry rc658-action-first" data-route-composer-owned="true" data-entry-guidance="learnit.entry_guidance.rc658.v1" data-session-entry-state="${attr(entry.state||'unknown')}" data-recommendation-code="${attr(entry.reasonCode||'unknown')}"><div class="entry-copy"><span class="entry-kicker">Votre prochaine étape</span><h2>${esc(entry.headline)}</h2><p>${esc(entry.reason)}</p></div><div class="entry-actions"><button type="button" class="entry-choice primary" data-entry-role="primary" data-rc580-intent="${attr(entry.intent)}" data-mode="${attr(entry.mode)}"><span class="entry-recommended">Recommandé pour vous</span><strong>${esc(primaryLabel)}</strong><span>${esc(primaryDetail)}</span></button>${secondary}</div><div class="assessment-boundary" role="note" aria-label="Différence entre diagnostic et validation"><span class="assessment-step"><b>Diagnostic</b><small>Au début · situe le niveau · progression inchangée</small></span><span class="assessment-arrow" aria-hidden="true">→</span><span class="assessment-step"><b>Validation</b><small>À la fin · confirme les acquis · progression enregistrée</small></span></div><details class="rc580-other-modes"><summary>Voir tous les modes</summary><div class="rc248-grid">${other}</div></details></section><div class="rc242-pedagogical-score" data-route-composer-owned="true" data-rc454-composed="true" data-rc455-static-route="true"><h2>Repères du parcours</h2><div class="rc242-grid"><div class="rc242-score"><b>${s.exposure}%</b><span class="tiny">activités vues</span></div><div class="rc242-score"><b>${s.correct}/${s.total}</b><span class="tiny">réussies au moins une fois</span></div><div class="rc242-score"><b>${s.review}</b><span class="tiny">fragiles</span></div><div class="rc242-score"><b>${esc(s.label)}</b><span class="tiny">état des preuves</span></div></div></div>`;
      }
      function modeOutcomePanel(runtime,courseId){
        const state=runtime.appState&&runtime.appState.state||{};const byCourse=state.lastBilanByCourseId||{};const last=byCourse[courseId]||(courseId===runtime.contentStore.activeCourseId?state.lastBilan:null);const model=window.LearnItSessionModeModel;if(!last||!model||typeof model.sessionPolicy!=='function')return '';
        const policy=model.sessionPolicy(last);if(!['validation','diagnostic'].includes(policy.id))return '';
        const outcome=last.modeOutcome||(typeof model.outcome==='function'?model.outcome(last):null);if(!outcome)return '';
        const tone=outcome.passed?'':' warn';const persistence=outcome.recordedInProgress?'Progression mise à jour':'Progression inchangée';const debriefRows=(outcome.debrief||[]).map(row=>`<li class="assessment-debrief-row is-${attr(row.status)}"><span><strong>${esc(row.label)}</strong><small>${esc(row.detail)}</small></span><span>${esc(row.next)}</span></li>`).join('');const debrief=debriefRows?`<details class="assessment-debrief"><summary>Voir le détail par objectif</summary><ul>${debriefRows}</ul></details>`:'';
        return `<section class="loop-panel bilan-mode-outcome${tone}" aria-label="Résultat ${attr(policy.label)}"><div class="loop-kicker">Résultat · ${esc(policy.label)}</div><div class="loop-title">${esc(outcome.title)}</div><p class="loop-detail">${esc(outcome.detail)}</p><div class="bilan-chip-row"><span class="loop-chip">${esc(persistence)}</span><span class="loop-chip">${Number(outcome.correct||0)}/${Number(outcome.total||0)} réussi${Number(outcome.correct||0)>1?'s':''}</span></div>${debrief}</section>`;
      }
      function bilanExtension(runtime,course,evidence){
        const e=evidence||explainableEvidence(runtime,course);const courseId=courseIdFromContent(course);const rem=(e.objectives||[]).find(row=>row.status==='fragile');
        const reviewPanel=e.fragile?`<section class="bilan-review-focus" aria-label="Points fragiles"><div><span class="bilan-section-kicker">À retravailler</span><strong>${e.fragile} activité${e.fragile>1?'s':''} fragile${e.fragile>1?'s':''}</strong><p>${esc(rem?`${rem.label} : ${evidenceDetail(rem)}`:'Une reprise ciblée est recommandée avant de poursuivre.')}</p></div><span class="badge warn">${e.fragile} fragile${e.fragile>1?'s':''}</span></section>`:'';
        return `${reviewPanel}<details class="bilan-more" data-bilan-secondary="true"><summary>Voir les preuves et options</summary><div class="bilan-more-grid"><section class="bilan-secondary-panel rc242-pedagogical-score"><h2>Preuves disponibles</h2><div class="rc242-grid"><div class="rc242-score"><b>${e.exposed||0}/${e.total||0}</b><span class="tiny">activités vues</span></div><div class="rc242-score"><b>${e.succeeded||0}</b><span class="tiny">réussies au moins une fois</span></div><div class="rc242-score"><b>${e.fragile||0}</b><span class="tiny">fragiles</span></div><div class="rc242-score"><b>${esc(e.statusLabel||'Non commencé')}</b><span class="tiny">état des preuves</span></div></div></section><section class="bilan-secondary-panel rc247-spaced-review"><h2>Révision espacée</h2><p class="tiny">${e.due||0} activité${Number(e.due||0)>1?'s':''} arrivée${Number(e.due||0)>1?'s':''} à échéance.</p><div class="actions"><button data-rc247-action="start-due" data-course="${attr(courseId)}" ${e.due?'':'disabled'}>Lancer la révision</button></div></section><section class="bilan-secondary-panel rc243-progress-export"><h2>Exporter</h2><p class="tiny">Résumé lisible du parcours sélectionné.</p><div class="actions"><button type="button" data-rc243-action="export-progress" data-course="${attr(courseId)}">Progression JSON</button></div></section></div></details>`;
      }
      function importFilePanel(runtime){
        const policy=runtime&&runtime.contentStore&&runtime.contentStore.importCollisionPolicy||'rename';
        return `<div class="import-file-panel rc612-import-file" data-import-file-selector="learnit.import_file_selector.rc612.v2" data-import-transactional="true"><div class="import-file-copy"><strong>Choisir un ou plusieurs kits JSON</strong><span class="tiny">Les fichiers sont analysés ensemble. Aucune écriture avant prévisualisation.</span></div><label class="import-file-label">Sélectionner des fichiers<input id="importFile" type="file" multiple accept=".json,application/json,text/json" aria-describedby="importFileStatus"></label><label class="import-policy-label">En cas de doublon<select id="importCollisionPolicy" aria-label="Politique de collision"><option value="rename" ${policy==='rename'?'selected':''}>Renommer automatiquement</option><option value="replace" ${policy==='replace'?'selected':''}>Remplacer l’import existant</option><option value="skip" ${policy==='skip'?'selected':''}>Ignorer le doublon</option><option value="reject" ${policy==='reject'?'selected':''}>Bloquer l’import</option></select></label><div id="importFileStatus" class="import-file-status" data-level="info">Vous pouvez aussi déposer les fichiers ou coller un package dans la zone ci-dessous.</div></div>`;
      }

      function learn(runtime){
        const p=buildLearningProjection(runtime);
        const check=runtime.mirror.assert();
        const secondary=p.status.kind==='done'?'<button data-nav="bilan">Voir le bilan</button>':'';
        const course=runtime.contentStore.content||{};
        const title=course.title||'Parcours sélectionné';
        const seq=course.sequence||'';
        return `<section class="card surface-compact rc208-learn rc330-learn rc454-composed-route rc455-static-route"><div class="view-title-head single"><div><div class="kicker view-kicker">Apprendre</div><h1>${esc(title)}</h1>${seq?`<p class="view-subtitle">${esc(seq)}</p>`:''}</div></div><div class="rc208-action-card rc330-learn-core"><div class="row between"><span class="badge ${p.status.kind==='active'?'blue':p.status.kind==='done'?'ok':''}">${esc(p.headline)}</span>${check.ok?'':'<span class="badge warn">État à vérifier</span>'}</div><div class="progress" aria-hidden="true"><span style="width:${p.pct}%"></span></div><p class="useful">${esc(p.detail)}</p>${secondary?`<div class="actions rc330-secondary">${secondary}</div>`:''}</div>${learnExtension(runtime)}</section>`;
      }

      function librarySearchField(runtime,visible,total){const query=String(runtime.libraryQuery||'');return `<label class="library-search"><span class="sr-only">Rechercher un parcours</span><input id="librarySearch" type="search" value="${attr(query)}" placeholder="Rechercher" autocomplete="off" enterkeyhint="search"><button type="button" class="library-search-clear ${query?'is-visible':''}" data-action="library-clear-search" aria-label="Effacer la recherche" ${query?'':'disabled'}>×</button><span class="library-search-count">${visible}/${total}</span></label>`;}
      function libraryCourseRow(runtime,c,course,k,color,selectedId,extraClass=''){
        const status=k.status||'À faire';const tone=courseToneClass(k);const action=courseActionLabel(k);
        const progress=`<span class="book-progress" title="Avancement">${Number(k.pct||0)}%</span>`;
        const review=k.reviewCount?`<span class="book-review" title="Points à revoir" aria-label="${k.reviewCount} points à revoir">↺${k.reviewCount}</span>`:`<span class="book-review" aria-hidden="true"></span>`;
        const timeInfo=rc198CourseTimeLabel(course,k);const time=`<span class="book-time rc198-time is-${timeInfo.state}" title="${attr(timeInfo.title)}">${esc(timeInfo.text)}</span>`;
        return `<article class="book-row ${c.courseId===selectedId?'is-selected':''} ${extraClass}" data-course-row="${attr(c.courseId)}" style="--c:${color}"><span class="book-accent"></span><button type="button" class="book-open-main" data-action="library-open-course" data-course="${attr(c.courseId)}" aria-label="Ouvrir les détails de ${attr(c.title)}"><span class="book-main"><span class="book-title-line"><span class="book-title">${esc(c.title)}</span><span class="book-sub">${esc(c.sequence||'')}</span></span><span class="book-status ${tone}">${esc(status)}</span></span></button><span class="book-metrics">${review}${progress}${time}</span><button type="button" class="book-direct-action ${tone}" data-action="learn-course" data-course="${attr(c.courseId)}" aria-label="${attr(action)} ${attr(c.title)}">${esc(action)}</button><button type="button" class="book-open" data-action="library-open-course" data-course="${attr(c.courseId)}" aria-label="Détails de ${attr(c.title)}">›</button></article>`;
      }

      function library(runtime){
        if(runtime.libraryV2Enabled)return libraryV2(runtime);
        const p=buildLibraryProjection(runtime);const selectedId=runtime.libraryOverlayCourseId||p.activeCourseId;const visible=rc163FilterCourses(runtime,p.courses);
        const chips=[['all','Tous'],['resume','À reprendre'],['review','À revoir'],['new','Nouveaux']].map(([id,label])=>`<button class="lib-chip" data-action="library-filter" data-filter="${id}" aria-pressed="${(runtime.libraryFilter||'all')===id?'true':'false'}">${label}</button>`).join('');
        const rows=visible.map((c,i)=>{const course=runtime.contentStore.courseById(c.courseId);const k=c.kpi||buildCourseProgressKpi(runtime,course);return libraryCourseRow(runtime,c,course,k,rc163CourseColor(i),selectedId);}).join('');
        const empty=`<div class="library-empty">Aucun parcours ne correspond.</div>`;
        return `<section class="card surface-compact library-page rc163 rc532-library rc454-composed-route rc455-static-route rc468-library-nav-shell" data-route-swipe-intent="observable" data-content-scroll-surface="library" data-library-scroll-contract="native-route-panel"><div class="library-head view-title-head"><div><div class="kicker view-kicker">Bibliothèque</div><h1>Choisir un parcours</h1></div><p class="library-count">${visible.length}/${p.courses.length} parcours</p></div>${libraryKpiStrip(runtime)}<div class="library-sticky-tools"><div class="library-tool-row"><div class="library-filters">${chips}</div>${librarySearchField(runtime,visible.length,p.courses.length)}<label class="lib-sort-wrap"><select class="lib-sort" id="librarySort" aria-label="Ordre des parcours"><option value="recommended" ${(runtime.librarySort||'recommended')==='recommended'?'selected':''}>Conseillé</option><option value="time" ${runtime.librarySort==='time'?'selected':''}>Temps court</option><option value="progress" ${runtime.librarySort==='progress'?'selected':''}>Avancement</option></select></label></div></div><div class="library-list">${rows||empty}</div></section>`;
      }

      function libraryV2(runtime){
        const p=buildLibraryProjection(runtime);const selectedId=runtime.libraryOverlayCourseId||p.activeCourseId;const visible=rc163FilterCourses(runtime,p.courses);const groups=runtime.libraryV2Groups(visible);
        const chips=[['all','Tous'],['resume','À reprendre'],['review','À revoir'],['new','Nouveaux']].map(([id,label])=>`<button class="lib-chip" data-action="library-filter" data-filter="${id}" aria-pressed="${(runtime.libraryFilter||'all')===id?'true':'false'}">${label}</button>`).join('');
        const groupHtml=groups.map((g,gi)=>{const color=rc163CourseColor(g.colorIndex||gi);const collectionPct=Math.round((g.seenCount/Math.max(g.activityCount,1))*100);const rows=g.courses.map((c,i)=>{const course=runtime.contentStore.courseById(c.courseId);const k=c.kpi||buildCourseProgressKpi(runtime,course);return libraryCourseRow(runtime,c,course,k,rc163CourseColor((g.colorIndex||gi)+i),selectedId);}).join('');const collectionTimeInfo=rc198CollectionTimeLabel(runtime,g.courses);const hasSelected=g.courses.some(c=>c.courseId===selectedId);const manual=Object.prototype.hasOwnProperty.call(runtime.libraryOpenCollections,g.key);const isOpen=manual?!!runtime.libraryOpenCollections[g.key]:(hasSelected||g.recent||gi===0);return `<details class="collection ${hasSelected?'is-active-collection':''}" data-collection-key="${attr(g.key)}" style="--c:${color}" ${isOpen?'open':''}><summary><span class="collection-accent"></span><span class="collection-title"><strong>${esc(g.label)}</strong><span>${g.courses.length} parcours · ${g.activityCount} activités</span></span><span class="collection-meta"><span class="collection-progress ${collectionPct?'':'empty'}">${collectionPct}%</span><span class="collection-time rc198-time is-${collectionTimeInfo.state}">${esc(collectionTimeInfo.text)}</span></span></summary><div class="collection-body">${rows}</div></details>`;}).join('');
        const empty='<div class="library-v2-empty">Aucun parcours ne correspond.</div>';
        return `<section class="card surface-compact library-page rc163 rc193 rc198 rc202 rc330-library rc532-library rc454-composed-route rc455-static-route rc468-library-nav-shell" data-route-swipe-intent="observable" data-content-scroll-surface="library" data-library-scroll-contract="native-route-panel"><div class="library-head view-title-head"><div><div class="kicker view-kicker">Bibliothèque</div><h1>Collections d’apprentissage</h1></div><p class="library-count">${groups.length} collection${groups.length>1?'s':''} · ${visible.length}/${p.courses.length} parcours</p></div>${libraryKpiStrip(runtime)}<div class="library-sticky-tools"><div class="library-tool-row"><div class="library-filters">${chips}</div>${librarySearchField(runtime,visible.length,p.courses.length)}<label class="lib-sort-wrap"><select class="lib-sort" id="librarySort" aria-label="Ordre des parcours"><option value="recommended" ${(runtime.librarySort||'recommended')==='recommended'?'selected':''}>Conseillé</option><option value="time" ${runtime.librarySort==='time'?'selected':''}>Temps court</option><option value="progress" ${runtime.librarySort==='progress'?'selected':''}>Avancement</option></select></label></div></div><div class="collection-list">${groupHtml||empty}</div></section>`;
      }

      function bilan(runtime){
        const collections=runtime.bilanCollections();
        const allCourses=runtime.contentStore.allCourses();
        const activeId=runtime.contentStore.activeCourseId;
        const selectedId=(runtime.bilanCourseId&&allCourses.some(c=>courseIdFromContent(c)===runtime.bilanCourseId))?runtime.bilanCourseId:activeId;
        runtime.bilanCourseId=selectedId;
        const selectedCourse=runtime.contentStore.courseById(selectedId);
        const chapters=rc163Chapters(selectedCourse);
        const evidence=explainableEvidence(runtime,selectedCourse,chapters);
        const selectedCollection=collections.find(g=>(g.courses||[]).some(c=>courseIdFromContent(c)===selectedId));
        if(selectedCollection&&selectedCollection.key&&runtime.bilanOpenCollections[selectedCollection.key]===undefined)runtime.bilanOpenCollections[selectedCollection.key]=true;
        const rec=nextAction(runtime,selectedCourse);const recAttrs=evidenceActionAttrs(rec,selectedId);const iaModel=window.LearnItBilanInformationArchitecture;const ia=iaModel&&typeof iaModel.plan==='function'?iaModel.plan(evidence,rec,lastBilan(runtime,selectedId)):{openStructure:evidence.status==='fragile',showBoundary:evidence.status==='not-started',primaryActionCount:1,secondaryActionCount:rec.secondary?1:0,decisionFirst:true};
        const navHtml=collections.map((g,gi)=>{
          const rows=(g.courses||[]).map(course=>{const id=courseIdFromContent(course);const e=explainableEvidence(runtime,course);const isSelected=id===selectedId;return `<button class="bilan-course-row ${isSelected?'is-selected':''} is-${attr(e.status)}" data-action="bilan-select-course" data-course="${attr(id)}"><span><strong>${esc(course.title||'Parcours')}</strong><small>${esc(course.sequence||'')}</small></span><span class="badge ${evidenceTone(e.status)}">${esc(e.statusLabel)}</span></button>`;}).join('');
          const selected=(g.courses||[]).some(c=>courseIdFromContent(c)===selectedId);
          const key=g.key||g.id||('collection-'+gi);
          const open=runtime.bilanOpenCollections[key]!==undefined?!!runtime.bilanOpenCollections[key]:(selected||gi===0);
          const totalActivities=(g.courses||[]).reduce((n,c)=>n+(c.activities||[]).length,0);
          return `<details class="bilan-collection" data-bilan-collection-key="${attr(key)}" ${open?'open':''}><summary><span><strong>${esc(g.label||'Collection')}</strong><small>${g.courses.length} parcours · ${totalActivities} activités</small></span></summary><div class="bilan-course-list">${rows}</div></details>`;
        }).join('');
        const metrics=evidence.status==='not-started'?`<div class="bilan-empty-state evidence-empty"><strong>Non commencé</strong><span>Aucune preuve n’est encore enregistrée. Commencez par une première activité ou lancez un diagnostic si le sujet vous est déjà familier.</span></div>`:`<div class="bilan-summary-strip evidence-summary"><span class="evidence-main is-${attr(evidence.status)}"><b>${esc(evidence.statusLabel)}</b><small>état des preuves</small></span><span><b>${evidence.exposed}/${evidence.total}</b><small>activités vues</small></span><span><b>${evidence.succeeded}</b><small>réussies au moins une fois</small></span><span class="${evidence.fragile?'warn':''}"><b>${evidence.fragile}</b><small>fragiles</small></span></div>`;
        const objectiveRows=(evidence.objectives||[]).map(row=>`<li class="bilan-objective-row is-${attr(row.status)}"><span class="chapter-state-dot" aria-hidden="true"></span><span class="chapter-main"><strong>${esc(row.label)}</strong><small>${esc(evidenceDetail(row))}</small></span><span class="badge ${evidenceTone(row.status)}">${esc(row.statusLabel)}</span></li>`).join('');
        const chapterRows=(evidence.chapters||[]).map((row,index)=>`<li class="bilan-chapter-row is-${attr(row.status)}"><span class="chapter-state-dot" aria-hidden="true"></span><span class="chapter-main"><strong>${esc(row.title||chapters[index]&&chapters[index].title||`Chapitre ${index+1}`)}</strong><small>${esc(evidenceDetail(row))}</small></span><span class="badge ${evidenceTone(row.status)}">${esc(row.statusLabel)}</span></li>`).join('');
        const evidenceBody=`<div class="bilan-objectives"><h2>État des objectifs</h2><ul>${objectiveRows}</ul></div><div class="bilan-chapters"><h2>État par chapitre</h2><ul>${chapterRows}</ul></div>`;
        const detailBody=`${metrics}<details class="bilan-structure" ${ia.openStructure?'open':''}><summary>Voir les objectifs et chapitres du parcours</summary>${evidenceBody}</details>`;
        const modeResult=modeOutcomePanel(runtime,selectedId);const secondaryAction=rec.secondary?`<button data-rc580-intent="${attr(rec.secondary.intent||rec.secondary.mode)}" data-mode="${attr(rec.secondary.mode)}" data-course="${attr(selectedId)}">${esc(rec.secondary.label)}</button>`:`<button data-action="bilan-go-learn" data-course="${attr(selectedId)}">Voir les autres modes</button>`;const boundary=ia.showBoundary?`<p class="mode-boundary-note bilan-mode-boundary"><strong>Diagnostic</strong> au début pour situer votre niveau · <strong>Validation</strong> à la fin pour vérifier vos acquis.</p>`:'';
        return `<section class="card view-page bilan-hierarchy rc532-bilan rc580-bilan-guidance rc593-evidence-bilan rc454-composed-route rc455-static-route" data-evidence-status="${attr(evidence.status)}" data-recommendation-code="${attr(rec.reasonCode||'unknown')}" data-decision-first="${ia.decisionFirst?'true':'false'}" data-primary-action-count="${Number(ia.primaryActionCount||1)}" data-secondary-action-count="${Number(ia.secondaryActionCount||0)}"><div class="view-title-head single"><div><div class="kicker view-kicker">Bilan</div><h1>${esc(selectedCourse.title||'Parcours')}</h1><p class="view-subtitle">${esc(selectedCollection?selectedCollection.label:'Collection')}</p></div></div>${modeResult}<section class="bilan-action-hero ${evidence.status==='fragile'?'warn':''}" aria-label="Prochaine étape" data-evidence-reason="${attr(rec.reasonCode)}"><div class="bilan-action-copy"><span class="bilan-section-kicker">Prochaine étape recommandée</span><strong>${esc(rec.label)}</strong><p>${esc(rec.reason)}</p></div><div class="bilan-action-buttons"><button class="primary" ${recAttrs}>${esc(rec.label)}</button>${secondaryAction}</div></section>${boundary}<div class="bilan-two-pane"><aside class="bilan-nav" aria-label="Collections et parcours">${navHtml}</aside><section class="bilan-detail">${detailBody}</section></div>${bilanExtension(runtime,selectedCourse,evidence)}</section>`;
      }

      function tools(runtime){
        const val=runtime.contentStore.validation;
        const gates=runtime.gates();
        const qa=buildContentQa(runtime.contentStore.content,val);
        const runtimeReport=buildRuntimeReport(runtime);
        const importDiag=buildImportDiagnostics(runtime);
        const importPreview=buildImportPreviewPanel(runtime);
        const readableImportPanel=buildReadableImportDiagnosticsPanel(runtime);
        const appliedImportPanel=buildAppliedImportPanel(runtime);
        const contractPanel=buildAiKitContractPanel(runtime);
        const pedagogicalPanel=buildPedagogicalQualityPanel(runtime);
        const expertItems=[...qa.items.slice(0,8),...importDiag.items.slice(0,8)];
        return `<section class="card view-page tools-clean rc454-composed-route rc455-static-route"><div class="view-title-head single"><div><div class="kicker view-kicker">Outils</div><h1>Importer et sauvegarder</h1></div></div><div class="rc267-tools-intent" data-route-composer-owned="true" data-rc454-composed="true" data-rc455-static-route="true"><strong>Outils</strong>Importer, exporter ou diagnostiquer. Les diagnostics experts restent rangés plus bas.</div><div class="tool-primary-grid"><section class="plain tool-main-card"><h2>Importer un kit</h2><p class="useful">Choisir ou coller des kits, prévisualiser les changements, puis importer en une transaction.</p><div class="row"><span class="badge ${val.ok?'ok':'warn'}">${val.ok?'Contenu actif OK':'Contenu à vérifier'}</span><span class="badge">${runtime.contentStore.imported.length} importé(s)</span></div>${importFilePanel(runtime)}<textarea id="importDraft" spellcheck="false" placeholder="Coller un parcours ou un package JSON">${esc(runtime.contentStore.importDraft)}</textarea><div class="actions"><button data-action="sample-import">Exemple</button><button data-action="preview-import">Prévisualiser</button><button class="primary" data-action="apply-import">Importer les changements</button><button data-action="library-show-imported">Bibliothèque</button><button data-action="rollback-import">Annuler import</button></div>${readableImportPanel}${appliedImportPanel}${importPreview}</section><section class="plain tool-main-card"><h2>Sauvegarder</h2><p class="useful">Télécharger le contenu, les imports ou le bilan courant.</p><div class="actions"><button class="primary" data-action="export-content">Contenu</button><button data-action="export-imported">Imports</button><button data-action="export-applied-import">Historique import</button><button data-action="export-enriched-bilan">Bilan</button><button data-action="export-targeted-remediation">Reprise ciblée</button></div><p class="tiny">Les exports ne modifient jamais la progression.</p></section></div><details class="plain tool-expert-drawer"><summary>Diagnostics expert</summary><div class="rc208-status-strip"><span class="badge ${gates.ok?'ok':'warn'}">${gates.ok?'Gates OK':'Gates KO'}</span><span class="badge ${runtimeReport.ok?'ok':'warn'}">${runtimeReport.ok?'Runtime propre':'Runtime à vérifier'}</span><span class="badge ${qa.ok?'ok':'warn'}">${qa.ok?'QA OK':'QA KO'}</span></div><div class="actions"><button data-action="diagnose-import">Diagnostiquer import</button><button data-action="validate-import">Contrôler aperçu</button><button data-action="export-qa">Exporter QA</button><button data-action="export-gates">Exporter gates</button><button data-action="run-local-audit">Audit local</button><button data-action="export-field-evidence">Exporter preuves</button><button data-action="export-contract-diagnostics">Exporter contrat</button><button data-action="export-pedagogical-quality">Exporter qualité</button><button data-action="export-learning-loop">Boucle</button><button data-action="export-author-template">Modèle patch</button></div>${contractPanel}${pedagogicalPanel}<div class="qa-list">${expertItems.map(i=>`<div class="qa-item ${i.ok?'ok':'warn'}"><b>${i.ok?'OK':'HOLD'}</b><span><strong>${esc(i.label)}</strong>${i.detail?`<br><span class="tiny">${esc(i.detail)}</span>`:''}${i.repair?`<br><span class="tiny">Réparation : ${esc(i.repair)}</span>`:''}</span></div>`).join('')}</div></details><details class="plain tool-expert-drawer"><summary>Patch contenu</summary><p class="useful">Modifier le contenu seulement ; jamais le comportement du runtime.</p><textarea id="patchDraft" spellcheck="false" placeholder="Coller un patch de contenu JSON">${esc(runtime.contentStore.patchDraft)}</textarea><div class="actions"><button data-action="sample-patch">Exemple patch</button><button data-action="validate-patch">Valider patch</button><button class="primary" data-action="apply-patch">Appliquer patch</button><button data-action="rollback-patch">Rollback patch</button></div><p class="useful">${esc(runtime.toolMessage)}</p></details><details class="plain tool-expert-drawer"><summary>Journal local</summary><p>${runtime.journal.items.length} événement(s) enregistrés.</p><div class="actions"><button data-action="export-journal">Exporter journal</button><button data-action="export-improvements">Exporter pistes</button><button data-action="reset-journal">Réinitialiser journal</button><button class="danger" data-action="reset-all">Réinitialiser app</button></div></details></section>`;
      }

      function route(runtime,routeName){
        if(routeName==='library')return library(runtime);
        if(routeName==='bilan')return bilan(runtime);
        if(routeName==='tools')return tools(runtime);
        return learn(runtime);
      }
      return Object.freeze({schema:'learnit.rc696.route_view_composer.v2',route,learn,library,libraryV2,bilan,tools,kpis,score,due,reviewPolicy,remediation,libraryKpiStrip,learnExtension,bilanExtension,explainableEvidence,evidenceDetail,modeOutcomePanel,importFilePanel,nextAction,lastBilan});
    })();

    AppRuntime.prototype.learnView=function(){return RouteViewComposer.route(this,'learn');};
    AppRuntime.prototype.libraryView=function(){return RouteViewComposer.route(this,'library');};
    AppRuntime.prototype.libraryV2View=function(){return RouteViewComposer.libraryV2(this);};
    AppRuntime.prototype.bilanView=function(){return RouteViewComposer.route(this,'bilan');};
    AppRuntime.prototype.toolsView=function(){return RouteViewComposer.route(this,'tools');};
    window.LearnItRouteViewComposer=RouteViewComposer;
