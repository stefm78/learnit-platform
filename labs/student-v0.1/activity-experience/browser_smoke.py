from pathlib import Path
from playwright.sync_api import sync_playwright
import json

ROOT = Path(__file__).parent.resolve()
html = (ROOT / 'index.html').read_text(encoding='utf-8')
css = (ROOT / 'styles.css').read_text(encoding='utf-8')
js = (ROOT / 'lab.js').read_text(encoding='utf-8')
# Browser policy in the execution host blocks local URL navigation.  The smoke
# therefore loads the same static bytes directly into a blank page, with no
# network navigation or external dependencies.
html = html.replace('<link rel="stylesheet" href="styles.css">', '').replace('<script src="lab.js"></script>', '')

variants = ['lesson-a','flashcard-a','flashcard-b','matching-a','matching-b','order-a','order-b','classify-a','classify-b','qcm-a','fill-a']
expected_keys = {
    'lesson-a': {'acknowledged'}, 'flashcard-a': {'revealed'}, 'flashcard-b': {'revealed'},
    'matching-a': {'associations'}, 'matching-b': {'associations'},
    'order-a': {'orderedItemIds'}, 'order-b': {'orderedItemIds'},
    'classify-a': {'assignments'}, 'classify-b': {'assignments'},
    'qcm-a': {'choiceId'}, 'fill-a': {'s1','s2'},
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    context = browser.new_context(viewport={'width':390,'height':844}, has_touch=True, is_mobile=True)
    page = context.new_page()
    external, errors = [], []
    page.on('request', lambda r: external.append(r.url) if r.url.startswith(('http:','https:')) else None)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.set_content(html, wait_until='load')
    page.add_style_tag(content=css)
    page.add_script_tag(content=js)

    assert page.evaluate('!!window.__LAB__'), errors
    assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth')

    for vid in variants:
        page.select_option('#variant', vid)
        page.wait_for_function("v => document.querySelector('#variant').value === v", arg=vid)
        assert page.locator('#response').get_attribute('data-emitted') is None, vid
        assert page.locator('#stage button, #stage select, #stage input').count() > 0, vid
        focusables = page.locator('#stage button:not([disabled]), #stage select:not([disabled]), #stage input:not([disabled])')
        assert focusables.count() > 0, vid
        focusables.first.focus()
        assert page.evaluate('document.activeElement!==document.body')
        for loc in page.locator('#stage button:visible, #stage select:visible').all():
            bb = loc.bounding_box()
            assert bb and bb['height'] >= 40, (vid, bb)

        if vid == 'lesson-a':
            page.get_by_role('button', name='Continuer').press('Enter')
        elif vid.startswith('flashcard-'):
            # Continue does not exist in the accessibility tree until reveal.
            assert page.get_by_role('button', name='Continuer').count() == 0
            page.get_by_role('button', name='Afficher la réponse').press('Enter')
            page.get_by_role('button', name='Continuer').press('Enter')
        elif vid.startswith('matching-'):
            send = page.get_by_role('button', name='Émettre la réponse')
            send.press('Enter')
            assert page.locator('#response').get_attribute('data-emitted') is None
            left = page.locator('#stage .column').nth(0).locator('button')
            right = page.locator('#stage .column').nth(1).locator('button')
            if vid == 'matching-b':
                assert left.first.get_attribute('draggable') == 'true'
            for i in range(left.count()):
                left.nth(i).press('Enter')
                right.nth(i).press('Enter')
            send.press('Enter')
        elif vid.startswith('order-'):
            page.locator('#stage button[aria-label^="Monter"]').nth(1).press('Enter')
            if vid == 'order-b':
                assert page.locator('#stage li[draggable="true"]').count() > 0
            page.get_by_role('button', name='Émettre la réponse').press('Enter')
        elif vid.startswith('classify-'):
            send = page.get_by_role('button', name='Émettre la réponse')
            send.press('Enter')
            assert page.locator('#response').get_attribute('data-emitted') is None
            page.locator('#stage').evaluate("root => { for (const s of [...root.querySelectorAll('select')]) { s.selectedIndex = 1; s.dispatchEvent(new Event('change', {bubbles:true})); } }")
            if vid == 'classify-b':
                assert page.locator('#stage [draggable="true"]').count() > 0
            send.press('Enter')
        elif vid == 'qcm-a':
            send = page.get_by_role('button', name='Émettre la réponse')
            send.press('Enter')
            assert page.locator('#response').get_attribute('data-emitted') is None
            page.locator('#stage input[type=radio]').first.check()
            send.press('Enter')
        elif vid == 'fill-a':
            send = page.get_by_role('button', name='Émettre la réponse')
            send.press('Enter')
            assert page.locator('#response').get_attribute('data-emitted') is None
            sels = page.locator('#stage select')
            for i in range(sels.count()):
                sels.nth(i).select_option(index=i+1)
            send.press('Enter')

        assert page.locator('#response').get_attribute('data-emitted') == 'true', vid
        payload = json.loads(page.locator('#response').text_content())
        assert set(payload) == expected_keys[vid], (vid, payload)
        assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth'), vid

    page.emulate_media(reduced_motion='reduce')
    page.select_option('#variant', 'flashcard-b')
    page.get_by_role('button', name='Afficher la réponse').click()
    assert page.evaluate("getComputedStyle(document.querySelector('.flash-inner')).transitionDuration") == '0s'

    # Screen-reader smoke: landmarks/labels/status are exposed and no unnamed controls.
    assert page.locator('main').count() == 1
    assert page.locator('[aria-label="Inspecteur de réponse"]').count() == 1
    assert page.locator('#stage button').evaluate_all('(xs)=>xs.every(x=>x.getAttribute("aria-label")||x.textContent.trim())')
    assert page.locator('#stage select').evaluate_all('(xs)=>xs.every(x=>x.getAttribute("aria-label")||x.labels.length)')
    assert not external, external
    assert not errors, errors
    browser.close()

print('BROWSER_ACCESSIBILITY_SMOKE: PASS')
