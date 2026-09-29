#!/usr/bin/env python3
"""390x844 browser oracle for JOB_29_G5_INLINE_COURSE_TITLE_RENAME_AFFORDANCE_R1."""
from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps" / "learnit-next"
ARTIFACT = APP / "dist" / "learnit-next.html"
KIT = ROOT / "showcase" / "student-v0.1" / "nombres-complexes" / "nombres_complexes_student_v01_v5.json"
EVIDENCE = Path(os.environ.get("JOB29_EVIDENCE_DIR", "/tmp/atlas-wp071-g5-inline-title-rename-evidence"))
EVIDENCE.mkdir(parents=True, exist_ok=True)

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return

@contextmanager
def serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ARTIFACT.parent)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/{ARTIFACT.name}"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)

def rect(locator) -> dict[str, float]:
    box = locator.bounding_box(); assert box is not None
    return {k: float(box[k]) for k in ("x", "y", "width", "height")}

def stable(before: dict[str, float], after: dict[str, float], fields=("x","y","width","height")) -> None:
    for field in fields:
        assert abs(before[field] - after[field]) <= 1.0, (field, before, after)

def no_overflow(page) -> None:
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def engine_snapshot(page) -> dict[str, Any]:
    return page.evaluate("""async () => {
      const report=await window.__LEARNIT_NEXT_TEST__.storageReport();
      return new Promise((resolve,reject)=>{
        const req=indexedDB.open(report.indexedDbName);
        req.onerror=()=>reject(req.error);
        req.onsuccess=()=>{
          const db=req.result;
          const stores=['courses','progress','objectiveProgress'].filter(x=>db.objectStoreNames.contains(x));
          const tx=db.transaction(stores,'readonly'); const result={}; let pending=stores.length;
          if(!pending){db.close();resolve(result);return;}
          for(const name of stores){const get=tx.objectStore(name).getAll();get.onerror=()=>reject(get.error);get.onsuccess=()=>{result[name]=get.result;pending-=1;};}
          tx.oncomplete=()=>{db.close();resolve(result);};tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);
        };
      });
    }""")

def open_import(page) -> None:
    page.get_by_role("button", name="Ouvrir la navigation").click()
    page.get_by_role("button", name="Importer un cours").click()
    page.locator(".library-file-picker").wait_for()

def open_library(page) -> None:
    page.get_by_role("button", name="Ouvrir la navigation").click()
    page.get_by_role("button", name="Tous les cours").click()
    page.get_by_role("heading", name="Vos cours").wait_for()

def import_kit(page) -> dict[str, Any]:
    page.locator("#kit-file").set_input_files({"name": KIT.name, "mimeType": "application/json", "buffer": KIT.read_bytes()})
    page.get_by_role("button", name="Ajouter à la bibliothèque").click()
    page.locator(".course-card[data-course-install-id]").first.wait_for()
    rows=page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()"); assert len(rows)==1
    return rows[0]

def clone_extra_courses(page) -> None:
    page.evaluate("""async () => {
      const report=await window.__LEARNIT_NEXT_TEST__.storageReport();
      await new Promise((resolve,reject)=>{
        const req=indexedDB.open(report.indexedDbName);req.onerror=()=>reject(req.error);
        req.onsuccess=()=>{const db=req.result;const names=['courses'];if(db.objectStoreNames.contains('libraryMetadata'))names.push('libraryMetadata');
          const tx=db.transaction(names,'readwrite'),courses=tx.objectStore('courses'),get=courses.getAll();get.onerror=()=>reject(get.error);
          get.onsuccess=()=>{const source=get.result[0];for(const [suffix,label,second] of [['second','Deuxième cours','00'],['third','Troisième cours','01']]){
            const clone=structuredClone(source);clone.courseInstallId=source.courseInstallId+'-'+suffix;clone.packageRevisionId='synthetic-layout-'+suffix;clone.displayLabel=label;clone.installedAt='2099-01-01T00:00:'+second+'Z';courses.put(clone);
            if(names.includes('libraryMetadata'))tx.objectStore('libraryMetadata').put({courseInstallId:clone.courseInstallId,displayLabel:label});
          }};tx.oncomplete=()=>{db.close();resolve();};tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);};
      });
    }""")

