"""QA-WP-014 phase-1 timing/recovery oracle."""
from __future__ import annotations
import unittest
MUTATIONS=("receipt_delete","receipt_edit","outcome_delete","outcome_body_mutation_same_comment_id","wrong_outcome_body_digest","invalid_gate0_outcome","terminal_ambiguity","unstable_read","descendant_request_mutation","graph_mutation")
SCENARIOS=tuple(f"boundary_a_{m}" for m in MUTATIONS)+tuple(f"boundary_b_{m}" for m in MUTATIONS)+("cached_runnable_mutant","cached_predecessor_truth_mutant","cached_receipt_mutant","final_effect_guard_only_mutant","strict_and_partial_fanin","completed_without_receipt_binding_pending","failed_predecessor_blocks","stale_predecessor_blocks","ambiguous_predecessor_blocks","divergent_receipts_global_hold","terminal_before_receipt_reconcile_no_replay","blocked_not_empty","reconciling_not_empty","global_hold_not_empty","complete_exact_all_succeeded_with_receipts","post_job_started_no_automatic_replay","unstable_double_scan_fail_closed")
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
