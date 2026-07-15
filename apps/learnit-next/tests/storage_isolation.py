#!/usr/bin/env python3
"""Prove RC718 storage is untouched and successor writes are transactional."""
from __future__ import annotations
import json, os, threading, unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
try:
    from playwright.sync_api import Error as PlaywrightError, sync_playwright
except ImportError:
    PlaywrightError, sync_playwright = RuntimeError, None

ROOT=Path(__file__).resolve().parents[3]; F=ROOT/"contracts/fixtures"
VALID,LEGACY=F/"v2-valid-minimal.json",F/"v2-invalid-legacy.json"
ARTIFACT=ROOT/"apps/learnit-next/dist/learnit-next.html"
KEYS=("learnit_clean_state_v2","learnit_imported_courses_v1","learnit_import_history_v1",
"learnit_import_last_applied_v1","learnit_import_transaction_v1","learnit_active_course_v1",
"learnit_content_patches_v2","learnit_library_revision_v1","learnit_library_persistence_meta_v1")
LEGACY_DB,STORE="learnit_durable_library_v1","snapshots"
NEXT_PREFIX,NEXT_DB="learnit.next.v1.","learnit_next_v1"; OTHER="qa.unrelated.sentinel"
STRICT=os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION")=="1"

def require_or_skip(condition,message):
    if condition:return
    if STRICT:raise RuntimeError(message)
    raise unittest.SkipTest(message)
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def negative(r): return isinstance(r,dict) and (any(r.get(k) is False for k in ("ok","valid","accepted","imported","success")) or str(r.get("status","")).lower() in {"error","invalid","rejected"})
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_): pass
@contextmanager
def serve(path):
    s=ThreadingHTTPServer(("127.0.0.1",0),partial(Quiet,directory=str(path.parent)));t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
    try:
        origin=f"http://127.0.0.1:{s.server_port}";yield origin,f"{origin}/{path.name}"
    finally:s.shutdown();s.server_close();t.join(timeout=5)

PREPARE=r"""async x=>{for(const [i,k] of x.keys.entries())localStorage.setItem(k,JSON.stringify({marker:'RC718',i,k,unicode:'é Ω',bytes:[0,1,255]}));localStorage.setItem(x.other,'unrelated::é');await new Promise((ok,no)=>{const q=indexedDB.deleteDatabase(x.db);q.onsuccess=ok;q.onerror=()=>no(q.error);q.onblocked=()=>no(Error('blocked'))});const db=await new Promise((ok,no)=>{const q=indexedDB.open(x.db,1);q.onupgradeneeded=()=>q.result.createObjectStore(x.store,{keyPath:'id'});q.onsuccess=()=>ok(q.result);q.onerror=()=>no(q.error)});await new Promise((ok,no)=>{const tx=db.transaction(x.store,'readwrite'),s=tx.objectStore(x.store);s.put({id:'library',revision:718,payload:{course:'legacy',answer:'é'}});s.put({id:'qa-shadow',payload:[true,false,null]});tx.oncomplete=ok;tx.onerror=()=>no(tx.error);tx.onabort=()=>no(tx.error)});db.close()}"""
SNAPSHOT=r"""async x=>{const enc=v=>Array.from(new TextEncoder().encode(v)),local={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i),v=localStorage.getItem(k);local[k]={value:v,utf8:enc(v)}}async function snap(name){const db=await new Promise((ok,no)=>{const q=indexedDB.open(name);q.onupgradeneeded=e=>e.target.transaction.abort();q.onsuccess=()=>ok(q.result);q.onerror=()=>no(q.error)}).catch(()=>null);if(!db)return null;const out={version:db.version,stores:{}};for(const n of Array.from(db.objectStoreNames).sort())out.stores[n]=await new Promise((ok,no)=>{const tx=db.transaction(n,'readonly'),s=tx.objectStore(n),kr=s.getAllKeys(),vr=s.getAll();tx.oncomplete=()=>ok({keyPath:s.keyPath,autoIncrement:s.autoIncrement,indexes:Array.from(s.indexNames).sort(),keys:kr.result,records:vr.result});tx.onerror=()=>no(tx.error)});db.close();return out}let names=null;if(indexedDB.databases)names=(await indexedDB.databases()).map(x=>x.name).filter(Boolean).sort();return{local,names,legacy:await snap(x.legacy),next:names&&names.includes(x.next)?await snap(x.next):null}}"""
INSTALL_FAILURE=r"""(()=>{const original=IDBObjectStore.prototype.put;let count=0;window.__qaFailureInstalled=true;window.__qaWriteCount=()=>count;IDBObjectStore.prototype.put=function(...args){if(this.transaction.db.name==='learnit_next_v1'){count+=1;if(count===3)throw new DOMException('QA forced after partial writes','QuotaExceededError')}return original.apply(this,args)}})();"""

class StorageIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(os.environ.get("LEARNIT_NEXT_ARTIFACT",ARTIFACT))
        require_or_skip(path.exists(),f"WAITING_FOR_INTEGRATION: {path}")
        require_or_skip(sync_playwright is not None,"DEPENDENCY: Playwright")
        cls.v,cls.l=load(VALID),load(LEGACY);cls.server=serve(path);cls.origin,cls.url=cls.server.__enter__();cls.pw=sync_playwright().start()
        try:cls.browser=cls.pw.chromium.launch(headless=True)
        except Exception as e:
            cls.pw.stop();cls.server.__exit__(None,None,None);require_or_skip(False,f"DEPENDENCY: Chromium: {e}")
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,"browser"):cls.browser.close()
        if hasattr(cls,"pw"):cls.pw.stop()
        if hasattr(cls,"server"):cls.server.__exit__(None,None,None)
    def setUp(self):
        self.ctx=self.browser.new_context();self.page=self.ctx.new_page();self.page.goto(self.origin+"/__qa_prepare__")
        self.page.evaluate(PREPARE,{"keys":list(KEYS),"other":OTHER,"db":LEGACY_DB,"store":STORE});self.before=self.snapshot()
    def tearDown(self):self.ctx.close()
    def boot(self):self.page.goto(self.url);self.page.wait_for_function("()=>window.__LEARNIT_NEXT_TEST__")
    def call(self,op,*args):return self.page.evaluate("async x=>await window.__LEARNIT_NEXT_TEST__[x.op](...x.args)",{"op":op,"args":list(args)})
    def snapshot(self):return self.page.evaluate(SNAPSHOT,{"legacy":LEGACY_DB,"next":NEXT_DB})
    def assert_rc718_untouched(self,after):
        self.assertEqual(self.before["legacy"],after["legacy"])
        for k in KEYS+(OTHER,):self.assertEqual(self.before["local"][k],after["local"].get(k))
        changed={k for k in set(self.before["local"])|set(after["local"]) if self.before["local"].get(k)!=after["local"].get(k)}
        self.assertEqual([],sorted(k for k in changed if not k.startswith(NEXT_PREFIX)))
        if self.before["names"] is not None and after["names"] is not None:
            delta=set(self.before["names"])^set(after["names"]);self.assertEqual([],sorted(x for x in delta if x!=NEXT_DB))
    def reject(self,payload):
        try:r=self.call("importPackage",payload);return negative(r)
        except PlaywrightError:return True
    def test_boot_preserves_rc718_byte_for_byte(self):self.boot();self.assert_rc718_untouched(self.snapshot())
    def test_import_and_session_preserve_rc718_record_for_record(self):
        self.boot();self.assertFalse(negative(self.call("importPackage",self.v)));c=self.call("listCourses")[0];self.call("startCourse",c["courseInstallId"]);q=self.v["courses"][0]["activities"][0];self.call("answer",q["activityRevisionId"],q["correctChoiceId"]);self.assert_rc718_untouched(self.snapshot())
    def test_legacy_rejection_is_atomic(self):
        self.boot();before=self.snapshot();self.assertTrue(self.reject(self.l));after=self.snapshot();self.assert_rc718_untouched(after);self.assertEqual(before["next"],after["next"]);self.assertEqual([],self.call("listCourses"))
    def test_forced_successor_write_failure_rolls_back_all_successor_stores(self):
        self.page.add_init_script(INSTALL_FAILURE);self.boot()
        self.assertTrue(self.page.evaluate("()=>window.__qaFailureInstalled"))
        before=self.snapshot();self.assertTrue(self.reject(self.v))
        self.assertGreaterEqual(self.page.evaluate("()=>window.__qaWriteCount()"),3)
        after=self.snapshot();self.assertEqual(before["next"],after["next"],"packages/courses/progress/meta must roll back record-for-record")
        self.assertEqual([],self.call("listCourses"));self.assert_rc718_untouched(after)
    def test_reset_changes_only_successor_namespaces(self):
        self.boot();self.call("importPackage",self.v);before=self.snapshot();self.call("resetNextData");after=self.snapshot();self.assert_rc718_untouched(after);self.assertEqual([],self.call("listCourses"));self.assertNotEqual(before["next"],after["next"])

if __name__=="__main__":unittest.main(verbosity=2)
