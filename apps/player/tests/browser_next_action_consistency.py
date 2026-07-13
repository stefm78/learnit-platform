#!/usr/bin/env python3
from __future__ import annotations
import json, shutil, sys
from support import ROOT
OUT=ROOT/'reports/browser_next_action_consistency_report.json'
rows=[];errors=[]
def add(code,ok,detail=''):rows.append({'code':code,'ok':bool(ok),'detail':detail})

def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps({'schema':'learnit.rc696.browser_next_action_consistency.v1','ok':False,'error':str(exc)},indent=2)+'\n');return 1
    html=(ROOT/'dist/learnit.html').read_text(encoding='utf-8')
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':1365,'height':900})
            page.set_default_timeout(7000)
            page.on('pageerror',lambda exc:errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg:errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content(html,wait_until='domcontentloaded');page.wait_for_timeout(450)
            learn=page.locator('.route-panel[data-route="learn"] [data-entry-guidance]')
            fresh_code=learn.get_attribute('data-recommendation-code')
            add('fresh-learn-code',fresh_code=='no-evidence-yet',fresh_code)
            page.locator('nav.nav button[data-nav="bilan"]').click();page.wait_for_timeout(250)
            bilan=page.locator('.route-panel[data-route="bilan"] [data-recommendation-code]')
            add('fresh-bilan-same-code',bilan.get_attribute('data-recommendation-code')==fresh_code,bilan.get_attribute('data-recommendation-code'))
            add('bilan-one-primary-one-secondary',bilan.get_attribute('data-primary-action-count')=='1' and int(bilan.get_attribute('data-secondary-action-count') or 0)<=1,bilan.get_attribute('data-secondary-action-count'))

            # Inject a completed mixed diagnostic with objective-level evidence.
            payload=page.evaluate('''() => {
              const r=window.__LEARNIT_TEST__.runtime;const acts=r.contentStore.content.activities.filter(a=>a.type!=='flashcard').slice(0,3);
              const norm=s=>String(s||'Objectif').trim().toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'objectif';
              const strong=acts[0],weak=acts[1]||acts[0];const strongKey=norm(strong.objective||strong.question),weakKey=norm(weak.objective||weak.question);
              const last={mode:'diagnostic',modePolicy:window.LearnItSessionModeModel.resolve('diagnostic'),done:2,total:2,correct:1,review:[weak.id],completedAt:new Date().toISOString(),contentVersion:r.contentStore.content.contentVersion,
                assessmentEvidence:[{id:strong.id,objective:strong.objective||strong.question,objectiveKey:strongKey,correct:true,role:strong.assessment_role||'',type:strong.type},{id:weak.id,objective:weak.objective||weak.question,objectiveKey:weakKey,correct:false,role:weak.assessment_role||'',type:weak.type}],
                objectiveAssessment:[{key:strongKey,label:strong.objective||strong.question,total:1,correct:1,incorrect:0,status:'strong'},{key:weakKey,label:weak.objective||weak.question,total:1,correct:0,incorrect:1,status:'fragile'}]};
              last.modeOutcome=window.LearnItSessionModeModel.outcome(last);r.appState.state.lastBilan=last;r.appState.state.lastBilanByCourseId[r.contentStore.activeCourseId]=last;r.appState.state.session=r.appState.initialSession();r.appState.state.session.status='idle';r.appState.save();r.go('learn');r.render();return {strongId:strong.id,weakId:weak.id,strongKey,weakKey};
            }''')
            page.wait_for_timeout(250)
            learn=page.locator('.route-panel[data-route="learn"] [data-entry-guidance]')
            mixed_code=learn.get_attribute('data-recommendation-code')
            add('diagnostic-mixed-learn',mixed_code=='diagnostic-mixed' and 'Travailler les points ciblés' in (learn.text_content() or ''),learn.text_content() or '')
            page.locator('nav.nav button[data-nav="bilan"]').click();page.wait_for_timeout(250)
            bilan=page.locator('.route-panel[data-route="bilan"] [data-recommendation-code]')
            add('diagnostic-mixed-bilan-same',bilan.get_attribute('data-recommendation-code')==mixed_code,bilan.get_attribute('data-recommendation-code'))
            outcome=page.locator('.route-panel[data-route="bilan"] .bilan-mode-outcome')
            add('diagnostic-debrief-objectives',outcome.count()==1 and outcome.locator('.assessment-debrief-row').count()>=2,outcome.text_content() or '')
            # Primary canonical action starts an adaptive training plan with weak objective first.
            page.locator('.route-panel[data-route="bilan"] .bilan-action-hero button.primary').click();page.wait_for_timeout(250)
            state=page.evaluate('''() => {const s=window.__LEARNIT_TEST__.runtime.session.session;return {view:window.__LEARNIT_TEST__.runtime.appState.view,mode:s.mode,adaptive:!!(s.modePlan&&s.modePlan.adaptive),source:s.modePlan&&s.modePlan.adaptiveSource,queue:s.queue};}''')
            add('diagnostic-primary-starts-adaptive-training',state['view']=='session' and state['mode']=='training' and state['adaptive'] and state['source']=='diagnostic-mixed',state)
            add('diagnostic-weak-objective-prioritized',payload['weakId'] in state['queue'][:2],{'payload':payload,'queue':state['queue'][:4]})
            page.close()
        finally:
            browser.close()
    add('no-browser-errors',not errors,' | '.join(errors[-10:]))
    ok=all(r['ok'] for r in rows)
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps({'schema':'learnit.rc696.browser_next_action_consistency.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(r['ok'] for r in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
