#!/usr/bin/env python3
"""Accessible black-box browser tests for the Learn-it successor vertical slice."""
from __future__ import annotations
import copy, hashlib, json, os, re, tempfile, threading, unicodedata, unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
try:
    from playwright.sync_api import Locator, sync_playwright
except ImportError:
    Locator, sync_playwright = Any, None

ROOT=Path(__file__).resolve().parents[3]
FIXTURE_DIR=ROOT/"contracts/fixtures"
VALID_PATH=FIXTURE_DIR/"v2-valid-minimal.json";LEGACY_PATH=FIXTURE_DIR/"v2-invalid-legacy.json"
DEFAULT_ARTIFACT=ROOT/"apps/learnit-next/dist/learnit-next.html"
STRICT=os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION")=="1"
IMPORT_NAMES=re.compile(r"import|installer|ajouter|charger|load",re.I)
START_NAMES=re.compile(r"commencer|démarrer|ouvrir|start|begin|apprendre|continuer|continue",re.I)
VALIDATE_NAMES=re.compile(r"valider|vérifier|soumettre|check|submit|confirm",re.I)
NEXT_NAMES=re.compile(r"suivant|continuer|next|continue",re.I)
RESET_NAMES=re.compile(r"réinitialiser|effacer|reset|clear",re.I)
EMPTY_NAMES=re.compile(r"bibliothèque.*vide|aucun.*cours|no courses|empty library",re.I)

