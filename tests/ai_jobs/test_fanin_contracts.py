"""QA-WP-014 phase-1 contract oracle. No OPS-WP-009 runtime import by design."""
from __future__ import annotations
import hashlib,json,re,unicodedata,unittest
from typing import Any
GRAPH_MARKER="AI_GATE2_FANIN_V1"; GRAPH_SCHEMA="learnit.gate2.fanin.v1"
SHA40=re.compile(r"^[0-9a-f]{40}$"); SHA64=re.compile(r"^[0-9a-f]{64}$")
SCOPE={"repository":"stefm78/learnit-platform","authority_issue":189,"request_issue":188,"session_id":"G1S-QA-GATE2","generation":1,"session_grant_comment_id":7001,"session_grant_digest":"a"*64}
SCENARIOS=("malformed_envelope","malformed_json","duplicate_json_key","float_forbidden","nan_forbidden","non_nfc_string","noncanonical_json","payload_digest_mismatch","edited_graph_comment","wrong_graph_author","wrong_repository","wrong_authority_issue","wrong_request_issue","wrong_session","wrong_generation","wrong_grant_comment","wrong_grant_digest","weak_job_id_only_identity","weak_missing_request_comment","weak_missing_request_digest","weak_missing_target_sha","receipt_comment_edited","receipt_author_mismatch","receipt_wrong_body_digest","receipt_invalid_gate0_outcome","receipt_terminal_mismatch","source_request_mutation")
def _pairs(pairs):
 d={}
 for k,v in pairs:
  if k in d: raise ValueError("duplicate")
  d[k]=v
 return d
def _nfc(v:Any)->Any:
 if v is None or type(v) in {bool,int}: return v
 if type(v) is float: raise ValueError("float")
 if isinstance(v,str):
  if unicodedata.normalize("NFC",v)!=v: raise ValueError("nfc")
  return v
 if isinstance(v,list): return [_nfc(x) for x in v]
 if isinstance(v,dict): return {k:_nfc(x) for k,x in v.items()}
 raise ValueError("type")
def loads_closed(s:str)->Any:
 try:return _nfc(json.loads(s,object_pairs_hook=_pairs,parse_float=lambda x:(_ for _ in()).throw(ValueError("float")),parse_constant=lambda x:(_ for _ in()).throw(ValueError("const"))))
 except json.JSONDecodeError as e: raise ValueError("json") from e
