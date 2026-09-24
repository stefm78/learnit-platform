#!/usr/bin/env python3
"""Explicit V5 admission adapter around the existing Atlas AI Kit Factory.

Identity primitives are intentionally not reimplemented here. Exact kit bytes,
brief digest, sorted source inventory, sourceSetDigest and contextDigest are all
created by the promoted ``factory_gate.build_context`` implementation. V5 adds
only fail-closed contract/policy/source-governance checks around that context.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from authoring.factory import factory_gate as factory
from authoring.factory import v5_web_admission as web
from authoring.v2.atlas import pedagogical_quality as legacy_quality
from authoring.v5 import validate_kit as v5
from authoring.v5 import authoring_policy

EVIDENCE_SCHEMA = "learnit.atlas.ai_kit_factory_v5_evidence.r1"
PROFILE = "atlas.ai-kit-factory.v5-r2"
REVIEW_SCHEMA = "learnit.atlas.semantic_review.v2"
REVIEW_PROFILE = "atlas.semantic-review.v5-r2"
REVIEWER_SKILL = "SKILL_ATLAS_KIT_REVIEW_V2"
SEMANTIC_PASS = "PASS_SEMANTIC_REVIEW_V5_R2"
SEMANTIC_HOLD = "HOLD_SEMANTIC_REVIEW_V5_R2"
ROLE_B_SCHEMA = "learnit.atlas.v5.role_b_source_manifest.v1"
ROLE_B_PROFILE = "atlas.v5.role-b-source-governance.r1"
ROLE_B_PASS = "PASS_V5_ROLE_B_SOURCE_GOVERNANCE_R1"
V5_CHECKS = ("hintProgression", "hintAnswerLeak", "roleAReferenceUsefulness", "roleBClaimMapping")
VERDICTS = {"PASS_AI_KIT_FACTORY_V5_R2":0,"HOLD_V5_FACTORY_CANONICAL_INVALID":2,"HOLD_V5_FACTORY_PEDAGOGICAL_WARNING":3,"HOLD_V5_FACTORY_INPUT":4,"HOLD_V5_FACTORY_REVIEW_BINDING":5,"HOLD_V5_FACTORY_SEMANTIC_REVIEW":6,"HOLD_V5_FACTORY_AUTHORING_POLICY":7,"HOLD_V5_FACTORY_ROLE_A_ADMISSION":8,"HOLD_V5_FACTORY_ROLE_B_SOURCE_GOVERNANCE":9}

class V5FactoryError(ValueError): pass

def _exact(value:Any,keys:set[str],label:str)->dict[str,Any]:
    if not isinstance(value,dict) or set(value)!=keys:
        actual=set(value) if isinstance(value,dict) else set(); raise V5FactoryError(f"{label} fields mismatch; missing={sorted(keys-actual)} extra={sorted(actual-keys)}")
    return value

def _load_json(path:Path,label:str)->Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeDecodeError,json.JSONDecodeError) as exc: raise V5FactoryError(f"{label}: {exc}") from exc

def _v5_quality(package:dict[str,Any])->dict[str,Any]:
    schema=v5.load(v5.SCHEMA_PATH); report=v5.validate(Path("<factory-v5>"),package,schema)
    if not report.ok: return {"canonicalValid":False,"verdict":"HOLD_CANONICAL_V5_INVALID","qualityBand":"BLOCKED","counts":{"blocking":len(report.errors),"warning":0,"advice":0},"diagnostics":list(report.errors)}
    diagnostics=legacy_quality._quality_diagnostics_v4(package); counts=legacy_quality._counts(diagnostics)
    return {"canonicalValid":True,"verdict":"PASS_ATLAS_PEDAGOGICAL_PROFILE_V5_R2","qualityBand":legacy_quality._band(counts["warning"],counts["advice"],counts["blocking"]),"counts":counts,"diagnostics":diagnostics}

def _parse_id_paths(specs:list[str],label:str)->dict[str,Path]:
    rows={}
    for spec in specs:
        if "=" not in spec: raise V5FactoryError(f"invalid {label} binding {spec!r}; expected ID=PATH")
        key,raw=spec.split("=",1)
        if not key or key in rows: raise V5FactoryError(f"invalid/duplicate {label} id {key!r}")
        rows[key]=Path(raw)
    return rows

def validate_role_a(package:dict[str,Any],admission_paths:list[Path])->dict[str,Any]:
    required=sorted(set(authoring_policy.reference_urls(package))); records={}
    for path in admission_paths:
        record=web.verify(_load_json(path,f"Role A admission {path}"))
        if record["purpose"]!="learner-reference": raise V5FactoryError(f"Role A evidence has wrong purpose: {path}")
        url=record["submittedUrl"]
        if url in records: raise V5FactoryError(f"duplicate Role A evidence for {url}")
        records[url]=record
    if sorted(records)!=required:
        missing=sorted(set(required)-set(records)); extra=sorted(set(records)-set(required)); raise V5FactoryError(f"Role A anti-orphan mismatch; missing={missing} extra={extra}")
    reasons=[f"ROLE_A_NOT_ADMITTED:{url}" for url,record in sorted(records.items()) if record["decision"]["verdict"]!=web.PASS]
    return {"requiredUrls":required,"admissionIds":[records[url]["admissionId"] for url in required],"verdict":"PASS_V5_ROLE_A_REFERENCE_ADMISSION_R1" if not reasons else "HOLD_V5_ROLE_A_REFERENCE_ADMISSION_R1","reasons":reasons}

def validate_role_b(manifest:Any,context:dict[str,Any],source_specs:list[str],web_admission_paths:list[Path])->dict[str,Any]:
    manifest=_exact(manifest,{"schema","profile","sources"},"Role B manifest")
    if manifest["schema"]!=ROLE_B_SCHEMA or manifest["profile"]!=ROLE_B_PROFILE: raise V5FactoryError("unsupported Role B manifest schema/profile")
    if not isinstance(manifest["sources"],list): raise V5FactoryError("Role B sources must be a list")
    source_paths=_parse_id_paths(source_specs,"source"); context_rows={row["sourceId"]:row for row in context["sources"]}
    if set(source_paths)!=set(context_rows): raise V5FactoryError("Factory source bindings do not match FactoryContext")
    web_records={}
    for path in web_admission_paths:
        record=web.verify(_load_json(path,f"Role B web admission {path}"))
        if record["purpose"]!="authoring-source" or record["decision"]["verdict"]!=web.PASS:
            raise V5FactoryError(f"Role B web evidence is not an admitted authoring-source: {path}")
        admission_id=record["admissionId"]
        if admission_id in web_records: raise V5FactoryError(f"duplicate Role B web admission {admission_id}")
        web_records[admission_id]=record
    records={}; used_web_ids=set()
    for index,raw in enumerate(manifest["sources"]):
        label=f"Role B sources[{index}]"; row=_exact(raw,{"sourceId","authorization","origin","capture","claimMappings"},label); source_id=row["sourceId"]
        if not isinstance(source_id,str) or not source_id or source_id in records: raise V5FactoryError(f"{label}.sourceId invalid/duplicate")
        auth=_exact(row["authorization"],{"allowed","basis","provenance"},label+".authorization")
        if auth["allowed"] is not True: raise V5FactoryError(f"{source_id}: Role B authorization is not explicit true")
        if not isinstance(auth["basis"],str) or not auth["basis"].strip() or not isinstance(auth["provenance"],str) or not auth["provenance"].strip(): raise V5FactoryError(f"{source_id}: authorization basis/provenance required")
        origin=_exact(row["origin"],{"kind","submittedUrl","finalUrl","checkedAt","contentType","webAdmissionId"},label+".origin")
        if origin["kind"] not in {"local-file","web"}: raise V5FactoryError(f"{source_id}: unsupported origin kind")
        if not isinstance(origin["checkedAt"],str) or not origin["checkedAt"].strip() or not isinstance(origin["contentType"],str) or not origin["contentType"].strip(): raise V5FactoryError(f"{source_id}: checkedAt/contentType required")
        web_record=None
        if origin["kind"]=="web":
            if not all(isinstance(origin[k],str) and origin[k].strip() for k in ("submittedUrl","finalUrl","webAdmissionId")): raise V5FactoryError(f"{source_id}: Web Role B origin requires submitted/final URL and webAdmissionId")
            web._normalized_url(origin["submittedUrl"]); web._normalized_url(origin["finalUrl"])
            web_record=web_records.get(origin["webAdmissionId"])
            if web_record is None: raise V5FactoryError(f"{source_id}: referenced Role B web admission is missing")
            used_web_ids.add(origin["webAdmissionId"])
            if web_record["submittedUrl"]!=origin["submittedUrl"] or web_record["finalUrl"]!=origin["finalUrl"]:
                raise V5FactoryError(f"{source_id}: Role B web admission URL binding mismatch")
        elif any(origin[k] is not None for k in ("submittedUrl","finalUrl","webAdmissionId")): raise V5FactoryError(f"{source_id}: local-file origin must not claim URL admission")
        capture=_exact(row["capture"],{"bytes","sha256"},label+".capture")
        if isinstance(capture["bytes"],bool) or not isinstance(capture["bytes"],int) or capture["bytes"]<0: raise V5FactoryError(f"{source_id}: invalid capture bytes")
        try: data=source_paths[source_id].read_bytes()
        except (KeyError,OSError) as exc: raise V5FactoryError(f"{source_id}: exact source bytes unavailable: {exc}") from exc
        actual={"bytes":len(data),"sha256":factory.sha256_bytes(data)}
        if capture!=actual: raise V5FactoryError(f"{source_id}: Role B capture mismatch")
        if web_record is not None and web_record["content"]!=actual:
            raise V5FactoryError(f"{source_id}: Role B web admission content does not match exact source bytes")
        if context_rows[source_id]["bytes"]!=actual["bytes"] or context_rows[source_id]["sha256"]!=actual["sha256"]: raise V5FactoryError(f"{source_id}: Role B capture not bound into sourceSetDigest inventory")
        mappings=row["claimMappings"]
        if not isinstance(mappings,list) or not mappings: raise V5FactoryError(f"{source_id}: at least one claim mapping is required")
        for mi,mapping in enumerate(mappings):
            mapping=_exact(mapping,{"kitPath","basis"},f"{label}.claimMappings[{mi}]")
            if not all(isinstance(mapping[k],str) and mapping[k].strip() for k in ("kitPath","basis")): raise V5FactoryError(f"{source_id}: claim mapping fields must be non-empty")
        records[source_id]=row
    if set(records)!=set(context_rows): raise V5FactoryError(f"Role B source-set mismatch; missing={sorted(set(context_rows)-set(records))} extra={sorted(set(records)-set(context_rows))}")
    if used_web_ids!=set(web_records): raise V5FactoryError(f"Role B web admission anti-orphan mismatch; unused={sorted(set(web_records)-used_web_ids)}")
    return {"verdict":ROLE_B_PASS,"sourceIds":sorted(records),"sourceSetDigest":context["sourceSetDigest"]}

def _validate_v5_review(review:Any,context:dict[str,Any])->tuple[dict[str,Any],list[str]]:
    review=_exact(review,{"schema","profile","target","independence","dimensions","findings","limitations","v5Checks","verdict"},"V5 semantic review")
    if review["schema"]!=REVIEW_SCHEMA or review["profile"]!=REVIEW_PROFILE: raise V5FactoryError("unsupported V5 semantic review schema/profile")
    checks=_exact(review["v5Checks"],{"reviewerSkill",*V5_CHECKS},"V5 semantic review checks")
    if checks["reviewerSkill"]!=REVIEWER_SKILL: raise V5FactoryError("V5 semantic review must declare SKILL_ATLAS_KIT_REVIEW_V2")
    for name in V5_CHECKS:
        if checks[name] not in {"pass","hold"}: raise V5FactoryError(f"v5Checks.{name} must be pass or hold")
    core=copy.deepcopy({k:review[k] for k in ("target","independence","dimensions","findings","limitations")}); core.update({"schema":factory.REVIEW_SCHEMA,"profile":factory.REVIEW_PROFILE,"verdict":factory.SEMANTIC_PASS if review["verdict"]==SEMANTIC_PASS else factory.SEMANTIC_HOLD})
    factory.validate_review(core,context); reasons=factory.semantic_reasons(core)+[f"V5_CHECK_HOLD:{name}" for name in V5_CHECKS if checks[name]!="pass"]
    expected=SEMANTIC_PASS if not reasons else SEMANTIC_HOLD
    if review["verdict"]!=expected: reasons.append(f"INCONSISTENT_V5_REVIEW_VERDICT:expected={expected}")
    return review,sorted(set(reasons))

def _binding_reasons(review:dict[str,Any],context:dict[str,Any])->list[str]:
    expected={key:context[key] for key in ("contextDigest","kitSha256","sourceSetDigest","briefSha256")}; return sorted(f"REVIEW_TARGET_MISMATCH:{key}" for key,value in expected.items() if review["target"].get(key)!=value)

def run_gate(kit_path:Path,brief_path:Path,review_path:Path,source_specs:list[str],role_a_admission_paths:list[Path],role_b_manifest_path:Path,role_b_web_admission_paths:list[Path])->dict[str,Any]:
    context=factory.build_context(kit_path,brief_path,source_specs); kit,_=factory.load_json(kit_path,"kit")
    if not isinstance(kit,dict) or kit.get("contract")!="learnit.kit.v5": raise V5FactoryError("V5 Factory admission requires exact discriminator learnit.kit.v5")
    quality=_v5_quality(kit); policy=authoring_policy.analyze(kit)
    try:
        role_a=validate_role_a(kit,role_a_admission_paths)
    except (V5FactoryError,web.WebAdmissionError) as exc:
        role_a={"requiredUrls":sorted(set(authoring_policy.reference_urls(kit))),"admissionIds":[],"verdict":"HOLD_V5_ROLE_A_REFERENCE_ADMISSION_R1","reasons":[str(exc)]}
    try:
        role_b=validate_role_b(_load_json(role_b_manifest_path,"Role B manifest"),context,source_specs,role_b_web_admission_paths)
    except (V5FactoryError,web.WebAdmissionError) as exc:
        role_b={"verdict":"HOLD_V5_ROLE_B_SOURCE_GOVERNANCE_R1","sourceIds":[],"sourceSetDigest":context["sourceSetDigest"],"reasons":[str(exc)]}
    review,semantic_reasons=_validate_v5_review(_load_json(review_path,"V5 semantic review"),context); bindings=_binding_reasons(review,context)
    if not quality["canonicalValid"]: verdict,reasons="HOLD_V5_FACTORY_CANONICAL_INVALID",["CANONICAL_V5_INVALID"]
    elif quality["qualityBand"] not in {"STRONG","EXCELLENT_BY_PROFILE"}: verdict,reasons="HOLD_V5_FACTORY_PEDAGOGICAL_WARNING",["PEDAGOGICAL_QUALITY_BAND:"+quality["qualityBand"]]
    elif policy["verdict"]!=authoring_policy.PASS: verdict,reasons="HOLD_V5_FACTORY_AUTHORING_POLICY",policy["reasons"]
    elif role_a["verdict"]!="PASS_V5_ROLE_A_REFERENCE_ADMISSION_R1": verdict,reasons="HOLD_V5_FACTORY_ROLE_A_ADMISSION",role_a["reasons"]
    elif role_b["verdict"]!=ROLE_B_PASS: verdict,reasons="HOLD_V5_FACTORY_ROLE_B_SOURCE_GOVERNANCE",role_b.get("reasons",[role_b["verdict"]])
    elif bindings: verdict,reasons="HOLD_V5_FACTORY_REVIEW_BINDING",bindings
    elif semantic_reasons: verdict,reasons="HOLD_V5_FACTORY_SEMANTIC_REVIEW",semantic_reasons
    else: verdict,reasons="PASS_AI_KIT_FACTORY_V5_R2",[]
    return {"schema":EVIDENCE_SCHEMA,"profile":PROFILE,"context":context,"canonicalValid":bool(quality["canonicalValid"]),"pedagogicalQuality":{"verdict":quality["verdict"],"qualityBand":quality["qualityBand"],"counts":quality["counts"]},"authoringPolicy":policy,"roleAReferences":role_a,"roleBSources":role_b,"semanticReview":{"verdict":review["verdict"]},"verdict":verdict,"reasons":reasons}

def parser()->argparse.ArgumentParser:
    p=argparse.ArgumentParser(description="Explicit V5 adapter around the existing Atlas Factory"); p.add_argument("--kit",type=Path,required=True); p.add_argument("--brief",type=Path,required=True); p.add_argument("--review",type=Path,required=True); p.add_argument("--source",action="append",default=[]); p.add_argument("--role-a-admission",action="append",default=[],type=Path); p.add_argument("--role-b-manifest",type=Path,required=True); p.add_argument("--role-b-web-admission",action="append",default=[],type=Path); return p

def main(argv:list[str]|None=None)->int:
    args=parser().parse_args(argv)
    try: evidence=run_gate(args.kit,args.brief,args.review,args.source,args.role_a_admission,args.role_b_manifest,args.role_b_web_admission)
    except (factory.FactoryInputError,V5FactoryError,web.WebAdmissionError,ValueError) as exc: evidence={"schema":EVIDENCE_SCHEMA,"profile":PROFILE,"verdict":"HOLD_V5_FACTORY_INPUT","reasons":[str(exc)]}
    print(factory.canonical_output(evidence),end=""); return VERDICTS.get(evidence["verdict"],4)

if __name__=="__main__": raise SystemExit(main())
