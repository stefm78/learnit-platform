#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, tempfile, sys
from pathlib import Path
from support import ROOT

checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':str(detail)})

def execute(files,expr):
    code="global.window=global;global.performance={now:()=>0};global.TextEncoder=TextEncoder;\n"
    for path in files: code+=f"eval(require('fs').readFileSync({json.dumps(str(path))},'utf8'));\n"
    code+=f"const r={expr};console.log(JSON.stringify(r));process.exit(r.ok?0:1);"
    return subprocess.run(['node','-e',code],cwd=ROOT,capture_output=True,text=True)

def mutated(path,replacements):
    text=path.read_text(encoding='utf-8')
    for old,new in replacements:
        assert old in text,(path,old)
        text=text.replace(old,new,1)
    temp=tempfile.NamedTemporaryFile('w',suffix='.js',delete=False,encoding='utf-8');temp.write(text);temp.close();return Path(temp.name)

perf=ROOT/'src/learning/performance_budget_model.js'
session=ROOT/'src/learning/session_mode_model.js'
remediation=ROOT/'src/learning/remediation_model.js'
orig=execute([perf], 'window.LearnItPerformanceBudgetModel.selfTest()')
add('original-performance-self-test',orig.returncode==0,(orig.stdout or orig.stderr)[-500:])
mp=mutated(perf,[('finite(value)<=finite(budget)','finite(value)<finite(budget)')])
r=execute([mp], 'window.LearnItPerformanceBudgetModel.selfTest()');add('mutation-budget-boundary-killed',r.returncode!=0,(r.stdout or r.stderr)[-500:]);mp.unlink(missing_ok=True)
ms=mutated(session,[('recordProgress:false,assessment:true','recordProgress:true,assessment:true')])
r=execute([remediation,ms], 'window.LearnItSessionModeModel.selfTest()');add('mutation-diagnostic-progress-killed',r.returncode!=0,(r.stdout or r.stderr)[-500:]);ms.unlink(missing_ok=True)
mr=mutated(remediation,[('Object.freeze([24,72,168,336,720])','Object.freeze([24,48,168,336,720])')])
r=execute([mr], 'window.LearnItRemediationModel.selfTest()');add('mutation-spaced-interval-killed',r.returncode!=0,(r.stdout or r.stderr)[-500:]);mr.unlink(missing_ok=True)
report={'schema':'learnit.rc659.targeted_mutation_gate.v1','ok':all(c['ok'] for c in checks),'killed':sum(1 for c in checks if c['code'].startswith('mutation-') and c['ok']),'mutations':3,'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/mutation_core_contracts_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(0 if report['ok'] else 1)
