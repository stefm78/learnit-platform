#!/usr/bin/env python3
"""Fail-closed, revision-safe router for Wave A and Atlas 0.3."""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys
from pathlib import Path
from typing import Any

P=Path(__file__).resolve(); ROOT=Path(os.environ.get('LEARNIT_REPO_ROOT',P.parents[3] if len(P.parents)>3 else Path.cwd())).resolve()
RUNNER='apps/learnit-next/dev/run_checks.py'; WORKFLOW='.github/workflows/learnit-next-ci.yml'
WAVE='8ebafee48cc5277b92776982639a0146ae7e76d0'; CONTRACT_BASE='58e39e8917006058fdf177a5daa37535f5e2c78d'
CORRECTIVE_BASE='6dae2f4f754431ed97c535a3a78fa71067bcd1de'; SUPPORT_BASE='247325c61d990731a24efdcff6e4f0b2e5d4b9c2'
CONTRACT_HEAD='f41de5043a22f8559a3b6a0d71654fbd542b5ec6'; CONTRACT_BRANCH='agent/ATLAS-WP-001-contracts-0-3'
SUPPORT_BRANCH='agent/ATLAS-WP-001-support-governance-ci'; SHA=re.compile(r'^[0-9a-f]{40}$'); SHA_ANY=re.compile(r'\b[0-9a-f]{40}\b')
INT_PROFILE='atlas-int'
INT_BRANCH='agent/ATLAS-WP-001-m1-0-3-int'
PRODUCT_PROFILES=('atlas-learning','atlas-core','atlas-experience','atlas-content')
INT_PATHS={
 'apps/learnit-next/build.py',
 'apps/learnit-next/source_manifest.json',
 'apps/learnit-next/src/main.js',
 'apps/learnit-next/src/integration/atlas/bootstrap.js',
 'apps/learnit-next/src/integration/atlas/import_adapter.js',
 'apps/learnit-next/src/integration/atlas/session.js',
 'apps/learnit-next/src/integration/atlas/surface.js',
 'apps/learnit-next/tests/atlas_m1_int.py',
}
CORRECTIVE={
'atlas-learning':'agent/ATLAS-WP-001-learning-corrective-0-3','atlas-core':'agent/ATLAS-WP-001-core-corrective-0-3',
'atlas-experience':'agent/ATLAS-WP-001-experience-corrective-0-3','atlas-content':'agent/ATLAS-WP-001-content-corrective-0-3',
'atlas-qa':'agent/ATLAS-WP-001-qa-0-3'}
HIST={'agent/ATLAS-WP-001-learning':'atlas-learning','agent/ATLAS-WP-001-core':'atlas-core','agent/ATLAS-WP-001-experience':'atlas-experience','agent/ATLAS-WP-001-content':'atlas-content','agent/ATLAS-WP-001-qa':'atlas-qa'}
WAVE_BRANCHES={'agent/PROG-WP-001-wave-a-learning','agent/PROG-WP-001-wave-a-ux','agent/PROG-WP-001-wave-a-authoring','agent/PROG-WP-001-wave-a-platform','agent/PROG-WP-001-wave-a-qa','agent/PROG-WP-001-wave-a-int'}
BY_BRANCH={v:k for k,v in CORRECTIVE.items()}; ATLAS={CONTRACT_BRANCH:'atlas-contracts',SUPPORT_BRANCH:'atlas-support',INT_BRANCH:INT_PROFILE,**HIST,**BY_BRANCH}
class E(RuntimeError): pass

def git(*a:str)->str:
 r=subprocess.run(['git',*a],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=1800)
 if r.returncode: raise E(f"git {' '.join(a)} failed:\n{r.stdout}")
 return r.stdout.strip()
def sha(v:str,label='target')->str:
 if not SHA.fullmatch(v): raise E(f'{label} must be an exact lowercase SHA40')
 return v
def resolve(b:str)->str:
 if b in ATLAS:return ATLAS[b]
 if b in WAVE_BRANCHES:return 'wave-a'
 raise E(f'unrecognized CI branch: {b}')
def base(b:str)->str:
 if b==CONTRACT_BRANCH or b in HIST:return CONTRACT_BASE
 if b==SUPPORT_BRANCH:return SUPPORT_BASE
 if b in BY_BRANCH or b==INT_BRANCH:return CORRECTIVE_BASE
 if b in WAVE_BRANCHES:return WAVE
 raise E(f'no baseline for CI branch: {b}')
