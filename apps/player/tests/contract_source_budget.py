#!/usr/bin/env python3
"""RC715 active source-size budget gate.

The goal is not arbitrary smallness. It prevents regressions back to huge monoliths
or hidden corrective piles by enforcing explicit budgets on active files.
"""
from __future__ import annotations
from pathlib import Path
import json, sys
from support import ROOT, active_script_paths, active_style_paths, load_manifest

budgets={
  'runtime_part_max_lines': 460,
  'runtime_part_max_bytes': 60_000,
  'app_shell_max_bytes': 12_000,
  'compiled_css_max_bytes': 180_000,
  'style_part_max_lines': 620,
  'activity_module_max_lines': 520,
  'enhancement_max_lines': 900,
  'active_js_total_max_bytes': 720_000,
  'active_css_total_max_bytes': 190_000,
}
checks=[]
def add(code,ok,detail=''):
    checks.append({'code':code,'ok':bool(ok),'detail':detail})

def lines(rel):
    return (ROOT/rel).read_text(encoding='utf-8',errors='ignore').count('\n')+1

def size(rel):
    return (ROOT/rel).stat().st_size
scripts=active_script_paths(); styles=active_style_paths()
active_js_total=sum(size(p) for p in scripts)
active_css_total=sum(size(p) for p in styles)
build_report_path=ROOT/'reports'/'build_report.json'
build_report=json.loads(build_report_path.read_text(encoding='utf-8')) if build_report_path.exists() else {}
compiled_css_bytes=int(build_report.get('compiledStyleBytes',10**9))
add('active-js-total-budget', active_js_total <= budgets['active_js_total_max_bytes'], str(active_js_total))
add('active-css-total-budget', active_css_total <= budgets['active_css_total_max_bytes'], str(active_css_total))
add('compiled-css-budget', compiled_css_bytes <= budgets['compiled_css_max_bytes'], str(compiled_css_bytes))
for rel in scripts:
    if rel.startswith('src/scripts/core/runtime_parts/'):
        add('runtime-part-line-budget-'+Path(rel).name, lines(rel) <= budgets['runtime_part_max_lines'], str(lines(rel)))
        add('runtime-part-byte-budget-'+Path(rel).name, size(rel) <= budgets['runtime_part_max_bytes'], str(size(rel)))
    if rel.startswith('src/activities/'):
        add('activity-module-budget-'+Path(rel).name, lines(rel) <= budgets['activity_module_max_lines'], str(lines(rel)))
    if rel.startswith('src/scripts/enhancements/'):
        add('enhancement-budget-'+Path(rel).name, lines(rel) <= budgets['enhancement_max_lines'], str(lines(rel)))
for rel in styles:
    if rel.startswith('src/styles/parts/'):
        add('style-part-budget-'+Path(rel).name, lines(rel) <= budgets['style_part_max_lines'], str(lines(rel)))
add('app-shell-byte-budget', size('src/scripts/core/runtime_parts/60_app_runtime_and_test_api.js') <= budgets['app_shell_max_bytes'], str(size('src/scripts/core/runtime_parts/60_app_runtime_and_test_api.js')))
# Explicitly ensure the old monoliths are not active.
add('no-active-core-monolith', 'src/scripts/core/00_app_runtime_monolith.js' not in scripts)
add('no-active-css-monolith', 'src/styles/app.css' not in styles)
report={'schema':'learnit.rc712.source_budget_gate.v1','ok':all(c['ok'] for c in checks),'budgets':budgets,'totals':{'activeJsBytes':active_js_total,'activeCssBytes':active_css_total,'compiledCssBytes':compiled_css_bytes},'checks':checks,'summary':{'total':len(checks),'passed':sum(c['ok'] for c in checks),'failed':sum(not c['ok'] for c in checks)}}
(ROOT/'reports/contract_source_budget_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