def canon(v:Any)->bytes:return json.dumps(_nfc(v),sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def envelope(payload:dict[str,Any])->str:
 p=canon(payload).decode(); return f"{GRAPH_MARKER}\npayload_sha256: {hashlib.sha256(p.encode()).hexdigest()}\n```json\n{p}\n```"
def parse_envelope(body:str)->dict[str,Any]:
 l=body.splitlines()
 if len(l)!=5 or l[0]!=GRAPH_MARKER or l[2]!="```json" or l[4]!="```" or not l[1].startswith("payload_sha256: "): raise ValueError("envelope")
 p=loads_closed(l[3]); claimed=l[1].split(": ",1)[1]
 if not isinstance(p,dict) or canon(p).decode()!=l[3] or SHA64.fullmatch(claimed) is None or hashlib.sha256(l[3].encode()).hexdigest()!=claimed: raise ValueError("canonical/digest")
 return p
def node_ref(v:dict[str,Any]):
 if set(v)!={"job_id","request_comment_id","request_sha256","target_sha"}: raise ValueError("weak")
 if not isinstance(v["job_id"],str) or type(v["request_comment_id"]) is not int or v["request_comment_id"]<=0 or SHA64.fullmatch(v["request_sha256"]) is None or SHA40.fullmatch(v["target_sha"]) is None: raise ValueError("identity")
 return tuple(v[k] for k in ("job_id","request_comment_id","request_sha256","target_sha"))
def truth(**k):
 t=k["terminal"]
 if t!="COMPLETED": return t if t in {"FAILED","STALE","AMBIGUOUS"} else "INVALIDATED"
 if not k["terminal_unique"]: return "AMBIGUOUS"
 if not k["receipt_present"]: return "BINDING_PENDING"
 if k["receipt_edited"] or not k["receipt_author_ok"] or not k["terminal_matches"] or not k["outcome_present"] or k["outcome_edited"] or not k["gate0_inner_valid"] or not k["source_unchanged"] or k["outcome_digest"]!=k["bound_digest"]: return "INVALIDATED"
 return "SATISFIED"
class ContractOracle(unittest.TestCase):
 def payload(self): return {**SCOPE,"schema_version":GRAPH_SCHEMA,"graph_id":"G2D-QA014","nodes":[]}
 def test_inventory(self): self.assertEqual((len(SCENARIOS),len(set(SCENARIOS))),(27,27))
 def test_closed_json(self):
  for s in ('{"x":','{"x":1,"x":2}','{"x":1.5}','{"x":NaN}','{"x":"e\\u0301"}'):
   with self.subTest(s=s),self.assertRaises(ValueError): loads_closed(s)
 def test_envelope(self):
  p=self.payload(); self.assertEqual(parse_envelope(envelope(p)),p)
  good=envelope(p)
  for bad in ("junk\n"+good,good.replace("payload_sha256: ","payload_sha256: "+"0"*64,1),good.replace(canon(p).decode(),'{"z":0,"a":1}')):
   with self.subTest(),self.assertRaises(ValueError): parse_envelope(bad)
 def test_scope_author_grant(self):
  p=self.payload();self.assertTrue(authority_ok(p,SCOPE,"t","t","grantor","grantor"))
  for f,w in (("repository","x/y"),("authority_issue",1),("request_issue",1),("session_id","G1S-X"),("generation",2),("session_grant_comment_id",2),("session_grant_digest","b"*64)):
   q=dict(p);q[f]=w
   with self.subTest(f=f),self.assertRaises(ValueError):authority_ok(q,SCOPE,"t","t","grantor","grantor")
  with self.assertRaises(ValueError):authority_ok(p,SCOPE,"t","u","grantor","grantor")
  with self.assertRaises(ValueError):authority_ok(p,SCOPE,"t","t","attacker","grantor")
 def test_strong_identity(self):
  r={"job_id":"JOB-A","request_comment_id":1,"request_sha256":"b"*64,"target_sha":"c"*40}; self.assertEqual(len(node_ref(r)),4)
  for f in tuple(r):
   q=dict(r);del q[f]
   with self.subTest(f=f),self.assertRaises(ValueError): node_ref(q)
 def test_current_dependency_truth(self):
  b=dict(terminal="COMPLETED",terminal_unique=True,receipt_present=True,receipt_edited=False,receipt_author_ok=True,terminal_matches=True,outcome_present=True,outcome_edited=False,gate0_inner_valid=True,source_unchanged=True,outcome_digest="d"*64,bound_digest="d"*64)
  self.assertEqual(truth(**b),"SATISFIED")
  for f,w,e in (("receipt_present",False,"BINDING_PENDING"),("receipt_edited",True,"INVALIDATED"),("receipt_author_ok",False,"INVALIDATED"),("terminal_unique",False,"AMBIGUOUS"),("terminal_matches",False,"INVALIDATED"),("outcome_present",False,"INVALIDATED"),("outcome_edited",True,"INVALIDATED"),("gate0_inner_valid",False,"INVALIDATED"),("source_unchanged",False,"INVALIDATED"),("outcome_digest","e"*64,"INVALIDATED")):
   q=dict(b);q[f]=w
   with self.subTest(f=f): self.assertEqual(truth(**q),e)
 def test_bad_terminals_never_satisfy(self):
  b=dict(terminal_unique=True,receipt_present=True,receipt_edited=False,receipt_author_ok=True,terminal_matches=True,outcome_present=True,outcome_edited=False,gate0_inner_valid=True,source_unchanged=True,outcome_digest="d"*64,bound_digest="d"*64)
  for t in ("FAILED","STALE","AMBIGUOUS"): self.assertNotEqual(truth(terminal=t,**b),"SATISFIED")
if __name__=="__main__":unittest.main()
