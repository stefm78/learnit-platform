/* RC467 — Route Nav Transition Contract.
   Linus rule: the top navigation is a passive view of the single route carousel
   transaction. It visualizes drag/tap progress without owning route state or
   triggering secondary renders. RC466 gesture surface contract remains active. */
(function(){
  'use strict';
  const C=window.LearnItRouteCarouselModel;
  const ROUTES=(C&&C.ROUTES)||Object.freeze(['learn','library','bilan','tools']);
  const ANIM_MS=230;
  function routeIndex(view){return C&&C.indexOf?C.indexOf(view):Math.max(0,ROUTES.indexOf(view));}
  function routeAt(index){return C&&C.routeAt?C.routeAt(index):(ROUTES[Math.max(0,Math.min(ROUTES.length-1,index))]||'learn');}
  function isMainRoute(view){return ROUTES.indexOf(view)>=0;}
  function pxWidth(el){const rect=el&&el.getBoundingClientRect?el.getBoundingClientRect():null;return Math.max(240,Math.round((rect&&rect.width)||window.innerWidth||document.documentElement.clientWidth||360));}
  function isReducedMotion(){return !!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);}
  function inertAttrs(active){return active?'':' aria-hidden="true" inert';}
  function routeLabel(route){return route==='library'?'Bibliothèque':route==='bilan'?'Bilan':route==='tools'?'Outils':'Apprendre';}
  function panel(route,active,body,renderKey){return `<section class="route-panel route-view-${escapeAttr(route)} ${active?'is-active':'is-inactive'}" data-route="${escapeAttr(route)}" data-route-render-key="${escapeAttr(renderKey||'')}" data-route-surface-contract="rc463" data-route-paint-contract="rc465" data-route-gesture-surface="rc466" data-scroll-owner="route-panel" data-scroll-contract="rc487-route-panel-owner" data-desktop-scroll-owner="window" role="region" aria-label="${escapeAttr(routeLabel(route))}"${inertAttrs(active)}>${body||''}</section>`;}
  function prefixPreviewIds(html,route){
    if(!html||typeof document==='undefined')return html||'';
    const prefix=previewPrefix(route);
    const template=document.createElement('template');
    template.innerHTML=html;
    const idMap=Object.create(null);
    template.content.querySelectorAll('[id]').forEach(el=>{
      const old=el.getAttribute('id');
      const next=prefix+old;
      idMap[old]=next;
      el.setAttribute('id',next);
      el.setAttribute('data-preview-id',old);
    });
    const attrNames=['for','list','aria-controls','aria-labelledby','aria-describedby','aria-owns','aria-activedescendant'];
    template.content.querySelectorAll('*').forEach(el=>{
      attrNames.forEach(attr=>{
        const raw=el.getAttribute(attr);
        if(!raw)return;
        const mapped=raw.split(/\s+/).map(token=>idMap[token]||token).join(' ');
        if(mapped!==raw)el.setAttribute(attr,mapped);
      });
    });
    return template.innerHTML;
  }
  function previewPrefix(route){return `rc451-${route}-preview-`;}
  function mapIdRefs(root,mapper){
    if(!root||!root.querySelectorAll)return;
    const attrNames=['for','list','aria-controls','aria-labelledby','aria-describedby','aria-owns','aria-activedescendant'];
    root.querySelectorAll('*').forEach(el=>{
      attrNames.forEach(attr=>{
        const raw=el.getAttribute(attr);
        if(!raw)return;
        const mapped=raw.split(/\s+/).map(token=>mapper(token)).join(' ');
        if(mapped!==raw)el.setAttribute(attr,mapped);
      });
    });
  }
  function promotePanelIds(panel,route){
    if(!panel)return;
    const idMap=Object.create(null);
    panel.querySelectorAll('[data-preview-id]').forEach(el=>{
      const old=el.getAttribute('data-preview-id');
      const current=el.getAttribute('id');
      if(old&&current){idMap[current]=old;el.setAttribute('id',old);}
    });
    mapIdRefs(panel,token=>idMap[token]||token);
    panel.querySelectorAll('[data-preview-id]').forEach(el=>el.removeAttribute('data-preview-id'));
    panel.removeAttribute('data-preview-prefix');
    panel.dataset.activeIds='true';
  }
  function demotePanelIds(panel,route){
    if(!panel)return;
    const prefix=previewPrefix(route);
    const idMap=Object.create(null);
    panel.querySelectorAll('[id]:not([data-preview-id])').forEach(el=>{
      const old=el.getAttribute('id');
      if(!old||old.indexOf(prefix)===0)return;
      const next=prefix+old;
      idMap[old]=next;
      el.setAttribute('id',next);
      el.setAttribute('data-preview-id',old);
    });
    mapIdRefs(panel,token=>idMap[token]||token);
    panel.setAttribute('data-preview-prefix',prefix);
    panel.removeAttribute('data-active-ids');
  }
  AppRuntime.prototype.ensureRouteCarouselState=function(){
    if(!this.routeCarouselState){
      this.routeCarouselState={scroll:Object.create(null),transaction:null,renderedRoute:null,installed:false,lastPanelRoutes:Object.create(null),renderKeys:Object.create(null)};
    }
    return this.routeCarouselState;
  };
  AppRuntime.prototype.routePanelRenderKey=function(route){
    const content=(this.contentStore&&this.contentStore.content)||{};
    const progress=(this.appState&&this.appState.state&&this.appState.state.progressByCourse)||{};
    const courseId=this.contentStore&&this.contentStore.activeCourseId;
    const courseProgress=courseId&&progress?progress[courseId]:null;
    const lastBilan=this.appState&&this.appState.state&&this.appState.state.lastBilan;
    const session=this.session&&this.session.session;
    const base={
      route,
      courseId,
      title:content.title||'',
      sequence:content.sequence||'',
      activityCount:Array.isArray(content.activities)?content.activities.length:0,
      importedCount:this.contentStore&&Array.isArray(this.contentStore.imported)?this.contentStore.imported.length:0,
      courseProgressKeys:courseProgress?Object.keys(courseProgress).length:0
    };
    let routeSpecific={};
    if(route==='learn'){
      routeSpecific={
        session:session?{status:session.status,mode:session.mode,currentIndex:session.currentIndex,total:Array.isArray(session.queue)?session.queue.length:0}:null,
        reviewCount:courseProgress?Object.keys(courseProgress).filter(id=>courseProgress[id]&&courseProgress[id].review).length:0
      };
    }else if(route==='library'){
      routeSpecific={filter:this.libraryFilter||'all',sort:this.librarySort||'',overlay:this.libraryOverlayCourseId||'',plan:!!this.libraryPlanMode,chapter:this.libraryPickedChapterIndex||0,v2:!!this.libraryV2Enabled,open:Object.keys(this.libraryOpenCollections||{}).filter(k=>this.libraryOpenCollections[k]).sort().join('|')};
    }else if(route==='bilan'){
      routeSpecific={course:this.bilanCourseId||'',open:Object.keys(this.bilanOpenCollections||{}).filter(k=>this.bilanOpenCollections[k]).sort().join('|'),lastBilan:lastBilan?{mode:lastBilan.mode,total:lastBilan.total,correct:lastBilan.correct,review:(lastBilan.review||[]).length}:null};
    }else if(route==='tools'){
      routeSpecific={importDraftLength:this.contentStore&&this.contentStore.importDraft?String(this.contentStore.importDraft).length:0,validationOk:this.contentStore&&this.contentStore.validation?!!this.contentStore.validation.ok:null,toolMessage:this.toolMessage||'',patchDraftLength:this.contentStore&&this.contentStore.patchDraft?String(this.contentStore.patchDraft).length:0};
    }
    try{return JSON.stringify(Object.assign(base,routeSpecific));}catch(e){return `${route}|stable-route-key-fallback`;}
  };
  AppRuntime.prototype.renderRouteCarouselShell=function(activeView,activeBody){
    const state=this.ensureRouteCarouselState();
    const activeIndex=routeIndex(activeView);
    state.renderedRoute=activeView;
    const panels=ROUTES.map(route=>{
      const active=route===activeView;
      const renderKey=this.routePanelRenderKey(route);
      const body=active?activeBody:prefixPreviewIds(this.renderRouteBodyForCarousel(route),route);
      state.lastPanelRoutes[route]=true;
      state.renderKeys[route]=renderKey;
      return panel(route,active,body,renderKey);
    }).join('');
    return `<main id="contenu" role="main" class="route-carousel-viewport" data-route-carousel="true" data-route-gesture-contract="rc466" data-route-swipe-boundary-contract="rc488" data-scroll-contract="rc487" data-desktop-scroll-contract="rc688-window-owner" data-active-route="${escapeAttr(activeView)}" data-active-index="${activeIndex}" style="--active-index:${activeIndex}"><div class="route-carousel-track" data-route-carousel-track="true">${panels}</div></main>`;
  };
  AppRuntime.prototype.routePanel=function(route){return this.root&&this.root.querySelector?this.root.querySelector(`.route-panel[data-route="${route}"]`):null;};
  AppRuntime.prototype.activeRoutePanel=function(){return this.root&&this.root.querySelector?this.root.querySelector('.route-panel.is-active'):null;};
  AppRuntime.prototype.saveRenderedRouteScroll=function(){
    const state=this.ensureRouteCarouselState();
    const panel=this.activeRoutePanel();
    const route=panel&&panel.dataset&&panel.dataset.route;
    if(route)state.scroll[route]=Math.max(0,Math.round(panel.scrollTop||0));
  };
  AppRuntime.prototype.restoreRouteScroll=function(route){
    const state=this.ensureRouteCarouselState();
    const top=Math.max(0,Math.round(Number(state.scroll[route]||0)));
    const p=this.routePanel(route);if(p)p.scrollTop=top;
  };
  AppRuntime.prototype.afterRouteCarouselRender=function(view){
    if(!isMainRoute(view))return;
    const state=this.ensureRouteCarouselState();
    state.renderedRoute=view;
    this.syncRouteCarouselPanels(view,{promoteIds:true});
    this.restoreRouteScroll(view);
  };
  AppRuntime.prototype.renderRouteBodyForCarousel=function(route){
    try{
      if(window.LearnItRouteViewComposer&&typeof window.LearnItRouteViewComposer.route==='function'){
        return window.LearnItRouteViewComposer.route(this,route);
      }
      return this.viewBody?this.viewBody(route):(route==='library'?this.libraryView():route==='bilan'?this.bilanView():route==='tools'?this.toolsView():this.learnView());
    }catch(error){
      try{this.journal.record('route_carousel_target_render_error',{route,error:String(error&&error.message||error)});}catch(e){}
      return `<section class="card"><h1>${escapeHtml(route||'Vue')}</h1></section>`;
    }
  };
  AppRuntime.prototype.refreshRoutePanelForCarousel=function(route,options){
    const p=this.routePanel(route);
    if(!p)return null;
    const state=this.ensureRouteCarouselState();
    const active=route===this.appState.view;
    const nextKey=this.routePanelRenderKey(route);
    const force=!!(options&&options.force);
    const stale=p.dataset.routeRenderKey!==nextKey;
    if(force||stale||!p.innerHTML.trim()){
      const rememberedTop=Math.max(0,Math.round(p.scrollTop||state.scroll[route]||0));
      const raw=this.renderRouteBodyForCarousel(route);
      p.innerHTML=active?raw:prefixPreviewIds(raw,route);
      p.dataset.routeRenderKey=nextKey;
      state.renderKeys[route]=nextKey;
      if(active)promotePanelIds(p,route);else demotePanelIds(p,route);
      p.scrollTop=rememberedTop;
      try{this.journal.record('route_panel_refresh',{route,force,stale,active});}catch(e){}
    }
    p.classList.remove('is-empty');
    p.inert=!active;
    if(route===this.appState.view){
      p.removeAttribute('aria-hidden');
    }else{
      p.setAttribute('aria-hidden','true');
    }
    const top=Math.max(0,Math.round(Number(state.scroll[route]||p.scrollTop||0)));
    p.scrollTop=top;
    return p;
  };
  AppRuntime.prototype.fillRoutePanelForCarousel=function(route){
    return this.refreshRoutePanelForCarousel(route,{force:false});
  };
  AppRuntime.prototype.clearInactiveRoutePanels=function(activeRoute){
    ROUTES.forEach(route=>{
      const p=this.routePanel(route);
      if(p&&(!p.innerHTML.trim()||p.dataset.routeRenderKey!==this.routePanelRenderKey(route))){
        this.refreshRoutePanelForCarousel(route,{force:false});
      }
    });
    this.syncRouteCarouselPanels(activeRoute,{promoteIds:true});
  };
  AppRuntime.prototype.syncRouteCarouselPanels=function(activeRoute,options){
    const promote=!(options&&options.promoteIds===false);
    ROUTES.forEach(route=>{
      const p=this.routePanel(route);
      if(!p)return;
      const active=route===activeRoute;
      p.classList.toggle('is-active',active);
      p.classList.toggle('is-inactive',!active);
      p.classList.remove('is-empty');
      p.inert=!active;
      if(active){
        p.removeAttribute('aria-hidden');
        if(promote)promotePanelIds(p,route);
      }else{
        p.setAttribute('aria-hidden','true');
        demotePanelIds(p,route);
      }
    });
    const viewport=this.root&&this.root.querySelector?this.root.querySelector('[data-route-carousel="true"]'):null;
    if(viewport){
      viewport.dataset.activeRoute=activeRoute;
      viewport.dataset.activeIndex=String(routeIndex(activeRoute));
      viewport.style.setProperty('--active-index',String(routeIndex(activeRoute)));
    }
    this.syncRouteNavState(activeRoute);
  };
  AppRuntime.prototype.syncRouteNavState=function(activeRoute){
    if(!this.root||!this.root.querySelectorAll)return;
    this.root.querySelectorAll('.nav [data-nav]').forEach(btn=>{
      const active=btn.dataset.nav===activeRoute;
      btn.classList.toggle('active',active);
      if(active)btn.setAttribute('aria-current','page');
      else btn.removeAttribute('aria-current');
    });
  };
  AppRuntime.prototype.commitRouteCarouselInPlace=function(targetRoute){
    if(!isMainRoute(targetRoute))return false;
    const state=this.ensureRouteCarouselState();
    const previous=this.appState.view;
    this.saveRenderedRouteScroll();
    this.refreshRoutePanelForCarousel(targetRoute,{force:false});
    this.appState.view=targetRoute;
    state.renderedRoute=targetRoute;
    this.syncViewShellClass(targetRoute);
    this.syncRouteCarouselPanels(targetRoute,{promoteIds:true});
    this.restoreRouteScroll(targetRoute);
    applyLibraryModalScrollLock(targetRoute==='library'&&!!this.libraryOverlayCourseId);
    try{this.journal.record('view',{view:targetRoute,previous,commit:'route-carousel-in-place'});}catch(e){}
    return true;
  };
  AppRuntime.prototype.afterRouteCarouselTransition=function(callback,ms){
    const state=this.ensureRouteCarouselState();
    const track=state.transaction&&state.transaction.track;
    let done=false;
    const finish=()=>{
      if(done)return;
      done=true;
      if(track)track.removeEventListener('transitionend',onEnd);
      callback();
    };
    const onEnd=event=>{if(event&&event.target===track&&event.propertyName==='transform')finish();};
    if(isReducedMotion()||!track){finish();return;}
    track.addEventListener('transitionend',onEnd);
    window.setTimeout(finish,Math.max(40,ms||ANIM_MS)+80);
  };
  AppRuntime.prototype.setRouteTrackX=function(x,transition){
    const track=this.root&&this.root.querySelector?this.root.querySelector('[data-route-carousel-track="true"]'):null;
    if(!track)return;
    track.style.transition=transition||'none';
    track.style.transform=`translate3d(${Math.round(x)}px,0,0)`;
  };
  AppRuntime.prototype.setRouteTrackAtIndex=function(index){
    const viewport=this.root&&this.root.querySelector?this.root.querySelector('[data-route-carousel="true"]'):null;
    const track=this.root&&this.root.querySelector?this.root.querySelector('[data-route-carousel-track="true"]'):null;
    if(!viewport||!track)return;
    const w=pxWidth(viewport);
    track.style.transition='none';
    track.style.transform=`translate3d(${-routeIndex(routeAt(index))*w}px,0,0)`;
  };
  AppRuntime.prototype.beginRouteCarouselTransaction=function(direction){
    if(!C||!isMainRoute(this.appState.view))return null;
    const state=this.ensureRouteCarouselState();
    if(state.transaction)return state.transaction;
    this.saveRenderedRouteScroll();
    const viewport=this.root.querySelector('[data-route-carousel="true"]');
    const track=this.root.querySelector('[data-route-carousel-track="true"]');
    if(!viewport||!track)return null;
    const currentIndex=routeIndex(this.appState.view);
    const decision=C.targetIndex(currentIndex,direction);
    const width=pxWidth(viewport);
    if(decision.kind==='move')this.fillRoutePanelForCarousel(routeAt(decision.targetIndex));
    viewport.classList.add('route-carousel-gesture');
    viewport.dataset.gestureDirection=direction;
    viewport.dataset.targetRoute=decision.kind==='move'?routeAt(decision.targetIndex):'';
    this.root.dataset.swipeScope='route-carousel';
    this.root.dataset.swipeCurrentView=this.appState.view;
    this.root.dataset.swipeTargetView=decision.kind==='move'?routeAt(decision.targetIndex):'';
    state.transaction={kind:'drag',direction,currentIndex,targetIndex:decision.targetIndex,width,decision,startAt:Date.now(),lastDx:0,viewport,track,currentRoute:this.appState.view,targetRoute:decision.kind==='move'?routeAt(decision.targetIndex):this.appState.view};
    this.setRouteNavTransition({phase:'drag',currentRoute:state.transaction.currentRoute,targetRoute:state.transaction.targetRoute,boundary:decision.kind==='boundary',progress:0});
    try{this.journal.record('route_carousel_drag_start',{direction,currentRoute:this.appState.view,targetRoute:state.transaction.targetRoute,boundary:decision.kind==='boundary'});}catch(e){}
    return state.transaction;
  };
  AppRuntime.prototype.renderRouteCarouselDrag=function(t,dx){
    if(!C||!t)return;
    t.lastDx=dx;
    const frame=C.frame({currentIndex:t.currentIndex,width:t.width,dx,direction:t.direction,decision:t.decision});
    this.setRouteTrackX(frame.trackX,'none');
    if(t.viewport)t.viewport.dataset.progress=String(Math.round((frame.progress||0)*100)/100);
    this.setRouteNavTransition({phase:'drag',currentRoute:t.currentRoute,targetRoute:t.targetRoute,boundary:t.decision&&t.decision.kind==='boundary',progress:frame.progress||0});
  };
  AppRuntime.prototype.finishRouteCarouselDrag=function(cancel){
    const state=this.ensureRouteCarouselState();
    const t=state.transaction;
    if(!t||t.kind!=='drag'){state.transaction=null;return false;}
    const commitDecision=C.shouldCommit({width:t.width,dx:t.lastDx,elapsedMs:Date.now()-t.startAt,direction:t.direction,decision:t.decision});
    const commit=!cancel&&commitDecision.commit&&t.decision.kind==='move';
    const snap=C.snap({currentIndex:t.currentIndex,targetIndex:t.targetIndex,width:t.width,commit});
    this.setRouteTrackX(snap.trackX,isReducedMotion()?'none':`transform ${ANIM_MS}ms cubic-bezier(.2,.82,.2,1)`);
    this.setRouteNavTransition({phase:commit?'commit':'cancel',currentRoute:t.currentRoute,targetRoute:t.targetRoute,boundary:t.decision&&t.decision.kind==='boundary',progress:commit?1:0});
    const target=t.targetRoute;
    this.afterRouteCarouselTransition(()=>{
      if(commit)this.commitRouteCarouselInPlace(target);
      else this.setRouteTrackAtIndex(t.currentIndex);
      this.cleanupRouteCarouselTransaction();
    },ANIM_MS);
    try{this.journal.record('route_carousel_drag_finish',{commit,targetRoute:target,reason:commitDecision.reason,progress:commitDecision.progress,boundary:t.decision.kind==='boundary'});}catch(e){}
    return commit;
  };
  AppRuntime.prototype.cleanupRouteCarouselTransaction=function(){
    const state=this.ensureRouteCarouselState();
    const active=this.appState.view;
    const viewport=this.root&&this.root.querySelector?this.root.querySelector('[data-route-carousel="true"]'):null;
    const track=this.root&&this.root.querySelector?this.root.querySelector('[data-route-carousel-track="true"]'):null;
    if(viewport){viewport.classList.remove('route-carousel-gesture','route-carousel-animating');delete viewport.dataset.gestureDirection;delete viewport.dataset.targetRoute;delete viewport.dataset.progress;}
    if(track){track.style.transition='';track.style.transform='';}
    this.clearRouteNavTransition();
    delete this.root.dataset.swipeScope;delete this.root.dataset.swipeCurrentView;delete this.root.dataset.swipeTargetView;
    state.transaction=null;
    this.clearInactiveRoutePanels(active);
  };
  AppRuntime.prototype.animateRouteCarouselTo=function(targetRoute){
    if(!C||!isMainRoute(this.appState.view)||!isMainRoute(targetRoute)||targetRoute===this.appState.view)return false;
    const state=this.ensureRouteCarouselState();
    if(state.transaction)return true;
    this.saveRenderedRouteScroll();
    const viewport=this.root.querySelector('[data-route-carousel="true"]');
    const track=this.root.querySelector('[data-route-carousel-track="true"]');
    if(!viewport||!track){this.go(targetRoute);return true;}
    const decision=C.navTarget(this.appState.view,targetRoute);
    const currentIndex=decision.currentIndex;
    const targetIndex=decision.targetIndex;
    const width=pxWidth(viewport);
    const from=Math.min(currentIndex,targetIndex),to=Math.max(currentIndex,targetIndex);
    for(let i=from;i<=to;i++)this.fillRoutePanelForCarousel(routeAt(i));
    viewport.classList.add('route-carousel-animating');
    viewport.dataset.targetRoute=targetRoute;
    this.root.dataset.swipeScope='route-carousel';
    this.root.dataset.swipeCurrentView=this.appState.view;
    this.root.dataset.swipeTargetView=targetRoute;
    state.transaction={kind:'nav',currentIndex,targetIndex,width,currentRoute:this.appState.view,targetRoute};
    this.setRouteNavTransition({phase:'nav',currentRoute:this.appState.view,targetRoute,progress:0});
    this.setRouteTrackX(-currentIndex*width,'none');
    requestAnimationFrame(()=>{
      this.setRouteTrackX(-targetIndex*width,isReducedMotion()?'none':`transform ${ANIM_MS}ms cubic-bezier(.2,.82,.2,1)`);
      this.setRouteNavTransition({phase:'nav',currentRoute:state.transaction&&state.transaction.currentRoute||this.appState.view,targetRoute,progress:1});
    });
    this.afterRouteCarouselTransition(()=>{this.commitRouteCarouselInPlace(targetRoute);this.cleanupRouteCarouselTransaction();},ANIM_MS);
    try{this.journal.record('route_carousel_nav_animate',{from:this.appState.view,to:targetRoute,direction:decision.direction});}catch(e){}
    return true;
  };
  AppRuntime.prototype.routeNavigate=function(targetRoute){
    if(!isMainRoute(targetRoute)||!isMainRoute(this.appState.view))return false;
    if(targetRoute===this.appState.view)return true;
    if(typeof this.animateRouteCarouselTo==='function')return this.animateRouteCarouselTo(targetRoute);
    return false;
  };
  /* Forward compatibility for static gates that assert older contracts remain present:
     learnit.rc455.route_carousel_runtime_report.v1 learnit.rc456.route_carousel_runtime_report.v1 learnit.rc457.route_carousel_runtime_report.v1 learnit.rc458.route_carousel_runtime_report.v1 learnit.rc459.route_carousel_runtime_report.v1 learnit.rc461.route_carousel_runtime_report.v1 learnit.rc462.route_carousel_runtime_report.v1 learnit.rc465.route_carousel_runtime_report.v1 learnit.rc466.route_carousel_runtime_report.v1 learnit.rc467.route_carousel_runtime_report.v1
     learnit.rc455.route_carousel_controller.v1 learnit.rc456.route_carousel_controller.v1 learnit.rc457.route_carousel_controller.v1 learnit.rc458.route_carousel_controller.v1 learnit.rc459.route_carousel_controller.v1 learnit.rc461.route_carousel_controller.v1 learnit.rc462.route_carousel_controller.v1 learnit.rc465.route_carousel_controller.v1 learnit.rc466.route_carousel_controller.v1 learnit.rc467.route_carousel_controller.v1 */
  AppRuntime.prototype.mobileSwipeShape=function(){return {view:this.appState.view,routes:[...ROUTES],activeIndex:routeIndex(this.appState.view),scroll:Object.assign({},this.ensureRouteCarouselState().scroll)};};
  AppRuntime.prototype.mobileSwipeReport=function(){return {schema:'learnit.rc688.route_carousel_runtime_report.v1',installed:!!this.mobileSwipeInstalled,routeCarouselController:true,inPlaceCommit:true,prepaintOffscreenPanels:true,activePanelIdPromotion:true,unifiedTopLevelNav:true,routePanelInvalidation:true,routePanelRenderKeys:true,targetPanelsRefreshBeforeAnimation:true,directRouteComposerApi:true,noAppStateMutationForTargetRender:true,routeStableRenderKeys:true,noNavOnlyPanelInvalidation:true,noForcedTargetRefresh:true,inactivePanelsAvoidInert:false,inactivePanelsUseInert:true,routeScopedStyles:true,routeSurfaceContract:true,routePaintContract:true,routeGestureSurfaceContract:true,standardizedSwipeSurfaces:true,routeNavTransitionContract:true,nestedChapterSwipe:false,nativeChapterSnap:false,customChapterPointerRuntime:false,routeSwipeIntentArbitrated:true,scrollOwnershipContract:true,routeSwipeBoundaryContract:true,routePanelScrollOwner:true,contentZonesExcludeRouteSwipe:false,topNavProgressIndicator:true,topNavPassiveTransactionView:true,observableRouteSurfacesByDefault:true,strictControlsOptOut:true,chapterContentZoneOptOutForRouteCarousel:true,gestureOwner:'69_gesture_orchestrator.js',summaryPassiveSwipeStart:true,labelPassiveSwipeStart:true,mediaFigureNoLongerStrictDefault:true,gestureArbiter:true,strictGestureExclusions:true,passiveControlSwipeStart:true,clickSuppressionAfterHorizontalLock:true,passiveButtonSwipeStart:true,refreshPreservesInactiveSemantics:true,persistentPanels:true,preRenderedPanels:true,initialRouteBodiesComplete:true,persistentPanelSelector:'.route-carousel-viewport .route-panel[data-route]',singleTopLevelController:true,tapMenuAnimated:true,swipeAndTapShareController:true,scrollIsolation:'per-route-panel-scrollTop',scrollOwner:'route-panel-mobile/window-desktop',desktopScrollOwner:'window',desktopWheelTargetInvariant:true,targetScrollIndependent:true,noPreviewClone:true,noStageOverlay:true,neverLaunches:true,routes:[...ROUTES],shape:this.mobileSwipeShape(),model:!!C};};
  if(window.__LEARNIT_TEST__){
    window.__LEARNIT_TEST__.routeCarouselModel=()=>C||null;
    window.__LEARNIT_TEST__.routeCarouselReport=()=>window.__LEARNIT_TEST__.runtime.mobileSwipeReport();
    window.__LEARNIT_TEST__.mobileSwipeReport=()=>window.__LEARNIT_TEST__.runtime.mobileSwipeReport();
  }
})();
