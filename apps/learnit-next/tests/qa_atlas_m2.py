#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import threading
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
EXPECTED_PRODUCT_HEAD = "104b80f2392c9a7593cf8aad8ed1f154487623f0"
PRODUCT_HEAD = os.environ.get("ATLAS_M2_PRODUCT_HEAD", EXPECTED_PRODUCT_HEAD)
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


def git(*args: str) -> str:
    run = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if run.returncode:
        raise AssertionError(run.stdout)
    return run.stdout.strip()


def node(script: str) -> str:
    run = subprocess.run(["node", "-e", script, str(APP)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if run.returncode:
        raise AssertionError(run.stdout)
    return run.stdout


class AtlasM2IndependentQA(unittest.TestCase):
    def test_exact_binding_and_static_boundary(self):
        self.assertEqual(PRODUCT_HEAD, EXPECTED_PRODUCT_HEAD)
        self.assertTrue(ARTIFACT.is_file())
        data = ARTIFACT.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), EXPECTED_ARTIFACT_SHA256)
        self.assertEqual(
            git("rev-parse", "refs/remotes/origin/agent/ATLAS-WP-003-m2-memory-proof-loop^{commit}"),
            EXPECTED_PRODUCT_HEAD,
        )
        sources = [
            APP / "src/core/atlas_claim_authority.js",
            APP / "src/core/atlas_memory.js",
            APP / "src/core/atlas_projection.js",
            APP / "src/core/atlas_recommendation.js",
            APP / "src/integration/atlas/surface.js",
            APP / "src/adapters/atlas_indexeddb.js",
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in sources)
        for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "http://", "https://"):
            self.assertNotIn(forbidden, text)
        adapter = (APP / "src/adapters/atlas_indexeddb.js").read_text(encoding="utf-8")
        self.assertIn("const DATABASE = 'learnit_atlas_m1_v2'", adapter)
        self.assertIn("const VERSION = 1", adapter)
        self.assertIn("'learningEvents'", adapter)
        self.assertIn("'scoredExecutions'", adapter)
        self.assertIn("'resumeStates'", adapter)
        self.assertIn("'atlasMeta'", adapter)

    def test_claim_memory_and_transfer_adversarial_matrix(self):
        out = node(r'''
          const assert=require('assert');
          const root=process.argv[1];
          const A=require(root+'/src/core/atlas_claim_authority.js');
          const E=require(root+'/src/core/atlas_evidence.js');
          const M=require(root+'/src/core/atlas_memory.js');
          const R=require(root+'/src/core/atlas_recommendation.js');
          const I=require(root+'/src/adapters/atlas_indexeddb.js');
          let n=0; const ok=fn=>{fn();n++};
          ok(()=>assert.equal(A.CLAIMS.length,4));
          ok(()=>assert.equal(new Set(A.ACCEPTED_CLAIM_IDS).size,4));
          ok(()=>assert.equal(A.ORACLE_VERSION,'git:67d70e7307402242dbc1939d6cabfd87af617d74'));
          ok(()=>assert.equal(A.EVIDENCE_ARTIFACT_DIGEST,'sha256:6ca39dd107aea45c14cd7bec7c7ff447c36af1fc12e1c8b3f6c1a0fdc066028f'));
          const c=A.CLAIMS[0];
          const d={objectiveRef:c.objectiveRef,sourceActivityRef:c.sourceActivityRef,targetActivityRef:c.targetActivityRef,contentRevisionRef:A.CONTENT_REVISION_REF,independenceClaimId:c.claimId};
          ok(()=>assert.equal(A.validateRuntimeClaim({independenceClaimId:c.claimId},d),true));
          ok(()=>assert.equal(A.validateRuntimeClaim({independenceClaimId:'atlas-claim-sha256:'+'0'.repeat(64)},d),false));
          ok(()=>assert.equal(A.validateRuntimeClaim({independenceClaimId:c.claimId},{...d,targetActivityRef:c.sourceActivityRef}),false));
          ok(()=>assert.equal(A.validateRuntimeClaim({independenceClaimId:c.claimId},{...d,contentRevisionRef:{...A.CONTENT_REVISION_REF,packageRevisionId:'wrong'}}),false));
          const hostile=I.runtimeRegistry({activity:()=>({}),validateClaim:()=>true});
          ok(()=>assert.equal(hostile.validateClaim({independenceClaimId:c.claimId},d),true));
          ok(()=>assert.equal(hostile.validateClaim({independenceClaimId:c.claimId},{...d,contentRevisionRef:{...A.CONTENT_REVISION_REF,packageDigest:'sha256:'+'0'.repeat(64)}}),false));
          const objective=c.objectiveRef;
          const ex=(id,action,at,extra={})=>({executionId:'atlas-execution-sha256:'+id.repeat(64),objectiveRef:objective,executionClass:'validation',action,outcome:'correct',assistance:'none',scoredAt:at,...extra});
          const v0=ex('1','attempt-validation','2026-08-01T10:00:00.000Z');
          const one=new Set([v0.executionId]);
          ok(()=>assert.equal(M.status({now:'2026-08-02T09:59:59.999Z',executions:[v0],objectiveRef:objective,admissibleExecutionIds:one,evidenceModule:E}).due,false));
          ok(()=>assert.equal(M.status({now:'2026-08-02T10:00:00.000Z',executions:[v0],objectiveRef:objective,admissibleExecutionIds:one,evidenceModule:E}).due,true));
          const v1=ex('2','maintain-recent-validation','2026-08-02T10:00:00.000Z');
          const v2=ex('3','maintain-recent-validation','2026-08-05T10:00:00.000Z');
          const v3=ex('4','maintain-recent-validation','2026-08-12T10:00:00.000Z');
          const v4=ex('5','maintain-recent-validation','2026-09-02T10:00:00.000Z');
          const all=new Set([v0,v1,v2,v3,v4].map(x=>x.executionId));
          ok(()=>assert.equal(M.status({now:v1.scoredAt,executions:[v0,v1],objectiveRef:objective,admissibleExecutionIds:all,evidenceModule:E}).intervalDays,3));
          ok(()=>assert.equal(M.status({now:v2.scoredAt,executions:[v0,v1,v2],objectiveRef:objective,admissibleExecutionIds:all,evidenceModule:E}).intervalDays,7));
          ok(()=>assert.equal(M.status({now:v3.scoredAt,executions:[v0,v1,v2,v3],objectiveRef:objective,admissibleExecutionIds:all,evidenceModule:E}).intervalDays,21));
          ok(()=>assert.equal(M.status({now:v4.scoredAt,executions:[v0,v1,v2,v3,v4],objectiveRef:objective,admissibleExecutionIds:all,evidenceModule:E}).intervalDays,21));
          const assisted=ex('6','attempt-validation','2026-08-01T10:00:00.000Z',{assistance:'used'});
          ok(()=>assert.equal(M.status({now:'2026-08-10T10:00:00.000Z',executions:[assisted],objectiveRef:objective,admissibleExecutionIds:new Set([assisted.executionId]),evidenceModule:E}).hasIndependentValidation,false));
          const unknown=ex('7','attempt-validation','2026-08-01T10:00:00.000Z',{assistance:'unknown'});
          ok(()=>assert.equal(M.status({now:'2026-08-10T10:00:00.000Z',executions:[unknown],objectiveRef:objective,admissibleExecutionIds:new Set([unknown.executionId]),evidenceModule:E}).hasIndependentValidation,false));
          const rows=[{objectiveRef:objective,evidence:{objectiveRef:objective,state:'validated-recently'}},{objectiveRef:A.CLAIMS[2].objectiveRef,evidence:{objectiveRef:A.CLAIMS[2].objectiveRef,state:'review-needed'}}];
          ok(()=>assert.equal(R.rankRecommendations(rows,[])[0].evidence.state,'review-needed'));
          const cr={packageLineageId:'pkg',courseLineageId:'course'}, obj={courseRef:cr,objectiveId:'obj'}, ar=id=>({courseRef:cr,activityLineageId:id});
          const acts=[{activityRef:ar('practice'),objectiveRef:obj,learningPhase:'application',assessmentRole:'practice',estimatedMinutes:4},{activityRef:ar('transfer'),objectiveRef:obj,learningPhase:'transfer',assessmentRole:'practice',estimatedMinutes:4}];
          const idx=E.indexActivities(acts,acts.map((x,i)=>({objectiveRef:obj,activityRef:x.activityRef,authorIndex:i})));
          ok(()=>assert.deepStrictEqual(E.eligibleActivities(idx,obj,'start-practice').map(x=>x.activityRef.activityLineageId),['practice']));
          console.log('ATLAS_M2_QA_NODE_PASS '+n+'/'+n);
        ''')
        self.assertIn("ATLAS_M2_QA_NODE_PASS", out)

    @unittest.skipIf(sync_playwright is None, "Playwright required")
    def test_visible_validation_and_due_reconfirmation(self):
        kit = json.loads(KIT_PATH.read_text(encoding="utf-8"))
        activities = {a["activityLineageId"]: a for course in kit["courses"] for a in course["activities"]}
        unexpected: list[str] = []
        with server_for(ARTIFACT) as url, sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            def route(r):
                if r.request.url.startswith("http://127.0.0.1:"):
                    r.continue_()
                else:
                    unexpected.append(r.request.url)
                    r.abort()

            page.route("**/*", route)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__ && window.__LEARNIT_ATLAS_M1__)")
            page.evaluate("async () => window.__LEARNIT_NEXT_TEST__.resetNextData()")
            page.evaluate("async payload => window.__LEARNIT_NEXT_TEST__.importPackage(payload)", kit)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_selector('[data-atlas-int-surface="ready"] .atlas-course-card')

            def snapshot() -> dict[str, Any]:
                return page.evaluate("""async () => {const M=window.__LEARNIT_ATLAS_M1__.modules,s=await M.indexedDb.IndexedDbAtlasStorage.open();try{return s.snapshot();}finally{s.close();}}""")

            def active(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
                started=[e for e in state["learningEvents"] if e["kind"]=="session-started"]
                self.assertTrue(started)
                latest=max(started,key=lambda e:(e["occurredAt"],e["eventId"]))
                sid=latest["sessionRef"]["sessionId"]
                checkpoint=next(r for r in state["resumeStates"] if r["sessionRef"]["sessionId"]==sid)
                return state["atlasMeta"]["sessions"][sid]["plan"],checkpoint

            def current_activity() -> dict[str, Any]:
                plan,checkpoint=active(snapshot())
                item=plan["payload"]["items"][checkpoint["nextItemPosition"]]
                return activities[item["activityRef"]["activityLineageId"]]

            def answer_current() -> None:
                activity=current_activity()
                if activity["type"]=="qcm":
                    page.locator(f'input[data-atlas-choice="true"][value="{activity["correctChoiceId"]}"]').check()
                else:
                    for answer in activity["answers"]:
                        page.locator(f'[data-atlas-slot="{answer["slotId"]}"]').select_option(answer["tokenId"])
                page.locator('[data-atlas-submit]').click()
                page.wait_for_timeout(100)

            def start(minutes: int) -> dict[str, Any]:
                page.locator(f'[data-atlas-duration="{minutes}"]').first.click()
                page.wait_for_selector('[data-atlas-action="start"]')
                page.locator('[data-atlas-action="start"]').click()
                page.wait_for_selector('[data-atlas-submit]')
                return active(snapshot())[0]

            def complete() -> None:
                plan,_=active(snapshot())
                for _ in range(len(plan["payload"]["items"])+2):
                    if page.get_by_role("button",name="Retour à Aujourd’hui").count():
                        return
                    page.wait_for_selector('[data-atlas-submit]')
                    answer_current()
                self.fail("session did not reach summary")

            practice=start(15)
            self.assertTrue(practice["payload"]["items"])
            self.assertTrue(all(i["executionClass"]=="practice" for i in practice["payload"]["items"]))
            complete()
            page.get_by_role("button",name="Retour à Aujourd’hui").click()
            page.wait_for_selector('[data-atlas-duration="15"]')

            validation=start(15)
            validation_items=[i for i in validation["payload"]["items"] if i["action"]=="attempt-validation"]
            self.assertTrue(validation_items,validation)
            for item in validation_items:
                self.assertIn(item["independenceClaimId"],ACCEPTED_IDS)
                self.assertRegex(item["validationBasisEventId"],r"^atlas-event-sha256:[0-9a-f]{64}$")
            complete()
            state=snapshot()
            validations=[x for x in state["scoredExecutions"] if x["action"]=="attempt-validation" and x["outcome"]=="correct" and x["assistance"]=="none"]
            self.assertTrue(validations)
            latest=max(x["scoredAt"] for x in validations)
            due=dt.datetime.fromisoformat(latest.replace("Z","+00:00"))+dt.timedelta(days=1)
            due_ms=int(due.timestamp()*1000)

            page.get_by_role("button",name="Retour à Aujourd’hui").click()
            context.add_init_script(script=f"""(() => {{const ms={due_ms};const NativeDate=Date;globalThis.Date=class extends NativeDate{{constructor(...a){{super(...(a.length?a:[ms]));}}static now(){{return ms;}}}};}})();""")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_selector('[data-atlas-duration="15"]')
            maintenance=start(15)
            maintenance_items=[i for i in maintenance["payload"]["items"] if i["action"]=="maintain-recent-validation"]
            self.assertTrue(maintenance_items,maintenance)
            for item in maintenance_items:
                self.assertIn(item["independenceClaimId"],ACCEPTED_IDS)

            page.set_viewport_size({"width":390,"height":844})
            self.assertLessEqual(page.evaluate("() => document.documentElement.scrollWidth"),390)
            hint=page.locator('[data-atlas-control="hint"]')
            submit=page.locator('[data-atlas-control="submit"]')
            pause=page.locator('[data-atlas-control="pause"]')
            self.assertTrue(hint.is_visible() and submit.is_visible() and pause.is_visible())
            hint.focus(); self.assertTrue(hint.evaluate("e=>e===document.activeElement"))
            page.keyboard.press("Tab"); self.assertTrue(submit.evaluate("e=>e===document.activeElement"))
            page.keyboard.press("Tab"); self.assertTrue(pause.evaluate("e=>e===document.activeElement"))
            self.assertEqual(unexpected,[])
            context.close(); browser.close()


if __name__ == "__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(AtlasM2IndependentQA)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("PASS_ATLAS_M2_INDEPENDENT_QA")
    raise SystemExit(0 if result.wasSuccessful() else 1)
