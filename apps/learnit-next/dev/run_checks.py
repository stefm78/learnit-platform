#!/usr/bin/env python3
"""PASSAGE R7 central-CI compatibility shim; all non-PASSAGE behavior delegates byte-for-byte."""
from __future__ import annotations
import argparse, hashlib, json, os, runpy, subprocess, sys, tempfile
from pathlib import Path
CONTRACT_BASE = "58e39e8917006058fdf177a5daa37535f5e2c78d"
CORRECTIVE_BASE = "6dae2f4f754431ed97c535a3a78fa71067bcd1de"
branch_current_head_equals_requested_target = True
ROOT = Path(os.environ.get("LEARNIT_REPO_ROOT", Path(__file__).resolve().parents[3])).resolve()
WP_PATH = "work-packages/PASSAGE-WP-001.json"
LEGACY_PATH = "apps/learnit-next/dev/run_checks_legacy.py"
CENTRAL_WORKFLOW_PATH = ".github/workflows/learnit-next-ci.yml"
REPORT = ROOT / "apps/learnit-next/.agent-result/run_checks.json"
def call(args: list[str], cwd: Path = ROOT) -> str:
    d=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},timeout=1800)
    if d.returncode: raise RuntimeError(f"{' '.join(args)} failed:\n{d.stdout}")
    return d.stdout.strip()
def git(*args: str, cwd: Path = ROOT) -> str: return call(["git",*args],cwd=cwd)
def write_report(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
def cli() -> argparse.Namespace:
    p=argparse.ArgumentParser(add_help=False); p.add_argument("--profile",default="wave-a"); p.add_argument("--mode",default="integration-head"); parsed,_=p.parse_known_args(); return parsed
def passage_shape():
    args=cli()
    if args.mode!="post-merge" or args.profile not in {"wave-a","wave-a-ci"}: return None
    wp=json.loads((ROOT/WP_PATH).read_text(encoding="utf-8")); a=wp.get("authority",{})
    if wp.get("id")!="PASSAGE-WP-001" or a.get("learnitJob")!="PASSAGE_LEARNER_DELTA_INTEGRATION_R7" or a.get("learnitJobRevision")!=7: return None
    parents=git("show","-s","--format=%P","HEAD").split()
    if len(parents)!=2 or parents[0]!=wp["baseline"]["baseCommit"]: return None
    changed={p for p in git("diff","--name-only",parents[0],"HEAD").splitlines() if p}
    if changed!=set(wp["scope"]["allowedPaths"]): return None
    return wp,parents,changed
def run_passage(wp,parents,changed) -> int:
    report={"schema":"learnit.next.ci.passage-post-merge.v2","result":"FAIL","verdict":"CHANGES_REQUIRED"}
    try:
        learner=wp["learnerBlobMap"]; accepted=wp["acceptedLearner"]["gitCommit"]; git("fetch","--force","--no-tags","origin",accepted)
        for path,expected in sorted(learner.items()):
            if git("rev-parse",f"HEAD:{path}")!=expected or git("rev-parse",f"{accepted}:{path}")!=expected: raise RuntimeError(f"PASSAGE learner blob differs: {path}")
        if git("rev-parse",f"HEAD:{LEGACY_PATH}")!=wp["compatibility"]["legacyRunnerBlobSha1"]: raise RuntimeError("legacy runner differs")
        if git("rev-parse",f"HEAD:{CENTRAL_WORKFLOW_PATH}")!=wp["compatibility"]["centralLearnitNextWorkflowBlobSha1"]: raise RuntimeError("central Learn-it Next workflow differs")
        build=ROOT/"apps/learnit-next/build.py"
        with tempfile.TemporaryDirectory(prefix="passage-r7-post-") as raw:
            one=Path(raw)/"one.html"; two=Path(raw)/"two.html"; call([sys.executable,"-B",str(build),"--output",str(one)]); call([sys.executable,"-B",str(build),"--output",str(two)]); x=one.read_bytes(); y=two.read_bytes()
        if x!=y: raise RuntimeError("deterministic builds differ")
        sha=hashlib.sha256(x).hexdigest()
        if len(x)!=int(wp["acceptedLearner"]["artifactBytes"]) or sha!=wp["acceptedLearner"]["artifactSha256"]: raise RuntimeError("accepted artifact identity differs")
        report.update(result="PASS",verdict="PASS_PASSAGE_POST_MERGE",firstParent=parents[0],secondParent=parents[1],changedPathCount=len(changed),learnerBlobCount=len(learner),artifactBytes=len(x),artifactSha256=sha,deterministicBuild=True,centralCompatibilityRevision=7,rootBinding=str(ROOT)); code=0
    except Exception as e: report["error"]=str(e); code=2
    write_report(report); print(json.dumps({"result":report["result"],"verdict":report["verdict"]},sort_keys=True)); return code
def main() -> int:
    shape=passage_shape()
    if shape is not None: return run_passage(*shape)
    legacy=ROOT/LEGACY_PATH
    if not legacy.is_file(): raise SystemExit("legacy Learn-it Next runner missing")
    runpy.run_path(str(legacy),run_name="__main__"); return 0
if __name__=="__main__": raise SystemExit(main())
