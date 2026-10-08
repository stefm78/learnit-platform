#!/usr/bin/env python3
"""Fail-closed PASSAGE V6 Factory gate."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any
from authoring.v6 import validator_runtime

FACTORY_EVIDENCE_SCHEMA="learnit.atlas.ai_kit_factory_v6_evidence.r2"
FACTORY_PROFILE="atlas.ai-kit-factory.v6-r2"
FACTORY_PASS="PASS_AI_KIT_FACTORY_V6_R2"; FACTORY_HOLD="HOLD_AI_KIT_FACTORY_V6_R2"
SEMANTIC_REVIEW_SCHEMA="learnit.atlas.semantic_review.v3"; SEMANTIC_REVIEW_PROFILE="atlas.semantic-review.v6-r1"
SEMANTIC_PASS="PASS_SEMANTIC_REVIEW_V6_R1"; SEMANTIC_HOLD="HOLD_SEMANTIC_REVIEW_V6_R1"
SOURCE_MANIFEST_SCHEMA="learnit.atlas.v6_source_manifest.v1"
SOURCE_GOVERNANCE_PASS="PASS_V6_SOURCE_GOVERNANCE_R1"; SOURCE_GOVERNANCE_HOLD="HOLD_V6_SOURCE_GOVERNANCE_R1"
POLICY_ID="v6-no-constructed-r1"; CONSTRUCTED_REASON="ACTIVITY_TYPE_DISABLED:constructed"
ADMITTED_FAMILIES=("lesson","flashcard","qcm","fill","matching","order","classify","productive")
CORE_DIMENSIONS=("sourceFidelity","answerCorrectness","ambiguity","objectiveCoverage","validationTransfer","learnerFit")
V6_CHECKS=("reviewerSkill","hintProgression","hintAnswerLeak","roleAReferenceUsefulness","roleBClaimMapping","productiveCorrectness","visualAdequacy")
FINDING_SEVERITIES=("blocking","major","minor","advice")
REPOSITORY="stefm78/learnit-platform"; SHA256=re.compile(r"^sha256:[0-9a-f]{64}$"); SHA40=re.compile(r"^[0-9a-f]{40}$")

class V6FactoryInputError(ValueError): pass

def canonical(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha256(b:bytes)->str:return "sha256:"+hashlib.sha256(b).hexdigest()
def digest(v:Any)->str:return sha256(canonical(v))
def exact(v:Any,k:set[str],label:str)->dict:
    if not isinstance(v,dict) or set(v)!=k: raise V6FactoryInputError(f"{label} fields mismatch")
    return v
def text(v:Any,label:str)->str:
    if not isinstance(v,str) or not v.strip(): raise V6FactoryInputError(f"{label} must be non-empty")
    return v
def nonnegative_int(v:Any,label:str)->int:
    if isinstance(v,bool) or not isinstance(v,int) or v<0: raise V6FactoryInputError(f"{label} must be >=0")
    return v
def load_json(p:Path,label:str)->tuple[Any,bytes]:
    try:r=p.read_bytes();return json.loads(r.decode()),r
    except Exception as e: raise V6FactoryInputError(f"{label}: {e}") from e

def validate_brief(v:Any)->dict:
    if not isinstance(v,dict) or v.get("schema")!="learnit.atlas.learner_brief.v1": raise V6FactoryInputError("invalid learner brief")
    for k in ("audience","goal","language"):text(v.get(k),"brief."+k)
    if isinstance(v.get("timeBudgetMinutes"),bool) or not isinstance(v.get("timeBudgetMinutes"),int) or v["timeBudgetMinutes"]<=0: raise V6FactoryInputError("invalid timeBudgetMinutes")
    return v

def parse_source_paths(specs:list[str])->dict[str,bytes]:
    out={}
    for spec in specs:
        if "=" not in spec: raise V6FactoryInputError("invalid source specification")
        sid,path=spec.split("=",1)
        if not re.fullmatch(r"[A-Za-z0-9._-]+",sid) or sid in out: raise V6FactoryInputError("invalid/duplicate sourceId")
        try: out[sid]=Path(path).read_bytes()
        except OSError as e: raise V6FactoryInputError(f"source {sid}: {e}") from e
    if not out: raise V6FactoryInputError("Role B sources required")
    return out

def validate_source_manifest(v:Any,raw:bytes,sources:dict[str,bytes])->dict:
    m=exact(v,{"schema","roleB","roleA","visualRequirement"},"source manifest")
    if m["schema"]!=SOURCE_MANIFEST_SCHEMA or not isinstance(m["roleB"],list) or not isinstance(m["roleA"],list): raise V6FactoryInputError("invalid source manifest")
    vr=exact(m["visualRequirement"],{"required","basis"},"visualRequirement")
    if not isinstance(vr["required"],bool):raise V6FactoryInputError("visualRequirement.required must be boolean")
    text(vr["basis"],"visualRequirement.basis")
    rb=[];seen=set()
    for x in m["roleB"]:
        x=exact(x,{"sourceId","bytes","sha256","authorized","provenance","kind","admittedAtAuthoring","claimIds"},"Role B")
        sid=text(x["sourceId"],"sourceId"); data=sources.get(sid)
        if data is None or sid in seen or x["bytes"]!=len(data) or x["sha256"]!=sha256(data) or x["authorized"] is not True: raise V6FactoryInputError("Role B exact-byte/authorization mismatch")
        if x["kind"] not in {"provided","web-frozen"} or (x["kind"]=="web-frozen" and x["admittedAtAuthoring"] is not True): raise V6FactoryInputError("Role B admission mismatch")
        if not isinstance(x["claimIds"],list) or not x["claimIds"] or len(x["claimIds"])!=len(set(x["claimIds"])): raise V6FactoryInputError("Role B claimIds invalid")
        text(x["provenance"],"provenance");seen.add(sid);rb.append(dict(x))
    if seen!=set(sources): raise V6FactoryInputError("Role B source set mismatch")
    ra=[];urls=set()
    for x in m["roleA"]:
        x=exact(x,{"url","authorized","supplemental","usedAsSourceTruth"},"Role A");url=text(x["url"],"url")
        if not url.startswith("https://") or url in urls or x["authorized"] is not True or x["supplemental"] is not True or not isinstance(x["usedAsSourceTruth"],bool): raise V6FactoryInputError("Role A admission mismatch")
        urls.add(url);ra.append(dict(x))
    return {"manifestSha256":sha256(raw),"roleB":sorted(rb,key=lambda x:x["sourceId"]),"roleA":sorted(ra,key=lambda x:x["url"]),"visualRequirement":dict(vr)}

def build_context(kit_raw:bytes,brief_raw:bytes,source:dict)->dict:
    inv={"roleB":source["roleB"],"roleA":source["roleA"],"visualRequirement":source["visualRequirement"]}; sd=digest(inv)
    core={"profile":FACTORY_PROFILE,"kitSha256":sha256(kit_raw),"briefSha256":sha256(brief_raw),"sourceSetDigest":sd}
    return {"profile":FACTORY_PROFILE,**{k:core[k] for k in ("kitSha256","briefSha256","sourceSetDigest")},"sourceInventory":inv,"contextDigest":digest(core)}

def production_policy(kit:dict)->dict:
    counts={x:0 for x in (*ADMITTED_FAMILIES,"constructed")};paths=[];unknown=[]
    for ci,c in enumerate(kit.get("courses",[])):
        for ai,a in enumerate(c.get("activities",[]) if isinstance(c,dict) else []):
            t=a.get("type") if isinstance(a,dict) else None
            if t in counts:counts[t]+=1
            else:unknown.append(str(t))
            if t=="constructed":paths.append(f"$.courses[{ci}].activities[{ai}]")
    reasons=([CONSTRUCTED_REASON] if paths else [])+["ACTIVITY_TYPE_UNKNOWN:"+x for x in sorted(set(unknown))]
    return {"policyId":POLICY_ID,"admittedFamilies":list(ADMITTED_FAMILIES),"excludedFamilies":["constructed"],"counts":counts,"constructedPaths":paths,"verdict":"PASS_V6_PRODUCTION_POLICY_R1" if not reasons else "HOLD_V6_PRODUCTION_POLICY_R1","reasons":reasons}

def source_reasons(source:dict)->list[str]:
    return sorted({"ROLE_A_HIDDEN_SOURCE_TRUTH:"+x["url"] for x in source["roleA"] if x["usedAsSourceTruth"]})
def quality(kit:dict)->dict:
    declared=set();used=set();activities=0
    for c in kit.get("courses",[]):
        if not isinstance(c,dict):continue
        declared.update(o.get("objectiveId") for o in c.get("objectives",[]) if isinstance(o,dict))
        for a in c.get("activities",[]):
            if isinstance(a,dict):activities+=1;used.update(a.get("objectiveIds",[]))
    missing=sorted(x for x in declared-used if isinstance(x,str)); ok=bool(declared and activities and not missing)
    return {"verdict":"PASS_V6_PEDAGOGICAL_QUALITY_R1" if ok else "HOLD_V6_PEDAGOGICAL_QUALITY_R1","qualityBand":"STRONG" if ok else "HOLD","counts":{"objectives":len(declared),"activities":activities,"unreferencedObjectives":len(missing)}}

def has_media(kit:dict)->bool:
    return any(a.get("media") for c in kit.get("courses",[]) if isinstance(c,dict) for a in c.get("activities",[]) if isinstance(a,dict))
def validate_review(v:Any,raw:bytes,ctx:dict,productive:bool)->tuple[dict,list[str]]:
    r=exact(v,{"schema","profile","target","independence","dimensions","findings","limitations","v6Checks","verdict"},"review")
    if r["schema"]!=SEMANTIC_REVIEW_SCHEMA or r["profile"]!=SEMANTIC_REVIEW_PROFILE: raise V6FactoryInputError("review identity mismatch")
    reasons=[];target=exact(r["target"],{"contextDigest","kitSha256","sourceSetDigest","briefSha256"},"target")
    for k in target:
        if target[k]!=ctx[k]: reasons.append("REVIEW_TARGET_MISMATCH:"+k)
    ind=exact(r["independence"],{"authorScratchpadSeen","authorActiveContextReused"},"independence")
    if ind["authorScratchpadSeen"]:reasons.append("REVIEWER_SAW_AUTHOR_SCRATCHPAD")
    if ind["authorActiveContextReused"]:reasons.append("REVIEWER_REUSED_AUTHOR_ACTIVE_CONTEXT")
    rb={x["sourceId"]:set(x["claimIds"]) for x in ctx["sourceInventory"]["roleB"]}; dims=exact(r["dimensions"],set(CORE_DIMENSIONS),"dimensions")
    for name,d in dims.items():
        d=exact(d,{"status","summary","evidence"},name); text(d["summary"],name)
        if d["status"] not in {"pass","hold"}: raise V6FactoryInputError("dimension status invalid")
        if d["status"]=="hold":reasons.append("DIMENSION_HOLD:"+name)
        if not isinstance(d["evidence"],list) or (name in {"sourceFidelity","answerCorrectness","objectiveCoverage","validationTransfer"} and not d["evidence"]): raise V6FactoryInputError("dimension evidence missing")
        for ev in d["evidence"]:
            ev=exact(ev,{"sourceId","claimId","locator"},"evidence")
            if ev["sourceId"] not in rb or ev["claimId"] not in rb[ev["sourceId"]]: raise V6FactoryInputError("Role B claim mapping mismatch")
    counts={x:0 for x in FINDING_SEVERITIES}
    if not isinstance(r["findings"],list) or not isinstance(r["limitations"],list): raise V6FactoryInputError("review lists invalid")
    for f in r["findings"]:
        sev=f.get("severity") if isinstance(f,dict) else None
        if sev not in counts: raise V6FactoryInputError("finding severity invalid")
        counts[sev]+=1
        if sev in {"blocking","major"}:reasons.append(sev.upper()+"_FINDING:"+str(f.get("id")))
    checks=exact(r["v6Checks"],set(V6_CHECKS),"v6Checks")
    for n in V6_CHECKS:
        allowed={"pass","hold","not_applicable"} if n in {"productiveCorrectness","visualAdequacy"} else {"pass","hold"}
        if checks[n] not in allowed: raise V6FactoryInputError("check status invalid:"+n)
        if checks[n]=="hold":reasons.append("V6_CHECK_HOLD:"+n)
    if productive and checks["productiveCorrectness"]!="pass":reasons.append("PRODUCTIVE_CORRECTNESS_REQUIRED")
    expected=SEMANTIC_PASS if not reasons else SEMANTIC_HOLD
    if r["verdict"]!=expected:reasons.append("INCONSISTENT_REVIEW_VERDICT:expected="+expected)
    return {"sha256":sha256(raw),"schema":r["schema"],"profile":r["profile"],"target":dict(target),"verdict":r["verdict"],"counts":counts,"v6Checks":dict(checks)},sorted(set(reasons))

def run_gate(kit_path:Path,brief_path:Path,review_path:Path,source_manifest_path:Path,source_specs:list[str],git_commit:str)->dict:
    if not SHA40.fullmatch(git_commit):raise V6FactoryInputError("gitCommit invalid")
    ids=validator_runtime.assert_exact_identities();kit,kr=load_json(kit_path,"kit");brief,br=load_json(brief_path,"brief");sv,sr=load_json(source_manifest_path,"source manifest")
    if not isinstance(kit,dict) or kit.get("contract")!="learnit.kit.v6":raise V6FactoryInputError("kit must be learnit.kit.v6")
    validate_brief(brief);source=validate_source_manifest(sv,sr,parse_source_paths(source_specs));ctx=build_context(kr,br,source)
    report=validator_runtime.validate_document(kit,str(kit_path));policy=production_policy(kit);q=quality(kit);sreasons=source_reasons(source);rv,rr=load_json(review_path,"review")
    sem,semreasons=validate_review(rv,rr,ctx,policy["counts"]["productive"]>0); visual=source["visualRequirement"]
    if visual["required"] and not has_media(kit):semreasons.append("VISUAL_REQUIRED_MEDIA_ABSENT")
    if visual["required"] and sem["v6Checks"]["visualAdequacy"]!="pass":semreasons.append("VISUAL_ADEQUACY_PASS_REQUIRED")
    if not visual["required"] and sem["v6Checks"]["visualAdequacy"]=="pass" and not has_media(kit):semreasons.append("VISUAL_ADEQUACY_PASS_WITHOUT_MEDIA")
    reasons=([] if report.ok else ["CANONICAL_V6_INVALID"])+policy["reasons"]+([] if q["qualityBand"]=="STRONG" else ["PEDAGOGICAL_QUALITY_HOLD"])+sreasons+semreasons; reasons=sorted(set(reasons))
    impl={"repository":REPOSITORY,"gitCommit":git_commit,"schemaBlob":ids["schemaBlob"],"validatorBlob":ids["validatorBlob"],"factoryEvidenceProfile":FACTORY_PROFILE}
    return {"schema":FACTORY_EVIDENCE_SCHEMA,"profile":FACTORY_PROFILE,"context":ctx,"canonicalValid":report.ok,"canonicalErrors":list(report.errors),"pedagogicalQuality":q,"sourceGovernance":{"manifestSha256":source["manifestSha256"],"roleB":source["roleB"],"roleA":source["roleA"],"visualRequirement":visual,"verdict":SOURCE_GOVERNANCE_PASS if not sreasons else SOURCE_GOVERNANCE_HOLD,"reasons":sreasons},"productionPolicy":policy,"semanticReview":sem,"implementationAuthority":impl,"verdict":FACTORY_PASS if not reasons else FACTORY_HOLD,"reasons":reasons}

def verify_evidence(e:Any)->dict:
    e=exact(e,{"schema","profile","context","canonicalValid","canonicalErrors","pedagogicalQuality","sourceGovernance","productionPolicy","semanticReview","implementationAuthority","verdict","reasons"},"evidence")
    if e["schema"]!=FACTORY_EVIDENCE_SCHEMA or e["profile"]!=FACTORY_PROFILE:raise V6FactoryInputError("factory identity mismatch")
    c=e["context"]; core={"profile":FACTORY_PROFILE,"kitSha256":c["kitSha256"],"briefSha256":c["briefSha256"],"sourceSetDigest":c["sourceSetDigest"]}
    if c["sourceSetDigest"]!=digest(c["sourceInventory"]) or c["contextDigest"]!=digest(core):raise V6FactoryInputError("context digest mismatch")
    i=e["implementationAuthority"]
    if i!={"repository":REPOSITORY,"gitCommit":i.get("gitCommit"),"schemaBlob":validator_runtime.V6_SCHEMA_BLOB,"validatorBlob":validator_runtime.V6_VALIDATOR_BLOB,"factoryEvidenceProfile":FACTORY_PROFILE} or not SHA40.fullmatch(i["gitCommit"]):raise V6FactoryInputError("implementation authority mismatch")
    sg=e["sourceGovernance"]
    if sg["roleB"]!=c["sourceInventory"]["roleB"] or sg["roleA"]!=c["sourceInventory"]["roleA"] or sg["visualRequirement"]!=c["sourceInventory"]["visualRequirement"] or (sg["verdict"]==SOURCE_GOVERNANCE_PASS)!=(not sg["reasons"]):raise V6FactoryInputError("source binding mismatch")
    p=e["productionPolicy"]; sem=e["semanticReview"]
    if p["policyId"]!=POLICY_ID or p["admittedFamilies"]!=list(ADMITTED_FAMILIES) or p["excludedFamilies"]!=["constructed"]:raise V6FactoryInputError("policy identity mismatch")
    if sem["schema"]!=SEMANTIC_REVIEW_SCHEMA or sem["profile"]!=SEMANTIC_REVIEW_PROFILE or sem["target"]!={k:c[k] for k in ("contextDigest","kitSha256","sourceSetDigest","briefSha256")}:raise V6FactoryInputError("review binding mismatch")
    if set(sem["v6Checks"])!=set(V6_CHECKS):raise V6FactoryInputError("review checks mismatch")
    expected=(e["canonicalValid"] is True and p["verdict"]=="PASS_V6_PRODUCTION_POLICY_R1" and e["pedagogicalQuality"]["qualityBand"]=="STRONG" and sg["verdict"]==SOURCE_GOVERNANCE_PASS and sem["verdict"]==SEMANTIC_PASS and not e["reasons"])
    if e["verdict"]!=(FACTORY_PASS if expected else FACTORY_HOLD):raise V6FactoryInputError("factory verdict mismatch")
    return e
