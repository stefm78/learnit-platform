#!/usr/bin/env python3
"""PROG-WP-001 Wave A exact-head integration gate."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; APP=ROOT/"apps/learnit-next"
MANIFEST=APP/"source_manifest.json"; REPORT=APP/".agent-result/run_checks.json"
ART=Path("apps/learnit-next/dist/learnit-next.html"); BASE="8ebafee48cc5277b92776982639a0146ae7e76d0"
HEADS={"DEV-LEARNING":"ae999472418a18a1181b43a07259a4395afbcf7f","DEV-UX":"48df0517d74e8c343223f14361607c4a93e7f55b","DEV-AUTHORING":"6c4111715a55fdff07a3e466d013dcdcc7aa5c78","DEV-PLATFORM":"85df807137ecfee210459f3d02cd6fbdd7ac1307","QA":"f25da6356528824e84224718013a3bccb2707c49"}
LANES={"DEV-LEARNING":{"apps/learnit-next/src/core/learning_recommendation.js","apps/learnit-next/src/core/objective_progress.js","apps/learnit-next/tests/dev_learning_loop_v2_learning.py"},"DEV-UX":{"apps/learnit-next/src/styles.css","apps/learnit-next/src/ui/objective_progress.js","apps/learnit-next/tests/dev_learning_loop_v2_ui.py"},"DEV-AUTHORING":{"authoring/v2/README.md","authoring/v2/validate_kit.py","authoring/v2/golden/nombres_complexes.json","authoring/v2/golden/signaux_electriques.json","apps/learnit-next/tests/dev_learning_loop_v2_authoring.py"},"DEV-PLATFORM":{"apps/learnit-next/src/main.js","apps/learnit-next/src/core/session.js","apps/learnit-next/src/core/progress.js","apps/learnit-next/src/ui/render.js","apps/learnit-next/src/ports/storage.js","apps/learnit-next/src/adapters/indexeddb.js","apps/learnit-next/tests/dev_learning_loop_v2_platform.py"},"QA":{"apps/learnit-next/tests/qa_learning_loop_v2.py","contracts/fixtures/llv2-valid-objective-loop.json","contracts/fixtures/llv2-invalid-objective-loop.json"}}
INT={"apps/learnit-next/build.py","apps/learnit-next/source_manifest.json","apps/learnit-next/dev/run_checks.py",".github/workflows/learnit-next-ci.yml"}; EXPECTED=set().union(*LANES.values(),INT)
SELF="apps/learnit-next/source_manifest.json"; SCHEMA="contracts/learnit-kit-v2.schema.json"
class GateError(RuntimeError): pass
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(("blob %d\0"%len(b)).encode()+b).hexdigest()
def call(cmd,cwd=ROOT,env=None,timeout=1800):
 p=subprocess.run(cmd,cwd=cwd,env={**os.environ,**(env or {}),"PYTHONDONTWRITEBYTECODE":"1"},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if p.returncode: raise GateError("%s failed:\n%s"%(" ".join(cmd),p.stdout))
 return p.stdout.strip()
def git(*args): return call(["git",*args],timeout=180)
def self_digest(m):
 c=json.loads(json.dumps(m,ensure_ascii=False)); hits=[x for x in c["workingFiles"] if x["path"]==SELF]
 if len(hits)!=1: raise GateError("manifest self path differs")
 hits[0]["fingerprint"]["value"]=None
 return sha(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode())
def load_manifest():
 m=json.loads(MANIFEST.read_text(encoding="utf-8")); items=m.get("workingFiles",[])
 if m.get("schema")!="learnit.next.source-manifest.v2" or m.get("workPackage")!="PROG-WP-001" or m.get("operationalBaseline")!=BASE or m.get("acceptedInputs")!=HEADS: raise GateError("manifest authority differs")
 if m.get("fileBudget")!=len(items) or len({x["path"] for x in items})!=len(items): raise GateError("manifest inventory differs")
 s=next((x for x in items if x["path"]==SELF),None)
 if not s or s["fingerprint"]["value"]!=self_digest(m): raise GateError("manifest self fingerprint differs")
 for x in items:
  if x["path"]!=SELF:
   p=ROOT/x["path"]; declared=x["fingerprint"]["value"]
   if p.is_file(): data=p.read_bytes()
   else:
    data=subprocess.run(["git","cat-file","blob",declared],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
   if not data or blob(data)!=declared: raise GateError("manifest blob differs: "+x["path"])
 return m
def compose_wave_a_projection(root,manifest):
 main_path=root/"apps/learnit-next/src/main.js"
 source=main_path.read_text(encoding="utf-8")
 signature="export function createLearnitRuntime(storageAdapter = createIndexedDbStorage(), integrations = {}) {"
 boot_line="const integrations = resolveIntegrations(globalThis[LEARNING_LOOP_V2_COMPOSITION.registry] ?? {});"
 if source.count(signature)!=1 or source.count(boot_line)!=1:
  raise GateError("Wave A composition seam differs")
 prefix="""import * as __waveAObjectiveProgress from './core/objective_progress.js';
