/* RC613-RC623 — Keyboard, focus, accessible state and resilient checkpoints.
   One owner only: no MutationObserver, no parallel gesture system, no modal shell. */
(function(){
  'use strict';

  const LIBRARY_KEY='learnit.library.state.rc496';
  const ACCESS_SCHEMA='learnit.accessibility_resilience.rc673.v1';
  const ROUTES=['learn','library','bilan','tools'];
  const ROUTE_LABELS={learn:'Apprendre',library:'Bibliothèque',bilan:'Bilan',tools:'Outils'};

  function safeJson(text){try{return JSON.parse(text);}catch(e){return null;}}
  function safeStoreGet(key){try{return storage.getItem(key)||'';}catch(e){return '';}}
  function safeStoreSet(key,value){try{storage.setItem(key,String(value));return true;}catch(e){return false;}}
  function courseExists(rt,id){return !!(id&&rt&&rt.contentStore&&rt.contentStore.courseById&&rt.contentStore.courseById(id));}
  function libraryPanel(rt){return rt&&typeof rt.routePanel==='function'?rt.routePanel('library'):null;}
  function activePanel(rt){if(!rt||!rt.root)return null;const route=rt.root.querySelector('.route-panel.is-active');if(route)return route;return rt.root.querySelector('[data-activity-shell="session"]')||rt.root;}
  const MODAL_FOCUSABLE='button:not([disabled]):not([tabindex="-1"]),a[href]:not([tabindex="-1"]),input:not([disabled]):not([tabindex="-1"]),select:not([disabled]):not([tabindex="-1"]),textarea:not([disabled]):not([tabindex="-1"]),summary:not([tabindex="-1"]),[tabindex]:not([tabindex="-1"])';
  function modalDialog(rt){return rt&&rt.root?rt.root.querySelector('.book-detail-sheet [role="dialog"][aria-modal="true"]'):null;}
  function modalFocusables(dialog){return dialog?Array.from(dialog.querySelectorAll(MODAL_FOCUSABLE)).filter(el=>!el.disabled&&!el.hidden&&!el.closest('[inert]')&&el.getClientRects().length>0):[];}
  function statusNode(){return document.getElementById('learnit-status');}
  function announce(text){const node=statusNode();if(!node)return;node.textContent='';requestAnimationFrame(()=>{node.textContent=String(text||'');});}
  function cssEscape(value){if(window.CSS&&typeof window.CSS.escape==='function')return window.CSS.escape(String(value));return String(value).replace(/[^a-zA-Z0-9_-]/g,'\\$&');}

  function readLibrary(){return safeJson(safeStoreGet(LIBRARY_KEY)||'null')||{};}
  function writeLibrary(state){return safeStoreSet(LIBRARY_KEY,JSON.stringify(state));}
  function captureLibrary(rt){
    const panel=libraryPanel(rt);
    return {schema:'learnit.rc496.library_state.v1',at:nowIso(),courseId:rt.libraryOverlayCourseId||rt.contentStore.activeCourseId||'',overlayCourseId:rt.libraryOverlayCourseId||'',planMode:!!rt.libraryPlanMode,chapterIndex:Math.max(0,Number(rt.libraryPickedChapterIndex||0)),filter:rt.libraryFilter||'all',sort:rt.librarySort||'recommended',scrollTop:panel?Math.max(0,Math.round(panel.scrollTop||0)):0};
  }
  function applyLibrary(rt,state){
    if(!rt||!state||state.schema!=='learnit.rc496.library_state.v1')return false;
    const id=state.overlayCourseId||state.courseId;
    if(courseExists(rt,id)){rt.libraryOverlayCourseId=state.overlayCourseId||id;rt.contentStore.setActiveCourse(id);rt.appState.alignWithContent();}
    rt.libraryPlanMode=!!state.planMode;rt.libraryPickedChapterIndex=Math.max(0,Number(state.chapterIndex||0));
    if(state.filter)rt.libraryFilter=state.filter;if(state.sort)rt.librarySort=state.sort;
    rt.__libraryStateRestoreScrollTop=Math.max(0,Number(state.scrollTop||0));return true;
  }
  function restoreLibraryScroll(rt){const top=Math.max(0,Number(rt&&rt.__libraryStateRestoreScrollTop||0));if(!top)return;requestAnimationFrame(()=>{const panel=libraryPanel(rt);if(panel)panel.scrollTop=top;});}

  function focusKey(el,index){
    if(!el)return '';
    if(el.id)return 'id:'+el.id;
    const d=el.dataset||{};
    const parts=['nav','action','qcmChoice','fillSlot','fillToken','matchLeft','dragMatchRight','dragOrderToken','course','chapter','filter','dir'].filter(k=>d[k]!==undefined).map(k=>k+'='+d[k]);
    if(parts.length)return el.tagName.toLowerCase()+':'+parts.join('|');
    return el.tagName.toLowerCase()+':'+String(el.getAttribute('aria-label')||el.textContent||'').trim().slice(0,80)+':'+index;
  }
  function decorateFocusKeys(rt){
    const root=rt&&rt.root;if(!root)return;
    const focusables=Array.from(root.querySelectorAll('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]'));
    focusables.forEach((el,index)=>{if(el.getAttribute('tabindex')!=='-1'||el.matches('h1,[role="status"]'))el.dataset.a11yFocusKey=focusKey(el,index);});
  }
  function captureFocus(rt){const el=document.activeElement;if(!el||!rt.root.contains(el))return null;return {key:el.dataset&&el.dataset.a11yFocusKey||focusKey(el,0),start:typeof el.selectionStart==='number'?el.selectionStart:null,end:typeof el.selectionEnd==='number'?el.selectionEnd:null};}
  function restoreFocus(rt,snapshot){
    if(!snapshot||!snapshot.key)return false;
    const el=rt.root.querySelector('[data-a11y-focus-key="'+cssEscape(snapshot.key)+'"]');
    if(!el||el.disabled||el.closest('[inert]'))return false;
    try{el.focus({preventScroll:true});if(snapshot.start!==null&&typeof el.setSelectionRange==='function')el.setSelectionRange(snapshot.start,snapshot.end);}catch(e){return false;}return true;
  }
  function focusRouteHeading(rt){
    const panel=activePanel(rt);const heading=panel&&panel.querySelector('h1');
    if(!heading)return false;heading.setAttribute('tabindex','-1');try{heading.focus({preventScroll:true});}catch(e){heading.focus();}return true;
  }
  function focusActionResult(rt,action){
    const panel=activePanel(rt);if(!panel)return false;
    let target=null;
    if(action==='validate')target=panel.querySelector('.feedback,[role="status"],.activity-feedback,[data-action="continue"]');
    else if(action==='flashcard-reveal')target=panel.querySelector('.flashcard-face.back,[data-action="flashcard-grade"]');
    else if(action==='continue')target=panel.querySelector('.activity-card h1,.activity-card h2,.activity-question,h1');
    if(!target)return false;if(!target.matches('button,a,input,select,textarea,[tabindex]'))target.setAttribute('tabindex','-1');
    try{target.focus({preventScroll:true});}catch(e){target.focus();}return true;
  }

  function ensureHelp(panel,type,text){
    if(!panel)return '';
    const id='a11y-help-'+type;let node=panel.querySelector('#'+id);
    if(!node){node=document.createElement('p');node.id=id;node.className='sr-only';panel.appendChild(node);}node.textContent=text;return id;
  }
  function enhanceActivity(rt,panel){
    const qcm=panel.querySelector('[data-activity-type="qcm"]');
    if(qcm){const id=ensureHelp(panel,'qcm','Utilisez les flèches pour parcourir les réponses, puis Entrée ou Espace pour choisir.');const group=qcm.querySelector('[role="radiogroup"]');if(group)group.setAttribute('aria-describedby',id);const radios=Array.from(qcm.querySelectorAll('[role="radio"]'));const selected=radios.findIndex(el=>el.getAttribute('aria-checked')==='true');radios.forEach((el,i)=>{el.tabIndex=i===(selected>=0?selected:0)?0:-1;});}
    const fill=panel.querySelector('[data-activity-type="fill"]');
    if(fill){const id=ensureHelp(panel,'fill','Choisissez un emplacement, puis un mot. Entrée ou Espace active chaque bouton.');fill.setAttribute('aria-describedby',id);const bank=fill.querySelector('.bank');if(bank)bank.setAttribute('role','group');}
    const matching=panel.querySelector('[data-activity-type="matching"]');
    if(matching){const id=ensureHelp(panel,'matching','Choisissez une réponse à placer, puis la case correspondante. Le glisser-déposer est facultatif.');matching.setAttribute('aria-describedby',id);matching.querySelectorAll('.label-bank,.matching-board').forEach(el=>el.setAttribute('role','group'));}
    const order=panel.querySelector('[data-activity-type="order"]');
    if(order){const id=ensureHelp(panel,'order','Sélectionnez une étape, puis utilisez les boutons Monter ou Descendre. Alt plus flèche haut ou bas fonctionne aussi.');order.setAttribute('aria-describedby',id);const board=order.querySelector('.order-board');if(board)board.setAttribute('role','list');order.querySelectorAll('[data-drag-order-token]').forEach((el,i)=>{el.setAttribute('aria-posinset',String(i+1));el.setAttribute('aria-setsize',String(order.querySelectorAll('[data-drag-order-token]').length));el.setAttribute('aria-keyshortcuts','Alt+ArrowUp Alt+ArrowDown');});}
    const flash=panel.querySelector('[data-activity-type="flashcard"]');if(flash){const id=ensureHelp(panel,'flashcard','Affichez la réponse, puis indiquez si vous la connaissiez.');flash.setAttribute('aria-describedby',id);}
  }
  function enhance(rt){
    if(!rt||!rt.root)return;
    const main=rt.root.querySelector('main#contenu');if(main)main.setAttribute('tabindex','-1');
    const nav=rt.root.querySelector('nav.nav');if(nav){nav.setAttribute('aria-label','Navigation principale, quatre sections');Array.from(nav.querySelectorAll('[data-nav]')).forEach((btn,i)=>{btn.setAttribute('aria-keyshortcuts','Alt+'+(i+1));btn.dataset.a11yRouteIndex=String(i);});}
    const panels=Array.from(rt.root.querySelectorAll('.route-panel[data-route]'));
    panels.forEach(panel=>{const active=panel.classList.contains('is-active');panel.inert=!active;panel.setAttribute('aria-hidden',active?'false':'true');const h=panel.querySelector('h1');if(h){const id='route-heading-'+panel.dataset.route;h.id=id;panel.setAttribute('aria-labelledby',id);}});
    const panel=activePanel(rt);if(panel){enhanceActivity(rt,panel);panel.querySelectorAll('.feedback').forEach(el=>{el.setAttribute('role',el.classList.contains('warn')?'alert':'status');el.setAttribute('aria-atomic','true');});panel.querySelectorAll('.import-status.is-warn,.diagnostic-blocker').forEach(el=>el.setAttribute('role','alert'));}
    const dialog=modalDialog(rt);
    if(dialog){
      Array.from(rt.root.children).forEach(child=>{if(child.closest&&child.closest('.book-detail-sheet'))return;if(child.classList&&child.classList.contains('book-detail-sheet'))return;child.inert=true;child.setAttribute('aria-hidden','true');child.dataset.modalBackgroundInert='true';});
      dialog.dataset.focusTrap='active';
    }
    decorateFocusKeys(rt);
    document.documentElement.dataset.reducedMotion=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches?'true':'false';
  }

  function moveFocus(items,current,delta){const list=Array.from(items).filter(el=>!el.disabled&&!el.closest('[inert]'));if(!list.length)return false;let index=list.indexOf(current);if(index<0)index=0;index=(index+delta+list.length)%list.length;list[index].focus();return true;}
  function keyboardHandler(rt,event){
    if(event.defaultPrevented)return;
    const dialog=modalDialog(rt);
    if(dialog&&event.key==='Tab'){
      const items=modalFocusables(dialog);
      if(items.length){
        const first=items[0],last=items[items.length-1],active=document.activeElement;
        if(event.shiftKey&&(active===first||!dialog.contains(active))){event.preventDefault();last.focus();return;}
        if(!event.shiftKey&&(active===last||!dialog.contains(active))){event.preventDefault();first.focus();return;}
      }
    }
    if(event.altKey&&!event.ctrlKey&&!event.metaKey&&/^Digit[1-4]$/.test(event.code)){const index=Number(event.code.slice(-1))-1;const btn=rt.root.querySelector('nav.nav [data-nav="'+ROUTES[index]+'"]');if(btn){event.preventDefault();rt.go(btn.dataset.nav);}return;}
    const target=event.target;if(!target||!rt.root.contains(target))return;
    const navButton=target.closest('nav.nav [data-nav]');
    if(navButton&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const buttons=Array.from(rt.root.querySelectorAll('nav.nav [data-nav]'));let next=event.key==='Home'?buttons[0]:event.key==='End'?buttons[buttons.length-1]:buttons[(buttons.indexOf(navButton)+(event.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length];if(next)rt.go(next.dataset.nav);return;}
    const radio=target.closest('[data-qcm-choice]');
    if(radio&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)){event.preventDefault();const radios=radio.closest('[role="radiogroup"]').querySelectorAll('[data-qcm-choice]');const list=Array.from(radios);let idx=event.key==='Home'?0:event.key==='End'?list.length-1:(list.indexOf(radio)+(['ArrowRight','ArrowDown'].includes(event.key)?1:-1)+list.length)%list.length;list[idx].click();requestAnimationFrame(()=>{const next=rt.root.querySelector('[data-qcm-choice="'+list[idx].dataset.qcmChoice+'"]');if(next)next.focus();});return;}
    const matchRight=target.closest('[data-drag-match-right]');
    if(matchRight&&['Enter',' '].includes(event.key)){event.preventDefault();rt.answer.chooseMatch(matchRight.dataset.dragMatchRight);announce('Réponse sélectionnée');return;}
    const matchLeft=target.closest('[data-match-left]');
    if(matchLeft&&['Enter',' '].includes(event.key)){event.preventDefault();rt.answer.selectMatchLeft(matchLeft.dataset.matchLeft);announce('Association placée');return;}
    const grouped=target.closest('[data-fill-slot],[data-fill-token],[data-drag-match-right],[data-match-left]');
    if(grouped&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)){const selector=grouped.matches('[data-fill-slot]')?'[data-fill-slot]':grouped.matches('[data-fill-token]')?'[data-fill-token]':grouped.matches('[data-drag-match-right]')?'[data-drag-match-right]':'[data-match-left]';const scope=grouped.closest('[data-activity-type]')||rt.root;const list=Array.from(scope.querySelectorAll(selector));event.preventDefault();if(event.key==='Home')list[0]&&list[0].focus();else if(event.key==='End')list[list.length-1]&&list[list.length-1].focus();else moveFocus(list,grouped,['ArrowRight','ArrowDown'].includes(event.key)?1:-1);return;}
    const orderCard=target.closest('[data-drag-order-token]');
    if(orderCard&&event.altKey&&['ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();const token=orderCard.dataset.dragOrderToken;rt.answer.orderToken(token);rt.answer.moveSelectedOrder(event.key==='ArrowUp'?-1:1);announce('Étape déplacée '+(event.key==='ArrowUp'?'vers le haut':'vers le bas'));return;}
    if(event.key==='Escape'){
      if(rt.drag&&typeof rt.cleanupDrag==='function'){event.preventDefault();rt.cleanupDrag(false);announce('Déplacement annulé');return;}
      const close=rt.root.querySelector('.book-detail-sheet [data-action="library-close-level"]');if(close){event.preventDefault();close.click();announce('Retour à la bibliothèque');}
    }
  }

  function checkpoint(rt,reason){
    if(!rt)return false;
    try{if(rt.appState&&typeof rt.appState.save==='function')rt.appState.save();if(rt.appState&&rt.appState.view==='library'&&typeof rt.saveLibraryState==='function')rt.saveLibraryState();const session=rt.appState&&rt.appState.state&&rt.appState.state.session||{};const meta={schema:'learnit.resilience_checkpoint.rc623.v1',at:nowIso(),reason,view:rt.appState&&rt.appState.view||'',courseId:rt.contentStore&&rt.contentStore.activeCourseId||'',sessionStatus:session.status||'idle',currentIndex:Number(session.currentIndex||0),contentVersion:session.contentVersion||''};safeStoreSet(RESILIENCE_META_KEY,JSON.stringify(meta));return true;}catch(e){return false;}
  }
  function recoveryReport(){return safeJson(safeStoreGet(RECOVERY_REPORT_KEY)||'null')||null;}
  function checkpointReport(){return safeJson(safeStoreGet(RESILIENCE_META_KEY)||'null')||null;}
  function installEvents(rt){
    if(rt.__a11yEventsInstalled)return;rt.__a11yEventsInstalled=true;
    rt.root.addEventListener('keydown',event=>keyboardHandler(rt,event),true);
    rt.root.addEventListener('click',event=>{const el=event.target.closest&&event.target.closest('button,a');if(!el)return;rt.__a11yLastAction=el.dataset.action||'';if(el.dataset.action==='library-open-course')rt.__libraryModalReturnFocus=captureFocus(rt);if(el.dataset.nav)rt.__a11yLastAction='route';},true);
    document.addEventListener('keydown',event=>keyboardHandler(rt,event),true);
    window.addEventListener('pagehide',()=>checkpoint(rt,'pagehide'),true);
    document.addEventListener('visibilitychange',()=>{if(document.visibilityState!=='visible')checkpoint(rt,'visibilitychange');},true);
  }

  const previousRender=AppRuntime.prototype.render;
  AppRuntime.prototype.render=function(){
    const modalWasOpen=!!modalDialog(this);const snapshot=captureFocus(this);const action=this.__a11yLastAction||'';this.__a11yLastAction='';
    const result=previousRender.apply(this,arguments);enhance(this);const modalNowOpen=!!modalDialog(this);
    requestAnimationFrame(()=>{
      enhance(this);
      if(modalWasOpen&&!modalNowOpen&&this.__libraryModalReturnFocus){const restored=restoreFocus(this,this.__libraryModalReturnFocus);this.__libraryModalReturnFocus=null;if(restored){announce('Retour à la bibliothèque');return;}}
      if(modalNowOpen){const dialog=modalDialog(this);if(dialog&&!dialog.contains(document.activeElement)){const first=modalFocusables(dialog)[0];if(first)first.focus({preventScroll:true});}}
      if(this.__a11yRouteFocus){this.__a11yRouteFocus=false;focusRouteHeading(this);announce(ROUTE_LABELS[this.appState.view]||'Section ouverte');return;}
      if(!restoreFocus(this,snapshot))focusActionResult(this,action);
    });
    return result;
  };
  const previousBoot=AppRuntime.prototype.boot;
  AppRuntime.prototype.boot=function(){
    if(!this.__libraryStateApplied)this.__libraryStateApplied=applyLibrary(this,readLibrary());
    installEvents(this);const result=previousBoot.apply(this,arguments);enhance(this);if(this.appState.view==='library')restoreLibraryScroll(this);
    const checkpointData=checkpointReport();if(checkpointData&&checkpointData.sessionStatus==='active'&&this.appState.state.session&&this.appState.state.session.status==='active'){document.documentElement.dataset.resumedSession='true';announce('Séance précédente disponible.');}
    return result;
  };
  const previousGo=AppRuntime.prototype.go;
  AppRuntime.prototype.go=function(view){
    const from=this.appState&&this.appState.view;if(from==='library'&&this.saveLibraryState)this.saveLibraryState();if(view!==from)this.__a11yRouteFocus=true;
    const result=previousGo.apply(this,arguments);if(view==='library')restoreLibraryScroll(this);checkpoint(this,'route-change');return result;
  };
  AppRuntime.prototype.saveLibraryState=function(){return writeLibrary(captureLibrary(this));};
  AppRuntime.prototype.loadLibraryState=function(){return readLibrary();};
  AppRuntime.prototype.libraryStatePersistenceReport=function(){return {schema:'learnit.rc623.library_state_persistence_report.v2',installed:true,key:LIBRARY_KEY,routePanelScroll:true,storesCourse:true,storesChapter:true,noGestureAdded:true};};
  AppRuntime.prototype.accessibilityReport=function(){
    enhance(this);const panels=Array.from(this.root.querySelectorAll('.route-panel'));const dialog=modalDialog(this);const active=panels.filter(p=>!p.inert&&p.getAttribute('aria-hidden')!=='true');const hiddenFocusable=panels.filter(p=>p.getAttribute('aria-hidden')==='true'&&!p.inert).reduce((n,p)=>n+p.querySelectorAll('button,a,input,select,textarea,[tabindex="0"]').length,0);return {schema:ACCESS_SCHEMA,installed:true,skipLink:!!document.querySelector('.skip-link[href="#contenu"]'),liveRegion:!!statusNode(),main:!!this.root.querySelector('main#contenu[tabindex="-1"]'),activePanels:active.length,inactivePanelsInert:panels.filter(p=>p.inert).length,hiddenFocusable,keyboardRoutes:true,keyboardActivities:true,focusRestoration:true,modalOpen:!!dialog,modalFocusTrap:!!(dialog&&dialog.dataset.focusTrap==='active'),modalBackgroundInert:!!(dialog&&this.root.querySelectorAll('[data-modal-background-inert="true"][inert]').length>=2),modalEscape:true,modalFocusReturn:true,reducedMotion:document.documentElement.dataset.reducedMotion==='true'};
  };
  AppRuntime.prototype.resilienceReport=function(){const state=this.appState&&this.appState.state||{};return {schema:'learnit.resilience_report.rc623.v1',stateSchemaVersion:state.stateSchemaVersion||0,expectedStateSchemaVersion:STATE_SCHEMA_VERSION,recovery:recoveryReport(),checkpoint:checkpointReport(),sessionStatus:state.session&&state.session.status||'idle',transactionRecovery:true};};
  const previousMobileReport=AppRuntime.prototype.mobileSwipeReport;
  AppRuntime.prototype.mobileSwipeReport=function(){const base=previousMobileReport?previousMobileReport.call(this):{};return Object.assign({},base,{schema:'learnit.rc623.route_carousel_runtime_report.v2',nestedChapterSwipe:false,nativeChapterSnap:false,customChapterPointerRuntime:false,libraryStatePersistence:true,chapterNavigation:'list-first',keyboardAlternative:true,reducedMotionAlternative:true});};

  if(window.__LEARNIT_TEST__){window.__LEARNIT_TEST__.libraryStatePersistenceReport=()=>runtime.libraryStatePersistenceReport();window.__LEARNIT_TEST__.accessibilityReport=()=>runtime.accessibilityReport();window.__LEARNIT_TEST__.resilienceReport=()=>runtime.resilienceReport();window.__LEARNIT_TEST__.checkpoint=reason=>checkpoint(runtime,reason||'test');}
})();
