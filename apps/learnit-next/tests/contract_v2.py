#!/usr/bin/env python3
"""Independent learnit.kit.v2 oracle plus black-box runtime attacks."""
from __future__ import annotations
import copy, hashlib, json, os, re, threading, unicodedata, unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
ROOT=Path(__file__).resolve().parents[3]; FIX=ROOT/'contracts/fixtures'; SCHEMA=ROOT/'contracts/learnit-kit-v2.schema.json'
VALID=FIX/'v2-valid-minimal.json'; LEGACY=FIX/'v2-invalid-legacy.json'; MISMATCH=FIX/'v2-invalid-digest-mismatch.json'
ARTIFACT=ROOT/'apps/learnit-next/dist/learnit-next.html'; STRICT=os.environ.get('LEARNIT_NEXT_STRICT_INTEGRATION')=='1'
UUID4=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'); SHA256=re.compile(r'^sha256:[0-9a-f]{64}$')
DOMAIN_ERROR_NAMES={'ContractError','ValidationError','SchemaValidationError','DigestMismatchError','RevisionConflictError','LegacyContractError','ImportRejectedError'}
NEXT_DB='learnit_next_v1'; NEXT_PREFIX='learnit.next.v1.'
SNAPSHOT=r"""async ({dbName,prefix})=>{const local={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k.startsWith(prefix))local[k]=localStorage.getItem(k)}if(typeof indexedDB.databases!=='function')throw Error('indexedDB.databases required');const names=(await indexedDB.databases()).map(x=>x.name).filter(Boolean);if(!names.includes(dbName))return{local,db:null};const db=await new Promise((ok,no)=>{const q=indexedDB.open(dbName);q.onsuccess=()=>ok(q.result);q.onerror=()=>no(q.error)});const stores={};for(const n of Array.from(db.objectStoreNames).sort())stores[n]=await new Promise((ok,no)=>{const tx=db.transaction(n,'readonly'),s=tx.objectStore(n),kr=s.getAllKeys(),vr=s.getAll();tx.oncomplete=()=>ok({keyPath:s.keyPath,autoIncrement:s.autoIncrement,indexes:Array.from(s.indexNames).sort(),keys:kr.result,records:vr.result});tx.onerror=()=>no(tx.error);tx.onabort=()=>no(tx.error||Error('snapshot aborted'))});const out={local,db:{version:db.version,stores}};db.close();return out}"""
def require_or_skip(ok,msg):
    if ok:return
    if STRICT: raise RuntimeError(msg)
    raise unittest.SkipTest(msg)
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def norm(v):
    if v is None or isinstance(v,(bool,int)): return v
    if isinstance(v,float): raise TypeError('floats forbidden')
    if isinstance(v,str): return unicodedata.normalize('NFC',v)
    if isinstance(v,list): return [norm(x) for x in v]
    if isinstance(v,dict):
        out={}
        for k,x in v.items():
            nk=unicodedata.normalize('NFC',k)
            if nk in out: raise ValueError('NFC key collision')
            out[nk]=norm(x)
        return out
    raise TypeError(type(v).__name__)
def canonical(v): return json.dumps(norm(v),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj,field): return 'sha256:'+hashlib.sha256(canonical({k:v for k,v in obj.items() if k!=field})).hexdigest()
def redigest(p):
    p=copy.deepcopy(p)
    for c in p['courses']:
        for a in c['activities']: a['activityRevisionDigest']=digest(a,'activityRevisionDigest')
        c['courseRevisionDigest']=digest(c,'courseRevisionDigest')
    p['packageRevisionDigest']=digest(p,'packageRevisionDigest'); return p
def dup(xs):
    seen=set()
    for x in xs:
        if x in seen:return True
        seen.add(x)
    return False
