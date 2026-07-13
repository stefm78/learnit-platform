#!/usr/bin/env python3
from __future__ import annotations
import json,shutil,time
from support import ROOT
OUT=ROOT/'reports/browser_endurance_session_report.json'
def main():
 from playwright.sync_api import sync_playwright
 checks=[];errors=[]
 def add(c,o,d=''):checks.append({'code':c,'ok':bool(o),'detail':d})
 html=(ROOT/'dist/learnit.html').read_text(); chromium=shutil.which('chromium') or shutil.which('chromium-browser')
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
  try:
   page=b.new_page(viewport={'width':1280,'height':820});page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(html,wait_until='domcontentloaded');page.wait_for_function('()=>!!window.__LEARNIT_TEST__?.runtime')
   t=time.perf_counter(); result=page.evaluate('''()=>{const api=window.__LEARNIT_TEST__,r=api.runtime;let ok=true;const routes=['learn','library','bilan','tools'];for(let i=0;i<160;i++)r.go(routes[i%4]);r.go('learn');r.session.start();for(let i=0;i<120;i++){r.appState.save();const x=r.appState.load();ok=ok&&x.stateSchemaVersion===4&&x.session&&x.session.status==='active';r.appState.state=x;}for(let i=0;i<100;i++){api.enrichedBilan();api.performanceReport();}const before=JSON.stringify(r.appState.courseProgress(r.appState.activeId()));r.appState.save();const after=JSON.stringify(r.appState.load().activityProgressByCourseId[r.appState.activeId()]||{});return {ok,route:(document.querySelector('[data-route-carousel]')||{}).dataset?.activeRoute||'',state:r.appState.state.stateSchemaVersion,session:r.appState.state.session.status,before,after,perf:api.performanceReport(),coverage:api.learningCoverage(),retention:api.retentionProtocol()};}'''); elapsed=(time.perf_counter()-t)*1000
   add('endurance-state-stable',result['ok'] and result['state']==4 and result['session']=='active',result)
   add('endurance-route-stable',result['route']=='learn',result['route'])
   add('endurance-progress-roundtrip',result['before']==result['after'],f"{result['before']} / {result['after']}")
   add('learning-evidence-apis-stable',bool(result.get('coverage',{}).get('schema')) and bool(result.get('retention',{}).get('schema')),result)
   add('endurance-budget',elapsed<12000,f'{elapsed:.1f}ms')
   add('no-browser-errors',not errors,' | '.join(errors[-10:]))
  finally:b.close()
 ok=all(x['ok'] for x in checks);OUT.write_text(json.dumps({'schema':'learnit.rc708.endurance_session.v1','ok':ok,'elapsedMs':elapsed,'checks':checks,'errors':errors},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':ok,'passed':sum(x['ok'] for x in checks),'total':len(checks),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
