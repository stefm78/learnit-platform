#!/usr/bin/env python3
import copy,importlib.util,json,pathlib,unittest
HERE=pathlib.Path(__file__).resolve();REPO=HERE.parents[3];VAL=REPO/'authoring/v2/atlas/validate_atlas_content.py'
spec=importlib.util.spec_from_file_location('atlas_validator',VAL);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class Content(unittest.TestCase):
 def kits(self):return [json.loads(p.read_text()) for p in v.FILES]
 def test_positive(self):
  for p in self.kits():self.assertTrue(v.validate_package(p))
 def test_exact_shape_and_budgets(self):
  for p in self.kits():
   c=p['courses'][0];self.assertEqual(len(c['objectives']),2);self.assertEqual(len(c['activities']),10);self.assertEqual(len(c['atlasValidationIndependenceClaims']),4)
   for o in c['objectives']:
    a=[x for x in c['activities'] if o['objectiveId'] in x['objectiveIds']];self.assertEqual([v.CLASS[(x['learningPhase'],x['assessmentRole'])] for x in a],['practice','correction','validation','validation','transfer']);self.assertTrue(all(x['estimatedMinutes']<=5 for x in a[:4]))
 def test_negative_missing_duration(self):
  p=self.kits()[0]
  del p['courses'][0]['activities'][0]['estimatedMinutes']
  with self.assertRaises(Exception): v.validate_package(p)
 def test_negative_uuid_order_substitution(self):
  p=self.kits()[0]
  a=p['courses'][0]['activities']; a[0],a[1]=a[1],a[0]
  with self.assertRaisesRegex(Exception,'AUTHOR_ORDER_INVALID'): v.validate_package(p)
 def test_negative_claim_digest(self):
  p=self.kits()[0]
  p['courses'][0]['atlasValidationIndependenceClaims'][0]['targetStimulusDigest']='sha256:'+'0'*64
  with self.assertRaisesRegex(Exception,'STIMULUS_DIGEST_INVALID'): v.validate_package(p)
if __name__=='__main__':unittest.main(verbosity=2)
