    function rc193HumanizePackageLabel(packageId){
      const raw=String(packageId||'').trim();
      if(!raw)return 'Imports';
      let tokens=raw.replace(/[_]+/g,'-').split('-').filter(Boolean);
      tokens=tokens.filter(t=>!/^rc\d+$/i.test(t) && !/^v?\d+(?:\.\d+)*$/i.test(t) && !/^(learnit|package|sample|importable|plus|content|demo|import)$/i.test(t));
      if(!tokens.length)return 'Imports';
      const cleaned=tokens.map(rc193TitleCaseToken).join(' ');
      return cleaned.replace(/\bNombres Complexes\b/,'Nombres complexes').replace(/\bElectricite\b/,'Électricité');
    }


    function applyLibraryModalScrollLock(active){
      /* RC663 — the library sheet owns scroll while it is open. We lock only
         the active route panel; no body positioning trick and no scroll jump. */
      const body = document.body;
      if(!body) return;
      body.classList.toggle('learnit-modal-scroll-lock',!!active);
    }

    function saveLibrarySheetScroll(runtime){
      if(!runtime||!runtime.root||!runtime.libraryOverlayCourseId)return;
      const body=runtime.root.querySelector('.book-detail-sheet .book-modal-body');
      if(body)runtime.librarySheetScrollTop=Math.max(0,Math.round(body.scrollTop||0));
    }

    function restoreLibrarySheetScroll(runtime){
      if(!runtime||!runtime.root||!runtime.libraryOverlayCourseId)return;
      const body=runtime.root.querySelector('.book-detail-sheet .book-modal-body');
      if(!body)return;
      const top=Math.max(0,Math.round(Number(runtime.librarySheetScrollTop||0)));
      body.scrollTop=Math.min(top,Math.max(0,body.scrollHeight-body.clientHeight));
    }

    function queueLibrarySearch(runtime,input){
      if(!runtime||!input)return;
      const value=input.value||'';
      const selection={start:Number.isInteger(input.selectionStart)?input.selectionStart:value.length,end:Number.isInteger(input.selectionEnd)?input.selectionEnd:value.length,direction:input.selectionDirection||'none'};
      runtime.libraryQuery=value;
      runtime.librarySearchSelection=selection;
      if(runtime.librarySearchTimer)clearTimeout(runtime.librarySearchTimer);
      runtime.librarySearchTimer=setTimeout(()=>{
        runtime.librarySearchTimer=0;
        if(runtime.appState.view!=='library')return;
        runtime.render();
        requestAnimationFrame(()=>{
          const next=runtime.root.querySelector('#librarySearch');
          if(!next)return;
          next.focus({preventScroll:true});
          const limit=next.value.length;
          const start=Math.max(0,Math.min(selection.start,limit));
          const end=Math.max(start,Math.min(selection.end,limit));
          try{next.setSelectionRange(start,end,selection.direction);}catch(e){/* search input fallback */}
        });
      },120);
    }

    class AppRuntime{
      constructor(root){this.root=root;this.journal=new UxJournal();this.contentStore=new ContentStore(this.journal);this.appState=new AppState(this.journal,this.contentStore);this.session=new SessionController(this.appState,this.journal,this.contentStore);this.mirror=new LearningMirror(this.session);this.answer=new AnswerController(this);this.renderer=new ActivityRenderer(this);this.shell=new NavigationShell(this);this.bound=false;this.toolMessage='';this.drag=null;this.suppressNextClick=false;this.libraryFilter='all';this.librarySort='recommended';this.libraryQuery='';this.librarySearchTimer=0;this.librarySearchSelection=null;this.librarySheetFocusPending=false;this.librarySheetScrollTop=0;this.libraryV2Enabled=true;this.libraryOverlayCourseId=null;this.libraryPlanMode=false;this.libraryPickedChapterIndex=0;this.libraryOpenCollections=Object.create(null);this.libraryRenameCourseId=null;this.libraryRenameDraft='';this.libraryRenameMessage='';this.bilanCourseId=null;this.bilanOpenCollections=Object.create(null);}
      boot(){if(this.bound)return;this.bound=true;this.root.addEventListener('click',e=>this.handleClick(e));this.root.addEventListener('toggle',e=>this.handleLibraryCollectionToggle(e),true);this.root.addEventListener('pointerdown',e=>this.handlePointerDown(e));document.addEventListener('pointermove',e=>this.handlePointerMove(e),{passive:false});document.addEventListener('pointerup',e=>this.handlePointerUp(e));document.addEventListener('pointercancel',e=>this.handlePointerCancel(e));window.addEventListener('blur',()=>this.cleanupDrag(true));document.addEventListener('visibilitychange',()=>{if(document.visibilityState!=='visible')this.cleanupDrag(true);});this.root.addEventListener('input',e=>{if(e.target&&e.target.id==='patchDraft')this.contentStore.patchDraft=e.target.value;if(e.target&&e.target.id==='importDraft'){this.contentStore.importDraft=e.target.value;this.contentStore.importPreviewConfirmed=false;this.contentStore.importPreviewPlan=null;}if(e.target&&e.target.id==='librarySearch'){queueLibrarySearch(this,e.target);}if(e.target&&e.target.matches&&e.target.matches('.import-title-override')){this.contentStore.setImportTitleOverride(e.target.dataset.importTitleKey,e.target.value);}if(e.target&&e.target.id==='courseRenameInput'){this.libraryRenameDraft=e.target.value;}});this.root.addEventListener('change',e=>{if(e.target&&e.target.id==='librarySort'){this.librarySort=e.target.value||'recommended';this.render();}if(e.target&&e.target.matches&&e.target.matches('.import-title-override')){this.contentStore.setImportTitleOverride(e.target.dataset.importTitleKey,e.target.value);this.render();}});this.journal.record('boot',{version:VERSION_LABEL,build:APP_BUILD});if(typeof this.installMobileSwipeNavigation==='function')this.installMobileSwipeNavigation();if(typeof this.installLibraryChapterSwipeNavigation==='function')this.installLibraryChapterSwipeNavigation();this.render();this.contentStore.durableHydrationPromise=this.contentStore.hydrateDurableLibrary().then(result=>{if(result&&result.changed){this.appState.state=this.appState.load();this.appState.ensureCourseState();this.appState.alignWithContent();this.answer.reset();}if(result)this.render();return result;});window.addEventListener('pagehide',()=>{this.contentStore.flushDurable();},{capture:true});}
      go(view){const previous=this.appState.view;this.appState.view=view;this.journal.record('view',{view});try{this.render();}catch(error){this.appState.view=previous;this.journal.record('render_error',{view,error:String(error&&error.message||error)});try{this.render();}catch(fallbackError){console.error('[Learn-it render fallback failed]',fallbackError);}console.error('[Learn-it render failed]',error);}}
      scrollTop(){requestAnimationFrame(()=>window.scrollTo({top:0,behavior:'auto'}));}
      afterContentChange(){this.appState.alignWithContent();this.answer.reset();this.render();}
      canValidate(a){if(a.type==='qcm')return (window.LearnItQcmActivity&&typeof window.LearnItQcmActivity.isComplete==='function')?window.LearnItQcmActivity.isComplete(a,this.answer.pending):Number.isInteger(this.answer.pending);if(a.type==='fill')return (window.LearnItFillActivity&&typeof window.LearnItFillActivity.isComplete==='function')?window.LearnItFillActivity.isComplete(a,this.answer.pending):(Array.isArray(this.answer.pending)&&this.answer.pending.every(Boolean));if(a.type==='matching')return (window.LearnItMatchingActivity&&typeof window.LearnItMatchingActivity.isComplete==='function')?window.LearnItMatchingActivity.isComplete(a,this.answer.pending):(this.answer.pending&&Object.keys(this.answer.pending.matches||{}).length===a.pairs.length);if(a.type==='order')return Array.isArray(this.answer.pending)&&this.answer.pending.length===a.tokens.length;return false;}
      viewBody(view){if(view==='session')return this.sessionView();if(view==='library')return this.libraryView();if(view==='bilan')return this.bilanView();if(view==='tools')return this.toolsView();return this.learnView();}
      syncViewShellClass(view){const body=document.body;if(!body)return;['learn','library','bilan','tools','session'].forEach(v=>body.classList.toggle('view-'+v,view===v));body.classList.toggle('has-floating-nav',view!=='session');}
      render(){if(typeof this.saveRenderedRouteScroll==='function')this.saveRenderedRouteScroll();saveLibrarySheetScroll(this);const view=this.appState.view;if(typeof this.syncViewShellClass==='function')this.syncViewShellClass(view);const body=this.viewBody(view);const main=view==='session'||typeof this.renderRouteCarouselShell!=='function'?`<main id="contenu" role="main">${body}</main>`:this.renderRouteCarouselShell(view,body);const librarySheet=view==='library'&&this.libraryOverlayCourseId&&typeof this.renderLibraryBookOverlay==='function'?this.renderLibraryBookOverlay(this.libraryOverlayCourseId):'';this.root.innerHTML=this.shell.top()+main+this.shell.nav()+librarySheet;if(typeof this.syncViewShellClass==='function')this.syncViewShellClass(view);applyLibraryModalScrollLock(view==='library'&&!!this.libraryOverlayCourseId);if(typeof this.afterRouteCarouselRender==='function')this.afterRouteCarouselRender(view);if(view==='library'&&this.libraryOverlayCourseId){requestAnimationFrame(()=>restoreLibrarySheetScroll(this));}if(view==='library'&&this.libraryOverlayCourseId&&this.librarySheetFocusPending){this.librarySheetFocusPending=false;requestAnimationFrame(()=>{const close=this.root.querySelector('.book-detail-sheet [data-action="library-close-level"]');if(close)close.focus({preventScroll:true});});}}
      gates(){const text=this.root?this.root.innerText:'';const forbidden=screenForbidden.filter(x=>hasForbiddenMarker(text,x));const mirror=this.mirror.assert();const content=this.contentStore.validation;const qa=buildContentQa(this.contentStore.content,content);const runtime=buildRuntimeReport(this);const surfaces=buildSurfaceReport(this);const courseQa=buildCourseQa(this.contentStore.allCourses());return {ok:forbidden.length===0&&mirror.ok&&content.ok&&qa.ok&&runtime.ok&&surfaces.ok&&courseQa.ok,title:document['title'],forbidden,mirror,contentOk:content.ok,qaOk:qa.ok,runtimeOk:runtime.ok,surfaceOk:surfaces.ok,courseQaOk:courseQa.ok,activeCourseId:this.contentStore.activeCourseId,surfaceSimilarities:surfaces.similarities,patches:this.contentStore.history.length};}
      exportJson(name,data){const y=window.scrollY||document.documentElement.scrollTop||0;const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);this.journal.record('export_json',{name});requestAnimationFrame(()=>window.scrollTo({top:y,behavior:'auto'}));}
    }
