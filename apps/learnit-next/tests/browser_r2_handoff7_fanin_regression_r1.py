#!/usr/bin/env python3
from __future__ import annotations
import json,threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from typing import Any
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3];APP=ROOT/"apps"/"learnit-next";ARTIFACT=APP/"dist"/"learnit-next.html";KIT=ROOT/"showcase"/"student-v0.1"/"nombres-complexes"/"nombres_complexes_student_v01_v5.json"
STATES={"À découvrir","En apprentissage","À renforcer","À confirmer","Acquis récemment"}
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_:Any)->None:return
@contextmanager
def serve():
    s=ThreadingHTTPServer(("127.0.0.1",0),partial(Quiet,directory=str(ARTIFACT.parent)));t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
    try:yield f"http://127.0.0.1:{s.server_port}/{ARTIFACT.name}"
    finally:s.shutdown();s.server_close();t.join(timeout=5)
def main():
    assert ARTIFACT.is_file();kit=json.loads(KIT.read_text(encoding="utf-8"));first,second=kit["courses"][0]["activities"][:2]
    with serve() as url,sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path="/usr/bin/chromium")
        for viewport,touch in [({"width":1365,"height":768},False),({"width":390,"height":844},True)]:
            c=browser.new_context(viewport=viewport,has_touch=touch);page=c.new_page();errors=[];external=[]
            page.on("pageerror",lambda e:errors.append(str(e)));page.on("request",lambda r:external.append(r.url) if r.url.startswith(("http://","https://")) and "127.0.0.1" not in r.url else None)
            page.goto(url);page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
            page.locator("#kit-file").set_input_files({"name":KIT.name,"mimeType":"application/json","buffer":KIT.read_bytes()});page.locator("form.import-panel button[type='submit']").click();page.get_by_text(kit["courses"][0]["title"],exact=True).wait_for()
            assert page.get_by_text("Aucun parcours Atlas installé",exact=True).count()==0
            page.get_by_role("button",name="Commencer").click();page.locator('[data-activity-presentation="lesson"]').wait_for()
            assert page.locator('[data-session-objective-buckets="true"]').count()==1
            states=page.locator('[data-session-objective-buckets="true"] .objective-bucket__state').all_inner_texts();assert states and set(states)<=STATES
            details=page.locator('[data-session-progress-details="true"]');assert details.count()==1 and details.get_attribute("open") is None
            assert page.evaluate("""() => {const a=document.querySelector('.served-activity-form'),b=document.querySelector('[data-session-objective-buckets="true"]'),d=document.querySelector('[data-session-progress-details="true"]');return Boolean(a&&b&&d&&(a.compareDocumentPosition(b)&Node.DOCUMENT_POSITION_FOLLOWING)&&(b.compareDocumentPosition(d)&Node.DOCUMENT_POSITION_FOLLOWING));}""")
            s=page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession()");assert s["currentActivity"]["activityLineageId"]==first["activityLineageId"]
            out=page.evaluate("""async (id) => window.__LEARNIT_NEXT_TEST__.answer(id,{acknowledged:true})""",first["activityRevisionId"]);assert out["progress"]["completed"]==1 and out["progress"]["total"]==10
            page.reload();page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)");page.locator('[data-activity-presentation="flashcard"]').wait_for()
            s=page.evaluate("() => window.__LEARNIT_NEXT_TEST__.getSession()");assert s["currentActivity"]["activityLineageId"]==second["activityLineageId"]
            assert page.get_by_text("1/10 activités",exact=True).count()==1
            assert page.locator('[data-session-objective-buckets="true"]').count()==1 and page.locator('[data-session-progress-details="true"]').get_attribute("open") is None
            assert page.evaluate("() => document.documentElement.scrollWidth<=window.innerWidth+1");assert errors==[],errors;assert external==[],external;c.close()
        browser.close()
    for m in ("STREAM_A_SHELL_AROUND_EXACT_V5_V8: PASS","NO_FALSE_ATLAS_EMPTY_STATE_V5: PASS","ACTIVE_ACTIVITY_PRIMARY_V5: PASS","COMPACT_OBJECTIVE_BUCKETS_V5: PASS","PROGRESSIVE_DISCLOSURE_V5: PASS","RELOAD_RESUME_EXACT_V5_ACTIVITY: PASS","TRUTHFUL_PROGRESS_RENDERING: PASS","NO_UNEXPECTED_NETWORK_FETCH: PASS","DESKTOP_MOBILE_V5: PASS"):print(m)
    return 0
if __name__=="__main__":raise SystemExit(main())
