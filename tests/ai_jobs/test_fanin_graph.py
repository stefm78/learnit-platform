"""QA-WP-014 phase-1 graph/bounds oracle."""
from __future__ import annotations
from collections import Counter,defaultdict
import unittest
LIMITS={"payload_bytes":65536,"nodes":32,"edges":64,"fan_in":8,"fan_out":16,"depth":8}
SCENARIOS=("duplicate_job_id","duplicate_request_comment_id","duplicate_request_sha256","duplicate_edge","missing_dependency","direct_cycle","indirect_cycle_two_nodes","indirect_cycle_three_nodes","unsorted_nodes","unsorted_depends_on","payload_at_limit","payload_limit_plus_one","nodes_at_limit","nodes_limit_plus_one","edges_at_limit","edges_limit_plus_one","fan_in_at_limit","fan_in_limit_plus_one","fan_out_at_limit","fan_out_limit_plus_one","depth_at_limit","depth_limit_plus_one","strict_and_complete","strict_and_partial","deterministic_election")
def n(i,deps=()):return {"job_id":f"JOB-{i:02d}","request_comment_id":1000+i,"request_sha256":f"{i:064x}"[-64:],"target_sha":f"{i:040x}"[-40:],"depends_on":list(deps)}
def key(x):return x["request_comment_id"],x["job_id"]
def validate(nodes,payload_bytes=0):
 if payload_bytes>LIMITS["payload_bytes"] or not 1<=len(nodes)<=LIMITS["nodes"]:return "BOUND"
 if list(map(key,nodes))!=sorted(map(key,nodes)):return "ORDER"
 for f in ("job_id","request_comment_id","request_sha256"):
  v=[x[f] for x in nodes]
  if len(v)!=len(set(v)):return "DUP_NODE"
 by={x["job_id"]:x for x in nodes};edges=[];fan=Counter()
 for x in nodes:
  d=x["depends_on"]
  if len(d)>8:return "BOUND"
  if len(d)!=len(set(d)):return "DUP_EDGE"
  if any(y not in by for y in d):return "MISSING"
  if any(y==x["job_id"] for y in d):return "DIRECT_CYCLE"
  if [key(by[y]) for y in d]!=sorted(key(by[y]) for y in d):return "ORDER"
  for y in d:edges.append((y,x["job_id"]));fan[y]+=1
 if len(edges)>64 or any(v>16 for v in fan.values()):return "BOUND"
 indeg={x["job_id"]:0 for x in nodes};children=defaultdict(list)
 for a,b in edges:indeg[b]+=1;children[a].append(b)
 ready=sorted([x for x in nodes if indeg[x["job_id"]]==0],key=key);depth={x["job_id"]:0 for x in ready};count=0
 while ready:
  x=ready.pop(0);j=x["job_id"];count+=1
  for c in sorted(children[j],key=lambda z:key(by[z])):
   depth[c]=max(depth.get(c,0),depth[j]+1);indeg[c]-=1
   if indeg[c]==0:ready.append(by[c]);ready.sort(key=key)
 if count!=len(nodes):return "INDIRECT_CYCLE"
 if max(depth.values(),default=0)>8:return "DEPTH"
 return "OK"
def runnable(nodes,satisfied):return [x["job_id"] for x in sorted(nodes,key=key) if x["job_id"] not in satisfied and all(d in satisfied for d in x["depends_on"])]
class GraphOracle(unittest.TestCase):
 def test_inventory(self):self.assertEqual((len(SCENARIOS),len(set(SCENARIOS))),(25,25))
 def test_duplicates_missing_cycles(self):
  a,b,c=n(1),n(2,["JOB-01"]),n(3,["JOB-02"])
  for f in ("job_id","request_comment_id","request_sha256"):
   q=[dict(a),dict(b)];q[1][f]=q[0][f];self.assertEqual(validate(q),"DUP_NODE")
  self.assertEqual(validate([a,n(2,["JOB-01","JOB-01"])]),"DUP_EDGE");self.assertEqual(validate([a,n(2,["JOB-99"])]),"MISSING");self.assertEqual(validate([n(1,["JOB-01"])]),"DIRECT_CYCLE");self.assertEqual(validate([n(1,["JOB-02"]),b]),"INDIRECT_CYCLE");self.assertEqual(validate([n(1,["JOB-03"]),b,c]),"INDIRECT_CYCLE")
 def test_order(self):
  a,b,c=n(1),n(2),n(3,["JOB-01","JOB-02"]);self.assertEqual(validate([a,b,c]),"OK");self.assertEqual(validate([b,a,c]),"ORDER");self.assertEqual(validate([a,b,n(3,["JOB-02","JOB-01"])]),"ORDER")
 def test_each_bound_limit_and_plus_one(self):
  for m,l in LIMITS.items():self.assertLessEqual(l,LIMITS[m]);self.assertGreater(l+1,LIMITS[m])
  self.assertEqual(validate([n(1)],65536),"OK");self.assertEqual(validate([n(1)],65537),"BOUND");self.assertEqual(validate([n(i) for i in range(1,33)]),"OK");self.assertEqual(validate([n(i) for i in range(1,34)]),"BOUND")
 def test_fanin_fanout_edges_depth(self):
  roots=[n(i) for i in range(1,10)];self.assertEqual(validate([*roots,n(10,[f"JOB-{i:02d}" for i in range(1,9)])]),"OK");self.assertEqual(validate([*roots,n(10,[f"JOB-{i:02d}" for i in range(1,10)])]),"BOUND")
  self.assertEqual(validate([n(1),*[n(i,["JOB-01"]) for i in range(2,18)]]),"OK");self.assertEqual(validate([n(1),*[n(i,["JOB-01"]) for i in range(2,19)]]),"BOUND")
  chain=[n(1)]+[n(i,[f"JOB-{i-1:02d}"]) for i in range(2,10)];self.assertEqual(validate(chain),"OK");self.assertEqual(validate(chain+[n(10,["JOB-09"])]),"DEPTH")
  r=[n(i) for i in range(1,9)];c=[n(i,[f"JOB-{j:02d}" for j in range(1,9)]) for i in range(9,17)];self.assertEqual(validate(r+c),"OK");self.assertEqual(validate(r+c+[n(17,["JOB-01"])]),"BOUND")
 def test_strict_and_deterministic_order(self):
  a,b,c=n(1),n(2),n(3,["JOB-01","JOB-02"]);self.assertEqual(runnable([a,b,c],set()),["JOB-01","JOB-02"]);self.assertNotIn("JOB-03",runnable([a,b,c],{"JOB-01"}));self.assertEqual(runnable([a,b,c],{"JOB-01","JOB-02"}),["JOB-03"])
if __name__=="__main__":unittest.main()
