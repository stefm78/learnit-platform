/* RC450 — Pure Route Carousel model.
   Four top-level routes are addressed by one immutable order. The model has no DOM
   dependency: it only decides target indices, drag frames, commit/cancel, and
   rubber-band boundary resistance. */
(function(global){
  'use strict';
  const ROUTES=Object.freeze(['learn','library','bilan','tools']);
  const DEFAULTS=Object.freeze({
    minWidth:240,
    lockDistance:14,
    verticalDistance:8,
    axisRatio:1.25,
    commitRatio:0.27,
    velocityCommit:0.55,
    rubberDamping:0.30,
    maxRubberRatio:0.16
  });
  function number(value,fallback){const n=Number(value);return Number.isFinite(n)?n:fallback;}
  function clamp(value,min,max){return Math.min(Math.max(value,min),max);}
  function width(value){return Math.max(DEFAULTS.minWidth,number(value,DEFAULTS.minWidth));}
  function indexOf(route){const i=ROUTES.indexOf(route);return i<0?0:i;}
  function routeAt(index){return ROUTES[clamp(Math.round(number(index,0)),0,ROUTES.length-1)];}
  function directionFromDx(dx){return number(dx,0)<0?'next':'prev';}
  function directionBetween(fromIndex,toIndex){return number(toIndex,0)>=number(fromIndex,0)?'next':'prev';}
  function targetIndex(currentIndex,direction){
    const current=clamp(Math.round(number(currentIndex,0)),0,ROUTES.length-1);
    const delta=direction==='next'?1:-1;
    const target=current+delta;
    if(target<0||target>=ROUTES.length)return {kind:'boundary',currentIndex:current,targetIndex:current,direction};
    return {kind:'move',currentIndex:current,targetIndex:target,direction,targetRoute:ROUTES[target]};
  }
  function classify(input,options){
    const opt=Object.assign({},DEFAULTS,options||{});
    const dx=number(input&&input.dx,0),dy=number(input&&input.dy,0);
    const ax=Math.abs(dx),ay=Math.abs(dy);
    if(ax<opt.lockDistance&&ay<opt.verticalDistance)return {kind:'pending',dx,dy};
    if(ay>=opt.verticalDistance&&ay>=ax)return {kind:'vertical',dx,dy};
    if(ax>=opt.lockDistance&&ax>ay*opt.axisRatio)return {kind:'horizontal',dx,dy,direction:directionFromDx(dx)};
    return {kind:'pending',dx,dy};
  }
  function rubber(dx,w,options){
    const opt=Object.assign({},DEFAULTS,options||{});
    const ww=width(w);
    return clamp(number(dx,0)*opt.rubberDamping,-ww*opt.maxRubberRatio,ww*opt.maxRubberRatio);
  }
  function frame(input,options){
    const currentIndex=clamp(Math.round(number(input&&input.currentIndex,0)),0,ROUTES.length-1);
    const w=width(input&&input.width);
    const dx=number(input&&input.dx,0);
    const direction=input&&input.direction||directionFromDx(dx);
    const decision=input&&input.decision||targetIndex(currentIndex,direction);
    const baseX=-currentIndex*w;
    if(decision.kind==='boundary'){
      const outward=direction==='next'?Math.min(0,dx):Math.max(0,dx);
      const trackX=baseX+rubber(outward,w,options);
      return {kind:'boundary',direction,currentIndex,targetIndex:currentIndex,width:w,baseX,trackX,progress:Math.abs(trackX-baseX)/w};
    }
    const forward=direction==='next'?Math.min(0,dx):Math.max(0,dx);
    const limited=clamp(forward,-w,w);
    const trackX=baseX+limited;
    return {kind:'move',direction,currentIndex,targetIndex:decision.targetIndex,width:w,baseX,trackX,progress:Math.min(1,Math.abs(limited)/w)};
  }
  function shouldCommit(input,options){
    const opt=Object.assign({},DEFAULTS,options||{});
    const w=width(input&&input.width);
    const dx=number(input&&input.dx,0);
    const direction=input&&input.direction||directionFromDx(dx);
    const decision=input&&input.decision;
    const forward=direction==='next'?Math.max(0,-dx):Math.max(0,dx);
    const elapsed=Math.max(1,number(input&&input.elapsedMs,1));
    const velocity=forward/elapsed;
    const progress=forward/w;
    if(decision&&decision.kind==='boundary')return {commit:false,reason:'boundary',progress,velocity,direction};
    if(forward<=0)return {commit:false,reason:'reversed',progress,velocity,direction};
    if(progress>=opt.commitRatio)return {commit:true,reason:'distance',progress,velocity,direction};
    if(progress>=0.12&&velocity>=opt.velocityCommit)return {commit:true,reason:'velocity',progress,velocity,direction};
    return {commit:false,reason:'insufficient',progress,velocity,direction};
  }
  function snap(input){
    const currentIndex=clamp(Math.round(number(input&&input.currentIndex,0)),0,ROUTES.length-1);
    const target=clamp(Math.round(number(input&&input.targetIndex,currentIndex)),0,ROUTES.length-1);
    const w=width(input&&input.width);
    const commit=!!(input&&input.commit);
    return {kind:'snap',commit,currentIndex,targetIndex:commit?target:currentIndex,width:w,trackX:-(commit?target:currentIndex)*w};
  }
  function navTarget(fromRoute,toRoute){
    const currentIndex=indexOf(fromRoute);
    const target=indexOf(toRoute);
    if(currentIndex===target)return {kind:'same',currentIndex,targetIndex:target,currentRoute:ROUTES[currentIndex],targetRoute:ROUTES[target],direction:'none'};
    return {kind:'move',currentIndex,targetIndex:target,currentRoute:ROUTES[currentIndex],targetRoute:ROUTES[target],direction:directionBetween(currentIndex,target)};
  }
  const api=Object.freeze({schema:'learnit.rc450.route_carousel_model.v1',ROUTES,DEFAULTS,indexOf,routeAt,directionFromDx,directionBetween,targetIndex,classify,rubber,frame,shouldCommit,snap,navTarget});
  global.LearnItRouteCarouselModel=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
