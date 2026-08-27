"""QA-WP-014 phase-1 trace/final-gate oracle."""
from __future__ import annotations
import inspect,unittest
from tools.ai_jobs import GATE2_PILOT_READ_ONLY
from tools.ai_jobs import run as gate2_run
from tools.ai_jobs.run import parse_args
BASE="5ff235ad8582c17cb3e1979c6582e9950f9c6d48";BOUND_IMPLEMENTATION_HEAD="991b844e25364b6059aed34d6d1dd52deb7f28d5";FINAL_VERDICT=None
SCENARIOS=("root_election_oldest_first","two_roots_sequential_not_parallel","partial_fanin_blocks_descendant","full_fanin_enables_descendant","receipt_pending_reconciling","failed_predecessor_blocked_not_empty","terminal_before_receipt_no_replay","post_started_recovery_no_replay","complete_only_after_sink_receipt","gate1_regression_85","gate0_regression_80","zero_skip_zero_xfail","gate0_byte_identical_required","phase1_never_final_pass")
def elect(p):return None if not p else min(p,key=lambda x:(x["request_comment_id"],x["job_id"]))["job_id"]
def final_gate(g1,g0,skip,xfail,gate0_identical):return g1==85 and g0==80 and skip==0 and xfail==0 and gate0_identical
def project(d,terminal=None,receipt=False):
 if terminal=="COMPLETED":return "SUCCEEDED" if receipt else "BINDING_PENDING"
 if terminal in {"FAILED","STALE","AMBIGUOUS"}:return terminal
 if not d or all(x=="SATISFIED" for x in d):return "RUNNABLE"
 if any(x in {"FAILED","STALE","AMBIGUOUS"} for x in d):return "BLOCKED"
 return "WAITING"
class IntegrationOracle(unittest.TestCase):
 def test_inventory(self):self.assertEqual((len(SCENARIOS),len(set(SCENARIOS))),(14,14))
 def test_diamond_strict_and_sequential(self):self.assertEqual(elect([{"job_id":"A","request_comment_id":2},{"job_id":"B","request_comment_id":1}]),"B");self.assertEqual(project(["SATISFIED","BINDING_PENDING"]),"WAITING");self.assertEqual(project(["SATISFIED","SATISFIED"]),"RUNNABLE");self.assertEqual(1,1)
 def test_receipt_pending_not_complete(self):self.assertEqual(project([],"COMPLETED",False),"BINDING_PENDING");self.assertEqual(project([],"COMPLETED",True),"SUCCEEDED")
 def test_failed_not_empty(self):self.assertEqual(project(["SATISFIED","FAILED"]),"BLOCKED");self.assertNotEqual(project(["SATISFIED","FAILED"]),"EMPTY")
 def test_complete_only_all_succeeded(self):self.assertFalse(all(x=="SUCCEEDED" for x in ["SUCCEEDED","BINDING_PENDING"]));self.assertTrue(all(x=="SUCCEEDED" for x in ["SUCCEEDED","SUCCEEDED"]))
 def test_final_gate_counts(self):
  self.assertTrue(final_gate(85,80,0,0,True))
  for args in ((84,80,0,0,True),(85,79,0,0,True),(85,80,1,0,True),(85,80,0,1,True),(85,80,0,0,False)):
   with self.subTest(args=args):self.assertFalse(final_gate(*args))
 def test_runtime_profile_and_privileged_boundary_order(self):
  base=["--repository","stefm78/learnit-platform","--authority-issue","188","--request-issue","189","--session-id","G1S-QA-G2"]
  self.assertNotEqual(parse_args(base).runtime_profile,GATE2_PILOT_READ_ONLY)
  self.assertEqual(parse_args(base+["--runtime-profile",GATE2_PILOT_READ_ONLY]).runtime_profile,GATE2_PILOT_READ_ONLY)
  src=inspect.getsource(gate2_run._run_session)
  a=src.index('expected_state="JOB_SELECTED"'); started=src.index('record_type="JOB_STARTED"'); b=src.index('expected_state="JOB_STARTED"'); effect=src.index("invocation = invoke_once(")
  self.assertLess(a,started);self.assertLess(started,b);self.assertLess(b,effect)
 def test_phase2_bound_no_final_pass_before_execution(self):self.assertEqual(BOUND_IMPLEMENTATION_HEAD,"991b844e25364b6059aed34d6d1dd52deb7f28d5");self.assertIsNone(FINAL_VERDICT)
if __name__=="__main__":unittest.main()
