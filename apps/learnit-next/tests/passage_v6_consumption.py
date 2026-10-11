#!/usr/bin/env python3
from __future__ import annotations
import base64, copy, hashlib, json, os, threading, zlib
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
ARTIFACT=Path(os.environ.get('LEARNIT_V6_ARTIFACT', ROOT/'apps/learnit-next/dist/learnit-next.html'))
R3_SHA='0ad6e8b1c8dbd5a6d4743a67daa9ad6dd6a3824086dda839746fb5e8a36ee4b2'
R3_ZLIB_B64=(Path(__file__).with_name('passage_v6_r3.zlib.b64').read_text(encoding='ascii').strip())

def canonical(v):
    return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj,key):
    x=copy.deepcopy(obj); x.pop(key,None); return 'sha256:'+hashlib.sha256(canonical(x)).hexdigest()
def redigest(pkg):
    for c in pkg['courses']:
        for a in c['activities']: a['activityRevisionDigest']=digest(a,'activityRevisionDigest')
        c['courseRevisionDigest']=digest(c,'courseRevisionDigest')
    pkg['packageRevisionDigest']=digest(pkg,'packageRevisionDigest'); return pkg

def uid(n): return f'{n:08x}-0000-4000-8000-{n:012x}'
def r3():
    raw=zlib.decompress(base64.b64decode(R3_ZLIB_B64)); assert len(raw)==41357; assert hashlib.sha256(raw).hexdigest()==R3_SHA
    return json.loads(raw)
def synthetic():
    p=r3(); c=p['courses'][0]; oid=c['objectives'][0]['objectiveId']; n=0x700000
    def common(t):
        nonlocal n; n+=1
        return {'activityLineageId':uid(n),'activityRevisionId':uid(n+1000),'activityRevisionDigest':'sha256:'+'0'*64,'objectiveIds':[oid],'type':t,'learningPhase':'application','estimatedMinutes':1}
    a=common('flashcard'); a.update(front='Question test',back='Réponse test',explanation='Explication test'); c['activities'].append(a)
    a=common('order'); a.update(prompt='Ordonner',explanation='Ordre attendu',difficulty='easy',assessmentRole='practice',items=[{'itemId':uid(n+1),'label':'A'},{'itemId':uid(n+2),'label':'B'}],correctOrder=[uid(n+1),uid(n+2)]); c['activities'].append(a)
    a=common('productive'); pid=uid(n+1); a.update(prompt='Nombre',explanation='Tolérance',difficulty='easy',assessmentRole='practice',parts=[{'partId':pid,'label':'Valeur','responseKind':'number','unitPrompt':'J'}],scoring={'aggregation':'all','evaluators':[{'partId':pid,'kind':'numeric-tolerance','expected':{'numerator':5,'denominator':1},'absoluteTolerance':{'numerator':1,'denominator':10},'acceptedUnits':['J']}]}); c['activities'].append(a)
    a=common('productive'); pid=uid(n+1); a.update(prompt='Concepts',explanation='Concepts requis',difficulty='easy',assessmentRole='practice',parts=[{'partId':pid,'label':'Texte','responseKind':'text'}],scoring={'aggregation':'all','evaluators':[{'partId':pid,'kind':'required-concepts','requiredConceptGroups':[['énergie','energie'],['système','systeme']]}]}); c['activities'].append(a)
    return redigest(p)
def answer(a):
    t=a['type']
    if t=='lesson': return {'acknowledged':True}
    if t=='flashcard': return {'revealed':True}
    if t=='qcm': return {'choiceId':a['correctChoiceId']}
    if t=='fill': return {x['slotId']:x['tokenId'] for x in a['answers']}
    if t=='matching': return {'associations':a['matches']}
    if t=='order': return {'orderedItemIds':a['correctOrder']}
    if t=='classify': return {'assignments':a['assignments']}
    if t=='productive':
        ev={x['partId']:x for x in a['scoring']['evaluators']}; out={}
        for part in a['parts']:
            e=ev[part['partId']]
            if e['kind']=='canonical-expression-set': out[part['partId']]={'value':e['acceptedExpressions'][0]}
            elif e['kind']=='numeric-tolerance': out[part['partId']]={'value':e['expected']['numerator']/e['expected']['denominator'],'unit':(e.get('acceptedUnits') or [None])[0]}
            else: out[part['partId']]={'value':' '.join(group[0] for group in e['requiredConceptGroups'])}
        return {'parts':out}
    raise AssertionError(t)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_): pass
@contextmanager
def serve(path):
    srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(path.parent))); th=threading.Thread(target=srv.serve_forever,daemon=True); th.start()
    try: yield f'http://127.0.0.1:{srv.server_port}/{path.name}'
    finally: srv.shutdown(); srv.server_close(); th.join(5)
