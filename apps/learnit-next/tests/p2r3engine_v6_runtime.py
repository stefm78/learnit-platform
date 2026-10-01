#!/usr/bin/env python3
import json, subprocess, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OBJECTIVES=["MO_01_01","MO_01_02","MO_01_03","MO_01_04","MO_01_05","MO_02_01","MO_02_02","MO_02_03","MO_02_04","MO_03_01","MO_03_02","MO_03_03","MO_04_01","MO_04_02","MO_04_03","MO_05_01","MO_05_02","MO_05_03","MO_05_04","MO_05_05","MO_06_01","MO_06_02","MO_06_03","MO_06_04","MO_06_05","MO_06_06","MO_07_01","MO_07_02","MO_07_03","MO_07_04","MO_07_05","MO_07_06","MO_07_07","MO_07_08","MO_07_09","MO_07_10","MO_07_11","MO_08_01","MO_08_02","MO_08_03","MO_08_04","MO_09_01","MO_09_02","MO_09_03","MO_09_04"]
NOT_FAITHFUL=["MO_04_03","MO_05_02","MO_05_03","MO_05_05","MO_06_02","MO_07_03","MO_07_04","MO_08_04","MO_09_01","MO_09_02","MO_09_04"]

class P2R3EngineV6(unittest.TestCase):
    def test_runtime_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            (td/"package.json").write_text('{"type":"module"}\n',encoding="utf-8")
            for rel in [
                "apps/learnit-next/src/core/activity_semantics.js",
                "apps/learnit-next/src/core/objective_progress.js",
                "apps/learnit-next/src/core/contract.js",
                "apps/learnit-next/src/integration/atlas/activity_projection.js",
            ]:
                target=td/Path(rel).name
                target.write_text((ROOT/rel).read_text(encoding="utf-8"),encoding="utf-8")
            script=f"""
import assert from 'node:assert/strict';
import * as S from './activity_semantics.js';
import * as O from './objective_progress.js';
import * as C from './contract.js';
import * as P from './activity_projection.js';
const objectives={json.dumps(OBJECTIVES)};
const nf={json.dumps(NOT_FAITHFUL)};
assert.equal(objectives.length,45); assert.equal(nf.length,11);
for (const objectiveId of objectives) {{
  let state=O.reduceObjectiveEvents(objectiveId,[
    {{type:'training-result',objectiveId,correct:true}},
    {{type:'validation-result',objectiveId,correct:true,validationSlot:'A'}},
  ]);
  assert.equal(state.status,'validation-a-complete');
  assert.equal(state.masteryEvidenceComplete,false);
  state=O.applyObjectiveEvent(state,{{type:'validation-result',objectiveId,correct:true,validationSlot:'B'}});
  assert.equal(state.status,'mastery-evidence-complete');
  assert.equal(state.masteryEvidenceComplete,true);
  state=O.applyObjectiveEvent(state,{{type:'training-result',objectiveId,correct:false}});
  assert.equal(state.status,'review-needed');
  assert.equal(state.validationAComplete,false); assert.equal(state.validationBComplete,false);
}}
const legacy=O.reduceObjectiveEvents('legacy',[{{type:'training-result',objectiveId:'legacy',correct:true}},{{type:'validation-result',objectiveId:'legacy',correct:true}}]);
assert.equal(legacy.status,'validated-recently'); assert.equal(Object.hasOwn(legacy,'masteryEvidenceComplete'),false);
const ids=['11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222','33333333-3333-4333-8333-333333333333'];
function productive(objectiveId){{
  return {{
    type:'productive',objectiveIds:[objectiveId],prompt:'Résolvez et justifiez.',explanation:'Correction structurée.',
    difficulty:'advanced',learningPhase:'validation',assessmentRole:'validation',validationSlot:'A',
    parts:[
      {{partId:ids[0],label:'Valeur',responseKind:'number',unitPrompt:'Unité'}},
      {{partId:ids[1],label:'Relation',responseKind:'expression'}},
      {{partId:ids[2],label:'Justification',responseKind:'text'}},
    ],
    scoring:{{aggregation:'all',evaluators:[
      {{partId:ids[0],kind:'numeric-tolerance',expected:{{numerator:981,denominator:100}},absoluteTolerance:{{numerator:1,denominator:100}},acceptedUnits:['m/s²']}},
      {{partId:ids[1],kind:'canonical-expression-set',acceptedExpressions:['F=ma','F = m a']}},
      {{partId:ids[2],kind:'required-concepts',requiredConceptGroups:[['système fermé'],['conservation','bilan'],['énergie']]}}
    ]}}
  }};
}}
const answer={{parts:[
  {{partId:ids[0],value:'9,81',unit:'m/s²'}},
  {{partId:ids[1],value:'F = m a'}},
  {{partId:ids[2],value:'Dans un système fermé, le bilan exprime la conservation de l’énergie.'}}
]}};
for(const objectiveId of nf){{
  const activity=productive(objectiveId);
  const result=S.evaluateActivityResponse(activity,answer);
  assert.equal(result.correct,true); assert.equal(result.partResults.length,3);
  const presentation=P.projectActivityPresentation(activity,{{contract:'learnit.kit.v6'}});
  assert.equal(presentation.type,'productive'); assert.equal(presentation.parts.length,3);
  const serialized=JSON.stringify(presentation);
  for(const secret of ['scoring','evaluators','expected','absoluteTolerance','acceptedExpressions','requiredConceptGroups'])assert.equal(serialized.includes(secret),false);
}}
const bad=productive(nf[0]); bad.scoring.evaluators[0].kind='mystery';
assert.throws(()=>S.evaluateActivityResponse(bad,answer),/Unsupported productive evaluator/);
const baseActivity={{
 activityLineageId:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
 activityRevisionId:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
 activityRevisionDigest:'sha256:'+'0'.repeat(64),
 objectiveIds:['cccccccc-cccc-4ccc-8ccc-cccccccccccc','dddddddd-dddd-4ddd-8ddd-dddddddddddd'],
 type:'productive',prompt:'x',explanation:'x',difficulty:'easy',learningPhase:'validation',assessmentRole:'validation',validationSlot:'A',
 parts:[{{partId:ids[0],label:'x',responseKind:'number'}}],
 scoring:{{aggregation:'all',evaluators:[{{partId:ids[0],kind:'numeric-tolerance',expected:{{numerator:1,denominator:1}},absoluteTolerance:{{numerator:0,denominator:1}}}}]}}
}};
const packageValue={{contract:'learnit.kit.v6',packageLineageId:'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',packageRevisionId:'ffffffff-ffff-4fff-8fff-ffffffffffff',packageRevisionDigest:'sha256:'+'0'.repeat(64),title:'x',versionLabel:'x',language:'fr',courses:[{{courseLineageId:'01234567-89ab-4cde-8fab-0123456789ab',courseRevisionId:'11234567-89ab-4cde-8fab-0123456789ab',courseRevisionDigest:'sha256:'+'0'.repeat(64),title:'x',estimatedMinutes:1,objectives:[{{objectiveId:baseActivity.objectiveIds[0],label:'a'}},{{objectiveId:baseActivity.objectiveIds[1],label:'b'}}],activities:[baseActivity]}}]}};
const validation=await C.validatePackageObject(packageValue);
assert.equal(validation.errors.some(e=>e.code==='v6_validation_objective_cardinality'),true);
console.log(JSON.stringify({{abObjectives:objectives.length,notFaithful:nf.length,secretBoundary:'PASS',legacy:'PASS',unknownEvaluator:'PASS',multiObjectiveValidationRejected:'PASS'}}));
"""
            (td/"test.mjs").write_text(script,encoding="utf-8")
            cp=subprocess.run(["node","test.mjs"],cwd=td,text=True,capture_output=True)
            self.assertEqual(cp.returncode,0,cp.stdout+"\n"+cp.stderr)
            report=json.loads(cp.stdout.strip().splitlines()[-1])
            self.assertEqual(report["abObjectives"],45);self.assertEqual(report["notFaithful"],11)

    def test_presenter_is_native_control_accessible_and_secret_free(self):
        text=(ROOT/"apps/learnit-next/src/ui/activity_presenters.js").read_text(encoding="utf-8")
        for token in ["case 'productive'","<" if False else "data-productive-part","label","textarea","input"]:
            self.assertIn(token,text)
        for secret in ["acceptedExpressions","requiredConceptGroups","absoluteTolerance"]:
            self.assertNotIn(secret,text)

if __name__=="__main__":unittest.main()
