#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil, time, sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'/'browser_performance_scale_report.json'

def courses(count:int)->list[dict]:
    rows=[]
    for i in range(count):
        objective=f'Objectif {i}'
        rows.append({'schemaVersion':'learnit-content-v2','contentVersion':f'perf-{i}','title':f'Parcours performance {i:04d}','sequence':f'Collection performance {i//50:02d}','objectives':[objective],'activities':[{'id':f'perf-{i}-q','type':'qcm','objective':objective,'question':f'Question {i} ?','choices':['Correct','Incorrect'],'answer':0,'why':'Réponse attendue.','remediation':'Revoir la règle.','difficulty':'easy','learning_phase':'validation','assessment_role':'validation','common_errors':['Choisir le distracteur.']} ]})
    return rows

def main()->int:
    from playwright.sync_api import sync_playwright
    rows=[];errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':str(detail)})
    html=(ROOT/'dist/learnit.html').read_text(encoding='utf-8')
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            for label,viewport,boot_budget in [('desktop',{'width':1440,'height':900},1200),('mobile',{'width':390,'height':844},1800)]:
                page=browser.new_page(viewport=viewport)
                local_errors=[]
                page.on('pageerror',lambda exc,bag=local_errors:bag.append(f'pageerror:{exc}'))
                page.on('console',lambda msg,bag=local_errors:bag.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
                wall=time.perf_counter();page.set_content(html,wait_until='domcontentloaded');page.wait_for_function('()=>!!window.__LEARNIT_TEST__?.performanceReport');wall_ms=(time.perf_counter()-wall)*1000
                report=page.evaluate('window.__LEARNIT_TEST__.performanceReport()')
                boot=float(report.get('boot',{}).get('max',999999))
                add(f'{label}-startup-budget',boot<=boot_budget,f'boot={boot:.1f}ms wall={wall_ms:.1f}ms budget={boot_budget}')
                route=page.evaluate("""()=>{const r=window.__LEARNIT_TEST__.runtime;const values=[];for(let cycle=0;cycle<4;cycle++)for(const name of ['learn','library','bilan','tools']){const t=performance.now();r.go(name);values.push({name,ms:performance.now()-t});}return values;}""")
                p95=sorted(float(x['ms']) for x in route)[max(0,int(len(route)*.95)-1)]
                add(f'{label}-warm-route-p95',p95<=120,f'p95={p95:.1f}ms max={max(float(x["ms"]) for x in route):.1f}ms')
                before=page.evaluate('window.__LEARNIT_TEST__.performanceReport().projection.cache')
                timings=page.evaluate("""()=>{const api=window.__LEARNIT_TEST__;api.invalidateProjectionCache();const a=performance.now();api.enrichedBilan();const cold=performance.now()-a;const b=performance.now();api.enrichedBilan();const warm=performance.now()-b;return {cold,warm,cache:api.performanceReport().projection.cache};}""")
                add(f'{label}-bilan-cold-budget',timings['cold']<=180,json.dumps(timings,ensure_ascii=False))
                add(f'{label}-bilan-warm-cache',timings['warm']<=45 and timings['cache']['hits']['bilan']>=before.get('hits',{}).get('bilan',0)+1,json.dumps(timings,ensure_ascii=False))
                resume=page.evaluate("""()=>{const r=window.__LEARNIT_TEST__.runtime;r.session.start();r.answer.reset();let ok=true;for(let i=0;i<20;i++){r.appState.save();const loaded=r.appState.load();ok=ok&&loaded.stateSchemaVersion===4&&loaded.session&&loaded.session.status==='active';r.appState.state=loaded;}return {ok,status:r.appState.state.session.status,cycles:20,storage:window.__LEARNIT_TEST__.performanceReport().storage};}""")
                add(f'{label}-twenty-resume-cycles',resume['ok'] and resume['status']=='active',json.dumps(resume,ensure_ascii=False))
                add(f'{label}-storage-budgets',all(v.get('ok') for v in resume['storage']['checks'].values()),json.dumps(resume['storage'],ensure_ascii=False))
                add(f'{label}-no-errors',not local_errors,' | '.join(local_errors[-10:]))
                errors.extend(local_errors);page.close()

            page=browser.new_page(viewport={'width':1440,'height':900});scale_errors=[]
            page.on('pageerror',lambda exc:scale_errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg:scale_errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content(html,wait_until='domcontentloaded');page.wait_for_function('()=>!!window.__LEARNIT_TEST__?.runtime')
            all_courses=courses(1000)
            for count,budget in [(100,450),(500,1100),(1000,1800)]:
                result=page.evaluate("""({rows,count})=>{const r=window.__LEARNIT_TEST__.runtime;r.contentStore.imported=rows.slice(0,count);r.contentStore.saveImportedCourses();r.contentStore.load();r.appState.alignWithContent();r.libraryFilter='all';r.libraryQuery='';r.libraryOverlayCourseId=null;r.invalidateProjectionCache();const t=performance.now();r.go('library');const ms=performance.now()-t;return {ms,total:r.contentStore.allCourses().length,rows:r.root.querySelectorAll('[data-course-row]').length,report:window.__LEARNIT_TEST__.performanceReport()};}""",{'rows':all_courses,'count':count})
                expected=count+3
                add(f'library-{count}-scale',result['total']>=expected and result['rows']>=count,f'total={result["total"]} rows={result["rows"]} ms={result["ms"]:.1f}')
                add(f'library-{count}-render-budget',result['ms']<=budget,f'{result["ms"]:.1f}ms <= {budget}ms')
            search=page.evaluate("""()=>{const r=window.__LEARNIT_TEST__.runtime;r.libraryQuery='Parcours performance 0999';const t=performance.now();r.render();return {ms:performance.now()-t,rows:r.root.querySelectorAll('[data-course-row]').length,text:r.root.innerText};}""")
            add('library-1000-search',search['rows']==1 and '0999' in search['text'],json.dumps({k:search[k] for k in ['ms','rows']},ensure_ascii=False))
            add('library-1000-search-budget',search['ms']<=500,f'{search["ms"]:.1f}ms')
            perf=page.evaluate('window.__LEARNIT_TEST__.performanceReport()')
            add('runtime-performance-report-ok',perf.get('ok') is True,json.dumps(perf.get('checks',{}),ensure_ascii=False))
            add('scale-no-errors',not scale_errors,' | '.join(scale_errors[-10:]));errors.extend(scale_errors);page.close()
        finally: browser.close()
    ok=all(x['ok'] for x in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps({'schema':'learnit.rc659.browser_performance_scale.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(x['ok'] for x in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2));return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