def call(page,op,args=None):
    return page.evaluate("async ({op,args})=>{const a=window.__LEARNIT_NEXT_TEST__; return await a[op](...(args||[]));}",{'op':op,'args':args or []})
def idb_snapshot(page):
    return page.evaluate("""async()=>{const dbs=(await indexedDB.databases()).filter(x=>x.name);const out={};for(const x of dbs){const db=await new Promise((res,rej)=>{const r=indexedDB.open(x.name);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});out[x.name]={};for(const s of [...db.objectStoreNames])out[x.name][s]=await new Promise((res,rej)=>{const tx=db.transaction(s,'readonly'),r=tx.objectStore(s).getAll();r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});db.close()}return out}""")
def course_records(snapshot):
    rows=[]
    for db in snapshot.values(): rows.extend(db.get('courses',[]))
    return rows
def exercise(page,pkg):
    v=call(page,'validatePackage',[pkg]); assert v['ok'],v
    prev=call(page,'previewImport',[pkg]); assert prev['contract']=='learnit.kit.v6'
    imp=call(page,'importPackage',[pkg]); assert imp['contract']=='learnit.kit.v6'; assert len(imp['courses'])==1
    cid=imp['courses'][0]['courseInstallId']; raw=pkg['courses'][0]['activities']; s=call(page,'startCourse',[cid])
    for i,a in enumerate(raw):
        assert s['currentActivity']['activityRevisionId']==a['activityRevisionId'],(i,s['currentActivity']['activityRevisionId'],a['activityRevisionId'])
        assert s['currentActivity']['presentation']['type']==a['type']
        r=call(page,'answer',[a['activityRevisionId'],answer(a)])
        if a['type'] not in ('lesson','flashcard'): assert r['scored'] is True and r['correct'] is True,(i,a['type'],r)
        s=call(page,'getSession',[])
    assert call(page,'getProgress',[cid])['completed']==len(raw)
    snap=idb_snapshot(page); rec=[x for x in course_records(snap) if x.get('courseInstallId')==cid][0]
    assert rec['contract']=='learnit.kit.v6'; assert rec['courseRevisionId']==pkg['courses'][0]['courseRevisionId']; assert len(rec['course']['activities'])==len(raw)
    for got,exp in zip(rec['course']['activities'],raw):
        assert got['activityRevisionId']==exp['activityRevisionId']; assert got['activityRevisionDigest']==exp['activityRevisionDigest']
def main():
    assert ARTIFACT.is_file(),ARTIFACT
    exact=r3(); assert len(exact['courses'])==1 and len(exact['courses'][0]['objectives'])==9 and len(exact['courses'][0]['activities'])==21
    with serve(ARTIFACT) as url, sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True); page=browser.new_page(viewport={'width':390,'height':844}); page.goto(url); page.wait_for_function('()=>Boolean(window.__LEARNIT_NEXT_TEST__?.importPackage)')
        call(page,'resetNextData',[]); exercise(page,exact)
        call(page,'resetNextData',[]); syn=synthetic(); exercise(page,syn)
        types={a['type'] for a in syn['courses'][0]['activities']}; assert {'lesson','flashcard','qcm','fill','matching','order','classify','productive'}<=types
        before=idb_snapshot(page); bad=copy.deepcopy(syn); a=bad['courses'][0]['activities'][3]; a.clear(); a.update({'activityLineageId':uid(0x990001),'activityRevisionId':uid(0x990002),'activityRevisionDigest':'sha256:'+'0'*64,'objectiveIds':[bad['courses'][0]['objectives'][0]['objectiveId']],'type':'constructed','learningPhase':'application','estimatedMinutes':1,'prompt':'x','explanation':'x','difficulty':'easy','assessmentRole':'practice','acceptedResponses':['x']}); redigest(bad)
        v=call(page,'validatePackage',[bad]); assert not v['ok'] and any(e['code']=='activity_type_disabled' for e in v['errors'])
        try: call(page,'importPackage',[bad]); raise AssertionError('constructed import unexpectedly passed')
        except Exception: pass
        assert idb_snapshot(page)==before
        bad=copy.deepcopy(syn); bad['title']+=' tampered'; v=call(page,'validatePackage',[bad]); assert not v['ok'] and any(e['code']=='digest_mismatch' for e in v['errors'])
        bad=copy.deepcopy(syn); prod=next(a for a in bad['courses'][0]['activities'] if a['type']=='productive' and a['parts'][0]['responseKind']=='number'); prod['scoring']['evaluators'][0]={'partId':prod['parts'][0]['partId'],'kind':'required-concepts','requiredConceptGroups':[['x']]}; redigest(bad); v=call(page,'validatePackage',[bad]); assert not v['ok'] and any(e['code']=='productive_evaluator_mismatch' for e in v['errors'])
        browser.close()
    print('PASSAGE_V6_CONSUMPTION_BROWSER_PASS')
if __name__=='__main__': main()
