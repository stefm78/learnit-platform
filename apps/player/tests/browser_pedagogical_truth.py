#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from support import ROOT

OUT = ROOT / 'reports' / 'browser_pedagogical_truth_report.json'


def main() -> int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    html=(ROOT/'dist'/'learnit.html').read_text(encoding='utf-8')
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    hollow={'kind':'learnit-course-package','schema_version':'learnit.import.v1.1','packageId':'hollow-metadata-rich','source':'automated truth probe','assets':[],'generation_report':{},'courses':[{'schemaVersion':'learnit-content-v2','contentVersion':'hollow-v1','title':'Métadonnées riches, apprentissage creux','sequence':'Rappel uniquement','objectives':['Mémoriser une liste'],'activities':[]}]}
    for i in range(8):
        hollow['courses'][0]['activities'].append({'id':f'hollow-{i}','type':'flashcard','objective':'Mémoriser une liste','question':f'Question de rappel {i+1}','answer':f'Réponse {i+1}','why':'Réponse déclarative.','remediation':'Relire la carte.','difficulty':'easy','learning_phase':'activation','assessment_role':'practice','common_errors':['oubli']})
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':900,'height':800}); page.set_default_timeout(8000)
            page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content(html,wait_until='domcontentloaded'); page.wait_for_timeout(400)
            report=page.evaluate('payload=>window.__LEARNIT_TEST__.pedagogicalQuality(JSON.stringify(payload))',hollow)
            add('quality-schema-v2',report.get('schema')=='learnit.pedagogical_quality.rc676.v2',report.get('schema'))
            add('raw-score-remains-auditable',isinstance(report.get('rawScore'),(int,float)) and report.get('rawScore')>=report.get('score',0),report)
            codes={row.get('code') for row in report.get('ceilings',[])}
            add('recall-only-kit-is-capped','no-application-or-transfer' in codes and report.get('effectiveCeiling')<=69,report)
            add('single-format-kit-is-capped','insufficient-interaction-variety' in codes and report.get('score')<=69,report)
            add('metadata-rich-hollow-kit-not-grade-a',report.get('grade')!='A' and report.get('score')<85,report)
            for path in [ROOT/'data/golden-kits/golden_nombres_complexes.json',ROOT/'data/golden-kits/golden_signaux_electriques.json']:
                payload=json.loads(path.read_text(encoding='utf-8'))
                golden=page.evaluate('payload=>window.__LEARNIT_TEST__.pedagogicalQuality(JSON.stringify(payload))',payload)
                add(f'{path.stem}-not-artificially-capped',golden.get('effectiveCeiling')==100 and not golden.get('ceilings') and golden.get('grade')=='A',golden)
            add('no-browser-errors',not errors,' | '.join(errors[-10:]))
        finally:
            browser.close()
    ok=all(row['ok'] for row in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc676.pedagogical_truth_matrix.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(row['ok'] for row in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__':
    raise SystemExit(main())
