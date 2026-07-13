#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from support import ROOT
checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':detail})
model=(ROOT/'src/learning/session_mode_model.js').read_text(encoding='utf-8')
add('assessment-pool-present','assessmentPool' in model and 'assessmentPurity' in model and 'assessmentFallbackReason' in model)
node=f"""
global.window=global;
require({json.dumps(str(ROOT/'src/learning/remediation_model.js'))});
require({json.dumps(str(ROOT/'src/learning/session_mode_model.js'))});
const M=window.LearnItSessionModeModel;function assert(v,m){{if(!v)throw new Error(m)}}
const course={{activities:[
{{id:'d1',type:'qcm',objective:'O1',assessment_role:'diagnostic'}},{{id:'d2',type:'qcm',objective:'O2',assessment_role:'diagnostic'}},
{{id:'v1',type:'qcm',objective:'O1',assessment_role:'validation'}},{{id:'v2',type:'order',objective:'O2',assessment_role:'validation'}},
{{id:'p1',type:'fill',objective:'O1',assessment_role:'practice'}},{{id:'r1',type:'qcm',objective:'O2',assessment_role:'remediation'}},
{{id:'f',type:'flashcard',objective:'O1',assessment_role:'diagnostic'}}]}};
const d=M.buildPlan(course,{{}},'diagnostic'),v=M.buildPlan(course,{{}},'validation');
assert(d.assessmentPurity==='strict'&&d.queueRoleCounts.diagnostic===2&&d.queue.length===2,'strict diagnostic');
assert(v.assessmentPurity==='strict'&&v.queueRoleCounts.validation===2&&v.queue.length===2,'strict validation');
assert(!d.queue.includes('f')&&!v.queue.includes('f'),'flashcard excluded');
const fallback=M.buildPlan({{activities:[{{id:'p',type:'qcm',objective:'O',assessment_role:'practice'}},{{id:'r',type:'order',objective:'O',assessment_role:'remediation'}}]}},{{}},'validation');
assert(fallback.assessmentPurity==='explicit-fallback'&&fallback.queue.length===1&&fallback.queue[0]==='p'&&fallback.assessmentFallbackReason==='no-validation-role','fallback explicit');
console.log(JSON.stringify({{ok:true,d:d.queue,v:v.queue,fallback:fallback}}));
"""
r=subprocess.run(['node','-e',node],cwd=ROOT,capture_output=True,text=True)
add('assessment-purity-node-behavior',r.returncode==0,(r.stderr or r.stdout)[-1800:])
report={'schema':'learnit.rc699.assessment_purity_contract.v1','ok':all(c['ok'] for c in checks),'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/contract_assessment_purity_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks),'report':'reports/contract_assessment_purity_report.json'},ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
