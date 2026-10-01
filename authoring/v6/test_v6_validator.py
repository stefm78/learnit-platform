#!/usr/bin/env python3
import importlib.util, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("v6_validate",ROOT/"authoring/v6/validate_kit.py")
v6=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(v6)

class V6ValidatorTests(unittest.TestCase):
    def test_validation_slot_and_productive_evaluator_rules(self):
        base={"courses":[{"activities":[{
          "type":"productive","assessmentRole":"validation","objectiveIds":["a","b"],"validationSlot":"A",
          "parts":[{"partId":"p","responseKind":"number"}],
          "scoring":{"evaluators":[{"partId":"p","kind":"required-concepts"}]}
        }]}]}
        errors=v6._v6_errors(base)
        self.assertTrue(any("exactly one objective" in e for e in errors))
        self.assertTrue(any("does not match" in e for e in errors))
    def test_non_validation_slot_rejected(self):
        doc={"courses":[{"activities":[{"type":"qcm","assessmentRole":"practice","objectiveIds":["a"],"validationSlot":"A"}]}]}
        self.assertTrue(any("validation-only" in e for e in v6._v6_errors(doc)))
if __name__=="__main__":unittest.main()
