#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil, sys
from support import ROOT

OUT=ROOT/'reports/browser_entry_guidance_report.json'
rows=[]; errors=[]
def add(code,ok,detail=''):
    rows.append({'code':code,'ok':bool(ok),'detail':detail})

def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps({'schema':'learnit.rc659.browser_entry_guidance.v1','ok':False,'error':str(exc)},indent=2)+'\n'); return 1
    html=(ROOT/'dist/learnit.html').read_text(encoding='utf-8')
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            for profile,viewport in [('mobile',{'width':390,'height':844}),('desktop',{'width':1440,'height':1000})]:
                page=browser.new_page(viewport=viewport,is_mobile=profile=='mobile',has_touch=profile=='mobile')
                page.set_default_timeout(7000)
                page.on('pageerror',lambda exc: errors.append(f'{profile}:pageerror:{exc}'))
                page.on('console',lambda msg: errors.append(f'{profile}:console:{msg.type}:{msg.text}') if msg.type=='error' else None)
                page.set_content(html,wait_until='domcontentloaded'); page.wait_for_timeout(500)
                section=page.locator('[data-entry-guidance="learnit.entry_guidance.rc658.v1"]')
                primary=section.locator('[data-entry-role="primary"]')
                alternative=section.locator('[data-entry-role="alternative"]')
                add(f'{profile}-entry-section',section.count()==1 and section.get_attribute('data-session-entry-state')=='new',section.get_attribute('data-session-entry-state'))
                add(f'{profile}-one-primary-one-alternative',primary.count()==1 and alternative.count()==1,f'{primary.count()}/{alternative.count()}')
                add(f'{profile}-other-modes-closed',not section.locator('details.rc580-other-modes').get_attribute('open'),str(section.locator('details.rc580-other-modes').get_attribute('open')))
                boundary=section.locator('.assessment-boundary').inner_text()
                add(f'{profile}-assessment-boundary','progression inchangée' in boundary and 'progression enregistrée' in boundary,boundary)
                pbox=primary.bounding_box(); abox=alternative.bounding_box()
                if profile=='desktop':
                    add('desktop-primary-width-dominance',bool(pbox and abox and pbox['width'] >= abox['width']*2),f'{pbox}/{abox}')
                else:
                    add('mobile-primary-height-dominance',bool(pbox and abox and pbox['height'] >= abox['height']*1.35),f'{pbox}/{abox}')
                    add('mobile-touch-targets',bool(pbox and abox and pbox['height']>=44 and abox['height']>=44),f'{pbox}/{abox}')
                focus_order=page.evaluate("""()=>Array.from(document.querySelectorAll('[data-entry-guidance] button,[data-entry-guidance] summary')).filter(e=>e.offsetParent!==null).map(e=>e.getAttribute('data-entry-role')||e.textContent.trim()).slice(0,3)""")
                add(f'{profile}-focus-order',focus_order[0]=='primary' and focus_order[1]=='alternative' and focus_order[2].startswith('Voir tous les modes'),focus_order)
                overflow=page.evaluate('({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})')
                add(f'{profile}-no-horizontal-overflow',overflow['sw']<=overflow['cw']+4,overflow)
                page.close()

            # Primary action starts Discovery and is keyboard-operable.
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page.set_content(html,wait_until='domcontentloaded');page.wait_for_timeout(400)
            page.locator('[data-entry-role="primary"]').focus(); page.keyboard.press('Enter'); page.wait_for_timeout(250)
            primary_state=page.evaluate("({view:window.__LEARNIT_TEST__.runtime.appState.view,mode:window.__LEARNIT_TEST__.runtime.session.session.mode,policy:window.LearnItSessionModeModel.sessionPolicy(window.__LEARNIT_TEST__.runtime.session.session)})")
            add('primary-starts-discovery',primary_state['view']=='session' and primary_state['mode']=='discovery' and primary_state['policy']['recordProgress'] is True,primary_state)
            page.close()

            # Alternative action starts a non-recording Diagnostic.
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page.set_content(html,wait_until='domcontentloaded');page.wait_for_timeout(400)
            page.locator('[data-entry-role="alternative"]').click(); page.wait_for_timeout(250)
            alt_state=page.evaluate("({view:window.__LEARNIT_TEST__.runtime.appState.view,mode:window.__LEARNIT_TEST__.runtime.session.session.mode,policy:window.LearnItSessionModeModel.sessionPolicy(window.__LEARNIT_TEST__.runtime.session.session)})")
            add('alternative-starts-diagnostic',alt_state['view']=='session' and alt_state['mode']=='diagnostic' and alt_state['policy']['recordProgress'] is False,alt_state)
            page.close()

            # Active session precedence removes competing alternative and offers resume.
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page.set_content(html,wait_until='domcontentloaded');page.wait_for_timeout(400)
            page.evaluate("window.__LEARNIT_TEST__.runtime.session.startMode('training'); window.__LEARNIT_TEST__.runtime.go('learn')")
            page.wait_for_timeout(300)
            active=page.locator('[data-entry-guidance]')
            add('active-session-precedence',active.get_attribute('data-session-entry-state')=='active' and active.locator('[data-entry-role="primary"]').inner_text().find('Reprendre la séance')>=0 and active.locator('[data-entry-role="alternative"]').count()==0,active.inner_text())
            page.close()
        finally:
            browser.close()
    add('no-browser-errors',not errors,' | '.join(errors[-10:]))
    ok=all(r['ok'] for r in rows)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc659.browser_entry_guidance.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(r['ok'] for r in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__':
    raise SystemExit(main())
