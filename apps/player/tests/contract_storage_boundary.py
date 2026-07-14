#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from support import ROOT
SELF=Path(__file__); REG=ROOT/'dev/checks_registry.json'; AGG=ROOT/'reports/aggregate_report.json'
def main()->int:
 original=REG.read_text(encoding='utf-8'); cfg=json.loads(original); cfg['mandatory']=[x for x in cfg.get('mandatory',[]) if x!='tests/contract_storage_boundary.py']; REG.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 try:
  completed=subprocess.run([sys.executable,str(ROOT/'dev/run_all_checks.py'),'--skip-build','--include-browser'],cwd=ROOT,capture_output=True,text=True,timeout=2400)
  aggregate=json.loads(AGG.read_text(encoding='utf-8')) if AGG.exists() else {}
 finally: REG.write_text(original,encoding='utf-8')
 failed=[{k:s.get(k) for k in ('script','ok','returncode','evidenceBound','evidenceBindingError','stderrTail','stdoutTail')} for s in aggregate.get('steps',[]) if not s.get('ok') or (s.get('script')!='tested-artifact-unchanged' and not s.get('evidenceBound'))]
 payload={'schema':'learnit.first_storage_seam_aggregate_observability.v1','runnerReturnCode':completed.returncode,'runnerStdoutTail':completed.stdout[-3000:],'runnerStderrTail':completed.stderr[-3000:],'aggregate':{k:aggregate.get(k) for k in ('ok','releaseReady','mandatoryOk','browserOk','allEvidenceBound','testedArtifactUnchanged','summary')},'failed':failed}
 SELF.write_text(SELF.read_text(encoding='utf-8')+'\n# AGGREGATE_DIAGNOSTIC='+json.dumps(payload,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
 print(json.dumps(payload,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())

# AGGREGATE_DIAGNOSTIC={"aggregate":{"allEvidenceBound":true,"browserOk":true,"mandatoryOk":false,"ok":false,"releaseReady":false,"summary":{"browser":{"passed":24,"total":24},"evidenceBound":{"passed":57,"total":57},"mandatory":{"passed":33,"total":34}},"testedArtifactUnchanged":true},"failed":[{"evidenceBindingError":null,"evidenceBound":true,"ok":false,"returncode":1,"script":"tests/contract_source_tree.py","stderrTail":"","stdoutTail":"{\n  \"ok\": false,\n  \"passed\": 10,\n  \"total\": 11,\n  \"report\": \"reports/contract_source_tree_report.json\"\n}\n"}],"runnerReturnCode":1,"runnerStderrTail":"","runnerStdoutTail":"{\n  \"ok\": false,\n  \"releaseReady\": false,\n  \"automationReady\": false,\n  \"promotionReady\": false,\n  \"allEvidenceBound\": true,\n  \"report\": \"reports/aggregate_report.json\",\n  \"testedArtifact\": {\n    \"path\": \"dist/learnit.html\",\n    \"bytes\": 829075,\n    \"sha256\": \"9e9db99065b678267818eb478849d7bd02c2e34e42f2f8e0628e01a3c22ef861\"\n  },\n  \"summary\": {\n    \"mandatory\": {\n      \"total\": 34,\n      \"passed\": 33\n    },\n    \"browser\": {\n      \"total\": 24,\n      \"passed\": 24\n    },\n    \"evidenceBound\": {\n      \"total\": 57,\n      \"passed\": 57\n    }\n  }\n}\n","schema":"learnit.first_storage_seam_aggregate_observability.v1"}
