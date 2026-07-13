#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from support import active_script_paths
OUT=ROOT/'reports/architecture_inventory.json'

def run():
    active=active_script_paths(); texts={p:(ROOT/p).read_text(encoding='utf-8') for p in active}
    removed=['src/learning/progression_by_course.js','src/learning/navigation_intent_model.js','src/learning/continuous_swipe_model.js']
    owner=json.loads((ROOT/'docs/OWNER_MAP.json').read_text(encoding='utf-8'))
    runtime=[p for p in active if '/runtime_parts/' in p]
    learning=[p for p in active if p.startswith('src/learning/')]
    globals={}
    for p in learning:
        for sym in re.findall(r'(?:global|window)\.([A-Za-z_$][\w$]*)\s*=',texts[p]): globals.setdefault(sym,[]).append(p)
    duplicate_globals={k:v for k,v in globals.items() if len(v)>1}
    prototype=[]
    for p,s in texts.items():
        prototype += [(m.group(1),p) for m in re.finditer(r'AppRuntime\.prototype\.([A-Za-z_$][\w$]*)\s*=',s)]
    by={}
    for name,p in prototype: by.setdefault(name,[]).append(p)
    duplicate_methods={k:v for k,v in by.items() if len(v)>1}
    missing_owners=[p for p in runtime if p not in owner.get('owners',{})]
    registered=owner.get('registered_decorators',{})
    unregistered_duplicates={k:v for k,v in duplicate_methods.items() if registered.get(k)!=v}
    checks=[
      {'code':'retired-unconsumed-models-absent','ok':all(p not in active and not (ROOT/p).exists() for p in removed),'detail':removed},
      {'code':'active-model-global-owners-unique','ok':not duplicate_globals,'detail':duplicate_globals},
      {'code':'runtime-prototype-decorators-registered','ok':not unregistered_duplicates,'detail':unregistered_duplicates},
      {'code':'runtime-owner-map-complete','ok':not missing_owners,'detail':missing_owners},
      {'code':'deferred-boot-name-version-neutral','ok':'src/scripts/enhancements/999_deferred_boot.js' in active and not any('deferred_boot_rc' in p for p in active),'detail':''},
    ]
    report={'schema':'learnit.rc703.architecture_inventory.v1','ok':all(x['ok'] for x in checks),'activeScripts':len(active),'runtimeOwners':len(runtime),'learningModels':len(learning),'prototypeMethodCount':len(prototype),'duplicatePrototypeMethods':duplicate_methods,'duplicateGlobalOwners':duplicate_globals,'checks':checks}
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return report
if __name__=='__main__':
 r=run();print(json.dumps({'ok':r['ok'],'passed':sum(x['ok'] for x in r['checks']),'total':len(r['checks']),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2));raise SystemExit(0 if r['ok'] else 1)
