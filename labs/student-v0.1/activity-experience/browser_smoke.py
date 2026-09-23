from pathlib import Path
from playwright.sync_api import sync_playwright
import json,re
ROOT=Path(__file__).parent
raw_html=(ROOT/'index.html').read_text(encoding='utf-8')
html=raw_html.replace('<link rel="stylesheet" href="styles.css">','').replace('<script src="lab.js"></script>','')
css=(ROOT/'styles.css').read_text(encoding='utf-8')
scripts=[(ROOT/n).read_text(encoding='utf-8') for n in ['lab_core.js','lab_baselines.js','lab_candidates_a.js','lab_candidates_b.js','lab_candidates_c.js','lab_bootstrap.js']]
variant_ids=[x['id'] for x in json.loads(re.search(r'<script id="variants" type="application/json">\s*(.*?)\s*</script>',raw_html,re.S).group(1))]
external=[]; errors=[]

def make_page(ctx):
    page=ctx.new_page()
    page.on('request',lambda r: external.append(r.url) if r.url.startswith(('http:','https:')) else None)
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.set_content(html,wait_until='load');page.add_style_tag(content=css);[page.add_script_tag(content=x) for x in scripts]
    assert page.evaluate('!!window.__LAB__')
    return page

def cdp_drag(page,src,dst):
    src.scroll_into_view_if_needed(); dst.scroll_into_view_if_needed(); page.wait_for_timeout(35)
    sb=src.bounding_box(); db=dst.bounding_box(); assert sb and db
    sx,sy=sb['x']+sb['width']/2,sb['y']+sb['height']/2
    dx,dy=db['x']+db['width']/2,db['y']+db['height']/2
    cdp=page.context.new_cdp_session(page)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'radiusX':7,'radiusY':7,'force':1,'id':1}]})
    for t in (.25,.5,.75,1):
        x=sx+(dx-sx)*t;y=sy+(dy-sy)*t
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y,'radiusX':7,'radiusY':7,'force':1,'id':1}]})
        page.wait_for_timeout(25)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(60)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)

    # General structure, response grammar, mobile layout.
    page=make_page(ctx)
    assert page.locator('#variant option').count()==12
    page.select_option('#variant','flashcard-a');assert page.locator('.flash-b-card').count()==0
    page.select_option('#variant','flashcard-b');assert page.locator('.flash-b-card').count()==1 and page.locator('.flash-question-repeat').count()==1
    page.select_option('#variant','matching-a');assert page.locator('.pair-row').count()==0
    page.select_option('#variant','matching-b');assert page.locator('.pair-row').count()==3
    page.select_option('#variant','order-b');assert page.locator('.order-b-card').count()==3 and '↑' not in page.locator('#stage').inner_text() and '↓' not in page.locator('#stage').inner_text()
    assert not re.search(r'(^|\s)[123](\s|$)',page.locator('.order-b-list').inner_text())
    page.select_option('#variant','classify-b');assert page.locator('.bucket').count()==2
    page.select_option('#variant','fill-b');assert page.locator('.fill-slot').count()==2
    page.select_option('#variant','lesson-a');page.get_by_role('button',name='Continuer').click();assert set(json.loads(page.locator('#response').text_content()))=={'acknowledged'}
    page.select_option('#variant','flashcard-a');page.get_by_role('button',name='Afficher la réponse').click();page.get_by_role('button',name='Continuer').click();assert set(json.loads(page.locator('#response').text_content()))=={'revealed'}
    page.select_option('#variant','flashcard-b');page.locator('.flash-b-card').click();assert 'Que signifie' in page.locator('.flash-question-repeat').inner_text();page.get_by_role('button',name='Continuer').click();assert set(json.loads(page.locator('#response').text_content()))=={'revealed'}
    page.select_option('#variant','qcm-a');page.locator('input[type=radio]').first.check();page.get_by_role('button',name='Émettre la réponse').click();assert set(json.loads(page.locator('#response').text_content()))=={'choiceId'}
    page.select_option('#variant','fill-a');sels=page.locator('.fill-a-sentence select');sels.nth(0).select_option('t1');sels.nth(1).select_option('t2');page.get_by_role('button',name='Émettre la réponse').click();assert json.loads(page.locator('#response').text_content())=={'s1':'t1','s2':'t2'}
    for vid in variant_ids:
        page.select_option('#variant',vid);assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth'),vid;assert page.locator('#stage button,#stage select,#stage input,[tabindex="0"]').count()>0,vid
    page.emulate_media(reduced_motion='reduce');page.select_option('#variant','flashcard-b');page.locator('.flash-b-card').click();assert page.evaluate("getComputedStyle(document.querySelector('.flash-b-inner')).transitionDuration")=='0s'
    page.close()

    # Matching B causal touch + persistent paired rows + fallback.
    page=make_page(ctx);page.select_option('#variant','matching-b');rows=page.locator('.pair-row');source=page.locator('.match-source')
    assert source.locator('.match-card').count()==3
    for i in range(3): cdp_drag(page,source.locator('.match-card').first,rows.nth(i))
    assert source.locator('.match-card').count()==0
    assert all(rows.nth(i).locator('.match-card').count()==1 for i in range(3))
    page.get_by_role('button',name='Émettr la réponse').click();payload=json.loads(page.locator('#response').text_content());assert set(payload)=={'associations'} and len(payload['associations'])==3
    cdp_drag(page,rows.nth(0).locator('.match-card'),rows.nth(1));assert source.locator('.match-card').count()==1
    source.locator('.match-card').first.press('Enter');rows.nth(0).locator('.pair-target').press('Enter');assert rows.nth(0).locator('.match-card').count()==1
    page.close()

    # Order B causal whole-card drag with reflow, and keyboard fallback.
    page=make_page(ctx);page.select_option('#variant','order-b');cards=page.locator('.order-b-card');cards.nth(2).scroll_into_view_if_needed();cards.nth(1).scroll_into_view_if_needed();page.wait_for_timeout(35)
    before=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')
    sb=cards.nth(2).bounding_box();db=cards.nth(1).bounding_box();assert sb and db
    sx,sy=sb['x']+sb['width']/2,sb['y']+sb['height']/2;dx,dy=db['x']+db['width']/2,db['y']+db['height']*.25
    cdp=ctx.new_cdp_session(page);cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'force':1,'id':1}]});page.wait_for_timeout(25)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':dx,'y':dy,'force':1,'id':1}]});page.wait_for_timeout(60)
    during=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');assert during!=before
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(40)
    assert cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')==during
    first=cards.first;first.press('Space');first.press('ArrowDown');first.press('Space')
    page.get_by_role('button',name='Émettre la réponse').click();assert set(json.loads(page.locator('#response').text_content()))=={'orderedItemIds'}
    page.close()

    # Classify B source-to-bucket DOM motion, inter-bucket motion, fallback.
    page=make_page(ctx);page.select_option('#variant','classify-b');source=page.locator('.classify-source-cards');buckets=page.locator('.bucket')
    for target_index in (0,1,0): cdp_drag(page,source.locator('.classify-card').first,buckets.nth(target_index))
    assert source.locator('.classify-card').count()==0 and buckets.nth(0).locator('.classify-card').count()==2 and buckets.nth(1).locator('.classify-card').count()==1
    cdp_drag(page,buckets.nth(0).locator('.classify-card').first,buckets.nth(1));assert buckets.nth(1).locator('.classify-card').count()==2
    buckets.nth(1).locator('.classify-card').first.press('Enter');page.locator('.classify-source').press('Enter');assert source.locator('.classify-card').count()==1
    source.locator('.classify-card').first.press('Enter');buckets.nth(0).press('Enter');page.get_by_role('button',name='Émettre la réponse').click();payload=json.loads(page.locator('#response').text_content());assert set(payload)=={'assignments'} and len(payload['assignments'])==3
    page.close()

    # Fill B token drag, reassignment, fallback, exact slot mapping.
    page=make_page(ctx);page.select_option('#variant','fill-b');bank=page.locator('.token-bank');slots=page.locator('.fill-slot')
    cdp_drag(page,bank.locator('.token-chip').first,slots.nth(0));assert bank.locator('.token-chip').count()==2
    cdp_drag(page,bank.locator('.token-chip').first,slots.nth(1));assert bank.locator('.token-chip').count()==1
    cdp_drag(page,slots.nth(0).locator('.token-chip'),slots.nth(1));assert bank.locator('.token-chip').count()==2 and slots.nth(0).locator('.token-chip').count()==0
    bank.locator('.token-chip').filter(has_text='tester').press('Enter');slots.nth(0).press('Enter')
    if slots.nth(1).locator('.token-chip').count()==0:
        bank.locator('.token-chip').first.press('Enter');slots.nth(1).press('Enter')
    page.get_by_role('button',name='Émettre la réponse').click();payload=json.loads(page.locator('#response').text_content());assert set(payload)=={'s1','s2'}
    page.close()

    # Long-label stress in fresh page at 390px.
    page=make_page(ctx);long='Texte extrêmement long destiné à vérifier que les contenus restent entièrement contenus dans leurs cartes même sur un écran mobile étroit sans débordement horizontal.'
    page.evaluate('(s)=>{window.__LAB__.fixtures.qcm.choices[0].label=s;window.__LAB__.fixtures.classify.items[1].label=s;window.__LAB__.fixtures.matching.leftItems[1].label=s}',long)
    for vid,selector in [('qcm-a','.qcm-option'),('classify-b','.classify-card'),('matching-b','.match-card')]:
        page.select_option('#variant',vid);assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth'),vid;assert page.locator(selector).evaluate_all('(xs)=>xs.every(x=>x.scrollWidth<=x.clientWidth+1)'),vid
    page.close()

    assert not external, external
    assert not errors, errors
    browser.close()
print('BROWSER_LAB_V3_TOUCH_AUDIT: PASS')
