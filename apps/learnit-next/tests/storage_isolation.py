#!/usr/bin/env python3
"""Prove RC718 storage is untouched and successor writes are transactional."""
from __future__ import annotations
import json, os, re, threading, unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None
ROOT=Path(__file__).resolve().parents[3];FIX=ROOT/'contracts/fixtures';VALID=FIX/'v2-valid-minimal.json';LEGACY=FIX/'v2-invalid-legacy.json';ARTIFACT=ROOT/'apps/learnit-next/dist/learnit-next.html'
PROTECTED_KEYS=('learnit_clean_state_v2','learnit_imported_courses_v1','learnit_import_history_v1','learnit_import_last_applied_v1','learnit_import_transaction_v1','learnit_active_course_v1','learnit_content_patches_v2','learnit_library_revision_v1','learnit_library_persistence_meta_v1')
LEGACY_DB='learnit_durable_library_v1';LEGACY_STORE='snapshots';NEXT_PREFIX='learnit.next.v1.';NEXT_DB='learnit_next_v1';OTHER='qa.unrelated.sentinel';STRICT=os.environ.get('LEARNIT_NEXT_STRICT_INTEGRATION')=='1'
DOMAIN_ERROR_NAMES={'ContractError','ValidationError','SchemaValidationError','DigestMismatchError','RevisionConflictError','LegacyContractError','ImportRejectedError','QuotaExceededError'}
def require_or_skip(ok,msg):
    if ok:return
    if STRICT:raise RuntimeError(msg)
    raise unittest.SkipTest(msg)
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def negative(v):return v is False or isinstance(v,dict) and (any(v.get(k) is False for k in ('ok','valid','accepted','imported','success')) or str(v.get('status','')).lower() in {'error','invalid','rejected'})
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_):pass
@contextmanager
def serve(path):
    s=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(path.parent)));t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
    try:origin=f'http://127.0.0.1:{s.server_port}';yield origin,f'{origin}/{path.name}'
    finally:s.shutdown();s.server_close();t.join(timeout=5)
