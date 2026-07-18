#!/usr/bin/env python3
"""Strict mode-aware CI gate for the released Learn-it Next artifact."""
from __future__ import annotations
import argparse,hashlib,importlib.metadata,json,os,platform,re,shutil,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];APP=ROOT/'apps/learnit-next'
MANIFEST=APP/'source_manifest.json';REPORT=APP/'.agent-result/run_checks.json'
ART=Path('apps/learnit-next/dist/learnit-next.html');SELF='apps/learnit-next/source_manifest.json'
BASE='b83fa032b262ce41a82f5a3664a7b854e8ab8296';RELEASE_MERGE='0604cad79a8ca765148c30090906b9f658af7109'
ACCEPTED_INTEGRATION_HEAD='e5ee65a37326f4861d33c3c80221527511a03f24'
INPUTS={'runtime':'7156749815fd727076786f9939aa4d7d78b8aa6d','authoring':'2cff1f7575b509d47095df7130137cf78276e58f','qa':'09da6c44741fd1421175f6d0feef0cab4b7761b1'}
REVIEWS={'runtime':4713406180,'authoring':4704571690,'qa':4711673437}
INTEGRATOR={'.github/workflows/learnit-next-ci.yml','apps/learnit-next/build.py','apps/learnit-next/dev/release.py','apps/learnit-next/dev/run_checks.py',SELF}
CI_ALLOWLIST={'.github/workflows/learnit-next-ci.yml','apps/learnit-next/dev/run_checks.py','apps/learnit-next/tests/build_determinism.py',SELF}
ROLE={
'runtime':{'apps/learnit-next/README.md','apps/learnit-next/index.template.html','apps/learnit-next/src/styles.css','apps/learnit-next/src/main.js','apps/learnit-next/src/core/canonical_json.js','apps/learnit-next/src/core/identity.js','apps/learnit-next/src/core/contract.js','apps/learnit-next/src/core/import.js','apps/learnit-next/src/core/library.js','apps/learnit-next/src/core/session.js','apps/learnit-next/src/core/progress.js','apps/learnit-next/src/ports/storage.js','apps/learnit-next/src/adapters/indexeddb.js','apps/learnit-next/src/ui/render.js'},
'authoring':{'authoring/v2/README.md','authoring/v2/generate_ids.py','authoring/v2/validate_kit.py','authoring/v2/golden/nombres_complexes.json','authoring/v2/golden/signaux_electriques.json'},
'qa':{'contracts/fixtures/v2-valid-minimal.json','contracts/fixtures/v2-invalid-legacy.json','contracts/fixtures/v2-invalid-digest-mismatch.json','apps/learnit-next/tests/contract_v2.py','apps/learnit-next/tests/storage_isolation.py','apps/learnit-next/tests/browser_vertical_slice.py','apps/learnit-next/tests/build_determinism.py'}}
SCHEMA='contracts/learnit-kit-v2.schema.json';VALID_MODES={'integration-head','post-merge','maintenance-pr'}
JS=sorted(p for p in ROLE['runtime'] if p.endswith('.js'));EXPECTED_BYTES=84060;BASELINE_TESTS=30

class GateError(RuntimeError):
 def __init__(self,message,stage,classification):super().__init__(message);self.stage=stage;self.classification=classification
