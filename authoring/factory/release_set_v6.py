#!/usr/bin/env python3
"""V6-only qualified release admission for PASSAGE."""
from __future__ import annotations
import argparse, io, json, stat, sys, zipfile
from pathlib import Path
from typing import Any
from authoring.factory import handoff, reliability_v6, v6_gate
from authoring.v6 import validator_runtime

RELEASE_SCHEMA="learnit.atlas.qualified_release_set.v2"; RELEASE_PROFILE="atlas.qualified-release-set.v6-r1"
RESULT_SCHEMA="learnit.atlas.qualified_release_set_result.v2"; PASS_BUILT="PASS_QUALIFIED_RELEASE_SET_V6_BUILT_R1"; PASS_VERIFIED="PASS_QUALIFIED_RELEASE_SET_V6_VERIFICATION_R1"; HOLD_INPUT="HOLD_QUALIFIED_RELEASE_SET_V6_INPUT_R1"; EXIT_HOLD=8
class V6ReleaseSetInputError(ValueError):pass

def canonical(v:Any)->bytes:return v6_gate.canonical(v)
def sha(b:bytes)->str:return v6_gate.sha256(b)
def digest(v:Any)->str:return v6_gate.digest(v)
def load_bytes(p:Path,label:str)->bytes:
    try:return p.read_bytes()
    except OSError as e:raise V6ReleaseSetInputError(f"{label}: {e}") from e
def load_json_bytes(b:bytes,label:str)->Any:
    try:return json.loads(b.decode())
    except Exception as e:raise V6ReleaseSetInputError(f"{label}: {e}") from e
def parse_specs(specs:list[str])->list[tuple[Path,Path]]:
    out=[]
    for s in specs:
        if "=" not in s:raise V6ReleaseSetInputError("entry must be RUN=KIT")
        r,k=s.split("=",1);out.append((Path(r),Path(k)))
    if not out:raise V6ReleaseSetInputError("at least one V6 release entry required")
    return out

def revision_rows(k:dict)->list[tuple[str,str]]:
    rows=[(k["packageRevisionId"],k["packageRevisionDigest"])]
    for c in k["courses"]:
        rows.append((c["courseRevisionId"],c["courseRevisionDigest"]));rows.extend((a["activityRevisionId"],a["activityRevisionDigest"]) for a in c["activities"])
    return rows

def entry_from_bytes(run_raw:bytes,kit_raw:bytes,label:str)->tuple[dict,dict,list[tuple[str,str]],str]:
    try:run=reliability_v6.verify_run(load_json_bytes(run_raw,label+" run"))
    except reliability_v6.V6ReliabilityInputError as e:raise V6ReleaseSetInputError(str(e)) from e
    if reliability_v6.decision_class(run)!="PASS":raise V6ReleaseSetInputError("FactoryRun is not PASS")
    gate=run["evidenceBundle"]["factoryEvidence"]
    if gate["verdict"]!=v6_gate.FACTORY_PASS or gate["schema"]!=v6_gate.FACTORY_EVIDENCE_SCHEMA or gate["profile"]!=v6_gate.FACTORY_PROFILE:raise V6ReleaseSetInputError("V6 Factory evidence is not exact PASS")
    sem=gate["semanticReview"];policy=gate["productionPolicy"]
    if sem["schema"]!=v6_gate.SEMANTIC_REVIEW_SCHEMA or sem["profile"]!=v6_gate.SEMANTIC_REVIEW_PROFILE or sem["verdict"]!=v6_gate.SEMANTIC_PASS:raise V6ReleaseSetInputError("semantic review is not exact PASS")
    if gate["sourceGovernance"]["verdict"]!=v6_gate.SOURCE_GOVERNANCE_PASS or policy["counts"]["constructed"]:raise V6ReleaseSetInputError("source/policy closure is not PASS")
    if policy["counts"]["productive"] and sem["v6Checks"]["productiveCorrectness"]!="pass":raise V6ReleaseSetInputError("productive correctness missing")
    if sem["v6Checks"]["visualAdequacy"]=="hold":raise V6ReleaseSetInputError("visual adequacy hold")
    if sha(kit_raw)!=run["evidenceBundle"]["artifacts"]["generatedKit"]["sha256"]:raise V6ReleaseSetInputError("kit bytes do not match FactoryRun")
    kit=load_json_bytes(kit_raw,label+" kit")
    if not isinstance(kit,dict) or kit.get("contract")!="learnit.kit.v6":raise V6ReleaseSetInputError("release requires learnit.kit.v6")
    report=validator_runtime.validate_document(kit,label)
    if not report.ok:raise V6ReleaseSetInputError("exact V6 validator failed")
    if v6_gate.production_policy(kit)["reasons"]:raise V6ReleaseSetInputError("V6 release policy failed")
    auth=gate["implementationAuthority"]["gitCommit"]
    entry={"packageLineageId":kit["packageLineageId"],"packageRevisionId":kit["packageRevisionId"],"packageRevisionDigest":kit["packageRevisionDigest"],"title":kit["title"],"versionLabel":kit["versionLabel"],"language":kit["language"],"kit":{"bytes":len(kit_raw),"sha256":sha(kit_raw)},"factoryRun":{"runId":run["runId"],"bytes":len(run_raw),"sha256":sha(run_raw),"factoryContextDigest":run["factoryContextDigest"],"implementationAuthority":auth}}
    return entry,kit,revision_rows(kit),auth

