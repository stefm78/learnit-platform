#!/usr/bin/env python3
"""Independent, fail-closed Atlas M1 0.3 QA oracle.

Default mode tests only the oracle and immutable contract fixtures. Strict mode
requires an exact integrated candidate, artifact, accepted heads/claims and real
product action selectors. Candidate declarations never count as evidence.
"""
from __future__ import annotations
import argparse, copy, datetime, hashlib, json, os, pathlib, re, subprocess, sys, tempfile, textwrap, unittest, unicodedata
from typing import Any

ROOT=pathlib.Path(__file__).resolve().parents[3]
FIXTURES={
 "contracts/fixtures/atlas-m1-valid-loop.json":"2abc0ecf8eb1f4b7afcb1e7a010015e9549bfbf0a4a6dcc4379a65c2c5fda46a",
 "contracts/fixtures/atlas-m1-invalid-loop.json":"dca06d3df5cdb0c0492f38e787996ca95f760f6cbdd0c72f8bed5e1a498cca0d"}
LANES={
 "learning":("apps/learnit-next/src/core/atlas_evidence.js","apps/learnit-next/src/core/atlas_recommendation.js","apps/learnit-next/src/core/atlas_planner.js","apps/learnit-next/tests/atlas_m1_learning.py"),
 "core":("apps/learnit-next/src/core/atlas_events.js","apps/learnit-next/src/core/atlas_projection.js","apps/learnit-next/src/core/atlas_clock.js","apps/learnit-next/src/ports/atlas_storage.js","apps/learnit-next/src/adapters/atlas_indexeddb.js","apps/learnit-next/tests/atlas_m1_core.py"),
 "experience":("apps/learnit-next/src/ui/atlas_today.js","apps/learnit-next/src/ui/atlas_session.js","apps/learnit-next/src/ui/atlas_summary.js","apps/learnit-next/src/ui/atlas_rewards.js","apps/learnit-next/src/atlas.css","apps/learnit-next/tests/atlas_m1_experience.py"),
 "content":("authoring/v2/atlas/README.md","authoring/v2/atlas/nombres_complexes_atlas.json","authoring/v2/atlas/signaux_electriques_atlas.json","authoring/v2/atlas/validate_atlas_content.py","apps/learnit-next/tests/atlas_m1_content.py")}
PACKAGES=tuple(x for x in LANES["content"] if x.endswith("_atlas.json"))
STORES=("learningEvents","resumeStates","scoredExecutions")
KEYS={"learningEvents":"eventId","resumeStates":"sessionRef.sessionId","scoredExecutions":"executionId"}
LIFECYCLE=("session-interrupted","session-resumed","session-completed")
REWARDS=("validation-reconfirmed","validation-completed","correction-completed","independent-success","resumed-after-interruption")
REASONS={"NEW_OBJECTIVE","PRACTICE_IN_PROGRESS","RECENT_ERROR","REVIEW_REQUIRED","CORRECTION_COMPLETED","NO_INDEPENDENT_VALIDATION","VALIDATION_AVAILABLE","RECENTLY_VALIDATED","SESSION_TIME_LIMIT"}
SHA40=re.compile(r"^[0-9a-f]{40}$"); HEX64=re.compile(r"^[0-9a-f]{64}$"); DIGEST=re.compile(r"^sha256:[0-9a-f]{64}$")
EVENT_ID=re.compile(r"^atlas-event-sha256:[0-9a-f]{64}$"); EXEC_ID=re.compile(r"^atlas-execution-sha256:[0-9a-f]{64}$"); CLAIM_ID=re.compile(r"^atlas-claim-sha256:[0-9a-f]{64}$")
UTC=re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"); DAY=86400000
EVENT_DOMAIN="learnit.atlas.m1.v0.3/event-id"; CLAIM_DOMAIN="learnit.atlas.m1.v0.3/validation-claim-id"

def sha(path: pathlib.Path|str)->str:
 h=hashlib.sha256()
 with pathlib.Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()

def canon(v:Any)->Any:
 if v is None or isinstance(v,(bool,int,str)): return unicodedata.normalize("NFC",v) if isinstance(v,str) else v
 if isinstance(v,float): raise AssertionError("NON_CANONICAL_NUMBER")
 if isinstance(v,list): return [canon(x) for x in v]
 if isinstance(v,dict):
  out={}; rows=[]
  for k,x in v.items():
   if not isinstance(k,str): raise AssertionError("NON_CANONICAL_KEY")
   n=unicodedata.normalize("NFC",k)
   if n in out: raise AssertionError("CANONICAL_KEY_COLLISION")
   out[n]=x; rows.append(n)
  return {k:canon(out[k]) for k in sorted(rows,key=lambda x:[ord(c) for c in x])}
 raise AssertionError("NON_CANONICAL_VALUE")

def cj(v:Any)->str: return json.dumps(canon(v),ensure_ascii=False,separators=(",",":"))
def same(a:Any,b:Any)->bool: return cj(a)==cj(b)
def dh(domain:str,v:Any)->str: return hashlib.sha256(domain.encode()+b"\0"+cj(v).encode()).hexdigest()
def event_id(payload:dict[str,Any])->str: return "atlas-event-sha256:"+dh(EVENT_DOMAIN,payload)
def without(v:dict[str,Any],field:str)->dict[str,Any]: return {k:x for k,x in v.items() if k!=field}

def closed(v:Any,required:tuple[str,...],optional:tuple[str,...]=())->None:
 if not isinstance(v,dict) or not set(required)<=set(v) or set(v)-set(required)-set(optional): raise AssertionError("OBJECT_NOT_CLOSED")

def utc_ms(v:Any)->int:
 if not isinstance(v,str) or not UTC.fullmatch(v): raise AssertionError("NONCANONICAL_UTC_TIMESTAMP")
 try: d=datetime.datetime.strptime(v,"%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
 except ValueError as e: raise AssertionError("INVALID_UTC_TIMESTAMP") from e
 if d.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]+"Z"!=v: raise AssertionError("NONCANONICAL_UTC_TIMESTAMP")
 return int(d.timestamp()*1000)

def maintenance_due(a:dict[str,Any],b:dict[str,Any])->bool:
 try:return utc_ms(b.get("occurredAt"))-utc_ms(a.get("occurredAt"))>=DAY
 except AssertionError:return False

def focus_trace(expected:list[str],forward:list[str],reverse:list[str],fb:str,rb:str)->bool:
 if not expected or len(expected)!=len(set(expected)): raise AssertionError("FOCUS_EXPECTED_INVALID")
 if forward!=expected: raise AssertionError("FOCUS_FORWARD_ORDER_INVALID")
 if reverse!=list(reversed(expected)): raise AssertionError("FOCUS_REVERSE_ORDER_INVALID")
 if fb!=expected[0]: raise AssertionError("FOCUS_FORWARD_BOUNDARY_INVALID")
 if rb!=expected[-1]: raise AssertionError("FOCUS_REVERSE_BOUNDARY_INVALID")
 return True

def nested(row:dict[str,Any],path:str)->Any:
 v:Any=row
 for p in path.split("."): v=v.get(p) if isinstance(v,dict) else None
 return v

def norm_store(rows:Any,store:str)->list[dict[str,Any]]:
 if not isinstance(rows,list): raise AssertionError("SNAPSHOT_ROWS_REQUIRED")
 out=[]; seen=set()
 for row in rows:
  if not isinstance(row,dict): raise AssertionError("SNAPSHOT_ROW_INVALID")
  k=nested(row,KEYS[store])
  if not isinstance(k,str) or not k or k in seen: raise AssertionError("SNAPSHOT_KEY_INVALID")
  seen.add(k); out.append((k,canon(row)))
 return [v for _,v in sorted(out,key=lambda x:[ord(c) for c in x[0]])]

def norm_snap(s:Any)->dict[str,list[dict[str,Any]]]:
 if not isinstance(s,dict) or set(s)!=set(STORES): raise AssertionError("SNAPSHOT_EXACT_STORES_REQUIRED")
 return {k:norm_store(s[k],k) for k in STORES}