def require_eq(actual:str,expected:str,label:str)->str:
 if actual!=expected:raise E(f'{label} differs: {actual} != {expected}')
 return actual
def remote(b:str)->str:return sha(git('rev-parse','--verify',f'refs/remotes/origin/{b}^{{commit}}'),'branch current head')
def bind(b:str,t:str)->str:return require_eq(remote(b),sha(t,'requested target'),'branch current head from requested target')
def reject(fn:Any,fragment:str)->str:
 try:fn()
 except E as e:
  if fragment in str(e):return 'PASS_REJECTED'
  raise
 raise E(f'expected rejection: {fragment}')
def profile_branch(p:str,b:str)->None:
 if resolve(b)!=p:raise E(f'Atlas branch/profile mismatch: {b} routes to {resolve(b)}, not {p}')
def paths(a:set[str],e:set[str])->None:
 if a!=e:raise E('Atlas path set differs: '+json.dumps({'actual':sorted(a),'expected':sorted(e)},sort_keys=True))
def artifact(p:str,t:str)->str:
 t=sha(t,'artifact target');return f'atlas-contracts-evidence-{t}' if p=='atlas-contracts' else f'learnit-next-{p}-{t}'
def frozen()->dict[str,Any]:
 ns={'__file__':str(ROOT/RUNNER),'__name__':'learnit_frozen_runner'};exec(compile(git('show',f'{CORRECTIVE_BASE}:{RUNNER}'),ns['__file__'],'exec'),ns)
 if ns.get('CONTRACT_HEAD')!=CONTRACT_HEAD:raise E('frozen runner contract head differs')
 return ns

def matrix()->dict[str,Any]:
 old=frozen()['ATLAS']; heads={}; bindings={}
 for p,b in sorted(CORRECTIVE.items()):
  require_eq(resolve(b),p,'route');require_eq(base(b),CORRECTIVE_BASE,'baseline');h=remote(b);bind(b,h);heads[p]=h
  bindings[p]={'branch':b,'requestedTarget':h,'branchCurrentHead':h,'result':'PASS_DYNAMIC_BINDING'}
 p='atlas-learning';b=CORRECTIVE[p];h=heads[p];other='0'*40 if h!='0'*40 else '1'*40; allowed=set(old[p][1])
 if SHA_ANY.findall(json.dumps(CORRECTIVE,sort_keys=True)):raise E('corrective route table contains a permanent lane head')
 neg={
 'otherSha40Rejected':reject(lambda:bind(b,other),'branch current head from requested target'),
 'profileBranchMismatchRejected':reject(lambda:profile_branch('atlas-core',b),'branch/profile mismatch'),
 'unknownBranchRejected':reject(lambda:resolve('agent/UNKNOWN-WP-999-example'),'unrecognized CI branch'),
 'badBaselineRejected':reject(lambda:require_eq(other,base(b),'baseline'),'baseline differs'),
 'badMergeBaseRejected':reject(lambda:require_eq(other,CORRECTIVE_BASE,'merge-base'),'merge-base differs'),
 'allowlistExcessRejected':reject(lambda:paths(allowed|{'unexpected/path'},allowed),'path set differs'),
 'allowlistDeficitRejected':reject(lambda:paths(set(sorted(allowed)[1:]),allowed),'path set differs')}
 c={'profile':resolve(CONTRACT_BRANCH),'branch':CONTRACT_BRANCH,'base':base(CONTRACT_BRANCH),'head':CONTRACT_HEAD,'artifact':artifact('atlas-contracts',CONTRACT_HEAD)}
 expected={'profile':'atlas-contracts','branch':CONTRACT_BRANCH,'base':CONTRACT_BASE,'head':CONTRACT_HEAD,'artifact':f'atlas-contracts-evidence-{CONTRACT_HEAD}'}
 require_eq(c,expected,'atlas-contracts identity')
 names={p:artifact(p,h) for p,h in heads.items()}
 if any(not names[p].endswith(h) for p,h in heads.items()):raise E('artifact does not contain verified target')
 int_head=remote(INT_BRANCH)
 bind(INT_BRANCH,int_head)

 for p in PRODUCT_PROFILES:
  git('merge-base','--is-ancestor',heads[p],int_head)

 expected_int=set(INT_PATHS)
 for p in PRODUCT_PROFILES:
  expected_int.update(old[p][1])

 actual_int={
  x for x in git('diff','--name-only',CORRECTIVE_BASE,int_head).splitlines()
  if x
 }
 paths(actual_int,expected_int)

 int_binding={
  'profile':INT_PROFILE,
  'branch':INT_BRANCH,
  'base':CORRECTIVE_BASE,
  'requestedTarget':int_head,
  'branchCurrentHead':int_head,
  'productHeads':{p:heads[p] for p in PRODUCT_PROFILES},
  'qaPreCandidateHead':heads['atlas-qa'],
  'pathCount':len(actual_int),
  'pathSetResult':'PASS_EXACT_COMPOSITION',
 }

 return {'integrationCandidate':int_binding,'dynamicBinding':'branch_current_head_equals_requested_target','correctiveRoutes':{p:{'branch':b,'base':CORRECTIVE_BASE} for p,b in sorted(CORRECTIVE.items())},'currentLaneBindings':bindings,'preservedLaneHeads':heads,'historicalAtlas':{b:{'profile':p,'base':base(b)} for b,p in sorted(HIST.items())},'waveA':{b:'wave-a' for b in sorted(WAVE_BRANCHES)},'atlasContracts':c,'artifactNames':names,'staticRejectedHeadPinningRemoved':True,'negativeTests':neg}