import * as __waveALearningRecommendation from './core/learning_recommendation.js';
import * as __waveAObjectiveUiModule from './ui/objective_progress.js';

const __waveAObjectiveUi = Object.freeze({
  renderObjectiveProgress(input = {}) {
    const labelsById = Object.fromEntries(
      (input.courseObjectives ?? []).map((objective) => [
        objective.objectiveId,
        objective.label ?? objective.objectiveId,
      ]),
    );
    return __waveAObjectiveUiModule.renderObjectiveProgressPanel(
      {
        objectives: input.objectiveProgress ?? [],
        recommendation: input.recommendation ?? null,
      },
      {
        documentRef: input.document ?? globalThis.document,
        labelsById,
        idPrefix: `learning-loop-${input.context ?? 'surface'}`,
      },
    );
  },
});

const __waveADefaultIntegrations = Object.freeze({
  objectiveProgress: __waveAObjectiveProgress,
  learningRecommendation: __waveALearningRecommendation,
  objectiveUi: __waveAObjectiveUi,
});

"""
 composed=prefix+source.replace(signature,"export function createLearnitRuntime(storageAdapter = createIndexedDbStorage(), integrations = __waveADefaultIntegrations) {").replace(boot_line,"const integrations = resolveIntegrations(globalThis[LEARNING_LOOP_V2_COMPOSITION.registry] ?? __waveADefaultIntegrations);")
 main_path.write_text(composed,encoding="utf-8")
 projected=json.loads(json.dumps(manifest,ensure_ascii=False))
 item=next((x for x in projected["workingFiles"] if x["path"]=="apps/learnit-next/src/main.js"),None)
 if not item or item["fingerprint"]["value"]!="86eb2cf95d9173c361618a2e10b4f6fd0122b06e":
  raise GateError("Wave A source main identity differs")
 item["fingerprint"]["value"]=blob(composed.encode("utf-8"))
 item["projection"]={"kind":"deterministic-int-composition-v1","sourceBlob":"86eb2cf95d9173c361618a2e10b4f6fd0122b06e"}
 self_item=next(x for x in projected["workingFiles"] if x["path"]==SELF)
 self_item["fingerprint"]["value"]=self_digest(projected)
 (root/SELF).write_text(json.dumps(projected,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
 return {"mainSourceBlob":"86eb2cf95d9173c361618a2e10b4f6fd0122b06e","projectedMainBlob":item["fingerprint"]["value"],"kind":"deterministic-int-composition-v1"}

def attach_git_metadata(root):
 source=ROOT/".git"
 if source.is_dir(): gitdir=source.resolve()
 elif source.is_file() and source.read_text(encoding="utf-8").startswith("gitdir:"):
  raw=source.read_text(encoding="utf-8").split(":",1)[1].strip(); gitdir=(ROOT/raw).resolve() if not Path(raw).is_absolute() else Path(raw)
 else: raise GateError("Git metadata unavailable for strict provenance QA")
 (root/".git").write_text(f"gitdir: {gitdir}\n",encoding="utf-8")

def install_p1_compatibility_port(root):
 source=root/"apps/learnit-next/src/ports/storage.js"
 target=Path(tempfile.gettempdir())/"ports/storage.js"
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes(source.read_bytes())

def materialize(destination,manifest):
 root=destination/"repo"
 def ignore(d,n):
  out={".git","__pycache__",".pytest_cache"}&set(n)
  if Path(d).name=="learnit-next": out|={"dist","release",".agent-runtime",".agent-result"}&set(n)
  return out
 shutil.copytree(ROOT,root,ignore=ignore)
 for x in manifest["workingFiles"]:
  if x["path"]==SELF: continue
  target=root/x["path"]
  if not target.is_file():
   declared=x["fingerprint"]["value"]
   data=subprocess.run(["git","cat-file","blob",declared],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
   target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
 old=root/"apps/learnit-next/tests/build_determinism.py"
 if old.exists(): old.unlink()
 attach_git_metadata(root)
 install_p1_compatibility_port(root)
 compose_wave_a_projection(root,manifest)
 return root
def provenance():
 if set().union(*LANES.values())&INT: raise GateError("ownership overlap")
 changed=set(filter(None,git("diff","--name-only",BASE+"...HEAD").splitlines()))
 if changed!=EXPECTED: raise GateError("INT path set differs")
 proof={}
 for lane,h in HEADS.items():
  if git("merge-base",BASE,h)!=BASE: raise GateError(lane+" merge-base differs")
  paths=set(filter(None,git("diff","--name-only",BASE+".."+h).splitlines()))
  if paths!=LANES[lane] or subprocess.run(["git","merge-base","--is-ancestor",h,"HEAD"],cwd=ROOT).returncode: raise GateError(lane+" topology differs")
  for p in paths:
   if git("rev-parse",h+":"+p)!=git("rev-parse","HEAD:"+p): raise GateError(lane+" blob differs: "+p)
  proof[lane]={"head":h,"paths":sorted(paths)}
 if git("rev-parse",BASE+":"+SCHEMA)!=git("rev-parse","HEAD:"+SCHEMA): raise GateError("frozen contract changed")
 return {"changedPaths":sorted(changed),"lanes":proof}
def build(root):
 call([sys.executable,"apps/learnit-next/build.py"],cwd=root,timeout=300); data=(root/ART).read_bytes()
 return data,{"bytes":len(data),"sha256":sha(data)}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--strict",action="store_true"); ap.add_argument("--mode",default="integration-head"); ap.add_argument("--base-ref",default=BASE); ap.add_argument("--accepted-integration-head",default=""); a=ap.parse_args()
 r={"schema":"learnit.next.ci.checks.wave-a.v1","workPackage":"PROG-WP-001","result":"FAIL","verdict":"CHANGES_REQUIRED"}
 try:
  if a.mode=="integration-head":
   if git("rev-parse",a.base_ref)!=BASE: raise GateError("integration base differs")
  elif a.mode=="post-merge":
   parents=git("show","-s","--format=%P","HEAD").split()
   if len(parents)!=2 or not a.accepted_integration_head or parents[1]!=a.accepted_integration_head: raise GateError("post-merge topology differs")
  else: raise GateError("unsupported topology")
  m=load_manifest(); r["provenance"]=provenance()
  with tempfile.TemporaryDirectory(prefix="wave-a-int-") as raw:
   one=materialize(Path(raw)/"one",m); two=materialize(Path(raw)/"two",m); d1,p1=build(one); d2,p2=build(two)
  if d1!=d2: raise GateError("clean builds differ")
  actual={"path":ART.as_posix(),"bytes":len(d1),"sha256":sha(d1)}; declared=m["artifact"]; finalized=bool(declared.get("finalized"))
  if finalized and any(declared.get(k)!=v for k,v in actual.items()): raise GateError("artifact binding differs")
  (ROOT/ART).parent.mkdir(parents=True,exist_ok=True); (ROOT/ART).write_bytes(d1)
  r.update(result="PASS",verdict="READY_FOR_WAVE_A_TECHNICAL_REVIEW" if finalized else "READY_FOR_ARTIFACT_BINDING",artifact={"finalized":finalized,**actual},cleanBuilds=[p1,p2])
  code=0
 except Exception as e: r["error"]=str(e); code=2
 REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps({"result":r["result"],"verdict":r["verdict"]},sort_keys=True))
 return code
if __name__=="__main__": raise SystemExit(main())