def snap_bytes(s:Any)->bytes:return cj(norm_snap(s)).encode()
def idx(s:Any,store:str)->dict[str,dict[str,Any]]:return {nested(x,KEYS[store]):x for x in norm_snap(s)[store]}

def delta(a:Any,b:Any,store:str)->tuple[list, list, list]:
 x=idx(a,store); y=idx(b,store)
 return ([y[k] for k in sorted(set(y)-set(x))],[x[k] for k in sorted(set(x)-set(y))],[y[k] for k in sorted(set(x)&set(y)) if not same(x[k],y[k])])

def validate_focus(v:Any)->bool:
 closed(v,("expected","forward","reverse","forwardBoundary","reverseBoundary","overflow","longLabelFits"))
 focus_trace(v["expected"],v["forward"],v["reverse"],v["forwardBoundary"],v["reverseBoundary"])
 if v["overflow"]: raise AssertionError("COMPONENT_OVERFLOW_DETECTED")
 if v["longLabelFits"] is not True: raise AssertionError("LONG_LABEL_OVERFLOW")
 return True

def tx(trace:Any,faulted:bool)->dict[str,Any]:
 closed(trace,("observerInstalledBeforeCandidate","trigger","candidateTransaction","additionalWriteTransactions","snapshots"),("viewport","focusEvidence"))
 if trace["observerInstalledBeforeCandidate"] is not True: raise AssertionError("OBSERVATION_HOOKS_MISSING")
 if trace["trigger"]!="user-action": raise AssertionError("SUBMISSION_NOT_PRODUCT_TRIGGERED")
 if trace.get("viewport") not in (None,[1440,900],[390,844]): raise AssertionError("FROZEN_VIEWPORT_INVALID")
 if "focusEvidence" in trace: validate_focus(trace["focusEvidence"])
 t=trace["candidateTransaction"]
 closed(t,("origin","mode","storeNames","writes","abortObserved","commitObserved","faultArmed","faultTriggered","faultWriteOrdinal","faultStage"))
 if t["origin"]!="candidate": raise AssertionError("ORACLE_TRANSACTION_FORBIDDEN")
 if t["mode"]!="readwrite" or not isinstance(t["storeNames"],list) or len(t["storeNames"])!=len(set(t["storeNames"])) or set(t["storeNames"])!=set(STORES): raise AssertionError("CANDIDATE_TRANSACTION_EXACT_THREE_STORES_REQUIRED")
 if trace["additionalWriteTransactions"]: raise AssertionError("UNEXPECTED_ADDITIONAL_WRITE_TRANSACTION")
 if not isinstance(t["writes"],list) or any(not isinstance(x,dict) for x in t["writes"]): raise AssertionError("CANDIDATE_TRANSACTION_WRITES_INVALID")
 if faulted:
  if t["faultArmed"] is not True or t["faultTriggered"] is not True: raise AssertionError("FAULT_INJECTION_NOT_TRIGGERED")
  if not isinstance(t["faultWriteOrdinal"],int) or t["faultWriteOrdinal"]<1: raise AssertionError("FAULT_BEFORE_ANY_WRITE")
  if t["faultStage"]!="after-write-before-complete": raise AssertionError("FAULT_TOO_EARLY_OR_TOO_LATE")
  if t["abortObserved"] is not True or t["commitObserved"] is not False: raise AssertionError("CANDIDATE_TRANSACTION_NOT_ABORTED")
 else:
  if t["faultArmed"] or t["faultTriggered"] or t["abortObserved"] or t["commitObserved"] is not True: raise AssertionError("POSITIVE_TRANSACTION_NOT_COMMITTED")
 return t

def fault_trace(trace:dict[str,Any])->bool:
 t=tx(trace,True); s=trace["snapshots"]; closed(s,("before","immediate","afterDatabaseClose","afterContextReopen","settled"))
 base=snap_bytes(s["before"])
 for p in ("immediate","afterDatabaseClose","afterContextReopen","settled"):
  if snap_bytes(s[p])!=base: raise AssertionError("ATOMICITY_PARTIAL_OR_COMPENSATING_WRITE:"+p)
 if len(t["writes"])<t["faultWriteOrdinal"]: raise AssertionError("FAULT_WRITE_NOT_OBSERVED")
 return True

def started_for(snapshot:Any,execution:dict[str,Any])->dict[str,Any]:
 rows=[x for x in norm_snap(snapshot)["learningEvents"] if x.get("kind")=="session-started" and x.get("sessionRef")==execution.get("sessionRef")]
 if len(rows)!=1: raise AssertionError("POSITIVE_SESSION_STARTED_REQUIRED")
 return rows[0]

def submission_links(exe:dict[str,Any],ev:dict[str,Any],resume:dict[str,Any],snapshot:Any,accepted:frozenset[str]|None,revision:dict[str,Any]|None)->None:
 required=("executionId","sessionRef","courseRef","contentRevisionRef","planDigest","itemPosition","objectiveRef","activityRef","action","executionClass","outcome","assistance","submittedAt","scoredAt")
 if any(k not in exe for k in required) or not EXEC_ID.fullmatch(exe.get("executionId","")): raise AssertionError("POSITIVE_EXECUTION_INCOMPLETE")
 if not EVENT_ID.fullmatch(ev.get("eventId","")) or ev.get("executionId")!=exe["executionId"] or ev.get("objectiveRef")!=exe["objectiveRef"]: raise AssertionError("POSITIVE_EVENT_LINK_INVALID")
 if resume.get("sessionRef")!=exe["sessionRef"] or resume.get("courseRef")!=exe["courseRef"] or resume.get("contentRevisionRef")!=exe["contentRevisionRef"] or resume.get("planDigest")!=exe["planDigest"] or resume.get("lastCommittedEventId")!=ev["eventId"]: raise AssertionError("POSITIVE_RESUME_LINK_INVALID")
 for k in ("submittedAt","scoredAt"): utc_ms(exe[k])
 utc_ms(ev.get("occurredAt"))
 if revision is not None and exe["contentRevisionRef"]!=revision: raise AssertionError("POSITIVE_REVISION_NOT_EXACT")
 start=started_for(snapshot,exe); items=start.get("selectedItems")
 if not isinstance(items,list) or exe["itemPosition"]>=len(items): raise AssertionError("POSITIVE_PLAN_ITEM_MISSING")
 item=items[exe["itemPosition"]]
 for k in ("objectiveRef","activityRef","action","executionClass"):
  if item.get(k)!=exe.get(k): raise AssertionError("POSITIVE_PLAN_LINK_INVALID")
 if exe["executionClass"]=="validation":
  claim=item.get("independenceClaimId")
  if accepted is None or claim not in accepted: raise AssertionError("POSITIVE_ACCEPTED_CLAIM_REQUIRED")

def positive_trace(trace:dict[str,Any],accepted:frozenset[str]|None=None,revision:dict[str,Any]|None=None)->dict[str,Any]:
 t=tx(trace,False); s=trace["snapshots"]; closed(s,("before","afterCommit","settled"))
 if snap_bytes(s["afterCommit"])!=snap_bytes(s["settled"]): raise AssertionError("UNEXPECTED_COMPENSATING_WRITE_AFTER_COMMIT")
 changes={k:delta(s["before"],s["afterCommit"],k) for k in STORES}
 ea,er,ec=changes["scoredExecutions"]; va,vr,vc=changes["learningEvents"]; ra,rr,rc=changes["resumeStates"]
 if er or ec or len(ea)!=1 or vr or vc or len(va)!=1 or rr or len(ra)+len(rc)!=1: raise AssertionError("POSITIVE_ALL_THREE_DELTA_INVALID")
 resume=(ra+rc)[0]; submission_links(ea[0],va[0],resume,s["afterCommit"],accepted,revision)
 ws=[x.get("store") for x in t["writes"]]
 if set(ws)!=set(STORES) or any(ws.count(k)!=1 for k in STORES): raise AssertionError("UNEXPECTED_ADDITIONAL_WRITE")
 return {"execution":ea[0],"event":va[0],"resumeState":resume}

