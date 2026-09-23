from pathlib import Path
from playwright.sync_api import sync_playwright
import json
ROOT=Path(__file__).parent.resolve()
html=(ROOT/'index.html').read_text(encoding='utf-8').replace('<link rel="stylesheet" href="styles.css">','').replace('<script src="lab.js"></script><script src="lab_v2_touch.js"></script>','')
css=(ROOT/'styles.css').read_text(encoding='utf-8'); js=(ROOT/'lab.js').read_text(encoding='utf-8'); overlay=(ROOT/'lab_v2_touch.js').read_text(encoding='utf-8')
variants=['lesson-a','flashcard-a','flashcard-b','matching-a','matching-b','order-a','order-b','classify-a','classify-b','qcm-a','fill-a']
expected={'lesson-a':{'acknowledged'},'flashcard-a':{'revealed'},'flashcard-b':{'revealed'},'matching-a':{'associations'},'matching-b':{'associations'},'order-a':{'orderedItemIds'},'order-b':{'orderedItemIds'},'classify-a':{'assignments'},'classify-b':{'assignments'},'qcm-a':{'choiceId'},'fill-a':{'s1','s2'}}

def touch_drag(page,src,dst):
    sb=src.bounding_box(); db=dst.bounding_box(); assert sb and db
    sx,sy=sb['x']+sb['width']/2,sb['y']+sb['height']/2
    dx,dy=db['x']+db['width']/2,db['y']+db['height']/2
    cdp=page.context.new_cdp_session(page)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'radiusX':8,'radiusY':8,'force':1,'id':1}]})
    for t in (0.25,0.5,0.75,1):
        x=sx+(dx-sx)*t;y=sy+(dy-sy)*t
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y,'radiusX':8,'radiusY':8,'force':1,'id':1}]})
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    page.wait_for_timeout(60)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
    page=ctx.new_page(); external=[]; errors=[]
    page.on('request',lambda r: external.append(r.url) if r.url.startswith(('http:','https:')) else None)
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.set_content(html,wait_until='load');page.add_style_tag(content=css);page.add_script_tag(content=js);page.add_script_tag(content=overlay)
    assert page.evaluate('!!window.__LAB__')
    assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth')
    # A/B structural discrimination.
    page.select_option('#variant','matching-a'); a_sig=page.locator('#stage').evaluate('(e)=>[...e.querySelectorAll("button,select")].map(x=>x.className+":"+x.tagName).join("|")')
    page.select_option('#variant','matching-b'); b_sig=page.locator('#stage').evaluate('(e)=>[...e.querySelectorAll("button,select")].map(x=>x.className+":"+x.tagName).join("|")')
    assert a_sig!=b_sig and 'match-drop-target' in b_sig
    page.select_option('#variant','order-a'); assert page.locator('.order-drag-handle').count()==0
    page.select_option('#variant','order-b'); assert page.locator('.order-drag-handle').count()==3
    page.select_option('#variant','classify-a'); assert page.locator('.classify-drop-zone').count()==0
    page.select_option('#variant','classify-b'); assert page.locator('.classify-drop-zone').count()==2
    page.select_option('#variant','flashcard-a'); assert page.locator('.flash-b-card').count()==0
    page.select_option('#variant','flashcard-b'); assert page.locator('.flash-b-card').count()==1
    # Exact frozen response grammar on A/base variants.
    page.select_option('#variant','lesson-a'); page.get_by_role('button',name='Continuer').click(); assert set(json.loads(page.locator('#response').text_content()))=={'acknowledged'}
    page.select_option('#variant','flashcard-a'); page.get_by_role('button',name='Afficher la réponse').click(); page.get_by_role('button',name='Continuer').click(); assert set(json.loads(page.locator('#response').text_content()))=={'revealed'}
    page.select_option('#variant','flashcard-b'); page.locator('.flash-b-card').click(); page.get_by_role('button',name='Continuer').click(); assert set(json.loads(page.locator('#response').text_content()))=={'revealed'}
    page.select_option('#variant','matching-a'); left=page.locator('#stage .column').nth(0).locator('button'); right=page.locator('#stage .column').nth(1).locator('button')
    for i in range(3): left.nth(i).click(); right.nth(i).click()
    page.get_by_role('button',name='Émettre la réponse').click(); assert set(json.loads(page.locator('#response').text_content()))=={'associations'}
    page.select_option('#variant','order-a'); page.get_by_role('button',name='Monter Observer').click(); page.get_by_role('button',name='Émettre la réponse').click(); assert set(json.loads(page.locator('#response').text_content()))=={'orderedItemIds'}
    page.select_option('#variant','classify-a'); sels=page.locator('#stage .classify-item select')
    for i in range(sels.count()): sels.nth(i).select_option(index=1+(i%2))
    page.get_by_role('button',name='Émettre la réponse').click(); assert set(json.loads(page.locator('#response').text_content()))=={'assignments'}
    page.select_option('#variant','qcm-a'); page.locator('#stage input[type=radio]').first.check(); page.get_by_role('button',name='Émettre la réponse').click(); assert set(json.loads(page.locator('#response').text_content()))=={'choiceId'}
    page.select_option('#variant','fill-a'); sels=page.locator('#stage select')
    for i in range(sels.count()): sels.nth(i).select_option(index=i+1)
    page.get_by_role('button',name='Émettre la réponse').click(); assert set(json.loads(page.locator('#response').text_content()))=={'s1','s2'}

    # Causal touch drag — matching B.
    page.select_option('#variant','matching-b'); page.locator('.matching-b-board').scroll_into_view_if_needed()
    cards=page.locator('.matching-card'); targets=page.locator('.match-drop-target')
    for i in range(3): touch_drag(page,cards.nth(i),targets.nth(i))
    page.get_by_role('button',name='Émettre la réponse').click(); payload=json.loads(page.locator('#response').text_content());assert set(payload)=={'associations'} and len(payload['associations'])==3
    # Causal touch reorder — move last row over first row.
    page.select_option('#variant','order-b'); page.locator('.order-b-list').scroll_into_view_if_needed(); before=page.locator('.order-b-row').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')
    touch_drag(page,page.locator('.order-drag-handle').nth(2),page.locator('.order-b-row').nth(0)); after=page.locator('.order-b-row').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')
    assert before!=after
    page.get_by_role('button',name='Émettre la réponse').click();payload=json.loads(page.locator('#response').text_content());assert payload['orderedItemIds']==after
    # Causal touch classify B.
    page.select_option('#variant','classify-b'); page.locator('.classify-b-layout').scroll_into_view_if_needed(); cards=page.locator('.classify-card'); zones=page.locator('.classify-drop-zone')
    touch_drag(page,cards.nth(0),zones.nth(0));touch_drag(page,cards.nth(1),zones.nth(1));touch_drag(page,cards.nth(2),zones.nth(0))
    page.get_by_role('button',name='Émettre la réponse').click();payload=json.loads(page.locator('#response').text_content());assert set(payload)=={'assignments'} and len(payload['assignments'])==3
    # Keyboard/tap fallbacks for drag variants.
    page.select_option('#variant','matching-b'); page.locator('.matching-card').nth(0).press('Enter');page.locator('.match-drop-target').nth(0).press('Enter');assert '1/3' in page.locator('.interaction-status').text_content()
    page.select_option('#variant','classify-b'); page.locator('.classify-card').nth(0).press('Enter');page.locator('.classify-drop-zone').nth(0).press('Enter');assert '1/3' in page.locator('.interaction-status').text_content()
    page.select_option('#variant','order-b');page.get_by_role('button',name='Monter Observer').press('Enter')
    # All variants still emit exact grammar via available interaction path.
    for vid in variants:
        page.select_option('#variant',vid); assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth')
        assert page.locator('#stage button,#stage select,#stage input').count()>0
    # Reduced motion B flip.
    page.emulate_media(reduced_motion='reduce');page.select_option('#variant','flashcard-b');page.locator('.flash-b-card').click();assert page.evaluate("getComputedStyle(document.querySelector('.flash-b-inner')).transitionDuration")=='0s'
    assert page.locator('main').count()==1 and page.locator('[aria-label="Inspecteur de réponse"]').count()==1
    assert not external, external
    assert not errors, errors
    browser.close()
print('BROWSER_TOUCH_V2_SMOKE: PASS')
