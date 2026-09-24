from pathlib import Path
from playwright.sync_api import sync_playwright
import json,re
ROOT=Path(__file__).parent
raw=(ROOT/'index.html').read_text(encoding='utf-8')
html=raw.replace('<link rel="stylesheet" href="styles.css">','')
for n in ['lab_core.js','lab_baselines.js','lab_candidates.js','lab_bootstrap.js']:
    html=html.replace(f'<script src="{n}"></script>','')
css=(ROOT/'styles.css').read_text(encoding='utf-8')
scripts=[(ROOT/n).read_text(encoding='utf-8') for n in ['lab_core.js','lab_baselines.js','lab_candidates.js','lab_bootstrap.js']]
external=[]; errors=[]

def make_page(ctx):
    p=ctx.new_page()
    p.on('request',lambda r: external.append(r.url) if r.url.startswith(('http:','https:')) else None)
    p.on('pageerror',lambda e: errors.append(str(e)))
    p.set_content(html,wait_until='load'); p.add_style_tag(content=css)
    for s in scripts: p.add_script_tag(content=s)
    assert p.evaluate('!!window.__LAB__')
    return p

def cdp_drag(page,src,dst,hold=False):
    src.scroll_into_view_if_needed(); dst.scroll_into_view_if_needed(); page.wait_for_timeout(40)
    sb=src.bounding_box(); db=dst.bounding_box(); assert sb and db
    sx,sy=sb['x']+sb['width']/2,sb['y']+sb['height']/2
    dx,dy=db['x']+db['width']/2,db['y']+db['height']/2
    cdp=page.context.new_cdp_session(page)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'radiusX':7,'radiusY':7,'force':1,'id':1}]})
    for t in (.2,.4,.6,.8,1):
        x=sx+(dx-sx)*t; y=sy+(dy-sy)*t
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y,'radiusX':7,'radiusY':7,'force':1,'id':1}]})
        page.wait_for_timeout(30)
    if hold: return cdp
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]}); page.wait_for_timeout(70)

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)

    # General, flash alignment, response grammar, layout.
    page=make_page(ctx)
    assert page.locator('#variant option').count()==12
    page.select_option('#variant','flashcard-b'); page.locator('.flash-b-card').click()
    for sel in ['.flash-question-repeat','.flash-answer','.flash-explanation']:
        assert page.locator(sel).evaluate("e=>getComputedStyle(e).textAlign") in ('left','start')
    page.get_by_role('button',name='Continuer').click(); assert set(json.loads(page.locator('#response').text_content()))=={'revealed'}
    page.select_option('#variant','lesson-a'); page.get_by_role('button',name='Continuer').click(); assert set(json.loads(page.locator('#response').text_content()))=={'acknowledged'}
    page.select_option('#variant','qcm-a'); page.locator('input[type=radio]').first.check(); page.get_by_role('button',name='Émettre la réponse').click(); assert set(json.loads(page.locator('#response').text_content()))=={'choiceId'}
    page.emulate_media(reduced_motion='reduce'); page.select_option('#variant','flashcard-b'); page.locator('.flash-b-card').click(); assert page.evaluate("getComputedStyle(document.querySelector('.flash-b-inner')).transitionDuration")=='0s'
    page.close()

    # Randomization: deterministic for same seed, different for different seed; stable during attempt.
    page=make_page(ctx)
    def qcm_order(seed):
        page.evaluate('(s)=>{window.__LAB_TEST_SEEDS__=[s];document.querySelector("#variant").value="qcm-a";window.__LAB__.render()}',seed)
        return page.locator('.qcm-option input').evaluate_all('(xs)=>xs.map(x=>x.value)')
    a=qcm_order(111); b=qcm_order(111); c=qcm_order(987654321)
    assert a==b and c!=a,(a,b,c)
    before=page.locator('.qcm-option input').evaluate_all('(xs)=>xs.map(x=>x.value)'); page.locator('input[type=radio]').nth(1).check(); after=page.locator('.qcm-option input').evaluate_all('(xs)=>xs.map(x=>x.value)'); assert before==after
    page.close()

    # Matching B stays functional with shuffled source/targets.
    page=make_page(ctx); page.select_option('#variant','matching-b'); source=page.locator('.match-source'); rows=page.locator('.pair-row')
    while source.locator('.match-card').count(): cdp_drag(page,source.locator('.match-card').first,rows.nth(source.locator('.match-card').count()-1))
    assert source.locator('.match-card').count()==0 and sum(rows.nth(i).locator('.match-card').count() for i in range(3))==3
    page.get_by_role('button',name='Émettre la réponse').click(); assert set(json.loads(page.locator('#response').text_content()))=={'associations'}
    page.close()

    # Order B: real touch, ghost follows pointer, DOM gap moves before pointerup, sibling rect reflows.
    page=make_page(ctx); page.select_option('#variant','order-b'); cards=page.locator('.order-b-card:not(.order-ghost)'); assert cards.count()==3
    before=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')
    first_rect_before=cards.nth(0).bounding_box(); assert first_rect_before
    src=cards.nth(2); dst=cards.nth(0); src.scroll_into_view_if_needed(); dst.scroll_into_view_if_needed(); page.wait_for_timeout(40)
    sb=src.bounding_box(); db=dst.bounding_box(); assert sb and db
    sx,sy=sb['x']+sb['width']/2,sb['y']+sb['height']/2; dx,dy=db['x']+db['width']/2,db['y']+db['height']*.15
    cdp=ctx.new_cdp_session(page); cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'force':1,'id':1}]}); page.wait_for_timeout(35)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':dx,'y':dy,'force':1,'id':1}]}); page.wait_for_timeout(100)
    assert page.locator('.order-ghost').count()==1
    ghost=page.locator('.order-ghost').bounding_box(); assert ghost and abs((ghost['y']+ghost['height']/2)-dy)<80
    during=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)'); assert during!=before,(before,during)
    # At least one sibling moved because the invisible insertion gap moved.
    rects=cards.evaluate_all('(xs)=>xs.map(x=>({id:x.dataset.id,y:x.getBoundingClientRect().y}))'); before_first_y=first_rect_before['y']; assert any(abs(x['y']-before_first_y)>5 for x in rects if x['id']==before[0]) or during[0]!=before[0]
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]}); page.wait_for_timeout(70)
    after_order=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')
    assert page.locator('.order-ghost').count()==0 and after_order==during
    first=cards.first; first.press('Space'); first.press('ArrowDown'); first.press('Space')
    page.get_by_role('button',name='Émettre la réponse').click(); assert set(json.loads(page.locator('#response').text_content()))=={'orderedItemIds'}
    page.close()

    # Classify B negative click oracle + explicit movement + no implicit bucket mutation.
    page=make_page(ctx); page.select_option('#variant','classify-b'); source=page.locator('.classify-source-cards'); buckets=page.locator('.bucket')
    loc=lambda: page.locator('.classify-card').evaluate_all('(xs)=>Object.fromEntries(xs.map(x=>[x.dataset.cardId,x.closest(".bucket")?.querySelector("h3")?.textContent||"source"]))')
    before=loc(); cards=source.locator('.classify-card'); cards.nth(0).click(); cards.nth(1).click(); cards.nth(2).click(); assert loc()==before
    # Dedicated fallback moves selected card only.
    page.locator('.move-buttons button[data-dest="b1"]').click(); assert buckets.nth(0).locator('.classify-card').count()==1
    # Fill remaining by drag.
    cdp_drag(page,source.locator('.classify-card').first,buckets.nth(1)); cdp_drag(page,source.locator('.classify-card').first,buckets.nth(0)); assert source.locator('.classify-card').count()==0
    after_place=loc(); allcards=page.locator('.classify-card');
    for i in range(allcards.count()): allcards.nth(i).click()
    assert loc()==after_place
    page.get_by_role('button',name='Émettre la réponse').click(); payload=json.loads(page.locator('#response').text_content()); assert set(payload)=={'assignments'} and len(payload['assignments'])==3
    page.close()

    # Fill B negative click oracle, occupied-slot simplification, explicit replacement only.
    page=make_page(ctx); page.select_option('#variant','fill-b'); bank=page.locator('.token-bank'); slots=page.locator('.fill-slot')
    floc=lambda: page.locator('.token-chip').evaluate_all('(xs)=>Object.fromEntries(xs.map(x=>[x.dataset.tokenId,x.closest(".fill-slot")?.dataset.slotId||"bank"]))')
    before=floc(); chips=bank.locator('.token-chip'); chips.nth(0).click(); chips.nth(1).click(); chips.nth(2).click(); assert floc()==before
    # Selected token -> explicit move button s1.
    page.locator('.move-buttons button[data-fill-dest="s1"]').click(); assert slots.nth(0).locator('.token-chip').count()==1
    cdp_drag(page,bank.locator('.token-chip').first,slots.nth(1)); assert slots.nth(1).locator('.token-chip').count()==1
    for i in range(2):
        assert slots.nth(i).evaluate("e=>e.classList.contains('filled')")
        assert slots.nth(i).evaluate("e=>getComputedStyle(e).borderTopStyle")=='none'
    placed=floc(); slots.nth(0).locator('.token-chip').click(); slots.nth(1).locator('.token-chip').click(); assert floc()==placed
    # Explicit drag replacement is allowed; displaced token returns to bank.
    cdp_drag(page,slots.nth(0).locator('.token-chip'),slots.nth(1)); assert bank.locator('.token-chip').count()==2 and slots.nth(0).locator('.token-chip').count()==0
    bank.locator('.token-chip').first.click(); page.locator('.move-buttons button[data-fill-dest="s1"]').click(); page.get_by_role('button',name='Émettre la réponse').click(); assert set(json.loads(page.locator('#response').text_content()))=={'s1','s2'}
    page.close()

    # Long labels and no horizontal overflow at 390px.
    page=make_page(ctx); long='Texte extrêmement long destiné à vérifier que les contenus restent entièrement contenus dans leurs cartes même sur un écran mobile étroit sans débordement horizontal.'
    page.evaluate('(s)=>{window.__LAB__.fixtures.qcm.choices[0].label=s;window.__LAB__.fixtures.classify.items[1].label=s;window.__LAB__.fixtures.matching.leftItems[1].label=s}',long)
    for vid,sel in [('qcm-a','.qcm-option'),('classify-b','.classify-card'),('matching-b','.match-card')]:
        page.select_option('#variant',vid); assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth'),vid; assert page.locator(sel).evaluate_all('(xs)=>xs.every(x=>x.scrollWidth<=x.clientWidth+1)'),vid
    page.close()

    assert not external,external
    assert not errors,errors
    browser.close()
print('BROWSER_LAB_V4_INTERACTION_AUDIT: PASS')
