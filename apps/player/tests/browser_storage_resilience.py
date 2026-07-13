#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from support import ROOT

OUT = ROOT / 'reports' / 'browser_storage_resilience_report.json'


def main() -> int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    html=(ROOT/'dist'/'learnit.html').read_text(encoding='utf-8')
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    package={'kind':'learnit-course-package','schema_version':'learnit.import.v1.1','packageId':'quota-probe','source':'automated storage resilience probe','assets':[],'generation_report':{},'courses':[{'schemaVersion':'learnit-content-v2','contentVersion':'quota-probe-v1','title':'Quota probe','sequence':'Probe','objectives':['Tester le rollback'],'activities':[{'id':'q1','type':'qcm','objective':'Tester le rollback','question':'Le rollback doit-il préserver les données ?','choices':['Oui','Non'],'answer':0,'why':'Une transaction atomique revient au snapshot.','remediation':'Relire la règle de transaction.'}]}]}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':900,'height':800}); page.set_default_timeout(8000)
            page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content(html,wait_until='domcontentloaded'); page.wait_for_timeout(350)
            result=page.evaluate('''payload=>{
              const runtime=window.__LEARNIT_TEST__.runtime;
              const api=window.__LEARNIT_TEST__;
              const before=api.storageRead('learnit_imported_courses_v1')||'[]';
              const beforeLast=api.storageRead('learnit_import_last_applied_v1')||'';
              const plan=runtime.contentStore.previewImportFiles([{name:'quota.json',text:JSON.stringify(payload)}],{});
              const injected=api.storageFaultOnce({operation:'setItem',key:'learnit_imported_courses_v1',name:'QuotaExceededError',message:'Synthetic quota limit'});
              const applied=runtime.contentStore.applyImportPlan(plan);
              return {
                planOk:plan.ok,
                applied,
                injected,
                before,
                after:api.storageRead('learnit_imported_courses_v1')||'[]',
                beforeLast,
                afterLast:api.storageRead('learnit_import_last_applied_v1')||'',
                transaction:api.storageRead('learnit_import_transaction_v1')||'',
                storageReport:api.storageReport(),
                runtimeImported:runtime.contentStore.imported.map(c=>c.title)
              };
            }''',package)
            add('quota-probe-plan-valid',result.get('planOk') is True,result)
            add('quota-write-fault-injected',result.get('injected') is True,result)
            applied=result.get('applied') or {}
            add('quota-fault-reported',applied.get('ok') is False and applied.get('rolledBack') is True and 'quota' in str(applied.get('error','')).lower(),applied)
            add('quota-rollback-restores-imported',result.get('after')==result.get('before') and result.get('runtimeImported')==[],result)
            add('quota-rollback-restores-last-report',result.get('afterLast')==result.get('beforeLast'),result)
            add('quota-transaction-marker-cleared',result.get('transaction')=='',result)

            recovery=page.evaluate('''()=>{
              const api=window.__LEARNIT_TEST__, runtime=api.runtime;
              const importedKey='learnit_imported_courses_v1', txKey='learnit_import_transaction_v1';
              const baseline=api.storageRead(importedKey)||'[]';
              api.storageWrite(importedKey,JSON.stringify([{schemaVersion:'learnit-content-v2',contentVersion:'partial',title:'Partial write',objectives:['x'],activities:[{id:'x',type:'qcm',question:'x',choices:['a','b'],answer:0}]}]));
              api.storageWrite(txKey,JSON.stringify({snapshot:{
                learnit_imported_courses_v1:baseline,
                learnit_import_history_v1:api.storageRead('learnit_import_history_v1'),
                learnit_import_last_applied_v1:api.storageRead('learnit_import_last_applied_v1'),
                learnit_active_course_v1:api.storageRead('learnit_active_course_v1')
              }}));
              const recovered=runtime.contentStore.recoverInterruptedImport();
              runtime.contentStore.imported=runtime.contentStore.loadImportedCourses();
              return {baseline,recovered,imported:api.storageRead(importedKey)||'[]',transaction:api.storageRead(txKey)||'',runtimeImported:runtime.contentStore.imported.map(c=>c.title)};
            }''')
            add('interrupted-import-auto-recovered',recovery['recovered'] and recovery['imported']==recovery['baseline'] and recovery['transaction']=='' and recovery['runtimeImported']==[],recovery)

            state=page.evaluate('''()=>{const api=window.__LEARNIT_TEST__;api.storageWrite('learnit_clean_state_v2','{broken-json');const loaded=api.runtime.appState.load();return {schema:loaded.stateSchemaVersion,recovery:JSON.parse(api.storageRead('learnit_recovery_report_v1')||'{}')};}''')
            add('corrupt-state-resets-safely',state.get('schema')==4 and state.get('recovery',{}).get('kind')=='corrupt-state-reset',state)
            perf=page.evaluate('()=>window.__LEARNIT_TEST__.performanceReport().storage')
            add('storage-budgets-observable',all(row.get('ok') for row in perf.get('checks',{}).values()),perf)
            add('no-unexpected-browser-errors',not errors,' | '.join(errors[-10:]))
        finally:
            browser.close()
    ok=all(row['ok'] for row in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc685.storage_resilience_matrix.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(row['ok'] for row in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__':
    raise SystemExit(main())
