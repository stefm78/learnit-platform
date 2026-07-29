#!/usr/bin/env python3
"""Deterministic checks for the isolated Project Atlas M1 experience lane."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASELINE = "58e39e8917006058fdf177a5daa37535f5e2c78d"
STRICT = os.environ.get("ATLAS_EXPERIENCE_STRICT", "0") == "1"
MODULES = {
    "atlas_today.mjs": ROOT / "apps/learnit-next/src/ui/atlas_today.js",
    "atlas_session.mjs": ROOT / "apps/learnit-next/src/ui/atlas_session.js",
    "atlas_summary.mjs": ROOT / "apps/learnit-next/src/ui/atlas_summary.js",
    "atlas_rewards.mjs": ROOT / "apps/learnit-next/src/ui/atlas_rewards.js",
}
STYLES = ROOT / "apps/learnit-next/src/atlas.css"
EXPECTED_CHANGED_PATHS = {
    "apps/learnit-next/src/ui/atlas_today.js",
    "apps/learnit-next/src/ui/atlas_session.js",
    "apps/learnit-next/src/ui/atlas_summary.js",
    "apps/learnit-next/src/ui/atlas_rewards.js",
    "apps/learnit-next/src/atlas.css",
    "apps/learnit-next/tests/atlas_m1_experience.py",
}

DOM = r"""
class N {
  constructor(tag) { this.tagName=String(tag); this.attributes=new Map(); this.childNodes=[]; this.listeners=new Map(); this._text=''; }
  set className(v){this.setAttribute('class',v)} get className(){return this.getAttribute('class')||''}
  set textContent(v){this._text=String(v);this.childNodes=[]} get textContent(){return this._text+this.childNodes.map(x=>x.textContent).join('')}
  set disabled(v){if(v)this.setAttribute('disabled','');else this.attributes.delete('disabled')} get disabled(){return this.attributes.has('disabled')}
  setAttribute(k,v){this.attributes.set(String(k),String(v))} getAttribute(k){return this.attributes.get(String(k))??null}
  appendChild(x){if(!(x instanceof N))throw new TypeError('node required');this.childNodes.push(x);return x}
  addEventListener(k,f){if(!this.listeners.has(k))this.listeners.set(k,[]);this.listeners.get(k).push(f)}
  click(){if(!this.disabled)for(const f of this.listeners.get('click')||[])f({type:'click'})}
  find(p){if(p(this))return this;for(const x of this.childNodes){const y=x.find(p);if(y)return y}return null}
  get outerHTML(){const a=[...this.attributes].map(([k,v])=>v===''?` ${k}`:` ${k}="${String(v)}"`).join('');return `<${this.tagName}${a}>${this._text}${this.childNodes.map(x=>x.outerHTML).join('')}</${this.tagName}>`}
}
class D { createElement(tag){return new N(tag)} }
const documentRef=new D();
"""

NODE = r"""
import assert from 'node:assert/strict';
import {ATLAS_DURATION_OPTIONS,ATLAS_REASON_CODES,ATLAS_RECOMMENDATION_ACTIONS,getAtlasReasonPresentation,normalizeAtlasSessionPlan,renderAtlasToday} from './atlas_today.mjs';
import {ATLAS_SESSION_PHASES,renderAtlasGuidedSession} from './atlas_session.mjs';
import {ATLAS_OBJECTIVE_STATES,renderAtlasObjectiveMap,renderAtlasSessionSummary} from './atlas_summary.mjs';
import {ATLAS_PEDAGOGICAL_REWARD_KINDS,normalizeAtlasReward,renderAtlasRewards} from './atlas_rewards.mjs';
__DOM__
const labels={'obj-a':'Corriger un calcul','obj-b':'Analyser un signal'};
const activities={'act-a':'Correction ciblée','act-b':'Validation indépendante'};
const recommendation={recommendationVersion:1,objectiveId:'obj-a',action:'correct-practice',priority:100,reasonCodes:['RECENT_ERROR','REVIEW_REQUIRED'],estimatedMinutes:5,eligibleActivityIds:['act-a']};
const plan={planVersion:1,planId:'sha256:plan',generatedAt:'2026-07-29T12:00:00.000Z',durationMinutes:15,items:[
 {position:1,objectiveId:'obj-a',activityLineageId:'act-a',action:'correct-practice',estimatedMinutes:5,reasonCodes:['RECENT_ERROR','REVIEW_REQUIRED']},
 {position:2,objectiveId:'obj-b',activityLineageId:'act-b',action:'attempt-validation',estimatedMinutes:5,reasonCodes:['VALIDATION_AVAILABLE','NO_INDEPENDENT_VALIDATION']}
],unusedMinutes:5};
const evidence=[
 {objectiveId:'obj-a',projectionVersion:1,practiceAttempts:2,latestPracticeCorrect:true,needsReview:false,correctionsCompleted:1,validationAttempts:0,latestValidationCorrect:null,lastEvidenceAt:'2026-07-29T12:05:00.000Z',state:'ready-for-validation',reasons:[]},
 {objectiveId:'obj-b',projectionVersion:1,practiceAttempts:1,latestPracticeCorrect:true,needsReview:false,correctionsCompleted:0,validationAttempts:1,latestValidationCorrect:true,lastEvidenceAt:'2026-07-29T12:10:00.000Z',state:'validated-recently',reasons:[]}
];
const rewards=[
 {rewardId:'r1',rewardVersion:1,kind:'correction-completed',objectiveId:'obj-a',occurredAt:'2026-07-29T12:05:00.000Z',evidenceEventIds:['e1']},
 {rewardId:'r2',rewardVersion:1,kind:'validation-completed',objectiveId:'obj-b',occurredAt:'2026-07-29T12:10:00.000Z',evidenceEventIds:['e2']}
];
const out=[];async function test(name,fn){try{await fn();out.push({name,status:'PASS'})}catch(e){out.push({name,status:'FAIL',error:String(e?.stack||e)})}}
await test('01 frozen contract vocabulary',()=>{
 assert.deepEqual(ATLAS_DURATION_OPTIONS,[5,15,30]);
 assert.deepEqual(ATLAS_REASON_CODES,['NEW_OBJECTIVE','PRACTICE_IN_PROGRESS','RECENT_ERROR','REVIEW_REQUIRED','CORRECTION_COMPLETED','NO_INDEPENDENT_VALIDATION','VALIDATION_AVAILABLE','RECENTLY_VALIDATED','SESSION_TIME_LIMIT']);
 assert.deepEqual(ATLAS_RECOMMENDATION_ACTIONS,['start-practice','continue-practice','correct-practice','attempt-validation','maintain-recent-validation']);
 assert.deepEqual(ATLAS_SESSION_PHASES,['practice','correction','validation','maintenance']);
 assert.deepEqual(ATLAS_OBJECTIVE_STATES,['not-started','training','review-needed','ready-for-validation','validated-recently']);
});
await test('02 reason codes are deterministic and fail closed',()=>{
 assert.equal(getAtlasReasonPresentation('RECENT_ERROR').label,'Erreur récente');
 assert.match(getAtlasReasonPresentation('NO_INDEPENDENT_VALIDATION').explanation,/validation indépendante/);
 assert.throws(()=>getAtlasReasonPresentation('MODEL_GUESS'),RangeError);
});
await test('03 Today consumes recommendation and plan without mutation',()=>{
 let duration=null,started=null,resumed=null;const before=JSON.stringify({recommendation,plan});
 const ui=renderAtlasToday({durationMinutes:15,recommendation,plan,resumableSession:{sessionId:'old',planId:'old-plan',completedItems:1,totalItems:2,objectiveId:'obj-b'}},{documentRef,objectiveLabelsById:labels,activityLabelsById:activities,onDurationChange:x=>duration=x,onStart:x=>started=x,onResume:x=>resumed=x});
 const html=ui.outerHTML;assert.match(html,/Pourquoi cette proposition|Raisons de la recommandation/);assert.match(html,/Correction ciblée/);assert.match(html,/Validation indépendante/);
 ui.find(x=>x.getAttribute('data-duration-minutes')==='30').click();ui.find(x=>x.textContent==='Démarrer la séance de 15 min').click();ui.find(x=>x.textContent==='Reprendre la séance').click();
 assert.equal(duration,30);assert.equal(started.planId,plan.planId);assert.equal(resumed.sessionId,'old');assert.equal(JSON.stringify({recommendation,plan}),before);
});
await test('04 SessionPlan and guided phase separation',()=>{
 assert.deepEqual(normalizeAtlasSessionPlan(plan),plan);
 assert.throws(()=>normalizeAtlasSessionPlan({...plan,durationMinutes:7}),RangeError);
 let next=null,interrupted=null;const ui=renderAtlasGuidedSession({sessionId:'s1',plan,activeIndex:0},{documentRef,objectiveLabelsById:labels,onNext:x=>next=x,onInterrupt:x=>interrupted=x});
 const html=ui.outerHTML;assert.match(html,/data-phase="correction"/);assert.match(html,/distincte d’une validation/);assert.match(html,/aria-current="step"/);
 ui.find(x=>x.textContent==='Étape suivante').click();ui.find(x=>x.textContent==='Interrompre et reprendre plus tard').click();assert.equal(next,1);assert.equal(interrupted.sessionId,'s1');
});
await test('05 summary preserves correction and validation categories',()=>{
 const results=[{position:1,objectiveId:'obj-a',activityLineageId:'act-a',assessmentRole:'practice',outcome:'corrected'},{position:2,objectiveId:'obj-b',activityLineageId:'act-b',assessmentRole:'validation',outcome:'correct'}];
 const ui=renderAtlasSessionSummary({sessionId:'s1',plan,results,objectiveEvidence:evidence,rewards},{documentRef,objectiveLabelsById:labels,activityLabelsById:activities,renderRewards:x=>renderAtlasRewards(x,{documentRef,objectiveLabelsById:labels})});
 const html=ui.outerHTML;assert.match(html,/data-assessment-role="practice" data-outcome="corrected"/);assert.match(html,/data-assessment-role="validation" data-outcome="correct"/);assert.match(html,/preuves observées/);
 assert.throws(()=>renderAtlasSessionSummary({sessionId:'s1',plan,results:[{...results[0],assessmentRole:'validation'}],objectiveEvidence:[]},{documentRef}),RangeError);
});
await test('06 objective map consumes exact evidence states',()=>{
 const html=renderAtlasObjectiveMap(evidence,{documentRef,objectiveLabelsById:labels}).outerHTML;assert.match(html,/data-evidence-state="ready-for-validation"/);assert.match(html,/data-evidence-state="validated-recently"/);assert.throws(()=>renderAtlasObjectiveMap([evidence[0],evidence[0]],{documentRef}),TypeError);
});
await test('07 rewards require explicit pedagogical evidence',()=>{
 assert.deepEqual(ATLAS_PEDAGOGICAL_REWARD_KINDS,['correction-completed','independent-success','validation-completed','resumed-after-interruption','transfer-completed']);
 const html=renderAtlasRewards(rewards,{documentRef,objectiveLabelsById:labels}).outerHTML;assert.match(html,/data-reward-origin="provided-evidence"/);assert.match(html,/ne créent ni score ni compétition/);
 for(const field of ['clickCount','elapsedMinutes','points','rank','streak','randomValue'])assert.throws(()=>normalizeAtlasReward({...rewards[0],[field]:1}),TypeError);
 assert.throws(()=>normalizeAtlasReward({...rewards[0],evidenceEventIds:[]}),TypeError);
});
await test('08 rendering is caller-data immutable',()=>{
 const bundle={recommendation,plan,evidence,rewards};const before=JSON.stringify(bundle);renderAtlasToday({durationMinutes:15,recommendation,plan},{documentRef});renderAtlasGuidedSession({sessionId:'s1',plan,activeIndex:1},{documentRef});renderAtlasObjectiveMap(evidence,{documentRef});renderAtlasRewards(rewards,{documentRef});assert.equal(JSON.stringify(bundle),before);
});
const failed=out.filter(x=>x.status!=='PASS');console.log(JSON.stringify({tests:out.length,passed:out.length-failed.length,failed},null,2));if(failed.length)process.exit(1);
"""


class AtlasM1ExperienceTests(unittest.TestCase):
    maxDiff = None

    def run_node_suite(self) -> dict[str, object]:
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required")
        with tempfile.TemporaryDirectory(prefix="atlas-m1-experience-") as raw:
            work = Path(raw)
            for target, source in MODULES.items():
                self.assertTrue(source.is_file(), source)
                text = source.read_text(encoding="utf-8").replace(
                    "'./atlas_today.js'", "'./atlas_today.mjs'"
                )
                (work / target).write_text(text, encoding="utf-8")
            (work / "experience_test.mjs").write_text(
                NODE.replace("__DOM__", DOM), encoding="utf-8"
            )
            result = subprocess.run(
                [node, "experience_test.mjs"], cwd=work, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=120, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout)
        return json.loads(result.stdout)

    def test_isolated_components(self) -> None:
        report = self.run_node_suite()
        self.assertEqual(report, {"tests": 8, "passed": 8, "failed": []})

    def test_no_network_llm_clock_or_persistence(self) -> None:
        forbidden = (
            "fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon",
            "http://", "https://", "localStorage", "sessionStorage", "indexedDB",
            "Date.now", "new Date", "Math.random", "openai", "chatgpt",
        )
        for path in MODULES.values():
            source = path.read_text(encoding="utf-8")
            for token in forbidden:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, source)

    def test_visible_copy_respects_evidence_boundary(self) -> None:
        source = "\n".join(path.read_text(encoding="utf-8").casefold() for path in MODULES.values())
        for claim in ("ma" + "îtrisé", "certi" + "fié", "rét" + "ention garantie", "niveau officiel"):
            with self.subTest(claim=claim):
                self.assertNotIn(claim, source)

    def test_css_accessibility_mobile_and_no_compulsion_animation(self) -> None:
        css = STYLES.read_text(encoding="utf-8")
        for fragment in (
            ".atlas-today", ".atlas-session--correction", ".atlas-session--validation",
            ".atlas-objective-map__item--review-needed", ".atlas-reward",
            ".atlas-button:focus-visible", "min-height: 44px",
            "@media (max-width: 520px)", "@media (prefers-reduced-motion: reduce)",
            "overflow-wrap: anywhere",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, css)
        self.assertNotIn("outline: none", css)
        self.assertNotIn("outline: 0", css)
        self.assertNotIn("@keyframes", css)

    @unittest.skipUnless(STRICT, "set ATLAS_EXPERIENCE_STRICT=1 for exact branch-delta checks")
    def test_exact_branch_delta(self) -> None:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{BASELINE}...HEAD"], cwd=ROOT,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=120, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual({line for line in result.stdout.splitlines() if line}, EXPECTED_CHANGED_PATHS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
