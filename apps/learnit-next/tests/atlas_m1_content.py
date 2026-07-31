#!/usr/bin/env python3
import copy,importlib.util,json,pathlib,unittest
HERE=pathlib.Path(__file__).resolve();REPO=HERE.parents[3];VAL=REPO/'authoring/v2/atlas/validate_atlas_content.py'
spec=importlib.util.spec_from_file_location('atlas_validator',VAL);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class Content(unittest.TestCase):
 def kits(self):return [json.loads(p.read_text()) for p in v.FILES]
 def test_positive(self):self.assertTrue(v.validate_packages(self.kits()))
 def test_digest_semantics(self):
  kits=self.kits();q=next(a for a in kits[0]['courses'][0]['activities'] if a['type']=='qcm');f=next(a for a in kits[0]['courses'][0]['activities'] if a['type']=='fill')
  changed=copy.deepcopy(q);changed['correctChoiceId']=next(x['choiceId'] for x in changed['choices'] if x['choiceId']!=changed['correctChoiceId']);self.assertNotEqual(v.stimulus(q),v.stimulus(changed))
  mapped=copy.deepcopy(f);mapped['answers'][0]['tokenId']=next(x['tokenId'] for x in mapped['tokens'] if x['tokenId']!=mapped['answers'][0]['tokenId']);self.assertNotEqual(v.stimulus(f),v.stimulus(mapped))
  technical=copy.deepcopy(f);technical['segments'][1]['slotId']='replacement-slot';technical['answers'][0]['slotId']='replacement-slot';self.assertEqual(v.stimulus(f),v.stimulus(technical))
  nfd=copy.deepcopy(q);nfd['prompt']=q['prompt'].replace('é','e\u0301');self.assertEqual(v.stimulus(q),v.stimulus(nfd))
 def test_claim_relations_and_global_uniqueness(self):
  kits=self.kits();bad=copy.deepcopy(kits);claim=bad[0]['courses'][0]['atlasValidationIndependenceClaims'][0];claim['objectiveId']=bad[0]['courses'][0]['objectives'][1]['objectiveId']
  with self.assertRaisesRegex(Exception,'CLAIM_OBJECTIVE_ACTIVITY_MISMATCH'):v.validate_packages(bad)
  duplicate=copy.deepcopy(kits);duplicate[1]['courses'][0]['atlasValidationIndependenceClaims'][0]['claimId']=duplicate[0]['courses'][0]['atlasValidationIndependenceClaims'][0]['claimId']
  with self.assertRaises(Exception):v.validate_packages(duplicate)
 def test_negative_duration_order_and_stale_digest(self):
  p=self.kits()[0];del p['courses'][0]['activities'][0]['estimatedMinutes']
  with self.assertRaises(Exception):v.validate_package(p)
  p=self.kits()[0];a=p['courses'][0]['activities'];a[0],a[1]=a[1],a[0]
  with self.assertRaisesRegex(Exception,'AUTHOR_ORDER_INVALID'):v.validate_package(p)
  p=self.kits()[0];p['courses'][0]['atlasValidationIndependenceClaims'][0]['targetStimulusDigest']='sha256:'+'0'*64
  with self.assertRaisesRegex(Exception,'STIMULUS_DIGEST_INVALID'):v.validate_package(p)
if __name__=='__main__':unittest.main(verbosity=2)
