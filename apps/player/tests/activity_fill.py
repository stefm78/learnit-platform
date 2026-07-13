#!/usr/bin/env python3
import json, re, sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
from support import load_runtime_core
source = (ROOT/'src/activities/fill.js').read_text(encoding='utf-8')
core = load_runtime_core()
checks=[]

def add(name, ok, detail=''):
    checks.append({'name':name,'ok':bool(ok),'detail':detail})

exports = ['tokenCapacities','effectiveTokens','makeInitial','normalizePending','nextEmptyIndex','tokenUsage','tokenStates','isTokenAvailable','placeToken','clearIndex','isComplete','isCorrect','expectedText','domSnapshot','auditDomSnapshot']
for name in exports:
    add(f'exports-{name}', re.search(r'\b'+re.escape(name)+r'\b', source) is not None)

add('schema-rc661', 'learnit.fill_activity.rc661.v2' in source)
add('multiplicity-guard', 'capacity' in source and 'current >= capacity' in source and 'tokenUsage' in source)
add('tap-to-slot-placement', 'selectedIndex' in source and 'placeToken' in source and 'nextEmptyIndex' in source)
add('clear-index-primitive', 'function clearIndex' in source and "values[i] = ''" in source)
add('dom-audit-no-keyboard', 'nativeInputs' in source and 'unexpected-mobile-keyboard-input' in source)
add('dom-audit-single-selected-slot', 'multiple-selected-fill-slots' in source)
add('core-reset-delegates-fill', 'LearnItFillActivity.makeInitial' in core)
add('core-token-place-delegates-fill', 'LearnItFillActivity' in core and 'api.placeToken' in core and 'validated_fill_token_place' in core)
add('core-slot-select-action', "action==='select-fill-slot'" in core and 'selectFillSlot' in core)
add('core-clear-delegates-fill', 'api.clearIndex' in core and 'validated_fill_slot_clear' in core)
add('core-validation-delegates-fill', 'api.isCorrect' in core and 'api.expectedText' in core)
add('core-canvalidate-delegates-fill', 'LearnItFillActivity.isComplete' in core)
add('renderer-fill-data-surfaces', 'data-fill-slot' in core and 'data-fill-token' in core and 'aria-selected' in core)
add('test-api-fill-module', 'fillModule:()=>window.LearnItFillActivity' in core)
add('order-delegation-preserved', 'LearnItOrderActivity.pointer.move' in core and 'LearnItOrderActivity.moveTokenByDelta' in core)
add('matching-delegation-preserved', 'LearnItMatchingActivity.pointer.move' in core and 'LearnItMatchingActivity.isComplete' in core)

node_code = f"""
global.window={{}};
global.document={{querySelector:()=>null, querySelectorAll:()=>[]}};
require({json.dumps(str(ROOT / 'src/activities/fill.js'))});
const m = window.LearnItFillActivity;
function assert(cond,msg){{ if(!cond) throw new Error(msg); }}
const activity = {{tokens:['R','I','I'], answer:['R','I'], sentence:'U = R × I'}};
assert(m && m.schema === 'learnit.fill_activity.rc661.v2', 'schema missing');
let pending = m.makeInitial(activity);
assert(JSON.stringify(pending) === JSON.stringify(['','']), 'initial mismatch: '+JSON.stringify(pending));
let placed = m.placeToken(activity, pending, 'I', 1);
assert(placed.changed && placed.placedIndex === 1 && JSON.stringify(placed.values) === JSON.stringify(['','I']), 'selected placement failed');
placed = m.placeToken(activity, placed.values, 'R', null);
assert(placed.changed && placed.placedIndex === 0 && JSON.stringify(placed.values) === JSON.stringify(['R','I']), 'next-empty placement failed');
assert(m.isComplete(activity, placed.values), 'complete expected');
assert(m.isCorrect(activity, placed.values), 'correct expected');
let cleared = m.clearIndex(activity, placed.values, 1);
assert(cleared.changed && cleared.cleared === 'I' && JSON.stringify(cleared.values) === JSON.stringify(['R','']), 'clear failed');
let blocked = m.placeToken({{tokens:['A'],answer:['A']}}, ['A'], 'A', null);
assert(!blocked.changed && blocked.reason === 'token-unavailable', 'multiplicity guard failed');
let normalized = m.normalizePending({{tokens:['A'],answer:['A','B']}}, ['A','B','A']);
assert(JSON.stringify(normalized) === JSON.stringify(['A','B']), 'normalize should drop unavailable/out-of-range tokens: '+JSON.stringify(normalized));

const repeated = {{tokens:['θ'], answer:['θ','θ'], sentence:'θ puis θ'}};
assert(JSON.stringify(m.effectiveTokens(repeated)) === JSON.stringify(['θ']), 'effective token should stay unique');
let repeatedPending = m.makeInitial(repeated);
let repeatedFirst = m.placeToken(repeated, repeatedPending, 'θ', null);
assert(repeatedFirst.changed && repeatedFirst.values[0] === 'θ' && m.isTokenAvailable(repeated,repeatedFirst.values,'θ'), 'first repeated placement should leave one use');
let repeatedSecond = m.placeToken(repeated, repeatedFirst.values, 'θ', null);
assert(repeatedSecond.changed && JSON.stringify(repeatedSecond.values) === JSON.stringify(['θ','θ']) && !m.isTokenAvailable(repeated,repeatedSecond.values,'θ'), 'second repeated placement failed');
const repeatedStates = m.tokenStates(repeated,repeatedFirst.values);
assert(repeatedStates[0].capacity === 2 && repeatedStates[0].remainingCount === 1 && repeatedStates[0].reusable, 'repeated token state mismatch');

const audit = m.auditDomSnapshot({{slots:2,focusableSlots:2,tokens:2,focusableTokens:2,selectedSlots:1,nativeInputs:0}});
assert(audit.ok, 'audit should pass');
console.log(JSON.stringify({{ok:true,schema:m.schema,placed:placed.values,cleared:cleared.values,blocked:blocked.reason,normalized}}));
"""
result = subprocess.run(['node', '-e', node_code], cwd=str(ROOT), capture_output=True, text=True)
add('node-behavior-fill-module', result.returncode == 0, (result.stderr or result.stdout)[:700])
behavior = None
if result.returncode == 0:
    behavior = json.loads(result.stdout.strip())

ok=all(c['ok'] for c in checks)
report={'schema':'learnit.rc677.fill_module_checks.v1','ok':ok,'checks':checks,'behavior':behavior}
(ROOT/'reports').mkdir(exist_ok=True)
(ROOT/'reports/activity_fill_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if ok else 1)
