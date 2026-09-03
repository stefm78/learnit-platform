#!/usr/bin/env python3
"""Independent contradictory QA oracle for QA-WP-027 / issue #348."""
from __future__ import annotations
import copy, io, json, os, sys, tempfile, unittest, zipfile
from pathlib import Path, PureWindowsPath
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
from authoring.factory import factory_gate as factory, handoff, reliability, release_set, source_admission
from authoring.factory import transient_source_admission as transient
FROZEN="723548f6dcc340aa9b4002cf8821f640a851bb2a"
KIT=ROOT/"authoring/v2/atlas/signaux_electriques_atlas.json"

def wj(p,v): p.write_bytes(factory.canonical_json_bytes(v))
def decl(sid="qa.source-01",ver="qa-v1",**kw):
 v={"schema":transient.DECLARATION_SCHEMA,"profile":transient.DECLARATION_PROFILE,"declarationVersion":transient.DECLARATION_VERSION,"sourceId":sid,"version":ver,"provenance":transient.PROVENANCE,"processingContext":transient.PROCESSING_CONTEXT,"authorizationBasis":transient.AUTHORIZATION_BASIS,"userDeclarationAccepted":True,"retention":transient.RETENTION,"redistribution":transient.REDISTRIBUTION,"legalRightsVerified":False}; v.update(kw); return v

def review(ctx,sid,**kw):
 dims={}
 for n in factory.REQUIRED_DIMENSIONS:
  ev=[] if n not in factory.EVIDENCE_REQUIRED_DIMENSIONS else [{"sourceId":sid,"locator":"qa:1","basis":"Independent QA evidence."}]
  dims[n]={"status":"pass","summary":"Independent QA review.","evidence":ev}
 v={"schema":factory.REVIEW_SCHEMA,"profile":factory.REVIEW_PROFILE,"target":handoff.target_from_context(ctx),"independence":{"authorScratchpadSeen":False,"authorActiveContextReused":False},"dimensions":dims,"findings":[],"limitations":[],"verdict":factory.SEMANTIC_PASS}
 for k,x in kw.items():
  if k=="target": v[k].update(x)
  elif k=="independence": v[k].update(x)
  else: v[k]=x
 return v

class Case:
 def __init__(self,root,sid="qa.source-01",ver="qa-v1"):
  self.r=root; self.sid=sid; self.ver=ver; self.kit=root/"kit.json"; self.brief=root/"brief.json"; self.src=root/"src.bin"; self.adm=root/"adm.json"; self.zip=root/"review.zip"; self.rev=root/"review.json"; self.run=root/"run.json"; self.rel=root/"release.zip"
  self.kit.write_bytes(KIT.read_bytes()); wj(self.brief,{"schema":factory.BRIEF_SCHEMA,"audience":"EPF learner","goal":"QA pipeline","language":"fr","timeBudgetMinutes":45}); self.src.write_bytes(b"%PDF-1.7\nqa-wp-027-source\n"); self.bind(sid,ver)
 def bind(self,sid,ver=None):
  self.sid=sid; self.ver=ver or self.ver; rec=transient.build_admission(decl(self.sid,self.ver),self.src); assert rec["decision"]["verdict"]==transient.PASS; wj(self.adm,rec); return rec
 def prep(self): return handoff.prepare_review_bundle(self.kit,self.brief,[f"{self.sid}={self.src}"],[f"{self.sid}={self.adm}"],self.zip)
 def verify(self): return handoff.verify_review_bundle(self.zip)
 def pass_review(self,**kw): v=review(self.verify()["context"],self.sid,**kw); wj(self.rev,v); return v
 def consume(self): return handoff.consume_review_bundle(self.zip,self.rev,self.run)

def zip_members(p):
 with zipfile.ZipFile(p,"r") as z: return {i.filename:z.read(i) for i in z.infolist()}