def semantic_errors(p):
    e=[]
    if p.get('contract')!='learnit.kit.v2': return ['contract']
    for key in ('courseLineageId','courseRevisionId'):
        if dup(c[key] for c in p['courses']): e.append('duplicate '+key)
    als=[]; ars=[]
    for c in p['courses']:
        objectives=[x['objectiveId'] for x in c['objectives']]
        if dup(objectives):e.append('duplicate objectiveId')
        for a in c['activities']:
            als.append(a['activityLineageId']);ars.append(a['activityRevisionId'])
            if any(x not in objectives for x in a['objectiveIds']):e.append('missing objective')
            if a['type']=='qcm':
                ids=[x['choiceId'] for x in a['choices']]
                if dup(ids):e.append('duplicate choice')
                if a['correctChoiceId'] not in ids:e.append('missing choice')
            else:
                slots=[x['slotId'] for x in a['segments'] if 'slotId' in x]; tokens=[x['tokenId'] for x in a['tokens']]; answers=[x['slotId'] for x in a['answers']]
                if dup(slots):e.append('duplicate slot')
                if dup(tokens):e.append('duplicate token')
                if dup(answers):e.append('duplicate answer')
                if set(answers)!=set(slots):e.append('slot reference')
                limits={x['tokenId']:x['maxUses'] for x in a['tokens']}; uses={}
                for x in a['answers']:
                    tid=x['tokenId']; uses[tid]=uses.get(tid,0)+1
                    if tid not in limits:e.append('token reference')
                if any(n>limits.get(t,-1) for t,n in uses.items()):e.append('maxUses')
    if dup(als):e.append('duplicate activityLineageId')
    if dup(ars):e.append('duplicate activityRevisionId')
    return e
def digest_errors(p):
    e=[]
    for c in p['courses']:
        for a in c['activities']:
            if a['activityRevisionDigest']!=digest(a,'activityRevisionDigest'):e.append('activity')
        if c['courseRevisionDigest']!=digest(c,'courseRevisionDigest'):e.append('course')
    if p['packageRevisionDigest']!=digest(p,'packageRevisionDigest'):e.append('package')
    return e
def identities(v):
    if isinstance(v,dict):
        for k,x in v.items():
            if k.endswith('Id') and isinstance(x,str):yield x
            yield from identities(x)
    elif isinstance(v,list):
        for x in v:yield from identities(x)
def uid(n):return f'{n:08x}-9abc-4def-8abc-{n:012x}'
def replace_identity(value,old,new):
    if isinstance(value,dict):
        for key,item in value.items():
            if item==old:value[key]=new
            else:replace_identity(item,old,new)
    elif isinstance(value,list):
        for index,item in enumerate(value):
            if item==old:value[index]=new
            else:replace_identity(item,old,new)
def append_course(p,key):
    s=p['courses'][0]; c=copy.deepcopy(s); i=100
    c['courseLineageId']=s['courseLineageId'] if key=='courseLineageId' else uid(i);i+=1
    c['courseRevisionId']=s['courseRevisionId'] if key=='courseRevisionId' else uid(i);i+=1
    om={}
    for o in c['objectives']:old=o['objectiveId'];o['objectiveId']=uid(i);i+=1;om[old]=o['objectiveId']
    for a in c['activities']:
        a['activityLineageId']=uid(i);i+=1;a['activityRevisionId']=uid(i);i+=1;a['objectiveIds']=[om[x] for x in a['objectiveIds']]
        if a['type']=='qcm':
            m={}
            for x in a['choices']:old=x['choiceId'];x['choiceId']=uid(i);i+=1;m[old]=x['choiceId']
            a['correctChoiceId']=m[a['correctChoiceId']]
        else:
            sm={};tm={}
            for x in a['segments']:
                if 'slotId' in x:old=x['slotId'];x['slotId']=uid(i);i+=1;sm[old]=x['slotId']
            for x in a['tokens']:old=x['tokenId'];x['tokenId']=uid(i);i+=1;tm[old]=x['tokenId']
            for x in a['answers']:x['slotId']=sm[x['slotId']];x['tokenId']=tm[x['tokenId']]
    p['courses'].append(c)
