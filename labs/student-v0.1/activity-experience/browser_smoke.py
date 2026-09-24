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
    for s in scripts:p.add_script_tag(content=s)
    assert p.evaluate('!!window.__LAB__')
    return p

def cdp_drag(page,src,dst):
    src.scroll_into_view_if_needed();dst.scroll_into_view_if_needed();page.wait_for_timeout(40)
    sb=src.bounding_box();db=dst.bounding_box();assert sb and db
    sx,sy=sb['x']+sb['width']/2,sb['y']+sb['height']/2
    dx,dy=db['x']+db['width']/2,db['y']+db['height']/2
    cdp=page.context.new_cdp_session(page)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'radiusX':7,'radiusY':7,'force':1,'id':1}]})
    for t in (.2,.4,.6,.8,1):
        x=sx+(dx-sx)*t;y=sy+(dy-sy)*t
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y,'radiusX':7,'radiusY':7,'force':1,'id':1}]});page.wait_for_timeout(30)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(70)

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)

    page=make_page(ctx)
    assert page.locator('#variant option').count()==12
    # Flash alignment / response
    page.select_option('#variant','flashcard-b');page.locator('.flash-b-card').click()
    for sel in ['.flash-question-repeat','.flash-answer','.flash-explanation']:
        assert page.locator(sel).evaluate("e=>getComputedStyle(e).textAlign") in ('left','start')
    page.get_by_role('button',name='Continuer').click();assert set(json.loads(page.locator('#response').text_content()))=={'revealed'}
    # deterministic randomization
    def qcm_order(seed):
        page.evaluate('(s)=>{window.__LAB_TEST_SEEDS__=[s];document.querySelector("#variant").value="qcm-a";window.__LAB__.render()}',seed)
        return page.locator('.qcm-option input').evaluate_all('(xs)=>xs.map(x=>x.value)')
    a=qcm_order(111);b=qcm_order(111);c=qcm_order(987654321);assert a==b and c!=a
    before=page.locator('.qcm-option input').evaluate_all('(xs)=>xs.map(x=>x.value)');page.locator('input[type=radio]').nth(1).check();after=page.locator('.qcm-option input').evaluate_all('(xs)=>xs.map(x=>x.value)');assert before==after
    page.close()

    # Matching: selected state distinct, no movement on repeated selection, no stacked frame when filled.
    page=make_page(ctx);page.select_option('#variant','matching-b');source=page.locator('.match-source');rows=page.locator('.pair-row')
    first=source.locator('.match-card').first;loc0=first.evaluate('(e)=>e.parentElement.className');first.click();page.wait_for_timeout(150);normal_bg=page.locator('.match-source-wrap').evaluate('e=>getComputedStyle(e).backgroundColor');selected_style=first.evaluate('e=>({bg:getComputedStyle(e).backgroundColor,border:getComputedStyle(e).borderColor,outline:getComputedStyle(e).outlineStyle})');assert selected_style['bg']!=normal_bg and selected_style['border']!='rgb(143, 160, 182)'
    assoc_before=page.locator('.pair-slot .match-card').count();source.locator('.match-card').nth(1).click();source.locator('.match-card').nth(0).click();assert page.locator('.pair-slot .match-card').count()==assoc_before
    # tap target path
    card=source.locator('.match-card').first;card.click();rows.nth(0).locator('.pair-target').click();assert rows.nth(0).locator('.match-card').count()==1
    slot=rows.nth(0).locator('.pair-slot');assert slot.evaluate("e=>getComputedStyle(e).borderTopStyle")=='none';assert rows.nth(0).evaluate("e=>getComputedStyle(e).borderTopStyle")=='none'
    # fill rest by drag
    while source.locator('.match-card').count():cdp_drag(page,source.locator('.match-card').first,rows.nth(source.locator('.match-card').count()))
    assert source.locator('.match-card').count()==0
    page.get_by_role('button',name='Émettre la réponse').click();assert set(json.loads(page.locator('#response').text_content()))=={'associations'}
    page.close()

    # Order: strict vertical ghost, placeholder moves/reflow before pointerup, drop changes order.
    page=make_page(ctx);page.select_option('#variant','order-b');cards=page.locator('.order-b-card');assert cards.count()==3
    before=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');src=cards.nth(2);dst=cards.nth(0);src.scroll_into_view_if_needed();dst.scroll_into_view_if_needed();page.wait_for_timeout(40)
    sb=src.bounding_box();db=dst.bounding_box();assert sb and db
    sx,sy=sb['x']+sb['width']/2,sb['y']+sb['height']/2;dy=db['y']+5
    cdp=ctx.new_cdp_session(page);cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'force':1,'id':1}]});page.wait_for_timeout(35)
    # A first vertical movement crosses the activation threshold and creates ghost + placeholder.
    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+30,'y':sy-12,'force':1,'id':1}]});page.wait_for_timeout(60)
    ghost0=page.locator('.order-ghost').bounding_box();ph0=page.locator('.order-placeholder').bounding_box();assert ghost0 and ph0
    fixed_x=ghost0['x']
    # Large move changes Y and insertion position while X of the ghost remains locked.
    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+90,'y':dy,'force':1,'id':1}]});page.wait_for_timeout(100)
    ghost1=page.locator('.order-ghost').bounding_box();ph1=page.locator('.order-placeholder').bounding_box();assert ghost1 and ph1
    assert abs(ghost1['x']-fixed_x)<2,(fixed_x,ghost1['x'])
    assert abs(ghost1['y']-ghost0['y'])>20
    assert abs(ph1['y']-ph0['y'])>5,(ph0,ph1)
    sibling_y=cards.nth(0).bounding_box()['y'];assert sibling_y>db['y']-5
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(80)
    after=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');assert after!=before,(before,after);assert page.locator('.order-ghost').count()==0 and page.locator('.order-placeholder').count()==0
    # no-drag intercalaires
    cards.nth(1).click();slots=page.locator('.order-insert-slot');assert slots.count()==4 and all(slots.nth(i).bounding_box()['height']>=40 for i in range(slots.count()))
    order1=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');slots.last.click();order2=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');assert order2!=order1
    page.get_by_role('button',name='Émettre la réponse').click();assert set(json.loads(page.locator('#response').text_content()))=={'orderedItemIds'}
    page.close()

    # Classify: no move panel; click card selects only; bucket tap moves exactly selected card; source tap returns.
    page=make_page(ctx);page.select_option('#variant','classify-b');assert page.locator('.move-panel').count()==0 and 'Déplacer «' not in page.locator('#stage').inner_text()
    source=page.locator('.classify-source-cards');buckets=page.locator('.bucket')
    loc=lambda: page.locator('.classify-card').evaluate_all('(xs)=>Object.fromEntries(xs.map(x=>[x.dataset.cardId,x.closest(".bucket")?.querySelector(".classify-destination")?.textContent||"source"]))')
    before=loc();cards=source.locator('.classify-card');cards.nth(0).click();cards.nth(1).click();cards.nth(2).click();assert loc()==before
    chosen=cards.nth(1).get_attribute('data-card-id');cards.nth(1).click();buckets.nth(0).locator('.classify-destination').click();assert loc()[chosen]==buckets.nth(0).locator('.classify-destination').text_content()
    placed=buckets.nth(0).locator(f'.classify-card[data-card-id="{chosen}"]');placed.click();buckets.nth(1).locator('.classify-destination').click();assert loc()[chosen]==buckets.nth(1).locator('.classify-destination').text_content()
    buckets.nth(1).locator(f'.classify-card[data-card-id="{chosen}"]').click();page.locator('.classify-source .classify-destination').click();assert loc()[chosen]=='source'
    # complete via tap destinations
    while source.locator('.classify-card').count():source.locator('.classify-card').first.click();buckets.nth(source.locator('.classify-card').count()%2).locator('.classify-destination').click()
    page.get_by_role('button',name='Émettre la réponse').click();assert set(json.loads(page.locator('#response').text_content()))=={'assignments'}
    page.close()

    # Fill: no move panel; token click only selects; slot tap places/replaces; bank tap returns; no double shell.
    page=make_page(ctx);page.select_option('#variant','fill-b');assert page.locator('.move-panel').count()==0 and 'Déplacer «' not in page.locator('#stage').inner_text()
    bank=page.locator('.token-bank');slots=page.locator('.fill-slot')
    floc=lambda: page.locator('.token-chip').evaluate_all('(xs)=>Object.fromEntries(xs.map(x=>[x.dataset.tokenId,x.closest(".fill-slot")?.dataset.slotId||"bank"]))')
    before=floc();chips=bank.locator('.token-chip');chips.nth(0).click();chips.nth(1).click();chips.nth(2).click();assert floc()==before
    first_id=chips.nth(0).get_attribute('data-token-id');chips.nth(0).click();slots.nth(0).click();assert floc()[first_id]=='s1';assert slots.nth(0).evaluate("e=>getComputedStyle(e).borderTopStyle")=='none'
    second=bank.locator('.token-chip').first;second_id=second.get_attribute('data-token-id');second.click();slots.nth(1).click();assert floc()[second_id]=='s2'
    # A filled slot is no longer an interactive shell; replacement remains available by explicit drag.
    assert slots.nth(1).get_attribute('role') is None and slots.nth(1).get_attribute('tabindex') is None
    third=bank.locator('.token-chip').first;third_id=third.get_attribute('data-token-id');cdp_drag(page,third,slots.nth(1));assert floc()[third_id]=='s2' and floc()[second_id]=='bank'
    # return selected placed token through the persistent bank title target
    slots.nth(0).locator('.token-chip').click();page.locator('.fill-bank-title').click();assert floc()[first_id]=='bank'
    # restore empty slot via direct tap path
    bank.locator('.token-chip').filter(has_text='observer').first.click();slots.nth(0).click();page.get_by_role('button',name='Émettre la réponse').click();assert set(json.loads(page.locator('#response').text_content()))=={'s1','s2'}
    page.close()

    # Long labels + no horizontal overflow.
    page=make_page(ctx);long='Texte extrêmement long destiné à vérifier que les contenus restent entièrement contenus dans leurs cartes même sur un écran mobile étroit sans débordement horizontal.'
    page.evaluate('(s)=>{window.__LAB__.fixtures.qcm.choices[0].label=s;window.__LAB__.fixtures.classify.items[1].label=s;window.__LAB__.fixtures.matching.leftItems[1].label=s;window.__LAB__.fixtures.order.items[1].label=s;window.__LAB__.fixtures.fill.tokens[1].label=s}',long)
    for vid,sel in [('qcm-a','.qcm-option'),('classify-b','.classify-card'),('matching-b','.match-card'),('order-b','.order-b-card'),('fill-b','.token-chip')]:
        page.select_option('#variant',vid);assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth'),vid;assert page.locator(sel).evaluate_all('(xs)=>xs.every(x=>x.scrollWidth<=x.clientWidth+1)'),vid
    page.emulate_media(reduced_motion='reduce');page.select_option('#variant','flashcard-b');page.locator('.flash-b-card').click();assert page.evaluate("getComputedStyle(document.querySelector('.flash-b-inner')).transitionDuration")=='0s'
    page.close()

    assert not external,external
    assert not errors,errors
    browser.close()
print('BROWSER_LAB_V5_INTERACTION_AUDIT: PASS')
