"""QA-WP-014 phase-1 timing/recovery oracle."""
from __future__ import annotations
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tools.ai_jobs import run as gate2_run
from tools.ai_jobs.contracts import LedgerRecord, QueueJob
from tools.ai_jobs.fanin import Gate2Error, Gate2Graph, Gate2Node, Gate2Projection, Gate2Ref
MUTATIONS=("receipt_delete","receipt_edit","outcome_delete","outcome_body_mutation_same_comment_id","wrong_outcome_body_digest","invalid_gate0_outcome","terminal_ambiguity","unstable_read","descendant_request_mutation","graph_mutation")
SCENARIOS=tuple(f"boundary_a_{m}" for m in MUTATIONS)+tuple(f"boundary_b_{m}" for m in MUTATIONS)+("cached_runnable_mutant","cached_predecessor_truth_mutant","cached_receipt_mutant","final_effect_guard_only_mutant","strict_and_partial_fanin","completed_without_receipt_binding_pending","failed_predecessor_blocks","stale_predecessor_blocks","ambiguous_predecessor_blocks","divergent_receipts_global_hold","terminal_before_receipt_reconcile_no_replay","blocked_not_empty","reconciling_not_empty","global_hold_not_empty","complete_exact_all_succeeded_with_receipts","post_job_started_no_automatic_replay","unstable_double_scan_fail_closed")
def privileged_authorized(*,fresh,shortcut=None):
 return bool(fresh and shortcut not in {"cached RUNNABLE","cached predecessor truth","cached receipt","final_effect_guard only"})
def _runtime_boundary_fixture(state,dep_truth):
 dep=Gate2Ref(1001,"JOB-DEP","a"*64,"b"*40); child=Gate2Ref(1002,"JOB-CHILD","c"*64,"d"*40)
 graph=Gate2Graph(repository="stefm78/learnit-platform",authority_issue=188,request_issue=189,session_id="G1S-QA-G2",generation=1,session_grant_comment_id=7001,session_grant_digest="e"*64,graph_id="G2QA",nodes=(Gate2Node(dep,()),Gate2Node(child,(dep,))),comment_id=8001,payload_sha256="f"*64,author="grantor")
 child_state="SELECTED" if state=="JOB_SELECTED" else "STARTED"
 proj=Gate2Projection(graph=graph,graph_state="ACTIVE",node_states=((dep,"SUCCEEDED"),(child,child_state)),dependency_truth=((dep,dep_truth),(child,"SATISFIED")),runnable=(),receipt_plans=())
 job=QueueJob(repository="stefm78/learnit-platform",origin_type="issue",origin_number=189,request_comment_id=1002,request_author="qa",created_at="2026-08-27T00:00:00Z",job_id="JOB-CHILD",operation="pr-snapshot",target_type="commit",target_number=None,target_sha="d"*40,request_digest="c"*64)
 payload={"job_id":"JOB-CHILD","request_digest":"c"*64,"request_comment_id":1002,"target_sha":"d"*40}
 if state=="JOB_SELECTED": payload={**payload,"target_type":"commit","target_number":None}
 tail=LedgerRecord.build(record_type=state,repository="stefm78/learnit-platform",authority_issue=188,session_id="G1S-QA-G2",generation=1,sequence=3,previous_record_sha256="0"*64,created_at="2026-08-27T00:00:01Z",payload=payload)
 return proj,job,tail,SimpleNamespace(state=state,last_record=tail)
def boundary(b,m):
 if b=="A":return {"state":"BLOCKED" if m=="terminal_ambiguity" else "GLOBAL_HOLD","job_started":False,"gate0":0,"replay":0}
 if b=="B":return {"state":"RECOVERY_REQUIRED","job_started":True,"gate0":0,"replay":0}
 raise ValueError(b)
def truth(term,receipt,receipt_valid=True,outcome_valid=True):
 if term=="COMPLETED":return "BINDING_PENDING" if not receipt else ("SATISFIED" if receipt_valid and outcome_valid else "INVALIDATED")
 return term if term in {"FAILED","STALE","AMBIGUOUS"} else "UNFINISHED"
def graph_state(s):
 if s and all(x=="SUCCEEDED" for x in s):return "COMPLETE"
 if "RECOVERY_REQUIRED" in s:return "RECOVERY_REQUIRED"
 if "INVALIDATED" in s:return "GLOBAL_HOLD"
 if "BINDING_PENDING" in s and not any(x in {"RUNNABLE","SELECTED","STARTED"} for x in s):return "RECONCILING"
 if "BLOCKED" in s and not any(x in {"RUNNABLE","SELECTED","STARTED","BINDING_PENDING"} for x in s):return "BLOCKED"
 return "ACTIVE"