PREPARE=r"""async c=>{for(const[i,k]of c.keys.entries())localStorage.setItem(k,JSON.stringify({marker:'RC718',i,k,unicode:'é Ω',bytes:[0,1,255]}));localStorage.setItem(c.other,'unrelated::é');await new Promise((ok,no)=>{const q=indexedDB.deleteDatabase(c.db);q.onsuccess=ok;q.onerror=()=>no(q.error);q.onblocked=()=>no(Error('blocked'))});const db=await new Promise((ok,no)=>{const q=indexedDB.open(c.db,1);q.onupgradeneeded=()=>q.result.createObjectStore(c.store,{keyPath:'id'});q.onsuccess=()=>ok(q.result);q.onerror=()=>no(q.error)});await new Promise((ok,no)=>{const tx=db.transaction(c.store,'readwrite'),s=tx.objectStore(c.store);s.put({id:'library',revision:718,payload:{course:'legacy',answer:'é'}});s.put({id:'qa-shadow',payload:[true,false,null]});tx.oncomplete=ok;tx.onerror=()=>no(tx.error);tx.onabort=()=>no(tx.error)});db.close()}"""
SNAPSHOT=r"""async c=>{const enc=v=>Array.from(new TextEncoder().encode(v)),local={},successor={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i),v=localStorage.getItem(k);local[k]={value:v,utf8:enc(v)};if(k.startsWith(c.prefix))successor[k]=local[k]}async function snap(name){const names=typeof indexedDB.databases==='function'?(await indexedDB.databases()).map(x=>x.name).filter(Boolean):null;if(names&&!names.includes(name))return null;const db=await new Promise((ok,no)=>{const q=indexedDB.open(name);q.onupgradeneeded=e=>e.target.transaction.abort();q.onsuccess=()=>ok(q.result);q.onerror=()=>no(q.error)}).catch(()=>null);if(!db)return null;const stores={};for(const n of Array.from(db.objectStoreNames).sort())stores[n]=await new Promise((ok,no)=>{const tx=db.transaction(n,'readonly'),s=tx.objectStore(n),kr=s.getAllKeys(),vr=s.getAll();tx.oncomplete=()=>ok({keyPath:s.keyPath,autoIncrement:s.autoIncrement,indexes:Array.from(s.indexNames).sort(),keys:kr.result,records:vr.result});tx.onerror=()=>no(tx.error);tx.onabort=()=>no(tx.error)});const out={version:db.version,stores};db.close();return out}let names=null;if(indexedDB.databases)names=(await indexedDB.databases()).map(x=>x.name).filter(Boolean).sort();return{local,successor,names,legacy:await snap(c.legacy),next:names&&names.includes(c.next)?await snap(c.next):null}}"""
INSTALL_DORMANT_FAILURE=r"""(()=>{let armed=false,count=0,methods=[];for(const method of['add','put']){const original=IDBObjectStore.prototype[method];if(typeof original!=='function')continue;IDBObjectStore.prototype[method]=function(...args){if(armed&&this.transaction?.db?.name==='learnit_next_v1'){count++;methods.push(method);if(count===3){armed=false;throw new DOMException('QA forced after partial successor writes','QuotaExceededError')}}return original.apply(this,args)}}window.__qaFailureInstalled=true;window.__qaArmFailure=()=>{armed=true;count=0;methods=[]};window.__qaWriteEvidence=()=>({armed,count,methods:[...methods]})})();"""
class StorageIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(c):
        path=Path(os.environ.get('LEARNIT_NEXT_ARTIFACT',ARTIFACT));require_or_skip(path.exists(),f'WAITING_FOR_INTEGRATION: {path}');require_or_skip(sync_playwright is not None,'DEPENDENCY: Playwright');c.v=load(VALID);c.l=load(LEGACY);c.srv=serve(path);c.origin,c.url=c.srv.__enter__();c.pw=sync_playwright().start()
        try:c.browser=c.pw.chromium.launch(headless=True)
        except Exception as e:c.pw.stop();c.srv.__exit__(None,None,None);require_or_skip(False,f'DEPENDENCY: Chromium: {e}')
    @classmethod
    def tearDownClass(c):
        if hasattr(c,'browser'):c.browser.close()
        if hasattr(c,'pw'):c.pw.stop()
        if hasattr(c,'srv'):c.srv.__exit__(None,None,None)
    def setUp(self):self.ctx=self.browser.new_context();self.page=self.ctx.new_page();self.page.goto(self.origin+'/__qa_prepare__');self.page.evaluate(PREPARE,{'keys':list(PROTECTED_KEYS),'other':OTHER,'db':LEGACY_DB,'store':LEGACY_STORE});self.before=self.snapshot()
    def tearDown(self):self.ctx.close()
    def boot(self):self.page.goto(self.url);self.page.wait_for_function('()=>window.__LEARNIT_NEXT_TEST__')
    def invoke(self,op,*args):return self.page.evaluate("""async x=>{const a=window.__LEARNIT_NEXT_TEST__;if(!a||typeof a[x.op]!=='function')return{kind:'harness'};try{return{kind:'return',value:await a[x.op](...x.args)}}catch(e){return{kind:'throw',name:String(e?.name||''),code:String(e?.code||''),message:String(e?.message||e||'')}}}""",{'op':op,'args':list(args)})
    def call(self,op,*args):r=self.invoke(op,*args);self.assertEqual('return',r.get('kind'),r);return r.get('value')
    def snapshot(self):return self.page.evaluate(SNAPSHOT,{'legacy':LEGACY_DB,'next':NEXT_DB,'prefix':NEXT_PREFIX})
    def assert_rc718(self,a):
        self.assertEqual(self.before['legacy'],a['legacy'])
        for k in PROTECTED_KEYS+(OTHER,):self.assertEqual(self.before['local'][k],a['local'].get(k))
        changed={k for k in set(self.before['local'])|set(a['local']) if self.before['local'].get(k)!=a['local'].get(k)};self.assertEqual([],sorted(k for k in changed if not k.startswith(NEXT_PREFIX)))
        if self.before['names'] is not None and a['names'] is not None:self.assertEqual([],sorted(x for x in set(self.before['names'])^set(a['names']) if x!=NEXT_DB))
    def assert_domain_rejection(self,r,forced=False):
        self.assertNotEqual('harness',r.get('kind'),r)
        if r.get('kind')=='return':self.assertTrue(negative(r.get('value')),r);return
        self.assertEqual('throw',r.get('kind'),r);self.assertNotIn(r.get('name'),{'TypeError','ReferenceError','SyntaxError','RangeError','InternalError','Error'},r)
        if forced:self.assertEqual('QuotaExceededError',r.get('name'),r)
        else:self.assertTrue(r.get('name') in DOMAIN_ERROR_NAMES or r.get('code') in {'ERR_CONTRACT','ERR_SCHEMA','ERR_DIGEST','ERR_REVISION_CONFLICT','ERR_LEGACY','ERR_IMPORT_REJECTED'},r)
    def test_boot_preserves_rc718_byte_for_byte(self):self.boot();self.assert_rc718(self.snapshot())
    def test_import_and_session_preserve_rc718_record_for_record(self):
        self.boot();self.assertFalse(negative(self.call('importPackage',self.v)));c=self.call('listCourses')[0];self.call('startCourse',c['courseInstallId']);q=self.v['courses'][0]['activities'][0];self.call('answer',q['activityRevisionId'],q['correctChoiceId']);self.assert_rc718(self.snapshot())
    def test_legacy_rejection_is_atomic(self):
        self.boot();b=self.snapshot();r=self.invoke('importPackage',self.l);self.assert_domain_rejection(r);a=self.snapshot();self.assert_rc718(a);self.assertEqual(b['next'],a['next']);self.assertEqual(b['successor'],a['successor']);self.assertEqual([],self.call('listCourses'))
    def test_forced_successor_write_failure_rolls_back_all_successor_stores(self):
        self.page.add_init_script(INSTALL_DORMANT_FAILURE);self.boot();self.assertTrue(self.page.evaluate('()=>window.__qaFailureInstalled'));b=self.snapshot();self.page.evaluate('()=>window.__qaArmFailure()');self.assertEqual({'armed':True,'count':0,'methods':[]},self.page.evaluate('()=>window.__qaWriteEvidence()'));r=self.invoke('importPackage',self.v);ev=self.page.evaluate('()=>window.__qaWriteEvidence()');self.assertEqual(3,ev['count'],ev);self.assertTrue(set(ev['methods']).issubset({'add','put'}),ev);self.assert_domain_rejection(r,forced=True);a=self.snapshot();self.assertEqual(b['next'],a['next']);self.assertEqual(b['successor'],a['successor']);self.assertEqual([],self.call('listCourses'));self.assert_rc718(a)
    def test_reset_changes_only_successor_namespaces(self):
        self.boot();self.call('importPackage',self.v);b=self.snapshot();self.call('resetNextData');a=self.snapshot();self.assert_rc718(a);self.assertEqual([],self.call('listCourses'));self.assertTrue(b['next']!=a['next'] or b['successor']!=a['successor'])
if __name__=='__main__':unittest.main(verbosity=2)
