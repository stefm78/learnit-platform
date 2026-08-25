#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import threading
import time
import unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = pathlib.Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
ARTIFACT = pathlib.Path(os.environ.get("ATLAS_M2_ARTIFACT", APP / "dist/learnit-next.html"))
PRODUCT_HEAD = os.environ.get("ATLAS_M2_PRODUCT_HEAD", "104b80f2392c9a7593cf8aad8ed1f154487623f0")
EXPECTED_PRODUCT_HEAD = "104b80f2392c9a7593cf8aad8ed1f154487623f0"
EXPECTED_ARTIFACT_SHA256 = "7c242614c394ca1a0eb739c0f02c672c6afe280a128056a8f75b96266727a091"
KIT_PATH = ROOT / "authoring/v2/atlas/nombres_complexes_atlas.json"
ACCEPTED_IDS = {
    "atlas-claim-sha256:e9e466b7b14953df7f85257c03dbb9e13918cc7b649626330a838c7dda564d2f",
    "atlas-claim-sha256:98de40e0629626f274617e4505c64e1b9737bd760a69e5c350fe78045d2b35ac",
    "atlas-claim-sha256:27a295974474567c290f5c2720c675f3af47565eeb30463bf462ad67b043af1e",
    "atlas-claim-sha256:9c3fe05a3570f844cb5bf92ca38f087b981db7262acd3d7bd27494a15df2ddb4",
}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return


