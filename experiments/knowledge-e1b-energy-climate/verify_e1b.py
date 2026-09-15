#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from authoring.v2 import validate_kit as v2
from authoring.v2.atlas import validate_atlas_content as atlas
from authoring.v2.atlas import pedagogical_quality as quality
from authoring.factory import factory_gate as factory

EXPECTED_SOURCE_SHA='cc411ddb76a904a684a44ce85be15b67a9ef9f2bc75288697a4981a62a4b0c73'
EXPECTED_SOURCE_BYTES=3042017
EXPECTED_SOURCE_PAGES=163
NAMES=[f'{route}_K{k}.json' for k in range(1,5) for route in ('DIRECT','KNOWLEDGE')]
EXPECTED_FACTORY_REASONS=['REVIEWER_REUSED_AUTHOR_ACTIVE_CONTEXT','REVIEWER_SAW_AUTHOR_SCRATCHPAD']

def load(rel): return json.loads((HERE/rel).read_text(encoding='utf-8'))
def sha256(b): return 'sha256:'+hashlib.sha256(b).hexdigest()
def git_blob(path): return subprocess.check_output(['git','hash-object',str(path)],cwd=ROOT,text=True).strip()
def fail(msg): raise SystemExit('E1B_FAIL:'+msg)

source=load('source/source-manifest.json')
if source.get('sha256')!=EXPECTED_SOURCE_SHA or source.get('bytes')!=EXPECTED_SOURCE_BYTES or source.get('pageCount')!=EXPECTED_SOURCE_PAGES: fail('SOURCE_IDENTITY')
if source.get('commitPolicy')!='SOURCE_BYTES_READ_ONLY_NOT_COMMITTED': fail('SOURCE_POLICY')
sm=load('source/source-map.json')
if sm.get('pageCount')!=163 or {a.get('kit') for a in sm.get('e1bAnchors',[])}!={'K1','K2','K3','K4'}: fail('SOURCE_MAP')
if list(HERE.rglob('*.pdf')): fail('PDF_COMMITTED')
if (HERE/'.publication-probe').exists(): fail('PUBLICATION_PROBE_PRESENT')

knowledge=load('knowledge/knowledge-bundle.json')
ids={o['id'] for o in knowledge['objects']}
if len(ids)!=21 or not knowledge.get('knowledgePathOptional'): fail('KNOWLEDGE_BUNDLE')
if len(load('knowledge/relations.json')['relations'])<8: fail('KNOWLEDGE_RELATIONS')
for k in range(1,5):
 ledger=load(f'coverage/K{k}-coverage-ledger.json')
 for item in ledger.get('items',[]):
  if item.get('class')!='TARGET_COVERAGE': continue
  disp=item.get('disposition')
  if disp=='REPRESENTED':
   if item.get('knowledgeRef') not in ids: fail(f'COVERAGE_UNKNOWN_REF:K{k}:{item.get("id")}')
  elif disp=='EXPLICITLY_EXCLUDED':
   if not str(item.get('reason','')).strip(): fail(f'COVERAGE_EXCLUSION_WITHOUT_REASON:K{k}')
  else: fail(f'COVERAGE_SILENT_LOSS:K{k}:{item.get("id")}')

freeze=load('candidate-freeze-manifest.json')
expected={Path(x['path']).name:x['gitBlobSha'] for x in freeze['candidates']}
if set(expected)!=set(NAMES): fail('FREEZE_MANIFEST_NAMES')
schema=v2.load(ROOT/'contracts/learnit-kit-v2.schema.json')
source_inventory=[{'sourceId':'epf-energie-climat','bytes':EXPECTED_SOURCE_BYTES,'sha256':'sha256:'+EXPECTED_SOURCE_SHA}]
source_set_digest=factory.sha256_bytes(factory.canonical_json_bytes(source_inventory))