def capability()->dict[str,Any]:
 w=(ROOT/WORKFLOW).read_text();r=(ROOT/RUNNER).read_text()
 wt={'atlas-contracts','atlas-learning','atlas-core','atlas-experience','atlas-content','atlas-int','atlas-qa',INT_BRANCH,CONTRACT_BASE,CORRECTIVE_BASE,SUPPORT_BASE,'name: ${{ steps.profile.outputs.artifact }}',*BY_BRANCH,*HIST}
 rt={CONTRACT_BASE,CORRECTIVE_BASE,SUPPORT_BASE,'atlas-int',INT_BRANCH,'branch_current_head_equals_requested_target',*BY_BRANCH,*HIST}
 missing=[f'workflow:{x}' for x in wt if x not in w]+[f'runner:{x}' for x in rt if x not in r]
 if missing:raise E('revision-safe CI capability incomplete: '+json.dumps(sorted(missing)))
 allowed={WAVE,CONTRACT_BASE,CORRECTIVE_BASE,SUPPORT_BASE,CONTRACT_HEAD,'ae999472418a18a1181b43a07259a4395afbcf7f','48df0517d74e8c343223f14361607c4a93e7f55b','6c4111715a55fdff07a3e466d013dcdcc7aa5c78','f260093914542f93ff9145cbac8e98aae415fe01','f25da6356528824e84224718013a3bccb2707c49'}
 unexpected={p:sorted(set(SHA_ANY.findall(t))-allowed) for p,t in ((WORKFLOW,w),(RUNNER,r))};unexpected={p:v for p,v in unexpected.items() if v}
 if unexpected:raise E('unexpected permanent SHA40 in revision-safe CI: '+json.dumps(unexpected,sort_keys=True))
 return {'contractEvidenceBase':CONTRACT_BASE,'correctiveCommonBaseline':CORRECTIVE_BASE,'revisionSafeSupportBase':SUPPORT_BASE,'contractHead':CONTRACT_HEAD,'dispatchProfiles':sorted([*CORRECTIVE,INT_PROFILE]),'dynamicBinding':'branch_current_head_equals_requested_target','staticRejectedHeadPinningRemoved':True,'staticShaAllowlistCheck':'PASS','routingSelfTest':matrix(),'failClosed':True}

