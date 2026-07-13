#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from support import ROOT, active_script_paths
checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':detail})
active=active_script_paths(); model_path='src/learning/retention_protocol_model.js'
add('retention-model-active',model_path in active)
state=(ROOT/'src/scripts/core/runtime_parts/10_content_store_and_state.js').read_text(encoding='utf-8')
session=(ROOT/'src/scripts/core/runtime_parts/20_session_answer_activity_rendering.js').read_text(encoding='utf-8')
bridge=(ROOT/'src/scripts/core/runtime_parts/74_learning_evidence_runtime.js').read_text(encoding='utf-8')
add('retention-state-course-scoped',all(t in state for t in ['retentionByCourseId','courseRetention','setCourseRetention','retentionStatus']))
add('validation-creates-protocol','fromAssessment' in session and 'completed.retentionProtocol' in session)
add('runtime-bridge-exposes-evidence',all(t in bridge for t in ['learningCoverageReport','retentionProtocolReport','recordRetentionCheckpoint']))
node=f"""
global.window=global;require({json.dumps(str(ROOT/model_path))});const M=window.LearnItRetentionProtocolModel;const a=M.audit();if(!a.ok)throw new Error('audit');
const p=M.schedule('c','2026-01-01T00:00:00Z',['o'],['t']);const s=M.status(p,'2026-01-04T00:00:00Z');if(s.retentionDemonstrated||s.completedCount!==0||s.dueCount!==2)throw new Error('premature claim');console.log(JSON.stringify({{ok:true,due:s.dueCount}}));
"""
r=subprocess.run(['node','-e',node],cwd=ROOT,capture_output=True,text=True)
add('retention-node-behavior',r.returncode==0,(r.stderr or r.stdout)[-1400:])
report={'schema':'learnit.rc701.retention_protocol_contract.v1','ok':all(c['ok'] for c in checks),'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/contract_retention_protocol_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks),'report':'reports/contract_retention_protocol_report.json'},ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
