#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, os, threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
ARTIFACT=Path(os.environ.get('LEARNIT_V6_ARTIFACT', ROOT/'apps/learnit-next/dist/learnit-next.html'))

def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj,key):
    x=copy.deepcopy(obj); x.pop(key,None); return 'sha256:'+hashlib.sha256(canonical(x)).hexdigest()
def uid(n): return f'{n:08x}-0000-4000-8000-{n:012x}'
def redigest(pkg):
    for c in pkg['courses']:
        for a in c['activities']: a['activityRevisionDigest']=digest(a,'activityRevisionDigest')
        c['courseRevisionDigest']=digest(c,'courseRevisionDigest')
    pkg['packageRevisionDigest']=digest(pkg,'packageRevisionDigest'); return pkg

def package():
    n=0x810000; oid=uid(n+1)
    def common(t):
        nonlocal n; n+=10
        return {'activityLineageId':uid(n),'activityRevisionId':uid(n+1),'activityRevisionDigest':'sha256:'+'0'*64,'objectiveIds':[oid],'type':t,'learningPhase':'application','estimatedMinutes':1}
    acts=[]
    a=common('lesson'); a.update(title='Leçon',body='Contenu de test',keyPoints=['Point clé']); acts.append(a)
    a=common('flashcard'); a.update(front='Question',back='Réponse',explanation='Explication'); acts.append(a)
    a=common('qcm'); c1,c2=uid(n+2),uid(n+3); a.update(prompt='QCM',explanation='Explication',difficulty='easy',assessmentRole='practice',choices=[{'choiceId':c1,'label':'A'},{'choiceId':c2,'label':'B'}],correctChoiceId=c2); acts.append(a)
    a=common('fill'); slot,t1,t2=uid(n+2),uid(n+3),uid(n+4); a.update(prompt='Fill',explanation='Explication',difficulty='easy',assessmentRole='practice',segments=[{'text':'Valeur '},{'slotId':slot}],tokens=[{'tokenId':t1,'label':'A','maxUses':1},{'tokenId':t2,'label':'B','maxUses':1}],answers=[{'slotId':slot,'tokenId':t2}]); acts.append(a)
    a=common('matching'); l1,l2,r1,r2=[uid(n+i) for i in range(2,6)]; a.update(prompt='Matching',explanation='Explication',difficulty='easy',assessmentRole='practice',leftItems=[{'itemId':l1,'label':'L1'},{'itemId':l2,'label':'L2'}],rightItems=[{'itemId':r1,'label':'R1'},{'itemId':r2,'label':'R2'}],matches=[{'leftItemId':l1,'rightItemId':r2},{'leftItemId':l2,'rightItemId':r1}]); acts.append(a)
    a=common('order'); i1,i2=uid(n+2),uid(n+3); a.update(prompt='Order',explanation='Explication',difficulty='easy',assessmentRole='practice',items=[{'itemId':i1,'label':'A'},{'itemId':i2,'label':'B'}],correctOrder=[i2,i1]); acts.append(a)
    a=common('classify'); b1,b2,i1,i2=[uid(n+i) for i in range(2,6)]; a.update(prompt='Classify',explanation='Explication',difficulty='easy',assessmentRole='practice',buckets=[{'bucketId':b1,'label':'B1'},{'bucketId':b2,'label':'B2'}],items=[{'itemId':i1,'label':'I1'},{'itemId':i2,'label':'I2'}],assignments=[{'itemId':i1,'bucketId':b2},{'itemId':i2,'bucketId':b1}]); acts.append(a)
    a=common('productive'); p=uid(n+2); a.update(prompt='Expression',explanation='Explication',difficulty='easy',assessmentRole='practice',parts=[{'partId':p,'label':'Expr','responseKind':'expression'}],scoring={'aggregation':'all','evaluators':[{'partId':p,'kind':'canonical-expression-set','acceptedExpressions':['x+y','y+x']}]}); acts.append(a)
    a=common('productive'); p=uid(n+2); a.update(prompt='Nombre',explanation='Explication',difficulty='easy',assessmentRole='practice',parts=[{'partId':p,'label':'Valeur','responseKind':'number','unitPrompt':'J'}],scoring={'aggregation':'all','evaluators':[{'partId':p,'kind':'numeric-tolerance','expected':{'numerator':5,'denominator':1},'absoluteTolerance':{'numerator':1,'denominator':10},'acceptedUnits':['J']}]}); acts.append(a)
    a=common('productive'); p=uid(n+2); a.update(prompt='Texte',explanation='Explication',difficulty='easy',assessmentRole='practice',parts=[{'partId':p,'label':'Texte','responseKind':'text'}],scoring={'aggregation':'all','evaluators':[{'partId':p,'kind':'required-concepts','requiredConceptGroups':[['énergie','energie'],['système','systeme']]}]}); acts.append(a)
    pkg={'contract':'learnit.kit.v6','packageLineageId':uid(0x820001),'packageRevisionId':uid(0x820002),'packageRevisionDigest':'sha256:'+'0'*64,'title':'PASSAGE V6 CI fixture','versionLabel':'R2-CI','language':'fr','courses':[{'courseLineageId':uid(0x820003),'courseRevisionId':uid(0x820004),'courseRevisionDigest':'sha256:'+'0'*64,'title':'V6 consumer fixture','estimatedMinutes':20,'objectives':[{'objectiveId':oid,'label':'Objectif'}],'activities':acts}]}
    return redigest(pkg)

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
        e=a['scoring']['evaluators'][0]; pid=a['parts'][0]['partId']
        if e['kind']=='canonical-expression-set': return {'parts':{pid:{'value':e['acceptedExpressions'][0]}}}
        if e['kind']=='numeric-tolerance': return {'parts':{pid:{'value':5,'unit':'J'}}}
        return {'parts':{pid:{'value':'énergie système'}}}
    raise AssertionError(t)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_): pass