def append_activity(p,key):
    a=copy.deepcopy(p['courses'][0]['activities'][0]);
    if key!='activityLineageId':a['activityLineageId']=uid(700)
    if key!='activityRevisionId':a['activityRevisionId']=uid(701)
    m={}
    for i,x in enumerate(a['choices'],710):old=x['choiceId'];x['choiceId']=uid(i);m[old]=x['choiceId']
    a['correctChoiceId']=m[a['correctChoiceId']];p['courses'][0]['activities'].append(a)
Mutation=Callable[[dict[str,Any]],None]
def attacks(valid):
    fill=lambda p:p['courses'][0]['activities'][1]; qcm=lambda p:p['courses'][0]['activities'][0]
    cases=[
('unknown root',lambda p:p.__setitem__('unknown',1)),('unknown course',lambda p:p['courses'][0].__setitem__('unknown',1)),('unknown objective',lambda p:p['courses'][0]['objectives'][0].__setitem__('unknown',1)),
('unknown qcm',lambda p:qcm(p).__setitem__('unknown',1)),('unknown fill',lambda p:fill(p).__setitem__('unknown',1)),('unknown choice',lambda p:qcm(p)['choices'][0].__setitem__('unknown',1)),('unknown token',lambda p:fill(p)['tokens'][0].__setitem__('unknown',1)),('unknown text segment',lambda p:fill(p)['segments'][0].__setitem__('unknown',1)),('unknown slot segment',lambda p:next(x for x in fill(p)['segments'] if 'slotId'in x).__setitem__('unknown',1)),('unknown answer',lambda p:fill(p)['answers'][0].__setitem__('unknown',1)),
('invalid package UUID',lambda p:p.__setitem__('packageLineageId','BAD')),('invalid course UUID',lambda p:p['courses'][0].__setitem__('courseRevisionId','BAD')),('invalid objective UUID',lambda p:replace_identity(p,p['courses'][0]['objectives'][0]['objectiveId'],'BAD')),('invalid activity UUID',lambda p:qcm(p).__setitem__('activityRevisionId','BAD')),('invalid choice UUID',lambda p:replace_identity(p,qcm(p)['correctChoiceId'],'BAD')),('invalid slot UUID',lambda p:replace_identity(p,fill(p)['answers'][0]['slotId'],'BAD')),('invalid token UUID',lambda p:replace_identity(p,fill(p)['answers'][0]['tokenId'],'BAD')),('invalid answer slot UUID',lambda p:replace_identity(p,fill(p)['answers'][1]['slotId'],'BAD')),('invalid answer token UUID',lambda p:replace_identity(p,fill(p)['answers'][0]['tokenId'],'BAD')),
('duplicate courseLineageId',lambda p:append_course(p,'courseLineageId')),('duplicate courseRevisionId',lambda p:append_course(p,'courseRevisionId')),('duplicate activityLineageId',lambda p:append_activity(p,'activityLineageId')),('duplicate activityRevisionId',lambda p:append_activity(p,'activityRevisionId')),('duplicate objectiveId',lambda p:p['courses'][0]['objectives'].append(copy.deepcopy(p['courses'][0]['objectives'][0]))),('duplicate choiceId',lambda p:qcm(p)['choices'][1].__setitem__('choiceId',qcm(p)['choices'][0]['choiceId'])),('duplicate slotId',lambda p:fill(p)['segments'].append(copy.deepcopy(next(x for x in fill(p)['segments'] if 'slotId'in x)))),('duplicate tokenId',lambda p:fill(p)['tokens'].append(copy.deepcopy(fill(p)['tokens'][0]))),('duplicate answer slotId',lambda p:fill(p)['answers'].append(copy.deepcopy(fill(p)['answers'][0]))),('slot without answer',lambda p:fill(p)['answers'].pop()),('answer absent slot',lambda p:fill(p)['answers'][0].__setitem__('slotId',uid(900))),('missing objective',lambda p:qcm(p).__setitem__('objectiveIds',[uid(901)])),('missing choice',lambda p:qcm(p).__setitem__('correctChoiceId',uid(902))),('missing token',lambda p:fill(p)['answers'][0].__setitem__('tokenId',uid(903))),('maxUses',lambda p:fill(p)['tokens'][0].__setitem__('maxUses',1))]
    out=[]
    for n,m in cases:
        p=copy.deepcopy(valid);m(p);out.append((n,redigest(p)))
    return out
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_):pass
@contextmanager
def serve(path):
    s=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(path.parent)));t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
    try:yield f'http://127.0.0.1:{s.server_port}/{path.name}'
    finally:s.shutdown();s.server_close();t.join(timeout=5)
