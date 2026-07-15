#!/usr/bin/env python3
"""Independent learnit.kit.v2 oracle plus black-box runtime attacks."""
from __future__ import annotations
import copy, hashlib, json, os, re, threading, unicodedata, unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None
try:
    from playwright.sync_api import Error as PlaywrightError, sync_playwright
except ImportError:
    PlaywrightError, sync_playwright = RuntimeError, None

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / "contracts/fixtures"
SCHEMA = ROOT / "contracts/learnit-kit-v2.schema.json"
VALID, LEGACY, MISMATCH = (F / n for n in (
    "v2-valid-minimal.json", "v2-invalid-legacy.json", "v2-invalid-digest-mismatch.json"))
ARTIFACT = ROOT / "apps/learnit-next/dist/learnit-next.html"
UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
STRICT = os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION") == "1"

def require_or_skip(condition: bool, message: str) -> None:
    if condition:
        return
    if STRICT:
        raise RuntimeError(message)
    raise unittest.SkipTest(message)

def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def norm(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int)): return v
    if isinstance(v, float): raise TypeError("floats forbidden")
    if isinstance(v, str): return unicodedata.normalize("NFC", v)
    if isinstance(v, list): return [norm(x) for x in v]
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            nk = unicodedata.normalize("NFC", k)
            if nk in out: raise ValueError("NFC key collision")
            out[nk] = norm(x)
        return out
    raise TypeError(type(v).__name__)

def canonical(v: Any) -> bytes:
    return json.dumps(norm(v), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()

def digest(obj: dict[str, Any], field: str) -> str:
    return "sha256:" + hashlib.sha256(canonical({k:v for k,v in obj.items() if k != field})).hexdigest()

def redigest(pkg: dict[str, Any]) -> dict[str, Any]:
    p = copy.deepcopy(pkg)
    for c in p["courses"]:
        for a in c["activities"]: a["activityRevisionDigest"] = digest(a, "activityRevisionDigest")
        c["courseRevisionDigest"] = digest(c, "courseRevisionDigest")
    p["packageRevisionDigest"] = digest(p, "packageRevisionDigest")
    return p

def duplicates(seq):
    seen, dup = set(), set()
    for x in seq:
        if x in seen: dup.add(x)
        seen.add(x)
    return dup

def semantic_errors(p: dict[str, Any]) -> list[str]:
    e = []
    if p.get("contract") != "learnit.kit.v2": return ["contract"]
    for key in ("courseLineageId", "courseRevisionId"):
        if duplicates(c[key] for c in p["courses"]): e.append(f"duplicate {key}")
    global_activity_lineage, global_activity_revision = [], []
    for c in p["courses"]:
        objectives = [o["objectiveId"] for o in c["objectives"]]
        if duplicates(objectives): e.append("duplicate objectiveId")
        global_activity_lineage += [a["activityLineageId"] for a in c["activities"]]
        global_activity_revision += [a["activityRevisionId"] for a in c["activities"]]
        for a in c["activities"]:
            if any(x not in objectives for x in a["objectiveIds"]): e.append("missing objective")
            if a["type"] == "qcm":
                ids = [x["choiceId"] for x in a["choices"]]
                if duplicates(ids): e.append("duplicate choice")
                if a["correctChoiceId"] not in ids: e.append("missing choice")
            else:
                slots = [x["slotId"] for x in a["segments"] if "slotId" in x]
                token_ids = [x["tokenId"] for x in a["tokens"]]
                if duplicates(slots): e.append("duplicate slot")
                if duplicates(token_ids): e.append("duplicate token")
                token_limits = {x["tokenId"]: x["maxUses"] for x in a["tokens"]}
                answers = [x["slotId"] for x in a["answers"]]
                if duplicates(answers): e.append("duplicate answer")
                if set(answers) != set(slots): e.append("slot reference")
                uses = {}
                for x in a["answers"]:
                    if x["tokenId"] not in token_limits: e.append("token reference")
                    uses[x["tokenId"]] = uses.get(x["tokenId"], 0) + 1
                if any(n > token_limits.get(t, -1) for t,n in uses.items()): e.append("maxUses")
    if duplicates(global_activity_lineage): e.append("duplicate activityLineageId")
    if duplicates(global_activity_revision): e.append("duplicate activityRevisionId")
    return e

def digest_errors(p: dict[str, Any]) -> list[str]:
    e = []
    for c in p["courses"]:
        for a in c["activities"]:
            if a["activityRevisionDigest"] != digest(a, "activityRevisionDigest"): e.append("activity")
        if c["courseRevisionDigest"] != digest(c, "courseRevisionDigest"): e.append("course")
    if p["packageRevisionDigest"] != digest(p, "packageRevisionDigest"): e.append("package")
    return e

def identity_values(v: Any):
    if isinstance(v, dict):
        for k,x in v.items():
            if k.endswith("Id") and isinstance(x, str): yield x
            yield from identity_values(x)
    elif isinstance(v, list):
        for x in v: yield from identity_values(x)

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass
@contextmanager
def serve(path: Path):
    s = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(path.parent)))
    t = threading.Thread(target=s.serve_forever, daemon=True); t.start()
    try: yield f"http://127.0.0.1:{s.server_port}/{path.name}"
    finally: s.shutdown(); s.server_close(); t.join(timeout=5)

