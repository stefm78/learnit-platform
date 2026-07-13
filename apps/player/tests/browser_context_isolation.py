#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'/'browser_context_isolation_report.json'

def main()->int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
            page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content((ROOT/'dist/learnit.html').read_text(encoding='utf-8'),wait_until='domcontentloaded')
            page.wait_for_timeout(400)
            result=page.evaluate("""async()=>{
              const r=window.__LEARNIT_TEST__.runtime;
              const wait=()=>new Promise(ok=>setTimeout(ok,20));
              const snapshot=()=>({course:r.contentStore.activeCourseId,activity:r.session.currentActivity()?.id,type:r.session.currentActivity()?.type,pending:JSON.parse(JSON.stringify(r.answer.pending)),feedback:r.answer.feedback,selectedFillIndex:r.answer.selectedFillIndex,selectedOrderToken:r.answer.selectedOrderToken});
              const ids=r.contentStore.courseList().map(c=>c.courseId).filter(Boolean);
              const out={ids,steps:[]};
              r.session.start();r.answer.reset();r.go('session');await wait();
              const a=r.session.currentActivity();
              if(a?.type==='qcm')r.answer.selectQcm(0);
              else if(a?.type==='fill')r.answer.fillToken((a.tokens||[])[0]);
              else if(a?.type==='matching')r.answer.selectMatchLeft((a.pairs||[])[0]?.[0]);
              else if(a?.type==='order')r.answer.selectedOrderToken=(a.tokens||[])[0]||null;
              else if(a?.type==='flashcard')r.answer.revealFlashcard();
              out.steps.push({name:'mutated-a',...snapshot()});
              if(ids.length>1){r.contentStore.setActiveCourse(ids[1]);r.appState.alignWithContent();r.answer.reset();r.session.start();r.answer.reset();await wait();}
              out.steps.push({name:'course-b-clean',...snapshot()});
              if(ids.length>1){r.contentStore.setActiveCourse(ids[0]);r.appState.alignWithContent();r.answer.reset();r.session.start();r.answer.reset();await wait();}
              out.steps.push({name:'course-a-reentry-clean',...snapshot()});
              r.answer.feedback={correct:false};r.answer.selectedFillIndex=2;r.answer.selectedOrderToken='x';r.answer.retry();await wait();
              out.steps.push({name:'retry-clean',...snapshot()});
              r.session.quit();r.answer.reset();r.session.resume();r.answer.reset();await wait();
              out.steps.push({name:'quit-resume-clean',...snapshot()});
              return out;
            }""")
            def clean(step):
                return step.get('feedback') is None and step.get('selectedFillIndex') is None and step.get('selectedOrderToken') is None
            clean_steps=[s for s in result['steps'] if s['name']!='mutated-a']
            add('multiple-courses-available',len(result['ids'])>=2,str(result['ids']))
            add('course-switch-clears-transients',clean(result['steps'][1]),json.dumps(result['steps'][1],ensure_ascii=False))
            add('course-reentry-clears-transients',clean(result['steps'][2]),json.dumps(result['steps'][2],ensure_ascii=False))
            add('retry-uses-canonical-clean-state',clean(result['steps'][3]),json.dumps(result['steps'][3],ensure_ascii=False))
            add('quit-resume-clears-transients',clean(result['steps'][4]),json.dumps(result['steps'][4],ensure_ascii=False))
            add('no-browser-errors',not errors,' | '.join(errors[-10:]))
        finally: browser.close()
    ok=all(r['ok'] for r in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps({'schema':'learnit.context_isolation.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'ok':ok,'passed':sum(r['ok'] for r in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