def require_or_skip(condition,message):
    if condition:return
    if STRICT:raise RuntimeError(message)
    raise unittest.SkipTest(message)
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*_):return
@contextmanager
def artifact_server(artifact):
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(QuietHandler,directory=str(artifact.parent)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{server.server_port}/{artifact.name}"
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
def load_json(path):return json.loads(path.read_text(encoding="utf-8"))
def normalise(v):
    if v is None or isinstance(v,(bool,int)):return v
    if isinstance(v,float):raise TypeError
    if isinstance(v,str):return unicodedata.normalize("NFC",v)
    if isinstance(v,list):return [normalise(x) for x in v]
    if isinstance(v,dict):return {unicodedata.normalize("NFC",k):normalise(x) for k,x in v.items()}
    raise TypeError
def canonical(v):return json.dumps(normalise(v),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(v,field):return "sha256:"+hashlib.sha256(canonical({k:x for k,x in v.items() if k!=field})).hexdigest()
def recompute(p):
    p=copy.deepcopy(p)
    for c in p["courses"]:
        for a in c["activities"]:a["activityRevisionDigest"]=digest(a,"activityRevisionDigest")
        c["courseRevisionDigest"]=digest(c,"courseRevisionDigest")
    p["packageRevisionDigest"]=digest(p,"packageRevisionDigest");return p
def reordered_qcm_fixture(valid):
    p=copy.deepcopy(valid);q=p["courses"][0]["activities"][0];q["choices"].reverse()
    q["activityRevisionId"]="44444444-4444-4444-8444-444444444449"
    p["courses"][0]["courseRevisionId"]="22222222-2222-4222-8222-222222222229"
    p["packageRevisionId"]="11111111-1111-4111-8111-111111111119";p["title"]="Fixture QCM réordonné";return recompute(p)
def find_activity_record(value,activity_id):
    if isinstance(value,dict):
        if value.get("activityRevisionId")==activity_id:return value
        for x in value.values():
            found=find_activity_record(x,activity_id)
            if found is not None:return found
    if isinstance(value,list):
        for x in value:
            found=find_activity_record(x,activity_id)
            if found is not None:return found
    return None

class BrowserVerticalSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact=Path(os.environ.get("LEARNIT_NEXT_ARTIFACT",DEFAULT_ARTIFACT))
        require_or_skip(artifact.exists(),f"WAITING_FOR_INTEGRATION: built artifact absent at {artifact}")
        require_or_skip(sync_playwright is not None,"DEPENDENCY: install Playwright")
        cls.valid=load_json(VALID_PATH);cls.legacy=load_json(LEGACY_PATH);cls.reordered=reordered_qcm_fixture(cls.valid)
        cls._server=artifact_server(artifact);cls.url=cls._server.__enter__();cls._playwright=sync_playwright().start()
        try:cls.browser=cls._playwright.chromium.launch(headless=True)
        except Exception as e:
            cls._playwright.stop();cls._server.__exit__(None,None,None);require_or_skip(False,f"DEPENDENCY: Chromium unavailable: {e}")
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,"browser"):cls.browser.close()
        if hasattr(cls,"_playwright"):cls._playwright.stop()
        if hasattr(cls,"_server"):cls._server.__exit__(None,None,None)
    def setUp(self):
        self.context=self.browser.new_context();self.page=self.context.new_page();self.page.goto(self.url,wait_until="domcontentloaded")
        self.page.wait_for_function("()=>Boolean(window.__LEARNIT_NEXT_TEST__)");self.api("resetNextData");self.page.reload(wait_until="domcontentloaded")
        self.page.wait_for_function("()=>Boolean(window.__LEARNIT_NEXT_TEST__)")
    def tearDown(self):self.context.close()
    def api(self,op,*args):
        return self.page.evaluate("async x=>{const a=window.__LEARNIT_NEXT_TEST__;if(typeof a[x.op]!=='function')throw Error('missing '+x.op);return await a[x.op](...x.args)}",{"op":op,"args":list(args)})
    def first_visible(self,locator):
        for i in range(locator.count()):
            c=locator.nth(i)
            if c.is_visible():return c
        return None
    def click_named(self,pattern):
        for role in ("button","link"):
            c=self.first_visible(self.page.get_by_role(role,name=pattern))
            if c is not None:
                c.focus();self.page.keyboard.press("Enter");return
        self.fail(f"no accessible visible control named /{pattern.pattern}/")
    def import_ui(self,payload):
        text=payload if isinstance(payload,str) else json.dumps(payload,ensure_ascii=False)
        chooser=self.first_visible(self.page.get_by_role("button",name=IMPORT_NAMES))
        if chooser is None:self.fail("import trigger lacks accessible button")
        with tempfile.NamedTemporaryFile("w",suffix=".json",encoding="utf-8",delete=False) as h:
            h.write(text);path=Path(h.name)
        try:
            with self.page.expect_file_chooser() as event:chooser.click()
            event.value.set_files(str(path))
        finally:path.unlink(missing_ok=True)
    def wait_courses(self,n):
        self.page.wait_for_function("async n=>(await window.__LEARNIT_NEXT_TEST__.listCourses()).length===n",n)
        courses=self.api("listCourses");self.assertEqual(n,len(courses));return courses
    def start_course(self,title,prompt):
        control=None
        for role in ("button","link"):
            control=self.first_visible(self.page.get_by_role(role,name=re.compile(re.escape(title),re.I)))
            if control is not None:break
        if control is not None:control.click()
        else:self.click_named(START_NAMES)
        self.page.get_by_text(prompt,exact=False).first.wait_for(state="visible")
    def assert_no_qcm_preselection(self,activity_id):
        self.assertEqual(0,self.page.locator('input[type="radio"]:checked,[role="radio"][aria-checked="true"],[aria-pressed="true"]').count())
        if self.page.evaluate("()=>typeof window.__LEARNIT_NEXT_TEST__.getCurrentProgress==='function'"):
            self.assertIsNone(find_activity_record(self.api("getCurrentProgress"),activity_id))
    def answer_qcm(self,label):
        radio=self.first_visible(self.page.get_by_role("radio",name=re.compile(f"^{re.escape(label)}$",re.I)))
        button=self.first_visible(self.page.get_by_role("button",name=re.compile(f"^{re.escape(label)}$",re.I)))
        control=radio or button
        if control is None:self.fail("QCM choice lacks accessible radio/button role and name")
        control.focus();self.page.keyboard.press("Space");self.click_named(VALIDATE_NAMES)
    def answer_fill(self,activity):
        slots=[s["slotId"] for s in activity["segments"] if "slotId" in s];token=activity["tokens"][0]
        controls=[]
        for slot in slots:
            c=self.first_visible(self.page.get_by_role("combobox",name=re.compile(slot,re.I)))
            if c is None:self.fail(f"slot {slot} lacks accessible combobox role/name")
            controls.append(c)
        for c in controls:
            try:c.select_option(value=token["tokenId"])
            except Exception:c.select_option(label=token["label"])
        self.click_named(VALIDATE_NAMES)
    def assert_activity_success(self,progress,activity,selected=None,slot_map=None):
        r=find_activity_record(progress,activity["activityRevisionId"]);self.assertIsNotNone(r,progress)
        self.assertIs(r.get("correct"),True,r);self.assertIs(r.get("completed"),True,r)
        if selected is not None:self.assertEqual(selected,r.get("selectedChoiceId"),r)
        if slot_map is not None:
            observed=r.get("answers") or r.get("slotAnswers") or r.get("responses")
            self.assertEqual(slot_map,observed,r)

    def test_empty_state_and_minimum_accessibility(self):
        self.assertEqual([],self.api("listCourses"));self.assertIsNotNone(self.first_visible(self.page.get_by_text(EMPTY_NAMES)))
        self.assertGreaterEqual(self.page.get_by_role("main").count(),1);self.assertGreaterEqual(self.page.get_by_role("heading",level=1).count(),1)
        unnamed=self.page.locator("button:visible").evaluate_all("els=>els.filter(e=>!((e.innerText||e.getAttribute('aria-label')||e.title||'').trim())).length")
        self.assertEqual(0,unnamed)
    def test_complete_visible_vertical_slice_persists_after_refresh_and_new_page(self):
        self.import_ui(self.valid);courses=self.wait_courses(1);course=self.valid["courses"][0];self.start_course(course["title"],course["activities"][0]["prompt"])
        q=course["activities"][0];self.assert_no_qcm_preselection(q["activityRevisionId"])
        correct=next(c["label"] for c in q["choices"] if c["choiceId"]==q["correctChoiceId"]);self.answer_qcm(correct);self.click_named(NEXT_NAMES)
        fill=course["activities"][1];self.page.get_by_text(fill["prompt"],exact=False).first.wait_for(state="visible");self.answer_fill(fill)
        cid=courses[0]["courseInstallId"];progress=self.api("getProgress",cid)
        self.assert_activity_success(progress,q,selected=q["correctChoiceId"])
        expected={a["slotId"]:a["tokenId"] for a in fill["answers"]};self.assert_activity_success(progress,fill,slot_map=expected)
        self.page.reload(wait_until="domcontentloaded");self.page.wait_for_function("()=>Boolean(window.__LEARNIT_NEXT_TEST__)");self.assertEqual(progress,self.api("getProgress",cid))
        reopened=self.context.new_page();reopened.goto(self.url);reopened.wait_for_function("()=>Boolean(window.__LEARNIT_NEXT_TEST__)")
        self.assertEqual(progress,reopened.evaluate("async id=>await window.__LEARNIT_NEXT_TEST__.getProgress(id)",cid));reopened.close()
    def test_legacy_and_malformed_rejection_reach_terminal_state_without_write(self):
        for payload,pattern in ((self.legacy,r"contract|version|legacy|learnit\.kit\.v2"),('{"contract":"learnit.kit.v2", invalid',r"json|syntax|invalid|invalide")):
            self.import_ui(payload);self.page.wait_for_function("p=>new RegExp(p,'i').test(document.body.innerText)",pattern)
            self.assertEqual([],self.api("listCourses"))
    def test_reordered_qcm_choices_keep_choice_id_correction_semantics(self):
        self.import_ui(self.reordered);courses=self.wait_courses(1);course=self.reordered["courses"][0];q=course["activities"][0]
        self.start_course(course["title"],q["prompt"]);self.assert_no_qcm_preselection(q["activityRevisionId"])
        label=next(c["label"] for c in q["choices"] if c["choiceId"]==q["correctChoiceId"]);self.answer_qcm(label)
        self.assert_activity_success(self.api("getProgress",courses[0]["courseInstallId"]),q,selected=q["correctChoiceId"])
    def test_fill_maxuses_one_is_rejected_without_progress_or_library_mutation(self):
        invalid=copy.deepcopy(self.valid);invalid["courses"][0]["activities"][1]["tokens"][0]["maxUses"]=1;invalid=recompute(invalid)
        self.import_ui(invalid);self.page.wait_for_function("()=>/max.?uses|token|invalid|invalide/i.test(document.body.innerText)")
        self.assertEqual([],self.api("listCourses"))
    def test_visible_reset_removes_successor_library_only(self):
        self.import_ui(self.valid);self.wait_courses(1);self.click_named(RESET_NAMES)
        confirm=self.first_visible(self.page.get_by_role("button",name=re.compile(r"confirmer|oui|confirm|yes",re.I)))
        if confirm is not None:confirm.click()
        self.wait_courses(0);self.assertIsNotNone(self.first_visible(self.page.get_by_text(EMPTY_NAMES)))

if __name__=="__main__":unittest.main(verbosity=2)