def negative(v):return v is False or isinstance(v,dict) and (any(v.get(k) is False for k in ('ok','valid','accepted','imported','success')) or str(v.get('status','')).lower() in {'error','invalid','rejected'})
class FixtureOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(c):require_or_skip(Draft202012Validator is not None,'DEPENDENCY: jsonschema');c.s=load(SCHEMA);c.v=load(VALID);c.l=load(LEGACY);c.m=load(MISMATCH);c.val=Draft202012Validator(c.s)
    def test_schema_and_valid_fixture(self):self.assertEqual('learnit.kit.v2',self.s['properties']['contract']['const']);self.assertFalse(self.s['additionalProperties']);self.assertEqual([],list(self.val.iter_errors(self.v)))
    def test_uuid_v4_lowercase_and_digest_shapes(self):
        for x in identities(self.v):self.assertRegex(x,UUID4)
        for x in [self.v['packageRevisionDigest']]+[c['courseRevisionDigest'] for c in self.v['courses']]+[a['activityRevisionDigest'] for c in self.v['courses'] for a in c['activities']]:self.assertRegex(x,SHA256)
    def test_valid_semantics_and_sha256(self):self.assertEqual([],semantic_errors(self.v));self.assertEqual([],digest_errors(self.v))
    def test_unknown_properties_and_nested_uuid_are_rejected(self):
        for n,p in attacks(self.v):
            if n.startswith('unknown') or n.startswith('invalid'):
                self.assertTrue(list(self.val.iter_errors(p)),n)
                if n.startswith('invalid'):
                    self.assertEqual([],semantic_errors(p),f'{n} also broke references')
                    self.assertEqual([],digest_errors(p),f'{n} was not redigested')
    def test_semantic_attack_matrix(self):
        for n,p in attacks(self.v):
            if n.startswith(('duplicate','slot ','answer ','missing','maxUses')):self.assertTrue(semantic_errors(p),n)
    def test_canonical_json_profile(self):
        self.assertEqual(b'{"a":[true,null,3],"z":"\xc3\xa9","\xc3\xa9":"ok"}',canonical({'z':'e\u0301','a':[True,None,3],'é':'ok'}))
        with self.assertRaises(TypeError):canonical({'x':1.5})
        with self.assertRaises(ValueError):canonical({'é':1,'e\u0301':2})
    def test_legacy_and_digest_mismatch_fixtures(self):self.assertTrue(list(self.val.iter_errors(self.l)));self.assertEqual([],list(self.val.iter_errors(self.m)));self.assertTrue(digest_errors(self.m))
    def test_qcm_reordering_keeps_choice_id_semantics(self):
        p=copy.deepcopy(self.v);q=p['courses'][0]['activities'][0];old=q['activityRevisionDigest'];q['choices'].reverse();self.assertIn(q['correctChoiceId'],[x['choiceId'] for x in q['choices']]);self.assertNotEqual(old,digest(q,'activityRevisionDigest'))
class RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(c):
        path=Path(os.environ.get('LEARNIT_NEXT_ARTIFACT',ARTIFACT));require_or_skip(path.exists(),f'WAITING_FOR_INTEGRATION: {path}');require_or_skip(sync_playwright is not None,'DEPENDENCY: Playwright');c.v=load(VALID);c.l=load(LEGACY);c.m=load(MISMATCH);c.srv=serve(path);c.url=c.srv.__enter__();c.pw=sync_playwright().start()
        try:c.browser=c.pw.chromium.launch(headless=True)
        except Exception as e:c.pw.stop();c.srv.__exit__(None,None,None);require_or_skip(False,f'DEPENDENCY: Chromium: {e}')
    @classmethod
    def tearDownClass(c):
        if hasattr(c,'browser'):c.browser.close()
        if hasattr(c,'pw'):c.pw.stop()
        if hasattr(c,'srv'):c.srv.__exit__(None,None,None)
    def setUp(self):self.ctx=self.browser.new_context();self.page=self.ctx.new_page();self.page.goto(self.url);self.page.wait_for_function('()=>window.__LEARNIT_NEXT_TEST__');self.call('resetNextData')
    def tearDown(self):self.ctx.close()
    def invoke(self,op,*args):return self.page.evaluate("""async x=>{const a=window.__LEARNIT_NEXT_TEST__;if(!a||typeof a[x.op]!=='function')return{kind:'harness'};try{return{kind:'return',value:await a[x.op](...x.args)}}catch(e){return{kind:'throw',name:String(e?.name||''),code:String(e?.code||''),message:String(e?.message||e||'')}}}""",{'op':op,'args':list(args)})
    def call(self,op,*args):r=self.invoke(op,*args);self.assertEqual('return',r.get('kind'),r);return r.get('value')
    def reject(self,op,p):
        r=self.invoke(op,p);self.assertNotEqual('harness',r.get('kind'),r)
        if r.get('kind')=='return':self.assertTrue(negative(r.get('value')),r)
        else:
            self.assertEqual('throw',r.get('kind'),r);self.assertNotIn(r.get('name'),{'TypeError','ReferenceError','SyntaxError','RangeError','InternalError','Error'},r);self.assertTrue(r.get('name') in DOMAIN_ERROR_NAMES or r.get('code') in {'ERR_CONTRACT','ERR_SCHEMA','ERR_DIGEST','ERR_REVISION_CONFLICT','ERR_LEGACY','ERR_IMPORT_REJECTED'},r)
    def snap(self):return self.page.evaluate(SNAPSHOT,{'dbName':NEXT_DB,'prefix':NEXT_PREFIX})
    def atomic(self,op,p,label):b=self.snap();self.reject(op,p);self.assertEqual(b,self.snap(),label)
    def test_contract_version_and_valid_import(self):self.assertEqual('learnit.kit.v2',self.page.evaluate('()=>window.__LEARNIT_NEXT_TEST__.contractVersion'));self.assertFalse(negative(self.call('validatePackage',self.v)));self.assertFalse(negative(self.call('importPackage',self.v)));self.assertEqual(1,len(self.call('listCourses')))
    def test_schema_uuid_unknown_duplicate_and_reference_attacks(self):
        for n,p in attacks(self.v):self.atomic('validatePackage',p,'validate '+n);self.atomic('importPackage',p,'import '+n);self.assertEqual([],self.call('listCourses'))
    def test_digest_mismatch_same_revision_conflict_and_legacy_are_atomic(self):
        for n,p in [('legacy',self.l),('digest',self.m)]:self.atomic('importPackage',p,n)
        self.assertFalse(negative(self.call('importPackage',self.v)));b=self.snap();p=copy.deepcopy(self.v);p['courses'][0]['activities'][0]['prompt']+=' changed';p=redigest(p);self.reject('importPackage',p);self.assertEqual(b,self.snap())
    def test_qcm_choice_reordering_does_not_change_correction(self):
        p=copy.deepcopy(self.v);q=p['courses'][0]['activities'][0];q['choices'].reverse();q['activityRevisionId']=uid(950);p['courses'][0]['courseRevisionId']=uid(951);p['packageRevisionId']=uid(952);p=redigest(p);self.assertFalse(negative(self.call('importPackage',p)));c=self.call('listCourses')[0];self.call('startCourse',c['courseInstallId']);r=self.call('answer',q['activityRevisionId'],q['correctChoiceId']);self.assertEqual(q['activityRevisionId'],r.get('activityRevisionId'),r);self.assertIs(r.get('correct'),True);self.assertIs(r.get('completed'),True);self.assertEqual(q['correctChoiceId'],r.get('selectedChoiceId'))
if __name__=='__main__':unittest.main(verbosity=2)
