#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
from support import load_runtime_core
source = (ROOT/'src/activities/matching.js').read_text(encoding='utf-8')
core = load_runtime_core()
checks=[]

def add(name, ok, detail=''):
    checks.append({'name':name,'ok':bool(ok),'detail':detail})

exports = ['makeInitial','normalizePending','chooseRight','selectLeft','clearLeft','assignMatch','isComplete','isCorrect','expectedText','domSnapshot','auditDomSnapshot','pointer']
for name in exports:
    add(f'exports-{name}', re.search(r'\b'+re.escape(name)+r'\b', source) is not None)

for name in ['start','move','end','cancel','cleanup','updateDrop']:
    add(f'pointer-has-{name}', re.search(r'\b'+name+r'\s*[:=,]', source) is not None or re.search(r'function '+name+r'\(', source) is not None)

add('single-use-right-dedup', 'if(p.matches[key] === right && key !== left)' in source and 'delete p.matches[key]' in source)
add('tap-and-drag-share-assign', 'selectLeft' in source and 'assignMatch(p, left, p.selectedRight)' in source and 'runtime.answer.dragMatch(drop.left, drop.right)' in source)
add('cleanup-removes-ghost', 'drag.ghost.remove()' in source)
add('cleanup-removes-hot', "querySelectorAll('.hot')" in source)
add('cleanup-releases-pointer', 'releasePointerCapture' in source)
add('core-uses-module-for-validation', 'api.isCorrect' in core and 'api.expectedText' in core)
add('core-uses-module-for-canvalidate', 'LearnItMatchingActivity.isComplete' in core)
add('core-uses-module-for-retry-reset', 'LearnItMatchingActivity.makeInitial' in core)
add('core-keeps-order-delegation', 'LearnItOrderActivity.pointer.move' in core and 'LearnItOrderActivity.moveTokenByDelta' in core)

ok=all(c['ok'] for c in checks)
report={'schema':'learnit.rc221.matching_module_checks.v1','ok':ok,'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True)
(ROOT/'reports/activity_matching_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if ok else 1)