def life_rows(snapshot:Any,session:dict[str,Any])->list[dict[str,Any]]:
 return sorted([x for x in norm_snap(snapshot)["learningEvents"] if x.get("kind") in LIFECYCLE and x.get("sessionRef")==session],key=lambda x:x.get("eventOrdinal",-1))

def life_event(ev:dict[str,Any],kind:str,start:dict[str,Any],resume:dict[str,Any],previous:int,previous_at:str,completed:bool=False)->bool:
 closed(ev,("eventVersion","eventId","eventOrdinal","kind","sessionRef","occurredAt"))
 if completed: raise AssertionError("LIFECYCLE_EVENT_AFTER_COMPLETION")
 if ev["eventVersion"]!="atlas.learning-event.v1" or ev["kind"]!=kind: raise AssertionError("LIFECYCLE_KIND_INVALID")
 if ev["eventOrdinal"]!=previous+1: raise AssertionError("LIFECYCLE_ORDINAL_SEQUENCE_INVALID")
 if ev["sessionRef"]!=start.get("sessionRef") or ev["sessionRef"]!=resume.get("sessionRef"): raise AssertionError("LIFECYCLE_SESSION_RELATION_INVALID")
 if resume.get("lifecycleOrdinal")!=ev["eventOrdinal"]: raise AssertionError("LIFECYCLE_RESUME_ORDINAL_MISMATCH")
 if resume.get("courseRef")!=start.get("courseRef") or resume.get("contentRevisionRef")!=start.get("contentRevisionRef") or resume.get("planDigest")!=start.get("planDigest"): raise AssertionError("LIFECYCLE_PLAN_REVISION_RELATION_INVALID")
 if utc_ms(ev["occurredAt"])<utc_ms(previous_at): raise AssertionError("LIFECYCLE_TIMESTAMP_REGRESSION")
 if ev["eventId"]!=event_id(without(ev,"eventId")): raise AssertionError("LIFECYCLE_EVENT_ID_INVALID")
 return True

def walk(v:Any):
 if isinstance(v,dict):
  yield v
  for x in v.values(): yield from walk(x)
 elif isinstance(v,list):
  for x in v: yield from walk(x)

def pedagogical(exact:Any,all_data:Any|None=None)->dict[str,Any]:
 s=norm_snap(exact); objects=list(walk(all_data)) if all_data is not None else [x for rows in s.values() for x in rows]
 return {"executions":s["scoredExecutions"],"events":[x for x in s["learningEvents"] if x.get("kind") not in LIFECYCLE],"evidence":sorted([x for x in objects if x.get("evidenceVersion")=="atlas.objective-evidence.v1"],key=cj),"rewards":sorted([x for x in objects if x.get("rewardKind") in REWARDS],key=cj)}

def lifecycle_trace(t:dict[str,Any])->bool:
 closed(t,("observerInstalledBeforeCandidate","triggerInterruption","triggerResume","startedEvent","beforeInterruption","afterInterruption","afterFirstReopen","afterResume","afterSecondReopen"),("viewport","focusEvidence","allBefore","allAfterInterruption","allAfterFirstReopen","allAfterResume","allAfterSecondReopen"))
 if t["observerInstalledBeforeCandidate"] is not True: raise AssertionError("OBSERVATION_HOOKS_MISSING")
 if t["triggerInterruption"]!="product-interruption-action" or t["triggerResume"]!="product-resume-action": raise AssertionError("LIFECYCLE_NOT_PRODUCT_TRIGGERED")
 if t.get("viewport") not in (None,[1440,900],[390,844]): raise AssertionError("FROZEN_VIEWPORT_INVALID")
 if "focusEvidence" in t: validate_focus(t["focusEvidence"])
 start=t["startedEvent"]
 if start.get("kind")!="session-started" or start.get("eventOrdinal")!=0: raise AssertionError("SESSION_STARTED_REQUIRED")
 session=start.get("sessionRef"); before=t["beforeInterruption"]; interrupted=t["afterInterruption"]; reopened=t["afterFirstReopen"]; resumed=t["afterResume"]; twice=t["afterSecondReopen"]
 base_res=[x for x in norm_snap(before)["resumeStates"] if x.get("sessionRef")==session]
 if len(base_res)!=1: raise AssertionError("RESUME_STATE_BEFORE_INTERRUPTION_REQUIRED")
 rows=life_rows(interrupted,session)
 if len(rows)!=1 or rows[0].get("kind")!="session-interrupted": raise AssertionError("SESSION_INTERRUPTED_EVENT_REQUIRED")
 ir=[x for x in norm_snap(interrupted)["resumeStates"] if x.get("sessionRef")==session]
 if len(ir)!=1: raise AssertionError("LIFECYCLE_RESUME_STATE_REQUIRED")
 life_event(rows[0],"session-interrupted",start,ir[0],0,start["occurredAt"])
 if snap_bytes(interrupted)!=snap_bytes(reopened): raise AssertionError("INTERRUPTION_NOT_PERSISTED_AFTER_REOPEN")
 rows2=life_rows(resumed,session)
 if len(rows2)!=2: raise AssertionError("SESSION_RESUMED_EVENT_REQUIRED")
 if [x.get("eventOrdinal") for x in rows2]!=[1,2]: raise AssertionError("LIFECYCLE_ORDINAL_SEQUENCE_INVALID")
 if [x.get("kind") for x in rows2]!=["session-interrupted","session-resumed"]: raise AssertionError("SESSION_RESUMED_EVENT_REQUIRED")
 rr=[x for x in norm_snap(resumed)["resumeStates"] if x.get("sessionRef")==session]
 if len(rr)!=1: raise AssertionError("LIFECYCLE_RESUME_STATE_REQUIRED")
 life_event(rows2[1],"session-resumed",start,rr[0],1,rows2[0]["occurredAt"])
 if snap_bytes(resumed)!=snap_bytes(twice): raise AssertionError("LIFECYCLE_NOT_PERSISTED_AFTER_SECOND_REOPEN")
 pairs=(("afterInterruption",interrupted,"allAfterInterruption"),("afterFirstReopen",reopened,"allAfterFirstReopen"),("afterResume",resumed,"allAfterResume"),("afterSecondReopen",twice,"allAfterSecondReopen"))
 baseline=pedagogical(before,t.get("allBefore"))
 for name,snap,all_key in pairs:
  if not same(pedagogical(snap,t.get(all_key)),baseline): raise AssertionError("LIFECYCLE_CHANGED_PEDAGOGICAL_EVIDENCE:"+name)
 return True

def fixture_report()->tuple[list[dict[str,Any]],bool]:
 allow=os.environ.get("ATLAS_QA_ALLOW_MISSING_FIXTURES")=="1"; out=[]; ok=True
 for rel,expected in FIXTURES.items():
  p=ROOT/rel; actual=sha(p) if p.exists() else None; good=actual==expected
  out.append({"path":rel,"expectedSha256":expected,"actualSha256":actual,"unchanged":good,"missingAllowedForLocalOracleSelfTest":actual is None and allow}); ok&=good or (actual is None and allow)
 return out,ok