def run_int_candidate(a:argparse.Namespace)->int:
 import hashlib
 import tempfile

 try:
  require_eq(a.branch_ref,INT_BRANCH,'INT branch')

  target=sha(a.target_ref,'INT requested target')
  checked=sha(git('rev-parse','HEAD'),'INT checked-out head')

  require_eq(checked,target,'INT checked-out head')
  require_eq(a.base_ref,CORRECTIVE_BASE,'INT corrective baseline')

  require_eq(
   sha(git('merge-base',CORRECTIVE_BASE,'HEAD'),'INT merge-base'),
   CORRECTIVE_BASE,
   'INT merge-base',
  )

  bind(INT_BRANCH,target)

  old=frozen()['ATLAS']

  accepted={}
  expected_paths=set(INT_PATHS)

  for profile in PRODUCT_PROFILES:
   branch=CORRECTIVE[profile]
   head=remote(branch)
   accepted[profile]=head

   git('merge-base','--is-ancestor',head,target)

   lane_paths=set(old[profile][1])
   expected_paths.update(lane_paths)

   for rel in sorted(lane_paths):
    require_eq(
     git('rev-parse',f'{target}:{rel}'),
     git('rev-parse',f'{head}:{rel}'),
     f'INT frozen blob {profile}:{rel}',
    )

  qa_head=remote(CORRECTIVE['atlas-qa'])

  actual_paths={
   x
   for x in git(
    'diff',
    '--name-only',
    CORRECTIVE_BASE,
    target,
   ).splitlines()
   if x
  }

  paths(actual_paths,expected_paths)

  commands=(
   ('apps/learnit-next/tests/atlas_m1_learning.py',),
   ('apps/learnit-next/tests/atlas_m1_core.py',),
   ('apps/learnit-next/tests/atlas_m1_experience.py',),
   ('apps/learnit-next/tests/atlas_m1_content.py',),
   ('authoring/v2/atlas/validate_atlas_content.py',),
   ('apps/learnit-next/tests/atlas_m1_int.py',),
  )

  outputs=[]

  for args in commands:
   command=[sys.executable,*args]

   done=subprocess.run(
    command,
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    env={
     **os.environ,
     'PYTHONDONTWRITEBYTECODE':'1',
    },
    timeout=1800,
   )

   outputs.append({
    'command':command,
    'exitCode':done.returncode,
    'output':done.stdout,
   })

   if done.returncode:
    raise E(
     'INT command failed: '
     +' '.join(command)
     +'\\n'
     +done.stdout
    )

  build=ROOT/'apps/learnit-next/build.py'

  def build_to(output:Path)->bytes:
   command=[
    sys.executable,
    '-B',
    str(build),
    '--output',
    str(output),
   ]

   done=subprocess.run(
    command,
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    env={
     **os.environ,
     'PYTHONDONTWRITEBYTECODE':'1',
    },
    timeout=1800,
   )

   if done.returncode:
    raise E('INT build failed:\\n'+done.stdout)

   return output.read_bytes()

  with tempfile.TemporaryDirectory(prefix='atlas-int-ci-') as raw:
   temp=Path(raw)
   first=build_to(temp/'first.html')
   second=build_to(temp/'second.html')

  if first!=second:
   raise E('INT deterministic artifact mismatch')

  artifact_sha=hashlib.sha256(first).hexdigest()

  canonical=ROOT/'apps/learnit-next/dist/learnit-next.html'

  done=subprocess.run(
   [sys.executable,'-B',str(build)],
   cwd=ROOT,
   text=True,
   stdout=subprocess.PIPE,
   stderr=subprocess.STDOUT,
   env={
    **os.environ,
    'PYTHONDONTWRITEBYTECODE':'1',
   },
   timeout=1800,
  )

  if done.returncode:
   raise E(
    'INT canonical build failed:\\n'
    +done.stdout
   )

  canonical_bytes=canonical.read_bytes()

  if canonical_bytes!=first:
   raise E(
    'INT canonical artifact differs from deterministic build'
   )

  html=canonical_bytes.decode('utf-8')

  markers=(
   '.atlas-m1',
   '__LEARNIT_ATLAS_CJS__',
   'data-atlas-planner-actions',
   'data-atlas-session-actions',
   'data-atlas-pause-session',
   'data-atlas-help',
   'data-atlas-submit',
   'Indice',
   'Valider la réponse',
   'Quitter et reprendre plus tard',
  )

  missing=[token for token in markers if token not in html]

  if missing:
   raise E(
    'INT artifact markers missing: '
    +json.dumps(missing)
   )

  proof={
   'schema':'learnit.next.ci.atlas-int.v1',
   'workPackage':'ATLAS-WP-001',
   'candidateHead':target,
   'candidateBranch':INT_BRANCH,
   'correctiveBaseline':CORRECTIVE_BASE,
   'acceptedProductHeads':accepted,
   'qaPreCandidateHead':qa_head,
   'pathCount':len(actual_paths),
   'pathSet':'PASS_EXACT_COMPOSITION',
   'tests':'PASS',
   'deterministicBuild':True,
   'artifactBytes':len(canonical_bytes),
   'artifactSha256':artifact_sha,
   'artifactMarkers':'PASS',
   'verdict':'PASS_TO_QA_CANDIDATE_REVIEW',
  }

  result_dir=ROOT/'apps/learnit-next/.agent-result'
  result_dir.mkdir(parents=True,exist_ok=True)

  (result_dir/'run_checks.json').write_text(
   json.dumps(
    {
     'result':'PASS',
     'verdict':'PASS_TO_QA_CANDIDATE_REVIEW',
     'atlasIntCandidate':proof,
     'tests':outputs,
    },
    indent=2,
    sort_keys=True,
    ensure_ascii=False,
   )+'\\n',
   encoding='utf-8',
  )

  print(json.dumps(proof,indent=2,sort_keys=True))
  return 0

 except Exception as e:
  print(str(e),file=sys.stderr)
  return 2

