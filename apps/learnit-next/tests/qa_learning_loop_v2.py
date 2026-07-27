#!/usr/bin/env python3
"""Independent contradictory QA for issue #119 / LEARNING-LOOP-V2 Wave A."""
from __future__ import annotations

import hashlib, json, os, re, shutil, subprocess, tempfile, threading, unittest, unicodedata
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(os.environ.get("LLV2_PRODUCT_TREE", Path(__file__).resolve().parents[3])).resolve()
FIX = ROOT / "contracts/fixtures"
VALID, INVALID = FIX / "llv2-valid-objective-loop.json", FIX / "llv2-invalid-objective-loop.json"
SCHEMA = ROOT / "contracts/learnit-kit-v2.schema.json"
ARTIFACT = Path(os.environ.get("LEARNIT_NEXT_ARTIFACT", ROOT / "apps/learnit-next/dist/learnit-next.html"))
STRICT = os.environ.get("LLV2_QA_STRICT") == "1"
BROWSER_STRICT = os.environ.get("LLV2_QA_BROWSER_STRICT") == "1"
STATUSES = {"not-started", "training", "review-needed", "ready-for-validation", "validated-recently"}
FIELDS = {"objectiveId", "trainingAttempts", "latestTrainingCorrect", "needsReview", "validationAttempts", "latestValidationCorrect", "status"}
CLAIM = re.compile(r"\b(ma[iî]trise durable|mastered|certification acquise|r[ée]tention (?:acquise|garantie))\b", re.I)


def load(path): return json.loads(path.read_text(encoding="utf-8"))
def norm(v):
    if v is None or isinstance(v, (bool, int)): return v
    if isinstance(v, float): raise TypeError("floats forbidden")
    if isinstance(v, str): return unicodedata.normalize("NFC", v)
    if isinstance(v, list): return [norm(x) for x in v]
    if isinstance(v, dict): return {unicodedata.normalize("NFC", k): norm(x) for k, x in v.items()}
    raise TypeError(type(v).__name__)