def init_script()->str:
 return r'''(()=>{const exact=['learningEvents','resumeStates','scoredExecutions'],m=new WeakMap(),dbs=new Set(),s={installedBeforeCandidate:true,phase:'bootstrap',next:1,transactions:[],fault:{armed:false,triggered:false,writeOrdinal:0,stage:null}};const o=IDBFactory.prototype.open;IDBFactory.prototype.open=function(...a){const r=o.apply(this,a);r.addEventListener('success',()=>{if(r.result)dbs.add(r.result)});return r};const t=IDBDatabase.prototype.transaction;IDBDatabase.prototype.transaction=function(n,mode,...a){const names=(typeof n==='string'?[n]:Array.from(n)).map(String).sort(),tx=t.call(this,n,mode,...a),x={origin:'candidate',mode:mode||'readonly',storeNames:names,phase:s.phase,writes:[],abortObserved:false,commitObserved:false,faultArmed:s.fault.armed,faultTriggered:false,faultWriteOrdinal:0,faultStage:null};s.transactions.push(x);m.set(tx,x);tx.addEventListener('complete',()=>x.commitObserved=true);tx.addEventListener('abort',()=>x.abortObserved=true);return tx};for(const name of ['put','add','delete','clear']){const f=IDBObjectStore.prototype[name];IDBObjectStore.prototype[name]=function(...a){const x=m.get(this.transaction);if(x){x.writes.push({store:this.name,method:name,ordinal:x.writes.length+1});if(s.fault.armed&&!s.fault.triggered&&x.phase==='submission-fault'&&x.mode==='readwrite'&&exact.every(k=>x.storeNames.includes(k))){s.fault={armed:true,triggered:true,writeOrdinal:x.writes.length,stage:'after-write-before-complete'};x.faultTriggered=true;x.faultWriteOrdinal=x.writes.length;x.faultStage=s.fault.stage;queueMicrotask(()=>{if(!x.commitObserved&&!x.abortObserved)this.transaction.abort()})}}return f.apply(this,a)}}Object.defineProperty(window,'__ATLAS_QA_OBSERVER__',{value:Object.freeze({setPhase:v=>s.phase=String(v),armFault:()=>s.fault={armed:true,triggered:false,writeOrdinal:0,stage:null},closeDatabases:()=>{for(const d of dbs)try{d.close()}catch(_){}dbs.clear()},report:()=>structuredClone(s)})})})();'''

def validate_driver(d:Any)->dict[str,Any]:
 closed(d,("startSelector","submitSelector","interruptSelector","resumeSelector","responseSteps","waitAfterActionMs"))
 for k in ("startSelector","submitSelector","interruptSelector","resumeSelector"):
  if not isinstance(d[k],str) or not d[k]: raise AssertionError("DRIVER_SELECTOR_REQUIRED")
 if not isinstance(d["waitAfterActionMs"],int) or isinstance(d["waitAfterActionMs"],bool) or not 0<=d["waitAfterActionMs"]<=5000: raise AssertionError("DRIVER_WAIT_INVALID")
 if not isinstance(d["responseSteps"],list) or not d["responseSteps"]: raise AssertionError("DRIVER_RESPONSE_REQUIRED")
 for x in d["responseSteps"]:
  closed(x,("action","selector"),("value",))
  if x["action"] not in ("click","fill","press") or not isinstance(x["selector"],str): raise AssertionError("DRIVER_STEP_INVALID")
  if x["action"] in ("fill","press") and not isinstance(x.get("value"),str): raise AssertionError("DRIVER_VALUE_REQUIRED")
 return d

def browser_script(artifact:pathlib.Path,driver:dict[str,Any])->str:
 return textwrap.dedent(f'''\
from playwright.sync_api import sync_playwright
from pathlib import Path
import json,tempfile
uri=Path({str(artifact)!r}).resolve().as_uri();driver=json.loads({json.dumps(json.dumps(driver,ensure_ascii=False))!r});preload={init_script()!r};exact=['learningEvents','resumeStates','scoredExecutions']
def guard(c,j):c.route('**/*',lambda r:r.continue_() if r.request.url.startswith('file:') else (j.append(r.request.url),r.abort())[1])
def open_c(p,d,j,v):
 c=p.chromium.launch_persistent_context(d,headless=True,viewport={{'width':v[0],'height':v[1]}});c.add_init_script(script=preload);guard(c,j);q=c.new_page();q.goto(uri);q.wait_for_load_state('domcontentloaded');assert q.evaluate("Boolean(window.__ATLAS_QA_OBSERVER__&&window.__ATLAS_QA_OBSERVER__.report().installedBeforeCandidate)");return c,q
def act(q,s):
 x=q.locator(s);assert x.count()==1,'PRODUCT_ACTION_PATH_NOT_EXACT:'+s;x.click();q.wait_for_timeout(driver['waitAfterActionMs'])
def answer(q):
 for a in driver['responseSteps']:
  x=q.locator(a['selector']);assert x.count()==1,'RESPONSE_PATH_NOT_EXACT:'+a['selector'];x.click() if a['action']=='click' else x.fill(a['value']) if a['action']=='fill' else x.press(a['value'])
def snap(q,all_stores=False):return q.evaluate("""async p=>{{const out={{}},found=[];for(const z of await indexedDB.databases()){{if(!z.name)continue;const d=await new Promise((ok,no)=>{{const r=indexedDB.open(z.name);r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)}}),names=[...d.objectStoreNames];if(p.all||p.exact.every(k=>names.includes(k)))found.push(d);else d.close()}}if(!p.all&&found.length!==1)throw Error('EXACT_ATLAS_DATABASE_REQUIRED:'+found.length);for(const d of found){{const target=p.all?(out[d.name]={{}}):out;for(const n of (p.all?[...d.objectStoreNames]:p.exact))target[n]=await new Promise((ok,no)=>{{const t=d.transaction(n,'readonly'),r=t.objectStore(n).getAll();r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)}});d.close()}}return out}}""",{{'all':all_stores,'exact':exact}})
def report(q,phase,fault):
 r=q.evaluate("window.__ATLAS_QA_OBSERVER__.report()");rows=[x for x in r['transactions'] if x['phase']==phase and x['mode']=='readwrite'];assert len(rows)==1,'EXACT_ONE_CANDIDATE_WRITE_TRANSACTION_REQUIRED:'+str(len(rows));x=rows[0];o={{k:x[k] for k in ('origin','mode','storeNames','writes','abortObserved','commitObserved','faultArmed','faultTriggered','faultWriteOrdinal','faultStage')}}
 if fault:o.update(faultArmed=r['fault']['armed'],faultTriggered=r['fault']['triggered'],faultWriteOrdinal=r['fault']['writeOrdinal'],faultStage=r['fault']['stage'])
 return o,[]
def focus(q):
 e=q.evaluate("""()=>{{const r=document.querySelector('.atlas-m1');if(!r)throw Error('ATLAS_SURFACE_MISSING');const s='button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex=\"-1\"])',a=[...r.querySelectorAll(s)].filter(x=>{{const z=getComputedStyle(x);return z.visibility!=='hidden'&&z.display!=='none'&&!x.hidden}});a.forEach((x,i)=>x.setAttribute('data-qa-focus-order',String(i)));return a.map((_,i)=>String(i))}}""");assert e and len(e)==len(set(e));active=lambda:q.evaluate("document.activeElement&&document.activeElement.getAttribute('data-qa-focus-order')");q.locator('[data-qa-focus-order="0"]').focus();f=[]
 for k in e:f.append(active());q.keyboard.press('Tab')
 fb=active();q.locator('[data-qa-focus-order="'+e[-1]+'"]').focus();rv=[]
 for k in reversed(e):rv.append(active());q.keyboard.press('Shift+Tab')
 rb=active();ov=q.evaluate("""()=>[...document.querySelectorAll('.atlas-m1,.atlas-m1 *')].filter(x=>x.scrollWidth>x.clientWidth+1||x.scrollHeight>x.clientHeight+1).map(x=>x.outerHTML.slice(0,120))""");long=q.evaluate("""()=>{{const r=document.querySelector('.atlas-m1'),b=document.createElement('button');b.textContent='Libellé très long '.repeat(30);b.style.maxWidth='280px';b.style.overflowWrap='anywhere';r.appendChild(b);const ok=b.scrollWidth<=b.clientWidth+1;b.remove();return ok}}""");return {{'expected':e,'forward':f,'reverse':rv,'forwardBoundary':fb,'reverseBoundary':rb,'overflow':ov,'longLabelFits':long}}
with sync_playwright() as p:
 out={{'fault':[],'positive':[],'lifecycle':[]}}
 for v in ((1440,900),(390,844)):
  j=[]
  with tempfile.TemporaryDirectory() as d:
   c,q=open_c(p,d,j,v);act(q,driver['startSelector']);answer(q);before=snap(q);q.evaluate("window.__ATLAS_QA_OBSERVER__.setPhase('submission-fault');window.__ATLAS_QA_OBSERVER__.armFault()")
   try:act(q,driver['submitSelector'])
   except Exception:pass
   q.wait_for_timeout(max(100,driver['waitAfterActionMs']));immediate=snap(q);x,extra=report(q,'submission-fault',True);q.evaluate("window.__ATLAS_QA_OBSERVER__.closeDatabases()");closed_db=snap(q);c.close();c,q=open_c(p,d,j,v);reopen=snap(q);q.wait_for_timeout(max(100,driver['waitAfterActionMs']));settled=snap(q);out['fault'].append({{'observerInstalledBeforeCandidate':True,'trigger':'user-action','candidateTransaction':x,'additionalWriteTransactions':extra,'snapshots':{{'before':before,'immediate':immediate,'afterDatabaseClose':closed_db,'afterContextReopen':reopen,'settled':settled}},'viewport':list(v)}});c.close()
  assert not j,'NETWORK_EGRESS_BLOCKED_FAULT:'+json.dumps(j)
  j=[]
  with tempfile.TemporaryDirectory() as d:
   c,q=open_c(p,d,j,v);act(q,driver['startSelector']);answer(q);before=snap(q);q.evaluate("window.__ATLAS_QA_OBSERVER__.setPhase('submission-positive')");act(q,driver['submitSelector']);after=snap(q);q.wait_for_timeout(max(100,driver['waitAfterActionMs']));settled=snap(q);x,extra=report(q,'submission-positive',False);out['positive'].append({{'observerInstalledBeforeCandidate':True,'trigger':'user-action','candidateTransaction':x,'additionalWriteTransactions':extra,'snapshots':{{'before':before,'afterCommit':after,'settled':settled}},'viewport':list(v),'focusEvidence':focus(q)}});c.close()
  assert not j,'NETWORK_EGRESS_BLOCKED_POSITIVE:'+json.dumps(j)
  j=[]
  with tempfile.TemporaryDirectory() as d:
   c,q=open_c(p,d,j,v);act(q,driver['startSelector']);before=snap(q);all0=snap(q,True);starts=[x for x in before['learningEvents'] if x.get('kind')=='session-started'];assert len(starts)==1;q.evaluate("window.__ATLAS_QA_OBSERVER__.setPhase('lifecycle-interrupt')");act(q,driver['interruptSelector']);i=snap(q);ai=snap(q,True);c.close();c,q=open_c(p,d,j,v);r1=snap(q);ar1=snap(q,True);q.evaluate("window.__ATLAS_QA_OBSERVER__.setPhase('lifecycle-resume')");act(q,driver['resumeSelector']);r=snap(q);ar=snap(q,True);fe=focus(q);c.close();c,q=open_c(p,d,j,v);r2=snap(q);ar2=snap(q,True);out['lifecycle'].append({{'observerInstalledBeforeCandidate':True,'triggerInterruption':'product-interruption-action','triggerResume':'product-resume-action','startedEvent':starts[0],'beforeInterruption':before,'afterInterruption':i,'afterFirstReopen':r1,'afterResume':r,'afterSecondReopen':r2,'allBefore':all0,'allAfterInterruption':ai,'allAfterFirstReopen':ar1,'allAfterResume':ar,'allAfterSecondReopen':ar2,'viewport':list(v),'focusEvidence':fe}});c.close()
  assert not j,'NETWORK_EGRESS_BLOCKED_LIFECYCLE:'+json.dumps(j)
 print(json.dumps(out,ensure_ascii=False))
''')

