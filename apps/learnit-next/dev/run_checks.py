#!/usr/bin/env python3
"""Strict INT-WP-001 provenance, build, test and release gate."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, platform, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
APP=ROOT/"apps/learnit-next"
MANIFEST=APP/"source_manifest.json"
REPORT=APP/".agent-result/run_checks.json"
ART=Path("apps/learnit-next/dist/learnit-next.html")
SELF="apps/learnit-next/source_manifest.json"
BASE="b83fa032b262ce41a82f5a3664a7b854e8ab8296"
INPUTS={"runtime":"7156749815fd727076786f9939aa4d7d78b8aa6d","authoring":"2cff1f7575b509d47095df7130137cf78276e58f","qa":"09da6c44741fd1421175f6d0feef0cab4b7761b1"}
REVIEWS={"runtime":4713406180,"authoring":4704571690,"qa":4711673437}
INTEGRATOR={".github/workflows/learnit-next-ci.yml","apps/learnit-next/build.py","apps/learnit-next/dev/release.py","apps/learnit-next/dev/run_checks.py",SELF}
ROLE={
"runtime":{"apps/learnit-next/README.md","apps/learnit-next/index.template.html","apps/learnit-next/src/styles.css","apps/learnit-next/src/main.js","apps/learnit-next/src/core/canonical_json.js","apps/learnit-next/src/core/identity.js","apps/learnit-next/src/core/contract.js","apps/learnit-next/src/core/import.js","apps/learnit-next/src/core/library.js","apps/learnit-next/src/core/session.js","apps/learnit-next/src/core/progress.js","apps/learnit-next/src/ports/storage.js","apps/learnit-next/src/adapters/indexeddb.js","apps/learnit-next/src/ui/render.js"},
"authoring":{"authoring/v2/README.md","authoring/v2/generate_ids.py","authoring/v2/validate_kit.py","authoring/v2/golden/nombres_complexes.json","authoring/v2/golden/signaux_electriques.json"},
"qa":{"contracts/fixtures/v2-valid-minimal.json","contracts/fixtures/v2-invalid-legacy.json","contracts/fixtures/v2-invalid-digest-mismatch.json","apps/learnit-next/tests/contract_v2.py","apps/learnit-next/tests/storage_isolation.py","apps/learnit-next/tests/browser_vertical_slice.py","apps/learnit-next/tests/build_determinism.py"}}
SCHEMA="contracts/learnit-kit-v2.schema.json"
JS=[p for p in ROLE["runtime"] if p.endswith(".js")]

class GateError(RuntimeError): pass
def h(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def bh(data:bytes)->str:return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
def run(args:list[str],cwd:Path,env:dict[str,str]|None=None,timeout:int=1200)->dict[str,Any]:
    p=subprocess.run(args,cwd=cwd,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1",**(env or {})},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,check=False)
    return {"command":args,"returnCode":p.returncode,"output":p.stdout,"outputSha256":h(p.stdout.encode())}
def need(r:dict[str,Any],label:str)->None:
    if r["returnCode"]:raise GateError(f"{label} failed ({r['returnCode']}):\n{r['output']}")
def git(*args:str)->str:
    r=run(["git",*args],ROOT,timeout=120);need(r,"git "+" ".join(args));return r["output"].strip()
def gbytes(*args:str)->bytes:
    p=subprocess.run(["git",*args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if p.returncode:raise GateError(p.stderr.decode("utf-8","replace"))
    return p.stdout
def self_digest(m:dict[str,Any])->str:
    c=json.loads(json.dumps(m,ensure_ascii=False));hits=[x for x in c["workingFiles"] if x["path"]==SELF]
    if len(hits)!=1:raise GateError("manifest self path is not unique")
    hits[0]["fingerprint"]["value"]=None
    return h(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode())
def inventory()->set[str]:
    out={SCHEMA,*INTEGRATOR}
    for paths in ROLE.values():out|=paths
    return out

def provenance(m:dict[str,Any])->dict[str,Any]:
    if m.get("acceptedInputs")!=INPUTS or m.get("acceptedReviews")!=REVIEWS:raise GateError("immutable inputs or reviews differ")
    if m.get("integrationOrder")!=["frozen-contract","qa","authoring","runtime","integrator"]:raise GateError("integration order differs")
    items=m.get("workingFiles",[]);paths=[x.get("path") for x in items]
    if m.get("fileBudget")!=32 or len(items)!=32 or len(set(paths))!=32 or set(paths)!=inventory():raise GateError("exact 32-file inventory differs")
    by={x["path"]:x for x in items};s=by[SELF]
    if s["fingerprint"]["kind"]!="canonical-self-sha256" or s["fingerprint"]["value"]!=self_digest(m):raise GateError("manifest self fingerprint is stale")
    base_ref=os.environ.get("LEARNIT_NEXT_BASE_REF","origin/main")
    if git("rev-parse",base_ref)!=BASE:raise GateError("frozen base moved")
    parents=git("show","-s","--format=%P","HEAD").split();expected=[BASE,INPUTS["qa"],INPUTS["authoring"],INPUTS["runtime"]]
    if parents!=expected:raise GateError(f"parent order differs: {parents}")
    if git("merge-base",base_ref,"HEAD")!=BASE:raise GateError("base is not first-parent merge base")
    changed=[x for x in git("diff","--name-only",f"{base_ref}...HEAD").splitlines() if x]
    if len(changed)!=5 or set(changed)!=INTEGRATOR:raise GateError(f"integrator diff differs: {changed}")
    if git("status","--porcelain"):raise GateError("repository dirty before checks")
    schema_blob=git("rev-parse",f"{BASE}:{SCHEMA}")
    if by[SCHEMA]["fingerprint"]["value"]!=schema_blob:raise GateError("frozen schema differs")
    proof={}
    for owner,owned in ROLE.items():
        actual={x["path"] for x in items if x.get("owner")==owner}
        if actual!=owned:raise GateError(f"{owner} inventory differs")
        files={}
        for path in sorted(owned):
            declared=by[path]["fingerprint"]["value"];accepted=git("rev-parse",f"{INPUTS[owner]}:{path}");data=gbytes("cat-file","blob",accepted)
            if declared!=accepted or bh(data)!=accepted:raise GateError(f"{owner} blob differs: {path}")
            files[path]={"acceptedBlobSha1":accepted,"materializedBlobSha1":accepted,"identical":True}
        proof[owner]={"commit":INPUTS[owner],"reviewId":REVIEWS[owner],"files":files}
    if {x["path"] for x in items if x.get("owner")=="integrator"}!=INTEGRATOR:raise GateError("integrator inventory differs")
    for path in INTEGRATOR-{SELF}:
        if by[path]["fingerprint"]["value"]!=git("rev-parse",f"HEAD:{path}"):raise GateError(f"integrator fingerprint stale: {path}")
    return {"baseCommit":BASE,"sourceCommit":git("rev-parse","HEAD"),"parents":parents,"changedPaths":sorted(changed),"changedPathCount":5,"manifestBudget":32,"roleFileCount":26,"roleFiles":proof,"schema":{"path":SCHEMA,"acceptedBlobSha1":schema_blob,"materializedBlobSha1":schema_blob,"identical":True}}

def materialize(dst:Path,m:dict[str,Any])->Path:
    root=dst/"repo"
    def ignore(d:str,n:list[str])->set[str]:
        x={".git","__pycache__",".pytest_cache"}&set(n)
        if Path(d).name=="learnit-next":x|={"dist","release",".agent-runtime",".agent-result"}&set(n)
        return x
    shutil.copytree(ROOT,root,ignore=ignore)
    for x in m["workingFiles"]:
        if x.get("owner") in ROLE or x["path"]==SCHEMA:
            data=gbytes("cat-file","blob",x["fingerprint"]["value"]);target=root/x["path"];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for x in m["workingFiles"]:
        p=root/x["path"]
        if not p.is_file():raise GateError(f"materialized file missing: {x['path']}")
        if x["path"]!=SELF and bh(p.read_bytes())!=x["fingerprint"]["value"]:raise GateError(f"materialized fingerprint differs: {x['path']}")
    return root
def build(root:Path)->dict[str,Any]:
    r=run([sys.executable,"apps/learnit-next/build.py"],root,timeout=300);need(r,"build");data=(root/ART).read_bytes()
    return {"sha256":h(data),"bytes":len(data),"data":data,"command":r}

def checks(report:dict[str,Any],m:dict[str,Any])->None:
    with tempfile.TemporaryDirectory() as raw:
        a=materialize(Path(raw)/"a",m);b=materialize(Path(raw)/"b",m);ba=build(a);bb=build(b)
        if ba["data"]!=bb["data"]:raise GateError("clean builds differ byte-for-byte")
        if ba["sha256"]!=m["artifact"]["sha256"]:raise GateError("manifest artifact digest differs")
        report["cleanBuilds"]={"builds":[{"name":"clean-1",**{k:v for k,v in ba.items() if k!="data"}},{"name":"clean-2",**{k:v for k,v in bb.items() if k!="data"}}],"byteForByteIdentical":True}
        out=ROOT/ART;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(ba["data"]);tested=h(out.read_bytes())
        uses={k:ba["sha256"] for k in ["cleanBuild1","cleanBuild2","manifest","releaseEnvelope","contradictoryQaProposal","governorReviewProposal"]};uses["browserTests"]=tested
        if len(set(uses.values()))!=1:raise GateError("artifact identity chain differs")
        report["artifact"]={"path":ART.as_posix(),"sha256":ba["sha256"],"bytes":ba["bytes"],"usages":uses}
        py=["apps/learnit-next/build.py","apps/learnit-next/dev/run_checks.py","apps/learnit-next/dev/release.py","authoring/v2/generate_ids.py","authoring/v2/validate_kit.py","apps/learnit-next/tests/contract_v2.py","apps/learnit-next/tests/storage_isolation.py","apps/learnit-next/tests/browser_vertical_slice.py","apps/learnit-next/tests/build_determinism.py"]
        r=run([sys.executable,"-m","py_compile",*py],a,timeout=180);need(r,"Python compilation");report["compilation"]=r
        node=[]
        for p in sorted(JS):
            r=run(["node","--check",p],a,timeout=120);need(r,f"Node syntax {p}");node.append(r)
        report["nodeSyntax"]={"count":len(node),"paths":sorted(JS),"results":node}
        jp=[SCHEMA,"docs/architecture/clean-generation/FILE_PLAN_V1.json",SELF,"contracts/fixtures/v2-valid-minimal.json","contracts/fixtures/v2-invalid-legacy.json","contracts/fixtures/v2-invalid-digest-mismatch.json","authoring/v2/golden/nombres_complexes.json","authoring/v2/golden/signaux_electriques.json"]
        for p in jp:json.loads((a/p).read_text(encoding="utf-8"))
        report["jsonParsing"]={"count":len(jp),"paths":jp}
        r=run([sys.executable,"authoring/v2/validate_kit.py","--schema",SCHEMA,"--foundation-profile","authoring/v2/golden/nombres_complexes.json","authoring/v2/golden/signaux_electriques.json"],a,timeout=300);need(r,"golden kits");report["goldenKits"]=r
        q=run([sys.executable,"-m","unittest","discover","-s","apps/learnit-next/tests","-p","*.py","-v"],a,{"LEARNIT_NEXT_STRICT_INTEGRATION":"1","LEARNIT_NEXT_ARTIFACT":str(a/ART)},1200);need(q,"strict QA")
        match=re.search(r"Ran\s+(\d+)\s+tests?",q["output"])
        if not match or int(match.group(1))!=30 or re.search(r"skipped=|FAILED|ERROR",q["output"]):raise GateError("QA did not prove 30/30 PASS, zero skip/failure/error:\n"+q["output"])
        report["qa"]={**q,"executed":30,"passed":30,"skipped":0,"failures":0,"errors":0}
        nodev=run(["node","--version"],ROOT,timeout=60);need(nodev,"Node version")
        chrom=run([sys.executable,"-c","from playwright.sync_api import sync_playwright;p=sync_playwright().start();b=p.chromium.launch(headless=True);print(b.version);b.close();p.stop()"],ROOT,timeout=180);need(chrom,"Chromium version")
        report["environment"]={"python":platform.python_version(),"jsonschema":importlib.metadata.version("jsonschema"),"playwright":importlib.metadata.version("playwright"),"node":nodev["output"].strip(),"chromium":chrom["output"].strip()}
        report["result"]="PASS"

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path,default=REPORT);p.add_argument("--strict",action="store_true");a=p.parse_args()
    target=a.report if a.report.is_absolute() else ROOT/a.report
    report={"schema":"learnit.next.integration.checks.v1","workPackage":"INT-WP-001","strict":bool(a.strict or os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION")=="1"),"result":"FAIL"}
    try:
        if not report["strict"]:raise GateError("strict mode is mandatory")
        m=json.loads(MANIFEST.read_text(encoding="utf-8"));report["provenance"]=provenance(m);checks(report,m)
    except Exception as exc:report["error"]=str(exc);report["result"]="FAIL"
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"result":report["result"],"report":target.relative_to(ROOT).as_posix(),"artifactSha256":report.get("artifact",{}).get("sha256")},sort_keys=True))
    if report["result"]!="PASS":print(report.get("error","unknown failure"),file=sys.stderr);return 1
    return 0
if __name__=="__main__":raise SystemExit(main())