def benchmark_case(root):
 c=Case(root,"benchmark-binding")
 cat,catsha=source_admission.load_catalog(handoff.CATALOG_PATH)
 row=next(x for x in cat["sources"] if x["benchmarkRole"]=="primary" and x["rights"]["status"] in {"allowed","conditional"} and x["rights"]["thirdPartyContentStatus"]!="present-unresolved" and cat["defaultUseContext"] in x["rights"]["allowedUseContexts"])
 ver=row["version"]["value"] if row["version"]["strategy"]=="fixed" else "qa-v1"
 rec=source_admission.build_admission(cat,catsha,row["sourceId"],cat["defaultUseContext"],c.src,list(row["rights"]["conditions"]),ver); assert rec["decision"]["verdict"]==source_admission.PASS
 wj(c.adm,rec); return c

class QA027(unittest.TestCase):
 def test_00_exact_frozen_head_binding(self): self.assertEqual(FROZEN,os.environ.get("QA_FROZEN_PRODUCT_HEAD"))

 def test_01_historical_grammar_length_and_cross_contract(self):
  missing=Path("/definitely/not/present/qa027")
  with self.assertRaisesRegex(transient.TransientSourceAdmissionError,"sourceId"): transient.build_admission(decl("user:private-course"),missing)
  # create independent cases for accepted boundaries and full M3.3 prepare/verify
  for n in (1,159,160):
   with self.subTest(n=n), tempfile.TemporaryDirectory() as td:
    c=Case(Path(td),"a"*n); self.assertEqual(handoff.PASS_PREPARED,c.prep()["verdict"]); c.verify()
  for n in (0,161,254,255,256,300,512):
   with self.subTest(n=n):
    with self.assertRaises(transient.TransientSourceAdmissionError): transient.build_admission(decl("a"*n),missing)
  with tempfile.TemporaryDirectory() as td:
   c=Case(Path(td),"user.private-course_01"); self.assertEqual(handoff.PASS_PREPARED,c.prep()["verdict"]); c.verify()
  # Search beyond the historical defects: case-distinct IDs must also remain safely
  # materializable by M3.3 on case-insensitive local filesystems.
  self.assertNotEqual("CourseA","coursea")
  self.assertIsNotNone(transient.SOURCE_ID.fullmatch("CourseA"))
  self.assertIsNotNone(transient.SOURCE_ID.fullmatch("coursea"))
  self.assertEqual(PureWindowsPath("CourseA.source"),PureWindowsPath("coursea.source"))

 @unittest.skipUnless(os.name=="nt","actual Windows case-fold materialization proof")
 def test_02_windows_casefold_collision_actual_m3_3(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); kit=root/"kit.json"; brief=root/"brief.json"; out=root/"review.zip"
   kit.write_bytes(KIT.read_bytes()); wj(brief,{"schema":factory.BRIEF_SCHEMA,"audience":"EPF learner","goal":"QA multi-source case-fold collision","language":"fr","timeBudgetMinutes":45})
   source_specs=[]; admission_specs=[]
   for sid,payload in (("CourseA",b"%PDF-1.7\nUPPER\n"),("coursea",b"%PDF-1.7\nlower\n")):
    src=root/(sid+"-input.pdf"); adm=root/(sid+"-admission.json"); src.write_bytes(payload)
    rec=transient.build_admission(decl(sid),src); self.assertEqual(transient.PASS,rec["decision"]["verdict"]); wj(adm,rec)
    source_specs.append(f"{sid}={src}"); admission_specs.append(f"{sid}={adm}")
   result=handoff.prepare_review_bundle(kit,brief,source_specs,admission_specs,out)
   self.assertEqual(handoff.PASS_PREPARED,result["verdict"])
   verified=handoff.verify_review_bundle(out)
   self.assertEqual(["CourseA","coursea"],verified["manifest"]["reviewEvidenceSourceIds"])

 def test_03_pre_ingestion_malformed_and_drift(self):
  with tempfile.TemporaryDirectory() as td:
   src=Path(td)/"source.pdf"; src.write_bytes(b"x")
   for bad in (None,{}, {"sourceId":"x"}):
    with self.assertRaises(transient.TransientSourceAdmissionError): transient.build_admission(bad,src)
  matrix=[({"userDeclarationAccepted":False},transient.HOLD_DECLARATION),({"provenance":"catalog"},transient.HOLD_DECLARATION),({"authorizationBasis":"filename"},transient.HOLD_DECLARATION),({"processingContext":"public"},transient.HOLD_CONTEXT),({"retention":"persistent"},transient.HOLD_RETENTION),({"redistribution":"allowed"},transient.HOLD_REDISTRIBUTION),({"legalRightsVerified":True},transient.HOLD_LEGAL_CLAIM)]
  missing=Path("/definitely/not/present/qa027-policy")
  for patch,expected in matrix:
   rec=transient.build_admission(decl(**patch),missing); self.assertEqual(expected,rec["decision"]["verdict"]); self.assertTrue(rec["preIngestionHold"]); self.assertIsNone(rec["content"])
  for bad in ({"sourceId":"bad space"},{"version":"bad version"}):
   with self.assertRaises(transient.TransientSourceAdmissionError): transient.build_admission(decl(**bad),None)
  v=decl(); del v["sourceId"]
  with self.assertRaises(transient.TransientSourceAdmissionError): transient.build_admission(v,None)
  with tempfile.TemporaryDirectory() as td:
   c=Case(Path(td)); rec=json.loads(c.adm.read_text()); c.src.write_bytes(b"drift")
   with self.assertRaises(transient.TransientSourceAdmissionError): transient.reproduce_admission(rec,c.src)
   with self.assertRaises(handoff.HandoffInputError): c.prep()
  with tempfile.TemporaryDirectory() as td:
   c=Case(Path(td)); rec=json.loads(c.adm.read_text())
   for key,val in (("sourceId","other"),("version","other-v2")):
    x=copy.deepcopy(rec); x["declaration"][key]=val
    with self.assertRaises(transient.TransientSourceAdmissionError): transient.verify_admission(x)

 def test_04_host_relocation_is_deterministic(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   ca,cb=Case(Path(a),"reloc.source"),Case(Path(b),"reloc.source"); ra,rb=ca.prep(),cb.prep(); self.assertEqual(ra["bundleDigest"],rb["bundleDigest"]); self.assertEqual(ca.zip.read_bytes(),cb.zip.read_bytes()); raw=ca.zip.read_bytes().decode("latin1"); self.assertNotIn(a,raw); self.assertNotIn(b,raw)

 def test_05_authority_separation_and_catalog_rules(self):
  with tempfile.TemporaryDirectory() as td:
   t=Case(Path(td)); t.prep(); tv=t.verify(); self.assertNotIn(handoff.OPTIONAL_ROLE_PATHS["source-catalog"],tv["members"])
   fake=json.loads(t.adm.read_text()); fake["schema"]=source_admission.ADMISSION_SCHEMA; wj(t.adm,fake)
   with self.assertRaises(handoff.HandoffInputError): t.prep()
  with tempfile.TemporaryDirectory() as td:
   b=benchmark_case(Path(td)); b.prep(); bv=b.verify(); self.assertEqual(handoff.CATALOG_PATH.read_bytes(),bv["members"][handoff.OPTIONAL_ROLE_PATHS["source-catalog"]])
  with tempfile.TemporaryDirectory() as td:
   t=Case(Path(td)); t.prep(); m=zip_members(t.zip); mf=json.loads(m["review-handoff.json"]); cp=handoff.OPTIONAL_ROLE_PATHS["source-catalog"]; cr=handoff.CATALOG_PATH.read_bytes(); m[cp]=cr; mf["artifacts"].append(handoff.artifact("source-catalog",cp,cr)); mf["artifacts"]=sorted(mf["artifacts"],key=lambda x:x["path"]); mf["bundleDigest"]=handoff.digest({k:v for k,v in mf.items() if k!="bundleDigest"}); m["review-handoff.json"]=handoff.canonical(mf); p=Path(td)/"injected.zip"; p.write_bytes(handoff.zip_bytes(m))
   with self.assertRaisesRegex(handoff.HandoffInputError,"forbidden"): handoff.verify_review_bundle(p)

 def test_06_archive_and_review_fail_closed(self):
  with tempfile.TemporaryDirectory() as td:
   c=Case(Path(td)); c.prep(); base=zip_members(c.zip)
   for label,mut in (("tamper",lambda m:m.__setitem__("candidate.json",m["candidate.json"]+b"\n")),("extra",lambda m:m.__setitem__("extra.txt",b"x"))):
    m=dict(base); mut(m); p=Path(td)/(label+".zip"); p.write_bytes(handoff.zip_bytes(m));
    with self.assertRaises(handoff.HandoffInputError): handoff.verify_review_bundle(p)
   raw=io.BytesIO()
   with zipfile.ZipFile(raw,"w",compression=zipfile.ZIP_STORED) as z:
    for name,data in sorted(base.items()):
     i=zipfile.ZipInfo(name,handoff.FIXED_ZIP_TIME); i.compress_type=zipfile.ZIP_STORED; i.create_system=3; i.external_attr=handoff.FILE_MODE<<16; z.writestr(i,data)
    i=zipfile.ZipInfo("../escape",handoff.FIXED_ZIP_TIME); i.compress_type=zipfile.ZIP_STORED; i.create_system=3; i.external_attr=handoff.FILE_MODE<<16; z.writestr(i,b"x")
   p=Path(td)/"unsafe.zip"; p.write_bytes(raw.getvalue())
   with self.assertRaises(handoff.HandoffInputError): handoff.verify_review_bundle(p)
   raw=io.BytesIO()
   with zipfile.ZipFile(raw,"w",compression=zipfile.ZIP_STORED) as z:
    rows=list(sorted(base.items()))+[list(sorted(base.items()))[0]]
    for name,data in rows:
     i=zipfile.ZipInfo(name,handoff.FIXED_ZIP_TIME); i.compress_type=zipfile.ZIP_STORED; i.create_system=3; i.external_attr=handoff.FILE_MODE<<16; z.writestr(i,data)
   p=Path(td)/"dup.zip"; p.write_bytes(raw.getvalue())
   with self.assertRaises(handoff.HandoffInputError): handoff.verify_review_bundle(p)
   attacks=[{"target":{"kitSha256":"sha256:"+"0"*64}},{"independence":{"authorScratchpadSeen":True}},{"independence":{"authorActiveContextReused":True}}]
   for a in attacks:
    c.pass_review(**a)
    with self.assertRaises(handoff.HandoffInputError): c.consume()
   v=c.pass_review(); v["dimensions"]["sourceFidelity"]["evidence"][0]["sourceId"]="injected"; wj(c.rev,v)
   with self.assertRaises(handoff.HandoffInputError): c.consume()

 def test_07_factoryrun_release_boundary_and_static_isolation(self):
  with tempfile.TemporaryDirectory() as td:
   c=Case(Path(td),"release.source"); c.prep(); exact=c.src.read_bytes(); self.assertIn(exact,c.verify()["members"].values()); c.pass_review(); self.assertEqual(handoff.PASS_CONSUMED,c.consume()["verdict"]); run=json.loads(c.run.read_text()); reliability.verify_run(run); self.assertEqual("PASS_AI_KIT_FACTORY_V1",run["decision"]["verdict"]); res=release_set.build_release_archive([f"{c.run}={c.kit}"],c.rel); self.assertEqual(release_set.PASS_BUILT,res["verdict"]); out=release_set.verify_release_archive(c.rel); self.assertFalse(any(n.startswith("sources/") for n in out["members"])); self.assertNotIn(exact,out["raw"])
  text="\n".join((ROOT/p).read_text(encoding="utf-8").lower() for p in ("authoring/factory/transient_source_admission.py","authoring/factory/handoff.py")); forbidden=("requests.","urllib.request","http.client","socket.","openai","anthropic","sqlite3","shelve","source_store","persistent_source"); self.assertEqual([], [x for x in forbidden if x in text])
  t=(ROOT/"authoring/factory/transient_source_admission.py").read_text(encoding="utf-8"); self.assertNotIn("apps.learnit",t); self.assertNotIn("contracts",t); self.assertNotIn("authoring.v2",t)

if __name__=="__main__": unittest.main(verbosity=2)