def git(root:pathlib.Path,*a:str)->str:
 p=subprocess.run(["git","-C",str(root),*a],capture_output=True,text=True)
 if p.returncode: raise AssertionError("GIT_FAILURE:"+" ".join(a)+":"+p.stderr.strip())
 return p.stdout.strip()
def heads(values:list[str])->dict[str,str]:
 out={}
 for v in values:
  if "=" not in v: raise AssertionError("ACCEPTED_HEAD_FORMAT_INVALID")
  k,x=v.split("=",1)
  if k not in LANES or k in out or not SHA40.fullmatch(x): raise AssertionError("ACCEPTED_HEAD_INVALID")
  out[k]=x
 if set(out)!=set(LANES): raise AssertionError("EXACT_FOUR_ACCEPTED_HEADS_REQUIRED")
 return out
def bind(repo:pathlib.Path,candidate:str,accepted:dict[str,str])->list[pathlib.Path]:
 if git(repo,"cat-file","-t",candidate)!="commit": raise AssertionError("CANDIDATE_COMMIT_MISSING")
 for lane,h in accepted.items():
  if git(repo,"cat-file","-t",h)!="commit": raise AssertionError("ACCEPTED_HEAD_MISSING:"+lane)
  for p in LANES[lane]:
   if git(repo,"rev-parse",f"{h}:{p}")!=git(repo,"rev-parse",f"{candidate}:{p}"): raise AssertionError("ACCEPTED_HEAD_BLOB_MISMATCH:"+p)
 return []
def bind_source(root:pathlib.Path,candidate:str)->list[pathlib.Path]:
 if git(root,"rev-parse","HEAD")!=candidate or git(root,"status","--porcelain=v1","--untracked-files=all"): raise AssertionError("SOURCE_CHECKOUT_NOT_EXACT_CLEAN")
 out=[]
 for p in (x for lane in LANES.values() for x in lane):
  f=root/p
  if not f.is_file() or f.is_symlink(): raise AssertionError("EXPECTED_SOURCE_FILE_MISSING:"+p)
  if git(root,"rev-parse",f"{candidate}:{p}")!=git(root,"hash-object","--",p): raise AssertionError("SOURCE_BLOB_MISMATCH:"+p)
  out.append(f)
 return out
def provenance(path:pathlib.Path,candidate:str,accepted:dict[str,str],artifact_sha:str)->None:
 v=json.loads(path.read_text());closed(v,("schemaVersion","candidateHead","artifactSha256","acceptedHeads","buildCommands","cleanCheckout","networkBlocked"))
 if v!={**v,"schemaVersion":"atlas.artifact-provenance.v1"} or v["candidateHead"]!=candidate or v["artifactSha256"]!=artifact_sha or v["acceptedHeads"]!=accepted or v["cleanCheckout"] is not True or v["networkBlocked"] is not True or not v["buildCommands"]: raise AssertionError("ARTIFACT_PROVENANCE_MISMATCH")

def visible(v:Any)->str:
 if not isinstance(v,str):raise AssertionError("INVALID_VISIBLE_STRING")
 return re.sub(r"\s+"," ",unicodedata.normalize("NFC",v).strip())
