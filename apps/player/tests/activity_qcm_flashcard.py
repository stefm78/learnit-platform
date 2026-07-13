#!/usr/bin/env python3
import json, re, sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
from support import load_runtime_core
qcm = (ROOT/'src/activities/qcm.js').read_text(encoding='utf-8')
flash = (ROOT/'src/activities/flashcard.js').read_text(encoding='utf-8')
core = load_runtime_core()
qcm_state_css = (ROOT/'src/styles/parts/64_library_chapter_comfort.css').read_text(encoding='utf-8')
checks=[]

def add(name, ok, detail=''):
    checks.append({'name':name,'ok':bool(ok),'detail':detail})

for name in ['makeInitial','normalizePending','selectChoice','isComplete','isCorrect','expectedText','choiceStates','domSnapshot','auditDomSnapshot']:
    add(f'qcm-exports-{name}', re.search(r'\b'+re.escape(name)+r'\b', qcm) is not None)
for name in ['makeInitial','normalizePending','reveal','grade','expectedText','isRevealed','domSnapshot','auditDomSnapshot']:
    add(f'flashcard-exports-{name}', re.search(r'\b'+re.escape(name)+r'\b', flash) is not None)
add('qcm-schema-rc223', 'learnit.qcm_activity.rc223.v1' in qcm)
add('flashcard-schema-rc223', 'learnit.flashcard_activity.rc223.v1' in flash)
add('core-delegates-qcm-select', 'LearnItQcmActivity' in core and 'api.selectChoice' in core and 'validated_qcm_choice_select' in core)
add('core-delegates-qcm-validation', 'api.isCorrect' in core and 'api.expectedText' in core and 'LearnItQcmActivity.isComplete' in core)
add('core-delegates-flashcard', 'LearnItFlashcardActivity' in core and 'api.reveal' in core and 'api.grade' in core and 'validated_flashcard_grade' in core)
add('renderer-qcm-data-surfaces', 'data-qcm-module' in core and 'data-qcm-choice' in core and 'aria-pressed' in core)
add('renderer-flashcard-data-surfaces', 'data-flashcard-module' in core and 'data-flashcard-revealed' in core)
add('test-api-qcm-flashcard', 'qcmModule:()=>window.LearnItQcmActivity' in core and 'flashcardModule:()=>window.LearnItFlashcardActivity' in core and 'activityDomAudit' in core)
add('qcm-null-guard-before-number-coercion', qcm.index('pending === null') < qcm.index('Number(pending)'), 'null must not coerce to zero')
add('qcm-nonanswers-guarded', all(term in qcm for term in ["pending === undefined", "pending === ''", "typeof pending === 'boolean'"]))
add('qcm-renderer-exposes-phase', 'data-qcm-phase' in core and "selected===null?'idle'" in core)
add('qcm-radio-semantics', 'role="radiogroup"' in core and 'role="radio"' in core and 'aria-checked' in core)
add('qcm-visual-state-explicit', 'data-qcm-state' in core and "state.correct?'correct'" in core)
add('qcm-touch-hover-neutralized', '@media (hover:none), (pointer:coarse)' in qcm_state_css and '.activity-qcm .choice.selected:hover' in qcm_state_css)
add('qcm-explicit-choice-marker', '.activity-qcm .choice::before' in qcm_state_css and '.choice.correct::before' in qcm_state_css and '.choice.wrong::before' in qcm_state_css)

node_code = f"""
global.window={{}};
global.document={{querySelector:()=>null, querySelectorAll:()=>[]}};
require({json.dumps(str(ROOT / 'src/activities/qcm.js'))});
require({json.dumps(str(ROOT / 'src/activities/flashcard.js'))});
const q = window.LearnItQcmActivity;
const f = window.LearnItFlashcardActivity;
function assert(cond,msg){{ if(!cond) throw new Error(msg); }}
const activity = {{choices:['A','B','C'], answer:1}};
assert(q && q.schema === 'learnit.qcm_activity.rc223.v1', 'qcm schema missing');
assert(q.makeInitial(activity) === null, 'qcm initial should be null');
assert(q.normalizePending(activity, null) === null, 'qcm null must stay unselected');
assert(q.normalizePending(activity, undefined) === null, 'qcm undefined must stay unselected');
assert(q.normalizePending(activity, '') === null, 'qcm empty string must stay unselected');
assert(!q.isComplete(activity, null), 'qcm null must be incomplete');
assert(!q.isCorrect(activity, null), 'qcm null must not equal answer index zero');
let sel = q.selectChoice(activity, null, 1);
assert(sel.changed && sel.pending === 1 && q.isComplete(activity, sel.pending) && q.isCorrect(activity, sel.pending), 'qcm selection/correct failed');
let bad = q.selectChoice(activity, sel.pending, 9);
assert(!bad.changed && bad.reason === 'invalid-choice-index' && bad.pending === 1, 'qcm invalid guard failed');
assert(q.expectedText(activity) === 'B', 'qcm expected failed');
let states = q.choiceStates(activity, 0, true);
assert(states[0].wrong && states[1].correct, 'qcm locked states failed');
assert(q.auditDomSnapshot({{choices:3,selected:0,focusableChoices:3,hasAnswerPanel:true}}).ok, 'qcm idle audit should pass');
assert(q.auditDomSnapshot({{choices:3,selected:1,focusableChoices:3,hasAnswerPanel:true}}).ok, 'qcm selected audit should pass');
assert(!q.auditDomSnapshot({{choices:3,selected:2,focusableChoices:3,hasAnswerPanel:true}}).ok, 'qcm audit should catch multiple selection');
const fc = {{front:'Question', answer:'Réponse', why:'Pourquoi', remediation:'Remède'}};
assert(f && f.schema === 'learnit.flashcard_activity.rc223.v1', 'flashcard schema missing');
let p = f.makeInitial(fc);
assert(!p.revealed && p.grade === null, 'flashcard initial failed');
let r = f.reveal(p);
assert(r.changed && r.pending.revealed, 'flashcard reveal failed');
let g = f.grade(fc, r.pending, false);
assert(g.pending.revealed && g.pending.grade === false && g.feedback.correct === false && g.feedback.expected === 'Réponse', 'flashcard grade failed');
assert(f.expectedText(fc) === 'Réponse', 'flashcard expected failed');
assert(f.auditDomSnapshot({{frontFaces:1,backFaces:0,revealButtons:1,gradeButtons:0,revealed:false,focusableActions:1}}).ok, 'flashcard hidden audit should pass');
assert(f.auditDomSnapshot({{frontFaces:1,backFaces:1,revealButtons:0,gradeButtons:2,revealed:true,focusableActions:2}}).ok, 'flashcard revealed audit should pass');
assert(!f.auditDomSnapshot({{frontFaces:1,backFaces:1,revealButtons:1,gradeButtons:0,revealed:false,focusableActions:1}}).ok, 'flashcard audit should catch premature back');
console.log(JSON.stringify({{ok:true,qcm:sel.pending,flashcard:g.feedback}}));
"""
result = subprocess.run(['node','-e',node_code], cwd=str(ROOT), capture_output=True, text=True)
add('node-behavior-qcm-flashcard', result.returncode == 0, (result.stderr or result.stdout)[:900])
behavior = None
if result.returncode == 0:
    behavior = json.loads(result.stdout.strip())
ok=all(c['ok'] for c in checks)
report={'schema':'learnit.rc579.qcm_flashcard_contract.v1','ok':ok,'checks':checks,'behavior':behavior}
(ROOT/'reports').mkdir(exist_ok=True)
(ROOT/'reports/activity_qcm_flashcard_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if ok else 1)
