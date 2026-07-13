#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "browser_navigation_report.json"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        OUT.write_text(json.dumps({"schema": "learnit.rc623.navigation_accessibility_matrix.v1", "ok": False, "error": f"playwright import failed: {exc}"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    manifest = json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))
    expected_version = f"Learn-it {manifest['rc']}"
    rows = []
    errors = []

    def add(code: str, ok: bool, detail: str = ""):
        rows.append({"code": code, "ok": bool(ok), "detail": detail})

    chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True, executable_path=chromium) if chromium else playwright.chromium.launch(headless=True)
        except Exception as exc:
            OUT.write_text(json.dumps({"schema": "learnit.rc623.navigation_accessibility_matrix.v1", "ok": False, "error": f"chromium launch failed: {exc}"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 1
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            page.set_default_timeout(7000)
            page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
            page.on("console", lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type == "error" else None)
            html = (ROOT / "dist" / "learnit.html").read_text(encoding="utf-8")
            page.set_content(html, wait_until="domcontentloaded")
            page.wait_for_timeout(500)

            main = page.locator("main[data-route-carousel]")
            add("version-current", page.locator(".version").first.text_content() == expected_version and page.title() == expected_version, f"{page.title()} / {page.locator('.version').first.text_content()}")
            add("four-persistent-route-panels", page.locator(".route-panel[data-route]").count() == 4, str(page.locator(".route-panel[data-route]").count()))
            add("initial-route-learn", main.get_attribute("data-active-route") == "learn" and main.get_attribute("data-active-index") == "0", f"{main.get_attribute('data-active-route')} / {main.get_attribute('data-active-index')}")

            # RC613/615: keyboard route parity, skip link and deterministic focus.
            page.locator('nav.nav button[data-nav="learn"]').focus()
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(420)
            active_focus = page.evaluate("document.activeElement && (document.activeElement.id || document.activeElement.getAttribute('data-nav') || document.activeElement.tagName)")
            add("keyboard-arrow-route-library", main.get_attribute("data-active-route") == "library" and active_focus == "route-heading-library", f"route={main.get_attribute('data-active-route')} focus={active_focus}")
            page.keyboard.press("Alt+3")
            page.wait_for_timeout(420)
            active_focus = page.evaluate("document.activeElement && (document.activeElement.id || document.activeElement.getAttribute('data-nav') || document.activeElement.tagName)")
            add("keyboard-shortcut-route-bilan", main.get_attribute("data-active-route") == "bilan" and active_focus == "route-heading-bilan", f"route={main.get_attribute('data-active-route')} focus={active_focus}")
            page.locator('.skip-link').focus()
            page.keyboard.press("Enter")
            page.wait_for_timeout(80)
            skip_focus = page.evaluate("document.activeElement && document.activeElement.id")
            add("skip-link-main-focus", skip_focus == "contenu", str(skip_focus))
            a11y = page.evaluate("window.__LEARNIT_TEST__.accessibilityReport()")
            add("inactive-routes-inert", a11y.get("activePanels") == 1 and a11y.get("inactivePanelsInert") == 3 and a11y.get("hiddenFocusable", 1) == 0, json.dumps(a11y, ensure_ascii=False))
            page.locator('nav.nav button[data-nav="learn"]').click()
            page.wait_for_timeout(420)

            def touch_swipe(selector: str, start_x: int, end_x: int, y: int = 650):
                page.evaluate(
                    """async ({selector,startX,endX,y}) => {
                      const target=document.querySelector(selector);
                      if(!target) throw new Error('missing swipe target '+selector);
                      const fire=(el,type,x)=>el.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,pointerId:77,pointerType:'touch',isPrimary:true,clientX:x,clientY:y,buttons:type==='pointerup'?0:1,button:0}));
                      fire(target,'pointerdown',startX);
                      const steps=7;
                      for(let i=1;i<=steps;i++){const x=startX+(endX-startX)*(i/steps);fire(document,'pointermove',x);await new Promise(r=>setTimeout(r,22));}
                      fire(document,'pointerup',endX);
                    }""",
                    {"selector": selector, "startX": start_x, "endX": end_x, "y": y},
                )
                page.wait_for_timeout(700)

            touch_swipe('.route-panel[data-route="learn"] .rc208-action-card', 340, 70)
            add("real-touch-swipe-learn-library", main.get_attribute("data-active-route") == "library" and main.get_attribute("data-active-index") == "1", f"{main.get_attribute('data-active-route')} / {main.get_attribute('data-active-index')}")

            nav_expected = [("learn", "0"), ("library", "1"), ("bilan", "2"), ("tools", "3")]
            for route, index in nav_expected:
                page.locator(f'nav.nav button[data-nav="{route}"]').click()
                page.wait_for_timeout(420)
                active_count = page.locator(".route-panel.is-active").count()
                add(f"tap-nav-{route}", main.get_attribute("data-active-route") == route and main.get_attribute("data-active-index") == index and active_count == 1, f"route={main.get_attribute('data-active-route')} index={main.get_attribute('data-active-index')} active={active_count}")

            page.locator('nav.nav button[data-nav="library"]').click()
            page.wait_for_timeout(1000)
            body_style_before_detail = page.evaluate("({position:getComputedStyle(document.body).position,overflow:getComputedStyle(document.body).overflow})")
            library = page.locator('.route-panel[data-route="library"]')
            rows_locator = library.locator(".book-row")
            add("library-course-rows", rows_locator.count() >= 3, str(rows_locator.count()))
            library.locator(".book-row.is-selected button.book-open-main").evaluate("el => el.click()")
            page.wait_for_timeout(350)
            detail = page.locator(".book-detail-sheet")
            add("layered-library-detail", detail.count() == 1 and detail.get_attribute("data-library-detail-shell") == "rc663", f"detail={detail.count()}")
            sheet_position = detail.evaluate("el => getComputedStyle(el).position") if detail.count() else "missing"
            body_style = page.evaluate("({position:getComputedStyle(document.body).position,overflow:getComputedStyle(document.body).overflow})")
            add("fixed-sheet-without-body-position-lock", sheet_position == "fixed" and body_style["position"] != "fixed", f"sheet={sheet_position} before={body_style_before_detail} after={body_style}")

            detail.get_by_role("button", name="Plan").click()
            page.wait_for_timeout(320)
            shell = page.locator(".book-detail-sheet .chapter-static-shell")
            chapters = shell.locator(".chapter")
            add("list-first-chapter-shell", shell.count() == 1 and shell.get_attribute("data-chapter-navigation-contract") == "list-first", str(shell.count()))
            add("chapter-list-is-single-navigation-owner", chapters.count() >= 2 and shell.locator('[data-action="library-prev-chapter"],[data-action="library-next-chapter"],.chapter-reading-head,.chapter-static-contract').count() == 0, f"chapters={chapters.count()}")
            add("plan-removes-course-stepper", page.locator('.book-detail-sheet .book-modal.plan-mode .book-head-nav').count() == 0)
            before_index = shell.get_attribute("data-chapter-index")
            chapters.nth(1).click()
            page.wait_for_timeout(300)
            shell = page.locator(".book-detail-sheet .chapter-static-shell")
            after_index = shell.get_attribute("data-chapter-index")
            selected = shell.locator('.chapter[aria-selected="true"]')
            action_chapter = shell.locator('[data-action="library-chapter-go"]').get_attribute('data-chapter')
            add("chapter-direct-selection-works", before_index == "0" and after_index == "1" and selected.count() == 1 and selected.get_attribute('data-chapter') == "1" and action_chapter == "1", f"{before_index}->{after_index} selected={selected.count()} action={action_chapter}")

            route_before_content_swipe = main.get_attribute("data-active-route")
            touch_swipe('.book-detail-sheet .chapter-static-panel', 340, 70, 600)
            add("chapter-content-excludes-route-swipe", main.get_attribute("data-active-route") == route_before_content_swipe == "library", f"before={route_before_content_swipe} after={main.get_attribute('data-active-route')}")
            sheet_overflow = page.locator('.book-detail-sheet .book-modal-body').evaluate("el => getComputedStyle(el).overflowY")
            add("native-sheet-scroll-owner", sheet_overflow in {"auto", "scroll"}, sheet_overflow)

            page.locator('[data-action="library-home"]').click(); page.wait_for_timeout(160)
            report = page.evaluate("window.__LEARNIT_TEST__.mobileSwipeReport()")
            add("runtime-report-route-only", bool(report.get("routeOnlyGestureOrchestrator")) and report.get("nestedChapterSwipe") is False and report.get("chapterNavigation") == "list-first" and report.get("keyboardAlternative") is True, json.dumps(report, ensure_ascii=False)[:1200])
            page.emulate_media(reduced_motion="reduce")
            page.locator('nav.nav button[data-nav="bilan"]').click(); page.wait_for_timeout(120)
            reduced = page.evaluate("window.__LEARNIT_TEST__.accessibilityReport()")
            add("reduced-motion-detected", reduced.get("reducedMotion") is True, json.dumps(reduced, ensure_ascii=False))
            page.evaluate("document.documentElement.style.fontSize='200%'")
            page.wait_for_timeout(100)
            reflow = page.evaluate("({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,bodyWidth:document.body.scrollWidth})")
            add("text-zoom-reflow", reflow["scrollWidth"] <= reflow["clientWidth"] + 4, json.dumps(reflow, ensure_ascii=False))
            add("no-browser-errors", not errors, " | ".join(errors[-10:]))
        finally:
            browser.close()

    ok = all(row["ok"] for row in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "learnit.rc623.navigation_accessibility_matrix.v1", "ok": ok, "checks": rows, "errors": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "passed": sum(row["ok"] for row in rows), "total": len(rows), "report": str(OUT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
