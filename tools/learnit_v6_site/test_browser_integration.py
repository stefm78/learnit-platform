#!/usr/bin/env python3
"""LearnIT v6 governed integrated-browser CI test based on locally passing R5.

Input: validated 52-file site and site-manifest from deterministic assembler.
The pinned v2 fixture is built locally from frozen Git object, not fetched from
live Pages. Tests synthetic v2 to v3 migration, blocked upgrade, 503 recovery,
8 V6 activity types and negative cases, basic 2-viewport keyboard checks.
No real learner data, remote writes or Pages credentials. Bounded CI only.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.util
import shutil
import copy
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PIN = 'c7f7587c9e5beb29a123e5139c17b6448229a0cc'
V2_BYTES = 366412
V2_SHA = '4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7'
V6_BYTES = 627042
V6_SHA = '92115133901b50509880c2e7ad9d76816f74e30443b5f52d1cf35d935dac953b'
FIX_BLOB = '508abb2085ca092527fb25b4c3dcb5e6b945f1a2'
FIX_SHA = '6b01a106e8de229fe0e67c2cbcda64eeb2d1f247b520defd6c24bc4446c2f1f9'
PREFIX = '/learnit-platform/'
DB_NAME = 'learnit_next_v1'
RECOVERY = PREFIX + 'recovery/v3/'
SNAPSHOT_JS = r'''async () => {
  const dbs = await indexedDB.databases();
  if (!dbs.some(d => d.name === 'learnit_next_v1')) throw Error('LearnIT DB missing');
  const db = await new Promise((resolve,reject)=> {
    const request=indexedDB.open('learnit_next_v1');
    const timer=setTimeout(()=>reject(Error('HOLD: IDB snapshot open exceeded 12s')),12000);
    request.onupgradeneeded=()=>{clearTimeout(timer);reject(Error('Unexpected upgrade during snapshot'))};
    request.onsuccess=()=>{clearTimeout(timer);resolve(request.result)};
    request.onerror=()=>{clearTimeout(timer);reject(request.error||Error('DB open error'))};
  });
  try {
    const stores={};
    const read = request => new Promise((resolve,reject)=>{
      request.onsuccess=()=>resolve(request.result);
      request.onerror=()=>reject(request.error||Error('IDB read error'));
    });
    for(const store of Array.from(db.objectStoreNames).sort()) {
      const tx=db.transaction(store,'readonly');
      const obj=tx.objectStore(store);
      const [keys,values]=await Promise.all([read(obj.getAllKeys()),read(obj.getAll())]);
      stores[store]=keys.map((key,i)=>({key,value:values[i]}));
    }
    const local={};
    for(let i=0;i<localStorage.length;i++){
      const k=localStorage.key(i);
      if(k.startsWith('learnit.next.v1.')) local[k]=localStorage.getItem(k);
    }
    return {version:db.version,stores,local};
  } finally { db.close(); }
}'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def git(repo: Path, *args: str, binary: bool = False):
    p = subprocess.run(['git', *args], cwd=repo, capture_output=True, check=False)
    check(p.returncode == 0,
          f'HOLD: git {" ".join(args)}: {p.stderr.decode("utf-8","replace")[-350:]}')
    return p.stdout if binary else p.stdout.decode('utf-8', 'replace').strip()


def locally_built_v2(repo: Path, scratch: Path) -> bytes:
    """Rebuild exact frozen learner from Git without contacting live Pages."""
    stable = '4eebdef9fb0014c2e4a965e0c1e78d127dd712f4'
    wt = scratch / 'frozen-v2'
    artifact = scratch / 'seed-v2.html'
    args = ['git','-c','core.autocrlf=false','-c','core.eol=lf',
            'worktree','add','--detach',str(wt),stable]
    p = subprocess.run(args,cwd=repo,capture_output=True,text=True)
    check(p.returncode == 0,'HOLD: cannot materialize frozen v2 source '+p.stderr[-500:])
    try:
        p = subprocess.run([sys.executable,'-B',str(wt/'apps/learnit-next/build.py'),
                            '--output',str(artifact)],cwd=wt,capture_output=True,text=True)
        check(p.returncode == 0,'HOLD: cannot rebuild v2 '+p.stderr[-800:])
        data = artifact.read_bytes()
        check(len(data)==V2_BYTES and sha(data)==V2_SHA,
              'HOLD: locally rebuilt v2 bytes/SHA mismatch')
        return data
    finally:
        subprocess.run(['git','worktree','remove','--force',str(wt)],cwd=repo,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)



def canonical_record(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def assert_preserved(before: dict, after: dict) -> None:
    for name, records in before['stores'].items():
        check(name in after['stores'], 'HOLD: lost IndexedDB store ' + name)
        old = {canonical_record(e['key']): canonical_record(e['value']) for e in records}
        new = {canonical_record(e['key']): canonical_record(e['value']) for e in after['stores'][name]}
        for key, value in old.items():
            check(key in new and new[key] == value,
                  'HOLD: existing IndexedDB row missing/modified in store ' + name)
    for key, value in before['local'].items():
        check(after['local'].get(key) == value, 'HOLD: localStorage key modified ' + key)


def summarize(snapshot: dict) -> dict:
    return {'version': snapshot['version'],
            'stores': {name: {'count': len(rows),
                              'sha256': sha(canonical_record(sorted(rows, key=lambda e: canonical_record(e['key']))).encode('utf-8'))}
                       for name, rows in snapshot['stores'].items()},
            'localStorageKeys': sorted(snapshot['local'])}


def main() -> int:
    started = time.perf_counter()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--site', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--repo', type=Path, default=Path.cwd())
    ap.add_argument('--browser', choices=('chromium','msedge'), default='chromium',
                    help='Chromium for CI; msedge for already-qualified local Windows Edge')
    args = ap.parse_args()
    out = Path(tempfile.mkdtemp(prefix='learnit-s3-local-', dir=Path.home()))
    report_path = out / 'S3_CONSOLIDATED_R5.json'
    report = {
        'schema': 'learnit.v6.site.ci-browser-integration.v1',
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'started_at_local': datetime.now().astimezone().isoformat(),
        'mode': 'PINNED_GIT_LOCALHOST_DISPOSABLE_CHROMIUM_CI_NO_REMOTE_MUTATIONS',
        'git_main': PIN, 'gates': {}, 'observations': {},
        'limitations': [
            'S1 complete historical Pages artifact inventory and external consumers remain unverified.',
            'The recovery/v3 route copies exact v6 HTML; no distinct recovery implementation is present.',
            '503 is simulated on localhost only; same-origin recovery cannot survive complete domain/Pages outage.',
            'Canonical v2 and v6 fixtures tested; only fixture-backed validated v3-v5 would count.',
            'Bounded native IDB blocked-upgrade and basic keyboard checks; full WCAG accessibility is not tested.',
            'No GitHub branch, PR, CI, release or live data is touched.',
        ], 'remote_mutations': 0,
    }
    server = None
    server_thread = None
    browser = None
    context = None
    blocker_context = None
    try:
        from playwright.sync_api import sync_playwright
        repo = args.repo.resolve(strict=True)
        check(git(repo,'rev-parse',PIN+'^{commit}') == PIN, 'HOLD: pinned base commit unavailable')
        # CI checkout is clean; local R6 candidate may contain exactly 8
        # authorized uncommitted text paths. Refuse anything else.
        allowed_local={
            '.github/workflows/learnit-v6-site-qualification.yml',
            'tools/learnit_v6_site/assemble.py',
            'tools/learnit_v6_site/expected_files.json',
            'tools/learnit_v6_site/historical.py',
            'tools/learnit_v6_site/test_site.py',
            'tools/learnit_v6_site/test_browser_integration.py',
            'tools/learnit_v6_site/v6_identity_frozen.json',
            'work-packages/OPS-WP-026.json'}
        changed={row[3:].strip('"') for row in git(repo,'status','--porcelain','-uall').splitlines()}
        check(changed.issubset(allowed_local),
              'HOLD: unexpected candidate source change '+repr(sorted(changed-allowed_local)))
        site = args.site.resolve(strict=True)
        candidate_manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        check(candidate_manifest.get('schema')=='learnit.v6.integrated.site-manifest.r1' and
              candidate_manifest.get('base')==PIN and
              candidate_manifest.get('known_files')==52,
              'HOLD: integrated site-manifest schema/base/count mismatch')
        entries = candidate_manifest['files']
        check(len(entries)==52, 'HOLD: site manifest entries count')
        expected = set()
        for e in entries:
            rel=e['path']
            check(rel not in expected and not rel.startswith(('/', '\\')) and
                  all(x not in ('', '.', '..') for x in rel.split('/')) and '\\' not in rel,
                  'HOLD: unsafe/duplicate manifest path '+rel)
            expected.add(rel)
            f=site/rel
            check(f.is_file() and not f.is_symlink() and f.resolve().is_relative_to(site),
                  'HOLD: missing/unsafe site file '+rel)
            b=f.read_bytes()
            check(len(b)==e['bytes'] and sha(b)==e['sha256'],
                  'HOLD: site file differs '+rel)
        check({p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()}==expected,
              'HOLD: site file set changed')
        # HTTP mount matches GitHub Pages project site: /learnit-platform/.
        root=out/'http-root'
        root.mkdir()
        shutil.copytree(site,root/'learnit-platform')
        for rel in ('index.html', 'learnit-next.html', 'recovery/v3/index.html'):
            f = site / rel
            check(len(f.read_bytes()) == V6_BYTES and sha(f.read_bytes()) == V6_SHA,
                  'HOLD: root/alias/recovery v6 identity mismatch ' + rel)
        fixture_bytes = git(repo, 'show', PIN + ':contracts/fixtures/llv2-valid-objective-loop.json', binary=True)
        check(sha(fixture_bytes) == FIX_SHA and
              hashlib.sha1((f'blob {len(fixture_bytes)}\0').encode() + fixture_bytes).hexdigest() == FIX_BLOB,
              'HOLD: pinned v2 public fixture mismatch')
        fixture = json.loads(fixture_bytes.decode('utf-8'))
        check(fixture.get('contract') == 'learnit.kit.v2', 'HOLD: fixture is not a v2 kit')
        qcm = next((x for c in fixture['courses'] for x in c['activities']
                    if x.get('type') == 'qcm' and x.get('correctChoiceId')), None)
        check(qcm is not None, 'HOLD: fixture has no valid QCM')
        v2 = locally_built_v2(repo, out)
        report['observations']['inputs'] = {
            'site_manifest': str(args.manifest), 'built_site': str(site),
            'fixture_git_blob': FIX_BLOB, 'v2_seed_sha256': V2_SHA, 'v6_sha256': V6_SHA}
        report['gates']['local_preview_exact_52_files'] = 'PASS'
        print('PASS_FROZEN_PREVIEW=52/52', flush=True)

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(root), **kw)
            def log_message(self, fmt, *params):
                pass  # isolate proof output; web server serves only localhost
            def do_GET(self):
                pure_path = self.path.split('?', 1)[0].split('#', 1)[0]
                if pure_path == PREFIX + '__s3_seed_v2.html':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(v2)))
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    self.wfile.write(v2)
                elif server_state['root_503'] and pure_path in (PREFIX, PREFIX + 'index.html'):
                    message = b'<!doctype html><title>S3 SIMULATED 503</title><h1>Local test only</h1>'
                    server_state['root_503_hits'] += 1
                    self.send_response(503)
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(message)))
                    self.end_headers()
                    self.wfile.write(message)
                else:
                    super().do_GET()

        server_state = {'root_503': False, 'root_503_hits': 0}
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        url = origin + PREFIX
        def httpcheck(e):
            rel = e['path']
            with urlopen(origin + PREFIX + rel, timeout=12) as resp:
                b = resp.read(e['bytes'] + 1)
                check(resp.status == 200 and len(b) == e['bytes'] and sha(b) == e['sha256'],
                      'HOLD: localhost bytes/HTTP mismatch ' + rel)
            return rel

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(httpcheck, e) for e in entries]
            for f in as_completed(futures):
                f.result()
        report['gates']['localhost_http_all_manifest_files'] = 'PASS'
        report['observations']['localhost_http_files'] = len(entries)
        print('PASS_LOCAL_HTTP=52/52', flush=True)
        report['gates']['same_origin_root_alias_recovery'] = 'PASS_BYTE_IDENTITIES_ONLY'

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True, **({'channel':'msedge'} if args.browser=='msedge' else {}))
            except Exception as err:
                raise RuntimeError('HOLD: requested Chromium/Edge unavailable: ' + str(err)) from err
            report['observations']['browser_channel'] = args.browser
            report['observations']['chromium_version'] = browser.version
            context = browser.new_context(viewport={'width': 390, 'height': 844}, locale='fr-FR',
                                          service_workers='block', accept_downloads=False)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda exc: errors.append(str(exc)[:500]))

            def navigate(p, target, expect=200):
                response = p.goto(target, wait_until='domcontentloaded', timeout=45000)
                check(response is not None and response.status == expect,
                      f'HOLD: browser navigation {target}: expected HTTP {expect}, '
                      f'got {response.status if response else "none"}')
                if expect == 200:
                    p.wait_for_function('typeof window.__LEARNIT_NEXT_TEST__?.importPackage === "function"',
                                        timeout=25000)
                return response

            navigate(page, url + '__s3_seed_v2.html')
            seed = page.evaluate('''async arg=>{
                const a=window.__LEARNIT_NEXT_TEST__;
                const imp=await a.importPackage(arg.fixture);
                const courses=await a.listCourses();
                if(courses.length!==1) throw Error('Unexpected v2 imported course count');
                const id=courses[0].courseInstallId;
                await a.startCourse(id);
                const answer=await a.answer(arg.qcm.activityRevisionId,{choiceId:arg.qcm.correctChoiceId});
                if(answer.correct!==true||answer.completed!==true) throw Error('Native v2 correct answer failed');
                const progress=await a.getProgress(id);
                if(progress.completed!==1) throw Error('Native v2 answer not persisted');
                return {id,progress};
            }''', {'fixture': fixture, 'qcm': qcm})
            before = page.evaluate(SNAPSHOT_JS)
            check(before['version'] == 2 and
                  len(before['stores'].get('courses', [])) == 1 and
                  len(before['stores'].get('progress', [])) >= 1,
                  'HOLD: actual native v2 IndexedDB seed did not persist')
            report['gates']['native_v2_synthetic_course_answer'] = 'PASS'
            print('PASS_SYNTHETIC_V2_SEED=VERSION_2_WITH_PROGRESS', flush=True)
            navigate(page, url)
            migrated = page.evaluate(SNAPSHOT_JS)
            check(migrated['version'] == 3, 'HOLD: v2->v3 did not migrate database')
            assert_preserved(before, migrated)
            progress = page.evaluate('(id)=>window.__LEARNIT_NEXT_TEST__.getProgress(id)', seed['id'])
            check(progress['completed'] == seed['progress']['completed'] and
                  progress['total'] == seed['progress']['total'], 'HOLD: v6 app does not preserve course progress')
            report['gates']['same_origin_v2_to_v3_existing_rows_preserved'] = 'PASS'
            report['observations']['seed_before'] = summarize(before)
            report['observations']['migrated_after'] = summarize(migrated)
            print('PASS_SAME_ORIGIN_V2_TO_V3=ALL_OLD_ROWS_PRESERVED', flush=True)

            tab2 = context.new_page()
            tab2.on('pageerror', lambda exc: errors.append(str(exc)[:500]))
            navigate(tab2, url + 'learnit-next.html')
            concurrent = tab2.evaluate(SNAPSHOT_JS)
            check(concurrent['version'] == 3, 'HOLD: second tab did not open v3')
            assert_preserved(migrated, concurrent)
            report['gates']['cooperative_v6_second_tab'] = 'PASS'
            print('PASS_COOPERATIVE_SECOND_TAB=V3', flush=True)

            for width, height in ((390, 844), (1280, 800)):
                tab2.set_viewport_size({'width': width, 'height': height})
                tab2.reload(wait_until='domcontentloaded')
                tab2.wait_for_function('typeof window.__LEARNIT_NEXT_TEST__?.listCourses === "function"', timeout=25000)
                ui = tab2.evaluate('''() => ({
                  root:!!document.querySelector('[data-learnit-next-app]'),
                  bodyText:(document.body?.innerText||'').trim().length,
                  controls:document.querySelectorAll('button,input,select,a[href],textarea').length,
                  viewport:[innerWidth,innerHeight],
                  courseApi:typeof window.__LEARNIT_NEXT_TEST__?.listCourses==='function'
                })''')
                check(ui['root'] and ui['bodyText'] > 40 and ui['controls'] >= 1 and ui['courseApi'],
                      f'HOLD: missing visible v6 UI at {width}x{height}: {ui}')
                report['observations'][f'ui_{width}x{height}'] = ui
                print(f'PASS_VISIBLE_UI_SMOKE={width}x{height}', flush=True)
            report['gates']['visible_v6_ui_two_viewports_smoke'] = 'PASS_BOUNDED'

            server_state['root_503'] = True
            # The normal '/' was already loaded earlier and may be served from
            # Chromium's HTTP cache. A unique query forces a server request
            # without changing the routed path or existing site files.
            server_probe_url = url + '?__s3_local_server_503=1'
            try:
                with urlopen(Request(server_probe_url, headers={
                        'Cache-Control': 'no-cache'}), timeout=12) as probe:
                    server_status = probe.status
            except HTTPError as exc:
                server_status = exc.code
            report['observations']['root_503_server_preflight_status'] = server_status
            check(server_status == 503,
                  f'HOLD: localhost server failed to generate root 503; status={server_status}')
            print('PASS_LOCAL_ROOT_503_SERVER_PREFLIGHT=503', flush=True)

            browser_probe_url = url + '?__s3_local_browser_503=1'
            down = page.goto(browser_probe_url, wait_until='domcontentloaded', timeout=20000)
            browser_status = down.status if down is not None else None
            report['observations']['root_503_browser_status'] = browser_status
            report['observations']['root_503_server_hits'] = server_state['root_503_hits']
            check(browser_status == 503 and server_state['root_503_hits'] >= 2,
                  f'HOLD: root 503 not confirmed in browser: browser_status={browser_status}, '
                  f'server_503_hits={server_state["root_503_hits"]}')
            print('PASS_ROOT_503_BROWSER=503', flush=True)
            navigate(page, origin + RECOVERY)
            recovered = page.evaluate(SNAPSHOT_JS)
            check(recovered['version'] == 3, 'HOLD: recovery route version downgraded')
            assert_preserved(migrated, recovered)
            restored = page.evaluate('(id)=>window.__LEARNIT_NEXT_TEST__.getProgress(id)', seed['id'])
            check(restored['completed'] == seed['progress']['completed'] and
                  restored['total'] == seed['progress']['total'],
                  'HOLD: recovery page cannot read seeded progress')
            report['gates']['root_503_same_origin_v3_recovery'] = 'PASS_BOUNDED_SIMULATED'
            report['observations']['recovered'] = summarize(recovered)
            print('PASS_ROOT_503_RECOVERY_ROUTE=V3_AND_PROGRESS_PRESERVED', flush=True)
            server_state['root_503'] = False
            check(not errors, 'HOLD: unhandled browser JS errors: ' + '; '.join(errors[:8]))
            report['gates']['no_unhandled_browser_js_errors'] = 'PASS'
            print('PASS_UNHANDLED_PAGE_ERRORS=0', flush=True)
            # R5: independent lanes; failures recorded without masking subsequent checks.
            report['lane_results'] = {}
            def lane(name, function):
                print('LANE_START=' + name, flush=True)
                lane_start = time.perf_counter()
                try:
                    detail = function()
                    report['lane_results'][name] = {
                        'status': 'PASS', 'detail': detail,
                        'elapsed_monotonic_seconds': round(time.perf_counter()-lane_start,3)}
                    print('LANE_PASS=' + name, flush=True)
                except Exception as lane_exc:
                    report['lane_results'][name] = {
                        'status': 'HOLD',
                        'blocker': type(lane_exc).__name__ + ': ' + str(lane_exc),
                        'elapsed_monotonic_seconds': round(time.perf_counter()-lane_start,3)}
                    print('LANE_HOLD=' + name + ': ' + str(lane_exc)[:450], flush=True)

            def native_idb_blocked():
                # Purposefully hold a native v2 IDB connection open. This test does
                # NOT wait for the app's boot/test hook on a blocked v3 page.
                c = browser.new_context(locale='fr-FR', service_workers='block')
                try:
                    tab = c.new_page()
                    navigate(tab, url + '__s3_seed_v2.html')
                    seed = tab.evaluate("""async ({fixture,qcm})=>{
                      const a=window.__LEARNIT_NEXT_TEST__;
                      await a.importPackage(fixture);
                      const courses=await a.listCourses();
                      if(courses.length!==1)throw Error('Expected one v2 course');
                      await a.startCourse(courses[0].courseInstallId);
                      const answer=await a.answer(qcm.activityRevisionId,{choiceId:qcm.correctChoiceId});
                      if(!answer.correct||!answer.completed)throw Error('v2 progress seed failed');
                      return {id:courses[0].courseInstallId};
                    }""", {'fixture':fixture,'qcm':qcm})
                    baseline = tab.evaluate(SNAPSHOT_JS)
                    check(baseline['version']==2 and len(baseline['stores'].get('progress',[]))>0,
                          'HOLD: no synthetic v2 progress')
                    holder = tab.evaluate("""async()=>{
                      const db=await new Promise((resolve,reject)=>{
                        const req=indexedDB.open('learnit_next_v1',2);
                        req.onsuccess=()=>resolve(req.result);
                        req.onerror=()=>reject(req.error);
                      });
                      window.__S3_HELD_DB__=db;
                      window.__S3_VERSION_EVENTS__=0;
                      db.onversionchange=()=>{window.__S3_VERSION_EVENTS__++};
                      return {version:db.version};
                    }""")
                    check(holder['version']==2,'HOLD: cannot keep v2 connection open')
                    second = c.new_page()
                    # Serve v2 (works while blocked) and perform a native IDB v3
                    # request. Abort its eventual transaction to leave v2 intact;
                    # the next real V6 app must perform the schema migration itself.
                    navigate(second, url + '__s3_seed_v2.html')
                    blocked = second.evaluate("""async()=>{
                      return await new Promise((resolve,reject)=>{
                        let completed=false;
                        const request=indexedDB.open('learnit_next_v1',3);
                        const timer=setTimeout(()=>{
                          if(!completed){completed=true;reject(Error('blocked event timeout'))}
                        },10000);
                        request.onblocked=()=>{
                          if(!completed){completed=true;clearTimeout(timer);
                            resolve({blocked:true})}
                        };
                        request.onupgradeneeded=()=>request.transaction.abort();
                        request.onsuccess=()=>request.result.close();
                        request.onerror=()=>{};
                      });
                    }""")
                    check(blocked['blocked'],'HOLD: expected native blocked event not emitted')
                    events=tab.evaluate('window.__S3_VERSION_EVENTS__')
                    check(events>=1,'HOLD: held v2 connection lacked versionchange event')
                    # CRITICAL: NEVER issue another indexedDB.open() while a blocked
                    # version upgrade is pending; it can queue indefinitely behind
                    # that request. Inspect the already-open holder in memory instead.
                    held_version=tab.evaluate('window.__S3_HELD_DB__.version')
                    check(held_version==2,'HOLD: held v2 connection changed unexpectedly')
                    print('PASS_NATIVE_IDB_BLOCKED_EVENT=OBSERVED_HELD_V2',flush=True)
                    tab.evaluate('window.__S3_HELD_DB__.close()')
                    # End both disposable seed tabs. The pending version-3 request
                    # intentionally aborts its upgrade in the second page.
                    second.close();tab.close()
                    print('PASS_NATIVE_IDB_BLOCKER_RELEASED=V2_TABS_CLOSED',flush=True)
                    retry=c.new_page()
                    navigate(retry,url+'learnit-next.html')
                    # Timeout inside JS: Playwright evaluate() alone need not time out
                    # when an unresolved promise is queued behind an IDB upgrade.
                    retry.evaluate("""async () => {
                      let timer;
                      try {
                        return await Promise.race([
                          window.__LEARNIT_NEXT_TEST__.listCourses(),
                          new Promise((_,reject)=> {timer=setTimeout(
                            ()=>reject(Error('HOLD: V6 retry listCourses timeout')),12000)})
                        ]);
                      } finally {clearTimeout(timer)}
                    }""")
                    migrated=retry.evaluate(SNAPSHOT_JS)
                    check(migrated['version']==3 and
                          {'objectiveProgress','libraryMetadata'}.issubset(migrated['stores']),
                          'HOLD: V6 retry missing v3 stores')
                    assert_preserved(baseline,migrated)
                    progress=retry.evaluate('(id)=>window.__LEARNIT_NEXT_TEST__.getProgress(id)',seed['id'])
                    check(progress.get('completed',0)>=1,'HOLD: retry lost course progress')
                    print('PASS_NATIVE_IDB_BLOCKED=OBSERVED_AND_REJECTED',flush=True)
                    print('PASS_NATIVE_IDB_RETRY=V3_PRESERVED',flush=True)
                    return {'versionchange_events':events, 'seed_id':seed['id'],
                            'before':summarize(baseline),'after':summarize(migrated)}
                finally:
                    c.close()

            def native_v6_eight_activities():
                # Reuse the existing governed repo's canonical V6 browser fixture,
                # but run with Edge, the already qualified browser on this PC.
                path=repo/'apps/learnit-next/tests/passage_v6_consumption.py'
                check(path.is_file(),'HOLD: native v6 fixture test source missing')
                spec=importlib.util.spec_from_file_location('_learnit_v6_native',path)
                module=importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                pkg=module.package()
                activities=pkg['courses'][0]['activities']
                canonical_types={'lesson','flashcard','qcm','fill','matching','order','classify','productive'}
                check({x['type'] for x in activities}==canonical_types,
                      'HOLD: native fixture does not cover eight types')
                c=browser.new_context(locale='fr-FR',service_workers='block')
                try:
                    tab=c.new_page()
                    navigate(tab,url+'learnit-next.html')
                    native=lambda op, args=None: tab.evaluate(
                        'async ({op,args})=>await window.__LEARNIT_NEXT_TEST__[op](...(args||[]))',
                        {'op':op,'args':args or []})
                    valid=native('validatePackage',[pkg])
                    check(valid.get('ok') is True, f'HOLD: v6 fixture rejected {valid}')
                    check(native('previewImport',[pkg]).get('contract')=='learnit.kit.v6',
                          'HOLD: previewImport contract differs')
                    imported=native('importPackage',[pkg])
                    check(imported.get('contract')=='learnit.kit.v6','HOLD: import contract differs')
                    cid=imported['courses'][0]['courseInstallId']
                    session=native('startCourse',[cid])
                    passed_types=[]
                    for activity in activities:
                        check(session['currentActivity']['activityRevisionId']==activity['activityRevisionId'],
                              'HOLD: v6 activity ordering incorrect')
                        check(session['currentActivity']['presentation']['type']==activity['type'],
                              'HOLD: v6 activity presentation differs')
                        ans=native('answer',[activity['activityRevisionId'],module.answer(activity)])
                        if activity['type'] not in ('lesson','flashcard'):
                            check(ans.get('scored') is True and ans.get('correct') is True,
                                  'HOLD: native v6 activity incorrectly scored '+activity['type'])
                        passed_types.append(activity['type'])
                        session=native('getSession')
                    progress=native('getProgress',[cid])
                    check(progress.get('completed')==len(activities),
                          'HOLD: v6 final progress incomplete')
                    before=tab.evaluate(SNAPSHOT_JS)
                    # A changed title without recomputed digest is rejected.
                    tampered=copy.deepcopy(pkg);tampered['title']+=' changed'
                    reject=native('validatePackage',[tampered])
                    check(reject.get('ok') is False and
                          any(e.get('code')=='digest_mismatch' for e in reject.get('errors',[])),
                          'HOLD: digest tampering accepted')
                    constructed=copy.deepcopy(pkg)
                    a=constructed['courses'][0]['activities'][0]
                    a.clear()
                    a.update({'activityLineageId':module.uid(0x990001),
                         'activityRevisionId':module.uid(0x990002),
                         'activityRevisionDigest':'sha256:'+'0'*64,
                         'objectiveIds':[constructed['courses'][0]['objectives'][0]['objectiveId']],
                         'type':'constructed','learningPhase':'application',
                         'estimatedMinutes':1,'prompt':'x','explanation':'x',
                         'difficulty':'easy','assessmentRole':'practice',
                         'acceptedResponses':['x']})
                    module.redigest(constructed)
                    reject=native('validatePackage',[constructed])
                    check(reject.get('ok') is False and
                          any(e.get('code')=='activity_type_disabled' for e in reject.get('errors',[])),
                          'HOLD: unsupported activity type accepted')
                    try:
                        native('importPackage',[constructed])
                        raise RuntimeError('HOLD: unsupported type actually imported')
                    except Exception as e:
                        if 'HOLD: unsupported type actually imported' in str(e):
                            raise
                    after=tab.evaluate(SNAPSHOT_JS)
                    check(canonical_record(before)==canonical_record(after),
                          'HOLD: rejected import mutated database')
                    print('PASS_NATIVE_V6_TYPES=8/8',flush=True)
                    print('PASS_NATIVE_V6_ACTIVITIES='+str(len(activities)),flush=True)
                    print('PASS_NATIVE_V6_NEGATIVES=2/2',flush=True)
                    return {'types':sorted(canonical_types),'activities':len(activities),
                            'completed':progress['completed'],'negative_scenarios':2}
                finally:
                    c.close()

            def basic_a11y():
                # Advisory bounded checks. Do not call this a WCAG evaluation.
                c=browser.new_context(locale='fr-FR',service_workers='block')
                try:
                    page=c.new_page()
                    obs={}
                    for width,height in ((390,844),(1280,800)):
                        page.set_viewport_size({'width':width,'height':height})
                        navigate(page,url+'learnit-next.html')
                        check(page.evaluate('document.querySelector("[data-learnit-next-app]")!==null'),
                              'HOLD: missing app root')
                        result=page.evaluate("""() => {
                          const visible=el=>{
                            const cs=getComputedStyle(el),r=el.getBoundingClientRect();
                            return r.width>0&&r.height>0&&cs.display!=='none'&&cs.visibility!=='hidden';
                          };
                          const label=el=>{
                            const aria=el.getAttribute('aria-label');if(aria?.trim())return aria.trim();
                            const ref=el.getAttribute('aria-labelledby');
                            if(ref){const val=ref.split(/\\s+/).map(id=>document.getElementById(id)?.textContent||'').join(' ').trim();if(val)return val;}
                            if(el.labels?.length){const x=[...el.labels].map(el=>el.textContent||'').join(' ').trim();if(x)return x;}
                            return (el.innerText||el.textContent||el.getAttribute('title')||el.getAttribute('value')||'').trim();
                          };
                          const controls=[...document.querySelectorAll('button,a[href],input,select,textarea,[role="button"]')].filter(visible);
                          const unnamed=controls.filter(el=>!label(el));
                          const imgs=[...document.querySelectorAll('img')].filter(visible);
                          return {lang:document.documentElement.lang,title:document.title,
                            controls:controls.length,unnamed:unnamed.map(x=>x.outerHTML.slice(0,160)).slice(0,12),
                            images:imgs.length,missingAlt:imgs.filter(x=>!x.hasAttribute('alt')).map(x=>x.outerHTML.slice(0,160)).slice(0,12)};
                        }""")
                        keys=[]
                        for _ in range(16):
                            page.keyboard.press('Tab')
                            f=page.evaluate("""() => {
                              const el=document.activeElement;
                              if(!el||el===document.body||el===document.documentElement)return null;
                              const r=el.getBoundingClientRect(),cs=getComputedStyle(el);
                              if(r.width<=0||r.height<=0||cs.visibility==='hidden'||cs.display==='none')return null;
                              return {tag:el.tagName,role:el.getAttribute('role'),name:(el.getAttribute('aria-label')||el.innerText||'').trim().slice(0,100)};
                            }""")
                            if f:keys.append(f)
                        result['visibleKeyboardFocusSteps']=len(keys)
                        result['keyboardFocusTrace']=keys[:6]
                        obs[f'{width}x{height}']=result
                        check(result['lang'].strip() and result['title'].strip() and
                              result['controls']>=1 and not result['unnamed'] and
                              not result['missingAlt'] and keys,
                              'HOLD: basic accessible controls/keyboard issue at '+str(width)+
                              ': '+str(result)[:450])
                        print(f'PASS_BASIC_A11Y={width}x{height}',flush=True)
                    return obs
                finally:
                    c.close()

            def kit_fixture_inventory():
                # Scan only pinned JSON fixtures, classify evidence. Discovery is
                # not semantic validation and never auto-credits absent formats.
                families={f'learnit.kit.v{i}':[] for i in range(2,7)}
                sources=[repo/'contracts'/'fixtures',repo/'authoring'/'v2'/'golden',
                         repo/'authoring'/'v2'/'atlas']
                for rootf in sources:
                    if not rootf.is_dir():continue
                    for path in rootf.glob('*.json'):
                        try:
                            data=json.loads(path.read_text(encoding='utf-8'))
                        except (UnicodeError, OSError, ValueError):continue
                        contract=data.get('contract') if isinstance(data,dict) else None
                        if contract in families:families[contract].append(path.relative_to(repo).as_posix())
                for key in families:families[key].sort()
                print('PASS_KIT_FIXTURE_DISCOVERY=V2_TO_V6_INVENTORIED',flush=True)
                for contract,paths in families.items():
                    print('  '+contract+' DISCOVERED='+str(len(paths)),flush=True)
                return {'fixture_paths_by_contract':families,
                        'important_limit':'discovery only; v3-v5 positive/negative browser matrix not certified'}

            for label,fn in (
                ('NATIVE_IDB_BLOCKED_AND_RETRY',native_idb_blocked),
                ('NATIVE_V6_EIGHT_TYPES_AND_NEGATIVES',native_v6_eight_activities),
                ('BASIC_KEYBOARD_ACCESSIBILITY',basic_a11y),
                ('KIT_V2_V6_FIXTURE_DISCOVERY',kit_fixture_inventory)):
                lane(label,fn)
            failures=[name for name,item in report['lane_results'].items()
                      if item['status']!='PASS']
            report['overall']=('PASS_BOUNDED_S3_R5_INDEPENDENT_CHECKS__FULL_S1_S2_S3_HOLD'
                               if not failures else 'HOLD_BOUNDED_S3_R5_INDEPENDENT_CHECKS')
            report['first_blocker']=('LANE '+failures[0]+': '+
                report['lane_results'][failures[0]]['blocker'] if failures else None)
            print('R5_LANES_PASS='+str(4-len(failures))+'/4',flush=True)

    except Exception as exc:
        report['overall'] = 'HOLD_S3_LOCAL_BROWSER_SMOKE'
        report['first_blocker'] = type(exc).__name__ + ': ' + str(exc)
        print('HOLD: ' + report['first_blocker'], file=sys.stderr, flush=True)
    finally:
        server_state_obj = locals().get('server_state')
        if server_state_obj is not None:
            server_state_obj['root_503'] = False
        try:
            if blocker_context:
                blocker_context.close()
        except Exception as exc:
            report['cleanup_blocker_context_error'] = str(exc)
        try:
            if context:
                context.close()
        except Exception as exc:
            report['cleanup_context_error'] = str(exc)
        try:
            if browser:
                browser.close()
        except Exception as exc:
            report['cleanup_browser_error'] = str(exc)
        try:
            if server:
                server.shutdown()
                server.server_close()
        except Exception as exc:
            report['cleanup_server_error'] = str(exc)
        if (out / 'http-root').is_dir():
            shutil.rmtree(out/'http-root',ignore_errors=True)
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        report['finished_at_local'] = datetime.now().astimezone().isoformat()
        report['elapsed_monotonic_seconds'] = round(time.perf_counter()-started, 3)
        report['s1_total'] = 'HOLD_COMPLETE_HISTORICAL_ARCHIVE_UNVERIFIED'
        report['s2_total'] = 'HOLD_SITE_NOT_RELEASE_QUALIFIED'
        report['s3_total'] = 'HOLD_KIT_V3_V5_CANONICAL_FIXTURES_AND_FULL_WCAG_NOT_CERTIFIED'
        report['remote_mutations'] = 0
        try:
            with report_path.open('x', encoding='utf-8', newline='\n') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                f.write('\n')
        except Exception as exc:
            print('HOLD: cannot durably write local proof: ' + str(exc), file=sys.stderr, flush=True)
            return 2
        print('OVERALL=' + report['overall'], flush=True)
        print('S3_TOTAL=' + report['s3_total'], flush=True)
        print('GITHUB_MUTATIONS=0 / ONEDRIVE_MUTATIONS=0', flush=True)
        print('EVIDENCE=' + str(report_path), flush=True)
        return 0 if report['overall'].startswith('PASS_BOUNDED_') else 2


if __name__ == '__main__':
    raise SystemExit(main())