def build_manifest(rows:list[tuple[dict,dict,list[tuple[str,str]],str]])->dict:
    lineages=set();runs=set();revs={};auths={r[3] for r in rows}
    if len(auths)!=1:raise V6ReleaseSetInputError("mixed V6 authorities unsupported")
    for e,_k,rr,_a in rows:
        if e["packageLineageId"] in lineages or e["factoryRun"]["runId"] in runs:raise V6ReleaseSetInputError("duplicate release identity")
        lineages.add(e["packageLineageId"]);runs.add(e["factoryRun"]["runId"])
        for rid,rd in rr:
            if rid in revs and revs[rid]!=rd:raise V6ReleaseSetInputError("revision collision")
            revs[rid]=rd
    entries=sorted((r[0] for r in rows),key=lambda e:e["packageLineageId"]);metrics={"packages":len(rows),"courses":sum(len(r[1]["courses"]) for r in rows),"activities":sum(len(c["activities"]) for r in rows for c in r[1]["courses"])}
    core={"schema":RELEASE_SCHEMA,"profile":RELEASE_PROFILE,"factoryAuthority":next(iter(auths)),"entries":entries,"metrics":metrics};return {**core,"releaseSetId":digest(core)}
def km(e:dict)->str:return f"kits/{e['packageLineageId']}/{e['packageRevisionId']}.json"
def rm(e:dict)->str:return "factory-runs/"+e["factoryRun"]["runId"].split(":",1)[1]+".json"
def build_release_archive(specs:list[str],out:Path)->dict:
    rows=[];raws={}
    for i,(rp,kp) in enumerate(parse_specs(specs)):
        rr,kr=load_bytes(rp,"run"),load_bytes(kp,"kit");row=entry_from_bytes(rr,kr,f"entry[{i}]");rows.append(row);raws[row[0]["packageLineageId"]]=(rr,kr)
    m=build_manifest(rows);members={"release-set.json":canonical(m)}
    for e in m["entries"]:rr,kr=raws[e["packageLineageId"]];members[km(e)]=kr;members[rm(e)]=rr
    raw=handoff.zip_bytes(members);out.write_bytes(raw);v=verify_release_archive(out)
    if v["manifest"]!=m:raise V6ReleaseSetInputError("self-verification changed manifest")
    return {"schema":RESULT_SCHEMA,"verdict":PASS_BUILT,"releaseSetId":m["releaseSetId"],"factoryAuthority":m["factoryAuthority"],"releaseSha256":sha(raw),"releaseBytes":len(raw),"metrics":m["metrics"]}
def read_archive(raw:bytes)->dict[str,bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            out={}
            for info in z.infolist():
                name=handoff.safe_member_name(info.filename);mode=(info.external_attr>>16)&0o170000
                if mode not in (0,stat.S_IFREG) or name in out:raise V6ReleaseSetInputError("unsafe/duplicate member")
                out[name]=z.read(info)
    except (zipfile.BadZipFile,OSError,KeyError,RuntimeError,handoff.HandoffInputError) as e:raise V6ReleaseSetInputError(str(e)) from e
    if handoff.zip_bytes(out)!=raw:raise V6ReleaseSetInputError("release ZIP is not canonical")
    return out
def verify_release_archive(path:Path)->dict:
    raw=load_bytes(path,"release");members=read_archive(raw);mv=load_json_bytes(members.get("release-set.json",b""),"manifest")
    if not isinstance(mv,dict) or mv.get("schema")!=RELEASE_SCHEMA or mv.get("profile")!=RELEASE_PROFILE or members["release-set.json"]!=canonical(mv):raise V6ReleaseSetInputError("manifest identity/canonical mismatch")
    core={k:mv[k] for k in ("schema","profile","factoryAuthority","entries","metrics")}
    if mv.get("releaseSetId")!=digest(core) or not v6_gate.SHA40.fullmatch(str(mv.get("factoryAuthority"))):raise V6ReleaseSetInputError("manifest authority/digest mismatch")
    rows=[];expected={"release-set.json"}
    for i,e in enumerate(mv["entries"]):
        expected|={km(e),rm(e)};row=entry_from_bytes(members[rm(e)],members[km(e)],f"entry[{i}]")
        if row[0]!=e or e["factoryRun"]["implementationAuthority"]!=mv["factoryAuthority"]:raise V6ReleaseSetInputError("embedded entry/authority mismatch")
        rows.append(row)
    if set(members)!=expected or build_manifest(rows)!=mv:raise V6ReleaseSetInputError("release bytes do not match manifest")
    return {"schema":RESULT_SCHEMA,"verdict":PASS_VERIFIED,"releaseSetId":mv["releaseSetId"],"factoryAuthority":mv["factoryAuthority"],"releaseSha256":sha(raw),"releaseBytes":len(raw),"metrics":mv["metrics"],"manifest":mv}
def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser();s=p.add_subparsers(dest="cmd",required=True);b=s.add_parser("build");b.add_argument("--entry",action="append",default=[]);b.add_argument("--out",type=Path,required=True);v=s.add_parser("verify");v.add_argument("--release",type=Path,required=True);a=p.parse_args(argv)
    try:r=build_release_archive(a.entry,a.out) if a.cmd=="build" else verify_release_archive(a.release)
    except Exception as e:print(canonical({"schema":RESULT_SCHEMA,"verdict":HOLD_INPUT,"cause":str(e)}).decode());return EXIT_HOLD
    print(canonical({k:x for k,x in r.items() if k!="manifest"}).decode());return 0
if __name__=="__main__":raise SystemExit(main())
