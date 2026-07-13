#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'/'browser_remediation_loop_report.json'

def main()->int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content((ROOT/'dist/learnit.html').read_text(encoding='utf-8'),wait_until='domcontentloaded')
            page.wait_for_timeout(350)
            result=page.evaluate("""async()=>{
              const r=window.__LEARNIT_TEST__.runtime;
              const wait=()=>new Promise(ok=>setTimeout(ok,40));
              r.appState.resetAll();
              r.contentStore.setActiveCourse(r.contentStore.courseList()[0].courseId);
              r.appState.alignWithContent();
              const a1=r.contentStore.content.activities.find(a=>a.id==='a1');
              const model=window.LearnItRemediationModel;
              for(let i=0;i<2;i++)r.appState.recordActivityProgress(a1.id,{correct:false,expected:'6 V'},a1,{mode:'normal',at:`2026-01-01T0${i}:00:00Z`});
              r.appState.state.lastBilan={done:1,correct:0,total:1,review:[a1.id],mode:'normal'};
              r.appState.save();
              const progress=r.appState.courseProgress();
              const plan=model.buildPlan(r.contentStore.content,progress,r.appState.state.lastBilan,{maxItems:5,maxRounds:2});

              r.session.startTargetedReview([a1.id],{summary:'feedback test',focus:a1.objective,maxRounds:2});
              r.answer.reset();r.go('session');await wait();
              r.answer.selectQcm(1);r.answer.validate();await wait();
              const feedback={data:JSON.parse(JSON.stringify(r.answer.feedback)),hasHypothesis:!!document.querySelector('.feedback-error-hypothesis'),retryLabel:[...document.querySelectorAll('button')].some(b=>/Réessayer autrement/.test(b.textContent))};
              const nonceBefore=Number((r.session.session.retryNonceByActivity||{})[a1.id]||0);
              r.answer.retry();await wait();
              const retry={nonceBefore,nonceAfter:Number((r.session.session.retryNonceByActivity||{})[a1.id]||0),pending:r.answer.pending,feedback:r.answer.feedback};

              r.answer.selectQcm(1);r.answer.validate();await wait();
              const rowAfter=r.appState.courseProgress()[a1.id];
              r.appState.state.lastBilan={done:1,correct:0,total:1,review:[a1.id],mode:'targeted-review'};
              r.appState.save();
              const stopped=model.buildPlan(r.contentStore.content,r.appState.courseProgress(),r.appState.state.lastBilan,{maxItems:5,maxRounds:2});

              for(let i=0;i<10;i++)r.appState.recordActivityProgress(a1.id,{correct:i%2===0,expected:'6 V'},a1,{mode:'normal',at:`2026-02-${String(i+1).padStart(2,'0')}T00:00:00Z`});
              const bounded=r.appState.courseProgress()[a1.id];

              // Deterministic spaced schedule and migration-safe state.
              const base='2026-03-01T00:00:00Z';
              const first=model.recordProgress({}, {correct:true,expected:'6 V'}, a1, {mode:'normal',at:base});
              const early=model.buildDuePlan(r.contentStore.content,{[a1.id]:first},{now:Date.parse('2026-03-01T12:00:00Z'),maxItems:8});
              const due=model.buildDuePlan(r.contentStore.content,{[a1.id]:first},{now:Date.parse('2026-03-02T01:00:00Z'),maxItems:8});
              const second=model.recordProgress(first,{correct:true,expected:'6 V'},a1,{mode:'spaced-review',at:'2026-03-02T01:00:00Z'});
              const failed=model.recordProgress(second,{correct:false,expected:'6 V'},a1,{mode:'spaced-review',at:'2026-03-05T02:00:00Z'});
              const synthetic={activities:Array.from({length:12},(_,i)=>({id:`s${i}`,type:'qcm',objective:`O${i}`}))};
              const syntheticProgress=Object.fromEntries(synthetic.activities.map((a,i)=>[a.id,{seen:true,correct:true,reviewLevel:1,nextReviewAt:`2026-01-${String(i+1).padStart(2,'0')}T00:00:00Z`,lastAt:'2026-01-01T00:00:00Z'}]));
              const capped=model.buildDuePlan(synthetic,syntheticProgress,{now:Date.parse('2026-04-01T00:00:00Z'),maxItems:8});

              // Bilan promotes due review and starts the dedicated mode without extra UI layers.
              r.appState.state.activityProgressByCourseId[r.contentStore.activeCourseId]={[a1.id]:first};
              r.appState.state.session={status:'completed',mode:'normal',currentIndex:0,queue:[a1.id],answers:{[a1.id]:{correct:true,expected:'6 V',at:base}},contentVersion:r.contentStore.content.contentVersion};
              r.appState.state.lastBilan={done:1,correct:1,total:1,review:[],mode:'normal'};
              r.appState.save();
              r.go('bilan');await wait();
              const panel=typeof r.routePanel==='function'?r.routePanel('bilan'):document;
              const button=panel&&panel.querySelector('[data-rc247-action="start-due"]');
              const bilan={hasButton:!!button,label:button&&button.textContent.trim(),text:r.root.innerText};
              if(button){button.click();await wait();}
              const started={mode:r.session.session.mode,queue:r.session.queue(),hasBanner:!!document.querySelector('.remediation-banner'),banner:document.querySelector('.remediation-banner')?.innerText||''};

              // Purposeful variety: diagnose weak variants, separate avoidable repetitions and preserve answer mapping.
              const varietyModel=window.LearnItVarietyModel;
              const varietyCourse={contentVersion:'variety-browser-v1',title:'Variety browser',activities:[
                {id:'vq1',type:'qcm',objective:'Appliquer U = R × I',question:'Quelle tension obtient-on avec U égale R fois I ?',choices:['six volts','trois volts'],answer:0,common_errors:['confondre multiplication et division'],learning_phase:'application'},
                {id:'vq2',type:'qcm',objective:'Appliquer U = R × I',question:'Quelle tension obtient-on ici avec U égale R fois I ?',choices:['six volts','trois volts'],answer:0,common_errors:['confondre multiplication et division'],learning_phase:'application'},
                {id:'vo1',type:'order',objective:'Appliquer U = R × I',question:'Ordonne les étapes pour appliquer la loi d Ohm.',tokens:['Écrire la formule','Remplacer','Calculer'],answer:['Écrire la formule','Remplacer','Calculer'],common_errors:['confondre multiplication et division'],learning_phase:'remediation'},
                {id:'vf1',type:'flashcard',objective:'Identifier une unité',question:'Quelle est l unité de la tension ?',answer:'volt',learning_phase:'activation'}
              ]};
              const audit=varietyModel.auditCourse(varietyCourse);
              const sequence1=varietyModel.sequenceIds(varietyCourse,['vq1','vq2','vo1','vf1'],{seed:'browser-seed',mode:'review'});
              const sequence2=varietyModel.sequenceIds(varietyCourse,['vq1','vq2','vo1','vf1'],{seed:'browser-seed',mode:'review'});
              const variantProgress={vq1:{seen:true,review:true,failureCount:2,failureStreak:2,commonErrors:['confondre multiplication et division']}};
              const variantPlan=model.buildPlan(varietyCourse,variantProgress,{review:['vq1']},{maxItems:3,maxRounds:2});

              r.session.start();r.answer.reset();r.go('session');await wait();
              const sessionVariety={queue:r.session.queue(),plan:JSON.parse(JSON.stringify(r.session.session.varietyPlan||{})),seed:!!r.session.session.varietySeed,allIds:r.contentStore.content.activities.map(a=>a.id)};
              r.session.startTargetedReview([a1.id],{summary:'qcm mapping'});r.answer.reset();r.go('session');await wait();
              const qcmOrder1=[...r.renderer.qcmOrder(a1)],qcmOrder2=[...r.renderer.qcmOrder(a1)];
              r.answer.selectQcm(a1.answer);r.answer.validate();await wait();
              const qcmMapping={order1:qcmOrder1,order2:qcmOrder2,correct:r.answer.feedback&&r.answer.feedback.correct,expected:r.answer.feedback&&r.answer.feedback.expected,sourceExpected:a1.choices[a1.answer]};
              const qualityPayload={kind:'learnit-course-package',schema_version:'learnit.import.v1.1',packageId:'variety-diagnostic',source:'browser',assets:[],generation_report:{},courses:[{schemaVersion:'learnit-content-v2',...varietyCourse,sequence:'test',objectives:['Appliquer U = R × I']}]};
              const quality=window.__LEARNIT_TEST__.pedagogicalQuality(JSON.stringify(qualityPayload));

              // RC573-RC579: five public modes share one orchestration policy model.
              r.appState.resetAll();
              r.contentStore.setActiveCourse(r.contentStore.courseList()[0].courseId);
              r.appState.alignWithContent();
              r.go('learn');await wait();
              const modeModel=window.LearnItSessionModeModel;
              const modeButtons=[...(typeof r.routePanel==='function'?r.routePanel('learn'):document).querySelectorAll('[data-rc580-intent]')].map(b=>({id:b.dataset.mode||b.dataset.rc580Intent,intent:b.dataset.rc580Intent,label:b.textContent.trim()}));
              const discoveryPlan=modeModel.buildPlan(r.contentStore.content,r.appState.courseProgress(),'discovery');
              r.appState.recordActivityProgress('a1',{correct:false,expected:'6 V'},a1,{mode:'training',at:'2026-05-01T00:00:00Z'});
              const reviewPlan=modeModel.buildPlan(r.contentStore.content,r.appState.courseProgress(),'review',{now:Date.parse('2026-05-02T12:00:00Z')});

              const validationPlan=r.session.startMode('validation');r.answer.reset();r.go('session');await wait();
              const validationActivity=r.session.currentActivity();
              if(validationActivity.type==='qcm')r.answer.selectQcm((Number(validationActivity.answer)+1)%validationActivity.choices.length);
              r.answer.validate();await wait();
              const validation={plan:validationPlan,activityType:validationActivity.type,feedback:JSON.parse(JSON.stringify(r.answer.feedback)),actualAnswer:JSON.parse(JSON.stringify(r.session.session.answers[validationActivity.id]||{})),uiText:r.root.innerText,hasRetry:!!document.querySelector('[data-action="retry"]'),objectiveVisible:r.root.innerText.includes(validationActivity.objective||'__missing__')};
              r.session.session.status='completed';r.appState.state.lastBilan=r.session.summary();r.appState.save();r.go('bilan');await wait();
              validation.bilanText=(typeof r.routePanel==='function'?r.routePanel('bilan'):r.root).innerText;

              const beforeDiagnostic=JSON.stringify(r.appState.courseProgress());
              const diagnosticPlan=r.session.startMode('diagnostic');r.answer.reset();r.go('session');await wait();
              const diagnosticActivity=r.session.currentActivity();
              if(diagnosticActivity.type==='qcm')r.answer.selectQcm((Number(diagnosticActivity.answer)+1)%diagnosticActivity.choices.length);
              r.answer.validate();await wait();
              const afterDiagnosticAnswer=JSON.stringify(r.appState.courseProgress());
              r.session.moveNext();r.answer.reset();await wait();
              const afterDiagnosticNext=JSON.stringify(r.appState.courseProgress());
              const diagnostic={plan:diagnosticPlan,activityType:diagnosticActivity.type,feedback:JSON.parse(JSON.stringify(r.answer.feedback)),beforeDiagnostic,afterDiagnosticAnswer,afterDiagnosticNext,storedPolicy:r.appState.state.sessionByCourseId[r.contentStore.activeCourseId]?.modePolicy||null};

              const priorDiagnosticAnswers=Object.keys(r.session.session.answers||{}).length;
              const transitionPlan=r.session.startMode('validation');r.answer.reset();await wait();
              const transition={priorDiagnosticAnswers,newMode:r.session.session.mode,newAnswers:Object.keys(r.session.session.answers||{}).length,pending:r.answer.pending,plan:transitionPlan};
              const modes={schema:modeModel.SCHEMA,list:modeModel.list(),buttons:modeButtons,discoveryPlan,reviewPlan,validation,diagnostic,transition};
              return {plan,feedback,retry,rowAfter,stopped,bounded,spaced:{first,early,due,second,failed,capped,bilan,started},variety:{audit,sequence1,sequence2,variantPlan,sessionVariety,qcmMapping,quality},modes};
            }""")
            plan=result['plan']; feedback=result['feedback']; retry=result['retry']; stopped=result['stopped']; bounded=result['bounded']; row=result['rowAfter']; spaced=result['spaced']; variety=result['variety']
            add('variant-precedes-source',bool(plan.get('ok')) and plan.get('queue',[None])[0] != 'a1' and 'a1' in plan.get('queue',[]),json.dumps(plan,ensure_ascii=False))
            add('queue-bounded',len(plan.get('queue',[]))<=5 and plan.get('maxRounds')==2,json.dumps(plan,ensure_ascii=False))
            add('wrong-feedback-is-actionable',bool(feedback['data'].get('commonErrors')) and feedback['hasHypothesis'] and feedback['retryLabel'],json.dumps(feedback,ensure_ascii=False))
            add('retry-resets-and-varies',retry['nonceAfter']==retry['nonceBefore']+1 and retry['pending'] is None and retry['feedback'] is None,json.dumps(retry,ensure_ascii=False))
            add('targeted-failure-cap-recorded',row.get('remediationExhausted') is True and row.get('remediationRounds')>=2,json.dumps(row,ensure_ascii=False))
            add('automatic-loop-blocked',stopped.get('exhaustedOnly') is True and not stopped.get('ok') and stopped.get('noInfiniteLoop') is True,json.dumps(stopped,ensure_ascii=False))
            add('attempt-history-bounded',len(bounded.get('attemptHistory',[]))<=8 and bounded.get('attempts',0)>=12,json.dumps(bounded,ensure_ascii=False))
            first=spaced['first']; second=spaced['second']; failed=spaced['failed']; capped=spaced['capped']
            add('first-success-scheduled',first.get('reviewLevel')==1 and first.get('reviewIntervalHours')==24 and first.get('nextReviewAt')=='2026-03-02T00:00:00.000Z',json.dumps(first,ensure_ascii=False))
            add('not-due-before-date',not spaced['early'].get('ok') and spaced['early'].get('totalDue')==0,json.dumps(spaced['early'],ensure_ascii=False))
            add('due-after-date',spaced['due'].get('queue')==['a1'] and spaced['due'].get('rows',[{}])[0].get('reason')=='scheduled',json.dumps(spaced['due'],ensure_ascii=False))
            add('success-extends-interval',second.get('reviewLevel')==2 and second.get('reviewIntervalHours')==72,json.dumps(second,ensure_ascii=False))
            add('failure-resets-schedule',failed.get('reviewLevel')==0 and failed.get('reviewIntervalHours')==8 and failed.get('review') is True,json.dumps(failed,ensure_ascii=False))
            add('daily-load-capped',len(capped.get('queue',[]))==8 and capped.get('totalDue')==12 and capped.get('deferredCount')==4 and capped.get('dailyLoadBounded') is True,json.dumps(capped,ensure_ascii=False))
            add('bilan-promotes-due-review',spaced['bilan']['hasButton'] and 'révision' in spaced['bilan']['label'].lower(),json.dumps(spaced['bilan'],ensure_ascii=False))
            add('dedicated-spaced-session-starts',spaced['started']['mode']=='spaced-review' and spaced['started']['queue']==['a1'] and spaced['started']['hasBanner'] and 'révision planifiée' in spaced['started']['banner'].lower(),json.dumps(spaced['started'],ensure_ascii=False))
            add('near-duplicate-detected',len(variety['audit'].get('nearDuplicates',[]))>=1,json.dumps(variety['audit'],ensure_ascii=False))
            add('queue-diversification-deterministic',variety['sequence1']['queue']==variety['sequence2']['queue'] and variety['sequence1']['after']['repeated']<=variety['sequence1']['before']['repeated'] and variety['sequence1']['preservesMembership'] is True,json.dumps(variety['sequence1'],ensure_ascii=False))
            add('remediation-chooses-meaningful-variant',variety['variantPlan'].get('queue',[None])[0]=='vo1' and variety['variantPlan'].get('reasons',[{}])[0].get('kind')=='variant',json.dumps(variety['variantPlan'],ensure_ascii=False))
            sv=variety['sessionVariety']
            add('session-persists-variety-plan',sv['seed'] and sv['plan'].get('deterministic') is True and len(sv['queue'])==len(set(sv['queue']))==len(sv['allIds']) and set(sv['queue'])==set(sv['allIds']),json.dumps(sv,ensure_ascii=False))
            qm=variety['qcmMapping']
            add('qcm-answer-mapping-preserved',qm['order1']==qm['order2'] and sorted(qm['order1'])==list(range(len(qm['order1']))) and qm['correct'] is True and qm['expected']==qm['sourceExpected'],json.dumps(qm,ensure_ascii=False))
            add('pedagogical-diagnostic-surfaces-repetition',variety['quality'].get('stats',{}).get('nearDuplicateCount',0)>=1 and any('formulations trop proches' in str(i.get('label','')).lower() for i in variety['quality'].get('items',[])),json.dumps(variety['quality'],ensure_ascii=False))
            modes=result['modes']; public_ids=['discovery','training','review','validation','diagnostic']
            add('five-mode-policy-published',modes['schema']=='learnit.session_modes.v1' and [row['id'] for row in modes['list']]==public_ids,json.dumps(modes['list'],ensure_ascii=False))
            add('guided-five-mode-entry-rendered',len(modes['buttons'])==5 and set(row['id'] for row in modes['buttons'])==set(public_ids) and modes['buttons'][0]['id']=='discovery' and modes['buttons'][1]['id']=='diagnostic',json.dumps(modes['buttons'],ensure_ascii=False))
            add('discovery-prefers-unseen',modes['discoveryPlan']['ok'] and modes['discoveryPlan']['unseenCount']>=1 and modes['discoveryPlan']['queue'][0]=='a1',json.dumps(modes['discoveryPlan'],ensure_ascii=False))
            add('review-prioritizes-fragile',modes['reviewPlan']['ok'] and modes['reviewPlan']['queue'][0]=='a1',json.dumps(modes['reviewPlan'],ensure_ascii=False))
            val=modes['validation']
            add('validation-is-deferred-assessment',val['plan']['policy']['feedbackTiming']=='deferred' and val['plan']['policy']['allowRetry'] is False and val['plan']['excludesFlashcards'] is True and val['activityType']!='flashcard',json.dumps(val,ensure_ascii=False))
            add('validation-feedback-does-not-leak',val['feedback'].get('deferred') is True and 'expected' not in val['feedback'] and val['actualAnswer'].get('expected') and 'Réponse enregistrée' in val['uiText'] and not val['hasRetry'] and not val['objectiveVisible'],json.dumps(val,ensure_ascii=False))
            add('validation-outcome-in-bilan','résultat · validation' in val['bilanText'].lower() and 'validation terminée' in val['bilanText'].lower(),val['bilanText'][:900])
            dia=modes['diagnostic']
            add('diagnostic-is-non-recording',dia['plan']['policy']['recordProgress'] is False and dia['plan']['excludesFlashcards'] is True and dia['activityType']!='flashcard' and dia['beforeDiagnostic']==dia['afterDiagnosticAnswer']==dia['afterDiagnosticNext'],json.dumps(dia,ensure_ascii=False))
            tr=modes['transition']
            add('mode-transition-clears-session-state',tr['priorDiagnosticAnswers']>=1 and tr['newMode']=='validation' and tr['newAnswers']==0 and tr['pending'] is None,json.dumps(tr,ensure_ascii=False))
            add('no-browser-errors',not errors,' | '.join(errors[-10:]))
        finally:
            browser.close()
    ok=all(r['ok'] for r in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc586.browser_learning_mode_guidance.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(r['ok'] for r in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
