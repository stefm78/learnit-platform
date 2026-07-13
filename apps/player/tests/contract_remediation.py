#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from support import ROOT, active_script_paths, load_runtime_core

checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':detail})

mastery_path=ROOT/'src/learning/mastery_evidence_model.js'
next_action_path=ROOT/'src/learning/next_action_model.js'
mode_path=ROOT/'src/learning/session_mode_model.js'
model_path=ROOT/'src/learning/remediation_model.js'
variety_path=ROOT/'src/learning/variety_model.js'
mode_model=mode_path.read_text(encoding='utf-8')
model=model_path.read_text(encoding='utf-8')
variety=variety_path.read_text(encoding='utf-8')
state=(ROOT/'src/scripts/core/runtime_parts/10_content_store_and_state.js').read_text(encoding='utf-8')
session=(ROOT/'src/scripts/core/runtime_parts/20_session_answer_activity_rendering.js').read_text(encoding='utf-8')
bilan=(ROOT/'src/scripts/core/runtime_parts/40_bilan_learning_models.js').read_text(encoding='utf-8')
runtime=load_runtime_core()
composer=(ROOT/'src/scripts/core/runtime_parts/66_route_view_composer.js').read_text(encoding='utf-8')
actions=(ROOT/'src/scripts/core/runtime_parts/67_route_static_actions.js').read_text(encoding='utf-8')
diagnostics=runtime
cap=json.loads((ROOT/'contract/learnit-capabilities.json').read_text(encoding='utf-8'))
active=active_script_paths()

add('session-mode-model-active',mode_path.exists() and 'src/learning/session_mode_model.js' in active)
add('five-public-modes',"['discovery','training','review','validation','diagnostic']" in mode_model)
add('single-policy-model',all(token in mode_model for token in ['buildPlan','sessionPolicy','feedbackTiming','recordProgress','assessment']))
add('assessment-excludes-flashcards',"policy.assessment&&activity.type==='flashcard'" in mode_model)
add('assessment-role-orders-queues','assessment_role' in mode_model and 'roleOrderedIds' in mode_model)
add('deferred-assessment-policy',all(token in mode_model for token in ["validation:Object.freeze", "diagnostic:Object.freeze", "feedbackTiming:'deferred'", "allowRetry:false", "showHints:false"]))
add('diagnostic-non-recording',"recordProgress:false" in mode_model and 'if(policy&&policy.recordProgress===false)return' in state)
add('common-session-entrypoint','startMode(mode' in session and "start(){return this.startMode('training');}" in session)
add('mode-policy-persisted',all(token in session for token in ['modePolicy:policy','modePlan:plan','policyId:policy.id']))
add('deferred-feedback-does-not-leak',"if(r&&r.deferred)" in runtime and 'Réponse enregistrée' in runtime and 'La correction sera présentée dans le bilan' in runtime)
add('assessment-hides-hints',"policy.showHints===false" in runtime)
add('guided-mode-ui-shared-model','modeModel.list()' in composer and 'nextAction(runtime' in composer and 'data-recommendation-code' in composer and 'data-rc580-intent' in composer and 'handleEntryIntent' in actions)
add('mode-outcome-in-bilan','modeOutcome' in session and 'Résultat ·' in bilan and 'modeLabel' in bilan)

