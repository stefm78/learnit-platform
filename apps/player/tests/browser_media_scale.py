#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from support import ROOT

OUT = ROOT / 'reports' / 'browser_media_scale_report.json'


def make_package(course_count: int = 100, activities_per_course: int = 10) -> dict:
    courses=[]
    for i in range(course_count):
        asset_id=f'media-scale-{i:03d}'
        svg=(f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 180'>"
             f"<title>Diagramme {i}</title><rect width='320' height='180' rx='16' fill='#fff' stroke='#334155' stroke-width='3'/>"
             f"<path d='M35 135L110 80L180 115L285 35' fill='none' stroke='#2563eb' stroke-width='5'/>"
             f"<circle cx='{40+(i%20)*10}' cy='{45+(i%10)*8}' r='9' fill='#0f766e'/><text x='24' y='165' font-size='18'>Parcours {i:03d}</text></svg>")
        objective=f'Interpréter le diagramme {i:03d}'
        activities=[]
        for j in range(activities_per_course):
            activity={'id':f'media-scale-{i:03d}-{j:02d}','type':'qcm','objective':objective,
                      'question':f'Question {j+1} sur le diagramme {i:03d} ?','choices':['Réponse correcte','Distracteur'],
                      'answer':0,'why':'La réponse correcte suit le diagramme.','remediation':'Relire le diagramme et comparer les repères.',
                      'difficulty':'medium','learning_phase':'application' if j<activities_per_course-2 else ('remediation' if j==activities_per_course-2 else 'validation'),
                      'assessment_role':'practice' if j<activities_per_course-2 else ('remediation' if j==activities_per_course-2 else 'validation'),
                      'common_errors':['Lire le mauvais repère.']}
            if j==0: activity['media']=[{'assetId':asset_id,'placement':'question','display':'contained','zoomable':True}]
            activities.append(activity)
        courses.append({'schemaVersion':'learnit-content-v2','contentVersion':f'media-scale-v{i}','title':f'Parcours média {i:03d}',
                        'sequence':f'Collection média {i//20:02d}','objectives':[objective],
                        'library_presentation':{'jacket_asset_id':asset_id},
                        'assets':[{'id':asset_id,'type':'image','format':'svg','source':'generated','alt':f'Diagramme du parcours {i:03d}',
                                   'caption':f'Diagramme {i:03d}','pedagogical_role':'diagram_to_interpret','data':svg}],
                        'activities':activities})
    return {'kind':'learnit-course-package','schema_version':'learnit.import.v1.1','packageId':'rc686-media-scale-100x10',
            'source':'automated realistic media scale probe','assets':[],'generation_report':{'course_count':course_count,'activity_count':course_count*activities_per_course},'courses':courses}


def main() -> int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    html=(ROOT/'dist'/'learnit.html').read_text(encoding='utf-8')
    payload=make_package(); text=json.dumps(payload,ensure_ascii=False,separators=(',',':'))
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(12000)
            page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content(html,wait_until='domcontentloaded');page.wait_for_timeout(350)
            result=page.evaluate('''text=>{
              const r=window.__LEARNIT_TEST__.runtime;
              const t0=performance.now();const plan=r.contentStore.previewImport(text,{});const planMs=performance.now()-t0;
              const t1=performance.now();const applied=r.contentStore.applyImportPlan(plan);const applyMs=performance.now()-t1;
              const t2=performance.now();r.go('library');const renderMs=performance.now()-t2;
              return {planMs,applyMs,renderMs,plan:{ok:plan.ok,count:plan.count,totalActivities:plan.totalActivities,blockers:plan.blockers,warnings:plan.warnings},applied:applied.report||applied,total:r.contentStore.allCourses().length,rows:r.root.querySelectorAll('[data-course-row]').length,storage:window.__LEARNIT_TEST__.performanceReport().storage};
            }''',text)
            add('realistic-package-size',500_000<=len(text.encode('utf-8'))<=3_000_000,f'{len(text.encode("utf-8"))} bytes')
            add('media-scale-plan-valid',result['plan']['ok'] and result['plan']['count']==100 and result['plan']['totalActivities']==1000,result['plan'])
            add('media-scale-plan-budget',result['planMs']<3000,f"{result['planMs']:.1f} ms")
            add('media-scale-apply',result['applied'].get('appliedCourses')==100 and result['applied'].get('totalActivities')==1000,result['applied'])
            add('media-scale-apply-budget',result['applyMs']<3000,f"{result['applyMs']:.1f} ms")
            add('media-scale-library-render',result['total']>=103 and result['rows']>=100,result)
            add('media-scale-library-budget',result['renderMs']<1500,f"{result['renderMs']:.1f} ms")
            add('media-scale-storage-budget',result['storage']['checks']['imported']['ok'],result['storage'])

            page.locator('.route-panel[data-route="library"] #librarySearch').fill('Parcours média 042');page.wait_for_timeout(250)
            row=page.locator('.route-panel[data-route="library"] [data-course-row]').first
            add('media-scale-search',row.count()==1 and '042' in (row.text_content() or ''),row.text_content() if row.count() else 'missing')
            row.locator('.book-open-main').click();page.wait_for_timeout(180)
            jacket=page.locator('.book-detail-shell .jacket-asset svg').first
            add('media-scale-jacket-sanitized',jacket.count()==1 and jacket.get_attribute('role')=='img' and jacket.get_attribute('data-learnit-media')=='svg',jacket.evaluate('(e)=>e.outerHTML')[:500] if jacket.count() else 'missing')
            page.evaluate('''()=>{const r=window.__LEARNIT_TEST__.runtime;const item=r.contentStore.courseList().find(c=>c.title==='Parcours média 042');r.contentStore.setActiveCourse(item.courseId);r.appState.alignWithContent();r.go('learn');r.session.start();r.go('session');}''')
            page.wait_for_timeout(250)
            media=page.locator('[data-learnit-media="svg"]').first
            html_media=media.evaluate('(e)=>e.outerHTML').lower() if media.count() else ''
            add('media-scale-activity-renders',media.count()==1 and '<script' not in html_media and ' onload=' not in html_media and 'style=' not in html_media,html_media[:500])
            rollback=page.evaluate('()=>window.__LEARNIT_TEST__.runtime.contentStore.rollbackImport()')
            add('media-scale-rollback',rollback.get('ok') is True and page.evaluate('()=>window.__LEARNIT_TEST__.runtime.contentStore.imported.length')==0,rollback)
            add('no-browser-errors',not errors,' | '.join(errors[-10:]))
        finally:
            browser.close()
    ok=all(row['ok'] for row in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc686.realistic_media_scale.v1','ok':ok,'packageBytes':len(text.encode('utf-8')),'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(row['ok'] for row in rows),'total':len(rows),'packageBytes':len(text.encode('utf-8')),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__':
    raise SystemExit(main())
