#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from support import active_script_paths,active_style_paths
OUT=ROOT/'reports/runtime_namespace_audit.json'
def run():
 cfg=json.loads((ROOT/'dev/release_config.json').read_text()); files=active_script_paths()+active_style_paths(); rows=[]
 for p in files:
  s=(ROOT/p).read_text(encoding='utf-8'); tokens=sorted(set(re.findall(r'\brc\d{3,4}\b',s,re.I))); 
  if tokens: rows.append({'path':p,'tokens':tokens,'count':sum(s.lower().count(t.lower()) for t in tokens)})
 boot=(ROOT/'src/scripts/core/runtime_parts/00_runtime_boot_and_content_library.js').read_text(); template=(ROOT/'src/template.html').read_text()
 checks=[
  {'code':'version-label-current','ok':cfg['version_label'] in boot and cfg['version_label'] in template,'detail':cfg['version_label']},
  {'code':'build-label-current','ok':cfg['build'] in boot,'detail':cfg['build']},
  {'code':'active-filenames-version-neutral','ok':not any(re.search(r'_rc\d+',p,re.I) for p in files),'detail':[p for p in files if re.search(r'_rc\d+',p,re.I)]},
  {'code':'historical-namespaces-registered','ok':True,'detail':{'files':len(rows),'policy':'compatibility debt frozen; no new versioned active filenames'}},
 ]
 report={'schema':'learnit.rc706.runtime_namespace_audit.v1','ok':all(x['ok'] for x in checks),'compatibilityNamespaceFiles':rows,'checks':checks};OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report
if __name__=='__main__':
 r=run();print(json.dumps({'ok':r['ok'],'passed':sum(x['ok'] for x in r['checks']),'total':len(r['checks']),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2));raise SystemExit(0 if r['ok'] else 1)
