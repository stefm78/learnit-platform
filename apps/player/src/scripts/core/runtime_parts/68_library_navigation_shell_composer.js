/* RC667 — Library scalable detail sheet composer.
   Course detail and plan use a dedicated layered sheet instead of being
   appended after the collection list. The plan is list-first: the chapter
   list is the single navigation owner and the selected chapter drives one
   sticky contextual action. */
(function(){
  'use strict';
  function clamp(n,min,max){return Math.max(min,Math.min(max,n));}
  function courseIndex(runtime,courseId){const all=runtime.contentStore.allCourses().map(courseIdFromContent);return Math.max(0,all.indexOf(courseId));}
  function chapterCountLabel(count){return `${count} chapitre${count>1?'s':''}`;}
  function head(runtime,courseId,course,color,collectionLabel,courseNav,planMode,chapterCount){
    const headButtons=planMode?`<button class="book-icon" data-action="library-home" aria-label="Retour direct à la bibliothèque" title="Bibliothèque">⌂</button>`:'';
    const subtitleParts=[];
    if(collectionLabel)subtitleParts.push(collectionLabel);
    if(planMode)subtitleParts.push(chapterCountLabel(chapterCount));
    const subtitle=subtitleParts.length?`<div class="book-head-collection">${escapeHtml(subtitleParts.join(' · '))}</div>`:'';
    const nav=!planMode&&courseNav?`<div class="book-head-nav">${courseNav}</div>`:'';
    return `<div class="book-modal-head"><div class="book-head-title-wrap"><div class="book-head-title" id="libraryBookTitle">${escapeHtml(course.title)}</div>${subtitle}</div>${nav}<div class="book-head-actions">${headButtons}<button class="book-icon close" data-action="library-close-level" aria-label="Fermer le niveau courant" title="Fermer">×</button></div></div>`;
  }
  function chapterRows(runtime,course,k,chapters,picked,color){
    return chapters.map((ch,i)=>{
      const meta=rc163ChapterMeta(runtime,course,ch,k,i);
      const tone=rc163ChapterTone(color,i,chapters.length);
      const status={done:'terminé',current:'en cours',review:'à revoir',todo:'à faire'}[meta.state]||'à faire';
      const micro=[`${meta.total} activité${meta.total>1?'s':''}`,`~${rc163FmtTime(meta.minutes)}`,status].concat(meta.review?[`${meta.review} fragile${meta.review>1?'s':''}`]:[]).join(' · ');
      return `<button type="button" role="option" aria-selected="${i===picked?'true':'false'}" class="chapter ${i===picked?'is-picked':''}" data-action="library-chapter" data-chapter="${i}" style="--bar:${tone}" aria-label="Sélectionner ${escapeAttr(ch.title)}"><span class="chapter-bar"></span><span class="chapter-line"><strong>${escapeHtml(ch.title)}</strong><span class="chapter-micro">${escapeHtml(micro)}</span></span></button>`;
    }).join('');
  }
  function chapterStaticPanel(runtime,course,courseId,k,chapters,picked,color){
    if(!chapters.length){return `<section class="chapter-static-panel is-empty" data-chapter-static-panel="rc667" data-chapter-nav-contract="list-first" data-chapter-index="0"><p class="muted">Aucun chapitre disponible.</p></section>`;}
    const safePicked=clamp(Number(picked)||0,0,chapters.length-1);
    const ch=chapters[safePicked];
    const meta=rc163ChapterMeta(runtime,course,ch,k,safePicked);
    const rows=chapterRows(runtime,course,k,chapters,safePicked,color);
    return `<section class="chapter-static-panel" data-chapter-static-panel="rc667" data-chapter-nav-contract="list-first" data-chapter-index="${safePicked}" aria-label="Plan du parcours, chapitre ${safePicked+1} sur ${chapters.length} sélectionné"><h2 class="sr-only">Plan du parcours</h2><div class="chapter-list" role="listbox" aria-label="Chapitres du parcours">${rows}</div><div class="chapter-action chapter-action-sticky" data-plan-action-owner="selected-chapter"><div class="chapter-action-row"><button class="chapter-go" data-action="library-chapter-go" data-course="${escapeAttr(courseId)}" data-chapter="${safePicked}">${escapeHtml(rc163ChapterActionLabel(meta.state))}</button></div></div></section>`;
  }
  function chapterStaticShell(runtime,course,courseId,k,chapters,picked,color){
    const count=chapters.length;
    const safePicked=clamp(Number(picked)||0,0,Math.max(0,count-1));
    return `<div class="chapter-static-shell" data-route-swipe-exclusion="content" data-content-scroll-surface="chapter" data-chapter-static-shell="rc667" data-chapter-navigation-contract="list-first" data-scroll-contract="rc663-sheet-body-owner" data-library-scroll-contract="sheet-body-owner" data-chapter-index="${safePicked}" data-chapter-count="${count}" aria-label="Plan en liste, sans navigation séquentielle ni swipe imbriqué">${chapterStaticPanel(runtime,course,courseId,k,chapters,safePicked,color)}</div>`;
  }
  function renamePanel(runtime,courseId,course){
    if(!course.importedAt)return '';
    if(runtime.libraryRenameCourseId!==courseId)return `<button class="book-secondary" data-action="library-rename-course" data-course="${escapeAttr(courseId)}">Renommer</button>`;
    const message=runtime.libraryRenameMessage?`<p class="tiny ${runtime.libraryRenameMessage.startsWith('Erreur')?'warn':''}">${escapeHtml(runtime.libraryRenameMessage)}</p>`:'';
    return `<div class="course-rename-editor"><label for="courseRenameInput">Nom du parcours</label><input id="courseRenameInput" value="${escapeAttr(runtime.libraryRenameDraft||course.title)}" maxlength="120" autocomplete="off"><div class="actions"><button type="button" class="primary" data-action="library-rename-save" data-course="${escapeAttr(courseId)}">Enregistrer</button><button type="button" data-action="library-rename-cancel">Annuler</button></div>${message}</div>`;
  }
  function sheet(runtime,color,content,planMode){
    const levelLabel=planMode?'Plan du parcours':'Détail du parcours';
    return `<section class="book-detail-shell book-detail-sheet rc163 rc198 rc468-library-nav-shell" data-library-detail-shell="rc663" data-library-modal-shell="rc663" data-route-swipe-exclusion="content" data-content-scroll-surface="library-detail" data-scroll-contract="rc663-layered-sheet" style="--c:${color}"><button type="button" class="book-sheet-backdrop" data-action="library-close-level" aria-label="Fermer ${escapeAttr(levelLabel)}" tabindex="-1"></button><article class="book-modal book-detail-panel ${planMode?'plan-mode':''}" role="dialog" aria-modal="true" aria-labelledby="libraryBookTitle" aria-describedby="librarySheetHint">${content}<span class="sr-only" id="librarySheetHint">Fenêtre superposée. Utilisez le bouton fermer ou la touche Échap pour revenir à la bibliothèque.</span></article></section>`;
  }
  function overlay(runtime,courseId){
    const course=runtime.contentStore.courseById(courseId);
    const order=courseIndex(runtime,courseId);
    const color=rc163CourseColor(order);
    const k=buildCourseProgressKpi(runtime,course);
    const actionLabel=courseActionLabel(k);
    const chapters=rc163Chapters(course);
    const picked=clamp(Number(runtime.libraryPickedChapterIndex||0),0,Math.max(0,chapters.length-1));
    const collectionLabel=runtime.libraryV2Enabled?runtime.libraryV2CurrentCollectionLabel(courseId):'';
    const courseNav=runtime.renderLibraryV2CourseNav(courseId);
    if(runtime.libraryPlanMode){
      return sheet(runtime,color,`${head(runtime,courseId,course,color,collectionLabel,'',true,chapters.length)}<div class="book-modal-body">${chapterStaticShell(runtime,course,courseId,k,chapters,picked,color)}</div>`,true);
    }
    const symbol=renderCourseJacketVisual(course);
    const next=rc163NextStep(runtime,course,k);
    return sheet(runtime,color,`${head(runtime,courseId,course,color,collectionLabel,courseNav,false,chapters.length)}<div class="book-modal-body"><div class="jacket-layout"><div class="book-wrap"><div class="book-cover" aria-hidden="true"><div class="cover-content"><div><h2 class="cover-title">${escapeHtml(course.title)}</h2><p class="cover-subtitle">${escapeHtml(course.sequence||'')}</p></div><div class="cover-symbol ${getCourseJacketAsset(course)?'jacket-asset':''}">${symbol}</div></div></div></div><section class="book-info"><p class="book-lead">${escapeHtml(course.sequence||'Parcours d’apprentissage')}</p><p class="backcopy">${escapeHtml(rc163BackCopy(course))}</p><div class="next-card"><span class="next-icon" aria-hidden="true">➜</span><strong>${escapeHtml(next)}</strong></div><div class="book-actions"><button class="book-primary" data-action="learn-course" data-course="${escapeAttr(courseId)}">${escapeHtml(actionLabel)}</button><button class="book-secondary" data-action="library-plan">Plan</button>${renamePanel(runtime,courseId,course)}</div></section></div></div>`,false);
  }
  window.LearnItLibraryNavigationShellComposer=Object.freeze({overlay,chapterStaticShell});
  AppRuntime.prototype.renderLibraryBookOverlay=function(courseId){return window.LearnItLibraryNavigationShellComposer.overlay(this,courseId);};
})();
