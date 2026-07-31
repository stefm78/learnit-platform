#!/usr/bin/env python3
"""Independent, fail-closed Atlas M1 0.3 QA oracle.

Preflight tests the oracle and immutable fixtures. Strict mode binds an exact
candidate checkout, exact accepted heads/artifact/content claims, and drives the
real browser/IndexedDB flow without trusting any candidate self-attestation.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, pathlib, re, subprocess, sys, tempfile, textwrap, unittest, unicodedata

ROOT=pathlib.Path(__file__).resolve().parents[3]
FIXTURES={
 'contracts/fixtures/atlas-m1-valid-loop.json':'2abc0ecf8eb1f4b7afcb1e7a010015e9549bfbf0a4a6dcc4379a65c2c5fda46a',
 'contracts/fixtures/atlas-m1-invalid-loop.json':'dca06d3df5cdb0c0492f38e787996ca95f760f6cbdd0c72f8bed5e1a498cca0d'}
LANES={
 'learning':('apps/learnit-next/src/core/atlas_evidence.js','apps/learnit-next/src/core/atlas_recommendation.js','apps/learnit-next/src/core/atlas_planner.js','apps/learnit-next/tests/atlas_m1_learning.py'),
 'core':('apps/learnit-next/src/core/atlas_events.js','apps/learnit-next/src/core/atlas_projection.js','apps/learnit-next/src/core/atlas_clock.js','apps/learnit-next/src/ports/atlas_storage.js','apps/learnit-next/src/adapters/atlas_indexeddb.js','apps/learnit-next/tests/atlas_m1_core.py'),
 'experience':('apps/learnit-next/src/ui/atlas_today.js','apps/learnit-next/src/ui/atlas_session.js','apps/learnit-next/src/ui/atlas_summary.js','apps/learnit-next/src/ui/atlas_rewards.js','apps/learnit-next/src/atlas.css','apps/learnit-next/tests/atlas_m1_experience.py'),
 'content':('authoring/v2/atlas/README.md','authoring/v2/atlas/nombres_complexes_atlas.json','authoring/v2/atlas/signaux_electriques_atlas.json','authoring/v2/atlas/validate_atlas_content.py','apps/learnit-next/tests/atlas_m1_content.py')}
PACKAGES=tuple(p for p in LANES['content'] if p.endswith('_atlas.json'))
SHA40=re.compile(r'^[0-9a-f]{40}$'); DIGEST=re.compile(r'^sha256:[0-9a-f]{64}$'); CLAIM=re.compile(r'^atlas-claim-sha256:[0-9a-f]{64}$')
UTC_TIMESTAMP=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
DAY_MS=24*60*60*1000
CLAIM_DOMAIN='learnit.atlas.m1.v0.3/validation-claim-id'; STIMULUS_DOMAIN='learnit.atlas.m1.v0.3/stimulus-digest/atlas.stimulus.v1'
REWARDS=('validation-reconfirmed','validation-completed','correction-completed','independent-success','resumed-after-interruption')
REASONS={'NEW_OBJECTIVE','PRACTICE_IN_PROGRESS','RECENT_ERROR','REVIEW_REQUIRED','CORRECTION_COMPLETED','NO_INDEPENDENT_VALIDATION','VALIDATION_AVAILABLE','RECENTLY_VALIDATED','SESSION_TIME_LIMIT'}

def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def canonical(v):
 if v is None or isinstance(v,(bool,int,str)):
  return unicodedata.normalize('NFC',v) if isinstance(v,str) else v
 if isinstance(v,float): raise AssertionError('NON_CANONICAL_NUMBER')
 if isinstance(v,list): return [canonical(x) for x in v]
 if isinstance(v,dict):
  rows=[]; seen=set()
  for k,x in v.items():
   if not isinstance(k,str): raise AssertionError('NON_CANONICAL_KEY')
   k=unicodedata.normalize('NFC',k)
   if k in seen: raise AssertionError('CANONICAL_KEY_COLLISION')
   seen.add(k); rows.append((k,x))
  rows.sort(key=lambda r:[ord(c) for c in r[0]])
  return {k:canonical(x) for k,x in rows}
 raise AssertionError('NON_CANONICAL_VALUE')

def cjson(v): return json.dumps(canonical(v),ensure_ascii=False,separators=(',',':'))
def ahash(domain,v): return hashlib.sha256(domain.encode()+b'\0'+cjson(v).encode()).hexdigest()
def norm(v):
 if not isinstance(v,str): raise AssertionError('INVALID_VISIBLE_STRING')
 return re.sub(r'\s+',' ',unicodedata.normalize('NFC',v).strip())
def closed(obj,required,optional=()):
 req=set(required); allowed=req|set(optional)
 if not isinstance(obj,dict) or not req<=set(obj) or set(obj)-allowed: raise AssertionError('OBJECT_NOT_CLOSED')
def same(a,b): return cjson(a)==cjson(b)

def utc_millis(value):
 if not isinstance(value,str) or not UTC_TIMESTAMP.fullmatch(value): raise AssertionError('NONCANONICAL_UTC_TIMESTAMP')
 try: parsed=datetime.datetime.strptime(value,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=datetime.timezone.utc)
 except ValueError as e: raise AssertionError('INVALID_UTC_TIMESTAMP') from e
 roundtrip=parsed.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]+'Z'
 if roundtrip!=value: raise AssertionError('NONCANONICAL_UTC_TIMESTAMP')
 delta=parsed-datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)
 return delta.days*DAY_MS+delta.seconds*1000+delta.microseconds//1000

def maintenance_due(basis_event,event):
 try: return utc_millis(event.get('occurredAt'))-utc_millis(basis_event.get('occurredAt'))>=DAY_MS
 except AssertionError: return False

def verify_focus_trace(expected,forward,reverse,forward_boundary,reverse_boundary):
 if not isinstance(expected,list) or not expected or any(not isinstance(x,str) or not x for x in expected) or len(expected)!=len(set(expected)): raise AssertionError('FOCUS_EXPECTED_INVALID')
 if forward!=expected: raise AssertionError('FOCUS_FORWARD_ORDER_INVALID')
 if reverse!=list(reversed(expected)): raise AssertionError('FOCUS_REVERSE_ORDER_INVALID')
 if forward_boundary!=expected[0]: raise AssertionError('FOCUS_FORWARD_BOUNDARY_INVALID')
 if reverse_boundary!=expected[-1]: raise AssertionError('FOCUS_REVERSE_BOUNDARY_INVALID')
 return True

def require_network_clean(blocked,phase):
 if blocked: raise AssertionError('NETWORK_EGRESS_BLOCKED_'+phase+':'+json.dumps(blocked,sort_keys=True))
 return True

def stimulus(activity):
 base={'type':activity.get('type'),'prompt':norm(activity.get('prompt'))}
 if activity.get('type')=='qcm':
  choices=activity.get('choices'); byid={}
  if not isinstance(choices,list) or not choices: raise AssertionError('QCM_CHOICES_REQUIRED')
  for x in choices:
   closed(x,('choiceId','label')); cid=x['choiceId']
   if not isinstance(cid,str) or not cid or cid in byid: raise AssertionError('QCM_CHOICE_COLLISION')
   byid[cid]=norm(x['label'])
  if activity.get('correctChoiceId') not in byid: raise AssertionError('QCM_OPERATION_INVALID')
  labels=sorted(byid.values())
  if len(labels)!=len(set(labels)): raise AssertionError('QCM_VISIBLE_CHOICE_COLLISION')
  base.update(choices=labels,answerOperation={'kind':'select-one','correctValue':byid[activity['correctChoiceId']]})
 elif activity.get('type')=='fill':
  tokens=activity.get('tokens'); token={}
  if not isinstance(tokens,list) or not tokens: raise AssertionError('FILL_TOKENS_REQUIRED')
  for x in tokens:
   closed(x,('tokenId','label','maxUses')); tid=x['tokenId']; mx=x['maxUses']
   if not isinstance(tid,str) or not tid or tid in token or not isinstance(mx,int) or isinstance(mx,bool) or mx<1: raise AssertionError('FILL_TOKEN_INVALID')
   token[tid]={'label':norm(x['label']),'maxUses':mx}
  slots=[]; segments=[]
  for x in activity.get('segments',[]):
   if set(x)=={'text'}: segments.append({'text':norm(x['text'])})
   elif set(x)=={'slotId'} and isinstance(x['slotId'],str) and x['slotId'] and x['slotId'] not in slots: slots.append(x['slotId']); segments.append({'blank':len(slots)-1})
   else: raise AssertionError('FILL_SEGMENT_INVALID')
  answers={}
  for x in activity.get('answers',[]):
   closed(x,('slotId','tokenId'))
   if x['slotId'] in answers: raise AssertionError('FILL_ANSWER_MAPPING_INVALID')
   answers[x['slotId']]=x['tokenId']
  if set(answers)!=set(slots): raise AssertionError('FILL_ANSWER_MAPPING_INVALID')
  used={k:0 for k in token}; correct=[]
  for slot in slots:
   tid=answers[slot]
   if tid not in token: raise AssertionError('FILL_ANSWER_TOKEN_UNKNOWN')
   used[tid]+=1
   if used[tid]>token[tid]['maxUses']: raise AssertionError('FILL_MAX_USES_EXCEEDED')
   correct.append(token[tid]['label'])
  visible=sorted(({'label':v['label'],'maxUses':v['maxUses']} for v in token.values()),key=cjson)
  base.update(segments=segments,tokens=visible,answerOperation={'kind':'fill-blanks','correctValues':correct})
 else: raise AssertionError('ATLAS_ACTIVITY_TYPE_UNSUPPORTED')
 return 'sha256:'+ahash(STIMULUS_DOMAIN,base)

def qref(pkg,course,*,objective=None,activity=None):
 if (objective is None)==(activity is None): raise AssertionError('UNQUALIFIED_REFERENCE')
 out={'courseRef':{'packageLineageId':pkg,'courseLineageId':course}}
 out['objectiveId' if objective is not None else 'activityLineageId']=objective if objective is not None else activity
 return out

def refkey(ref):
 closed(ref,('courseRef',),('objectiveId','activityLineageId')); closed(ref['courseRef'],('packageLineageId','courseLineageId'))
 haso='objectiveId' in ref; hasa='activityLineageId' in ref
 if haso==hasa: raise AssertionError('UNQUALIFIED_REFERENCE')
 suffix=('objective:'+ref['objectiveId']) if haso else ('activity:'+ref['activityLineageId'])
 if not all(isinstance(x,str) and x for x in (*ref['courseRef'].values(),suffix)): raise AssertionError('UNQUALIFIED_REFERENCE')
 return '\0'.join((*ref['courseRef'].values(),suffix))

def revision(package): return {'packageLineageId':package.get('packageLineageId'),'packageRevisionId':package.get('packageRevisionId'),'packageDigest':package.get('packageRevisionDigest')}
def check_revision(r):
 closed(r,('packageLineageId','packageRevisionId','packageDigest'))
 if not all(isinstance(r[k],str) and r[k] for k in ('packageLineageId','packageRevisionId')) or not isinstance(r['packageDigest'],str) or not DIGEST.fullmatch(r['packageDigest']): raise AssertionError('INVALID_CONTENT_REVISION')
 return r

def qualify_claim(package,course,raw):
 closed(raw,('claimVersion','claimId','objectiveId','sourceActivityLineageId','targetActivityLineageId','basisCode','sourceStimulusDigest','targetStimulusDigest'))
 if raw['claimVersion']!='atlas.independence.v1' or raw['basisCode'] not in {'new-instance','new-context','alternate-representation'}: raise AssertionError('CLAIM_SHAPE_INVALID')
 byid={a['activityLineageId']:a for a in course.get('activities',[])}
 if len(byid)!=len(course.get('activities',[])): raise AssertionError('DUPLICATE_ACTIVITY_REF')
 try: source,target=byid[raw['sourceActivityLineageId']],byid[raw['targetActivityLineageId']]
 except KeyError as e: raise AssertionError('CLAIM_ACTIVITY_UNKNOWN') from e
 oid=raw['objectiveId']
 if source.get('objectiveIds')!=[oid] or target.get('objectiveIds')!=[oid] or source is target: raise AssertionError('CLAIM_RELATION_INVALID')
 sd,td=stimulus(source),stimulus(target)
 if sd==td or raw['sourceStimulusDigest']!=sd or raw['targetStimulusDigest']!=td: raise AssertionError('CLAIM_STIMULUS_INVALID')
 pkg=package['packageLineageId']; cid=course['courseLineageId']
 payload={'claimVersion':'atlas.independence.v1','objectiveRef':qref(pkg,cid,objective=oid),'sourceActivityRef':qref(pkg,cid,activity=raw['sourceActivityLineageId']),'targetActivityRef':qref(pkg,cid,activity=raw['targetActivityLineageId']),'basisCode':raw['basisCode'],'sourceStimulusDigest':sd,'targetStimulusDigest':td}
 expected='atlas-claim-sha256:'+ahash(CLAIM_DOMAIN,payload)
 if raw['claimId']!=expected: raise AssertionError('CLAIM_ID_INVALID')
 return {'claimId':expected,**payload}

def load_claims(root,content_revision):
 check_revision(content_revision); matches=[]
 for rel in PACKAGES:
  path=root/rel
  if not path.is_file() or path.is_symlink(): raise AssertionError('EXPECTED_SOURCE_FILE_MISSING:'+rel)
  p=json.loads(path.read_text(encoding='utf-8'))
  if same(revision(p),content_revision): matches.append(p)
 if len(matches)!=1: raise AssertionError('CONTENT_REVISION_PACKAGE_MATCH_COUNT')
 claims={}; package=matches[0]
 for course in package.get('courses',[]):
  for raw in course.get('atlasValidationIndependenceClaims',[]):
   item=qualify_claim(package,course,raw)
   if item['claimId'] in claims: raise AssertionError('DUPLICATE_CLAIM_ID')
   claims[item['claimId']]=item
 if not claims: raise AssertionError('CANDIDATE_CLAIMS_REQUIRED')
 return claims

def check_claim_set(obj,artifact_sha,content_revision,oracle,candidate_claims):
 closed(obj,('schemaVersion','contentRevisionRef','oracleVersion','artifactDigest','acceptedClaimIds'))
 if obj['schemaVersion']!='atlas.accepted-validation-claims.v1' or obj['oracleVersion']!=oracle or not oracle: raise AssertionError('CLAIM_SET_BINDING')
 if obj['artifactDigest']!='sha256:'+artifact_sha or not same(obj['contentRevisionRef'],content_revision): raise AssertionError('CLAIM_SET_BINDING')
 ids=obj['acceptedClaimIds']
 if not isinstance(ids,list) or not ids or ids!=sorted(set(ids)) or any(not isinstance(x,str) or not CLAIM.fullmatch(x) for x in ids): raise AssertionError('CLAIM_SET_NOT_SORTED_UNIQUE')
 unknown=[x for x in ids if x not in candidate_claims]
 if unknown: raise AssertionError('CLAIM_SET_UNKNOWN_CANDIDATE_CLAIM')
 return frozenset(ids)

def index(rows,key,code):
 out={}
 for row in rows:
  value=row.get(key)
  if not isinstance(value,str) or not value or value in out: raise AssertionError(code)
  out[value]=row
 return out

def started(events):
 out={}
 for e in events:
  if e.get('kind')!='session-started': continue
  sid=e.get('sessionRef',{}).get('sessionId'); items=e.get('selectedItems')
  if not isinstance(sid,str) or not isinstance(items,list): raise AssertionError('INVALID_SESSION_STARTED')
  for i,item in enumerate(items):
   if item.get('position')!=i or (sid,i) in out: raise AssertionError('INVALID_SESSION_STARTED')
   out[sid,i]={'item':item,'event':e}
 return out

def admissible(execution,event,plan,events,executions,claims,accepted,content_revision):
 item=plan['item']; start=plan['event']; sid=execution.get('sessionRef',{}).get('sessionId')
 if event.get('kind')!='activity-attempt' or event.get('executionId')!=execution.get('executionId') or event.get('objectiveRef')!=execution.get('objectiveRef'): return False
 exact=(execution.get('sessionRef')==start.get('sessionRef') and execution.get('planDigest')==start.get('planDigest') and execution.get('courseRef')==start.get('courseRef') and execution.get('contentRevisionRef')==start.get('contentRevisionRef')==content_revision and execution.get('itemPosition')==item.get('position') and execution.get('objectiveRef')==item.get('objectiveRef') and execution.get('activityRef')==item.get('activityRef') and execution.get('action')==item.get('action') and execution.get('executionClass')==item.get('executionClass')=='validation')
 if not exact or execution.get('outcome')!='correct' or execution.get('assistance')!='none': return False
 claim_id=item.get('independenceClaimId'); basis_id=item.get('validationBasisEventId'); claim=claims.get(claim_id)
 if claim_id not in accepted or not claim or not isinstance(basis_id,str): return False
 basis_event=events.get(basis_id); basis_exec=executions.get((basis_event or {}).get('executionId'))
 if not basis_event or not basis_exec or basis_exec.get('outcome')!='correct' or basis_exec.get('assistance')!='none': return False
 if item.get('action')=='maintain-recent-validation':
  if basis_exec.get('executionClass')!='validation' or not maintenance_due(basis_event,event): return False
 return (claim['objectiveRef']==item.get('objectiveRef') and claim['sourceActivityRef']==basis_exec.get('activityRef') and claim['targetActivityRef']==item.get('activityRef') and basis_exec.get('objectiveRef')==item.get('objectiveRef') and basis_exec.get('courseRef')==execution.get('courseRef') and basis_exec.get('contentRevisionRef')==content_revision)

def project(events,executions,claims,accepted,content_revision):
 ex=index(executions,'executionId','DUPLICATE_OR_INVALID_EXECUTION'); ev=index(events,'eventId','DUPLICATE_OR_INVALID_EVENT'); plans=started(events); rows={}; latest_error={}; corrected=set()
 for e in sorted((x for x in events if x.get('kind') in ('activity-attempt','activity-corrected')),key=lambda x:(x.get('occurredAt',''),x['eventId'])):
  x=ex.get(e.get('executionId'))
  if not x: raise AssertionError('MISSING_EXECUTION')
  key=cjson(e.get('objectiveRef')); row=rows.setdefault(key,{'practiceAttempts':0,'correctionsCompleted':0,'validationAttempts':0,'latestPracticeCorrect':None,'latestValidationCorrect':None,'lastValidationAt':None,'lastEvidenceAt':None,'state':'not-started'})
  row['lastEvidenceAt']=max(filter(None,(row['lastEvidenceAt'],e.get('occurredAt'))))
  if e['kind']=='activity-corrected': row['correctionsCompleted']+=1; corrected.add(e.get('correctsEventId')); continue
  if x.get('executionClass')=='practice': row['practiceAttempts']+=1; row['latestPracticeCorrect']=x.get('outcome')=='correct'; latest_error[key]=e['eventId'] if x.get('outcome')=='incorrect' else latest_error.get(key)
  elif x.get('executionClass')=='validation':
   row['validationAttempts']+=1; row['latestValidationCorrect']=x.get('outcome')=='correct'
   plan=plans.get((x.get('sessionRef',{}).get('sessionId'),x.get('itemPosition')))
   if plan and admissible(x,e,plan,ev,ex,claims,accepted,content_revision): row['state']='validated-recently'; row['lastValidationAt']=x.get('scoredAt')
   elif x.get('outcome')=='incorrect': row['state']='review-needed'
  if latest_error.get(key) and latest_error[key] not in corrected: row['state']='review-needed'
 for key,row in rows.items():
  if row['state']=='not-started': row['state']='ready-for-validation' if row['latestPracticeCorrect'] else 'training'
 return rows

def exclusive_rewards(facts):
 used=set(); out=[]
 for f in sorted(facts,key=lambda x:(REWARDS.index(x['rewardKind']),x['occurredAt'],x['eventId'])):
  if f['eventId'] not in used: used.add(f['eventId']); out.append(f['rewardKind'])
 return out

def git(root,*args,check=True):
 cp=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
 if check and cp.returncode: raise AssertionError('GIT_FAILURE:'+' '.join(args)+':'+cp.stderr.strip())
 return cp.stdout.strip()

def parse_heads(values):
 out={}
 for value in values:
  if '=' not in value: raise SystemExit('--accepted-head requires lane=sha')
  lane,head=value.split('=',1)
  if lane not in LANES or lane in out or not SHA40.fullmatch(head): raise SystemExit('invalid accepted head')
  out[lane]=head
 if set(out)!=set(LANES): raise SystemExit('exact learning/core/experience/content heads required')
 return out

def bind_heads(repo,candidate,heads):
 if git(repo,'cat-file','-t',candidate)!='commit': raise AssertionError('CANDIDATE_COMMIT_MISSING')
 for lane,head in heads.items():
  if git(repo,'cat-file','-t',head)!='commit': raise AssertionError('ACCEPTED_HEAD_MISSING:'+lane)
  for path in LANES[lane]:
   if git(repo,'rev-parse',f'{head}:{path}')!=git(repo,'rev-parse',f'{candidate}:{path}'): raise AssertionError('ACCEPTED_HEAD_BLOB_MISMATCH:'+path)

def bind_source(root,candidate):
 if git(root,'rev-parse','HEAD')!=candidate: raise AssertionError('SOURCE_HEAD_MISMATCH')
 if git(root,'status','--porcelain=v1','--untracked-files=all'): raise AssertionError('SOURCE_WORKTREE_NOT_CLEAN')
 paths=[]
 for rel in (p for rows in LANES.values() for p in rows):
  path=root/rel
  if not path.is_file() or path.is_symlink(): raise AssertionError('EXPECTED_SOURCE_FILE_MISSING:'+rel)
  git(root,'ls-files','--error-unmatch','--',rel)
  if git(root,'rev-parse',f'{candidate}:{rel}')!=git(root,'hash-object','--',rel): raise AssertionError('SOURCE_BLOB_MISMATCH:'+rel)
  paths.append(path)
 return paths

def provenance(path,candidate,heads,artifact_sha):
 obj=json.loads(path.read_text(encoding='utf-8')); closed(obj,('schemaVersion','candidateHead','artifactSha256','acceptedHeads','buildCommands','cleanCheckout','networkBlocked'))
 if obj['schemaVersion']!='atlas.artifact-provenance.v1' or obj['candidateHead']!=candidate or obj['artifactSha256']!=artifact_sha or obj['acceptedHeads']!=heads or obj['cleanCheckout'] is not True or obj['networkBlocked'] is not True or not isinstance(obj['buildCommands'],list) or not obj['buildCommands']: raise AssertionError('ARTIFACT_PROVENANCE_MISMATCH')

def network(paths):
 forbidden=('fetch(','XMLHttpRequest','WebSocket','openai','anthropic','http://','https://'); return [(str(p),t) for p in paths for t in forbidden if t in p.read_text(encoding='utf-8')]

def browser_script(artifact):
 return textwrap.dedent(f'''\
 from playwright.sync_api import sync_playwright
 from pathlib import Path
 import json
 uri=Path({str(artifact)!r}).resolve().as_uri()
 def snap(page):
  return page.evaluate("""async()=>{{const out={{}};for(const d of await indexedDB.databases()){{if(!d.name)continue;const db=await new Promise((ok,no)=>{{const r=indexedDB.open(d.name);r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)}});out[d.name]={{}};for(const n of db.objectStoreNames)out[d.name][n]=await new Promise((ok,no)=>{{const tx=db.transaction(n,'readonly'),r=tx.objectStore(n).getAll();r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)}});db.close()}}return out}}""")
 def rows(s,n): return [x for db in s.values() for k,v in db.items() if k==n for x in v]
 def guard(context,blocked):
  context.route('**/*',lambda r:(r.continue_() if r.request.url.startswith('file:') else (blocked.append(r.request.url),r.abort())[1]))
 def focus_keys(page):
  return page.evaluate("""()=>{{const root=document.querySelector('.atlas-m1');if(!root)throw Error('ATLAS_SURFACE_MISSING');const selector='button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';const rows=[...root.querySelectorAll(selector)].filter(e=>{{const s=getComputedStyle(e);return s.visibility!=='hidden'&&s.display!=='none'&&!e.hidden}});rows.forEach((e,i)=>e.setAttribute('data-qa-focus-order',String(i)));return rows.map((e,i)=>String(i))}}""")
 def active_key(page): return page.evaluate("document.activeElement&&document.activeElement.getAttribute('data-qa-focus-order')")
 with sync_playwright() as p:
  browser=p.chromium.launch()
  evidence=[]
  for width,height in ((1440,900),(390,844)):
   blocked=[]; context=browser.new_context(viewport={{'width':width,'height':height}}); guard(context,blocked); page=context.new_page()
   page.goto(uri); page.wait_for_load_state('domcontentloaded')
   assert page.locator('[data-atlas-action="start"]').count()==1
   before=snap(page); page.locator('[data-atlas-action="start"]').click(); page.locator('[data-atlas-help]').wait_for()
   help_before=snap(page); text_before=page.locator('.atlas-m1').inner_text(); page.locator('[data-atlas-help]').first.click(); help_after=snap(page); text_after=page.locator('.atlas-m1').inner_text()
   assert help_after!=help_before and text_after!=text_before
   dbname=next((n for n in help_after if 'atlas' in n),None); assert dbname
   # A real multi-store transaction is explicitly aborted; no sentinel may persist.
   aborted=page.evaluate("""async(name)=>{{const db=await new Promise((ok,no)=>{{const r=indexedDB.open(name);r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)}});const names=[...db.objectStoreNames].slice(0,2);if(names.length<2)throw Error('ATLAS_STORES_MISSING');const tx=db.transaction(names,'readwrite');for(const n of names)tx.objectStore(n).put({{eventId:'qa-abort',executionId:'qa-abort',sessionRef:{{sessionId:'qa-abort'}},key:'qa-abort'}});tx.abort();await new Promise(ok=>{{tx.onabort=ok;tx.onerror=ok}});db.close();return true}}""",dbname); assert aborted and 'qa-abort' not in json.dumps(snap(page))
   page.locator('[data-atlas-submit]').click(); page.wait_for_timeout(30); committed=snap(page)
   executions=rows(committed,'scoredExecutions'); assert executions and executions[-1].get('assistance')=='used' and executions[-1].get('assistanceUseIds')
   expected=focus_keys(page); assert expected and len(expected)==len(set(expected))
   page.locator('[data-qa-focus-order="0"]').focus(); forward=[]
   for key in expected: forward.append(active_key(page)); assert forward[-1]==key; page.keyboard.press('Tab')
   forward_boundary=active_key(page); assert forward_boundary==expected[0]
   page.locator(f'[data-qa-focus-order="{{expected[-1]}}"]' ).focus(); reverse=[]
   for key in reversed(expected): reverse.append(active_key(page)); assert reverse[-1]==key; page.keyboard.press('Shift+Tab')
   reverse_boundary=active_key(page); assert reverse_boundary==expected[-1]
   assert forward==expected and reverse==list(reversed(expected))
   overflow=page.evaluate("""()=>[...document.querySelectorAll('.atlas-m1,.atlas-m1 *')].filter(e=>e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1).map(e=>e.outerHTML.slice(0,120))"""); assert not overflow
   long=page.evaluate("""()=>{{const b=document.createElement('button');b.textContent='Libellé très long '.repeat(30);b.style.maxWidth='280px';b.style.overflowWrap='anywhere';document.querySelector('.atlas-m1').appendChild(b);const ok=b.scrollWidth<=b.clientWidth+1;b.remove();return ok}}"""); assert long
   assert not blocked,'NETWORK_EGRESS_BLOCKED_BEFORE_REOPEN:'+json.dumps(blocked)
   context.close()
   context=browser.new_context(viewport={{'width':width,'height':height}}); guard(context,blocked); page=context.new_page()
   page.goto(uri); page.wait_for_load_state('domcontentloaded')
   assert snap(page)==committed; resume=page.locator('[data-atlas-action="resume"]'); assert resume.count()==1; resume.click(); page.wait_for_timeout(20)
   focus=page.evaluate('document.activeElement && document.activeElement.id'); states=rows(committed,'resumeStates'); target=states[-1].get('focusTarget') if states else None
   assert not target or focus==target
   assert not blocked,'NETWORK_EGRESS_BLOCKED_AFTER_REOPEN:'+json.dumps(blocked)
   evidence.append({{'viewport':[width,height],'snapshot':committed,'focusTarget':target,'focusOrder':expected}}); context.close()
  browser.close(); print(json.dumps(evidence))
 ''')

def run_browser(artifact):
 script=browser_script(artifact)
 if 'qaScenario' in script: raise AssertionError('CANDIDATE_SELF_ATTESTATION_FORBIDDEN')
 cp=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True)
 if cp.returncode: raise AssertionError('BROWSER_GATE_FAILED:'+cp.stderr)
 return json.loads(cp.stdout)

def snapshot_rows(snapshot,store): return [row for db in snapshot.values() for name,rows in db.items() if name==store for row in rows]

class OracleTests(unittest.TestCase):
 def claim_fixture(self):
  obj={'courseRef':{'packageLineageId':'p','courseLineageId':'c'},'objectiveId':'o'}; src={'courseRef':obj['courseRef'],'activityLineageId':'src'}; dst={'courseRef':obj['courseRef'],'activityLineageId':'dst'}
  payload={'claimVersion':'atlas.independence.v1','objectiveRef':obj,'sourceActivityRef':src,'targetActivityRef':dst,'basisCode':'new-instance','sourceStimulusDigest':'sha256:'+'1'*64,'targetStimulusDigest':'sha256:'+'2'*64}; cid='atlas-claim-sha256:'+ahash(CLAIM_DOMAIN,payload); return cid,{'claimId':cid,**payload}
 def maintenance_fixture(self,target_at):
  cid,claim=self.claim_fixture(); rev={'packageLineageId':'p','packageRevisionId':'r','packageDigest':'sha256:'+'1'*64}; session={'sessionId':'s','planId':'p'}; basis_at='2026-01-01T00:00:00.000Z'
  basis={'executionId':'xb','sessionRef':session,'courseRef':claim['objectiveRef']['courseRef'],'contentRevisionRef':rev,'objectiveRef':claim['objectiveRef'],'activityRef':claim['sourceActivityRef'],'executionClass':'validation','action':'attempt-validation','outcome':'correct','assistance':'none','scoredAt':basis_at}
  execution={'executionId':'xv','sessionRef':session,'courseRef':claim['objectiveRef']['courseRef'],'contentRevisionRef':rev,'planDigest':'sha256:'+'3'*64,'itemPosition':0,'objectiveRef':claim['objectiveRef'],'activityRef':claim['targetActivityRef'],'action':'maintain-recent-validation','executionClass':'validation','outcome':'correct','assistance':'none','scoredAt':target_at}
  item={'position':0,'objectiveRef':claim['objectiveRef'],'activityRef':claim['targetActivityRef'],'action':'maintain-recent-validation','executionClass':'validation','estimatedMinutes':5,'validationBasisEventId':'eb','independenceClaimId':cid}
  start={'eventId':'es','kind':'session-started','sessionRef':session,'courseRef':claim['objectiveRef']['courseRef'],'contentRevisionRef':rev,'planDigest':execution['planDigest'],'selectedItems':[item],'occurredAt':basis_at}
  events=[start,{'eventId':'eb','kind':'activity-attempt','objectiveRef':claim['objectiveRef'],'executionId':'xb','occurredAt':basis_at},{'eventId':'ev','kind':'activity-attempt','objectiveRef':claim['objectiveRef'],'executionId':'xv','occurredAt':target_at}]
  return next(iter(project(events,[basis,execution],{cid:claim},frozenset({cid}),rev).values()))
 def test_v2_01_browser_is_independent(self):
  s=browser_script(pathlib.Path('/tmp/a.html')); self.assertNotIn('qaScenario',s)
  for x in ('[data-atlas-action="start"]','[data-atlas-help]','[data-atlas-submit]','indexedDB.databases()','tx.abort()','context.close()'): self.assertIn(x,s)
 def test_v2_02_claim_ids_reconciled(self):
  cid,claim=self.claim_fixture(); rev={'packageLineageId':'p','packageRevisionId':'r','packageDigest':'sha256:'+'1'*64}; base={'schemaVersion':'atlas.accepted-validation-claims.v1','contentRevisionRef':rev,'oracleVersion':'o','artifactDigest':'sha256:'+'2'*64,'acceptedClaimIds':[cid]}
  self.assertEqual(check_claim_set(base,'2'*64,rev,'o',{cid:claim}),frozenset({cid}))
  base['acceptedClaimIds']=['atlas-claim-sha256:'+'9'*64]
  with self.assertRaisesRegex(AssertionError,'UNKNOWN_CANDIDATE'): check_claim_set(base,'2'*64,rev,'o',{cid:claim})
 def test_v2_03_projection_requires_exact_claim_and_basis(self):
  cid,claim=self.claim_fixture(); rev={'packageLineageId':'p','packageRevisionId':'r','packageDigest':'sha256:'+'1'*64}; session={'sessionId':'s','planId':'p'}
  basis={'executionId':'xb','sessionRef':session,'courseRef':claim['objectiveRef']['courseRef'],'contentRevisionRef':rev,'objectiveRef':claim['objectiveRef'],'activityRef':claim['sourceActivityRef'],'executionClass':'practice','action':'start-practice','outcome':'correct','assistance':'none'}
  execution={'executionId':'xv','sessionRef':session,'courseRef':claim['objectiveRef']['courseRef'],'contentRevisionRef':rev,'planDigest':'sha256:'+'3'*64,'itemPosition':0,'objectiveRef':claim['objectiveRef'],'activityRef':claim['targetActivityRef'],'action':'attempt-validation','executionClass':'validation','outcome':'correct','assistance':'none','scoredAt':'2026-01-02T00:00:00.000Z'}
  item={'position':0,'objectiveRef':claim['objectiveRef'],'activityRef':claim['targetActivityRef'],'action':'attempt-validation','executionClass':'validation','estimatedMinutes':5,'validationBasisEventId':'eb','independenceClaimId':cid}
  start={'eventId':'es','kind':'session-started','sessionRef':session,'courseRef':claim['objectiveRef']['courseRef'],'contentRevisionRef':rev,'planDigest':execution['planDigest'],'selectedItems':[item],'occurredAt':'2026-01-01T00:00:00.000Z'}
  events=[start,{'eventId':'eb','kind':'activity-attempt','objectiveRef':claim['objectiveRef'],'executionId':'xb','occurredAt':'2026-01-01T01:00:00.000Z'},{'eventId':'ev','kind':'activity-attempt','objectiveRef':claim['objectiveRef'],'executionId':'xv','occurredAt':'2026-01-02T00:00:00.000Z'}]
  row=next(iter(project(events,[basis,execution],{cid:claim},frozenset({cid}),rev).values())); self.assertEqual(row['state'],'validated-recently')
  row=next(iter(project(events,[basis,execution],{cid:claim},frozenset(),rev).values())); self.assertNotEqual(row['state'],'validated-recently')
 def test_v2_04_missing_source_fails(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); subprocess.run(['git','init','-q',str(root)],check=True); subprocess.run(['git','-C',str(root),'config','user.email','qa@example.test'],check=True); subprocess.run(['git','-C',str(root),'config','user.name','QA'],check=True); (root/'x').write_text('x'); subprocess.run(['git','-C',str(root),'add','x'],check=True); subprocess.run(['git','-C',str(root),'commit','-qm','init'],check=True); head=git(root,'rev-parse','HEAD')
   with self.assertRaisesRegex(AssertionError,'EXPECTED_SOURCE_FILE_MISSING'): bind_source(root,head)
 def test_v2_05_keyboard_focus_component_overflow(self):
  s=browser_script(pathlib.Path('/tmp/a.html'))
  for x in ('data-qa-focus-order','forward==expected','reverse==list(reversed(expected))','ATLAS_SURFACE_MISSING','scrollWidth>e.clientWidth','scrollHeight>e.clientHeight','focus==target','Libellé très long'): self.assertIn(x,s)
 def test_v3_01_maintenance_24h_boundaries_and_fail_closed(self):
  for target,expected in (('2026-01-01T23:59:59.999Z',False),('2026-01-02T00:00:00.000Z',True),('2026-01-02T00:00:00.001Z',True)):
   with self.subTest(target=target): self.assertEqual(self.maintenance_fixture(target)['state']=='validated-recently',expected)
  invalid=('2026-01-01T23:00:00.000Z','2026-01-02T00:00:00.000+00:00','2026-01-02 00:00:00.000Z','2026-02-30T00:00:00.000Z','2026-01-02T00:00:00Z','not-a-date')
  for target in invalid:
   with self.subTest(invalid=target): self.assertNotEqual(self.maintenance_fixture(target)['state'],'validated-recently')
 def test_v3_02_network_interception_survives_reopen(self):
  s=browser_script(pathlib.Path('/tmp/a.html')); contexts=[m.start() for m in re.finditer('context=browser.new_context',s)]; routes=[m.start() for m in re.finditer(r'; guard\(context,blocked\); page=context.new_page\(\)',s)]; pages=[m.start() for m in re.finditer(r'page=context.new_page\(\)',s)]
  self.assertEqual(len(contexts),2); self.assertEqual(len(routes),2); self.assertEqual(len(pages),2)
  for context,route,page in zip(contexts,routes,pages): self.assertLess(context,route); self.assertLess(route,page)
  self.assertIn('NETWORK_EGRESS_BLOCKED_AFTER_REOPEN',s)
  with self.assertRaisesRegex(AssertionError,'AFTER_REOPEN'): require_network_clean(['https://example.invalid/only-after-reopen'],'AFTER_REOPEN')
 def test_v3_03_exact_forward_reverse_focus_order_and_boundaries(self):
  expected=['0','1','2']; self.assertTrue(verify_focus_trace(expected,expected,['2','1','0'],'0','2'))
  bad=(('jump',['0','2','1'],['2','1','0'],'0','2'),('inversion',['2','1','0'],['2','1','0'],'0','2'),('duplicate',['0','1','1'],['2','1','0'],'0','2'),('outside',['0','outside','2'],['2','1','0'],'0','2'),('omitted',['0','1'],['2','1','0'],'0','2'),('reverse',['0','1','2'],['2','0','1'],'0','2'),('forward-boundary',['0','1','2'],['2','1','0'],'outside','2'),('reverse-boundary',['0','1','2'],['2','1','0'],'0','outside'))
  for name,forward,reverse,fb,rb in bad:
   with self.subTest(name=name):
    with self.assertRaisesRegex(AssertionError,'FOCUS_'): verify_focus_trace(expected,forward,reverse,fb,rb)
 def test_fill_max_uses_is_semantic_and_fail_closed(self):
  a={'type':'fill','prompt':'P','segments':[{'slotId':'a'},{'slotId':'b'}],'tokens':[{'tokenId':'t','label':'x','maxUses':2}],'answers':[{'slotId':'a','tokenId':'t'},{'slotId':'b','tokenId':'t'}]}; d=stimulus(a); a['tokens'][0]['maxUses']=3; self.assertNotEqual(d,stimulus(a)); a['tokens'][0]['maxUses']=1
  with self.assertRaisesRegex(AssertionError,'MAX_USES'): stimulus(a)
 def test_negative_canonical_collision(self):
  with self.assertRaisesRegex(AssertionError,'KEY_COLLISION'): canonical({'é':1,'e\u0301':2})
 def test_reward_priority(self):
  facts=[{'eventId':'same','rewardKind':'independent-success','occurredAt':'2026-01-01T00:00:00.000Z'},{'eventId':'same','rewardKind':'validation-completed','occurredAt':'2026-01-01T00:00:00.000Z'}]; self.assertEqual(exclusive_rewards(facts),['validation-completed'])
 def test_closed_reason_codes(self): self.assertIn('VALIDATION_AVAILABLE',REASONS); self.assertNotIn('FREE_TEXT',REASONS)
 def test_fixture_bytes(self):
  for rel,expected in FIXTURES.items():
   if (ROOT/rel).exists(): self.assertEqual(sha(ROOT/rel),expected)

def fixture_report():
 rows=[]; ok=True
 for rel,expected in FIXTURES.items():
  actual=sha(ROOT/rel) if (ROOT/rel).exists() else None; rows.append({'path':rel,'expectedSha256':expected,'actualSha256':actual,'unchanged':actual==expected}); ok &= actual==expected
 return rows,ok

def preflight():
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OracleTests)); rows,ok=fixture_report(); print(json.dumps({'verdict':'PRE_CANDIDATE_QA_READY' if result.wasSuccessful() and ok else 'CHANGES_REQUIRED','oracleTests':result.testsRun,'fixtures':rows,'contractFixturesModified':not ok},indent=2)); return 0 if result.wasSuccessful() and ok else 1

def strict(a):
 required=(a.candidate_head,a.artifact,a.artifact_sha256,a.claim_set,a.content_revision,a.oracle_version,a.artifact_provenance,a.repo_root,a.source_root)
 if not all(required): raise SystemExit('strict mode requires all exact inputs')
 if not SHA40.fullmatch(a.candidate_head) or not re.fullmatch(r'[0-9a-f]{64}',a.artifact_sha256): raise SystemExit('invalid candidate or artifact digest')
 heads=parse_heads(a.accepted_head); repo=pathlib.Path(a.repo_root).resolve(); bind_heads(repo,a.candidate_head,heads); source=pathlib.Path(a.source_root).resolve(); paths=bind_source(source,a.candidate_head)
 artifact=pathlib.Path(a.artifact).resolve(); actual=sha(artifact)
 if actual!=a.artifact_sha256: raise SystemExit('ARTIFACT_SHA256_MISMATCH')
 provenance(pathlib.Path(a.artifact_provenance),a.candidate_head,heads,actual); rev=json.loads(pathlib.Path(a.content_revision).read_text(encoding='utf-8')); claims=load_claims(source,rev); accepted=check_claim_set(json.loads(pathlib.Path(a.claim_set).read_text(encoding='utf-8')),actual,rev,a.oracle_version,claims)
 findings=network(paths)
 if findings: raise SystemExit('STATIC_NETWORK_GATE_FAILED:'+json.dumps(findings))
 _,ok=fixture_report()
 if not ok: raise SystemExit('CONTRACT_FIXTURES_MODIFIED')
 evidence=run_browser(artifact); projections=[]
 for viewport in evidence:
  events=snapshot_rows(viewport['snapshot'],'learningEvents'); executions=snapshot_rows(viewport['snapshot'],'scoredExecutions')
  if not events or not executions: raise SystemExit('BROWSER_FACT_EVIDENCE_EMPTY')
  projections.append(project(events,executions,claims,accepted,rev))
 print(json.dumps({'verdict':'PASS_TO_HUMAN_GATE','candidateHead':a.candidate_head,'artifactSha256':actual,'acceptedHeads':heads,'oracleVersion':a.oracle_version,'acceptedClaimIds':sorted(accepted),'candidateClaimsRecalculated':len(claims),'contractFixturesModified':False,'staticNetworkGate':'PASS','browserAndFaultInjection':'PASS_INDEPENDENT_DRIVER','viewports':[x['viewport'] for x in evidence],'independentEvidenceProjections':projections},indent=2)); return 0

def main():
 p=argparse.ArgumentParser(); p.add_argument('--strict',action='store_true'); p.add_argument('--candidate-head'); p.add_argument('--artifact'); p.add_argument('--artifact-sha256'); p.add_argument('--accepted-head',action='append',default=[]); p.add_argument('--claim-set'); p.add_argument('--content-revision'); p.add_argument('--oracle-version'); p.add_argument('--artifact-provenance'); p.add_argument('--repo-root'); p.add_argument('--source-root'); a=p.parse_args(); return strict(a) if a.strict else preflight()
if __name__=='__main__': raise SystemExit(main())
