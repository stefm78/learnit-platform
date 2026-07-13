#!/usr/bin/env python3
from __future__ import annotations
import json,shutil,time
from support import ROOT
OUT=ROOT/'reports/browser_realistic_device_performance_report.json'
def main():
 from playwright.sync_api import sync_playwright
 checks=[];errors=[]
 def add(c,o,d=''):checks.append({'code':c,'ok':bool(o),'detail':d})
 html=(ROOT/'dist/learnit.html').read_text(); chromium=shutil.which('chromium') or shutil.which('chromium-browser')
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
  try:
   for label,viewport in [('desktop',{'width':1366,'height':768}),('android-mid',{'width':390,'height':844})]:
    page=b.new_page(viewport=viewport);local=[];page.on('pageerror',lambda e,bag=local:bag.append(str(e)));t=time.perf_counter();page.set_content(html,wait_until='domcontentloaded');page.wait_for_function('()=>!!window.__LEARNIT_TEST__?.runtime');boot=(time.perf_counter()-t)*1000
    result=page.evaluate('''()=>{const r=window.__LEARNIT_TEST__.runtime,values=[];for(let c=0;c<15;c++)for(const route of ['learn','library','bilan','tools']){const t=performance.now();r.go(route);values.push(performance.now()-t);}values.sort((a,b)=>a-b);return {p95:values[Math.floor(values.length*.95)-1],max:values[values.length-1],perf:window.__LEARNIT_TEST__.performanceReport()};}''')
    add(label+'-boot-budget',boot<2500,f'{boot:.1f}ms');add(label+'-route-p95',result['p95']<160,f"p95={result['p95']:.1f} max={result['max']:.1f}");add(label+'-reported-budgets',all(x.get('ok') for x in result['perf'].get('checks',{}).values()),result['perf'].get('checks',{}));add(label+'-no-errors',not local,' | '.join(local));errors+=local;page.close()
  finally:b.close()
 ok=all(x['ok'] for x in checks);OUT.write_text(json.dumps({'schema':'learnit.rc709.realistic_device_performance.v1','ok':ok,'checks':checks,'errors':errors},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':ok,'passed':sum(x['ok'] for x in checks),'total':len(checks),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
