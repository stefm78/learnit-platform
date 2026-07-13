#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'/'browser_scale_progress_import_report.json'


def make_package(start:int,count:int,activities_per_course:int=10)->dict:
    courses=[]
    for i in range(start,start+count):
        objective=f'Objective {i}'
        activities=[]
        for j in range(activities_per_course):
            role='validation' if j==activities_per_course-1 else ('remediation' if j==activities_per_course-2 else 'practice')
            phase='validation' if role=='validation' else ('remediation' if role=='remediation' else ('application' if j>2 else 'comprehension'))
            activities.append({
                'id':f'scale-{i}-q{j}', 'type':'qcm', 'objective':objective,
                'question':f'Question unique {i}-{j} ?', 'choices':['Correct','Wrong'], 'answer':0,
                'why':'Correct is expected.', 'remediation':'Review the objective with another example.',
                'difficulty':'medium' if j>4 else 'easy', 'learning_phase':phase,
                'assessment_role':role, 'common_errors':['Choose the distractor.']
            })
        courses.append({'schemaVersion':'learnit-content-v2','contentVersion':f'scale-{i}','title':f'Scale course {i:03d}','sequence':f'Collection scale {i//10:02d}','objectives':[objective],'activities':activities})
    return {'kind':'learnit-course-package','schema_version':'learnit.import.v1.1','packageId':f'rc612-scale-{start}-{count}','source':'automated scale fixture','assets':[],'generation_report':{'activity_count':count*activities_per_course},'courses':courses}


def main()->int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    html=(ROOT/'dist/learnit.html').read_text(encoding='utf-8')
    entries=[
        {'name':'scale-a.json','text':json.dumps(make_package(0,50),ensure_ascii=False)},
        {'name':'scale-b.json','text':json.dumps(make_package(50,50),ensure_ascii=False)},
    ]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':1440,'height':900})
            page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content(html,wait_until='domcontentloaded');page.wait_for_timeout(350)
            page.wait_for_function('() => !!window.__LEARNIT_TEST__?.runtime')

            plan=page.evaluate('''entries=>window.__LEARNIT_TEST__.runtime.contentStore.planImportTexts(entries,{collisionPolicy:'rename'})''',entries)
            add('multifile-plan-valid',plan.get('ok') and len(plan.get('files',[]))==2 and plan.get('count')==100 and plan.get('totalActivities')==1000,json.dumps({k:plan.get(k) for k in ['ok','files','count','totalActivities','counts']},ensure_ascii=False))
            add('multifile-plan-no-write',page.evaluate('window.__LEARNIT_TEST__.runtime.contentStore.imported.length')==0)

            fault=page.evaluate('''plan=>window.__LEARNIT_TEST__.runtime.contentStore.applyImportPlan(plan,{faultAt:'after-imported-write'})''',plan)
            add('transaction-fault-rolls-back',not fault.get('ok') and fault.get('rolledBack') is True and page.evaluate('window.__LEARNIT_TEST__.runtime.contentStore.imported.length')==0,json.dumps(fault,ensure_ascii=False)[:500])
            add('transaction-marker-cleared',page.evaluate('window.__LEARNIT_TEST__.runtime.contentStore.recoverInterruptedImport()') is False)

            result=page.evaluate('plan=>window.__LEARNIT_TEST__.runtime.contentStore.applyImportPlan(plan)',plan)
            add('large-import-applied',bool(result.get('ok')) and result.get('report',{}).get('appliedCourses')==100 and result.get('report',{}).get('totalActivities')==1000,json.dumps(result.get('report',{}),ensure_ascii=False)[:800])
            add('large-import-persisted',page.evaluate('window.__LEARNIT_TEST__.runtime.contentStore.loadImportedCourses().length')==100)

            collision_text=json.dumps(make_package(42,1),ensure_ascii=False)
            collision_plans=page.evaluate('''text=>{
              const s=window.__LEARNIT_TEST__.runtime.contentStore;
              return Object.fromEntries(['rename','replace','skip','reject'].map(policy=>[policy,s.previewImport(text,{collisionPolicy:policy})]));
            }''',collision_text)
            add('collision-rename-planned',collision_plans['rename']['ok'] and collision_plans['rename']['counts'].get('rename')==1)
            add('collision-replace-planned',collision_plans['replace']['ok'] and collision_plans['replace']['counts'].get('replace')==1)
            add('collision-skip-planned',collision_plans['skip']['ok'] and collision_plans['skip']['counts'].get('skip')==1 and len(collision_plans['skip']['operations'])==0)
            add('collision-reject-blocks',not collision_plans['reject']['ok'] and any(row.get('code')=='collision-rejected' for row in collision_plans['reject']['blockers']))

            perf=page.evaluate('''()=>{const r=window.__LEARNIT_TEST__.runtime;const t=performance.now();r.go('library');return {ms:performance.now()-t,total:r.contentStore.allCourses().length};}''')
            page.wait_for_timeout(400)
            count=page.locator('.route-panel[data-route="library"] [data-course-row]').count()
            add('large-library-renders',count>=100 and perf['total']>=100,f'rows={count} total={perf["total"]} renderMs={perf["ms"]:.1f}')
            add('large-library-render-budget',perf['ms']<1500,f'{perf["ms"]:.1f}ms')
            page.locator('.route-panel[data-route="library"] #librarySearch').fill('Scale course 042');page.wait_for_timeout(250)
            visible=page.locator('.route-panel[data-route="library"] [data-course-row]')
            add('large-library-search-precise',visible.count()==1 and 'Scale course 042' in (visible.first.text_content() or ''),str(visible.count()))

            isolation=page.evaluate('''()=>{
              const r=window.__LEARNIT_TEST__.runtime;const ids=r.contentStore.courseList().filter(x=>x.imported).map(x=>x.courseId);
              const a=ids[0],b=ids[1];r.contentStore.setActiveCourse(a);r.appState.alignWithContent();r.session.start();r.answer.reset();r.answer.selectQcm(1);r.answer.validate();
              const pa=r.appState.courseProgress(a),pb=r.appState.courseProgress(b);return {a,b,pa,pb};
            }''')
            add('imported-course-progress-isolated',len(isolation.get('pa',{}))==1 and len(isolation.get('pb',{}))==0,json.dumps(isolation,ensure_ascii=False)[:900])
            rollback=page.evaluate('window.__LEARNIT_TEST__.runtime.contentStore.rollbackImport()')
            add('large-import-rollback',bool(rollback.get('ok')) and page.evaluate('window.__LEARNIT_TEST__.runtime.contentStore.imported.length')==0,json.dumps(rollback,ensure_ascii=False))
            add('no-browser-errors',not errors,' | '.join(errors[-10:]))
        finally: browser.close()
    ok=all(x['ok'] for x in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps({'schema':'learnit.rc612.scale_progress_import.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(x['ok'] for x in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
