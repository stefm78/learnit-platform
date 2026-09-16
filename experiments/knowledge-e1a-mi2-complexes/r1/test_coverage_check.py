#!/usr/bin/env python3
import copy, json, unittest
from coverage_check import check

LEDGER={"items":[
 {"sourceItemId":"t1","scopeRole":"TARGET_COVERAGE","coverageDisposition":"REPRESENTED","knowledgeRefs":["c1"]},
 {"sourceItemId":"ctx","scopeRole":"CONTEXT_ONLY"}]}
KNOWLEDGE={"concepts":[{"id":"c1"}]}

class CoverageCheckTests(unittest.TestCase):
    def test_pass_represented(self):
        self.assertEqual(check(copy.deepcopy(LEDGER),copy.deepcopy(KNOWLEDGE))["result"],"PASS")
    def test_target_without_disposition_fails(self):
        l=copy.deepcopy(LEDGER); l["items"][0].pop("coverageDisposition")
        self.assertIn("TARGET_DISPOSITION_REQUIRED",[e["code"] for e in check(l,KNOWLEDGE)["errors"]])
    def test_dangling_knowledge_ref_fails(self):
        l=copy.deepcopy(LEDGER); l["items"][0]["knowledgeRefs"]=["missing"]
        self.assertIn("KNOWLEDGE_REF_NOT_FOUND",[e["code"] for e in check(l,KNOWLEDGE)["errors"]])
    def test_exclusion_without_reason_fails(self):
        l=copy.deepcopy(LEDGER); l["items"][0]={"sourceItemId":"t1","scopeRole":"TARGET_COVERAGE","coverageDisposition":"EXPLICITLY_EXCLUDED"}
        self.assertIn("EXCLUSION_REASON_REQUIRED",[e["code"] for e in check(l,KNOWLEDGE)["errors"]])
    def test_context_only_is_not_obligation(self):
        l={"items":[{"sourceItemId":"ctx","scopeRole":"CONTEXT_ONLY"}]}
        self.assertEqual(check(l,{"concepts":[]})["result"],"PASS")
    def test_claim_ref_resolves(self):
        l={"items":[{"sourceItemId":"t","scopeRole":"TARGET_COVERAGE","coverageDisposition":"REPRESENTED","knowledgeRefs":["c#p"]}]}
        k={"concepts":[{"id":"c","claims":[{"id":"p"}]}]}
        self.assertEqual(check(l,k)["result"],"PASS")

if __name__=="__main__": unittest.main()
