#!/usr/bin/env python3
from __future__ import annotations
import json, sys, re
from pathlib import Path
from support import ROOT, active_script_paths, load_manifest

checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':str(detail)})
manifest=load_manifest(); scripts=active_script_paths(); owners=json.loads((ROOT/'docs/OWNER_MAP.json').read_text(encoding='utf-8'))
runtime=[p for p in scripts if p.startswith('src/scripts/core/runtime_parts/')]
owner_map=owners.get('owners',{})
add('runtime-owner-complete',set(runtime)==set(owner_map),json.dumps({'missing':sorted(set(runtime)-set(owner_map)),'extra':sorted(set(owner_map)-set(runtime))}))
add('active-script-paths-unique',len(scripts)==len(set(scripts)),len(scripts))
add('one-performance-owner',sum('performance' in v for v in owner_map.values())==1)
add('one-gesture-orchestrator',sum(v=='single-route-gesture-orchestrator' for v in owner_map.values())==1)
all_runtime='\n'.join((ROOT/p).read_text(encoding='utf-8',errors='ignore') for p in runtime)
add('no-mutation-observer',not re.search(r'\bnew\s+MutationObserver\b',all_runtime))
add('no-eval-runtime',not re.search(r'\beval\s*\(',all_runtime))
add('shell-method-boundaries',all(token not in (ROOT/'src/scripts/core/runtime_parts/60_app_runtime_and_test_api.js').read_text(encoding='utf-8') for token in ['handleClick(event)','handlePointerDown(event)','AUTOMATION_TEST_KIT','window.__LEARNIT_TEST__']),str((ROOT/'src/scripts/core/runtime_parts/60_app_runtime_and_test_api.js').stat().st_size))
add('test-api-before-accessibility',runtime.index('src/scripts/core/runtime_parts/73_runtime_test_api.js')<runtime.index('src/scripts/core/runtime_parts/71_accessibility_resilience_runtime.js'))
add('diagnostics-split-owned',all(p in runtime for p in ['src/scripts/core/runtime_parts/50_diagnostics_import_quality.js','src/scripts/core/runtime_parts/51_contract_pedagogy_diagnostics.js','src/scripts/core/runtime_parts/52_import_diagnostic_views.js']))
add('performance-before-deferred-boot',runtime.index('src/scripts/core/runtime_parts/72_performance_scalability_runtime.js')<runtime.index('src/scripts/core/runtime_parts/70_automation_and_boot.js'))
add('accessibility-before-performance',runtime.index('src/scripts/core/runtime_parts/71_accessibility_resilience_runtime.js')<runtime.index('src/scripts/core/runtime_parts/72_performance_scalability_runtime.js'))
add('frozen-gesture-files-present',all(p in runtime for p in ['src/scripts/core/runtime_parts/65_mobile_swipe_runtime.js','src/scripts/core/runtime_parts/69_gesture_orchestrator.js']))

install_token='AppRuntime.prototype.installMobileSwipeNavigation=function()'
install_owners=[path for path in runtime if install_token in (ROOT/path).read_text(encoding='utf-8',errors='ignore')]
add('single-mobile-swipe-installer',install_owners==['src/scripts/core/runtime_parts/69_gesture_orchestrator.js'],install_owners)
gesture_model=(ROOT/'src/learning/gesture_navigation_model.js').read_text(encoding='utf-8')
gesture_runtime=(ROOT/'src/scripts/core/runtime_parts/69_gesture_orchestrator.js').read_text(encoding='utf-8')
add('route-gesture-intent-model-consumed','LearnItRouteGestureIntentModel' in gesture_model and 'LearnItRouteGestureIntentModel' in gesture_runtime)
add('obsolete-nested-gesture-model-removed',all(token not in gesture_model for token in ['library-chapter','library-course-consultation','nextSibling']))
add('carousel-engine-has-no-input-listeners',all(token not in (ROOT/'src/scripts/core/runtime_parts/65_mobile_swipe_runtime.js').read_text(encoding='utf-8') for token in ['touchstart','pointerdown','installMobileSwipeNavigation']))

add('current-title-no-stale-baseline',f"Learn-it {manifest.get('rc')}" in (ROOT/'src/template.html').read_text(encoding='utf-8'))
report={'schema':'learnit.rc688.dependency_ownership_gate.v1','ok':all(c['ok'] for c in checks),'owners':owner_map,'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/contract_dependency_ownership_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks)},ensure_ascii=False,indent=2));sys.exit(0 if report['ok'] else 1)