@contextmanager
def serve(path):
    srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(path.parent))); th=threading.Thread(target=srv.serve_forever,daemon=True); th.start()
    try: yield f'http://127.0.0.1:{srv.server_port}/{path.name}'
    finally: srv.shutdown(); srv.server_close(); th.join(5)
def call(page,op,args=None): return page.evaluate("async ({op,args})=>await window.__LEARNIT_NEXT_TEST__[op](...(args||[]))",{'op':op,'args':args or []})
def snapshot(page):
    return page.evaluate("""async()=>{const out={};for(const x of (await indexedDB.databases()).filter(x=>x.name)){const db=await new Promise((res,rej)=>{const r=indexedDB.open(x.name);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});out[x.name]={};for(const s of [...db.objectStoreNames])out[x.name][s]=await new Promise((res,rej)=>{const tx=db.transaction(s,'readonly'),r=tx.objectStore(s).getAll();r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});db.close()}return out}""")
def course_records(s):
    return [row for db in s.values() for row in db.get('courses',[])]

def main():
    assert ARTIFACT.is_file(), ARTIFACT
    pkg=package(); expected_types={'lesson','flashcard','qcm','fill','matching','order','classify','productive'}
    assert expected_types=={a['type'] for a in pkg['courses'][0]['activities']}
    with serve(ARTIFACT) as url, sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True); page=browser.new_page(viewport={'width':390,'height':844}); page.goto(url); page.wait_for_function('()=>Boolean(window.__LEARNIT_NEXT_TEST__?.importPackage)')
        call(page,'resetNextData'); v=call(page,'validatePackage',[pkg]); assert v['ok'],v; assert call(page,'previewImport',[pkg])['contract']=='learnit.kit.v6'; imp=call(page,'importPackage',[pkg]); assert imp['contract']=='learnit.kit.v6'
        cid=imp['courses'][0]['courseInstallId']; s=call(page,'startCourse',[cid])
        for a in pkg['courses'][0]['activities']:
            assert s['currentActivity']['activityRevisionId']==a['activityRevisionId']; assert s['currentActivity']['presentation']['type']==a['type']; r=call(page,'answer',[a['activityRevisionId'],answer(a)])
            if a['type'] not in ('lesson','flashcard'): assert r['scored'] is True and r['correct'] is True,(a['type'],r)
            s=call(page,'getSession')
        assert call(page,'getProgress',[cid])['completed']==len(pkg['courses'][0]['activities'])
        rec=next(x for x in course_records(snapshot(page)) if x.get('courseInstallId')==cid); assert rec['contract']=='learnit.kit.v6'; assert rec['courseRevisionId']==pkg['courses'][0]['courseRevisionId']
        for got,exp in zip(rec['course']['activities'],pkg['courses'][0]['activities']): assert (got['activityRevisionId'],got['activityRevisionDigest'])==(exp['activityRevisionId'],exp['activityRevisionDigest'])
        before=snapshot(page)
        bad=copy.deepcopy(pkg); a=bad['courses'][0]['activities'][0]; a.clear(); a.update({'activityLineageId':uid(0x990001),'activityRevisionId':uid(0x990002),'activityRevisionDigest':'sha256:'+'0'*64,'objectiveIds':[bad['courses'][0]['objectives'][0]['objectiveId']],'type':'constructed','learningPhase':'application','estimatedMinutes':1,'prompt':'x','explanation':'x','difficulty':'easy','assessmentRole':'practice','acceptedResponses':['x']}); redigest(bad); v=call(page,'validatePackage',[bad]); assert not v['ok'] and any(e['code']=='activity_type_disabled' for e in v['errors'])
        try: call(page,'importPackage',[bad]); raise AssertionError('constructed unexpectedly imported')
        except Exception: pass
        assert snapshot(page)==before
        bad=copy.deepcopy(pkg); bad['title']+=' tampered'; v=call(page,'validatePackage',[bad]); assert not v['ok'] and any(e['code']=='digest_mismatch' for e in v['errors'])
        bad=copy.deepcopy(pkg); prod=next(a for a in bad['courses'][0]['activities'] if a['type']=='productive' and a['parts'][0]['responseKind']=='number'); prod['scoring']['evaluators'][0]={'partId':prod['parts'][0]['partId'],'kind':'required-concepts','requiredConceptGroups':[['x']]}; redigest(bad); v=call(page,'validatePackage',[bad]); assert not v['ok'] and any(e['code']=='productive_evaluator_mismatch' for e in v['errors'])
        browser.close()
    print('PASSAGE_V6_CONSUMPTION_BROWSER_PASS')
if __name__=='__main__': main()
