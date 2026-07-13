#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from support import ROOT, active_script_paths

checks=[]
def add(code, ok, detail=''): checks.append({'code':code,'ok':bool(ok),'detail':detail})

active=active_script_paths()
next_model=(ROOT/'src/learning/next_action_model.js').read_text(encoding='utf-8')
session=(ROOT/'src/learning/session_mode_model.js').read_text(encoding='utf-8')
composer=(ROOT/'src/scripts/core/runtime_parts/66_route_view_composer.js').read_text(encoding='utf-8')
actions=(ROOT/'src/scripts/core/runtime_parts/67_route_static_actions.js').read_text(encoding='utf-8')
summary=(ROOT/'src/scripts/core/runtime_parts/20_session_answer_activity_rendering.js').read_text(encoding='utf-8')

add('next-action-model-active','src/learning/next_action_model.js' in active)
add('canonical-model-reason-coded',all(t in next_model for t in ['reasonCode','diagnostic-strong','diagnostic-mixed','diagnostic-foundations','validation-errors','active-session']))
add('learn-and-bilan-share-next-action',composer.count('nextAction(runtime')>=3 and 'data-recommendation-code' in composer)
add('entry-intent-passes-adaptive-options','sessionOptions(rec,last)' in actions and 'startMode(target,options)' in actions)
add('assessment-summary-per-objective',all(t in summary for t in ['assessmentEvidence','objectiveAssessment','completedAt','nextAction']))
add('session-plan-adaptive',all(t in session for t in ['adaptiveOrder','focusObjectiveKeys','objectiveAssessment','sourceRecommendationCode']))

node_code=f"""
global.window={{}};
require({json.dumps(str(ROOT/'src/learning/mastery_evidence_model.js'))});
require({json.dumps(str(ROOT/'src/learning/remediation_model.js'))});
require({json.dumps(str(ROOT/'src/learning/session_mode_model.js'))});
require({json.dumps(str(ROOT/'src/learning/next_action_model.js'))});
require({json.dumps(str(ROOT/'src/learning/action_intent_model.js'))});
require({json.dumps(str(ROOT/'src/learning/bilan_decision_model.js'))});
const N=window.LearnItNextActionModel,M=window.LearnItSessionModeModel,A=window.LearnItActionIntentModel;
function assert(v,m){{if(!v)throw new Error(m)}}
const course={{id:'c',title:'Cours',activities:[
 {{id:'a1',type:'qcm',objective:'Objectif fort',assessment_role:'diagnostic'}},
 {{id:'a2',type:'qcm',objective:'Objectif faible',assessment_role:'diagnostic'}},
 {{id:'a3',type:'fill',objective:'Objectif faible',assessment_role:'practice'}},
 {{id:'a4',type:'order',objective:'Objectif fort',assessment_role:'practice'}}
]}};
const fresh=N.recommend(course,{{}},{{status:'idle'}},null);
assert(fresh.reasonCode==='no-evidence-yet'&&fresh.mode==='discovery','fresh');
const active=N.recommend(course,{{}},{{status:'active',mode:'training',currentIndex:1,queue:['a1','a2']}},null);
assert(active.reasonCode==='active-session'&&active.intent==='resume','active');
const last={{mode:'diagnostic',total:2,correct:1,review:['a2'],modeOutcome:{{mode:'diagnostic',total:2,correct:1,reviewCount:1}},assessmentEvidence:[{{id:'a1',objective:'Objectif fort',objectiveKey:'objectif-fort',correct:true}},{{id:'a2',objective:'Objectif faible',objectiveKey:'objectif-faible',correct:false}}],objectiveAssessment:[{{key:'objectif-fort',label:'Objectif fort',total:1,correct:1,incorrect:0,status:'strong'}},{{key:'objectif-faible',label:'Objectif faible',total:1,correct:0,incorrect:1,status:'fragile'}}]}};
const diagnostic=N.recommend(course,{{}},{{status:'idle'}},last);
assert(diagnostic.reasonCode==='diagnostic-mixed'&&diagnostic.adaptive===true&&diagnostic.objectiveKeys.includes('objectif-faible'),'diagnostic');
const opts=N.sessionOptions(diagnostic,last);
const plan=M.buildPlan(course,{{}},'training',opts);
assert(plan.adaptive===true&&plan.queue[0]==='a2'&&plan.queue[1]==='a3','adaptive queue');
const failed=N.recommend(course,{{}},{{status:'idle'}},{{mode:'validation',total:2,correct:1,review:['a2'],modeOutcome:{{mode:'validation',total:2,correct:1,reviewCount:1}},objectiveAssessment:last.objectiveAssessment}});
assert(failed.reasonCode==='validation-errors'&&failed.mode==='review','validation fail');
const info=A.courseAction({{reviewCount:1,hasAny:true,total:4,seen:3,mastery:50,exposure:75}});
assert(info.reasonCode==='fragile-activities'&&info.mode==='review','action intent wrapper');
assert(N.audit().ok&&M.selfTest().ok,'self tests');
console.log(JSON.stringify({{ok:true,fresh:fresh.reasonCode,active:active.reasonCode,diagnostic:diagnostic.reasonCode,queue:plan.queue}}));
"""
node=subprocess.run(['node','-e',node_code],cwd=str(ROOT),capture_output=True,text=True)
add('next-action-node-behavior',node.returncode==0,(node.stderr or node.stdout)[:1600])

report={'schema':'learnit.rc693.next_action_contract.v1','ok':all(c['ok'] for c in checks),'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True)
(ROOT/'reports/contract_next_action_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks),'report':'reports/contract_next_action_report.json'},ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
