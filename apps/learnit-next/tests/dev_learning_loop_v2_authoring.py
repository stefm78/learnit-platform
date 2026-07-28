#!/usr/bin/env python3
"""DEV-AUTHORING tests for Wave A objective -> training -> validation."""
from __future__ import annotations
import copy, importlib.util, json, subprocess, sys, unittest
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[3]
VP=ROOT/'authoring/v2/validate_kit.py'; SP=ROOT/'contracts/learnit-kit-v2.schema.json'
KITS=(ROOT/'authoring/v2/golden/nombres_complexes.json',ROOT/'authoring/v2/golden/signaux_electriques.json')
spec=importlib.util.spec_from_file_location('authoring_validator',VP)
if spec is None or spec.loader is None: raise RuntimeError(f'cannot load {VP}')
V=importlib.util.module_from_spec(spec); sys.modules[spec.name]=V; spec.loader.exec_module(V)
def load(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding='utf-8'))
def redigest(d:dict[str,Any])->dict[str,Any]:
    for c in d['courses']:
        for a in c['activities']: a['activityRevisionDigest']=V.digest(a,'activityRevisionDigest')[0]
        c['courseRevisionDigest']=V.digest(c,'courseRevisionDigest')[0]
    d['packageRevisionDigest']=V.digest(d,'packageRevisionDigest')[0]; return d
def report(d:dict[str,Any]): return V.validate(Path('mutated.json'),d,load(SP),True)
def loop_error(r,path): return [e for e in r.errors if e.startswith(path)]
class AuthoringLoopTests(unittest.TestCase):
    def test_golden_kits_have_ordered_distinct_loop(self):
        s=load(SP)
        for p in KITS:
            with self.subTest(p=p.name):
                r=V.validate(p,load(p),s,True); self.assertTrue(r.ok,'\n'.join(r.errors))
                complete=[x for x in r.objective_loops if x['complete']]; self.assertTrue(complete)
                for x in complete:
                    self.assertTrue(x['trainingActivities']); self.assertTrue(x['validationActivities'])
                    self.assertTrue(x['orderedDistinctPairs'])
                    self.assertTrue(all(y['training']!=y['validation'] for y in x['orderedDistinctPairs']))
    def test_missing_validation_diagnostic(self):
        d=copy.deepcopy(load(KITS[0])); c=d['courses'][0]
        for a in c['activities']:
            if a['assessmentRole']=='validation': a['assessmentRole']='practice'; a['learningPhase']='application'
        r=report(redigest(d)); p='$.courses[0].objectives[1].objectiveId'; e=loop_error(r,p)
        self.assertEqual(1,len(e)); self.assertIn('no validation activity',e[0]); self.assertIn('"validationActivityPaths":[]',e[0])
    def test_missing_training_diagnostic(self):
        d=copy.deepcopy(load(KITS[1])); c=d['courses'][0]; oid='e6a159cb-cd4d-4565-9d61-eda32db9002e'
        for a in c['activities']:
            if oid in a['objectiveIds'] and a['assessmentRole']=='practice': a['assessmentRole']='diagnostic'; a['learningPhase']='diagnostic'
        r=report(redigest(d)); p='$.courses[0].objectives[0].objectiveId'; e=loop_error(r,p)
        self.assertEqual(1,len(e)); self.assertIn('no training activity',e[0]); self.assertIn('"trainingActivityPaths":[]',e[0])
    def test_validation_before_training_rejected(self):
        d=copy.deepcopy(load(KITS[0])); c=d['courses'][0]; c['activities'].insert(0,c['activities'].pop())
        r=report(redigest(d)); e=loop_error(r,'$.courses[0].objectives[1].objectiveId')
        self.assertEqual(1,len(e)); self.assertIn('validation must follow',e[0]); self.assertIn('"validationActivityPaths":["$.courses[0].activities[0]"]',e[0])
    def test_phase_role_mismatch_diagnostic(self):
        d=copy.deepcopy(load(KITS[0])); d['courses'][0]['activities'][-1]['assessmentRole']='practice'
        r=report(redigest(d)); e=[x for x in r.errors if x.startswith('$.courses[0].activities[5]: validation')]
        self.assertEqual(1,len(e)); self.assertIn('"assessmentRole":"practice"',e[0]); self.assertIn('"learningPhase":"validation"',e[0])
    def test_cli_json_exposes_objective_loops(self):
        cmd=[sys.executable,str(VP),'--schema',str(SP),'--foundation-profile','--format','json',*(str(p) for p in KITS)]
        done=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
        self.assertEqual(0,done.returncode,done.stdout); payload=json.loads(done.stdout); self.assertTrue(payload['ok'])
        self.assertTrue(all(any(x['complete'] for x in f['objectiveLoops']) for f in payload['files']))
    def test_write_digests_refuses_stale_revision(self):
        d=copy.deepcopy(load(KITS[0])); d['courses'][0]['activities'][0]['prompt']+=' modifié'
        e=V.fill_new_digests(d); self.assertTrue(e); self.assertIn('non-zero digest mismatch',e[0]); self.assertIn('"calculated"',e[0]); self.assertIn('"declared"',e[0])
if __name__=='__main__': unittest.main()
