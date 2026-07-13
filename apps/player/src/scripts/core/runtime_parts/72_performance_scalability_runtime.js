/* RC624-RC632 — stable performance instrumentation, projection cache and scale evidence.
   No visual feature, no gesture, no content mutation. */
(function(){
  'use strict';
  const Model=window.LearnItPerformanceBudgetModel;
  if(!Model||typeof AppRuntime!=='function')return;
  const samples={boot:[],render:[],route:Object.create(null),library:[],bilan:[],storage:[]};
  const cacheByRuntime=new WeakMap();
  let dataRevision=1;
  const now=()=>performance&&typeof performance.now==='function'?performance.now():Date.now();
  const push=(list,value,limit=80)=>{list.push(Math.max(0,Number(value)||0));if(list.length>limit)list.splice(0,list.length-limit);};
  const bump=()=>{dataRevision+=1;return dataRevision;};
  const cache=runtime=>{let value=cacheByRuntime.get(runtime);if(!value){value={revision:0,libraryKey:'',library:null,bilanKey:'',bilan:null,hits:{library:0,bilan:0},misses:{library:0,bilan:0}};cacheByRuntime.set(runtime,value);}return value;};
  const originalSave=AppState.prototype.save;
  AppState.prototype.save=function(){const result=originalSave.apply(this,arguments);bump();return result;};
  const originalLoadContent=ContentStore.prototype.load;
  ContentStore.prototype.load=function(){const result=originalLoadContent.apply(this,arguments);bump();return result;};
  const originalLibraryProjection=buildLibraryProjection;
  buildLibraryProjection=function(runtime){
    const c=cache(runtime);const key=`${dataRevision}|${runtime.contentStore.activeCourseId}|${runtime.contentStore.allCourses().length}`;
    if(c.library&&c.libraryKey===key){c.hits.library+=1;return c.library;}
    const started=now();const result=originalLibraryProjection(runtime);push(samples.library,now()-started);c.libraryKey=key;c.library=result;c.revision=dataRevision;c.misses.library+=1;return result;
  };
  const originalBilanProjection=buildBilanProjection;
  buildBilanProjection=function(runtime){
    const session=runtime.appState&&runtime.appState.state&&runtime.appState.state.session||{};
    const key=`${dataRevision}|${runtime.contentStore.activeCourseId}|${session.status||''}|${session.currentIndex||0}`;
    const c=cache(runtime);
    if(c.bilan&&c.bilanKey===key){c.hits.bilan+=1;return c.bilan;}
    const started=now();const result=originalBilanProjection(runtime);push(samples.bilan,now()-started);c.bilanKey=key;c.bilan=result;c.revision=dataRevision;c.misses.bilan+=1;return result;
  };
  const originalRender=AppRuntime.prototype.render;
  AppRuntime.prototype.render=function(){
    const view=this.appState&&this.appState.view||'unknown';const started=now();const result=originalRender.apply(this,arguments);const duration=now()-started;
    push(samples.render,duration);if(!samples.route[view])samples.route[view]=[];push(samples.route[view],duration);
    return result;
  };
  const originalBoot=AppRuntime.prototype.boot;
  AppRuntime.prototype.boot=function(){const started=now();const result=originalBoot.apply(this,arguments);push(samples.boot,now()-started);return result;};
  function storageMetrics(){
    const report=Model.storageReport(storage,{state:STORAGE_KEY,imported:IMPORTED_COURSES_KEY,journal:JOURNAL_KEY});push(samples.storage,report.total);return report;
  }
  function report(runtime){
    const route={};for(const [name,values] of Object.entries(samples.route))route[name]=Model.summarize(values);
    const c=cache(runtime);const storageReport=storageMetrics();const render=Model.summarize(samples.render);const boot=Model.summarize(samples.boot);
    const budgets=Model.BUDGETS;const nonLibrary=[];for(const [name,values] of Object.entries(samples.route))if(name!=='library')nonLibrary.push(...values);
    const standardRender=Model.summarize(nonLibrary);const libraryRender=Model.summarize(samples.route.library||[]);const courseCount=runtime.contentStore.allCourses().length;
    const libraryBudget=courseCount>500?budgets.library1000Ms:(courseCount>100?budgets.library500Ms:budgets.library100Ms);
    const checks={boot:Model.classify(boot.max,budgets.startupMobileMs),renderP95:Model.classify(standardRender.p95,budgets.routeRenderP95Ms),libraryRender:Model.classify(libraryRender.p95,libraryBudget),storageState:storageReport.checks.state,storageImported:storageReport.checks.imported,storageJournal:storageReport.checks.journal};
    return Object.freeze({schema:'learnit.performance_scalability_report.rc637.v1',version:VERSION_LABEL,build:APP_BUILD,budgets,boot,render,standardRender,libraryRender,courseCount,route,projection:Object.freeze({library:Model.summarize(samples.library),bilan:Model.summarize(samples.bilan),cache:Object.freeze({hits:{...c.hits},misses:{...c.misses},revision:dataRevision})}),storage:storageReport,checks,ok:Object.values(checks).every(item=>item.ok)});
  }
  AppRuntime.prototype.performanceReport=function(){return report(this);};
  AppRuntime.prototype.invalidateProjectionCache=function(){bump();const c=cache(this);c.library=null;c.bilan=null;c.libraryKey='';c.bilanKey='';return dataRevision;};
  window.LearnItPerformanceRuntime=Object.freeze({schema:'learnit.performance_scalability_runtime.rc637.v1',report:()=>window.__LEARNIT_TEST__&&window.__LEARNIT_TEST__.runtime?report(window.__LEARNIT_TEST__.runtime):null,invalidate:bump});
  queueMicrotask(()=>{if(window.__LEARNIT_TEST__){window.__LEARNIT_TEST__.performanceReport=()=>report(window.__LEARNIT_TEST__.runtime);window.__LEARNIT_TEST__.invalidateProjectionCache=()=>window.__LEARNIT_TEST__.runtime.invalidateProjectionCache();window.__LEARNIT_TEST__.performanceModel=()=>({schema:Model.schema,budgets:Model.BUDGETS,selfTest:Model.selfTest()});}});
})();
