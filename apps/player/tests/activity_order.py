#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
from support import load_runtime_core
errors = []

def check(cond, msg):
    if not cond:
        errors.append(msg)

order_module = (ROOT / 'src/activities/order.js').read_text(encoding='utf-8')
core = load_runtime_core()

for needle in [
    'window.LearnItOrderActivity = Object.freeze',
    'tokensEqual', 'repairPending', 'moveTokenByDelta', 'moveTokenToIndex',
    'buildRenderModel', 'domSnapshot', 'auditDomSnapshot',
    "schema: 'learnit.order_activity.rc220.v1'",
    "const POINTER_SCHEMA = 'learnit.order_pointer_controller.rc662.v2'",
    'const pointer = Object.freeze', 'orderPointerStart', 'orderPointerMove',
    'orderPointerEnd', 'orderPointerCleanup', 'orderPointerSyncPreviewDom',
]:
    check(needle in order_module, 'order module missing ' + needle)

for needle in [
    'LearnItOrderActivity.makeInitial', 'LearnItOrderActivity.tokensEqual',
    'LearnItOrderActivity.repairPending', 'LearnItOrderActivity.moveTokenByDelta',
    'LearnItOrderActivity.moveTokenToIndex', 'LearnItOrderActivity.buildRenderModel',
    'LearnItOrderActivity.pointer.start', 'LearnItOrderActivity.pointer.move',
    'LearnItOrderActivity.pointer.end', 'LearnItOrderActivity.pointer.cancel',
    'LearnItOrderActivity.pointer.cleanup', 'data-order-module="LearnItOrderActivity"',
]:
    check(needle in core, 'core does not delegate/mark ' + needle)

# The active gate must be self-contained: no dependency on legacy/quarantine harnesses.

node_code = f"""
global.window={{innerWidth:1024}};
global.document={{}};
global.requestAnimationFrame=(fn)=>{{ fn(); return 1; }};
global.cancelAnimationFrame=(id)=>{{}};
require({json.dumps(str(ROOT / 'src/activities/order.js'))});
const m = window.LearnItOrderActivity;
function assert(cond,msg){{ if(!cond) throw new Error(msg); }}
assert(m && m.schema === 'learnit.order_activity.rc220.v1','schema missing');
assert(m.pointer && m.pointer.schema === 'learnit.order_pointer_controller.rc662.v2','pointer schema missing');
assert(['start','move','end','cancel','cleanup','computeIndex','computeIndexFromRects','probeY','syncPreviewDom','updatePreview'].every(k=>typeof m.pointer[k] === 'function'), 'pointer api incomplete');
assert(m.tokensEqual(['a','b','a'], ['a','a','b']), 'tokensEqual duplicates');
assert(!m.tokensEqual(['a','b'], ['a','b','c']), 'tokensEqual length');
const repaired = m.repairPending(['x','b','a','a'], ['a','b','c'], ['c','b','a']);
assert(JSON.stringify(repaired) === JSON.stringify(['b','a','c']), 'repairPending mismatch');
const moved = m.moveTokenByDelta(['a','b','c'], 'b', 1);
assert(moved.changed && JSON.stringify(moved.values) === JSON.stringify(['a','c','b']) && moved.from === 1 && moved.to === 2, 'moveTokenByDelta mismatch');
const inserted = m.moveTokenToIndex(['a','b','c','d'], 'b', 3);
assert(JSON.stringify(inserted.values) === JSON.stringify(['a','c','d','b']) && inserted.from === 1 && inserted.to === 3, 'moveTokenToIndex mismatch');
const model = m.buildRenderModel(['a','b','c'], 'b', {{type:'order', token:'b', overIndex:1, placeholderHeight:72}});
assert(JSON.stringify(model.preview) === JSON.stringify(['a','__placeholder__','c']), 'buildRenderModel mismatch');
console.log(JSON.stringify({{ok:true,schema:m.schema,pointerSchema:m.pointer.schema,repaired,moved,inserted,modelPreview:model.preview}}));
"""
result = subprocess.run(['node', '-e', node_code], cwd=str(ROOT), capture_output=True, text=True)
check(result.returncode == 0, 'order module node behavior failed: ' + (result.stderr or result.stdout)[:700])
behavior = json.loads(result.stdout.strip()) if result.returncode == 0 else None
report = {'schema':'learnit.rc677.order_module_checks.v1','ok':not errors,'errors':errors,'behavior':behavior}
(ROOT / 'reports/activity_order_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if not errors else 1)
