#!/usr/bin/env python3
"""Create the non-committed INT-WP-001 release envelope after every gate passes."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];APP=ROOT/"apps/learnit-next"
REPORT=APP/".agent-result/run_checks.json";OUTPUT=APP/"release";ART=APP/"dist/learnit-next.html"
INPUTS={"base":{"commit":"b83fa032b262ce41a82f5a3664a7b854e8ab8296","contract":"contracts/learnit-kit-v2.schema.json"},"runtime":{"pullRequest":82,"head":"7156749815fd727076786f9939aa4d7d78b8aa6d","reviewId":4713406180},"authoring":{"pullRequest":80,"head":"2cff1f7575b509d47095df7130137cf78276e58f","reviewId":4704571690},"qa":{"pullRequest":81,"head":"09da6c44741fd1421175f6d0feef0cab4b7761b1","reviewId":4711673437}}
ORDER=["frozen-contract","qa","authoring","runtime","integrator"]
def h(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def head()->str:
    p=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=False)
    if p.returncode:raise RuntimeError("exact Git source commit required")
    return p.stdout.strip()
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path,default=REPORT);p.add_argument("--output",type=Path,default=OUTPUT);a=p.parse_args()
    rp=a.report if a.report.is_absolute() else ROOT/a.report;out=a.output if a.output.is_absolute() else ROOT/a.output
    try:
        r=json.loads(rp.read_text(encoding="utf-8"));mfile=APP/"source_manifest.json";m=json.loads(mfile.read_text(encoding="utf-8"));q=r.get("qa",{})
        if r.get("result")!="PASS" or q.get("executed")!=30 or q.get("passed")!=30 or any(q.get(k) for k in ("skipped","failures","errors")):raise RuntimeError("strict 30/30 PASS report required")
        data=ART.read_bytes();digest=h(data);uses=dict(r["artifact"]["usages"]);uses["releaseEnvelopeArtifact"]=digest
        if len(set(uses.values()))!=1 or digest!=m["artifact"]["sha256"]:raise RuntimeError("release artifact differs from tested identity")
        if out.exists():shutil.rmtree(out)
        out.mkdir(parents=True);(out/"learnit-next.html").write_bytes(data)
        self_fp=next(x["fingerprint"]["value"] for x in m["workingFiles"] if x["path"]=="apps/learnit-next/source_manifest.json")
        e={"schema":"learnit.next.integration.release.v1","workPackage":"INT-WP-001","status":"READY_FOR_CONTRADICTORY_QA_AND_GOVERNOR_REVIEW","sourceCommit":head(),"acceptedInputs":INPUTS,"integrationOrder":ORDER,"manifest":{"path":"apps/learnit-next/source_manifest.json","sha256":h(mfile.read_bytes()),"selfFingerprint":self_fp,"fileBudget":32},"artifact":{"path":"learnit-next.html","sha256":digest,"bytes":len(data),"identityUsages":uses},"tests":{"result":"PASS","executed":30,"passed":30,"skipped":0,"failures":0,"errors":0,"detailedReportSha256":h(rp.read_bytes()),"details":r},"environment":r["environment"],"cleanBuildProof":r["cleanBuilds"],"roleProvenance":r["provenance"]["roleFiles"],"browserArtifactProof":{"sha256":r["artifact"]["usages"]["browserTests"],"sameAsRelease":True},"residualRisks":["Contradictory QA has not accepted this exact integration head.","The governor has not accepted this exact integration head.","No human successor test has been launched.","NVDA, TalkBack, VoiceOver and physical-device evidence remain absent.","The clean break intentionally does not migrate RC718 history."],"missingHumanEvidence":["rupture-notice comprehension","physical-device interaction","assistive-technology validation","final human release gate"],"rollback":"Close PR #83, discard generated dist/release outputs, and leave RC718 promoted."}
        ep=out/"release-envelope.json";ep.write_text(json.dumps(e,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"result":"PASS","sourceCommit":e["sourceCommit"],"artifactSha256":digest,"envelopeSha256":h(ep.read_bytes()),"output":out.relative_to(ROOT).as_posix()},sort_keys=True));return 0
    except Exception as exc:print(f"RELEASE_ERROR: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
