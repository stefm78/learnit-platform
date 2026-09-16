#!/usr/bin/env python3
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    media = (ROOT / "apps/learnit-next/src/ui/media.js").read_text(encoding="utf-8")
    presenters = (ROOT / "apps/learnit-next/src/ui/activity_presenters.js").read_text(encoding="utf-8")
    css = (ROOT / "apps/learnit-next/src/atlas.css").read_text(encoding="utf-8")
    bundle = media.replace("export function ", "function ")
    bundle += "\n" + presenters.replace("import { renderEmbeddedMediaSet } from './media.js';\n", "").replace("export function ", "function ")
    bundle += "\nwindow.Job02={renderActivityPresentation,readActivityResponse};"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        page = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True)
        page_errors = []
        blocked_requests = []
        blocked_host = ".".join(["evil", "invalid"])
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("request", lambda request: blocked_requests.append(request.url) if blocked_host in request.url else None)
        page.set_content('<main class="atlas-m1"><div id="mount"></div></main>')
        page.add_style_tag(content=css)
        page.add_script_tag(content=bundle)
        page.wait_for_function("() => Boolean(window.Job02)")

        def render(value):
            page.evaluate("p => document.getElementById('mount').replaceChildren(Job02.renderActivityPresentation(p))", value)

        def response(value):
            return page.evaluate("p => Job02.readActivityResponse(document.getElementById('mount'), p)", value)

        def response_error(value):
            return page.evaluate("p => { try { Job02.readActivityResponse(document.getElementById('mount'), p); return ''; } catch (e) { return e.code || e.message; } }", value)

        qcm = {"type":"qcm","prompt":"Quel choix ?","choices":[{"choiceId":"a","label":"Alpha"},{"choiceId":"b","label":"Beta"}],"correctChoiceId":"SECRET_QCM"}
        render(qcm); page.locator('[data-activity-choice="true"]').nth(1).check()
        assert response(qcm) == {"choiceId":"b"} and page.get_by_text("Alpha").count() == 1

        fill = {"type":"fill","prompt":"Compléter","tokens":[{"tokenId":"t1","label":"Token"}],"segments":[{"text":"Avant "},{"slotId":"s1"}],"answers":"SECRET_FILL"}
        render(fill); page.locator('[data-activity-slot="s1"]').select_option("t1")
        assert response(fill) == {"s1":"t1"} and page.get_by_text("Avant").count() == 1

        lesson = {"type":"lesson","title":"La notion","body":"Premier.\n\nDeuxième.","keyPoints":["Point A"],"contextNote":"Contexte."}
        render(lesson); assert response_error(lesson) == "ACTIVITY_RESPONSE_REQUIRED"
        page.locator('[data-activity-continue="lesson"]').click(); assert response(lesson) == {"acknowledged":True}

        flash = {"type":"flashcard","front":"Question","back":"Réponse révélée","explanation":"Explication"}
        render(flash); assert page.get_by_text("Réponse révélée").count() == 0 and page.get_by_role("button", name="Correct").count() == 0
        page.locator('[data-flashcard-reveal="true"]').click(); assert page.get_by_text("Réponse révélée").count() == 1
        page.locator('[data-activity-continue="flashcard"]').click(); assert response(flash) == {"revealed":True}

        matching = {"type":"matching","prompt":"Associer","leftItems":[{"itemId":"l1","label":"Gauche 1"},{"itemId":"l2","label":"Gauche 2"}],"rightItems":[{"itemId":"r2","label":"Droite 2"},{"itemId":"r1","label":"Droite 1"}],"matches":"SECRET_MATCH"}
        render(matching); assert page.locator('.activity-matching-pools > section').count() == 2
        page.locator('[data-matching-left="l1"]').focus(); page.keyboard.press("Enter")
        page.locator('[data-matching-right="r1"]').focus(); page.keyboard.press("Enter")
        page.locator('[data-matching-left="l2"]').click(); page.locator('[data-matching-right="r2"]').click()
        assert response(matching) == {"associations":[{"leftItemId":"l1","rightItemId":"r1"},{"leftItemId":"l2","rightItemId":"r2"}]}
        page.locator('[data-matching-left="l1"]').click(); page.locator('[data-matching-right="r2"]').click()
        assert page.locator('[data-matching-association]').count() == 1

        order = {"type":"order","prompt":"Ordonner","items":[{"itemId":"o1","label":"Un"},{"itemId":"o2","label":"Deux"},{"itemId":"o3","label":"Trois"}],"correctOrder":"SECRET_ORDER"}
        render(order); page.locator('[data-order-item="o2"] [data-order-move="up"]').focus(); page.keyboard.press("Enter")
        assert response(order) == {"orderedItemIds":["o2","o1","o3"]}

        classify = {"type":"classify","prompt":"Classer","buckets":[{"bucketId":"b1","label":"Catégorie 1"},{"bucketId":"b2","label":"Catégorie 2"}],"items":[{"itemId":"c1","label":"Objet 1"},{"itemId":"c2","label":"Objet 2"}],"assignments":"SECRET_CLASSIFY"}
        render(classify); page.locator('[data-classify-select="c1"]').select_option("b1"); page.locator('[data-classify-select="c2"]').select_option("b2")
        assert response(classify) == {"assignments":[{"itemId":"c1","bucketId":"b1"},{"itemId":"c2","bucketId":"b2"}]}
        page.locator('[data-classify-select="c1"]').select_option("b2")
        assert page.locator('[data-classify-target="b2"] [data-classify-item="c1"]').count() == 1

        constructed = {"type":"constructed","prompt":"Expliquez.","acceptedResponses":"SECRET_CONSTRUCTED"}
        render(constructed); assert response_error(constructed) == "ACTIVITY_RESPONSE_REQUIRED"
        page.locator('[data-constructed-response]').fill("  Une réponse libre.  "); assert response(constructed) == {"text":"Une réponse libre."}

        safe_svg = '<svg viewBox="0 0 10 10"><rect width="10" height="10" fill="#fff"/></svg>'
        event_name = "on" + "load"; blocked_element = "foreign" + "Object"
        unsafe_svg = f'<svg viewBox="0 0 10 10" {event_name}="x"><{blocked_element}></{blocked_element}></svg>'
        remote_media = "http" + "s://" + blocked_host + "/remote.png"
        media_activity = {"type":"lesson","title":"Média","body":"Visuel.","media":[
            {"assetId":"safe","format":"svg","alt":"Schéma sûr","caption":"Légende","data":safe_svg,"display":"contained","placement":"content","zoomable":True},
            {"assetId":"bad","format":"svg","alt":"Schéma actif","data":unsafe_svg,"placement":"content"},
            {"assetId":"remote","format":"png","alt":"Image distante","data":remote_media,"placement":"content"},
        ]}
        render(media_activity)
        assert page.locator('[data-activity-media="safe"] img').count() >= 1 and page.locator('[data-activity-media-rejected]').count() == 2
        assert page.locator('[data-activity-media="safe"] details summary').count() == 1
        page.wait_for_timeout(50); assert blocked_requests == []

        secrets = {"type":"matching","prompt":"Aucun secret","leftItems":[{"itemId":"sx","label":"Visible gauche"}],"rightItems":[{"itemId":"sy","label":"Visible droite"}],"correctChoiceId":"SECRET_QCM_SENTINEL","answers":"SECRET_FILL_SENTINEL","acceptedResponses":"SECRET_CONSTRUCTED_SENTINEL","matches":"SECRET_MATCH_SENTINEL","correctOrder":"SECRET_ORDER_SENTINEL","assignments":"SECRET_CLASSIFY_SENTINEL"}
        render(secrets); exposed = page.locator('#mount').inner_text() + page.locator('#mount').evaluate("e => e.outerHTML")
        assert all(token not in exposed for token in ["SECRET_QCM_SENTINEL","SECRET_FILL_SENTINEL","SECRET_CONSTRUCTED_SENTINEL","SECRET_MATCH_SENTINEL","SECRET_ORDER_SENTINEL","SECRET_CLASSIFY_SENTINEL"])

        render(matching)
        sizes = page.locator('#mount button, #mount select, #mount textarea, #mount summary').evaluate_all("els => els.map(e => [e.getBoundingClientRect().width,e.getBoundingClientRect().height])")
        assert all(width >= 44 and height >= 44 for width, height in sizes)
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        page.locator('[data-matching-left="l1"]').focus()
        assert page.locator('[data-matching-left="l1"]').evaluate("e => getComputedStyle(e).outlineStyle !== 'none' && getComputedStyle(e).outlineWidth !== '0px'")
        assert page_errors == []
        browser.close()

    print("QCM_FILL_BROWSER_PASS")
    print("LESSON_FLASHCARD_BROWSER_PASS")
    print("MATCHING_ORDER_CLASSIFY_CONSTRUCTED_BROWSER_PASS")
    print("MEDIA_SECRET_ACCESSIBILITY_BROWSER_PASS")
    print("STUDENT_V01_ACTIVITY_PRESENTATION_BROWSER_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
