#!/usr/bin/env python3
"""Independent contradictory QA for Project Atlas M1 (issue #130)."""
from __future__ import annotations
import hashlib,json,os,re,shutil,subprocess,tempfile,unittest
from pathlib import Path
try:
 from playwright.sync_api import sync_playwright
except ImportError: sync_playwright=None
ROOT=Path(os.environ.get('ATLAS_PRODUCT_TREE',Path(__file__).resolve().parents[3])).resolve()
VALID=ROOT/'contracts/fixtures/atlas-m1-valid-loop.json'; INVALID=ROOT/'contracts/fixtures/atlas-m1-invalid-loop.json'
ARTIFACT=Path(os.environ.get('ATLAS_ARTIFACT',ROOT/'apps/learnit-next/dist/learnit-next.html')).resolve()
BASE='58e39e8917006058fdf177a5daa37535f5e2c78d'; STRICT=os.environ.get('ATLAS_QA_STRICT')=='1'; BSTRICT=os.environ.get('ATLAS_QA_BROWSER_STRICT')=='1'
HEAD=os.environ.get('ATLAS_EXPECTED_HEAD',''); ART_SHA=os.environ.get('ATLAS_EXPECTED_ARTIFACT_SHA256','')
CODES={'NEW_OBJECTIVE','PRACTICE_IN_PROGRESS','RECENT_ERROR','REVIEW_REQUIRED','CORRECTION_COMPLETED','NO_INDEPENDENT_VALIDATION','VALIDATION_AVAILABLE','RECENTLY_VALIDATED','SESSION_TIME_LIMIT'}
RISKS=(
 'deterministic plan divergence','runtime network or remote AI','invalid duplicate contradictory rewritten events','fabricated non-applicable identifiers',
 'practice credited as validation','correction shown as durable mastery or certification','missing or non-canonical reasonCodes','plan duration overrun',
 'loss on interruption close reopen export import','reward from clicks time or trivial repetition','corrupt or partial data accepted','cross-kit identity leakage',
 'ambient clock bypass','Windows and Android incompatibility')
MODULES=['core/atlas_events.js','core/atlas_projection.js','core/atlas_clock.js','core/atlas_evidence.js','core/atlas_recommendation.js','core/atlas_planner.js','ports/atlas_storage.js','adapters/atlas_indexeddb.js']
CLAIM=re.compile(r'(?i)ma[iî]trise durable|mastered|certification|r[ée]tention (?:acquise|garantie)')
NET=re.compile(r'(?m)\bfetch\s*\(|\bXMLHttpRequest\s*\(|\bnew\s+(?:WebSocket|EventSource)\s*\(|navigator\.sendBeacon\s*\(|https?://(?!localhost|127\.0\.0\.1)')
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*a):
 r=subprocess.run(a,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False,timeout=180)
 if r.returncode: raise AssertionError(r.stdout)
 return r.stdout.strip()
def require(case):
 missing=[ROOT/'apps/learnit-next/src'/p for p in MODULES if not (ROOT/'apps/learnit-next/src'/p).is_file()]
 if not missing:return
 msg='candidate absent: '+','.join(str(p.relative_to(ROOT)) for p in missing)
 case.fail(msg) if STRICT else case.skipTest(msg)
def event_errors(e):
 if not isinstance(e,dict):return ['object']
 common={'eventId','eventVersion','occurredAt','kind','sessionId','metadata'}
 if common-e.keys():return ['common']
 k=e['kind']; ids={'courseLineageId','objectiveId','activityLineageId'}
 if k=='activity-attempt':
  req=ids|{'assessmentRole','outcome','assistance'}
  return ['attempt'] if req-e.keys() or e.get('assessmentRole') not in {'practice','validation'} or e.get('outcome') not in {'correct','incorrect'} else []
 if k=='activity-corrected':
  req=ids|{'assessmentRole','outcome','assistance'}
  return ['correction'] if req-e.keys() or (e.get('assessmentRole'),e.get('outcome'),e.get('assistance'))!=('practice','completed','review') else []
 if k=='session-started':return ['fabricated'] if ids&e.keys() or any(x in e for x in ('assessmentRole','outcome','assistance')) else []
 if k=='session-interrupted':
  present=ids&e.keys(); return ['interrupted'] if e.get('outcome')!='interrupted' or (present and present!=ids) else []
 if k=='session-completed':return ['completed'] if e.get('outcome')!='completed' or ids&e.keys() else []
 return ['kind']
