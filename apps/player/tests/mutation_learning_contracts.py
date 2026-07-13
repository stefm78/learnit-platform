#!/usr/bin/env python3
from __future__ import annotations
import json,subprocess,tempfile,sys
from pathlib import Path
from support import ROOT
checks=[]
def add(code,ok,detail=''):checks.append({'code':code,'ok':bool(ok),'detail':str(detail)})
def run(files,expr):
 code='global.window=global;\n'+''.join(f"eval(require('fs').readFileSync({json.dumps(str(p))},'utf8'));\n" for p in files)+f"const r={expr};console.log(JSON.stringify(r));process.exit(r.ok?0:1);"
 return subprocess.run(['node','-e',code],cwd=ROOT,capture_output=True,text=True)
def mutant(path,old,new):
 s=path.read_text();assert old in s,(path,old);p=Path(tempfile.mkstemp(suffix='.js')[1]);p.write_text(s.replace(old,new,1));return p
cov=ROOT/'src/learning/learning_coverage_model.js';ret=ROOT/'src/learning/retention_protocol_model.js'
r=run([cov],'window.LearnItLearningCoverageModel.audit()');add('coverage-original-pass',r.returncode==0,(r.stderr or r.stdout)[-500:])
m=mutant(cov,"if(levels.transfer&&!farTransfer)gaps.push('far-transfer-probe-missing');","if(false)gaps.push('far-transfer-probe-missing');")
r=run([m],"(()=>{const M=window.LearnItLearningCoverageModel;const x=M.courseCoverage({activities:[{id:'r',objective:'O',learning_phase:'activation',assessment_role:'practice'},{id:'c',objective:'O',learning_phase:'comprehension',assessment_role:'diagnostic'},{id:'a',objective:'O',learning_phase:'application',assessment_role:'practice'},{id:'t',objective:'O',learning_phase:'transfer',assessment_role:'validation',transfer_probe:true,transfer_distance:'near'}]});return {ok:x.objectives[0].gaps.includes('far-transfer-probe-missing')}})()");add('far-transfer-mutation-killed',r.returncode!=0,(r.stderr or r.stdout)[-500:]);m.unlink()
r=run([ret],'window.LearnItRetentionProtocolModel.audit()');add('retention-original-pass',r.returncode==0,(r.stderr or r.stdout)[-500:])
m=mutant(ret,'retained:CHECKPOINTS.every(cp=>completed.some(done=>done.id===cp.id','retained:completed.length>0&&completed.every(cp=>completed.some(done=>done.id===cp.id')
r=run([m],"(()=>{const M=window.LearnItRetentionProtocolModel;let p=M.schedule('c','2026-01-01T00:00:00Z',['o'],['t']);p=M.record(p,'immediate',[{objectiveKey:'o',correct:true}],'2026-01-01T00:00:00Z');return {ok:!M.status(p,'2026-01-01T01:00:00Z').retentionDemonstrated}})()");add('premature-retention-mutation-killed',r.returncode!=0,(r.stderr or r.stdout)[-500:]);m.unlink()
report={'schema':'learnit.rc707.learning_mutation_gate.v1','ok':all(x['ok'] for x in checks),'mutations':2,'killed':sum(x['ok'] for x in checks if 'mutation-killed' in x['code']),'checks':checks};(ROOT/'reports/mutation_learning_contracts_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