def stimulus(a:dict[str,Any])->str:
 base={"type":a.get("type"),"prompt":visible(a.get("prompt"))}
 if a.get("type")=="qcm":
  choices=a.get("choices");by={}
  if not isinstance(choices,list) or not choices:raise AssertionError("QCM_CHOICES_REQUIRED")
  for x in choices:
   closed(x,("choiceId","label"));cid=x["choiceId"]
   if not isinstance(cid,str) or not cid or cid in by:raise AssertionError("QCM_CHOICE_COLLISION")
   by[cid]=visible(x["label"])
  if a.get("correctChoiceId") not in by:raise AssertionError("QCM_OPERATION_INVALID")
  labels=sorted(by.values())
  if len(labels)!=len(set(labels)):raise AssertionError("QCM_VISIBLE_CHOICE_COLLISION")
  base.update(choices=labels,answerOperation={"kind":"select-one","correctValue":by[a["correctChoiceId"]]})
 elif a.get("type")=="fill":
  tokens=a.get("tokens");tok={}
  if not isinstance(tokens,list) or not tokens:raise AssertionError("FILL_TOKENS_REQUIRED")
  for x in tokens:
   closed(x,("tokenId","label","maxUses"));tid=x["tokenId"];mx=x["maxUses"]
   if not isinstance(tid,str) or not tid or tid in tok or not isinstance(mx,int) or isinstance(mx,bool) or mx<1:raise AssertionError("FILL_TOKEN_INVALID")
   tok[tid]={"label":visible(x["label"]),"maxUses":mx}
  slots=[];segments=[]
  for x in a.get("segments",[]):
   if set(x)=={"text"}:segments.append({"text":visible(x["text"])})
   elif set(x)=={"slotId"} and isinstance(x["slotId"],str) and x["slotId"] and x["slotId"] not in slots:slots.append(x["slotId"]);segments.append({"blank":len(slots)-1})
   else:raise AssertionError("FILL_SEGMENT_INVALID")
  answers={}
  for x in a.get("answers",[]):
   closed(x,("slotId","tokenId"))
   if x["slotId"] in answers:raise AssertionError("FILL_ANSWER_MAPPING_INVALID")
   answers[x["slotId"]]=x["tokenId"]
  if set(answers)!=set(slots):raise AssertionError("FILL_ANSWER_MAPPING_INVALID")
  used={k:0 for k in tok};correct=[]
  for slot in slots:
   tid=answers[slot]
   if tid not in tok:raise AssertionError("FILL_ANSWER_TOKEN_UNKNOWN")
   used[tid]+=1
   if used[tid]>tok[tid]["maxUses"]:raise AssertionError("FILL_MAX_USES_EXCEEDED")
   correct.append(tok[tid]["label"])
  base.update(segments=segments,tokens=sorted(tok.values(),key=cj),answerOperation={"kind":"fill-blanks","correctValues":correct})
 else:raise AssertionError("ATLAS_ACTIVITY_TYPE_UNSUPPORTED")
 return "sha256:"+dh("learnit.atlas.m1.v0.3/stimulus-digest/atlas.stimulus.v1",base)
def qref(pkg:str,course:str,objective:str|None=None,activity:str|None=None)->dict[str,Any]:
 if (objective is None)==(activity is None):raise AssertionError("UNQUALIFIED_REFERENCE")
 out={"courseRef":{"packageLineageId":pkg,"courseLineageId":course}};out["objectiveId" if objective is not None else "activityLineageId"]=objective if objective is not None else activity;return out
def qualify_claim(package:dict[str,Any],course:dict[str,Any],raw:dict[str,Any])->str:
 closed(raw,("claimVersion","claimId","objectiveId","sourceActivityLineageId","targetActivityLineageId","basisCode","sourceStimulusDigest","targetStimulusDigest"))
 if raw["claimVersion"]!="atlas.independence.v1" or raw["basisCode"] not in {"new-instance","new-context","alternate-representation"}:raise AssertionError("CLAIM_SHAPE_INVALID")
 by={a["activityLineageId"]:a for a in course.get("activities",[])}
 if len(by)!=len(course.get("activities",[])):raise AssertionError("DUPLICATE_ACTIVITY_REF")
 try:src,dst=by[raw["sourceActivityLineageId"]],by[raw["targetActivityLineageId"]]
 except KeyError as e:raise AssertionError("CLAIM_ACTIVITY_UNKNOWN") from e
 oid=raw["objectiveId"]
 if src.get("objectiveIds")!=[oid] or dst.get("objectiveIds")!=[oid] or src is dst:raise AssertionError("CLAIM_RELATION_INVALID")
 sd,td=stimulus(src),stimulus(dst)
 if sd==td or raw["sourceStimulusDigest"]!=sd or raw["targetStimulusDigest"]!=td:raise AssertionError("CLAIM_STIMULUS_INVALID")
 pkg=package["packageLineageId"];cid=course["courseLineageId"];payload={"claimVersion":"atlas.independence.v1","objectiveRef":qref(pkg,cid,objective=oid),"sourceActivityRef":qref(pkg,cid,activity=raw["sourceActivityLineageId"]),"targetActivityRef":qref(pkg,cid,activity=raw["targetActivityLineageId"]),"basisCode":raw["basisCode"],"sourceStimulusDigest":sd,"targetStimulusDigest":td};expected="atlas-claim-sha256:"+dh(CLAIM_DOMAIN,payload)
 if raw["claimId"]!=expected:raise AssertionError("CLAIM_ID_INVALID")
 return expected
def claim_ids(source:pathlib.Path,revision:dict[str,Any])->set[str]:
 found=[]
 for rel in PACKAGES:
  p=json.loads((source/rel).read_text())
  r={"packageLineageId":p.get("packageLineageId"),"packageRevisionId":p.get("packageRevisionId"),"packageDigest":p.get("packageRevisionDigest")}
  if r==revision:found.append(p)
 if len(found)!=1:raise AssertionError("CONTENT_REVISION_PACKAGE_MATCH_COUNT")
 ids=set();package=found[0]
 for course in package.get("courses",[]):
  for raw in course.get("atlasValidationIndependenceClaims",[]):
   cid=qualify_claim(package,course,raw)
   if cid in ids:raise AssertionError("DUPLICATE_CLAIM_ID")
   ids.add(cid)
 if not ids:raise AssertionError("CANDIDATE_CLAIMS_REQUIRED")
 return ids
def accepted_claims(path:pathlib.Path,artifact_sha:str,revision:dict[str,Any],oracle:str,candidate:set[str])->frozenset[str]:
 v=json.loads(path.read_text());closed(v,("schemaVersion","contentRevisionRef","oracleVersion","artifactDigest","acceptedClaimIds"))
 ids=v["acceptedClaimIds"]
 if v["schemaVersion"]!="atlas.accepted-validation-claims.v1" or v["contentRevisionRef"]!=revision or v["oracleVersion"]!=oracle or v["artifactDigest"]!="sha256:"+artifact_sha or not isinstance(ids,list) or not ids or ids!=sorted(set(ids)) or any(x not in candidate for x in ids): raise AssertionError("ACCEPTED_CLAIM_SET_BINDING")
 return frozenset(ids)
def network(paths:list[pathlib.Path])->list:
 tokens=("fetch(","XMLHttpRequest","WebSocket","openai","anthropic","http://","https://")
 return [(str(p),t) for p in paths for t in tokens if t in p.read_text()]

def sample_rows():
 course={"packageLineageId":"pkg","courseLineageId":"course"};rev={"packageLineageId":"pkg","packageRevisionId":"rev","packageDigest":"sha256:"+"1"*64};session={"sessionId":"atlas-session-sha256:"+"2"*64,"planId":"atlas-plan-sha256:"+"3"*64};obj={"courseRef":course,"objectiveId":"objective"};act={"courseRef":course,"activityLineageId":"activity"}
 exe={"executionVersion":"atlas.scored-execution.v1","executionId":"atlas-execution-sha256:"+"4"*64,"sessionRef":session,"courseRef":course,"contentRevisionRef":rev,"planDigest":"sha256:"+"5"*64,"itemPosition":0,"submissionOrdinal":1,"objectiveRef":obj,"activityRef":act,"action":"start-practice","executionClass":"practice","outcome":"correct","assistance":"none","assistanceUseIds":[],"submittedAt":"2026-01-01T00:00:00.000Z","scoredAt":"2026-01-01T00:00:00.001Z"}
 ep={"eventVersion":"atlas.learning-event.v1","kind":"activity-attempt","executionId":exe["executionId"]};ev={**ep,"eventId":event_id(ep),"objectiveRef":obj,"occurredAt":"2026-01-01T00:00:00.001Z"};resume={"resumeVersion":"atlas.resume-state.v1","sessionRef":session,"courseRef":course,"contentRevisionRef":rev,"planDigest":exe["planDigest"],"nextItemPosition":1,"lastCommittedEventId":ev["eventId"],"focusTarget":"atlas-session-summary","lifecycleOrdinal":0,"itemStates":[]};sp={"eventVersion":"atlas.learning-event.v1","kind":"session-started","sessionRef":session,"planDigest":exe["planDigest"],"eventOrdinal":0};start={**sp,"eventId":event_id(sp),"courseRef":course,"contentRevisionRef":rev,"selectedItems":[{"position":0,"objectiveRef":obj,"activityRef":act,"action":"start-practice","executionClass":"practice","estimatedMinutes":5}],"occurredAt":"2026-01-01T00:00:00.000Z"};return exe,ev,resume,start
