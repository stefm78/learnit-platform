#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil
from support import ROOT

OUT=ROOT/'reports/browser_desktop_scroll_reliability_report.json'
SHOT=ROOT/'reports/RC688_DESKTOP_SCROLL.png'

def main()->int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    html=(ROOT/'dist/learnit.html').read_text(encoding='utf-8')
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':1440,'height':900})
        page=context.new_page(); page.set_default_timeout(8000)
        page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
        page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
        try:
            page.set_content(html,wait_until='domcontentloaded'); page.wait_for_timeout(650)
            page.locator('nav.nav button[data-nav="library"]').click(); page.wait_for_timeout(420)
            page.evaluate("""()=>{
              const body=document.querySelector('.collection-body');
              const row=body&&body.querySelector('.book-row');
              if(body&&row){for(let i=0;i<28;i++){const clone=row.cloneNode(true);clone.dataset.rc688Clone=String(i);body.appendChild(clone);}}
            }""")
            page.wait_for_timeout(120)
            metrics=page.evaluate("""()=>{
              const panel=document.querySelector('.route-panel.route-view-library.is-active');
              const viewport=document.querySelector('[data-route-carousel]');
              const inactive=[...document.querySelectorAll('.route-panel.is-inactive')].map(el=>({h:el.getBoundingClientRect().height,overflow:getComputedStyle(el).overflowY}));
              return {doc:document.documentElement.scrollHeight,innerHeight,windowY:scrollY,panelScrollHeight:panel.scrollHeight,panelClientHeight:panel.clientHeight,panelOverflow:getComputedStyle(panel).overflowY,panelOverscroll:getComputedStyle(panel).overscrollBehaviorY,contract:viewport&&viewport.dataset.desktopScrollContract,inactive};
            }""")
            add('desktop-contract-active',metrics['contract']=='rc688-window-owner',metrics)
            add('desktop-document-is-scrollable',metrics['doc']>metrics['innerHeight']+350,metrics)
            add('desktop-panel-does-not-own-scroll',metrics['panelOverflow']=='visible' and metrics['panelOverscroll']=='auto',metrics)
            add('inactive-panels-do-not-inflate-layout',all(item['h']<=1 for item in metrics['inactive']),metrics['inactive'])

            def wheel_from(code,selector,delta=520):
                page.evaluate('window.scrollTo(0,0)'); page.wait_for_timeout(40)
                loc=page.locator(selector).first; loc.scroll_into_view_if_needed(); box=loc.bounding_box()
                if not box: add(code,False,'missing box'); return
                x=min(1410,max(30,box['x']+max(4,min(box['width']-4,box['width']*.45))))
                y=min(860,max(90,box['y']+max(4,min(box['height']-4,box['height']*.45))))
                page.mouse.move(x,y); page.mouse.wheel(0,delta); page.wait_for_timeout(130)
                state=page.evaluate("""()=>({windowY:Math.round(scrollY),panelY:Math.round(document.querySelector('.route-panel.route-view-library.is-active').scrollTop),view:window.__LEARNIT_TEST__.runtime.appState.view})""")
                add(code,state['windowY']>=180 and state['panelY']==0 and state['view']=='library',state)

            wheel_from('W01-wheel-from-book-title','.route-panel.route-view-library.is-active .book-title')
            wheel_from('W02-wheel-from-status','.route-panel.route-view-library.is-active .book-status')
            wheel_from('W03-wheel-from-row','.route-panel.route-view-library.is-active .book-row')
            wheel_from('W04-wheel-from-collection','.route-panel.route-view-library.is-active .collection')
            wheel_from('W05-wheel-from-list-space','.route-panel.route-view-library.is-active .collection-list')
            wheel_from('W06-wheel-from-search','.route-panel.route-view-library.is-active #librarySearch')
            wheel_from('W07-wheel-from-open-button','.route-panel.route-view-library.is-active .book-open-main')

            page.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)'); page.wait_for_timeout(60)
            before=page.evaluate('Math.round(scrollY)')
            loc=page.locator('.route-panel.route-view-library.is-active .book-row').last; loc.scroll_into_view_if_needed(); box=loc.bounding_box()
            page.mouse.move(box['x']+20,min(850,box['y']+15)); page.mouse.wheel(0,-520); page.wait_for_timeout(130)
            after=page.evaluate('Math.round(scrollY)')
            add('W08-wheel-up-from-content',before-after>=180,{'before':before,'after':after})

            page.evaluate('window.scrollTo(0,0)'); page.locator('.book-open-main').first.click(); page.wait_for_timeout(220)
            page.add_style_tag(content='.book-detail-sheet .book-modal.book-detail-panel{max-height:300px!important}')
            body=page.locator('.book-detail-sheet .book-modal-body'); body_box=body.bounding_box()
            page.mouse.move(body_box['x']+60,body_box['y']+150); page.mouse.wheel(0,420); page.wait_for_timeout(140)
            nested=body.evaluate('el=>({top:Math.round(el.scrollTop),scrollHeight:el.scrollHeight,clientHeight:el.clientHeight})')
            window_y=page.evaluate('Math.round(scrollY)')
            add('W09-modal-retains-local-scroll-owner',nested['scrollHeight']>nested['clientHeight'] and nested['top']>=60 and window_y==0,{'modal':nested,'windowY':window_y})
            page.locator('[data-action="library-close-level"]').last.click(); page.wait_for_timeout(160)
            SHOT.parent.mkdir(exist_ok=True); page.screenshot(path=str(SHOT),full_page=False)
        finally:
            context.close(); browser.close()
    add('no-browser-errors',not errors,' | '.join(errors[-10:]))
    ok=all(r['ok'] for r in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc688.browser_desktop_scroll_matrix.v1','ok':ok,'checks':rows,'errors':errors,'screenshot':str(SHOT.relative_to(ROOT))},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(r['ok'] for r in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__': raise SystemExit(main())