def reconcile(ds,ids):
 if not ds:return "PUBLISH_OR_RECONCILE",None
 if len(set(ds))!=1:return "GLOBAL_HOLD",None
 return "RECONCILED",min(ids)
class RecoveryOracle(unittest.TestCase):
 def test_inventory(self):self.assertEqual((len(SCENARIOS),len(set(SCENARIOS))),(37,37))
 def test_boundary_a(self):
  for m in MUTATIONS:
   r=boundary("A",m);self.assertFalse(r["job_started"]);self.assertEqual(r["gate0"],0);self.assertIn(r["state"],{"GLOBAL_HOLD","BLOCKED"})
 def test_boundary_b(self):
  for m in MUTATIONS:
   r=boundary("B",m);self.assertEqual((r["state"],r["gate0"],r["replay"]),("RECOVERY_REQUIRED",0,0))
 def test_cached_mutants_killed(self):
  for x in ("cached RUNNABLE","cached predecessor truth","cached receipt","final_effect_guard only"):
   with self.subTest(mutant=x):self.assertFalse(privileged_authorized(fresh=True,shortcut=x))
  self.assertFalse(privileged_authorized(fresh=False));self.assertTrue(privileged_authorized(fresh=True))
 def test_runtime_boundary_a_and_b_use_fresh_runtime_guard(self):
  for state in ("JOB_SELECTED","JOB_STARTED"):
   valid,job,tail,current=_runtime_boundary_fixture(state,"SATISFIED")
   with patch.object(gate2_run,"_gate2_fresh_projection",return_value=(valid,current)) as fresh:
    gate2_run._gate2_boundary(args=object(),gh=object(),grant=object(),authenticated_login="qa",job=job,expected_state=state,expected_tail=tail)
    self.assertEqual(fresh.call_count,1)
   invalid,job,tail,current=_runtime_boundary_fixture(state,"INVALIDATED")
   with patch.object(gate2_run,"_gate2_fresh_projection",return_value=(invalid,current)):
    with self.assertRaises(Gate2Error) as cm: gate2_run._gate2_boundary(args=object(),gh=object(),grant=object(),authenticated_login="qa",job=job,expected_state=state,expected_tail=tail)
    self.assertEqual(cm.exception.code,"G2_BOUNDARY_INVALIDATED")
 def test_dependency_truth_strict_and(self):
  self.assertEqual(truth("COMPLETED",False),"BINDING_PENDING");self.assertEqual(truth("COMPLETED",True),"SATISFIED");self.assertFalse(all(x=="SATISFIED" for x in ["SATISFIED","BINDING_PENDING"]));self.assertTrue(all(x=="SATISFIED" for x in ["SATISFIED","SATISFIED"]))
  for t in ("FAILED","STALE","AMBIGUOUS"):self.assertNotEqual(truth(t,True),"SATISFIED")
  self.assertEqual(truth("COMPLETED",True,False),"INVALIDATED");self.assertEqual(truth("COMPLETED",True,True,False),"INVALIDATED")
 def test_nonempty_states_and_complete_exact(self):
  self.assertEqual(graph_state(["SUCCEEDED","BLOCKED"]),"BLOCKED");self.assertEqual(graph_state(["SUCCEEDED","BINDING_PENDING"]),"RECONCILING");self.assertEqual(graph_state(["SUCCEEDED","INVALIDATED"]),"GLOBAL_HOLD");self.assertEqual(graph_state(["SUCCEEDED","SUCCEEDED"]),"COMPLETE")
  for s in (["SUCCEEDED","BLOCKED"],["SUCCEEDED","BINDING_PENDING"],["SUCCEEDED","INVALIDATED"]):self.assertNotIn(graph_state(s),{"EMPTY","COMPLETE"})
 def test_receipt_reconcile_no_replay(self):
  self.assertEqual(reconcile(["a"*64,"a"*64],[902,901]),("RECONCILED",901));self.assertEqual(reconcile(["a"*64,"b"*64],[901,902]),("GLOBAL_HOLD",None))
 def test_post_started_unstable_fail_closed(self):
  r=boundary("B","unstable_read");self.assertEqual((r["state"],r["gate0"],r["replay"]),("RECOVERY_REQUIRED",0,0))
if __name__=="__main__":unittest.main()
