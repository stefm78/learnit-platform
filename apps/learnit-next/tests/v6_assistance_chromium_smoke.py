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
    if artifact_text:
        run_isolated_functional_demo(tests, Path(artifact_text))
    print('CHROMIUM_SUMMARY',json.dumps({'passed':sum(x['status']=='PASS' for x in tests),'total':len(tests)}))
    import os
    report_path=Path(os.environ.get('LEARNIT_V6_CHROMIUM_REPORT', '/tmp/LEARNIT_V6_R1_CHROMIUM_SMOKE_RESULTS.json'))
    report_path.write_text(json.dumps({'tests':tests,'synthetic_only':True},indent=2)+'\n')
DEMO_BOOTSTRAP = "async ({courseId, activityId, hints, moduleSources}) => {\n  const api=window.__LEARNIT_NEXT_TEST__;\n  // The built learner enforces connect-src 'none': do not request source modules.\n  // Inject only audited exact-PR source bytes from the CI checkout as CSP-allowed blob modules.\n  const blobUrl=code=>URL.createObjectURL(new Blob([code],{type:'text/javascript'}));\n  const domainUrl=blobUrl(moduleSources.domain), persistenceUrl=blobUrl(moduleSources.persistence);\n  const [domain,persistence]=await Promise.all([import(domainUrl),import(persistenceUrl)]);\n  URL.revokeObjectURL(domainUrl);URL.revokeObjectURL(persistenceUrl);\n  const session=await api.getSession();\n  const installed=await api.getAtlasCourseContext(courseId);\n  const activity=installed.course.activities.find(x=>x.activityRevisionId===activityId);\n  if (!session?.v6AssistanceSessionId||!activity||session.currentActivity?.activityRevisionId!==activityId)\n    throw Error('SYNTHETIC_DEMO_SESSION_OR_ACTIVITY_MISMATCH');\n  const ctx={contract:'learnit.kit.v6',sessionId:session.v6AssistanceSessionId,\n    activityId,packageRevisionDigest:installed.packageDigest,\n    activityRevisionDigest:activity.activityRevisionDigest,hints};\n  const port=persistence.createV6AssistanceIndexedDbCAS({\n    dbName:'learnit-v6-pr514-isolated-demo-only'});\n  const svc=domain.createV6AssistanceService(port,{\n    authorize:async (c,purpose)=>{\n      const live=await api.getSession();\n      const source=await api.getAtlasCourseContext(courseId);\n      const matched=source.course.activities.find(x=>x.activityRevisionId===c.activityId);\n      const same=live?.v6AssistanceSessionId===c.sessionId &&\n        source.packageDigest===c.packageRevisionDigest &&\n        matched?.activityRevisionDigest===c.activityRevisionDigest;\n      return Boolean(same&&(purpose==='read'||live.currentActivity?.activityRevisionId===c.activityId));\n    }\n  });\n  const readView=async()=>{\n    const value=await svc.readAuthorizedView(ctx);\n    const live=await api.getSession();\n    return {...value,canRequest:live?.v6AssistanceSessionId===ctx.sessionId &&\n      live.currentActivity?.activityRevisionId===ctx.activityId};\n  };\n  const request=async()=>{\n    const live=await api.getSession();\n    if(live?.v6AssistanceSessionId!==ctx.sessionId||\n       live.currentActivity?.activityRevisionId!==ctx.activityId)\n      throw Error('PARCOURS_POST_ANSWER_DENIED');\n    const requestId=crypto.randomUUID();\n    await svc.requestNext(ctx,requestId);\n    await svc.acknowledge(ctx,requestId);\n  };\n  const presenter=api.createV6AssistancePresenter({\n    totalHints:hints.length,readView,requestNext:request\n  });\n  const nativeForm=api.renderActivityPresentation(session.currentActivity.presentation);\n  const stage=document.createElement('section');\n  stage.setAttribute('data-v6-native-test-stage','true');\n  stage.append(nativeForm);\n  document.body.append(stage);\n  nativeForm.after(presenter.element);\n  window.__isolatedV6Demo={ctx,port,svc,presenter,render:presenter.refresh,request};\n  return presenter.refresh();\n}"

