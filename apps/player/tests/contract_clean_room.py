#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from support import ROOT
OUT=ROOT/'reports/contract_clean_room_report.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def add(c,o,d=''):checks.append({'code':c,'ok':bool(o),'detail':str(d)})
with tempfile.TemporaryDirectory(prefix='learnit-clean-room-') as td:
 dst=Path(td)/'learnit';dst.mkdir()
 for name in ['src','contract','authoring','data','dev','docs','tests','tools']:
  shutil.copytree(ROOT/name,dst/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 for name in ['build.py','source_manifest.json','requirements-test.txt','README.md','Makefile','.gitignore']:
  shutil.copy2(ROOT/name,dst/name)
 r1=subprocess.run([sys.executable,'dev/update_manifest.py'],cwd=dst,capture_output=True,text=True)
 add('clean-room-manifest-refresh',r1.returncode==0,(r1.stderr or r1.stdout)[-1500:])
 r2=subprocess.run([sys.executable,'build.py'],cwd=dst,capture_output=True,text=True)
 add('clean-room-build',r2.returncode==0,(r2.stderr or r2.stdout)[-1500:])
 expected=ROOT/'dist/learnit.html';actual=dst/'dist/learnit.html'
 add('clean-room-byte-identical',actual.exists() and expected.exists() and sha(actual)==sha(expected),{'expected':sha(expected) if expected.exists() else '', 'actual':sha(actual) if actual.exists() else ''})
 valid=[]
 for rel in ['data/golden-kits/golden_nombres_complexes.json','data/golden-kits/golden_signaux_electriques.json']:
  rr=subprocess.run([sys.executable,'tools/validate_kit.py',rel],cwd=dst,capture_output=True,text=True);valid.append({'path':rel,'ok':rr.returncode==0,'tail':(rr.stderr or rr.stdout)[-500:]})
 add('clean-room-golden-validation',all(x['ok'] for x in valid),valid)
report={'schema':'learnit.rc711.clean_room_contract.v1','ok':all(x['ok'] for x in checks),'checks':checks};OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':report['ok'],'passed':sum(x['ok'] for x in checks),'total':len(checks),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