def title_relation(page, card, expected_name: str) -> None:
    heading=card.get_by_role("heading", name=expected_name, exact=True); assert heading.count()==1
    edit=card.get_by_role("button", name=f"Renommer le cours {expected_name}", exact=True); assert edit.count()==1
    geom=page.evaluate("""([h,b]) => {
      const r=document.createRange();r.selectNodeContents(h);
      const rects=[...r.getClientRects()].filter(x=>x.width>0&&x.height>0);
      const last=rects.at(-1);const eb=b.getBoundingClientRect();
      return {last:{x:last.x,y:last.y,right:last.right,bottom:last.bottom,width:last.width,height:last.height},
              edit:{x:eb.x,y:eb.y,right:eb.right,bottom:eb.bottom,width:eb.width,height:eb.height},lines:rects.length};
    }""",[heading.element_handle(),edit.element_handle()])
    assert geom["edit"]["x"] >= geom["last"]["right"] - 1.5, geom
    assert geom["edit"]["x"] - geom["last"]["right"] <= 12.0, geom
    assert geom["edit"]["y"] < geom["last"]["bottom"] + 4 and geom["edit"]["bottom"] > geom["last"]["y"] - 4, geom

def effective_hit_target(page, edit) -> None:
    box=rect(edit);assert box["width"]<=32 and box["height"]<=32 and box["width"]<44 and box["height"]<44,box
    style=edit.evaluate("""el => {const s=getComputedStyle(el),p=getComputedStyle(el,'::before');return {
      borderTop:s.borderTopWidth,borderRight:s.borderRightWidth,bg:s.backgroundColor,pw:p.width,ph:p.height
    }}""")
    assert style["borderTop"]=="0px" and style["borderRight"]=="0px",style
    assert style["bg"] in ("rgba(0, 0, 0, 0)","transparent"),style
    assert float(style["pw"].replace("px",""))>=44 and float(style["ph"].replace("px",""))>=44,style
    hit=page.evaluate("""el => {
      const r=el.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,pts=[[cx-20,cy],[cx+20,cy],[cx,cy-20],[cx,cy+20]];
      return pts.map(([x,y])=>{const t=document.elementFromPoint(x,y);return t===el||el.contains(t);});
    }""",edit.element_handle())
    assert all(hit),hit