def run_isolated_functional_demo(tests, artifact):
    """In-browser fixture overlay, NOT shipped learner UI or approved kit hint source."""
    import importlib.util
    spec=importlib.util.spec_from_file_location('pr514_demo_fixture', ROOT/'apps/learnit-next/tests/passage_v6_consumption.py')
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fixture=mod.package()
    qcm=fixture['courses'][0]['activities'][2]
    class DemoH(H):
        def do_GET(self):
            if self.path.split('?',1)[0]=='/__learnit_pr514_demo.html':
                raw=artifact.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(raw)))
                self.send_header('Cache-Control','no-store')
                self.end_headers()
                self.wfile.write(raw)
                return
            return super().do_GET()
    def record(name, pass_condition):
        ok=bool(pass_condition)
        tests.append({'name':name,'status':'PASS' if ok else 'FAIL'})
        print(name, 'PASS' if ok else 'FAIL', flush=True)
        if not ok: raise AssertionError(name)
    with S(('127.0.0.1',0),DemoH) as server:
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        url=f'http://127.0.0.1:{server.server_port}/__learnit_pr514_demo.html'
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            context=browser.new_context()
            page=context.new_page();page.goto(url)
            page.wait_for_function('()=>Boolean(window.__LEARNIT_NEXT_TEST__?.importPackage)')
            mod.call(page,'resetNextData')
            imported=mod.call(page,'importPackage',[fixture])
            course_id=imported['courses'][0]['courseInstallId']
            first=mod.call(page,'startCourse',[course_id])
            record('demo_native_v6_session_created',bool(first.get('v6AssistanceSessionId')))
            for activity in fixture['courses'][0]['activities'][:2]:
                mod.call(page,'answer',[activity['activityRevisionId'],mod.answer(activity)])
            current=mod.call(page,'getSession')
            record('demo_real_qcm_fixture_active',current['currentActivity']['activityRevisionId']==qcm['activityRevisionId'])
            hints=['Indice 1 : relisez la question.',
                   '<img src=x onerror=alert(1)>',
                   'Indice 3 : vérifiez les réponses possibles.']
            args={'courseId':course_id,'activityId':qcm['activityRevisionId'],'hints':hints,
                'moduleSources': {
                  'domain':(ROOT/'apps/learnit-next/src/core/v6_assistance.js').read_text(encoding='utf-8'),
                  'persistence':(ROOT/'apps/learnit-next/src/adapters/v6_assistance_indexeddb.js').read_text(encoding='utf-8')}}
            initial=page.evaluate(DEMO_BOOTSTRAP,args)
            record('demo_starts_with_no_acquired_hints',initial['visible']==0 and initial['active'])
            record('demo_native_renderer_component_attached_to_qcm',
                   page.locator('[data-activity-presentation="qcm"] + [data-v6-assistance-candidate]').count()==1)
            record('demo_renderer_has_accessible_live_status',
                   page.locator('[data-v6-assistance-status][role="status"][aria-live="polite"]').count()==1)
            page.locator('[data-v6-assistance-next]').click()
            page.wait_for_function("()=>document.querySelectorAll('[data-v6-assistance-hint]').length===1")
            record('demo_click_commits_then_displays_first_hint',
                   page.locator('[data-v6-assistance-hint]').count()==1)
            page.reload();page.wait_for_function('()=>Boolean(window.__LEARNIT_NEXT_TEST__?.resumeActiveCourse)')
            resumed=mod.call(page,'resumeActiveCourse')
            record('demo_real_v6_uuid_resumed',resumed.get('v6AssistanceSessionId')==first['v6AssistanceSessionId'])
            restored=page.evaluate(DEMO_BOOTSTRAP,args)
            record('demo_reload_restores_acquired_hint',restored['visible']==1)
            page.locator('[data-v6-assistance-next]').click()
            page.wait_for_function("()=>document.querySelectorAll('[data-v6-assistance-hint]').length===2")
            record('demo_second_hint_rendered_as_safe_text',
                   page.locator('[data-v6-assistance-candidate] img').count()==0 and
                   '<img src=x' in page.locator('[data-v6-assistance-hint]').nth(1).inner_text())
            page.locator('[data-v6-assistance-next]').click()
            page.wait_for_function("()=>document.querySelectorAll('[data-v6-assistance-hint]').length===3")
            record('demo_three_indice_limit_enforced',
                   page.locator('[data-v6-assistance-next]').is_disabled())
            result=mod.call(page,'answer',[qcm['activityRevisionId'],mod.answer(qcm)])
            locked=page.evaluate("async()=>await window.__isolatedV6Demo.render()")
            record('demo_postanswer_preserves_acquired_hints_and_disables_request',
                   locked['visible']==3 and not locked['active'] and
                   page.locator('[data-v6-assistance-next]').is_disabled())
            refused=page.evaluate("""async()=>{
                const d=window.__isolatedV6Demo;
                try{await d.svc.requestNext(d.ctx,crypto.randomUUID());return null}
                catch(e){return e.code||e.message}
            }""")
            record('demo_direct_postanswer_call_denied',refused=='PARCOURS_AUTHORIZATION_DENIED')
            record('demo_score_unchanged_assisted_nonautonomous_derived_only',
                   result.get('scored') is True and result.get('correct') is True and locked['visible']>0)
            previous=page.evaluate("""async()=>{
                const d=window.__isolatedV6Demo;
                return d.port.read('learnit.v6.assistance-journal.v1:'+d.ctx.sessionId+':'+d.ctx.activityId)
            }""")
            fresh=mod.call(page,'startCourse',[course_id])
            record('demo_new_session_uuid_rotates_again',
                   fresh.get('v6AssistanceSessionId')!=first['v6AssistanceSessionId'])
            new=page.evaluate("""async()=>{
                const old=window.__isolatedV6Demo,api=window.__LEARNIT_NEXT_TEST__;
                const live=await api.getSession();
                const next={...old.ctx,sessionId:live.v6AssistanceSessionId,
                    activityId:live.currentActivity.activityRevisionId};
                const source=await api.getAtlasCourseContext(live.courseInstallId);
                next.activityRevisionDigest=source.course.activities.find(
                    x=>x.activityRevisionId===next.activityId).activityRevisionDigest;
                return {
                    old:await old.port.read('learnit.v6.assistance-journal.v1:'+old.ctx.sessionId+':'+old.ctx.activityId),
                    fresh:await old.port.read('learnit.v6.assistance-journal.v1:'+next.sessionId+':'+next.activityId)
                }
            }""")
            record('demo_new_session_fresh_hints_and_old_history_retained',
                   new['fresh']['state'] is None and new['old']==previous and
                   len(previous['state']['events'])==6)
            browser.close()
        server.shutdown();worker.join(5)

if __name__=='__main__':main()