@contextmanager
def server_for(path: pathlib.Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(path.parent)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/{path.name}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_node(script: str) -> str:
    completed = subprocess.run(
        ["node", "-e", script, str(APP)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        raise AssertionError(completed.stdout)
    return completed.stdout


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        raise AssertionError(completed.stdout)
    return completed.stdout.strip()


class AtlasM2IndependentQA(unittest.TestCase):
    def test_exact_product_and_artifact_binding(self):
        self.assertEqual(PRODUCT_HEAD, EXPECTED_PRODUCT_HEAD)
        self.assertTrue(ARTIFACT.is_file(), ARTIFACT)
        data = ARTIFACT.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), EXPECTED_ARTIFACT_SHA256)
        self.assertEqual(
            git("rev-parse", "refs/remotes/origin/agent/ATLAS-WP-003-m2-memory-proof-loop^{commit}"),
            EXPECTED_PRODUCT_HEAD,
        )

    def test_independent_claim_and_memory_adversarial_matrix(self):
        out = run_node(r'''
          const assert=require('assert');
          const root=process.argv[1];
          const A=require(root+'/src/core/atlas_claim_authority.js');
          const E=require(root+'/src/core/atlas_evidence.js');
          const M=require(root+'/src/core/atlas_memory.js');
          const R=require(root+'/src/core/atlas_recommendation.js');
          const P=require(root+'/src/core/atlas_projection.js');
          const I=require(root+'/src/adapters/atlas_indexeddb.js');
          let n=0; const ok=fn=>{fn();n+=1};

          ok(()=>assert.equal(A.CLAIMS.length,4));
          ok(()=>assert.deepStrictEqual(new Set(A.ACCEPTED_CLAIM_IDS).size,4));
          ok(()=>assert.equal(A.ORACLE_VERSION,'git:67d70e7307402242dbc1939d6cabfd87af617d74'));
          ok(()=>assert.equal(A.EVIDENCE_ARTIFACT_DIGEST,'sha256:6ca39dd107aea45c14cd7bec7c7ff447c36af1fc12e1c8b3f6c1a0fdc066028f'));

          const claim=A.CLAIMS[0];
          const details={
            objectiveRef:claim.objectiveRef,
            sourceActivityRef:claim.sourceActivityRef,
            targetActivityRef:claim.targetActivityRef,
            contentRevisionRef:A.CONTENT_REVISION_REF,
            independenceClaimId:claim.claimId,
          };
          ok(()=>assert.equal(A.validateRuntimeClaim({independenceClaimId:claim.claimId},details),true));
          ok(()=>assert.equal(A.validateRuntimeClaim({independenceClaimId:'atlas-claim-sha256:'+'0'.repeat(64)},details),false));
          ok(()=>assert.equal(A.validateRuntimeClaim({independenceClaimId:claim.claimId},{...details,targetActivityRef:claim.sourceActivityRef}),false));
          ok(()=>assert.equal(A.validateRuntimeClaim({independenceClaimId:claim.claimId},{...details,contentRevisionRef:{...A.CONTENT_REVISION_REF,packageRevisionId:'wrong'}}),false));

          const hostile=I.runtimeRegistry({activity:()=>({}),validateClaim:()=>true});
          ok(()=>assert.equal(hostile.validateClaim({independenceClaimId:claim.claimId},details),true));
          ok(()=>assert.equal(hostile.validateClaim({independenceClaimId:claim.claimId},{...details,contentRevisionRef:{...A.CONTENT_REVISION_REF,packageDigest:'sha256:'+'0'.repeat(64)}}),false));

          const objective=claim.objectiveRef;
          const exec=(id,action,at,extra={})=>({
            executionId:'atlas-execution-sha256:'+id.repeat(64),
            objectiveRef:objective,
            executionClass:'validation',
            action,
            outcome:'correct',
            assistance:'none',
            scoredAt:at,
            ...extra,
          });
          const v0=exec('1','attempt-validation','2026-08-01T10:00:00.000Z');
          const admissible=new Set([v0.executionId]);
          ok(()=>assert.equal(M.status({now:'2026-08-02T09:59:59.999Z',executions:[v0],objectiveRef:objective,admissibleExecutionIds:admissible,evidenceModule:E}).due,false));
          ok(()=>assert.equal(M.status({now:'2026-08-02T10:00:00.000Z',executions:[v0],objectiveRef:objective,admissibleExecutionIds:admissible,evidenceModule:E}).due,true));

          const v1=exec('2','maintain-recent-validation','2026-08-02T10:00:00.000Z');
          const v2=exec('3','maintain-recent-validation','2026-08-05T10:00:00.000Z');
          const v3=exec('4','maintain-recent-validation','2026-08-12T10:00:00.000Z');
          const v4=exec('5','maintain-recent-validation','2026-09-02T10:00:00.000Z');
          const chain=[v0,v1,v2,v3,v4]; const ids=new Set(chain.map(x=>x.executionId));
          ok(()=>assert.equal(M.status({now:v1.scoredAt,executions:[v0,v1],objectiveRef:objective,admissibleExecutionIds:ids,evidenceModule:E}).intervalDays,3));
          ok(()=>assert.equal(M.status({now:v2.scoredAt,executions:[v0,v1,v2],objectiveRef:objective,admissibleExecutionIds:ids,evidenceModule:E}).intervalDays,7));
          ok(()=>assert.equal(M.status({now:v3.scoredAt,executions:[v0,v1,v2,v3],objectiveRef:objective,admissibleExecutionIds:ids,evidenceModule:E}).intervalDays,21));
          ok(()=>assert.equal(M.status({now:v4.scoredAt,executions:chain,objectiveRef:objective,admissibleExecutionIds:ids,evidenceModule:E}).intervalDays,21));
          const assisted=exec('6','attempt-validation','2026-08-01T10:00:00.000Z',{assistance:'used'});
          ok(()=>assert.equal(M.status({now:'2026-08-10T10:00:00.000Z',executions:[assisted],objectiveRef:objective,admissibleExecutionIds:new Set([assisted.executionId]),evidenceModule:E}).hasIndependentValidation,false));
          const unknown=exec('7','attempt-validation','2026-08-01T10:00:00.000Z',{assistance:'unknown'});
          ok(()=>assert.equal(M.status({now:'2026-08-10T10:00:00.000Z',executions:[unknown],objectiveRef:objective,admissibleExecutionIds:new Set([unknown.executionId]),evidenceModule:E}).hasIndependentValidation,false));

          const rows=[
            {objectiveRef:objective,evidence:{objectiveRef:objective,state:'validated-recently'}},
            {objectiveRef:A.CLAIMS[2].objectiveRef,evidence:{objectiveRef:A.CLAIMS[2].objectiveRef,state:'review-needed'}},
          ];
          ok(()=>assert.equal(R.rankRecommendations(rows,[])[0].evidence.state,'review-needed'));

          const fakeCourse={packageLineageId:'pkg',courseLineageId:'course'};
          const obj={courseRef:fakeCourse,objectiveId:'obj'};
          const ref=id=>({courseRef:fakeCourse,activityLineageId:id});
          const activities=[
            {activityRef:ref('practice'),objectiveRef:obj,learningPhase:'application',assessmentRole:'practice',estimatedMinutes:4},
            {activityRef:ref('transfer'),objectiveRef:obj,learningPhase:'transfer',assessmentRole:'practice',estimatedMinutes:4},
          ];
          const index=E.indexActivities(activities,activities.map((x,i)=>({objectiveRef:obj,activityRef:x.activityRef,authorIndex:i})));
          ok(()=>assert.deepStrictEqual(E.eligibleActivities(index,obj,'start-practice').map(x=>x.activityRef.activityLineageId),['practice']));
          console.log('ATLAS_M2_QA_NODE_PASS '+n+'/'+n);
        ''')
        self.assertIn("ATLAS_M2_QA_NODE_PASS", out)

    def test_static_local_only_and_storage_boundary(self):
        paths = [
            APP / "src/core/atlas_claim_authority.js",
            APP / "src/core/atlas_memory.js",
            APP / "src/core/atlas_projection.js",
            APP / "src/core/atlas_recommendation.js",
            APP / "src/integration/atlas/surface.js",
            APP / "src/adapters/atlas_indexeddb.js",
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "http://", "https://"):
            self.assertNotIn(forbidden, text)
        adapter = (APP / "src/adapters/atlas_indexeddb.js").read_text(encoding="utf-8")
        self.assertIn("const DATABASE = 'learnit_atlas_m1_v2'", adapter)
        self.assertIn("const VERSION = 1", adapter)
        self.assertIn("'learningEvents'", adapter)
        self.assertIn("'scoredExecutions'", adapter)
        self.assertIn("'resumeStates'", adapter)
        self.assertIn("'atlasMeta'", adapter)

    @unittest.skipIf(sync_playwright is None, "Playwright is required")
    def test_real_browser_validation_then_due_reconfirmation_desktop_mobile_keyboard(self):
        kit = json.loads(KIT_PATH.read_text(encoding="utf-8"))
        activities = {
            item["activityLineageId"]: item
            for course in kit["courses"]
            for item in course["activities"]
        }
        unexpected: list[str] = []

        with server_for(ARTIFACT) as url, sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            def route(route):
                request_url = route.request.url
                if request_url.startswith("http://127.0.0.1:"):
                    route.continue_()
                else:
                    unexpected.append(request_url)
                    route.abort()

            page.route("**/*", route)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__ && window.__LEARNIT_ATLAS_M1__)")
            page.evaluate("async () => window.__LEARNIT_NEXT_TEST__.resetNextData()")
            page.evaluate("async payload => window.__LEARNIT_NEXT_TEST__.importPackage(payload)", kit)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_selector('[data-atlas-int-surface="ready"] .atlas-course-card')

            def snapshot() -> dict[str, Any]:
                return page.evaluate("""async () => {
                  const M=window.__LEARNIT_ATLAS_M1__.modules;
                  const s=await M.indexedDb.IndexedDbAtlasStorage.open();
                  try{return s.snapshot();}finally{s.close();}
                }""")

            def active_plan() -> dict[str, Any]:
                state = snapshot()
                self.assertTrue(state["resumeStates"])
                checkpoint = state["resumeStates"][-1]
                sid = checkpoint["sessionRef"]["sessionId"]
                return state["atlasMeta"]["sessions"][sid]["plan"]

            def current_activity() -> dict[str, Any]:
                state = snapshot()
                checkpoint = state["resumeStates"][-1]
                sid = checkpoint["sessionRef"]["sessionId"]
                plan = state["atlasMeta"]["sessions"][sid]["plan"]
                pos = checkpoint["nextItemPosition"]
                return activities[plan["payload"]["items"][pos]["activityRef"]["activityLineageId"]]

            def answer_current() -> None:
                activity = current_activity()
                if activity["type"] == "qcm":
                    page.locator(
                        f'input[data-atlas-choice="true"][value="{activity["correctChoiceId"]}"]'
                    ).check()
                elif activity["type"] == "fill":
                    for answer in activity["answers"]:
                        page.locator(f'[data-atlas-slot="{answer["slotId"]}"]').select_option(answer["tokenId"])
                else:
                    self.fail(f"unsupported activity {activity['type']}")
                page.locator('[data-atlas-submit]').click()
                page.wait_for_timeout(80)

            def complete_session() -> dict[str, Any]:
                plan = active_plan()
                limit = len(plan["payload"]["items"]) + 2
                for _ in range(limit):
                    if page.get_by_role("button", name="Retour à Aujourd’hui").count():
                        break
                    page.wait_for_selector('[data-atlas-submit]')
                    answer_current()
                self.assertTrue(page.get_by_role("button", name="Retour à Aujourd’hui").count())
                return plan

            def start(minutes: int) -> dict[str, Any]:
                page.locator(f'[data-atlas-duration="{minutes}"]').first.click()
                page.wait_for_selector('[data-atlas-action="start"]')
                page.locator('[data-atlas-action="start"]').click()
                page.wait_for_selector('[data-atlas-submit]')
                return active_plan()

            practice_plan = start(15)
            self.assertTrue(practice_plan["payload"]["items"])
            self.assertTrue(all(item["executionClass"] == "practice" for item in practice_plan["payload"]["items"]))
            complete_session()
            page.get_by_role("button", name="Retour à Aujourd’hui").click()
            page.wait_for_selector('[data-atlas-duration="15"]')

            validation_plan = start(15)
            validation_items = [item for item in validation_plan["payload"]["items"] if item["action"] == "attempt-validation"]
            self.assertTrue(validation_items, validation_plan)
            for item in validation_items:
                self.assertIn(item["independenceClaimId"], ACCEPTED_IDS)
                self.assertRegex(item["validationBasisEventId"], r"^atlas-event-sha256:[0-9a-f]{64}$")
            complete_session()

            state = snapshot()
            validations = [
                execution for execution in state["scoredExecutions"]
                if execution["action"] == "attempt-validation"
                and execution["outcome"] == "correct"
                and execution["assistance"] == "none"
            ]
            self.assertTrue(validations)
            latest = max(item["scoredAt"] for item in validations)
            due_ms = int(time.mktime(time.strptime(latest[:19], "%Y-%m-%dT%H:%M:%S")) * 1000) + 24 * 60 * 60 * 1000

            page.get_by_role("button", name="Retour à Aujourd’hui").click()
            context.add_init_script(
                """ms => {
                  const NativeDate=Date;
                  globalThis.Date=class extends NativeDate {
                    constructor(...args){super(...(args.length?args:[ms]));}
                    static now(){return ms;}
                  };
                }""",
                due_ms,
            )
            page.reload(wait_until="domcontentloaded")
            page.wait_for_selector('[data-atlas-duration="15"]')
            maintenance_plan = start(15)
            maintenance_items = [
                item for item in maintenance_plan["payload"]["items"]
                if item["action"] == "maintain-recent-validation"
            ]
            self.assertTrue(maintenance_items, maintenance_plan)
            for item in maintenance_items:
                self.assertIn(item["independenceClaimId"], ACCEPTED_IDS)

            page.set_viewport_size({"width": 390, "height": 844})
            self.assertLessEqual(
                page.evaluate("() => document.documentElement.scrollWidth"),
                390,
            )
            hint = page.locator('[data-atlas-control="hint"]')
            submit = page.locator('[data-atlas-control="submit"]')
            pause = page.locator('[data-atlas-control="pause"]')
            for control in (hint, submit, pause):
                self.assertTrue(control.is_visible())
            hint.focus()
            self.assertTrue(hint.evaluate("e => e === document.activeElement"))
            page.keyboard.press("Tab")
            self.assertTrue(submit.evaluate("e => e === document.activeElement"))
            page.keyboard.press("Tab")
            self.assertTrue(pause.evaluate("e => e === document.activeElement"))

            self.assertEqual(unexpected, [])
            context.close()
            browser.close()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AtlasM2IndependentQA)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("PASS_ATLAS_M2_INDEPENDENT_QA")
    raise SystemExit(0 if result.wasSuccessful() else 1)
