#!/usr/bin/env python3
from __future__ import annotations
import json,shutil
from support import ROOT
OUT=ROOT/'reports/browser_interruption_resilience_report.json'
def main():
 from playwright.sync_api import sync_playwright
 checks=[];errors=[]
 def add(c,o,d=''):checks.append({'code':c,'ok':bool(o),'detail':d})
 html=(ROOT/'dist/learnit.html').read_text(); chromium=shutil.which('chromium') or shutil.which('chromium-browser')
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
  try:
   page=b.new_page(viewport={'width':390,'height':844});page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(html,wait_until='domcontentloaded');page.wait_for_function('()=>!!window.__LEARNIT_TEST__?.runtime')
   result=page.evaluate('''()=>{const api=window.__LEARNIT_TEST__,r=api.runtime;r.go('learn');r.session.start();api.checkpoint('rc710-before-interruption');window.dispatchEvent(new Event('blur'));document.dispatchEvent(new Event('visibilitychange'));window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));r.appState.save();const loaded=r.appState.load();r.appState.state=loaded;const retention=window.LearnItRetentionProtocolModel.schedule(r.appState.activeId(),'2026-01-01T00:00:00Z',['o'],['t']);r.appState.setCourseRetention(retention);r.appState.save();const restored=r.appState.load();return {schema:restored.stateSchemaVersion,status:restored.session.status,checkpoint:api.resilienceReport().checkpoint,retention:restored.retentionByCourseId[r.appState.activeId()],gesture:api.mobileSwipeReport(),storage:api.storageReport()};}''')
   add('interrupted-state-restored',result['schema']==4 and result['status']=='active',result)
   add('checkpoint-recorded',result.get('checkpoint',{}).get('reason') in {'pagehide','visibilitychange','rc710-before-interruption','blur'},result.get('checkpoint'))
   add('retention-protocol-restored',result.get('retention',{}).get('schema')=='learnit.retention_protocol_model.rc701.v1',result.get('retention'))
   add('gesture-runtime-healthy',bool(result.get('gesture',{}).get('installed')),result.get('gesture'))
   add('storage-observable',bool(result.get('storage',{}).get('schema')),result.get('storage'))
   add('no-browser-errors',not errors,' | '.join(errors[-10:]))
  finally:b.close()
 ok=all(x['ok'] for x in checks);OUT.write_text(json.dumps({'schema':'learnit.rc710.interruption_resilience.v1','ok':ok,'checks':checks,'errors':errors},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':ok,'passed':sum(x['ok'] for x in checks),'total':len(checks),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