def negative(result: Any) -> bool:
    return isinstance(result, dict) and (any(result.get(k) is False for k in
        ("ok","valid","accepted","imported","success")) or str(result.get("status","")).lower() in
        {"error","invalid","rejected"})

class FixtureOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_or_skip(Draft202012Validator is not None, "DEPENDENCY: jsonschema")
        cls.s, cls.v, cls.l, cls.m = load(SCHEMA), load(VALID), load(LEGACY), load(MISMATCH)
        cls.validator = Draft202012Validator(cls.s)
    def test_schema_and_valid_fixture(self):
        self.assertEqual("learnit.kit.v2", self.s["properties"]["contract"]["const"])
        self.assertFalse(self.s["additionalProperties"])
        self.assertEqual([], [x.message for x in self.validator.iter_errors(self.v)])
    def test_uuid_v4_lowercase_and_digest_shapes(self):
        for x in identity_values(self.v): self.assertRegex(x, UUID4)
        values = [self.v["packageRevisionDigest"]]
        for c in self.v["courses"]:
            values += [c["courseRevisionDigest"], *[a["activityRevisionDigest"] for a in c["activities"]]]
        for x in values: self.assertRegex(x, SHA)
    def test_valid_semantics_and_sha256(self):
        self.assertEqual([], semantic_errors(self.v)); self.assertEqual([], digest_errors(self.v))
    def test_unknown_properties_and_nested_uuid_are_rejected(self):
        paths = [
            lambda x: x.__setitem__("unknown", True),
            lambda x: x["courses"][0].__setitem__("unknown", True),
            lambda x: x["courses"][0]["activities"][0].__setitem__("unknown", True),
            lambda x: x["courses"][0]["activities"][0]["choices"][0].__setitem__("unknown", True),
            lambda x: x["courses"][0]["activities"][1]["tokens"][0].__setitem__("unknown", True),
            lambda x: x["courses"][0]["activities"][0].__setitem__("activityRevisionId", "NOT-A-UUID"),
        ]
        for mutate in paths:
            x = copy.deepcopy(self.v); mutate(x)
            self.assertTrue(list(self.validator.iter_errors(x)))
    def test_semantic_attack_matrix(self):
        attacks = {}
        x=copy.deepcopy(self.v); x["courses"].append(copy.deepcopy(x["courses"][0])); attacks["duplicate course"]=redigest(x)
        x=copy.deepcopy(self.v); x["courses"][0]["activities"].append(copy.deepcopy(x["courses"][0]["activities"][0])); attacks["duplicate activity"]=redigest(x)
        x=copy.deepcopy(self.v); x["courses"][0]["objectives"][1]["objectiveId"]=x["courses"][0]["objectives"][0]["objectiveId"]; attacks["duplicate objective"]=redigest(x)
        x=copy.deepcopy(self.v); x["courses"][0]["activities"][0]["choices"][1]["choiceId"]=x["courses"][0]["activities"][0]["choices"][0]["choiceId"]; attacks["duplicate choice"]=redigest(x)
        x=copy.deepcopy(self.v); f=x["courses"][0]["activities"][1]; f["tokens"].append(copy.deepcopy(f["tokens"][0])); attacks["duplicate token"]=redigest(x)
        x=copy.deepcopy(self.v); f=x["courses"][0]["activities"][1]; f["segments"].append(copy.deepcopy(next(s for s in f["segments"] if "slotId" in s))); attacks["duplicate slot"]=redigest(x)
        x=copy.deepcopy(self.v); x["courses"][0]["activities"][0]["objectiveIds"]=["99999999-9999-4999-8999-999999999999"]; attacks["missing objective"]=redigest(x)
        x=copy.deepcopy(self.v); x["courses"][0]["activities"][0]["correctChoiceId"]="99999999-9999-4999-8999-999999999999"; attacks["missing choice"]=redigest(x)
        x=copy.deepcopy(self.v); x["courses"][0]["activities"][1]["answers"][0]["tokenId"]="99999999-9999-4999-8999-999999999999"; attacks["missing token"]=redigest(x)
        x=copy.deepcopy(self.v); x["courses"][0]["activities"][1]["tokens"][0]["maxUses"]=1; attacks["maxUses"]=redigest(x)
        for name, attack in attacks.items():
            self.assertTrue(semantic_errors(attack), name)
    def test_canonical_json_profile(self):
        self.assertEqual(b'{"a":[true,null,3],"z":"\xc3\xa9","\xc3\xa9":"ok"}', canonical({"z":"e\u0301","a":[True,None,3],"é":"ok"}))
        with self.assertRaises(TypeError): canonical({"x":1.5})
        with self.assertRaises(ValueError): canonical({"é":1,"e\u0301":2})
    def test_legacy_and_digest_mismatch_fixtures(self):
        self.assertEqual("learnit.import.v1.1", self.l["schema_version"])
        self.assertTrue(list(self.validator.iter_errors(self.l)))
        self.assertEqual([], [x.message for x in self.validator.iter_errors(self.m)])
        self.assertTrue(digest_errors(self.m))
    def test_qcm_reordering_keeps_choice_id_semantics(self):
        x=copy.deepcopy(self.v); q=x["courses"][0]["activities"][0]; old=q["activityRevisionDigest"]
        q["choices"].reverse(); self.assertIn(q["correctChoiceId"],[c["choiceId"] for c in q["choices"]]); self.assertNotEqual(old,digest(q,"activityRevisionDigest"))

class RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(os.environ.get("LEARNIT_NEXT_ARTIFACT",ARTIFACT))
        require_or_skip(path.exists(), f"WAITING_FOR_INTEGRATION: {path}")
        require_or_skip(sync_playwright is not None, "DEPENDENCY: Playwright")
        cls.v,cls.l,cls.m=load(VALID),load(LEGACY),load(MISMATCH); cls.server=serve(path); cls.url=cls.server.__enter__()
        cls.pw=sync_playwright().start()
        try: cls.browser=cls.pw.chromium.launch(headless=True)
        except Exception as e:
            cls.pw.stop(); cls.server.__exit__(None,None,None)
            require_or_skip(False, f"DEPENDENCY: Chromium: {e}")
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,"browser"): cls.browser.close()
        if hasattr(cls,"pw"): cls.pw.stop()
        if hasattr(cls,"server"): cls.server.__exit__(None,None,None)
    def setUp(self):
        self.ctx=self.browser.new_context(); self.page=self.ctx.new_page(); self.page.goto(self.url); self.page.wait_for_function("()=>window.__LEARNIT_NEXT_TEST__"); self.call("resetNextData")
    def tearDown(self): self.ctx.close()
    def call(self,op,*args):
        return self.page.evaluate("async x=>{const a=window.__LEARNIT_NEXT_TEST__;if(typeof a[x.op]!=='function')throw Error('missing '+x.op);return await a[x.op](...x.args)}",{"op":op,"args":list(args)})
    def outcome(self,op,*args):
        try:
            r=self.call(op,*args); return not negative(r),r
        except PlaywrightError as e: return False,str(e)
    def reject(self,op,payload):
        ok,r=self.outcome(op,payload); self.assertFalse(ok,r); return r
    def courses(self): return self.call("listCourses")
    def test_contract_version_and_valid_import(self):
        self.assertEqual("learnit.kit.v2",self.page.evaluate("()=>window.__LEARNIT_NEXT_TEST__.contractVersion"))
        self.assertTrue(self.outcome("validatePackage",self.v)[0]); self.assertTrue(self.outcome("importPackage",self.v)[0]); self.assertEqual(1,len(self.courses()))
    def test_schema_uuid_unknown_duplicate_and_reference_attacks(self):
        attacks=[]
        for mutate in (
            lambda x:x.__setitem__("unknown",1),
            lambda x:x["courses"][0].__setitem__("unknown",1),
            lambda x:x.__setitem__("packageLineageId","AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"),
            lambda x:x["courses"][0]["activities"][0]["choices"][1].__setitem__("choiceId",x["courses"][0]["activities"][0]["choices"][0]["choiceId"]),
            lambda x:x["courses"][0]["activities"][1]["tokens"].append(copy.deepcopy(x["courses"][0]["activities"][1]["tokens"][0])),
            lambda x:x["courses"][0]["activities"][1]["answers"][0].__setitem__("tokenId","99999999-9999-4999-8999-999999999999"),
        ):
            a=copy.deepcopy(self.v); mutate(a); attacks.append(redigest(a))
        for a in attacks:self.reject("validatePackage",a)
    def test_digest_mismatch_same_revision_conflict_and_legacy_are_atomic(self):
        before=self.courses(); self.reject("importPackage",self.m); self.reject("importPackage",self.l); self.assertEqual(before,self.courses())
        self.assertTrue(self.outcome("importPackage",self.v)[0]); before=self.courses()
        x=copy.deepcopy(self.v);x["courses"][0]["activities"][0]["prompt"]+=" changed";x=redigest(x)
        self.reject("importPackage",x); self.assertEqual(before,self.courses())
    def test_qcm_choice_reordering_does_not_change_correction(self):
        x=copy.deepcopy(self.v);q=x["courses"][0]["activities"][0];q["choices"].reverse();q["activityRevisionId"]="44444444-4444-4444-8444-444444444449";x["courses"][0]["courseRevisionId"]="22222222-2222-4222-8222-222222222229";x["packageRevisionId"]="11111111-1111-4111-8111-111111111119";x=redigest(x)
        self.assertTrue(self.outcome("importPackage",x)[0]);c=self.courses()[0];self.call("startCourse",c["courseInstallId"]);r=self.call("answer",q["activityRevisionId"],q["correctChoiceId"])
        self.assertIsInstance(r,dict,r); self.assertIs(r.get("correct"),True,r); self.assertIs(r.get("completed"),True,r)
        self.assertEqual(q["correctChoiceId"],r.get("selectedChoiceId"),r)
        self.assertEqual(q["activityRevisionId"],r.get("activityRevisionId"),r)

if __name__ == "__main__": unittest.main(verbosity=2)
