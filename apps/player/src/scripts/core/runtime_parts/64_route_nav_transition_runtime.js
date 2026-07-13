/* RC467 — Route Nav Transition Runtime.
   Passive top-nav visualization for the Route Carousel transaction. This module
   deliberately does not change appState or render route bodies. */
(function(){
  'use strict';
  const NAV_TRANSITION_SCHEMA='rc467';
  function clamp01(value){value=Number(value);if(!Number.isFinite(value))return 0;return Math.max(0,Math.min(1,value));}
  function progressText(value){return String(Math.round(clamp01(value)*1000)/1000);}
  AppRuntime.prototype.routeNavButtons=function(){
    return this.root&&this.root.querySelectorAll?Array.from(this.root.querySelectorAll('.nav [data-nav]')):[];
  };
  AppRuntime.prototype.setRouteNavTransition=function(options){
    if(!this.root||!this.root.querySelector)return;
    const nav=this.root.querySelector('.nav');
    if(!nav)return;
    const currentRoute=(options&&options.currentRoute)||this.appState.view;
    const targetRoute=(options&&options.targetRoute)||currentRoute;
    const phase=(options&&options.phase)||'idle';
    const boundary=!!(options&&options.boundary);
    const progress=clamp01(options&&options.progress);
    nav.dataset.routeNavTransition=NAV_TRANSITION_SCHEMA;
    nav.dataset.routeNavPhase=phase;
    nav.dataset.routeNavCurrent=currentRoute||'';
    nav.dataset.routeNavTarget=targetRoute||'';
    nav.style.setProperty('--route-nav-progress',progressText(progress));
    this.routeNavButtons().forEach(btn=>{
      const route=btn.dataset.nav;
      const isCurrent=route===currentRoute;
      const isTarget=route===targetRoute&&targetRoute!==currentRoute&&!boundary;
      const isBoundary=isCurrent&&boundary;
      let role='idle';
      let local=0;
      if(isBoundary){role='boundary';local=progress;}
      else if(isTarget){role='to';local=progress;}
      else if(isCurrent&&targetRoute!==currentRoute){role='from';local=1-progress;}
      btn.dataset.routeTransitionRole=role;
      btn.dataset.routeTransitionPhase=phase;
      btn.style.setProperty('--route-nav-progress',progressText(local));
      btn.style.setProperty('--route-nav-strength',progressText(role==='idle'?0:Math.max(.08,local)));
    });
  };
  AppRuntime.prototype.clearRouteNavTransition=function(){
    if(!this.root||!this.root.querySelector)return;
    const nav=this.root.querySelector('.nav');
    if(nav){
      delete nav.dataset.routeNavTransition;
      delete nav.dataset.routeNavPhase;
      delete nav.dataset.routeNavCurrent;
      delete nav.dataset.routeNavTarget;
      nav.style.removeProperty('--route-nav-progress');
    }
    this.routeNavButtons().forEach(btn=>{
      delete btn.dataset.routeTransitionRole;
      delete btn.dataset.routeTransitionPhase;
      btn.style.removeProperty('--route-nav-progress');
      btn.style.removeProperty('--route-nav-strength');
    });
  };
})();
