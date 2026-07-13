#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, sys
from support import ROOT

COMPOSER = (ROOT / 'src/scripts/core/runtime_parts/66_route_view_composer.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src/styles/parts/50_bilan_tools.css').read_text(encoding='utf-8')
OUT = ROOT / 'reports/contract_entry_guidance_report.json'
checks=[]
def add(code,ok,detail=''):
    checks.append({'code':code,'ok':bool(ok),'detail':detail})

add('entry-guidance-schema-visible','data-entry-guidance="learnit.entry_guidance.rc658.v1"' in COMPOSER)
add('exactly-one-primary-role',COMPOSER.count('data-entry-role="primary"')==1,str(COMPOSER.count('data-entry-role="primary"')))
add('at-most-one-alternative-role',COMPOSER.count('data-entry-role="alternative"')==1,str(COMPOSER.count('data-entry-role="alternative"')))
add('primary-recommendation-label','Recommandé pour vous' in COMPOSER)
add('alternative-deemphasized','class="entry-alternative"' in COMPOSER and 'entry-choice secondary' not in COMPOSER)
add('diagnostic-boundary-explicit','Diagnostic' in COMPOSER and 'progression inchangée' in COMPOSER)
add('validation-boundary-explicit','Validation' in COMPOSER and 'progression enregistrée' in COMPOSER)
add('all-modes-collapsed','<details class="rc580-other-modes"><summary>Voir tous les modes</summary>' in COMPOSER)
add('desktop-primary-dominance','grid-template-columns:2fr .8fr' in CSS)
add('mobile-alternative-detail-collapsed','@media(max-width:820px)' in CSS and '.entry-alternative>span:last-child{display:none}' in CSS)
add('touch-targets-explicit','min-height:92px' in CSS and 'min-height:48px' in CSS and 'min-height:44px' in CSS)
add('source-css-budget-preserved',sum(p.stat().st_size for p in (ROOT/'src/styles/parts').glob('*.css')) < 180_000)

ok=all(c['ok'] for c in checks)
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps({'schema':'learnit.rc658.entry_guidance_contract.v1','ok':ok,'checks':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':ok,'passed':sum(c['ok'] for c in checks),'total':len(checks),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
sys.exit(0 if ok else 1)