add('learning-evidence-model-active',model_path.exists() and 'src/learning/remediation_model.js' in active)
add('pedagogical-variety-model-active',variety_path.exists() and 'src/learning/variety_model.js' in active)
add('near-duplicate-audit','auditCourse' in variety and 'NEAR_DUPLICATE_THRESHOLD=0.82' in variety)
add('deterministic-queue-diversification','sequenceIds' in variety and 'preserveFirst' in variety and 'droppedDuplicateIds' in variety)
add('session-variety-integration',all(token in session for token in ['prepareQueue','varietyPlan','varietySeed','shuffleSeed:seed']))
add('diagnostics-use-variety-audit','varietyModel.auditCourse' in diagnostics and 'formulations trop proches' in diagnostics)
add('progress-history-bounded','MAX_HISTORY=8' in model and 'attemptHistory' in model and 'model.recordProgress' in state)
add('recurring-error-evidence','failureCount' in model and 'failureStreak' in model)
add('variant-before-source',"kind:'variant'" in model and 'bestAlternative' in model and 'isMeaningfullyDifferent' in model)
add('remediation-loop-cap','DEFAULT_MAX_ROUNDS=2' in model and 'remediation_auto_loop_blocked' in runtime)
add('runtime-progress-integration','model.recordProgress' in state and 'recordActivityProgress(a.id,result,a' in session)
add('bilan-plan-integration','model.buildPlan' in bilan and "source:'remediation-model-v1'" in bilan)
add('retry-variation','retryNonceByActivity' in session and '|retry:' in session)
add('feedback-error-hypothesis','commonErrors' in session and 'feedback-error-hypothesis' in runtime)
add('spaced-intervals-explainable','REVIEW_INTERVAL_HOURS=Object.freeze([24,72,168,336,720])' in model and 'FAILURE_RETRY_HOURS=8' in model)
add('spaced-schedule-persisted',all(token in model for token in ['reviewLevel','nextReviewAt','reviewScheduleVersion']))
add('due-plan-bounded','buildDuePlan' in model and 'DEFAULT_DUE_LIMIT=8' in model and 'dailyLoadBounded:true' in model)
add('spaced-session-mode',"baseSession('spaced-review'" in session and 'startSpacedReview' in session)
add('spaced-bilan-action','start-spaced-review' in bilan and 'data-rc247-action="start-due"' in runtime)
add('spaced-action-uses-model','model.buildDuePlan' in actions and 'startSpacedReview' in actions)
learning=cap.get('learning_capabilities',{})
add('remediation-capability-published',learning.get('targeted_remediation',{}).get('status')=='stable')
add('spaced-capability-published',learning.get('spaced_review',{}).get('status')=='stable' and learning.get('spaced_review',{}).get('tested') is True)
add('variety-capability-published',learning.get('pedagogical_variety',{}).get('status')=='stable' and learning.get('pedagogical_variety',{}).get('tested') is True)
modes=learning.get('session_modes',{})
add('session-modes-capability-published',modes.get('status')=='stable' and modes.get('tested') is True and modes.get('authoring_fields')==[] and modes.get('modes')==['discovery','training','review','validation','diagnostic'])
add('session-entry-guidance-published',modes.get('entry_guidance_owner')=='runtime' and modes.get('learner_intents')==['new-topic','prior-knowledge','continue-learning'] and 'entryRecommendation' in mode_model)

node_script=f"""
global.window=global;
const fs=require('fs');
eval(fs.readFileSync({json.dumps(str(mastery_path))},'utf8'));
eval(fs.readFileSync({json.dumps(str(next_action_path))},'utf8'));
eval(fs.readFileSync({json.dumps(str(mode_path))},'utf8'));
eval(fs.readFileSync({json.dumps(str(variety_path))},'utf8'));
eval(fs.readFileSync({json.dumps(str(model_path))},'utf8'));
const modeResult=window.LearnItSessionModeModel.selfTest();
const varietyResult=window.LearnItVarietyModel.selfTest();
const remediationResult=window.LearnItRemediationModel.selfTest();
const result={{ok:modeResult.ok&&varietyResult.ok&&remediationResult.ok,modes:modeResult,variety:varietyResult,remediation:remediationResult}};
console.log(JSON.stringify(result));
process.exit(result.ok?0:1);
"""
proc=subprocess.run(['node','-e',node_script],capture_output=True,text=True,cwd=ROOT)
try: node_result=json.loads((proc.stdout or '{}').strip().splitlines()[-1])
except Exception: node_result={'raw':proc.stdout,'stderr':proc.stderr}
add('learning-model-self-tests',proc.returncode==0 and bool(node_result.get('ok')),json.dumps(node_result,ensure_ascii=False))

report={'schema':'learnit.rc586.learning_mode_guidance_gate.v1','ok':all(c['ok'] for c in checks),'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True)
(ROOT/'reports/contract_remediation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