def patch(ns:dict[str,Any],p:str,bref:str)->None:
 ns['ATLAS_BASE']=bref;a=ns['ATLAS'];cur=a[p];b=SUPPORT_BRANCH if p=='atlas-support' else CORRECTIVE[p]
 pp={WORKFLOW,RUNNER} if p=='atlas-support' else ({'apps/learnit-next/tests/qa_atlas_m1.py'} if p=='atlas-qa' else set(cur[1]))
 a[p]=(b,pp,cur[2],cur[3],cur[4]);ns['ATLAS_BRANCHES']={v[0]:k for k,v in a.items()}
 if p=='atlas-support':ns['routing_matrix']=matrix;ns['support_contract_capability']=capability

def run_atlas(a:argparse.Namespace)->int:
 try:
  if not a.branch_ref:raise E('Atlas profile requires --branch-ref')
  profile_branch(a.profile,a.branch_ref);expected=base(a.branch_ref);require_eq(a.base_ref,expected,'baseline')
  require_eq(sha(git('rev-parse','HEAD'),'checked-out head'),sha(a.target_ref,'requested target'),'checked-out head from requested target')
  require_eq(sha(git('merge-base',expected,'HEAD'),'merge-base'),expected,'merge-base')
  if a.post_merge:
   if a.profile!='atlas-support':raise E('post-merge branch-binding exemption is support-only')
  else:bind(a.branch_ref,a.target_ref)
  if a.profile=='atlas-contracts':require_eq(a.target_ref,CONTRACT_HEAD,'contract head')
  ns=frozen()
  if a.branch_ref==SUPPORT_BRANCH or a.branch_ref in BY_BRANCH:patch(ns,a.profile,expected)
  return int(ns['run_atlas'](a.profile,a.branch_ref,a.base_ref))
 except Exception as e:print(str(e),file=sys.stderr);return 2

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--strict',action='store_true');p.add_argument('--mode',default='integration-head');p.add_argument('--base-ref',default=WAVE);p.add_argument('--accepted-integration-head',default='');p.add_argument('--profile',default='wave-a');p.add_argument('--branch-ref',default='');p.add_argument('--target-ref',default='');p.add_argument('--post-merge',action='store_true');p.add_argument('--resolve-branch',default='');p.add_argument('--routing-self-test',action='store_true');a=p.parse_args()
 if a.resolve_branch:
  try:print(resolve(a.resolve_branch));return 0
  except E as e:print(e,file=sys.stderr);return 2
 if a.routing_self_test:
  try:print(json.dumps(matrix(),indent=2,sort_keys=True));return 0
  except E as e:print(e,file=sys.stderr);return 2
 if a.profile==INT_PROFILE:return run_int_candidate(a)
 if a.profile in {'wave-a','wave-a-ci'}:return int(frozen()['main']())
 if a.profile not in {'atlas-support','atlas-contracts',*CORRECTIVE}:print(f'unsupported Atlas profile: {a.profile}',file=sys.stderr);return 2
 return run_atlas(a)
if __name__=='__main__':raise SystemExit(main())
