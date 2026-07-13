#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from support import ROOT, active_script_paths
checks=[]
def add(code,ok,detail=''):checks.append({'code':code,'ok':bool(ok),'detail':detail})
active=active_script_paths();model=(ROOT/'src/learning/bilan_information_architecture_model.js').read_text();composer=(ROOT/'src/scripts/core/runtime_parts/66_route_view_composer.js').read_text();css=(ROOT/'src/styles/parts/50_bilan_tools.css').read_text()
add('bilan-ia-model-active','src/learning/bilan_information_architecture_model.js' in active)
add('one-primary-at-most-one-secondary',all(t in model for t in ['primaryActionCount:1','secondaryActionCount:rec.secondary?1:0','duplicatePrimaryActions:false']))
add('decision-first-surface',all(t in composer for t in ['data-decision-first','data-primary-action-count','data-secondary-action-count','ia.openStructure','ia.showBoundary']))
add('evidence-secondary-collapsed','<details class="bilan-structure"' in composer and '<details class="bilan-more"' in composer)
add('assessment-debrief-readable',all(t in composer for t in ['assessment-debrief','Voir le détail par objectif','outcome.debrief']) and '.assessment-debrief-row' in css)
node_code=f"""global.window={{}};require({json.dumps(str(ROOT/'src/learning/bilan_information_architecture_model.js'))});const M=window.LearnItBilanInformationArchitecture;const a=M.plan({{status:'not-started'}},{{secondary:{{mode:'diagnostic'}}}},null);const b=M.plan({{status:'fragile'}},{{secondary:null}},{{mode:'diagnostic',total:2,modeOutcome:{{}}}});if(!a.showBoundary||a.openStructure||!b.openStructure||!b.showAssessmentOutcome||!M.audit(b).ok)throw new Error('ia behavior');console.log(JSON.stringify({{ok:true,a,b}}));"""
node=subprocess.run(['node','-e',node_code],cwd=str(ROOT),capture_output=True,text=True)
add('bilan-ia-node-behavior',node.returncode==0,(node.stderr or node.stdout)[:1200])
report={'schema':'learnit.rc696.bilan_information_architecture_contract.v1','ok':all(c['ok'] for c in checks),'checks':checks}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/contract_bilan_information_architecture_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks),'report':'reports/contract_bilan_information_architecture_report.json'},ensure_ascii=False,indent=2));sys.exit(0 if report['ok'] else 1)
