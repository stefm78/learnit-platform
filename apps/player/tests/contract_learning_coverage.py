#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from support import ROOT, active_script_paths

checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':detail})

active=active_script_paths()
model_path='src/learning/learning_coverage_model.js'
model=(ROOT/model_path).read_text(encoding='utf-8')
add('coverage-model-active',model_path in active)
add('coverage-levels-explicit',all(token in model for token in ["'recall'","'comprehension'","'application'","'transfer'",'far-transfer-probe-missing','higher-order-assessment-missing']))
add('coverage-no-opaque-percentage','percentage' not in model.lower() and 'score' not in model.lower())
node=f"""
global.window=global;
require({json.dumps(str(ROOT/model_path))});
const M=window.LearnItLearningCoverageModel;
function assert(v,m){{if(!v)throw new Error(m)}}
assert(M.audit().ok,'self audit');
const weak=M.courseCoverage({{title:'Weak',activities:[{{id:'f',type:'flashcard',objective:'O',learning_phase:'activation',assessment_role:'practice'}}]}});
assert(weak.objectives[0].status==='insufficient','weak status');
assert(weak.objectives[0].gaps.includes('application-evidence-missing'),'application gap');
assert(weak.objectives[0].gaps.includes('transfer-evidence-missing'),'transfer gap');
const strong=M.courseCoverage({{title:'Strong',activities:[
{{id:'r',type:'flashcard',objective:'O',learning_phase:'activation',assessment_role:'practice'}},
{{id:'c',type:'qcm',objective:'O',learning_phase:'comprehension',assessment_role:'diagnostic'}},
{{id:'a',type:'fill',objective:'O',learning_phase:'application',assessment_role:'practice'}},
{{id:'t',type:'qcm',objective:'O',learning_phase:'transfer',assessment_role:'validation',transfer_probe:true,transfer_distance:'far',variant_of:'a'}}]}});
assert(strong.completeForAuthoring&&strong.readyForHumanTransferProbe,'strong status');
console.log(JSON.stringify({{ok:true,weak:weak.objectives[0].gaps,strong:strong.statuses}}));
"""
r=subprocess.run(['node','-e',node],cwd=ROOT,capture_output=True,text=True)
add('coverage-node-behavior',r.returncode==0,(r.stderr or r.stdout)[-1600:])
report={'schema':'learnit.rc698.learning_coverage_contract.v1','ok':all(c['ok'] for c in checks),'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/contract_learning_coverage_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks),'report':'reports/contract_learning_coverage_report.json'},ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
