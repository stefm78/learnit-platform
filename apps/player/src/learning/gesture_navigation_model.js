/* RC672 — Pure route gesture intent model.
   The model has no DOM dependency. It classifies one pointer trajectory only;
   nested course/chapter navigation is deliberately out of scope. */
(function(global){
  'use strict';
  const schema='learnit.route_gesture_intent.rc672.v1';
  const DEFAULTS=Object.freeze({
    horizontalPx:16,
    scrollHorizontalPx:20,
    verticalPx:7,
    ratio:1.24,
    scrollRatio:1.34,
    verticalDominance:.92
  });
  function number(value,fallback=0){const n=Number(value);return Number.isFinite(n)?n:fallback;}
  function options(value){return Object.assign({},DEFAULTS,value||{});}
  function classify(input,overrides){
    const opt=options(overrides);const dx=number(input&&input.dx),dy=number(input&&input.dy);const scrollBias=!!(input&&input.scrollBias);const ax=Math.abs(dx),ay=Math.abs(dy);
    if(ax<3&&ay<3)return {kind:'pending',dx,dy,scrollBias};
    if(scrollBias&&ay>=opt.verticalPx&&ay>=ax*opt.verticalDominance)return {kind:'vertical',dx,dy,scrollBias};
    const min=scrollBias?opt.scrollHorizontalPx:opt.horizontalPx;
    const ratio=scrollBias?opt.scrollRatio:opt.ratio;
    if(ax>=min&&ax>ay*ratio)return {kind:'horizontal',direction:dx<0?'next':'prev',dx,dy,scrollBias};
    if(ay>=opt.verticalPx+2&&ay>ax*1.04)return {kind:'vertical',dx,dy,scrollBias};
    return {kind:'pending',dx,dy,scrollBias};
  }
  function startPolicy(input){
    const value=input||{};
    if(value.session)return {observe:false,reason:'session'};
    if(value.drag)return {observe:false,reason:'drag-active'};
    if(value.nonPrimary)return {observe:false,reason:'non-primary'};
    if(value.strict)return {observe:false,reason:'strict-exclusion'};
    if(value.contentExclusion)return {observe:false,reason:'content-exclusion'};
    if(!value.routeSurface)return {observe:false,reason:'outside-route-surface'};
    return {observe:true,reason:value.scrollBias?'scroll-owner-observed':'route-surface-observed'};
  }
  function audit(){
    const vertical=classify({dx:28,dy:155,scrollBias:true});
    const horizontal=classify({dx:-180,dy:-42,scrollBias:true});
    const ambiguous=classify({dx:-14,dy:-11,scrollBias:true});
    const strict=startPolicy({strict:true,routeSurface:true});
    const library=startPolicy({routeSurface:true,scrollBias:true});
    return {schema,ok:vertical.kind==='vertical'&&horizontal.kind==='horizontal'&&horizontal.direction==='next'&&ambiguous.kind==='pending'&&!strict.observe&&library.observe,vertical,horizontal,ambiguous,strict,library};
  }
  const api=Object.freeze({schema,DEFAULTS,classify,startPolicy,audit});
  global.LearnItRouteGestureIntentModel=api;
  /* Compatibility name now points to the same route-only contract. */
  global.LearnItGestureNavigationModel=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
