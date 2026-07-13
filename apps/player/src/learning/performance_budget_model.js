(function(global){
  'use strict';
  const BUDGETS=Object.freeze({
    startupDesktopMs:1200,
    startupMobileMs:1800,
    routeRenderMs:260,
    routeRenderP95Ms:320,
    library100Ms:450,
    library500Ms:1100,
    library1000Ms:1800,
    bilanColdMs:180,
    bilanWarmMs:45,
    storageStateBytes:2_000_000,
    storageImportedBytes:12_000_000,
    storageJournalBytes:500_000,
    activeHtmlBytes:900_000,
    activeJsBytes:700_000,
    activeCssBytes:190_000
  });
  const finite=value=>Number.isFinite(Number(value))?Number(value):0;
  const percentile=(values,p=0.95)=>{
    const sorted=(values||[]).map(finite).filter(v=>v>=0).sort((a,b)=>a-b);
    if(!sorted.length)return 0;
    return sorted[Math.min(sorted.length-1,Math.max(0,Math.ceil(sorted.length*p)-1))];
  };
  const summarize=values=>{
    const rows=(values||[]).map(finite).filter(v=>v>=0);
    const total=rows.reduce((sum,v)=>sum+v,0);
    return Object.freeze({count:rows.length,min:rows.length?Math.min(...rows):0,max:rows.length?Math.max(...rows):0,mean:rows.length?total/rows.length:0,p50:percentile(rows,.5),p95:percentile(rows,.95)});
  };
  const classify=(value,budget)=>Object.freeze({value:finite(value),budget:finite(budget),ok:finite(value)<=finite(budget),ratio:finite(budget)>0?finite(value)/finite(budget):0});
  const byteLength=value=>{
    const text=typeof value==='string'?value:JSON.stringify(value==null?'':value);
    if(typeof TextEncoder!=='undefined')return new TextEncoder().encode(text).length;
    return unescape(encodeURIComponent(text)).length;
  };
  const storageReport=(storage,keys={})=>{
    const read=key=>{try{return key&&storage&&typeof storage.getItem==='function'?(storage.getItem(key)||''):'';}catch(e){return '';}};
    const state=byteLength(read(keys.state));
    const imported=byteLength(read(keys.imported));
    const journal=byteLength(read(keys.journal));
    return Object.freeze({state,imported,journal,total:state+imported+journal,checks:Object.freeze({state:classify(state,BUDGETS.storageStateBytes),imported:classify(imported,BUDGETS.storageImportedBytes),journal:classify(journal,BUDGETS.storageJournalBytes)})});
  };
  const selfTest=()=>{
    const summary=summarize([1,2,3,4,100]);
    const storage={getItem:key=>({s:'abc',i:'é',j:'[]'}[key]||'')};
    const report=storageReport(storage,{state:'s',imported:'i',journal:'j'});
    const checks=[summary.count===5,summary.p95===100,summary.p50===3,classify(10,10).ok,!classify(11,10).ok,report.total>=7];
    return Object.freeze({ok:checks.every(Boolean),checks,summary,report});
  };
  global.LearnItPerformanceBudgetModel=Object.freeze({schema:'learnit.performance_budget_model.rc637.v1',BUDGETS,percentile,summarize,classify,byteLength,storageReport,selfTest});
})(typeof window!=='undefined'?window:globalThis);