def project(oid,events):
 p={'practiceAttempts':0,'latestPracticeCorrect':None,'needsReview':False,'correctionsCompleted':0,'validationAttempts':0,'latestValidationCorrect':None,'state':'not-started'}
 for e in sorted((x for x in events if x.get('objectiveId')==oid),key=lambda x:(x['occurredAt'],x['eventId'])):
  if e['kind']=='activity-attempt':
   key='practice' if e['assessmentRole']=='practice' else 'validation'; p[key+'Attempts']+=1;p['latest'+key.title()+'Correct']=e['outcome']=='correct';p['needsReview']=e['outcome']=='incorrect'
  elif e['kind']=='activity-corrected':p['correctionsCompleted']+=1;p['needsReview']=False
 p['state']='review-needed' if p['needsReview'] else 'validated-recently' if p['validationAttempts'] and p['latestValidationCorrect'] else 'ready-for-validation' if p['practiceAttempts'] or p['correctionsCompleted'] else 'not-started'
 return p
NODE=r"""
import assert from'node:assert/strict';import fs from'node:fs';import{pathToFileURL}from'node:url';
const root=process.env.ATLAS_PRODUCT_TREE,f=JSON.parse(fs.readFileSync(process.env.ATLAS_VALID,'utf8')),bad=JSON.parse(fs.readFileSync(process.env.ATLAS_INVALID,'utf8')),calls=[];
globalThis.fetch=(...a)=>{calls.push(a);throw Error('NETWORK')};
const imp=async p=>import(pathToFileURL(`${root}/apps/learnit-next/src/${p}`).href),E=await imp('core/atlas_events.js'),P=await imp('core/atlas_projection.js'),R=await imp('core/atlas_recommendation.js'),S=await imp('core/atlas_planner.js');
const pick=(m,n)=>{for(const x of n)if(typeof m[x]=='function')return m[x];throw Error(`missing export ${n}`)},tryc=async cs=>{let es=[];for(const c of cs)try{return await c()}catch(e){es.push(e.message)}throw Error(es.join('|'))};
const ve=pick(E,['validateLearningEvent','normalizeLearningEvent','assertLearningEvent','createLearningEvent']),pe=pick(P,['projectObjectiveEvidence','reduceObjectiveEvidence','replayObjectiveEvidence','projectLearningEvents']),rr=pick(R,['buildLearningRecommendations','createLearningRecommendations','rankLearningRecommendations','recommendLearningActions']),sp=pick(S,['buildSessionPlan','createSessionPlan','planSession']);
for(const e of f.events)await ve(structuredClone(e));for(const c of bad.cases.filter(x=>x.category=='event-validation')){let ok=false;try{await ve(c.input)}catch{ok=true}assert.ok(ok,c.id)}
const oid=f.kits[0].objectives[0].objectiveId,ev=f.events.filter(x=>x.objectiveId==oid),proj=async x=>tryc([()=>pe(oid,x),()=>pe(x,oid),()=>pe({objectiveId:oid,events:x})]);
const one=x=>Array.isArray(x)?x.find(y=>y.objectiveId==oid):x.objectiveId==oid?x:x.objectives?.find(y=>y.objectiveId==oid),p=one(await proj(ev));assert.equal(p.validationAttempts,1);assert.equal(p.state,'validated-recently');
const q=one(await proj(ev.filter(x=>x.assessmentRole!='validation')));assert.equal(q.validationAttempts,0);assert.notEqual(q.state,'validated-recently');
const evidence=f.kits.flatMap(k=>k.objectives.map(o=>o.objectiveId==oid?p:{objectiveId:o.objectiveId,state:'not-started',practiceAttempts:0,validationAttempts:0,needsReview:false})),content={kits:f.kits,activities:f.kits.flatMap(k=>k.activities)};
let rec=await tryc([()=>rr({evidence,content,now:f.controlledClock,engineVersion:f.engineVersion}),()=>rr(evidence,content,f.controlledClock),()=>rr(content,evidence,f.controlledClock)]);rec=Array.isArray(rec)?rec:rec.recommendations||[rec];for(const x of rec){assert.ok(x.reasonCodes?.length);for(const c of x.reasonCodes)assert.ok(f.canonicalReasonCodes.includes(c))}
for(const d of f.durationsMinutes){const make=async()=>tryc([()=>sp({recommendations:rec,durationMinutes:d,generatedAt:f.controlledClock,engineVersion:f.engineVersion,content}),()=>sp(rec,d,f.controlledClock,f.engineVersion),()=>sp(d,rec,f.controlledClock,f.engineVersion)]);let a=await make(),b=await make();a=a.plan||a;b=b.plan||b;assert.deepEqual(a,b);assert.equal(a.planId,b.planId);assert.ok(a.items.reduce((s,x)=>s+x.estimatedMinutes,0)<=d)}assert.deepEqual(calls,[]);console.log(JSON.stringify({ok:true}));
"""
class Prep(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.v=load(VALID);c.i=load(INVALID)
 def test_00_risks_frozen(self):self.assertEqual(14,len(RISKS));self.assertEqual(14,len(set(RISKS)))
 def test_01_two_kits_clock_codes(self):
  self.assertEqual([5,15,30],self.v['durationsMinutes']);self.assertEqual(CODES,set(self.v['canonicalReasonCodes']));self.assertEqual(2,len({k['courseLineageId'] for k in self.v['kits']}))
  for k in self.v['kits']:
   ids={o['objectiveId'] for o in k['objectives']};roles={i:set() for i in ids}
   for a in k['activities']:roles[a['objectiveId']].add(a['assessmentRole'])
   self.assertTrue(all(x=={'practice','validation'} for x in roles.values()))
 def test_02_valid_events_and_order(self):
  self.assertEqual(len(self.v['events']),len({e['eventId'] for e in self.v['events']}))
  for e in self.v['events']:self.assertEqual([],event_errors(e),e['eventId'])
  self.assertEqual(self.v['expected']['orderedEventIds'],[e['eventId'] for e in sorted(self.v['events'],key=lambda x:(x['occurredAt'],x['eventId']))])
 def test_03_independent_projection(self):
  for oid,want in self.v['expected']['objectiveEvidence'].items():
   got=project(oid,self.v['events'])
   for k,v in want.items():self.assertEqual(v,got[k],f'{oid}.{k}')
 def test_04_invalid_coverage(self):
  cats={x['category'] for x in self.i['cases']};self.assertEqual({'event-validation','projection-integrity','journal-integrity','recommendation-integrity','planning-integrity','reward-integrity','persistence-integrity','claim-integrity','network-integrity'},cats)
  for c in [x for x in self.i['cases'] if x['category']=='event-validation']:self.assertTrue(event_errors(c['input']),c['id'])
 def test_05_claim_and_reward_boundaries(self):
  self.assertIsNone(CLAIM.search(VALID.read_text()));self.assertTrue(CLAIM.search(INVALID.read_text()));self.assertIn('click-count',self.v['expected']['rewardIneligibleSignals'])
class Candidate(unittest.TestCase):
 def test_10_exact_head(self):
  require(self)
  if not HEAD:self.fail('ATLAS_EXPECTED_HEAD required') if STRICT else self.skipTest('head not supplied')
  self.assertEqual(HEAD,run('git','rev-parse','HEAD'))
 def test_11_static_no_network_llm_or_claim(self):
  require(self);bad=[]
  for p in MODULES:
   t=(ROOT/'apps/learnit-next/src'/p).read_text()
   if NET.search(t):bad.append(p+':network')
   if re.search(r'(?i)\b(openai|anthropic|gemini|chatgpt|llm)\b',t):bad.append(p+':ai')
   if CLAIM.search(t):bad.append(p+':claim')
  self.assertEqual([],bad)
 def test_12_behavior_matrix(self):
  require(self);node=shutil.which('node');self.assertIsNotNone(node)
  with tempfile.TemporaryDirectory() as d:
   h=Path(d)/'h.mjs';h.write_text(NODE);env={**os.environ,'ATLAS_PRODUCT_TREE':str(ROOT),'ATLAS_VALID':str(VALID),'ATLAS_INVALID':str(INVALID)}
   r=subprocess.run([node,str(h)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,check=False,timeout=240)
  self.assertEqual(0,r.returncode,r.stdout);self.assertTrue(json.loads(r.stdout.splitlines()[-1])['ok'])
 def test_13_exact_artifact(self):
  require(self)
  if not ARTIFACT.is_file():self.fail('artifact absent') if STRICT else self.skipTest('artifact absent')
  if not ART_SHA:self.fail('ATLAS_EXPECTED_ARTIFACT_SHA256 required') if STRICT else self.skipTest('digest not supplied')
  self.assertEqual(ART_SHA.lower(),digest(ARTIFACT))
class Browser(unittest.TestCase):
 def test_20_windows_android_offline(self):
  if not ARTIFACT.is_file() or sync_playwright is None:self.fail('artifact+Playwright required') if BSTRICT else self.skipTest('artifact+Playwright absent')
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True)
   for n,v in [('windows',{'width':1440,'height':900}),('android',{'width':390,'height':844})]:
    page=b.new_page(viewport=v);blocked=[];page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(('file:','data:','blob:')) else (blocked.append(route.request.url),route.abort())[1]);page.goto(ARTIFACT.as_uri());page.wait_for_load_state('domcontentloaded');self.assertEqual([],blocked,n);self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth'),1,n);self.assertIsNone(CLAIM.search(page.locator('body').inner_text()));page.close()
   b.close()
if __name__=='__main__':unittest.main(verbosity=2)
