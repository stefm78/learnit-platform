#!/usr/bin/env python3
from __future__ import annotations
import json, sys, subprocess
from support import ROOT, active_script_paths, load_runtime_core
checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':detail})
rt=load_runtime_core()
model=(ROOT/'src/learning/bilan_decision_model.js').read_text(encoding='utf-8')
mastery=(ROOT/'src/learning/mastery_evidence_model.js').read_text(encoding='utf-8')
active=active_script_paths()

composer=(ROOT/'src/scripts/core/runtime_parts/66_route_view_composer.js').read_text(encoding='utf-8')
css=(ROOT/'src/styles/parts/50_bilan_tools.css').read_text(encoding='utf-8')
add('bilan-primary-action-hero', 'bilan-action-hero' in composer and 'Prochaine étape recommandée' in composer and 'data-evidence-reason' in composer)
add('bilan-secondary-details-collapsed', 'bilan-more' in composer and '<details class="bilan-more"' in composer)
add('bilan-no-duplicate-review-stack', 'rc241-review-freedom' not in composer and 'rc246-remediation-map' not in composer)
add('bilan-renders-explainable-evidence', all(token in composer for token in ['explainableEvidence','bilan-objective-row','evidence.statusLabel','evidence.recommendation','État des objectifs','État par chapitre']))
add('bilan-no-arbitrary-mastery-percentage', 'summary.mastery' not in composer and 's.mastery' not in composer and 'confirmer votre maîtrise' not in composer)
add('bilan-responsive-hero-css', '.rc532-bilan .bilan-action-hero' in css and '@media(max-width:520px)' in css)
add('bilan-mobile-no-nested-scroll', '.rc532-bilan .bilan-nav{max-height:none!important;overflow:visible!important}' in css)
add('bilan-course-title-wraps', '.bilan-hierarchy .bilan-course-row strong{overflow-wrap:anywhere' in css)
add('bilan-model-active', 'src/learning/bilan_decision_model.js' in active)
add('mastery-evidence-model-active', 'src/learning/mastery_evidence_model.js' in active)
add('mastery-model-truthful-spacing', all(token in mastery for token in ['successfulSpanHours','spacingThresholdHours','same-day-successes','span-under-24h']))
add('mastery-model-no-false-percentage', 'masteryPct' not in mastery and 'masteryPercent' not in mastery and 'scorePercent' not in mastery)
add('mastery-model-objective-owned', all(token in mastery for token in ['objectiveEvidence','normalizeObjective','chapterEvidence','courseEvidence']))
add('mastery-recommendation-explained', all(token in mastery for token in ['reasonCode','fragile-objectives','scheduled-review-due','no-evidence-yet','all-objectives-consolidated']))
node_code=f"""
global.window={{}};
require({json.dumps(str(ROOT/'src/learning/mastery_evidence_model.js'))});
const m=window.LearnItMasteryEvidenceModel;
function assert(v,msg){{if(!v)throw new Error(msg);}}
const courseA={{id:'c',title:'C',chapters:[{{id:'ch1',title:'Bases',ids:['a1','a2']}},{{id:'ch2',title:'Mesure',ids:['a3']}}],activities:[{{id:'a1',objective:"Loi d'Ohm"}},{{id:'a2',objective:"Loi d'Ohm"}},{{id:'a3',objective:'Mesurer I'}}]}};
const courseB={{...courseA,activities:[courseA.activities[2],courseA.activities[0],courseA.activities[1]]}};
const progress={{a1:{{seen:true,correct:true,attempts:2,successCount:2,reviewLevel:2,nextReviewAt:'2099-01-01T00:00:00Z',attemptHistory:[{{correct:true,at:'2026-01-01T00:00:00Z'}},{{correct:true,at:'2026-01-03T00:00:00Z'}}]}},a2:{{seen:true,correct:false,review:true,attempts:2,failureCount:2,attemptHistory:[{{correct:false,at:'2026-01-02T00:00:00Z'}}]}}}};
const a=m.explainCourse(courseA,progress,'2026-01-04T00:00:00Z');
const b=m.explainCourse(courseB,progress,'2026-01-04T00:00:00Z');
assert(m.schema==='learnit.mastery_evidence_model.rc675.v1','schema');
assert(a.objectives.length===2&&a.chapters.length===2,'aggregation');
assert(a.status===m.STATUS.FRAGILE&&a.recommendation.reasonCode==='fragile-objectives','fragile recommendation');
assert(JSON.stringify(a.objectives.map(x=>[x.key,x.status]))===JSON.stringify(b.objectives.map(x=>[x.key,x.status])),'objective state depends on source index');
assert(!('masteryPct' in a)&&!('score' in a),'false score exposed');
const fresh=m.explainCourse({{id:'n',title:'N',activities:[{{id:'n1',objective:'Nouveau'}}]}},{{}},'2026-01-04T00:00:00Z');
assert(fresh.status===m.STATUS.NOT_STARTED&&fresh.recommendation.reasonCode==='no-evidence-yet','fresh state');
const stable=m.explainCourse({{id:'s',title:'S',activities:[{{id:'s1',objective:'Stable'}}]}},{{s1:{{seen:true,correct:true,attempts:2,successCount:2,reviewLevel:2,nextReviewAt:'2099-01-01T00:00:00Z',attemptHistory:[{{correct:true,at:'2026-01-01T00:00:00Z'}},{{correct:true,at:'2026-01-03T00:00:00Z'}}]}}}},'2026-01-04T00:00:00Z');
assert(stable.status===m.STATUS.CONSOLIDATED&&stable.recommendation.reasonCode==='all-objectives-consolidated','stable state');
const sameDay=m.explainCourse({{id:'d',title:'D',activities:[{{id:'d1',objective:'Même jour'}}]}},{{d1:{{seen:true,correct:true,attempts:2,successCount:2,reviewLevel:4,nextReviewAt:'2099-01-01T00:00:00Z',attemptHistory:[{{correct:true,at:'2026-01-01T08:00:00Z'}},{{correct:true,at:'2026-01-01T18:00:00Z'}}]}}}},'2026-01-02T00:00:00Z');
assert(sameDay.status===m.STATUS.IN_PROGRESS,'same-day successes must not consolidate');
assert(sameDay.activities[0].spacedSuccess===false&&sameDay.activities[0].spacingReason==='same-day-successes','same-day spacing truth');
const shortCrossDay=m.explainCourse({{id:'x',title:'X',activities:[{{id:'x1',objective:'Trop rapproché'}}]}},{{x1:{{seen:true,correct:true,attempts:2,successCount:2,nextReviewAt:'2099-01-01T00:00:00Z',attemptHistory:[{{correct:true,at:'2026-01-01T23:30:00Z'}},{{correct:true,at:'2026-01-02T00:30:00Z'}}]}}}},'2026-01-02T01:00:00Z');
assert(shortCrossDay.status===m.STATUS.IN_PROGRESS&&shortCrossDay.activities[0].spacingReason==='span-under-24h','calendar-day boundary is not real spacing');
const implicit=m.chapterDefinitions({{title:'Implicit',objectives:['O1','O2','O3'],activities:[{{id:'i1',objective:'O1'}},{{id:'i2',objective:'O1'}},{{id:'i3',objective:'O2'}},{{id:'i4',objective:'O3'}}]}});
assert(implicit.length===2&&implicit[0].ids.length===2&&implicit[1].ids.length===2,'implicit chapter compatibility');
console.log(JSON.stringify({{ok:true,status:a.status,recommendation:a.recommendation.reasonCode,objectives:a.objectives.length,chapters:a.chapters.length}}));
"""
node=subprocess.run(['node','-e',node_code],cwd=str(ROOT),capture_output=True,text=True)
add('mastery-model-node-behavior',node.returncode==0,(node.stderr or node.stdout)[:1200])
add('bilan-hierarchy-view', 'bilan-two-pane' in rt and 'bilanCollections' in rt and 'bilanCourseSummary' in rt)
add('bilan-select-does-not-set-active', "action==='bilan-select-course'" in rt and "this.contentStore.setActiveCourse(el.dataset.course)" not in rt.split("action==='bilan-select-course'")[1].split("return;")[0])
add('bilan-guided-start-explicit', 'data-rc580-intent' in composer and 'nextAction(runtime' in composer and 'data-recommendation-code' in composer and 'Diagnostic</strong> au début' in composer and 'vérifier vos acquis' in composer)
add('bilan-chapters-list', 'bilan-chapter-row' in composer and 'evidence.chapters' in composer)
add('bilan-objective-list', 'bilan-objective-row' in composer and 'evidence.objectives' in composer)
add('summary-course-has-any', 'hasAny' in model and 'summarizeChapter' in model and 'summarizeCollection' in model)
add('css-bilan-part-active', 'src/styles/parts/50_bilan_tools.css' in json.dumps(json.loads((ROOT/'source_manifest.json').read_text(encoding='utf-8')).get('styles',[])))
report={'schema':'learnit.rc594.bilan_explainable_evidence_gate.v1','ok':all(c['ok'] for c in checks),'checks':checks}
(ROOT/'reports').mkdir(parents=True,exist_ok=True)
(ROOT/'reports/contract_bilan_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2)); sys.exit(0 if report['ok'] else 1)
