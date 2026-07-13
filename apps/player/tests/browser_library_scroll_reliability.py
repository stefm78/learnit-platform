#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil
from support import ROOT

OUT=ROOT/'reports/browser_library_scroll_reliability_report.json'
SHOT_MAIN=ROOT/'reports/RC688_MOBILE_LIBRARY_SCROLL_SWIPE.png'
SHOT_PLAN=ROOT/'reports/RC688_MOBILE_PLAN_SCROLL.png'


def main()->int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    html=(ROOT/'dist/learnit.html').read_text(encoding='utf-8')
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':390,'height':640},is_mobile=True,has_touch=True,device_scale_factor=2)
        page=context.new_page(); page.set_default_timeout(8000)
        page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
        page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
        client=context.new_cdp_session(page)

        def gesture(selector:str,dx:float=0,dy:float=0,steps:int=18,wait:int=360):
            loc=page.locator(selector).first
            loc.scroll_into_view_if_needed()
            box=loc.bounding_box()
            if not box: raise AssertionError(f'No box for {selector}')
            viewport=page.viewport_size or {'width':390,'height':640}
            x0=min(viewport['width']-32,max(32,box['x']+max(18,min(box['width']-18,box['width']*0.52))))
            y0=min(viewport['height']-54,max(100,box['y']+max(20,min(box['height']-18,box['height']*0.62))))
            x1=min(viewport['width']-18,max(18,x0+dx)); y1=min(viewport['height']-44,max(72,y0+dy))
            client.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x0,'y':y0,'radiusX':5,'radiusY':5,'force':1}], 'modifiers':0})
            for i in range(1,steps+1):
                x=x0+(x1-x0)*i/steps; y=y0+(y1-y0)*i/steps
                client.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y,'radiusX':5,'radiusY':5,'force':1}], 'modifiers':0})
                page.wait_for_timeout(18)
            client.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[], 'modifiers':0})
            page.wait_for_timeout(wait)

        def nav(route:str):
            page.wait_for_timeout(620)
            page.locator(f'nav.nav button[data-nav="{route}"]').click(); page.wait_for_timeout(360)

        def active()->str:
            return page.evaluate("window.__LEARNIT_TEST__.runtime.appState.view")

        def transaction()->bool:
            return bool(page.evaluate("!!(window.__LEARNIT_TEST__.runtime.routeCarouselState&&window.__LEARNIT_TEST__.runtime.routeCarouselState.transaction)"))

        def scroll_check(code:str,selector:str,dx:float=0,dy:float=-145):
            panel=page.locator('.route-panel.route-view-library.is-active')
            page.evaluate("document.querySelector('.route-panel.route-view-library.is-active').scrollTop=0")
            before=panel.evaluate('el=>el.scrollTop'); gesture(selector,dx,dy,wait=180); after=panel.evaluate('el=>el.scrollTop')
            add(code,active()=='library' and after>=before+35 and not transaction(),{'before':before,'after':after,'active':active()})

        try:
            page.set_content(html,wait_until='domcontentloaded'); page.wait_for_timeout(600)
            nav('library')
            panel=page.locator('.route-panel.route-view-library.is-active')
            metrics=panel.evaluate("""el=>{const lib=el.querySelector('.library-page');const cs=getComputedStyle(el);return {scrollHeight:el.scrollHeight,clientHeight:el.clientHeight,overflowY:cs.overflowY,touchAction:cs.touchAction,contract:lib&&lib.dataset.libraryScrollContract,intent:lib&&lib.dataset.routeSwipeIntent,excluded:lib&&lib.dataset.routeSwipeExclusion,transform:cs.transform}}""")
            add('library-route-is-native-scroll-owner',metrics['scrollHeight']>metrics['clientHeight']+20 and metrics['overflowY']=='scroll' and 'pan-y' in metrics['touchAction'] and metrics['contract']=='native-route-panel',metrics)
            add('library-content-observable-for-intent',metrics['intent']=='observable' and not metrics['excluded'] and metrics['transform']=='none',metrics)

            # G01-G04 — native vertical movement from natural Library zones.
            scroll_check('G01-scroll-from-card','.route-panel.route-view-library.is-active .book-row')
            scroll_check('G02-scroll-from-title','.route-panel.route-view-library.is-active .book-title')
            scroll_check('G03-scroll-from-status','.route-panel.route-view-library.is-active .book-status')
            scroll_check('G04-scroll-from-list-space','.route-panel.route-view-library.is-active .collection-list')

            # G05/G06 — both horizontal directions from content.
            page.evaluate("document.querySelector('.route-panel.route-view-library.is-active').scrollTop=0")
            gesture('.route-panel.route-view-library.is-active .book-title',-185,-8)
            add('G05-library-swipe-left-to-bilan',active()=='bilan',active())
            nav('library'); gesture('.route-panel.route-view-library.is-active .book-title',185,7)
            add('G06-library-swipe-right-to-learn',active()=='learn',active())

            # G07/G08/G09 — diagonals and ambiguous movement.
            nav('library'); page.evaluate("document.querySelector('.route-panel.route-view-library.is-active').scrollTop=0")
            before=panel.evaluate('el=>el.scrollTop'); gesture('.route-panel.route-view-library.is-active .book-title',28,-155,wait=180); after=panel.evaluate('el=>el.scrollTop')
            add('G07-diagonal-vertical-scrolls',active()=='library' and after>=before+35 and not transaction(),{'before':before,'after':after,'active':active()})
            page.evaluate("document.querySelector('.route-panel.route-view-library.is-active').scrollTop=0"); gesture('.route-panel.route-view-library.is-active .book-title',-185,-42)
            add('G08-diagonal-horizontal-routes',active()=='bilan',active())
            nav('library'); gesture('.route-panel.route-view-library.is-active .book-title',-14,-11,steps=5,wait=140)
            add('G09-ambiguous-gesture-does-nothing',active()=='library' and not transaction(),active())

            # G10/G11 — sequential ownership remains healthy.
            page.evaluate("document.querySelector('.route-panel.route-view-library.is-active').scrollTop=0"); gesture('.route-panel.route-view-library.is-active .book-title',0,-145,wait=160)
            scrolled=panel.evaluate('el=>el.scrollTop'); gesture('.route-panel.route-view-library.is-active .book-title',-185,0)
            add('G10-scroll-then-swipe',scrolled>35 and active()=='bilan',{'scrollTop':scrolled,'active':active()})
            nav('library'); page.evaluate("document.querySelector('.route-panel.route-view-library.is-active').scrollTop=0"); gesture('.route-panel.route-view-library.is-active .book-title',0,-145,wait=180)
            add('G11-swipe-return-then-scroll',active()=='library' and panel.evaluate('el=>el.scrollTop')>35,{'active':active(),'scrollTop':panel.evaluate('el=>el.scrollTop')})

            # G12/G13 — form fields remain strict exclusions.
            page.evaluate("document.querySelector('.route-panel.route-view-library.is-active').scrollTop=0")
            search=page.locator('#librarySearch'); search.click(); search.fill('comp'); search.evaluate("el=>el.setSelectionRange(2,2)")
            gesture('#librarySearch',-185,0)
            state=search.evaluate("el=>({value:el.value,start:el.selectionStart,focused:document.activeElement===el})")
            add('G12-search-excludes-route-swipe',active()=='library' and state['value']=='comp' and not transaction(),state)
            search.fill('complexe'); page.wait_for_timeout(120); page.locator('[data-action="library-clear-search"]').click(); page.wait_for_timeout(180)
            add('G13-search-edit-clear-stable',active()=='library' and page.locator('#librarySearch').input_value()=='',active())

            # Store main position before opening the sheet.
            page.evaluate("document.querySelector('.route-panel.route-view-library.is-active').scrollTop=90")
            main_top=panel.evaluate('el=>el.scrollTop')
            page.evaluate("document.querySelector('.book-open-main').click()"); page.wait_for_timeout(240)
            page.add_style_tag(content='.book-detail-sheet .book-modal.book-detail-panel{max-height:300px!important}')
            body=page.locator('.book-detail-sheet .book-modal-body')
            detail=body.evaluate("el=>({scrollHeight:el.scrollHeight,clientHeight:el.clientHeight,overflowY:getComputedStyle(el).overflowY,touchAction:getComputedStyle(el).touchAction})")
            gesture('.book-detail-sheet .book-modal-body',0,-180,wait=180); detail_top=body.evaluate('el=>el.scrollTop')
            add('G14-library-detail-touch-scrolls',detail['scrollHeight']>detail['clientHeight']+20 and detail_top>=45 and active()=='library',{'metrics':detail,'top':detail_top})

            page.get_by_role('button',name='Plan').click(); page.wait_for_timeout(240)
            plan_body=page.locator('.book-detail-sheet .book-modal.plan-mode .book-modal-body')
            plan_metrics=plan_body.evaluate("el=>({scrollHeight:el.scrollHeight,clientHeight:el.clientHeight,touchAction:getComputedStyle(el).touchAction})")
            gesture('.book-detail-sheet .chapter-list .chapter',0,-150,wait=180); plan_before=plan_body.evaluate('el=>el.scrollTop')
            add('G15-library-plan-touch-scrolls',plan_metrics['scrollHeight']>plan_metrics['clientHeight']+15 and plan_before>=35 and active()=='library',{'metrics':plan_metrics,'top':plan_before})
            page.evaluate("document.querySelectorAll('.book-detail-sheet .chapter')[1].click()"); page.wait_for_timeout(260)
            plan_after=page.locator('.book-detail-sheet .book-modal.plan-mode .book-modal-body').evaluate('el=>el.scrollTop')
            selected=page.locator('.book-detail-sheet .chapter[aria-selected="true"]').get_attribute('data-chapter')
            add('G16-plan-selection-preserves-scroll',selected=='1' and abs(plan_after-plan_before)<=4,{'before':plan_before,'after':plan_after,'selected':selected})
            SHOT_PLAN.parent.mkdir(exist_ok=True); page.screenshot(path=str(SHOT_PLAN),full_page=False)
            page.locator('[data-action="library-home"]').click(); page.wait_for_timeout(220)
            restored=page.locator('.route-panel.route-view-library.is-active').evaluate('el=>el.scrollTop')
            add('G17-closing-sheet-restores-position',abs(restored-main_top)<=4,{'before':main_top,'after':restored})

            # G18/G19 — strict exclusions survive on representative targets.
            strict=page.evaluate("""()=>{const host=document.querySelector('.library-page');const a=document.createElement('button');a.textContent='drag';a.dataset.dragOrderToken='x';a.id='rc677StrictDrag';host.appendChild(a);const m=document.createElement('figure');m.id='rc677Zoomed';m.className='media-figure is-zooming';m.textContent='zoom';m.style.cssText='height:80px';host.appendChild(m);return true;}""")
            gesture('#rc677StrictDrag',-185,0); add('G18-drag-target-excludes-route-swipe',strict and active()=='library' and not transaction(),active())
            gesture('#rc677Zoomed',-185,0); add('G19-zoomed-media-excludes-route-swipe',active()=='library' and not transaction(),active())

            nav('bilan'); nav('tools'); nav('library')
            add('G20-top-navigation-transaction-intact',active()=='library' and page.locator('nav.nav button[data-nav="library"]').get_attribute('aria-current')=='page',active())
            SHOT_MAIN.parent.mkdir(exist_ok=True); page.screenshot(path=str(SHOT_MAIN),full_page=False)
        finally:
            context.close(); browser.close()

    add('no-browser-errors',not errors,' | '.join(errors[-10:]))
    ok=all(r['ok'] for r in rows)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc688.browser_library_scroll_swipe_matrix.v1','ok':ok,'checks':rows,'errors':errors,'screenshots':[str(SHOT_MAIN.relative_to(ROOT)),str(SHOT_PLAN.relative_to(ROOT))]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(r['ok'] for r in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__': raise SystemExit(main())
