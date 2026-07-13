/* RC496 — Route-only Gesture Orchestrator.
   Linus decision: one custom horizontal gesture remains: the top-level route
   carousel. Chapter navigation has no swipe and no scroll-snap bridge. The
   chapter zone is an explicit vertical/tap surface excluded from route swipe. */
(function(){
  'use strict';
  const RouteModel=window.LearnItRouteCarouselModel;
  const IntentModel=window.LearnItRouteGestureIntentModel;
  const STRICT='input,textarea,select,option,[contenteditable="true"],[data-drag-order-token],[data-drag-match-right],.drag-ghost,.horizontal-scroll,[data-no-swipe],[data-no-route-swipe],[data-route-swipe="strict"],.media-figure.is-zooming,.media-figure[data-zoom-active="true"]';
  const CONTENT_EXCLUSION='[data-route-swipe-exclusion="content"],[data-chapter-static-shell],[data-library-detail-shell],.chapter-static-shell,.book-detail-shell';
  const PASSIVE='button,a,[role="button"],summary,label,.chapter,.chapter-nav-card,.chapter-go,.course-nav-card,.book-primary,.book-secondary,.book-icon';
  const ROUTE_SURFACE='.route-panel,.nav,[data-route-swipe-surface],[data-route-gesture-surface],.card,.view-page,.library-page,.bilan-panel,.tool-primary-grid,.qa-item,.collection,summary,label,button,a,[role="button"]';
  const SCROLL_OWNER='.book-modal-body,.route-panel,.library-list,.collection-list,.chapter-list,.tool-stack,.bilan-two-pane,.activity-scroll';
  function point(event){if(event&&event.touches&&event.touches.length===1)return {x:event.touches[0].clientX,y:event.touches[0].clientY,id:'touch'};if(event&&event.changedTouches&&event.changedTouches.length===1)return {x:event.changedTouches[0].clientX,y:event.changedTouches[0].clientY,id:'touch'};if(event&&typeof event.clientX==='number')return {x:event.clientX,y:event.clientY,id:event.pointerId||'pointer'};return null;}
  function isStrict(target){return !!(target&&target.closest&&target.closest(STRICT));}
  function isContentExclusion(target){return !!(target&&target.closest&&target.closest(CONTENT_EXCLUSION));}
  function routeSurface(target){return target&&target.closest?target.closest(ROUTE_SURFACE):null;}
  function isPassive(target){return !!(target&&target.closest&&target.closest(PASSIVE));}
  function canScrollY(el){return !!(el&&el.scrollHeight>el.clientHeight+2);}
  function nearestScrollOwner(target){
    if(!target||!target.closest)return null;
    let el=target.nodeType===1?target:target.parentElement;
    let fallback=null;
    while(el&&el!==document.body&&el!==document.documentElement){
      if(el.matches&&el.matches(SCROLL_OWNER)){if(!fallback)fallback=el;if(canScrollY(el))return el;}
      el=el.parentElement;
    }
    return fallback;
  }
  function suppressClick(runtime){runtime.routeGestureSuppressClickUntil=Date.now()+560;}
  function prevent(event){if(event&&event.cancelable!==false&&event.preventDefault)event.preventDefault();if(event&&event.stopPropagation)event.stopPropagation();}

  AppRuntime.prototype.installLibraryChapterSwipeNavigation=function(){return false;};
  AppRuntime.prototype.libraryChapterSwipeReport=function(){return {schema:'learnit.rc496.library_chapter_navigation_report.v1',installed:false,nestedChapterSwipe:false,nativeChapterSnap:false,customChapterPointerRuntime:false,chapterNavigation:'list-first',inlineLibraryDetailShell:true,libraryDetailExcludesRouteSwipe:true,modalScrollLock:false,chapterZoneExcludesRouteSwipe:true,inlineDetailShell:true,noChapterPreventDefault:true,noChapterScrollBridge:true};};
  AppRuntime.prototype.gestureOrchestratorReport=function(){return {schema:'learnit.rc672.gesture_orchestrator_report.v1',installed:!!this.gestureOrchestratorInstalled,routeOnlyGestureOrchestrator:true,priority:'strict > content exclusion tap/scroll > native vertical scroll > route > tap',pointerEventsFirst:!!window.PointerEvent,touchFallbackNoPointer:!window.PointerEvent,routeCarouselModel:!!RouteModel,nestedChapterSwipe:false,nativeChapterSnap:false,preventDefaultAfterHorizontalLockOnly:true,scrollOwnershipContract:true,routeSwipeBoundaryContract:true,contentExclusions:true,libraryContentObservable:true,libraryIntentArbitration:true,intentModel:!!IntentModel,intentModelSchema:IntentModel&&IntentModel.schema||''};};
  const previousMobileReport=AppRuntime.prototype.mobileSwipeReport;
  AppRuntime.prototype.mobileSwipeReport=function(){const base=previousMobileReport?previousMobileReport.call(this):{};return Object.assign({},base,{schema:'learnit.rc672.route_carousel_runtime_report.v1',gestureOrchestrator:true,routeOnlyGestureOrchestrator:true,nestedChapterSwipe:false,nativeChapterSnap:false,customChapterPointerRuntime:false,noParallelChapterRuntime:true,chapterStaticShell:true,chapterRouteSwipeExclusion:true,noPreventDefaultInChapterZone:true,noChapterScrollBridge:true,chapterNavigation:'list-first',inlineLibraryDetailShell:true,libraryDetailExcludesRouteSwipe:true,contentZonesExcludeRouteSwipe:false,libraryContentObservable:true,libraryIntentArbitration:true,scrollOwnershipContract:true,routeSwipeBoundaryContract:true,modalScrollLock:false});};

  AppRuntime.prototype.installMobileSwipeNavigation=function(){
    if(this.gestureOrchestratorInstalled)return;
    this.mobileSwipeInstalled=true;this.gestureOrchestratorInstalled=true;this.ensureRouteCarouselState().installed=true;
    let st=null;
    const start=(event,input)=>{
      if(st)return;
      const p=point(event);if(!p)return;
      const owner=nearestScrollOwner(event.target);
      const scrollBias=canScrollY(owner);
      const policy=IntentModel&&IntentModel.startPolicy?IntentModel.startPolicy({session:this.appState.view==='session',drag:!!this.drag,nonPrimary:input==='pointer'&&(event.pointerType==='mouse'||event.isPrimary===false),strict:isStrict(event.target),contentExclusion:isContentExclusion(event.target),routeSurface:!!routeSurface(event.target),scrollBias}):{observe:!(this.drag||this.appState.view==='session'||isStrict(event.target)||isContentExclusion(event.target))&&!!routeSurface(event.target)};
      if(!policy.observe)return;
      st={input,target:event.target,startX:p.x,startY:p.y,lastX:p.x,lastY:p.y,startAt:Date.now(),locked:null,direction:null,passive:isPassive(event.target),scrollOwner:owner,scrollBias,pointerId:p.id,policyReason:policy.reason||''};
      try{this.journal.record('route_gesture_start',{input,passive:st.passive,scrollBias:st.scrollBias,scrollOwner:owner&&owner.className||'',contract:'rc672'});}catch(e){}
    };
    const releaseVertical=(dx,dy)=>{try{this.journal.record('route_gesture_vertical_release',{dx,dy,scrollBias:st&&st.scrollBias,contract:'rc672'});}catch(e){} st=null;};
    const lockHorizontal=(event,classified)=>{st.locked='horizontal';st.direction=classified.direction;this.beginRouteCarouselTransaction(st.direction);prevent(event);if(st.passive)suppressClick(this);};
    const move=(event,input)=>{
      if(!st||st.input!==input)return;
      const p=point(event);if(!p)return;
      if(input==='pointer'&&p.id!==st.pointerId)return;
      st.lastX=p.x;st.lastY=p.y;
      const dx=st.lastX-st.startX,dy=st.lastY-st.startY;
      if(!st.locked){
        const classified=IntentModel&&IntentModel.classify?IntentModel.classify({dx,dy,scrollBias:st.scrollBias}):RouteModel.classify({dx,dy});
        if(classified.kind==='vertical'){releaseVertical(dx,dy);return;}
        if(classified.kind==='horizontal')lockHorizontal(event,classified);
        else return;
      }
      if(st&&st.locked==='horizontal'){
        prevent(event);if(st.passive)suppressClick(this);
        const tx=this.ensureRouteCarouselState().transaction||this.beginRouteCarouselTransaction(st.direction||((dx<0)?'next':'prev'));
        this.renderRouteCarouselDrag(tx,dx);
      }
    };
    const finish=(event,input,cancel)=>{
      if(!st||st.input!==input)return;
      const p=point(event);if(input==='pointer'&&p&&p.id!==st.pointerId)return;
      const cur=st;st=null;
      if(cur.locked!=='horizontal')return;
      prevent(event);if(cur.passive)suppressClick(this);
      this.finishRouteCarouselDrag(!!cancel);
    };
    this.root.addEventListener('click',event=>{const until=this.routeGestureSuppressClickUntil||0;if(until&&Date.now()<until){event.preventDefault();event.stopImmediatePropagation();}},true);
    this.root.addEventListener('click',event=>{const btn=event.target&&event.target.closest&&event.target.closest('.nav [data-nav]');if(!btn||this.appState.view==='session')return;const target=btn.dataset.nav;if(target&&typeof this.routeNavigate==='function'&&this.routeNavigate(target)){event.preventDefault();event.stopPropagation();}},true);
    if(window.PointerEvent){
      this.root.addEventListener('pointerdown',event=>start(event,'pointer'),{passive:true,capture:true});
      document.addEventListener('pointermove',event=>move(event,'pointer'),{passive:false,capture:true});
      document.addEventListener('pointerup',event=>finish(event,'pointer',false),{passive:false,capture:true});
      document.addEventListener('pointercancel',event=>finish(event,'pointer',true),{passive:false,capture:true});
    }else{
      this.root.addEventListener('touchstart',event=>start(event,'touch'),{passive:true,capture:true});
      this.root.addEventListener('touchmove',event=>move(event,'touch'),{passive:false,capture:true});
      this.root.addEventListener('touchend',event=>finish(event,'touch',false),{passive:false,capture:true});
      this.root.addEventListener('touchcancel',event=>finish(event,'touch',true),{passive:false,capture:true});
    }
    const abortGesture=()=>{if(st){if(this.ensureRouteCarouselState().transaction)this.finishRouteCarouselDrag(true);st=null;}};
    window.addEventListener('blur',abortGesture,true);
    document.addEventListener('visibilitychange',()=>{if(document.visibilityState!=='visible')abortGesture();},true);
    try{this.journal.record('gesture_orchestrator_installed',{schema:'learnit.rc672.route_only_orchestrator.v1',nestedChapterSwipe:false,nativeChapterSnap:false});}catch(e){}
  };
  if(window.__LEARNIT_TEST__){window.__LEARNIT_TEST__.gestureOrchestratorReport=()=>window.__LEARNIT_TEST__.runtime.gestureOrchestratorReport();window.__LEARNIT_TEST__.libraryChapterSwipeReport=()=>window.__LEARNIT_TEST__.runtime.libraryChapterSwipeReport();}
})();
