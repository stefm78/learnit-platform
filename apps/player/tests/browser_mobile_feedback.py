#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil
from support import ROOT

OUT=ROOT/'reports/browser_mobile_feedback_report.json'
SHOT_SESSION=ROOT/'reports/RC677_MOBILE_SESSION.png'
SHOT_LIBRARY=ROOT/'reports/RC677_MOBILE_LIBRARY_DETAIL.png'
SHOT_PLAN=ROOT/'reports/RC677_MOBILE_LIBRARY_PLAN.png'

def main()->int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    html=(ROOT/'dist/learnit.html').read_text(encoding='utf-8')
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page.set_default_timeout(7000)
            page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content(html,wait_until='domcontentloaded');page.wait_for_timeout(450)

            # Mobile navigation must never split Bibliothèque.
            page.locator('nav.nav button[data-nav="library"]').click();page.wait_for_timeout(250)
            nav=page.locator('nav.nav button[data-nav="library"]')
            nav_metrics=nav.evaluate("el=>({text:el.innerText,whiteSpace:getComputedStyle(el).whiteSpace,scrollHeight:el.scrollHeight,clientHeight:el.clientHeight,scrollWidth:el.scrollWidth,clientWidth:el.clientWidth})")
            add('library-nav-single-line',nav_metrics['whiteSpace']=='nowrap' and nav_metrics['scrollHeight']<=nav_metrics['clientHeight']+2 and nav_metrics['scrollWidth']<=nav_metrics['clientWidth']+2,nav_metrics)

            # Search: middle edit keeps exact caret and explicit clear stays easy.
            search=page.locator('#librarySearch')
            search.fill('Nombres');page.wait_for_timeout(180)
            page.evaluate("""()=>{const el=document.querySelector('#librarySearch');el.focus();el.setSelectionRange(3,3);el.setRangeText('X',3,3,'end');el.dispatchEvent(new Event('input',{bubbles:true}));}""")
            page.wait_for_timeout(220)
            edit=page.evaluate("""()=>{const el=document.querySelector('#librarySearch');return {value:el.value,start:el.selectionStart,end:el.selectionEnd,active:document.activeElement===el}}""")
            add('search-middle-edit-caret',edit=={'value':'NomXbres','start':4,'end':4,'active':True},edit)
            clear=page.locator('[data-action="library-clear-search"]')
            add('search-clear-visible',clear.count()==1 and clear.is_enabled())
            clear.click();page.wait_for_timeout(120)
            clear_state=page.evaluate("""()=>{const el=document.querySelector('#librarySearch');return {value:el.value,active:document.activeElement===el}}""")
            add('search-clear-keeps-focus',clear_state=={'value':'','active':True},clear_state)

            # Course detail is a viewport sheet, not a block appended at the end.
            page.locator('.book-open-main').first.click();page.wait_for_timeout(220)
            sheet=page.locator('.book-detail-sheet')
            sheet_metrics=sheet.evaluate("el=>{const r=el.getBoundingClientRect();const b=el.querySelector('.book-modal-body');const t=el.querySelector('.cover-title');return {position:getComputedStyle(el).position,top:r.top,height:r.height,viewport:innerHeight,bodyOverflow:getComputedStyle(b).overflowY,titleColor:getComputedStyle(t).color,dialog:el.querySelector('[role=dialog]')!==null}}")
            add('library-detail-viewport-sheet',sheet_metrics['position']=='fixed' and sheet_metrics['top']==0 and sheet_metrics['height']>=sheet_metrics['viewport']-2 and sheet_metrics['dialog'],sheet_metrics)
            add('library-sheet-independent-scroll',sheet_metrics['bodyOverflow'] in ('auto','scroll'),sheet_metrics)
            rgb=[int(x) for x in sheet_metrics['titleColor'].replace('rgb(','').replace(')','').split(',')[:3]]
            add('jacket-title-high-contrast',min(rgb)>=235,sheet_metrics['titleColor'])
            SHOT_LIBRARY.parent.mkdir(exist_ok=True);page.screenshot(path=str(SHOT_LIBRARY),full_page=False)

            # Plan: the chapter list is the single navigation owner. No duplicated
            # selected-chapter card, no sequential steppers, no explanatory banner.
            page.get_by_role('button',name='Plan').click();page.wait_for_timeout(220)
            plan=page.locator('.book-detail-sheet .book-modal.plan-mode')
            shell=plan.locator('.chapter-static-shell')
            chapter_rows=shell.locator('.chapter')
            plan_state=plan.evaluate("""el=>{const body=el.querySelector('.book-modal-body');const first=el.querySelector('.chapter');const action=el.querySelector('.chapter-action-sticky');const button=el.querySelector('.chapter-go');const subtitle=el.querySelector('.book-head-collection');const br=body.getBoundingClientRect(),fr=first.getBoundingClientRect(),ar=action.getBoundingClientRect(),bt=button.getBoundingClientRect();return {bodyTop:br.top,firstTop:fr.top,gap:fr.top-br.top,actionPosition:getComputedStyle(action).position,actionBottom:innerHeight-ar.bottom,buttonWidth:bt.width,bodyWidth:br.width,subtitle:subtitle?subtitle.innerText:'',bodyOverflow:getComputedStyle(body).overflowY}}""")
            add('plan-list-first-contract',shell.get_attribute('data-chapter-navigation-contract')=='list-first' and chapter_rows.count()>=2,{'contract':shell.get_attribute('data-chapter-navigation-contract'),'chapters':chapter_rows.count()})
            duplicate_nav=plan.locator('.chapter-reading-head,.chapter-static-contract,[data-action="library-prev-chapter"],[data-action="library-next-chapter"],.book-head-nav')
            add('plan-removes-duplicate-navigation',duplicate_nav.count()==0,duplicate_nav.count())
            add('plan-list-starts-near-header',plan_state['gap']<=24,plan_state)
            add('plan-header-carries-count',f"{chapter_rows.count()} chapitres" in plan_state['subtitle'],plan_state['subtitle'])
            add('plan-sticky-contextual-action',plan_state['actionPosition']=='sticky' and plan_state['buttonWidth']>=plan_state['bodyWidth']-40,plan_state)
            chapter_rows.nth(1).click();page.wait_for_timeout(180)
            selection=page.evaluate("""()=>{const shell=document.querySelector('.book-detail-sheet .chapter-static-shell');const selected=shell.querySelector('.chapter[aria-selected="true"]');const cta=shell.querySelector('[data-action="library-chapter-go"]');return {index:shell.dataset.chapterIndex,selected:selected&&selected.dataset.chapter,cta:cta&&cta.dataset.chapter}}""")
            add('plan-direct-selection-drives-action',selection=={'index':'1','selected':'1','cta':'1'},selection)
            page.screenshot(path=str(SHOT_PLAN),full_page=False)
            page.locator('[data-action="library-home"]').click();page.wait_for_timeout(120)

            # Inject a repeated-token fill activity to prove the exact reported defect.
            page.evaluate("""()=>{const r=window.__LEARNIT_TEST__.runtime;const a={id:'rc677-fill-theta-twice',type:'fill',question:'Complète la formule avec le même angle.',objective:'Déterminer un argument et une forme trigonométrique complète',parts:['cos(',0,') + i sin(',1,')'],tokens:['θ'],answer:['θ','θ'],sentence:'cos(θ) + i sin(θ)',why:'Le même angle intervient deux fois.',remediation:'Réutiliser θ dans les deux emplacements.'};r.contentStore.content.activities.push(a);r.appState.state.session=r.session.baseSession('training',[a.id]);r.answer.reset();r.go('session');}""")
            page.wait_for_timeout(180)
            banner=page.locator('.session-mode-banner')
            add('session-banner-compact',banner.inner_text().strip()=='Entraînement' and 'Nouveau sujet' not in banner.inner_text(),banner.inner_text())
            objective=page.locator('.activity-objective')
            obj=objective.evaluate("el=>({text:el.innerText,whiteSpace:getComputedStyle(el).whiteSpace,overflow:getComputedStyle(el).overflow,scrollWidth:el.scrollWidth,clientWidth:el.clientWidth,scrollHeight:el.scrollHeight,clientHeight:el.clientHeight})")
            add('objective-wraps-without-clipping',obj['text'].endswith('Déterminer un argument et une forme trigonométrique complète') and obj['whiteSpace']=='normal' and obj['scrollHeight']<=obj['clientHeight']+2,obj)
            theta=page.locator('[data-fill-token="θ"]')
            theta.click();page.wait_for_timeout(100)
            first=page.evaluate("""()=>{const b=document.querySelector('[data-fill-token="θ"]');return {disabled:b.disabled,label:b.getAttribute('aria-label'),slots:Array.from(document.querySelectorAll('[data-fill-slot]')).map(x=>x.innerText)}}""")
            add('theta-remains-after-first-use',not first['disabled'] and 'encore 1 fois' in first['label'] and first['slots'].count('θ')==1,first)
            page.locator('[data-fill-token="θ"]').click();page.wait_for_timeout(100)
            second=page.evaluate("""()=>{const b=document.querySelector('[data-fill-token="θ"]');return {disabled:b.disabled,slots:Array.from(document.querySelectorAll('[data-fill-slot]')).map(x=>x.innerText)}}""")
            add('theta-usable-twice',second['disabled'] and second['slots']==['θ','θ'],second)
            SHOT_SESSION.parent.mkdir(exist_ok=True);page.screenshot(path=str(SHOT_SESSION),full_page=False)

            order_probe=page.evaluate("""()=>{const p=window.LearnItOrderActivity.pointer;const rects=[{top:100,height:60},{top:160,height:60}];return {up:p.computeIndexFromRects(rects,{y:135,offsetY:30,sourceRect:{height:60},directionY:-1}),neutral:p.computeIndexFromRects(rects,{y:135,offsetY:30,sourceRect:{height:60},directionY:0})}}""")
            add('order-upward-insertion-earlier',order_probe=={'up':0,'neutral':1},order_probe)
            page.close()
        finally:
            browser.close()
    add('no-browser-errors',not errors,' | '.join(errors[-10:]))
    ok=all(r['ok'] for r in rows)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc677.browser_mobile_feedback.v1','ok':ok,'checks':rows,'errors':errors,'screenshots':[str(SHOT_SESSION.relative_to(ROOT)),str(SHOT_LIBRARY.relative_to(ROOT)),str(SHOT_PLAN.relative_to(ROOT))]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(r['ok'] for r in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__': raise SystemExit(main())
