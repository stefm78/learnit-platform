#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from support import ROOT
sys.path.insert(0,str(ROOT/'dev'))
from authoring_alignment import course_metrics
from tools.validate_kit import validate_payload
checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':detail})
paths=[ROOT/'data/golden-kits/golden_nombres_complexes.json',ROOT/'data/golden-kits/golden_signaux_electriques.json']
for path in paths:
    payload=json.loads(path.read_text(encoding='utf-8')); report=validate_payload(payload); activities=payload['courses'][0]['activities']; by={a['id']:a for a in activities}; probes=[a for a in activities if a.get('transfer_probe') is True]; objectives=set(a['objective'] for a in activities)
    add(path.stem+'-strict-valid',report['ok'] and report['summary']=={'errors':0,'warnings':0},report['summary'])
    add(path.stem+'-probe-per-objective',all(any(p['objective']==o for p in probes) for o in objectives),[p['id'] for p in probes])
    add(path.stem+'-far-validation-per-objective',all(any(p['objective']==o and p.get('transfer_distance')=='far' and p.get('assessment_role')=='validation' for p in probes) for o in objectives),[p['id'] for p in probes])
    add(path.stem+'-variant-links-resolve',all(p.get('variant_of') in by and p.get('variant_of')!=p['id'] for p in probes),[(p['id'],p.get('variant_of')) for p in probes])
    add(path.stem+'-far-probes-not-verbatim',all(p['question'].strip().lower()!=by[p['variant_of']]['question'].strip().lower() for p in probes if p.get('transfer_distance')=='far'),[p['id'] for p in probes])
report={'schema':'learnit.rc700.transfer_probe_contract.v1','ok':all(c['ok'] for c in checks),'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/contract_transfer_probes_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks),'report':'reports/contract_transfer_probes_report.json'},ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