for name in NAMES:
 path=HERE/'candidates'/name
 if not path.exists(): fail('MISSING_CANDIDATE:'+name)
 if git_blob(path)!=expected[name]: fail('FROZEN_GIT_BLOB_MISMATCH:'+name)
 doc=v2.load(path)
 rep=v2.validate(path,doc,schema,False)
 if rep.errors: fail('V2:'+name+':'+rep.errors[0])
 try: atlas.validate_package(doc)
 except Exception as exc: fail('ATLAS:'+name+':'+str(exc))
 q=quality.analyze_package(doc)
 if not q.get('canonicalValid') or q.get('qualityBand')!='EXCELLENT_BY_PROFILE' or q.get('counts')!={'blocking':0,'warning':0,'advice':0}: fail('M31:'+name+':'+json.dumps(q.get('counts')))
 course=doc['courses'][0]
 if course.get('estimatedMinutes')!=40 or sum(a.get('estimatedMinutes',0) for a in course['activities'])!=40: fail('DURATION:'+name)
 k=name.split('_K')[1].split('.')[0]
 brief=load(f'briefs/K{k}-learner-brief.json')
 factory.validate_brief(brief)
 kit_raw=path.read_bytes()
 brief_digest=factory.sha256_bytes(factory.canonical_json_bytes(brief))
 kit_digest=factory.sha256_bytes(kit_raw)
 context_digest=factory.sha256_bytes(factory.canonical_json_bytes({'profile':factory.FACTORY_PROFILE,'kitSha256':kit_digest,'briefSha256':brief_digest,'sourceSetDigest':source_set_digest}))
 context={'schema':factory.CONTEXT_SCHEMA,'profile':factory.FACTORY_PROFILE,'kitSha256':kit_digest,'briefSha256':brief_digest,'sources':source_inventory,'sourceSetDigest':source_set_digest,'contextDigest':context_digest}
 ev=[{'sourceId':'epf-energie-climat','locator':f'K{k}-source-scope','basis':'Exact EPF source locators recorded in source map and scope manifest.'}]
 dims={d:{'status':'pass','summary':'Comparative source-grounded review found no material defect in this dimension.','evidence':ev} for d in factory.REQUIRED_DIMENSIONS}
 review={'schema':factory.REVIEW_SCHEMA,'profile':factory.REVIEW_PROFILE,'target':{'contextDigest':context_digest,'kitSha256':kit_digest,'sourceSetDigest':source_set_digest,'briefSha256':brief_digest},'independence':{'authorScratchpadSeen':True,'authorActiveContextReused':True},'dimensions':dims,'findings':[],'limitations':['NON_INDEPENDENT_COMPARATIVE_REVIEW; not semantic certification.'],'verdict':factory.SEMANTIC_HOLD}
 factory.validate_review(review,context)
 if factory.binding_reasons(review,context): fail('FACTORY_BINDING:'+name)
 if factory.semantic_reasons(review)!=EXPECTED_FACTORY_REASONS: fail('FACTORY_REASONS:'+name)
 if q['qualityBand'] not in ('STRONG','EXCELLENT_BY_PROFILE'): fail('FACTORY_QUALITY:'+name)

for name in ('DIRECT_K4.json','KNOWLEDGE_K4.json'):
 text=(HERE/'candidates'/name).read_text(encoding='utf-8').casefold()
 for banned in ('résistance thermique','conduction stationnaire','écoulement incompressible','bernoulli','tuyère'):
  if banned in text: fail('K4_SCOPE_LEAK:'+name+':'+banned)

metrics=load('metrics/E1B_REUSE_METRICS.json')
if metrics['direct']['totalOccurrences']!=47 or metrics['direct']['uniqueObligations']!=40 or metrics['knowledgeProxy']['total']!=65: fail('METRICS_CORE')
if metrics['projectedObservedMediumOverlapBreakEvenN']!=13 or metrics['observedBreakEvenByFourKits'] is not False: fail('BREAK_EVEN')
impact=load('impact/change-impact-report.json')
if impact.get('globalInvalidation') is not False or impact.get('verdict')!='PASS_LOCALIZED_IMPACT': fail('IMPACT')
for r in impact['results']:
 if r.get('falsePositive') or r.get('falseNegative') or r.get('action')!='REVIEW_REQUIRED': fail('IMPACT_RESULT')

print('E1B_SOURCE: PASS sha256='+EXPECTED_SOURCE_SHA+' pages=163')
print('E1B_CANDIDATES: PASS 8/8 frozen Git blobs; v2=PASS; Atlas=PASS; M3.1=EXCELLENT_BY_PROFILE')
print('E1B_FACTORY_COMPARISON: HOLD_FACTORY_SEMANTIC_REVIEW expected due NON_INDEPENDENT_COMPARATIVE_REVIEW only')
print('E1B_COVERAGE: PASS K1-K4 fail-closed ledgers')
print('E1B_K4_SCOPE: PASS')
print('E1B_IMPACT: PASS localized')
print('E1B_METRICS: PASS Direct=47 KnowledgeProxy=65 projected-medium-break-even-N=13')
print('PASS_E1B_EXACT_HEAD_DETERMINISTIC_QUALIFICATION')
