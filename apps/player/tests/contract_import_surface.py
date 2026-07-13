#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from support import ROOT, load_runtime_core

checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':detail})

def text(rel): return (ROOT/rel).read_text(encoding='utf-8')

store=text('src/scripts/core/runtime_parts/10_content_store_and_state.js')
diag=load_runtime_core()
view=text('src/scripts/core/runtime_parts/66_route_view_composer.js')
actions=text('src/scripts/core/runtime_parts/67_route_static_actions.js')
runtime=diag
boot=text('src/scripts/core/runtime_parts/00_runtime_boot_and_content_library.js')

add('multiple-file-input', 'type="file"' in view and 'multiple' in view and 'readFiles' in actions)
add('collision-policy-visible', 'id="importCollisionPolicy"' in view and all(value in view for value in ['rename','replace','skip','reject']))
add('collision-policies-modeled', all(f"'{value}'" in store or f'"{value}"' in store for value in ['rename','replace','skip','reject']))
add('preview-is-pure', 'preview_writes_state' not in store and 'planImportTexts' in store and 'previewImportFiles' in store and 'Aucune écriture avant prévisualisation' in view)
add('confirmed-preview-required', 'requireConfirmed:true' in runtime and 'importPreviewConfirmed' in runtime and 'confirmImportPreview' in runtime)
add('transaction-write-ahead', 'IMPORT_TRANSACTION_KEY' in boot and 'transactionSnapshot' in store and 'storage.setItem(IMPORT_TRANSACTION_KEY' in store)
add('rollback-on-failure', 'restoreTransactionSnapshot' in store and 'rolledBack:true' in store and 'faultAt' in store)
add('interrupted-transaction-recovery', 'recoverInterruptedImport' in store and 'storage.removeItem(IMPORT_TRANSACTION_KEY)' in store)
add('built-in-replacement-protected', 'builtin-replace-forbidden' in store and "policy==='replace'" in store)
add('diagnostic-taxonomy', 'learnit.kit_diagnostics.v2' in diag and all(sev in diag for sev in ["'blocker'","'warning'","'advice'"]))
add('diagnostic-corrections', all(token in diag for token in ['code','severity','message','correction']))
add('diagnostic-pedagogical-coverage', all(code in diag for code in ['objective-no-validation','objective-no-remediation','objective-no-transfer','course-format-imbalance']))
add('diagnostic-media-integrity', all(code in diag for code in ['asset-id-duplicate','media-reference-missing','asset-alt-missing','svg-unsafe','asset-unused']))
add('human-first-preview', 'Prévisualisation sans écriture' in diag and 'Voir le plan détaillé' in diag and 'transaction' in diag.lower())
add('important-actions-present', all(x in view or x in runtime for x in ['data-action="preview-import"','data-action="apply-import"','data-action="export-content"','data-action="rollback-import"']))
add('test-api-exposes-new-contracts', 'kitDiagnostics:' in runtime and 'importPlan:' in runtime)

report={'schema':'learnit.rc612.tools_import_surface_gate.v1','ok':all(c['ok'] for c in checks),'checks':checks}
(ROOT/'reports/contract_import_surface_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks),'report':'reports/contract_import_surface_report.json'},ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