def main() -> int:
    assert ARTIFACT.is_file(), ARTIFACT
    canonical=json.loads(KIT.read_text(encoding="utf-8"))["courses"][0]["title"]
    with serve() as url, sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":390,"height":844},has_touch=True,is_mobile=True)
        page=context.new_page(); errors=[]; external=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("request",lambda r:external.append(r.url) if r.url.startswith(("http://","https://")) and "127.0.0.1" not in r.url else None)
        page.goto(url,wait_until="load");page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")

        menu=page.get_by_role("button",name="Ouvrir la navigation");assert menu.locator(".nav-menu-bar").count()==3
        mb=menu.bounding_box();assert mb and mb["width"]>=44 and mb["height"]>=44
        menu.focus();menu.press("Enter");page.get_by_role("dialog").wait_for();page.keyboard.press("Escape")

        open_import(page);import_kit(page);clone_extra_courses(page);page.reload();page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)");open_library(page)
        cards=page.locator(".learner-course-card");assert cards.count()==3
        card=cards.first;next_card=cards.nth(1);title=card.locator(".course-title-slot")
        start=card.get_by_role("button",name="Commencer");objective=card.locator(".course-objectives-details > summary")
        assert title.count()==1 and start.count()==1 and objective.count()==1

        objective.click();r15=card.locator('[data-objective-progress-r15="true"]');assert r15.count()==1
        reservoirs=r15.locator('button.objective-progress-r15__reservoir');assert reservoirs.count()>=1
        reservoirs.first.click();assert r15.locator('[data-objective-progress-r15-selected="true"]').count()==1;objective.click()

        search=page.locator(".library-search-input");search.fill("nombres complexes");assert page.locator(".course-card:not([hidden])").count()>=1
        search.fill("complexes absent");assert page.locator(".course-card:not([hidden])").count()==0
        search.fill("");assert page.locator(".course-card:not([hidden])").count()==3

        edit=card.get_by_role("button",name=f"Renommer le cours {canonical}",exact=True)
        assert edit.count()==1 and card.locator(".learner-course-actions .course-rename-button").count()==0
        assert card.locator(".course-settings-details,.course-settings-menu").count()==0
        effective_hit_target(page,edit);title_relation(page,card,canonical)
        before_engine=engine_snapshot(page)
        before={"card":rect(card),"title":rect(title),"start":rect(start),"objective":rect(objective),"next":rect(next_card)}
        page.screenshot(path=str(EVIDENCE/"01-inline-pencil-before-rename.png"),full_page=True)

        edit.tap();overlay=card.locator("[data-course-rename-overlay='true']");overlay.wait_for()
        ob=rect(overlay);vp=page.evaluate("() => ({width:innerWidth,height:innerHeight})")
        assert ob["x"]>=-1 and ob["y"]>=-1 and ob["x"]+ob["width"]<=vp["width"]+1 and ob["y"]+ob["height"]<=vp["height"]+1,(ob,vp)
        inp=overlay.locator("input");assert page.evaluate("() => document.activeElement?.matches('[data-course-rename-overlay] input')") is True
        sel=inp.evaluate("el => [el.selectionStart,el.selectionEnd,el.value.length]");assert sel==[0,len(canonical),len(canonical)]
        during={"card":rect(card),"title":rect(title),"start":rect(start),"objective":rect(objective),"next":rect(next_card)}
        stable(before["card"],during["card"],fields=("height",));stable(before["title"],during["title"]);stable(before["start"],during["start"]);stable(before["objective"],during["objective"]);stable(before["next"],during["next"]);no_overflow(page)
        page.screenshot(path=str(EVIDENCE/"02-overlay-open-no-reflow.png"),full_page=True)

        inp.fill("Nom temporaire");page.keyboard.press("Escape");assert overlay.count()==0
        assert page.evaluate("() => document.activeElement?.classList.contains('course-rename-button')") is True
        assert engine_snapshot(page)==before_engine

        edit=card.get_by_role("button",name=f"Renommer le cours {canonical}",exact=True);edit.press("Enter")
        overlay=card.locator("[data-course-rename-overlay='true']");overlay.wait_for();inp=overlay.locator("input")
        alias="Nombres complexes — édition locale";inp.fill(alias);inp.press("Enter")
        card.get_by_role("heading",name=alias,exact=True).wait_for();edit=card.get_by_role("button",name=f"Renommer le cours {alias}",exact=True)
        assert page.evaluate("() => document.activeElement?.classList.contains('course-rename-button')") is True
        title_relation(page,card,alias);effective_hit_target(page,edit);no_overflow(page)
        page.screenshot(path=str(EVIDENCE/"03-saved-alias-inline-pencil.png"),full_page=True)

        edit.press("Enter");overlay=card.locator("[data-course-rename-overlay='true']");overlay.wait_for();inp=overlay.locator("input")
        long_alias="Nombres complexes — formes algébriques, polaires et exponentielles pour une révision guidée complète"
        inp.fill(long_alias);inp.press("Enter");card.get_by_role("heading",name=long_alias,exact=True).wait_for()
        title_relation(page,card,long_alias)
        line_count=card.get_by_role("heading",name=long_alias,exact=True).evaluate("""h=>{const r=document.createRange();r.selectNodeContents(h);return [...r.getClientRects()].filter(x=>x.width>0&&x.height>0).length}""")
        assert line_count>=2,line_count
        page.screenshot(path=str(EVIDENCE/"04-wrapped-title-inline-pencil.png"),full_page=True)

        rows=page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
        assert any(r["title"]==long_alias and r["canonicalTitle"]==canonical for r in rows)
        assert sum(1 for r in rows if r["title"]==long_alias)==1
        assert any(r["title"]=="Deuxième cours" for r in rows) and any(r["title"]=="Troisième cours" for r in rows)
        assert engine_snapshot(page)==before_engine

        page.reload();page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)");open_library(page)
        page.get_by_role("heading",name=long_alias,exact=True).wait_for()
        rows=page.evaluate("() => window.__LEARNIT_NEXT_TEST__.listCourses()")
        assert any(r["title"]==long_alias and r["canonicalTitle"]==canonical for r in rows)
        no_overflow(page);assert not errors,errors;assert not external,external
        browser.close()

    print("INLINE_VISUAL_INTEGRATION=PASS")
    print("EFFECTIVE_TOUCH_TARGET=PASS")
    print("NO_LAYOUT_SHIFT_390x844=PASS")
    print("RENAME_POINTER_KEYBOARD_ESCAPE_ENTER=PASS")
    print("ALIAS_PERSISTENCE_CANONICAL_IMMUTABILITY=PASS")
    print("MULTI_COURSE_ISOLATION=PASS")
    print("SEARCH_HAMBURGER_R15_REGRESSION=PASS")
    print("NO_EXTERNAL_NETWORK=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
