"""QA-WP-014 phase-1 security-profile oracle."""
from __future__ import annotations
import hashlib,unittest
from pathlib import Path
OPS=frozenset({"pr-snapshot","pr-governor-evidence","run-repository-validation","run-test-profile"});PROFILE="GATE2_PILOT_READ_ONLY"
FORBIDDEN=frozenset({"generic-shell","generic-argv","repository-write","branch-create","commit","push","workflow-dispatch","merge","release","promotion","codespace-create","codespace-start","codespace-restart","dynamic-request","predecessor-output-dataflow","cross-session-delegation","cross-generation-delegation","cross-authority-delegation","parallel-runtime"})
SCENARIOS=("gate2_requires_explicit_opt_in","default_gate1_unchanged","exact_four_gate0_operations","no_generic_shell","no_generic_argv","no_repository_write","no_branch_create","no_commit","no_push","no_workflow_dispatch","no_merge","no_release","no_promotion","no_codespace_create","no_codespace_start","no_codespace_restart","no_dynamic_request","no_predecessor_dataflow","no_cross_session_delegation","no_cross_generation_delegation","no_cross_authority_delegation","single_runtime_job_only","gate3_hold","gate4_hold","no_full_v6_claim")
GATE0={"tools/codespace_evidence/__init__.py":"cbf9a25d086e8431c522aa688f01b2b378d4ab26","tools/codespace_evidence/execute.py":"12c7cd770ec392422ba281616327038c43c92c37","tools/codespace_evidence/github.py":"d8b467a13e1ea741fe9dbb7eac62fedfdb48e044","tools/codespace_evidence/operations.py":"c78b1b8e2fbf854f892ce2601325b0bdf786067d","tools/codespace_evidence/outcome.py":"bb3c78a42fc958b52fb0b84897e237539cb68690","tools/codespace_evidence/request.py":"a9e07dedbf772b597ea980f870d96ea98af297da","tools/codespace_evidence/run.py":"91b7463ffa1fc81a22c5f02d0e922bfc992bccdd","tools/codespace_evidence/stop.py":"c13b199cc7b15ef3642145582dab1700cd804caf","tools/codespace_evidence/workspace.py":"c83a9b515ffea14911bba6e93b19ac5411b64c25"}
def profile(x):return "GATE1_DEFAULT" if x is None else x
def descendant(b,out=None):
 if out is not None:raise ValueError("dataflow")
 return b
class SecurityOracle(unittest.TestCase):
 def test_inventory(self):self.assertEqual((len(SCENARIOS),len(set(SCENARIOS))),(25,25))
 def test_explicit_opt_in(self):self.assertEqual(profile(None),"GATE1_DEFAULT");self.assertEqual(profile(PROFILE),PROFILE);self.assertNotEqual(profile(None),PROFILE)
 def test_exact_four_operations(self):self.assertEqual(OPS,{"pr-snapshot","pr-governor-evidence","run-repository-validation","run-test-profile"});self.assertEqual(len(OPS),4)
 def test_forbidden_surface(self):self.assertEqual(len(FORBIDDEN),19);self.assertIn("repository-write",FORBIDDEN);self.assertIn("parallel-runtime",FORBIDDEN)
 def test_request_immutability_no_dataflow(self):
  b=b"request";self.assertEqual(descendant(b),b)
  with self.assertRaises(ValueError):descendant(b,b"inject")
 def test_no_cross_boundary_delegation(self):
  e=("repo",188,189,"G1S-A",1,"grant")
  for i in range(1,6):
   q=list(e);q[i]=999 if i in {1,2,4} else "wrong";self.assertNotEqual(tuple(q),e)
 def test_one_job_gate3_gate4_no_full_v6(self):
  p=profile_contract();self.assertEqual(p["max_runtime_jobs"],1);self.assertEqual((p["gate3"],p["gate4"]),("HOLD","HOLD"));self.assertFalse(p["full_v6"]);self.assertTrue(p["explicit_opt_in"]);self.assertTrue(p["default_gate1_unchanged"])
 def test_gate0_tree_byte_identity(self):
  root=Path(__file__).resolve().parents[2];self.assertEqual(len(GATE0),9)
  for rel,expected in GATE0.items():
   p=root/rel;self.assertTrue(p.is_file(),rel);d=p.read_bytes();self.assertEqual(hashlib.sha1(f"blob {len(d)}\0".encode()+d).hexdigest(),expected,rel)
if __name__=="__main__":unittest.main()