def canonical(v): return json.dumps(norm(v), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def digest(obj, field): return "sha256:" + hashlib.sha256(canonical({k: v for k, v in obj.items() if k != field})).hexdigest()
def digest_errors(p):
    out = []
    for ci, c in enumerate(p.get("courses", [])):
        for ai, a in enumerate(c.get("activities", [])):
            if a.get("activityRevisionDigest") != digest(a, "activityRevisionDigest"): out.append(f"course[{ci}].activity[{ai}]")
        if c.get("courseRevisionDigest") != digest(c, "courseRevisionDigest"): out.append(f"course[{ci}]")
    if p.get("packageRevisionDigest") != digest(p, "packageRevisionDigest"): out.append("package")
    return out
def semantic_errors(p):
    out = []
    for ci, c in enumerate(p.get("courses", [])):
        objectives = {o.get("objectiveId") for o in c.get("objectives", [])}
        roles = {o: {"practice": set(), "validation": set()} for o in objectives}
        for ai, a in enumerate(c.get("activities", [])):
            for oid in a.get("objectiveIds", []):
                if oid not in objectives: out.append(f"course[{ci}].activity[{ai}]: unknown objective {oid}"); continue
                role = a.get("assessmentRole")
                if role in roles[oid]: roles[oid][role].add(a.get("activityRevisionId"))
        for oid, by_role in roles.items():
            if not by_role["practice"]: out.append(f"{oid}: missing practice")
            if not by_role["validation"]: out.append(f"{oid}: missing validation")
            if by_role["practice"] & by_role["validation"]: out.append(f"{oid}: activity role overlap")
    return out

def require_candidate(case):
    needed = [ROOT/"apps/learnit-next/src/core/objective_progress.js", ROOT/"apps/learnit-next/src/main.js"]
    if all(p.is_file() for p in needed): return
    if STRICT: case.fail("integrated LLV2 candidate modules absent")
    case.skipTest("preparation branch: integrated LLV2 candidate modules absent")

NODE = r"""
import assert from 'node:assert/strict'; import fs from 'node:fs'; import {pathToFileURL} from 'node:url';
const root=process.env.LLV2_PRODUCT_TREE, fixture=JSON.parse(fs.readFileSync(process.env.LLV2_VALID_FIXTURE,'utf8'));
const {createLearnitRuntime}=await import(pathToFileURL(`${root}/apps/learnit-next/src/main.js`).href); assert.equal(typeof createLearnitRuntime,'function');
const clone=v=>structuredClone(v), key=(c,a)=>`${c}::${a}`;
class S { constructor(){this.courses=new Map;this.progress=new Map;this.meta=new Map([['rc718-sentinel',{value:'UNCHANGED'}]]);this.obj=new Map;this.rev=new Map;}
 async commitImport(p){for(const c of p.courses)this.courses.set(c.courseInstallId,clone(c));for(const r of p.revisions)this.rev.set(r.revisionId,r.digest);for(const m of p.meta)this.meta.set(m.key,clone(m.value));}
 async getRevisionDigestIndex(){return new Map(this.rev)} async listCourses(){return [...this.courses.values()].map(clone)} async getCourse(i){return clone(this.courses.get(i)||null)}
 async setCourseDisplayLabel(i,l){this.courses.get(i).displayLabel=l} async listProgress(c){return [...this.progress.values()].filter(x=>x.courseInstallId===c).map(clone)}
 async getProgress(c,a){return clone(this.progress.get(key(c,a))||null)} async putProgress(r){this.progress.set(key(r.courseInstallId,r.activityRevisionId),clone(r))}
 async getMeta(k){return clone(this.meta.get(k)||null)} async setMeta(k,v){this.meta.set(k,clone(v))} async deleteMeta(k){this.meta.delete(k)}
 async resetNextData(){this.courses.clear();this.progress.clear();this.obj.clear()} async storageReport(){return {courses:this.courses.size,progress:this.progress.size}}
 async listObjectiveProgress(c){return [...this.obj.values()].filter(x=>x.courseInstallId===c).map(clone)} async getObjectiveProgress(c,o){return clone(this.obj.get(key(c,o))||null)}
 async putObjectiveProgress(r){this.obj.set(key(r.courseInstallId,r.objectiveId),clone(r))} async setObjectiveProgress(r){return this.putObjectiveProgress(r)}
 async listLearningProgress(c){return this.listObjectiveProgress(c)} async getLearningProgress(c,o){return this.getObjectiveProgress(c,o)} async putLearningProgress(r){return this.putObjectiveProgress(r)} }
const storage=new Proxy(new S,{get(t,p,r){if(Reflect.has(t,p))return Reflect.get(t,p,r);if(typeof p!=='string')return;return async(...a)=>{const n=p.toLowerCase();if((n.includes('objective')||n.includes('learning'))&&n.startsWith('list'))return t.listObjectiveProgress(a[0]);if((n.includes('objective')||n.includes('learning'))&&n.startsWith('get'))return t.getObjectiveProgress(a[0],a[1]);if((n.includes('objective')||n.includes('learning'))&&(n.startsWith('put')||n.startsWith('set')||n.startsWith('save'))){const x=a.at(-1);if(x?.objectiveId)return t.putObjectiveProgress(x)}return null}}});
const rt=createLearnitRuntime(storage), imported=await rt.importPackage(fixture), cid=imported.courses[0].courseInstallId, c=fixture.courses[0], [p1,v1,p2,v2]=c.activities;
const answer=(a,ok)=>a.type==='qcm'?{choiceId:ok?a.correctChoiceId:a.choices.find(x=>x.choiceId!==a.correctChoiceId).choiceId}:Object.fromEntries(a.answers.map((x,i)=>[x.slotId,ok?x.tokenId:a.tokens.find(t=>t.tokenId!==x.tokenId)?.tokenId||a.tokens[(i+1)%a.tokens.length].tokenId]));
const project=async()=>{for(const n of ['getObjectiveProgress','getLearningProgress','getLearningLoop','getProgress'])if(typeof rt[n]==='function'){const x=await rt[n](cid);if(x?.objectives)return x.objectives;if(Array.isArray(x))return x}return await storage.listObjectiveProgress(cid)};
const by=(xs,o)=>xs.find(x=>x.objectiveId===o), oid1=c.objectives[0].objectiveId, oid2=c.objectives[1].objectiveId;
await rt.startCourse(cid); let r=await rt.answer(p1.activityRevisionId,answer(p1,false)); assert.equal(r.completed,true);
let x=by(await project(),oid1); assert.ok(x); assert.equal(x.trainingAttempts,1); assert.equal(x.validationAttempts,0); assert.equal(x.needsReview,true); assert.equal(x.status,'review-needed');
let q=await rt.getReviewQueue(cid); assert.deepEqual(q.activityRevisionIds,[p1.activityRevisionId]); await rt.startReviewQueue(cid); r=await rt.answer(p1.activityRevisionId,answer(p1,true));
x=by(await project(),oid1); assert.equal(x.validationAttempts,0); assert.equal(x.needsReview,false); assert.equal(x.status,'ready-for-validation');
await rt.startCourse(cid); await rt.answer(v1.activityRevisionId,answer(v1,true)); x=by(await project(),oid1); assert.equal(x.validationAttempts,1); assert.equal(x.status,'validated-recently');
let y=by(await project(),oid2); assert.ok(!y||y.validationAttempts===0); await rt.answer(p2.activityRevisionId,answer(p2,false)); await rt.startReviewQueue(cid);
const before=await rt.getSession(), rt2=createLearnitRuntime(storage), resumed=await rt2.resumeActiveCourse(); assert.equal(resumed.mode,'review'); assert.equal(resumed.currentActivity.activityRevisionId,before.currentActivity.activityRevisionId);
y=by(await project(),oid2); assert.equal(y.validationAttempts,0); assert.equal(y.needsReview,true); assert.deepEqual(await storage.getMeta('rc718-sentinel'),{value:'UNCHANGED'});
const text=JSON.stringify(await project()); assert.ok(!/maîtrise durable|mastered|certification acquise|rétention (?:acquise|garantie)/i.test(text));
console.log(JSON.stringify({ok:true,objectives:(await project()).length,review:(await rt.getReviewQueue(cid)).total}));
"""

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass
@contextmanager
def serve(path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(path.parent)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try: yield f"http://127.0.0.1:{server.server_port}/{path.name}"
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)

class FixturePreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if Draft202012Validator is None: raise unittest.SkipTest("DEPENDENCY: jsonschema")
        cls.schema, cls.valid, cls.invalid = load(SCHEMA), load(VALID), load(INVALID)
        cls.validator = Draft202012Validator(cls.schema)
    def test_00_frozen_contract(self):
        self.assertEqual("learnit.kit.v2", self.schema["properties"]["contract"]["const"])
        self.assertFalse(self.schema["additionalProperties"])
    def test_01_valid_multi_objective_distinct_loop(self):
        self.assertEqual([], list(self.validator.iter_errors(self.valid)))
        self.assertEqual([], digest_errors(self.valid)); self.assertEqual([], semantic_errors(self.valid))
        self.assertEqual(2, len(self.valid["courses"][0]["objectives"]))
    def test_02_unknown_objective_is_semantic_not_schema_noise(self):
        self.assertEqual([], list(self.validator.iter_errors(self.invalid)))
        self.assertEqual([], digest_errors(self.invalid)); self.assertTrue(any("unknown objective" in e for e in semantic_errors(self.invalid)))
    def test_03_no_durable_claims_in_fixtures(self):
        self.assertIsNone(CLAIM.search(VALID.read_text(encoding="utf-8"))); self.assertIsNone(CLAIM.search(INVALID.read_text(encoding="utf-8")))

class CandidateContract(unittest.TestCase):
    def test_10_shared_projection_and_statuses_are_declared(self):
        require_candidate(self); text=(ROOT/"apps/learnit-next/src/core/objective_progress.js").read_text(encoding="utf-8")
        for token in FIELDS|STATUSES: self.assertIn(token, text)
        self.assertIsNone(CLAIM.search(text))
    def test_11_qcm_fill_completed_and_p1_contract_remain(self):
        require_candidate(self); text="\n".join((ROOT/p).read_text(encoding="utf-8") for p in ["apps/learnit-next/src/core/session.js","apps/learnit-next/src/core/progress.js","apps/learnit-next/src/main.js"])
        for token in ("qcm","fill","completed","startReviewQueue","resumeActiveCourse","reviewIndex"): self.assertIn(token,text)
    def test_12_rc718_storage_is_unchanged_and_extension_is_additive(self):
        require_candidate(self); port=(ROOT/"apps/learnit-next/src/ports/storage.js").read_text(encoding="utf-8"); adapter=(ROOT/"apps/learnit-next/src/adapters/indexeddb.js").read_text(encoding="utf-8")
        for token in ("learnit.next.v1.","learnit_next_v1","NEXT_INDEXED_DB_VERSION = 1","packages","courses","progress","meta"): self.assertIn(token,port+adapter)
        self.assertRegex(port+adapter, r"(?i)(llv2|objective|learning)")
    def test_13_public_runtime_behavior_matrix(self):
        require_candidate(self); node=shutil.which("node"); self.assertIsNotNone(node)
        with tempfile.TemporaryDirectory(prefix="llv2-qa-") as d:
            h=Path(d)/"harness.mjs"; h.write_text(NODE,encoding="utf-8")
            env={**os.environ,"LLV2_PRODUCT_TREE":str(ROOT),"LLV2_VALID_FIXTURE":str(VALID),"LLV2_INVALID_FIXTURE":str(INVALID)}
            result=subprocess.run([node,str(h)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,timeout=180,check=False)
        self.assertEqual(0,result.returncode,result.stdout); self.assertTrue(json.loads(result.stdout.strip().splitlines()[-1])["ok"])

class CandidateBrowser(unittest.TestCase):
    def test_20_mobile_render_navigation_and_resume(self):
        if not ARTIFACT.is_file() or sync_playwright is None:
            if BROWSER_STRICT: self.fail("exact artifact and Playwright are required")
            self.skipTest("browser candidate prerequisites absent")
        with serve(ARTIFACT) as url, sync_playwright() as p:
            browser=p.chromium.launch(headless=True); page=browser.new_page(viewport={"width":390,"height":844}); page.goto(url); page.wait_for_load_state("networkidle")
            result=page.evaluate("""async payload=>{const api=globalThis.__LEARNIT_NEXT_TEST__;const x=await api.importPackage(payload);const c=x.courses[0].courseInstallId;await api.startCourse(c);return {courses:(await api.listCourses()).length,session:await api.getSession?.()}}""",load(VALID))
            self.assertEqual(1,result["courses"]); page.reload(); page.wait_for_load_state("networkidle")
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth"),1)
            body=page.locator("body").inner_text(); self.assertIsNone(CLAIM.search(body)); self.assertIn("Objectif",body)
            page.keyboard.press("Tab"); self.assertNotIn(page.evaluate("document.activeElement.tagName"),("BODY","HTML")); browser.close()

if __name__ == "__main__": unittest.main(verbosity=2)