def empty():return {k:[] for k in STORES}
def good_fault():
 s=empty();return {"observerInstalledBeforeCandidate":True,"trigger":"user-action","candidateTransaction":{"origin":"candidate","mode":"readwrite","storeNames":list(STORES),"writes":[{"store":"scoredExecutions","method":"put","ordinal":1}],"abortObserved":True,"commitObserved":False,"faultArmed":True,"faultTriggered":True,"faultWriteOrdinal":1,"faultStage":"after-write-before-complete"},"additionalWriteTransactions":[],"snapshots":{k:copy.deepcopy(s) for k in ("before","immediate","afterDatabaseClose","afterContextReopen","settled")}}
def good_positive():
 e,v,r,start=sample_rows();a={"learningEvents":[start,v],"resumeStates":[r],"scoredExecutions":[e]};return {"observerInstalledBeforeCandidate":True,"trigger":"user-action","candidateTransaction":{"origin":"candidate","mode":"readwrite","storeNames":list(STORES),"writes":[{"store":"scoredExecutions","method":"put","ordinal":1},{"store":"learningEvents","method":"put","ordinal":2},{"store":"resumeStates","method":"put","ordinal":3}],"abortObserved":False,"commitObserved":True,"faultArmed":False,"faultTriggered":False,"faultWriteOrdinal":0,"faultStage":None},"additionalWriteTransactions":[],"snapshots":{"before":{"learningEvents":[start],"resumeStates":[],"scoredExecutions":[]},"afterCommit":a,"settled":copy.deepcopy(a)}}
def good_life():
 _,_,r,start=sample_rows();r={**r,"nextItemPosition":0,"lastCommittedEventId":None,"lifecycleOrdinal":0};r.pop("lastCommittedEventId")
 ip={"eventVersion":"atlas.learning-event.v1","kind":"session-interrupted","sessionRef":start["sessionRef"],"eventOrdinal":1,"occurredAt":"2026-01-01T00:00:01.000Z"};i={**ip,"eventId":event_id(ip)};rp={"eventVersion":"atlas.learning-event.v1","kind":"session-resumed","sessionRef":start["sessionRef"],"eventOrdinal":2,"occurredAt":"2026-01-01T00:00:02.000Z"};re={**rp,"eventId":event_id(rp)};b={"learningEvents":[start],"resumeStates":[r],"scoredExecutions":[]};a={"learningEvents":[start,i],"resumeStates":[{**r,"lifecycleOrdinal":1}],"scoredExecutions":[]};z={"learningEvents":[start,i,re],"resumeStates":[{**r,"lifecycleOrdinal":2}],"scoredExecutions":[]};return {"observerInstalledBeforeCandidate":True,"triggerInterruption":"product-interruption-action","triggerResume":"product-resume-action","startedEvent":start,"beforeInterruption":b,"afterInterruption":a,"afterFirstReopen":copy.deepcopy(a),"afterResume":z,"afterSecondReopen":copy.deepcopy(z)}

class Tests(unittest.TestCase):
 def test_atomic_positive_and_fault(self): self.assertTrue(fault_trace(good_fault()));self.assertEqual(positive_trace(good_positive())["execution"]["executionClass"],"practice")
 def test_atomic_negative_matrix(self):
  cases=[]
  for stores in (["learningEvents","scoredExecutions"],[*STORES,"atlasMeta"],["learningEvents","resumeState","scoredExecutions"]):
   x=good_fault();x["candidateTransaction"]["storeNames"]=stores;cases.append((x,"EXACT_THREE"))
  x=good_fault();x["additionalWriteTransactions"]=[{"storeNames":["resumeStates"]}];cases.append((x,"ADDITIONAL"));x=good_fault();x["candidateTransaction"]["origin"]="oracle";cases.append((x,"ORACLE_TRANSACTION"));x=good_fault();x["observerInstalledBeforeCandidate"]=False;cases.append((x,"HOOKS_MISSING"));x=good_fault();x["candidateTransaction"]["faultWriteOrdinal"]=0;cases.append((x,"BEFORE_ANY_WRITE"));x=good_fault();x["candidateTransaction"]["faultStage"]="after-commit";cases.append((x,"TOO_EARLY_OR_TOO_LATE"));x=good_fault();x["snapshots"]["settled"]["learningEvents"]=[{"eventId":"orphan"}];cases.append((x,"PARTIAL_OR_COMPENSATING"));x=good_fault();del x["snapshots"]["settled"]["resumeStates"];cases.append((x,"SNAPSHOT_EXACT_STORES"))
  for trace,msg in cases:
   with self.subTest(msg=msg),self.assertRaisesRegex(AssertionError,msg):fault_trace(trace)
  x=good_fault();x["candidateAtomic"]=True
  with self.assertRaisesRegex(AssertionError,"OBJECT_NOT_CLOSED"):fault_trace(x)
 def test_lifecycle_positive_and_negative_matrix(self):
  self.assertTrue(lifecycle_trace(good_life()))
  cases=[]
  x=good_life();x["afterResume"]["learningEvents"]=[x["startedEvent"],x["afterResume"]["learningEvents"][-1]];x["afterSecondReopen"]=copy.deepcopy(x["afterResume"]);cases.append((x,"RESUMED_EVENT_REQUIRED"))
  for o in (0,1,3):
   x=good_life();e=x["afterResume"]["learningEvents"][-1];e["eventOrdinal"]=o;e["eventId"]=event_id(without(e,"eventId"));x["afterSecondReopen"]=copy.deepcopy(x["afterResume"]);cases.append((x,"ORDINAL"))
  x=good_life();x["afterFirstReopen"]=x["beforeInterruption"];cases.append((x,"NOT_PERSISTED"));x=good_life();x["afterSecondReopen"]=x["afterInterruption"];cases.append((x,"NOT_PERSISTED"));x=good_life();x["afterResume"]["resumeStates"]=[];cases.append((x,"RESUME_STATE"));x=good_life();x["afterResume"]["resumeStates"][0]["lifecycleOrdinal"]=1;x["afterSecondReopen"]=copy.deepcopy(x["afterResume"]);cases.append((x,"RESUME_ORDINAL"));x=good_life();e,_,_,_=sample_rows();x["afterResume"]["scoredExecutions"].append(e);x["afterSecondReopen"]=copy.deepcopy(x["afterResume"]);cases.append((x,"PEDAGOGICAL_EVIDENCE"));x=good_life();x["lifecyclePass"]=True;cases.append((x,"OBJECT_NOT_CLOSED"))
  for trace,msg in cases:
   with self.subTest(msg=msg),self.assertRaisesRegex(AssertionError,msg):lifecycle_trace(trace)
 def test_lifecycle_identity_time_completion(self):
  x=good_life();ev=x["afterResume"]["learningEvents"][-1];r=x["afterResume"]["resumeStates"][0]
  with self.assertRaisesRegex(AssertionError,"AFTER_COMPLETION"):life_event(ev,"session-resumed",x["startedEvent"],r,1,"2026-01-01T00:00:01.000Z",True)
  for ts in ("2026-01-01T00:00:02Z","2026-01-01 00:00:02.000Z","2026-01-01T00:00:02.000+00:00","not-a-date","2025-12-31T23:59:59.999Z"):
   y=copy.deepcopy(ev);y["occurredAt"]=ts;y["eventId"]=event_id(without(y,"eventId"))
   with self.assertRaises(AssertionError):life_event(y,"session-resumed",x["startedEvent"],r,1,"2026-01-01T00:00:01.000Z")
 def test_v3_regressions(self):
  b={"occurredAt":"2026-01-01T00:00:00.000Z"}
  self.assertFalse(maintenance_due(b,{"occurredAt":"2026-01-01T23:59:59.999Z"}));self.assertTrue(maintenance_due(b,{"occurredAt":"2026-01-02T00:00:00.000Z"}));self.assertTrue(maintenance_due(b,{"occurredAt":"2026-01-02T00:00:00.001Z"}))
  for bad in ("2025-12-31T23:59:59.999Z","2026-01-01T23:00:00.000Z","2026-01-02T00:00:00.000+00:00","2026-01-02 00:00:00.000Z","2026-02-30T00:00:00.000Z","2026-01-02T00:00:00Z","bad"):self.assertFalse(maintenance_due(b,{"occurredAt":bad}))
  expected=["0","1","2"];self.assertTrue(focus_trace(expected,expected,["2","1","0"],"0","2"))
  for args in ((["0","2","1"],["2","1","0"],"0","2"),(["0","1","1"],["2","1","0"],"0","2"),(["0","1"],["2","1","0"],"0","2"),(["0","1","2"],["2","0","1"],"0","2"),(["0","1","2"],["2","1","0"],"outside","2"),(["0","1","2"],["2","1","0"],"0","outside")):
   with self.assertRaisesRegex(AssertionError,"FOCUS_"):focus_trace(expected,*args)
 def test_browser_preload_network_and_no_attestation(self):
  d={"startSelector":"#s","submitSelector":"#x","interruptSelector":"#i","resumeSelector":"#r","responseSteps":[{"action":"click","selector":"#a"}],"waitAfterActionMs":1};s=browser_script(pathlib.Path("/tmp/a.html"),d);compile(s,"<browser>","exec")
  for token in ("add_init_script","armFault","after-write-before-complete","launch_persistent_context","NETWORK_EGRESS_BLOCKED_LIFECYCLE","focusEvidence"):self.assertIn(token,s)
  for token in ("objectStoreNames].slice(0,2)","candidateAtomic","lifecyclePass","qaScenario"):self.assertNotIn(token,s)
 def test_fixture_and_closed_config(self):
  rows,ok=fixture_report();self.assertTrue(ok,rows);self.assertIn("VALIDATION_AVAILABLE",REASONS);self.assertNotIn("FREE_TEXT",REASONS)
  d={"startSelector":"#s","submitSelector":"#x","interruptSelector":"#i","resumeSelector":"#r","responseSteps":[{"action":"click","selector":"#a"}],"waitAfterActionMs":1};self.assertEqual(validate_driver(d),d);d["candidateAtomic"]=True
  with self.assertRaisesRegex(AssertionError,"OBJECT_NOT_CLOSED"):validate_driver(d)

