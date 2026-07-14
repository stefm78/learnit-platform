#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from support import ROOT
SELF=Path(__file__); REPORT=ROOT/'reports/contract_source_tree_report.json'
def main()->int:
 completed=subprocess.run([sys.executable,str(ROOT/'tests/contract_source_tree.py')],cwd=ROOT,capture_output=True,text=True)
 report=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {}
 payload={'schema':'learnit.first_storage_seam_source_tree_observability.v1','returncode':completed.returncode,'stdout':completed.stdout,'stderr':completed.stderr,'checks':report.get('checks',[])}
 SELF.write_text(SELF.read_text(encoding='utf-8')+'\n# SOURCE_TREE_DIAGNOSTIC='+json.dumps(payload,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
 print(json.dumps(payload,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())

# SOURCE_TREE_DIAGNOSTIC={"checks":[{"code":"working-file-budget","detail":"148","ok":true},{"code":"canonical-doc-budget","detail":"['ENGINEERING.md', 'HUMAN_VALIDATION.md']","ok":true},{"code":"no-history-directory","detail":"","ok":true},{"code":"no-legacy-or-quarantine","detail":"","ok":true},{"code":"no-inactive-monoliths","detail":"","ok":true},{"code":"all-src-files-manifest-owned","detail":"unowned=[]","ok":true},{"code":"all-tests-registered","detail":"unregistered=[], missing=[]","ok":true},{"code":"runtime-fingerprint-declared","detail":"a2baa53db1c4d232073b79bf4f08c7245b756182dc3a98b830187fdddee32fca","ok":true},{"code":"protected-css-semantics-preserved-outside-authorized-style-files","detail":"a379d4516bbc7ad96f3964c3f59d5ba2921086026a8b4ed562990c94275235ca","ok":true},{"code":"protected-runtime-js-preserved-outside-authorized-owner-files","detail":"d9d078c482250ccdc63042823a7dcab9662d117135d504c686fbb9eefdec2d73","ok":true},{"code":"generated-dirs-gitignored","detail":"","ok":true}],"returncode":0,"schema":"learnit.first_storage_seam_source_tree_observability.v1","stderr":"","stdout":"{\n  \"ok\": true,\n  \"passed\": 11,\n  \"total\": 11,\n  \"report\": \"reports/contract_source_tree_report.json\"\n}\n"}
