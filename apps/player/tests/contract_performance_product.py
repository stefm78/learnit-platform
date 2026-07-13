#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from support import ROOT, active_script_paths, active_style_paths, load_manifest

checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':str(detail)})
manifest=load_manifest(); scripts=active_script_paths(); styles=active_style_paths()
perf_model=ROOT/'src/learning/performance_budget_model.js'
perf_runtime=ROOT/'src/scripts/core/runtime_parts/72_performance_scalability_runtime.js'
model=perf_model.read_text(encoding='utf-8'); runtime=perf_runtime.read_text(encoding='utf-8')
js_bytes=sum((ROOT/p).stat().st_size for p in scripts)
css_bytes=sum((ROOT/p).stat().st_size for p in styles)
html=ROOT/'dist/learnit.html'; html_bytes=html.stat().st_size if html.exists() else 10**9
add('current-release-metadata',manifest.get('rc')=='RC715' and 'RC715' in (ROOT/'src/template.html').read_text(encoding='utf-8'))
add('performance-model-active','src/learning/performance_budget_model.js' in scripts)
add('performance-runtime-active','src/scripts/core/runtime_parts/72_performance_scalability_runtime.js' in scripts)
add('measure-before-optimize',all(token in runtime for token in ['performance.now','originalRender','originalBoot','projection','storageMetrics']))
add('pure-projection-cache',all(token in runtime for token in ['originalLibraryProjection','originalBilanProjection','cacheByRuntime','dataRevision']))
add('explicit-cache-invalidation','invalidateProjectionCache' in runtime and 'AppState.prototype.save' in runtime and 'ContentStore.prototype.load' in runtime)
add('no-gesture-owner-in-performance',all(token not in runtime for token in ['pointerdown','pointermove','touchstart','preventDefault']))
add('model-self-test-present','selfTest' in model and 'classify(10,10).ok' in model)
add('active-js-budget',js_bytes<=700_000,js_bytes)
add('active-css-budget',css_bytes<=190_000,css_bytes)
add('active-html-budget',html_bytes<=900_000,html_bytes)
largest_runtime=max((ROOT/p).stat().st_size for p in scripts if p.startswith('src/scripts/core/runtime_parts/'))
add('largest-runtime-owner-budget',largest_runtime<=60_000,largest_runtime)
add('app-shell-budget',(ROOT/'src/scripts/core/runtime_parts/60_app_runtime_and_test_api.js').stat().st_size<=12_000,(ROOT/'src/scripts/core/runtime_parts/60_app_runtime_and_test_api.js').stat().st_size)
build_report=json.loads((ROOT/'reports/build_report.json').read_text(encoding='utf-8')) if (ROOT/'reports/build_report.json').exists() else {}
add('compiled-css-budget',int(build_report.get('compiledStyleBytes',10**9))<=180_000,build_report.get('compiledStyleBytes'))
add('css-build-savings',int(build_report.get('styleSavingsBytes',0))>0,build_report.get('styleSavingsBytes'))
node=f"""
global.window=global;global.performance={{now:()=>0}};global.TextEncoder=TextEncoder;
eval(require('fs').readFileSync({json.dumps(str(perf_model))},'utf8'));
const r=window.LearnItPerformanceBudgetModel.selfTest();console.log(JSON.stringify(r));process.exit(r.ok?0:1);
"""
proc=subprocess.run(['node','-e',node],cwd=ROOT,capture_output=True,text=True)
add('performance-model-self-test',proc.returncode==0,(proc.stdout or proc.stderr)[-1000:])
report={'schema':'learnit.rc712.performance_product_contract.v1','ok':all(c['ok'] for c in checks),'totals':{'activeJsBytes':js_bytes,'activeCssBytes':css_bytes,'activeHtmlBytes':html_bytes},'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/contract_performance_product_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks),'totals':report['totals']},ensure_ascii=False,indent=2));sys.exit(0 if report['ok'] else 1)
