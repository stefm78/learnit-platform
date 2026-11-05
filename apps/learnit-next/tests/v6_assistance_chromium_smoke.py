"""Synthetic isolated Chromium smoke; NOT the production learner UI qualification."""
import contextlib, http.server, json, socketserver, threading, time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[3]
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**k): super().__init__(*a,directory=str(ROOT),**k)
    def log_message(self,*a): pass
class S(socketserver.ThreadingMixIn,http.server.HTTPServer): daemon_threads=True

def main():
    tests=[]
    with S(('127.0.0.1',0),H) as server:
        thr=threading.Thread(target=server.serve_forever,daemon=True);thr.start()
        origin=f'http://127.0.0.1:{server.server_port}'
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            c=browser.new_context();page=c.new_page();page.goto(origin)
            def check(label,js):
                got=page.evaluate(js)
                ok=bool(got)
                tests.append(dict(name=label,status='PASS' if ok else 'FAIL'))
                print(label,'PASS' if ok else 'FAIL')
                if not ok: raise RuntimeError(label)
            init="""async () => {
                const m=await import('/apps/learnit-next/src/core/v6_assistance.js');
                const d=await import('/apps/learnit-next/src/adapters/v6_assistance_indexeddb.js');
                const port=d.createV6AssistanceIndexedDbCAS({dbName:'learnit-v6-r1-synthetic-only'});
                const svc=m.createV6AssistanceService(port,{authorize:x=>x.parcoursAuthorized===true});
                const scope={contract:'learnit.kit.v6',sessionId:'synsession_123456',activityId:'synactivity_12345',packageRevisionDigest:'sha256:'+'a'.repeat(64),activityRevisionDigest:'sha256:'+'b'.repeat(64),hints:['first','<img src=x onerror=alert(1)>','third'],parcoursAuthorized:true};
                window.__test={svc,scope,port,m};return true;
            }"""
            check('browser_module_import_and_idb_open',init)
            check('idb_no_uncommitted_hint_leak',"""async () => {
                const {svc,scope}=window.__test;
                let x=await svc.requestNext(scope,'e41026be-146f-4b98-a532-20484884b931');
                let v=await svc.readAuthorizedView(scope);
                return x.rank===0 && !x.acknowledged && v.visibleCount===0 && v.hints.length===0;
            }""")
            check('idb_persist_before_reveal',"""async () => {
                const {svc,scope}=window.__test;
                const r=await svc.acknowledge(scope,'e41026be-146f-4b98-a532-20484884b931');
                const v=await svc.readAuthorizedView(scope);
                return r.acknowledged===true && v.visibleCount===1 && v.hints[0]==='first';
            }""")
            page.reload();check('reload_recovers_acknowledged_prefix',init)
            check('idb_replay_after_reload',"""async () => {
                const {svc,scope}=window.__test;
                let v=await svc.readAuthorizedView(scope);
                let d=await svc.requestNext(scope,'e41026be-146f-4b98-a532-20484884b931');
                return v.visibleCount===1 && d.acknowledged===true && d.rank===0;
            }""")
            check('idb_concurrency_exact_single_authorization',"""async () => {
                const {svc,scope}=window.__test;
                const ids=['b47750b6-7929-488d-98d7-e6dfec04c1f5','d5d54391-bef7-47ee-8b04-b68b99412c5d'];
                const all=await Promise.allSettled(ids.map(id=>svc.requestNext(scope,id)));
                const ok=all.filter(x=>x.status==='fulfilled');const bad=all.filter(x=>x.status==='rejected');
                window.__test.pendingId=ok[0]?.value.requestId;
                return ok.length===1&&bad.length===1&&ok[0].value.rank===1;
            }""")
            check('idb_xss_hint_treated_as_text_only',"""async () => {
                const {svc,scope,pendingId}=window.__test;await svc.acknowledge(scope,pendingId);
                let v=await svc.readAuthorizedView(scope);
                let root=document.createElement('div');for(let hint of v.hints){let p=document.createElement('p');p.textContent=hint;root.append(p)}
                document.body.append(root);
                return v.visibleCount===2 && root.querySelectorAll('img,script').length===0 && root.textContent.includes('<img src=x onerror=alert(1)>');
            }""")
            check('idb_source_digest_mutation_refused',"""async () => {
                const {svc,scope}=window.__test;
                try{await svc.readAuthorizedView({...scope,activityRevisionDigest:'sha256:'+'f'.repeat(64)});return false}
                catch(e){return e.code==='SOURCE_BINDING_CHANGED'}
            }""")
            check('idb_v5_leak_refused',"""async () => {
                const {svc,scope}=window.__test;
                try{await svc.readAuthorizedView({...scope,contract:'learnit.kit.v5'});return false}
                catch(e){return e.code==='V6_CONTRACT_REQUIRED'}
            }""")
            browser.close()
        server.shutdown()
    # Native candidate learner (real import/session APIs, disposable synthetic V6 kit).
    import importlib.util, os, re
    artifact_text=os.environ.get('LEARNIT_V6_ARTIFACT')
    if artifact_text:
        artifact=Path(artifact_text)
        if not artifact.is_file():
            raise AssertionError('LEARNIT_V6_ARTIFACT_NOT_FOUND')
        spec=importlib.util.spec_from_file_location('pr514_v6_consumption_fixture', ROOT/'apps/learnit-next/tests/passage_v6_consumption.py')
        if not spec or not spec.loader:
            raise AssertionError('V6_CONSUMPTION_FIXTURE_LOADER_UNAVAILABLE')
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fixture=mod.package()
        with mod.serve(artifact) as url, sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page()
            page.goto(url)
            page.wait_for_function('()=>Boolean(window.__LEARNIT_NEXT_TEST__?.importPackage)')
            mod.call(page,'resetNextData')
            result=mod.call(page,'importPackage',[fixture])
            course_id=result['courses'][0]['courseInstallId']
            first=mod.call(page,'startCourse',[course_id])
            first_id=first.get('v6AssistanceSessionId')
            assert isinstance(first_id,str) and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f-]{27}',first_id,re.I),first
            tests.append(dict(name='real_v6_learner_session_uuid_created',status='PASS'))
            print('real_v6_learner_session_uuid_created PASS')
            page.reload()
            page.wait_for_function('()=>Boolean(window.__LEARNIT_NEXT_TEST__?.resumeActiveCourse)')
            resumed=mod.call(page,'resumeActiveCourse')
            assert resumed.get('v6AssistanceSessionId')==first_id,(resumed,first_id)
            tests.append(dict(name='real_v6_learner_uuid_persists_reload',status='PASS'))
            print('real_v6_learner_uuid_persists_reload PASS')
            fresh=mod.call(page,'startCourse',[course_id])
            assert fresh.get('v6AssistanceSessionId')!=first_id,(fresh,first_id)
            tests.append(dict(name='real_v6_new_course_session_uuid_rotates',status='PASS'))
            print('real_v6_new_course_session_uuid_rotates PASS')
            browser.close()
    print('CHROMIUM_SUMMARY',json.dumps({'passed':sum(x['status']=='PASS' for x in tests),'total':len(tests)}))
    import os
    report_path=Path(os.environ.get('LEARNIT_V6_CHROMIUM_REPORT', '/tmp/LEARNIT_V6_R1_CHROMIUM_SMOKE_RESULTS.json'))
    report_path.write_text(json.dumps({'tests':tests,'synthetic_only':True},indent=2)+'\n')
if __name__=='__main__':main()
