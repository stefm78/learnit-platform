#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'/'browser_bilan_library_ux_report.json'

def main()->int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    html=(ROOT/'dist/learnit.html').read_text(encoding='utf-8')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            # Desktop Bilan: a new learner gets an explicit recommendation and a prior-knowledge branch.
            page=browser.new_page(viewport={'width':1365,'height':900})
            page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content(html,wait_until='domcontentloaded');page.wait_for_timeout(350)
            page.locator('nav.nav button[data-nav="bilan"]').click();page.wait_for_timeout(300)
            hero=page.locator('.route-panel[data-route="bilan"] .bilan-action-hero')
            add('bilan-single-primary-hero',hero.count()==1 and hero.locator('[data-rc580-intent="discovery"]').count()==1)
            add('bilan-new-course-guidance','Découvrir ce parcours' in (hero.text_content() or '') and 'Évaluer rapidement mon niveau' in (hero.text_content() or ''),hero.text_content() or '')
            add('bilan-fresh-evidence-status',page.locator('.route-panel[data-route="bilan"] .rc593-evidence-bilan[data-evidence-status="not-started"]').count()==1 and page.locator('.route-panel[data-route="bilan"] .evidence-empty').count()==1)
            add('bilan-recommendation-reason-coded',hero.get_attribute('data-evidence-reason')=='no-evidence-yet',str(hero.get_attribute('data-evidence-reason')))
            add('bilan-no-false-percentage','%' not in (page.locator('.route-panel[data-route="bilan"] .bilan-detail').text_content() or ''),page.locator('.route-panel[data-route="bilan"] .bilan-detail').text_content() or '')
            add('bilan-diagnostic-validation-boundary','Diagnostic' in (page.locator('.bilan-mode-boundary').text_content() or '') and 'Validation' in (page.locator('.bilan-mode-boundary').text_content() or ''))
            more=page.locator('.route-panel[data-route="bilan"] .bilan-more')
            add('bilan-secondary-collapsed',more.count()==1 and more.get_attribute('open') is None)
            add('bilan-no-legacy-visible-stack',page.locator('.route-panel[data-route="bilan"] .rc241-review-freedom').count()==0 and page.locator('.route-panel[data-route="bilan"] .rc246-remediation-map').count()==0)
            add('bilan-chapter-hierarchy',page.locator('.route-panel[data-route="bilan"] .bilan-chapter-row').count()>=2)
            page.evaluate('''() => {const r=window.__LEARNIT_TEST__.runtime;const id=r.contentStore.activeCourseId;const acts=r.contentStore.content.activities;const p={};p[acts[0].id]={seen:true,correct:false,review:true,lastAt:'2026-07-10T10:00:00Z'};p[acts[1].id]={seen:true,correct:true,attempts:2,successCount:2,reviewLevel:2,nextReviewAt:'2099-01-01T00:00:00Z',attemptHistory:[{correct:true,at:'2026-07-01T10:00:00Z'},{correct:true,at:'2026-07-03T10:00:00Z'}]};r.appState.state.activityProgressByCourseId[id]=p;r.appState.save();r.render();}''');page.wait_for_timeout(220)
            mixed=page.locator('.route-panel[data-route="bilan"] .rc593-evidence-bilan')
            add('bilan-migrates-legacy-progress',mixed.get_attribute('data-evidence-status')=='fragile' and mixed.locator('.bilan-action-hero').get_attribute('data-evidence-reason')=='fragile-objectives',mixed.text_content() or '')
            add('bilan-objective-evidence-visible',mixed.locator('.bilan-objective-row').count()>=2 and 'Fragile' in (mixed.text_content() or '') and 'Consolidé' in (mixed.text_content() or ''),mixed.text_content() or '')
            # Restore a fresh state to keep the prior-knowledge branch under test.
            page.evaluate('''() => {const r=window.__LEARNIT_TEST__.runtime;const id=r.contentStore.activeCourseId;r.appState.state.activityProgressByCourseId[id]={};r.appState.save();r.render();}''');page.wait_for_timeout(180)
            hero=page.locator('.route-panel[data-route="bilan"] .bilan-action-hero')
            hero.locator('[data-rc580-intent="diagnostic"]').click();page.wait_for_timeout(250)
            mode=page.evaluate('window.__LEARNIT_TEST__.runtime.session.session.mode')
            view=page.evaluate('window.__LEARNIT_TEST__.runtime.appState.view')
            add('bilan-prior-knowledge-starts-diagnostic',mode=='diagnostic' and view=='session',f'{mode}/{view}')
            page.close()

            # Desktop Learn: only two situation-led choices are visible; all other modes stay available but collapsed.
            learn=browser.new_page(viewport={'width':1365,'height':900})
            learn.on('pageerror',lambda exc: errors.append(f'learn-pageerror:{exc}'))
            learn.set_content(html,wait_until='domcontentloaded');learn.wait_for_timeout(350)
            entry=learn.locator('.route-panel[data-route="learn"] .rc580-course-entry')
            add('learn-entry-guidance-visible',entry.count()==1 and entry.get_attribute('data-session-entry-state')=='new')
            add('learn-action-first-with-alternative',entry.locator('[data-entry-role="primary"]').count()==1 and entry.locator('[data-entry-role="alternative"]').count()==1 and entry.locator('[data-rc580-intent="discovery"]').count()==1 and entry.locator('[data-rc580-intent="diagnostic"]').count()==1)
            other=entry.locator('details.rc580-other-modes')
            add('learn-other-modes-collapsed',other.count()==1 and other.get_attribute('open') is None and other.locator('[data-rc580-intent]').count()==3)
            add('learn-no-duplicated-mode-panels',learn.locator('.route-panel[data-route="learn"] .rc239-smart-resume').count()==0 and learn.locator('.route-panel[data-route="learn"] .rc247-spaced-review').count()==0 and learn.locator('.route-panel[data-route="learn"] .rc248-training-modes').count()==0)
            learn.evaluate('''() => {const r=window.__LEARNIT_TEST__.runtime;const id=r.contentStore.activeCourseId;const p={};for(const a of r.contentStore.content.activities)p[a.id]={seen:true,correct:true,review:false,attempts:2,attemptCount:2,successCount:2,reviewLevel:2,nextReviewAt:'2099-01-01T00:00:00.000Z',attemptHistory:[{correct:true,at:'2026-07-01T10:00:00.000Z'},{correct:true,at:'2026-07-03T10:00:00.000Z'}],lastAt:'2026-07-03T10:00:00.000Z'};r.appState.state.activityProgressByCourseId[id]=p;r.appState.state.session=r.appState.initialSession();r.appState.state.session.status='idle';r.appState.save();r.render();}''')
            learn.wait_for_timeout(250)
            ready=learn.locator('.route-panel[data-route="learn"] .rc580-course-entry')
            add('learn-completed-recommends-validation',ready.get_attribute('data-session-entry-state')=='ready-to-validate' and ready.locator('[data-rc580-intent="validation"]').count()==1,ready.text_content() or '')
            ready.locator('[data-rc580-intent="validation"]').click();learn.wait_for_timeout(200)
            add('learn-validation-action-starts-validation',learn.evaluate('window.__LEARNIT_TEST__.runtime.session.session.mode')=='validation')
            learn.close()

            # Desktop Library keeps explicit statuses, search and direct actions.
            library=browser.new_page(viewport={'width':1365,'height':900})
            library.on('pageerror',lambda exc: errors.append(f'library-pageerror:{exc}'))
            library.set_content(html,wait_until='domcontentloaded');library.wait_for_timeout(350)
            library.locator('nav.nav button[data-nav="library"]').click();library.wait_for_timeout(300)
            lib=library.locator('.route-panel[data-route="library"]')
            course_rows=lib.locator('[data-course-row]')
            add('library-explicit-status',course_rows.count()>=3 and course_rows.locator('.book-status').count()==course_rows.count(),str(course_rows.count()))
            add('library-direct-actions-desktop',course_rows.locator('.book-direct-action').count()==course_rows.count())
            search=lib.locator('#librarySearch')
            add('library-search-available',search.count()==1)
            search.fill('Puissance');library.wait_for_timeout(250)
            filtered=lib.locator('[data-course-row]')
            add('library-search-filters',filtered.count()==1 and 'Puissance' in (filtered.first.text_content() or ''),str(filtered.count()))
            search.fill('');library.wait_for_timeout(250)
            direct=lib.locator('[data-course-row]').nth(1).locator('.book-direct-action')
            course_id=direct.get_attribute('data-course')
            direct.click();library.wait_for_timeout(300)
            active=library.evaluate('window.__LEARNIT_TEST__.runtime.contentStore.activeCourseId')
            add('library-direct-action-starts-course',library.locator('main').count()==1 and library.locator('.activity-delta-minimal').count()==1 and active==course_id,f'{active}/{course_id}')
            library.close()

            # Mobile: Bilan hierarchy owns natural document height, with no clipped/nested referral list.
            mobile=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            mobile.on('pageerror',lambda exc: errors.append(f'mobile-pageerror:{exc}'))
            mobile.set_content(html,wait_until='domcontentloaded');mobile.wait_for_timeout(350)
            mobile.evaluate("window.__LEARNIT_TEST__.runtime.contentStore.content.title='Golden — parcours prêt pour les modes';window.__LEARNIT_TEST__.runtime.render()")
            mobile.locator('nav.nav button[data-nav="bilan"]').click();mobile.wait_for_timeout(250)
            mobile_hero=mobile.locator('.route-panel[data-route="bilan"] .bilan-action-hero')
            add('mobile-bilan-action-first',mobile_hero.count()==1 and mobile_hero.bounding_box()['y'] < mobile.locator('.bilan-two-pane').bounding_box()['y'])
            nav_style=mobile.locator('.route-panel[data-route="bilan"] .bilan-nav').evaluate("el=>({maxHeight:getComputedStyle(el).maxHeight,overflowY:getComputedStyle(el).overflowY,scrollHeight:el.scrollHeight,clientHeight:el.clientHeight})")
            add('mobile-bilan-no-nested-scroll',nav_style['maxHeight']=='none' and nav_style['overflowY']=='visible',json.dumps(nav_style))
            collection=mobile.locator('.route-panel[data-route="bilan"] details.bilan-collection[open]').first
            selected=mobile.locator('.route-panel[data-route="bilan"] .bilan-course-row.is-selected')
            selected.locator('strong').evaluate("el=>el.textContent='Golden — parcours prêt pour les modes avec un titre volontairement long'")
            mobile.wait_for_timeout(80)
            last_row=collection.locator('.bilan-course-row').last
            cbox=collection.bounding_box();rbox=last_row.bounding_box()
            add('mobile-bilan-collection-not-clipped',bool(cbox and rbox and rbox['y']+rbox['height']<=cbox['y']+cbox['height']+2),f'{cbox}/{rbox}')
            visible_text=selected.locator('strong').text_content() or ''
            add('mobile-bilan-long-title-readable','Golden — parcours prêt pour les modes' in visible_text and selected.evaluate('el=>el.scrollHeight<=el.clientHeight+2'),visible_text)
            mobile.locator('nav.nav button[data-nav="library"]').click();mobile.wait_for_timeout(250)
            hidden=mobile.locator('.route-panel[data-route="library"] .book-direct-action').first.evaluate('el=>getComputedStyle(el).display')
            add('mobile-library-direct-action-delegated',hidden=='none',hidden)
            add('mobile-library-row-open-target',mobile.locator('.route-panel[data-route="library"] .book-open-main').count()>=3)
            mobile.close()
            add('no-browser-errors',not errors,' | '.join(errors[-10:]))
        finally:
            browser.close()
    ok=all(x['ok'] for x in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc659.bilan_explainable_evidence_ux.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(x['ok'] for x in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