def run_tests():return unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
def preflight()->int:
 r=run_tests();rows,ok=fixture_report();verdict="PRE_CANDIDATE_QA_READY" if r.wasSuccessful() and ok else "CHANGES_REQUIRED";print(json.dumps({"verdict":verdict,"productVerdictAvailable":False,"oracleTests":r.testsRun,"fixtures":rows,"contractFixturesModified":not ok,"strictCandidateScenariosExecuted":False},indent=2,ensure_ascii=False));return 0 if verdict=="PRE_CANDIDATE_QA_READY" else 1
def strict_missing(a):
 fields=("candidate_head","artifact","artifact_sha256","claim_set","content_revision","oracle_version","artifact_provenance","repo_root","source_root","driver_config");out=[x.replace("_","-") for x in fields if not getattr(a,x)]
 if len(a.accepted_head)!=4:out.append("accepted-head=learning/core/experience/content")
 return out
def strict(a)->int:
 missing=strict_missing(a)
 if missing:print(json.dumps({"verdict":"STRICT_CANDIDATE_NOT_EXECUTABLE","productVerdictAvailable":False,"missingDependencies":missing},indent=2));return 2
 if not SHA40.fullmatch(a.candidate_head) or not HEX64.fullmatch(a.artifact_sha256):raise AssertionError("INVALID_CANDIDATE_OR_ARTIFACT_DIGEST")
 accepted_heads=heads(a.accepted_head);repo=pathlib.Path(a.repo_root).resolve();source=pathlib.Path(a.source_root).resolve();bind(repo,a.candidate_head,accepted_heads);paths=bind_source(source,a.candidate_head);artifact=pathlib.Path(a.artifact).resolve();actual=sha(artifact)
 if actual!=a.artifact_sha256:raise AssertionError("ARTIFACT_SHA256_MISMATCH")
 provenance(pathlib.Path(a.artifact_provenance),a.candidate_head,accepted_heads,actual);revision=json.loads(pathlib.Path(a.content_revision).read_text());candidate=claim_ids(source,revision);accepted=accepted_claims(pathlib.Path(a.claim_set),actual,revision,a.oracle_version,candidate)
 findings=network(paths)
 if findings:raise AssertionError("STATIC_NETWORK_GATE_FAILED:"+json.dumps(findings))
 rows,ok=fixture_report()
 if not ok:raise AssertionError("CONTRACT_FIXTURES_MODIFIED")
 driver=validate_driver(json.loads(pathlib.Path(a.driver_config).read_text()));r=run_tests()
 if not r.wasSuccessful():raise AssertionError("ORACLE_SELF_TEST_FAILED")
 script=browser_script(artifact,driver)
 if any(x in script for x in ("candidateAtomic","lifecyclePass","qaScenario")):raise AssertionError("CANDIDATE_SELF_ATTESTATION_FORBIDDEN")
 p=subprocess.run([sys.executable,"-c",script],capture_output=True,text=True)
 if p.returncode:raise AssertionError("BROWSER_GATE_FAILED:"+p.stderr.strip())
 browser=json.loads(p.stdout);fault=[fault_trace(x) for x in browser.get("fault",[])];positive=[positive_trace(x,accepted,revision) for x in browser.get("positive",[])];life=[lifecycle_trace(x) for x in browser.get("lifecycle",[])]
 if (len(fault),len(positive),len(life))!=(2,2,2):raise AssertionError("FROZEN_VIEWPORT_MATRIX_INCOMPLETE")
 print(json.dumps({"verdict":"PASS_TO_HUMAN_GATE","candidateHead":a.candidate_head,"artifactSha256":actual,"acceptedHeads":accepted_heads,"acceptedClaimIds":sorted(accepted),"contractFixturesModified":False,"fixtureHashes":rows,"browserObservation":"INDEPENDENT_PRELOAD_INSTRUMENTATION","atomicity":"REAL_CANDIDATE_ALL_THREE_OR_ZERO_AND_POSITIVE_COMMIT","lifecycle":"INTERRUPT_REOPEN_RESUME_REOPEN_PERSISTED","viewports":[[1440,900],[390,844]]},indent=2));return 0
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--strict",action="store_true");p.add_argument("--candidate-head");p.add_argument("--artifact");p.add_argument("--artifact-sha256");p.add_argument("--accepted-head",action="append",default=[]);p.add_argument("--claim-set");p.add_argument("--content-revision");p.add_argument("--oracle-version");p.add_argument("--artifact-provenance");p.add_argument("--repo-root");p.add_argument("--source-root");p.add_argument("--driver-config");a=p.parse_args()
 try:return strict(a) if a.strict else preflight()
 except (AssertionError,OSError,ValueError,json.JSONDecodeError) as e:print(json.dumps({"verdict":"CHANGES_REQUIRED" if a.strict else "ORACLE_SELF_TEST_FAILED","productVerdictAvailable":False,"error":str(e)},indent=2));return 1
if __name__=="__main__":raise SystemExit(main())
