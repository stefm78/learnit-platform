#!/usr/bin/env python3
import copy,importlib.util,json,pathlib,unittest
HERE=pathlib.Path(__file__).resolve();REPO=HERE.parents[3];VAL=REPO/'authoring/v2/atlas/validate_atlas_content.py'
spec=importlib.util.spec_from_file_location('atlas_validator',VAL);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class Content(unittest.TestCase):
 def raw_kits(self):return [json.loads(p.read_text(encoding='utf-8')) for p in v.FILES]
 def kits(self):return [v.rewrite_claims(copy.deepcopy(p)) for p in self.raw_kits()]
 def repeated_fill(self,max_uses):
  p=self.kits()[0];f=next(a for a in p['courses'][0]['activities'] if a['type']=='fill');token_id=f['answers'][0]['tokenId'];slot_id='11111111-1111-4111-8111-111111111111'
  f['segments'][-1:-1]=[{'text':' puis '},{'slotId':slot_id}];f['answers'].append({'slotId':slot_id,'tokenId':token_id});next(t for t in f['tokens'] if t['tokenId']==token_id)['maxUses']=max_uses
  return p,f
 def test_disk_claims_are_current(self):
  raw=self.raw_kits();rewritten=[v.rewrite_claims(copy.deepcopy(p)) for p in raw];self.assertEqual(raw,rewritten)
 def test_positive(self):self.assertTrue(v.validate_packages(self.kits()))
 def test_digest_semantics(self):
  kits=self.kits();q=next(a for a in kits[0]['courses'][0]['activities'] if a['type']=='qcm');f=next(a for a in kits[0]['courses'][0]['activities'] if a['type']=='fill')
  changed=copy.deepcopy(q);changed['correctChoiceId']=next(x['choiceId'] for x in changed['choices'] if x['choiceId']!=changed['correctChoiceId']);self.assertNotEqual(v.stimulus(q),v.stimulus(changed))
  mapped=copy.deepcopy(f);mapped['answers'][0]['tokenId']=next(x['tokenId'] for x in mapped['tokens'] if x['tokenId']!=mapped['answers'][0]['tokenId']);self.assertNotEqual(v.stimulus(f),v.stimulus(mapped))
  technical=copy.deepcopy(f);technical['segments'][1]['slotId']='replacement-slot';technical['answers'][0]['slotId']='replacement-slot';self.assertEqual(v.stimulus(f),v.stimulus(technical))
  nfd=copy.deepcopy(q);nfd['prompt']=q['prompt'].replace('é','e\u0301');self.assertEqual(v.stimulus(q),v.stimulus(nfd))
  permuted=copy.deepcopy(f);permuted['tokens'].reverse();self.assertEqual(v.stimulus(f),v.stimulus(permuted))
 def test_fill_max_uses_semantics_and_feasibility(self):
  original=next(a for a in self.kits()[0]['courses'][0]['activities'] if a['type']=='fill');changed=copy.deepcopy(original);changed['tokens'][0]['maxUses']=2;self.assertNotEqual(v.stimulus(original),v.stimulus(changed))
  invalid,_=self.repeated_fill(1)
  with self.assertRaisesRegex(Exception,'FILL_TOKEN_MAX_USES_EXCEEDED'):v.validate_package(invalid)
  valid,_=self.repeated_fill(2);v.rewrite_claims(valid);self.assertTrue(v.validate_package(valid))
 def test_fill_max_uses_fail_closed(self):
  f=next(a for a in self.kits()[0]['courses'][0]['activities'] if a['type']=='fill');missing=copy.deepcopy(f);del missing['tokens'][0]['maxUses']
  with self.assertRaisesRegex(Exception,'FILL_TOKEN_MAX_USES_INVALID'):v.stimulus(missing)
  invalid=copy.deepcopy(f);invalid['tokens'][0]['maxUses']=0
  with self.assertRaisesRegex(Exception,'FILL_TOKEN_MAX_USES_INVALID'):v.stimulus(invalid)
 def test_claim_relations_and_global_uniqueness(self):
  kits=self.kits();bad=copy.deepcopy(kits);claim=bad[0]['courses'][0]['atlasValidationIndependenceClaims'][0];course=bad[0]['courses'][0];other_objective=next(o['objectiveId'] for o in course['objectives'] if o['objectiveId']!=claim['objectiveId']);claim['targetActivityLineageId']=next(a['activityLineageId'] for a in course['activities'] if a['objectiveIds']==[other_objective])
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