def fail(message,stage,classification):raise GateError(message,stage,classification)
def sha(data):return hashlib.sha256(data).hexdigest()
def blob_sha(data):return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
def run(cmd,cwd=ROOT,env=None,timeout=1200):
 p=subprocess.run(cmd,cwd=cwd,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1',**(env or {})},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,check=False)
 return {'command':cmd,'returnCode':p.returncode,'output':p.stdout,'outputSha256':sha(p.stdout.encode())}
def need(result,label,stage,classification):
 if result['returnCode']:fail(f"{label} failed ({result['returnCode']}):\n{result['output']}",stage,classification)
def git(*args):
 r=run(['git',*args],timeout=120);need(r,'git '+' '.join(args),'topology','TOPOLOGY_FAILURE');return r['output'].strip()
def ancestor(a,b):
 r=run(['git','merge-base','--is-ancestor',a,b],timeout=120)
 if r['returnCode'] in (0,1):return r['returnCode']==0
 fail(r['output'],'topology','TOPOLOGY_FAILURE')
def gbytes(*args):
 p=subprocess.run(['git',*args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
 if p.returncode:fail(p.stderr.decode('utf-8','replace'),'provenance','PROVENANCE_FAILURE')
 return p.stdout
def self_digest(m):
 c=json.loads(json.dumps(m,ensure_ascii=False));hits=[x for x in c['workingFiles'] if x['path']==SELF]
 if len(hits)!=1:fail('manifest self path is not unique','provenance','PROVENANCE_FAILURE')
 hits[0]['fingerprint']['value']=None
 return sha(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def inventory():
 out={SCHEMA,*INTEGRATOR}
 for paths in ROLE.values():out|=paths
 return out
def validate_manifest(m):
 if m.get('acceptedInputs')!=INPUTS or m.get('acceptedReviews')!=REVIEWS:fail('immutable inputs or reviews differ','provenance','PROVENANCE_FAILURE')
 if m.get('integrationOrder')!=['frozen-contract','qa','authoring','runtime','integrator']:fail('integration order differs','provenance','PROVENANCE_FAILURE')
 items=m.get('workingFiles',[]);paths=[x.get('path') for x in items]
 if m.get('fileBudget')!=32 or len(items)!=32 or len(set(paths))!=32 or set(paths)!=inventory():fail('exact 32-file inventory differs','provenance','PROVENANCE_FAILURE')
 by={x['path']:x for x in items};s=by[SELF]
 if s['fingerprint']['kind']!='canonical-self-sha256' or s['fingerprint']['value']!=self_digest(m):fail('manifest self fingerprint is stale','provenance','PROVENANCE_FAILURE')
 return items,by

def integration_topology(base_ref):
 if git('rev-parse',base_ref)!=BASE:fail('frozen base moved','topology','TOPOLOGY_FAILURE')
 parents=git('show','-s','--format=%P','HEAD').split();expected=[BASE,INPUTS['qa'],INPUTS['authoring'],INPUTS['runtime']]
 if parents!=expected:fail(f'parent order differs: {parents}','topology','TOPOLOGY_FAILURE')
 if git('merge-base',base_ref,'HEAD')!=BASE:fail('base is not first-parent merge base','topology','TOPOLOGY_FAILURE')
 changed=[x for x in git('diff','--name-only',f'{base_ref}...HEAD').splitlines() if x]
 if len(changed)!=5 or set(changed)!=INTEGRATOR:fail(f'integrator diff differs: {changed}','provenance','PROVENANCE_FAILURE')
 return {'parents':parents,'changedPaths':sorted(changed),'changedPathCount':5}
def post_merge_topology(expected):
 if not expected:fail('post-merge mode requires --accepted-integration-head','configuration','CONFIGURATION_FAILURE')
 parents=git('show','-s','--format=%P','HEAD').split()
 if len(parents)!=2:fail(f'post-merge commit must have exactly two parents: {parents}','topology','TOPOLOGY_FAILURE')
 if parents[1]!=expected:fail(f'wrong accepted integration head: expected={expected} actual={parents[1]}','provenance','PROVENANCE_FAILURE')
 if not ancestor(BASE,parents[0]):fail(f'post-merge first parent does not descend from frozen base: {parents[0]}','topology','TOPOLOGY_FAILURE')
 paths=['apps/learnit-next/index.template.html','apps/learnit-next/src','apps/learnit-next/build.py',SCHEMA]
 divergence=[x for x in git('diff','--name-only',expected,'HEAD','--',*paths).splitlines() if x]
 if divergence:fail(f'executable tree divergence from accepted integration head: {divergence}','provenance','EXECUTABLE_TREE_DIVERGENCE')
 return {'parents':parents,'acceptedIntegrationHead':expected,'firstParent':parents[0],'executableTreeDivergence':[]}
def maintenance_topology(base_ref):
 base=git('rev-parse',base_ref)
 if not ancestor(RELEASE_MERGE,base):fail(f'maintenance base does not descend from released baseline: {base}','topology','MAINTENANCE_TOPOLOGY_FAILURE')
 if not ancestor(base,'HEAD'):fail(f'maintenance branch is not synchronized with reviewed base: {base}','topology','MAINTENANCE_TOPOLOGY_FAILURE')
 merge_base=git('merge-base',base_ref,'HEAD')
 if merge_base!=base:fail(f'maintenance merge base differs: expected={base} actual={merge_base}','topology','MAINTENANCE_TOPOLOGY_FAILURE')
 changed=[x for x in git('diff','--name-only',f'{base_ref}...HEAD').splitlines() if x]
 if len(changed)!=4 or set(changed)!=CI_ALLOWLIST:fail(f'maintenance diff differs from exact CI allowlist: {changed}','provenance','MAINTENANCE_SCOPE_FAILURE')
 statuses={}
 for line in filter(None,git('diff','--name-status',f'{base_ref}...HEAD').splitlines()):
  parts=line.split('\t')
  if len(parts)!=2:fail(f'unsupported maintenance diff status line: {line}','provenance','MAINTENANCE_SCOPE_FAILURE')
  statuses[parts[1]]=parts[0]
 if set(statuses)!=CI_ALLOWLIST or any(v!='M' for v in statuses.values()):fail(f'maintenance paths must be modifications only: {statuses}','provenance','MAINTENANCE_SCOPE_FAILURE')
 return {'maintenanceBaseRef':base_ref,'maintenanceBaseCommit':base,'releasedBaseline':RELEASE_MERGE,'changedPaths':sorted(changed),'changedPathCount':4,'pathStatuses':dict(sorted(statuses.items()))}

def provenance(m,mode,base_ref,expected):
 items,by=validate_manifest(m)
 topo=integration_topology(base_ref) if mode=='integration-head' else post_merge_topology(expected) if mode=='post-merge' else maintenance_topology(base_ref)
 if git('status','--porcelain'):fail('repository dirty before checks','provenance','PROVENANCE_FAILURE')
 schema_blob=git('rev-parse',f'{BASE}:{SCHEMA}')
 if by[SCHEMA]['fingerprint']['value']!=schema_blob:fail('frozen schema differs','provenance','PROVENANCE_FAILURE')
 proof={}
 for owner,owned in ROLE.items():
  if {x['path'] for x in items if x.get('owner')==owner}!=owned:fail(f'{owner} inventory differs','provenance','PROVENANCE_FAILURE')
  files={}
  for path in sorted(owned):
   declared=by[path]['fingerprint']['value'];accepted=git('rev-parse',f'{INPUTS[owner]}:{path}')
   if blob_sha(gbytes('cat-file','blob',accepted))!=accepted:fail(f'{owner} accepted blob cannot be reproduced: {path}','provenance','PROVENANCE_FAILURE')
   if path.endswith('/build_determinism.py'):
    current=git('rev-parse',f'HEAD:{path}')
    if declared!=current:fail(f'CI-WP-001 test fingerprint stale: {path}','provenance','PROVENANCE_FAILURE')
    files[path]={'acceptedBaselineBlobSha1':accepted,'materializedBlobSha1':current,'identicalToAcceptedBaseline':current==accepted,'authorizedOverride':'CI-WP-001'}
   else:
    if declared!=accepted:fail(f'{owner} blob differs: {path}','provenance','PROVENANCE_FAILURE')
    files[path]={'acceptedBlobSha1':accepted,'materializedBlobSha1':accepted,'identical':True}
  proof[owner]={'commit':INPUTS[owner],'reviewId':REVIEWS[owner],'files':files}
 if {x['path'] for x in items if x.get('owner')=='integrator'}!=INTEGRATOR:fail('integrator inventory differs','provenance','PROVENANCE_FAILURE')
 for path in INTEGRATOR-{SELF}:
  if by[path]['fingerprint']['value']!=git('rev-parse',f'HEAD:{path}'):fail(f'integrator fingerprint stale: {path}','provenance','PROVENANCE_FAILURE')
 return {'mode':mode,'baseCommit':BASE,'sourceCommit':git('rev-parse','HEAD'),**topo,'manifestBudget':32,'roleFileCount':26,'roleFiles':proof,'schema':{'path':SCHEMA,'acceptedBlobSha1':schema_blob,'materializedBlobSha1':schema_blob,'identical':True}}

def materialize(dst,m):
 root=dst/'repo'
 def ignore(directory,names):
  out={'.git','__pycache__','.pytest_cache'}&set(names)
  if Path(directory).name=='learnit-next':out|={'dist','release','.agent-runtime','.agent-result'}&set(names)
  return out
 shutil.copytree(ROOT,root,ignore=ignore)
 for item in m['workingFiles']:
  if item.get('owner') in ROLE or item['path']==SCHEMA:
   target=root/item['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(gbytes('cat-file','blob',item['fingerprint']['value']))
 for item in m['workingFiles']:
  path=root/item['path']
  if not path.is_file():fail(f"materialized file missing: {item['path']}",'build','BUILD_FAILURE')
  if item['path']!=SELF and blob_sha(path.read_bytes())!=item['fingerprint']['value']:fail(f"materialized fingerprint differs: {item['path']}",'build','BUILD_FAILURE')
 return root
def build(root):
 r=run([sys.executable,'apps/learnit-next/build.py'],root,timeout=300);need(r,'build','build','BUILD_FAILURE');data=(root/ART).read_bytes()
 return {'sha256':sha(data),'bytes':len(data),'data':data,'command':r}
def test_count(output,label):
 m=re.search(r'Ran\s+(\d+)\s+tests?',output)
 if not m:fail(f'{label} did not report an executed test count:\n{output}','product','PRODUCT_TEST_FAILURE')
 return int(m.group(1))
def checks(report,m):
 with tempfile.TemporaryDirectory() as raw:
  a=materialize(Path(raw)/'a',m);b=materialize(Path(raw)/'b',m);ba=build(a);bb=build(b)
  if ba['data']!=bb['data']:fail('clean builds differ byte-for-byte','build','BUILD_FAILURE')
  if ba['sha256']!=m['artifact']['sha256']:fail('manifest artifact digest differs','build','BUILD_FAILURE')
  if ba['bytes']!=EXPECTED_BYTES:fail(f"released artifact size differs: {ba['bytes']}",'build','BUILD_FAILURE')
  report['cleanBuilds']={'builds':[{'name':'clean-1',**{k:v for k,v in ba.items() if k!='data'}},{'name':'clean-2',**{k:v for k,v in bb.items() if k!='data'}}],'byteForByteIdentical':True}
  out=ROOT/ART;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(ba['data']);tested=sha(out.read_bytes())
  usages={k:ba['sha256'] for k in ('cleanBuild1','cleanBuild2','manifest','releaseEnvelope','contradictoryQaProposal','governorReviewProposal')};usages['browserTests']=tested
  if len(set(usages.values()))!=1:fail('artifact identity chain differs','build','BUILD_FAILURE')
  report['artifact']={'path':ART.as_posix(),'sha256':ba['sha256'],'bytes':ba['bytes'],'usages':usages}
  py=['apps/learnit-next/build.py','apps/learnit-next/dev/run_checks.py','apps/learnit-next/dev/release.py','authoring/v2/generate_ids.py','authoring/v2/validate_kit.py','apps/learnit-next/tests/contract_v2.py','apps/learnit-next/tests/storage_isolation.py','apps/learnit-next/tests/browser_vertical_slice.py','apps/learnit-next/tests/build_determinism.py']
  comp=run([sys.executable,'-m','py_compile',*py],a,timeout=180);need(comp,'Python compilation','product','PRODUCT_TEST_FAILURE');report['compilation']=comp
  results=[]
  for path in JS:
   r=run(['node','--check',path],a,timeout=120);need(r,f'Node syntax {path}','product','PRODUCT_TEST_FAILURE');results.append(r)
  report['nodeSyntax']={'count':len(results),'paths':JS,'results':results}
  json_paths=[SCHEMA,'docs/architecture/clean-generation/FILE_PLAN_V1.json',SELF,'contracts/fixtures/v2-valid-minimal.json','contracts/fixtures/v2-invalid-legacy.json','contracts/fixtures/v2-invalid-digest-mismatch.json','authoring/v2/golden/nombres_complexes.json','authoring/v2/golden/signaux_electriques.json']
  for path in json_paths:json.loads((a/path).read_text(encoding='utf-8'))
  report['jsonParsing']={'count':len(json_paths),'paths':json_paths}
  golden=run([sys.executable,'authoring/v2/validate_kit.py','--schema',SCHEMA,'--foundation-profile','authoring/v2/golden/nombres_complexes.json','authoring/v2/golden/signaux_electriques.json'],a,timeout=300);need(golden,'golden kits','product','PRODUCT_TEST_FAILURE');report['goldenKits']=golden
  env={'LEARNIT_NEXT_STRICT_INTEGRATION':'1','LEARNIT_NEXT_ARTIFACT':str(a/ART)}
  qa=run([sys.executable,'-m','unittest','discover','-s','apps/learnit-next/tests','-p','*.py','-v'],a,env,1200);need(qa,'strict QA','product','PRODUCT_TEST_FAILURE');total=test_count(qa['output'],'strict QA')
  if total<BASELINE_TESTS or re.search(r'skipped=|FAILED(?:\s|\()|errors?=',qa['output'],re.I):fail('QA did not preserve the baseline 30 tests with zero skip/failure/error:\n'+qa['output'],'product','PRODUCT_TEST_FAILURE')
  added=total-BASELINE_TESTS
  if added<=0:fail('no new topology regression tests were counted','product','PRODUCT_TEST_FAILURE')
  report['qa']={**qa,'executed':total,'passed':total,'baselineProductTests':BASELINE_TESTS,'newTopologyRegressionTests':added,'skipped':0,'failures':0,'errors':0}
  node=run(['node','--version'],timeout=60);need(node,'Node version','product','PRODUCT_TEST_FAILURE')
  chromium=run([sys.executable,'-c','from playwright.sync_api import sync_playwright;p=sync_playwright().start();b=p.chromium.launch(headless=True);print(b.version);b.close();p.stop()'],timeout=180);need(chromium,'Chromium version','product','PRODUCT_TEST_FAILURE')
  report['environment']={'python':platform.python_version(),'jsonschema':importlib.metadata.version('jsonschema'),'playwright':importlib.metadata.version('playwright'),'node':node['output'].strip(),'chromium':chromium['output'].strip()}
  report['stages']['build']={'result':'PASS','classification':'BUILD_PASS'};report['stages']['product']={'result':'PASS','classification':'PRODUCT_TEST_PASS'};report['result']='PASS'

def main():
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,default=REPORT);p.add_argument('--strict',action='store_true');p.add_argument('--mode');p.add_argument('--base-ref',default=os.environ.get('LEARNIT_NEXT_BASE_REF','origin/main'));p.add_argument('--accepted-integration-head',default=os.environ.get('LEARNIT_NEXT_ACCEPTED_INTEGRATION_HEAD',''));a=p.parse_args();target=a.report if a.report.is_absolute() else ROOT/a.report;strict=bool(a.strict or os.environ.get('LEARNIT_NEXT_STRICT_INTEGRATION')=='1')
 report={'schema':'learnit.next.ci.checks.v3','workPackage':'CI-WP-001','mode':a.mode,'strict':strict,'result':'FAIL','stages':{k:{'result':'PENDING'} for k in ('configuration','topology','provenance','build','product')}}
 try:
  if not strict:fail('strict mode is mandatory','configuration','CONFIGURATION_FAILURE')
  if a.mode not in VALID_MODES:fail(f'unknown or missing verification mode: {a.mode!r}','configuration','CONFIGURATION_FAILURE')
  report['stages']['configuration']={'result':'PASS','classification':'CONFIGURATION_PASS'};m=json.loads(MANIFEST.read_text(encoding='utf-8'));report['provenance']=provenance(m,a.mode,a.base_ref,a.accepted_integration_head);report['stages']['topology']={'result':'PASS','classification':'TOPOLOGY_PASS'};report['stages']['provenance']={'result':'PASS','classification':'PROVENANCE_PASS'};checks(report,m)
 except GateError as e:
  report['error']={'message':str(e),'stage':e.stage,'classification':e.classification}
  if e.stage in report['stages']:report['stages'][e.stage]={'result':'FAIL','classification':e.classification}
 except Exception as e:report['error']={'message':str(e),'stage':'internal','classification':'INTERNAL_HARNESS_FAILURE'}
 target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'result':report['result'],'report':target.relative_to(ROOT).as_posix(),'mode':a.mode,'classification':report.get('error',{}).get('classification'),'artifactSha256':report.get('artifact',{}).get('sha256')},sort_keys=True))
 if report['result']!='PASS':print(report.get('error',{}).get('message','unknown failure'),file=sys.stderr);return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
