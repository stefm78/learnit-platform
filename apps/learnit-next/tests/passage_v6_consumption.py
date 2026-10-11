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
R3_ZLIB_B64='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[... content abridged in this view ...]';

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
