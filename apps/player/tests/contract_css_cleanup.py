#!/usr/bin/env python3
from __future__ import annotations
import json,subprocess,sys
from support import ROOT
r=subprocess.run([sys.executable,'dev/css_semantic_audit.py'],cwd=ROOT,capture_output=True,text=True)
p=json.loads((ROOT/'reports/css_semantic_audit.json').read_text()) if (ROOT/'reports/css_semantic_audit.json').exists() else {}
t=p.get('totals',{}); checks=[
 {'code':'css-audit-runs','ok':r.returncode==0,'detail':(r.stderr or r.stdout)[-1000:]},
 {'code':'no-exact-duplicate-rules','ok':t.get('exactDuplicateRuleGroups')==0,'detail':t.get('exactDuplicateRuleGroups')},
 {'code':'no-shadowed-same-selector-properties','ok':t.get('shadowedSameSelectorPropertyDeclarations')==0,'detail':t.get('shadowedSameSelectorPropertyDeclarations')},
]
report={'schema':'learnit.rc705.css_cleanup_contract.v1','ok':all(x['ok'] for x in checks),'checks':checks,'totals':t};(ROOT/'reports/contract_css_cleanup_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':report['ok'],'passed':sum(x['ok'] for x in checks),'total':len(checks),'report':'reports/contract_css_cleanup_report.json'},ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
