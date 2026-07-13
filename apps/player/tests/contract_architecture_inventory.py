#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from support import ROOT
sys.path.insert(0,str(ROOT/'dev'))
from architecture_inventory import run
r=run();print(json.dumps({'ok':r['ok'],'passed':sum(x['ok'] for x in r['checks']),'total':len(r['checks']),'report':'reports/architecture_inventory.json'},ensure_ascii=False,indent=2));raise SystemExit(0 if r['ok'] else 1)
