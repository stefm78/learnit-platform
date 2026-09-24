from pathlib import Path
from playwright.sync_api import sync_playwright
import json
ROOT=Path(__file__).parent
raw=(ROOT/'index.html').read_text(encoding='utf-8')
html=raw.replace('<link rel="stylesheet" href="styles.css">','')
for n in ['lab_core.js','lab_baselines.js','lab_candidates.js','lab_bootstrap.js']:
    html=html.replace(f'<script src="{n}"></script>','')
css=(ROOT/'styles.css').read_text(encoding='utf-8')
scripts=[(ROOT/n).read_text(encoding='utf-8') for n in ['lab_core.js','lab_baselines.js','lab_candidates.js','lab_bootstrap.js']]

def make_page(ctx):
    p=ctx.new_page(); p.set_content(html,wait_until='load'); p.add_style_tag(content=css)
    for s in scripts:p.add_script_tag(content=s)
    return p

def touch_drag(page,src,dst):
    src.scroll_into_view_if_needed();dst.scroll_into_view_if_needed();page.wait_for_timeout(35)
    sb=src.bounding_box();db=dst.bounding_box();assert sb and db
    sx,sy=sb['x']+sb['width']/2,sb['y']+sb['height']/2; dx,dy=db['x']+db['width']/2,db['y']+db['height']/2
    cdp=page.context.new_cdp_session(page);cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'force':1,'id':1}]})
    for t in (.25,.5,.75,1):
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+(dx-sx)*t,'y':sy+(dy-sy)*t,'force':1,'id':1}]});page.wait_for_timeout(25)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(60)

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)

    # Tap path must survive pointer handlers (regression found during V5 audit).
    p=make_page(ctx);p.select_option('#variant','matching-b');card=p.locator('.match-card').first;card.click();p.wait_for_timeout(160)
    assert card.get_attribute('aria-pressed')=='true'
    selected=card.evaluate('e=>({bg:getComputedStyle(e).backgroundColor,border:getComputedStyle(e).borderColor,outline:getComputedStyle(e).outlineStyle})')
    assert selected['bg']!='rgb(255, 255, 255)' and selected['outline']=='none'
    assert ':focus-visible' in css
    p.close()

    # No nested framing in Matching filled state; pair row itself has no border.
    p=make_page(ctx);p.select_option('#variant','matching-b');src=p.locator('.match-source');row=p.locator('.pair-row').first;src.locator('.match-card').first.click();row.locator('.pair-target').click();slot=row.locator('.pair-slot')
    assert slot.evaluate('e=>getComputedStyle(e).borderTopStyle')=='none'
    assert row.evaluate('e=>getComputedStyle(e).borderTopStyle')=='none'
    assert row.locator('.match-card').evaluate('e=>getComputedStyle(e).borderTopWidth')=='1px'
    p.close()

    # Order tap alternative and drag architecture are independent.
    p=make_page(ctx);p.select_option('#variant','order-b');cards=p.locator('.order-b-card');before=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');cards.nth(1).click();slots=p.locator('.order-insert-slot');assert slots.count()==4
    assert all(slots.nth(i).bounding_box()['height']>=40 for i in range(slots.count()))
    slots.last.click();after=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');assert after!=before
    # no permanent arrows/ordinals
    txt=p.locator('.order-b-list').inner_text();assert '↑' not in txt and '↓' not in txt
    p.close()

    # Classify destination remains directly available even when bucket has cards.
    p=make_page(ctx);p.select_option('#variant','classify-b');src=p.locator('.classify-source-cards');bucket=p.locator('.bucket').first
    src.locator('.classify-card').first.click();bucket.locator('.classify-destination').click();assert bucket.locator('.classify-card').count()==1
    src.locator('.classify-card').first.click();bucket.locator('.classify-destination').click();assert bucket.locator('.classify-card').count()==2
    # No stale movement panel and no nested interactive bucket container.
    assert p.locator('.move-panel').count()==0
    assert bucket.get_attribute('role') is None and bucket.get_attribute('tabindex') is None
    p.close()

    # Fill: empty slot is a direct target; filled slot loses target semantics/shell; drag replacement works.
    p=make_page(ctx);p.select_option('#variant','fill-b');bank=p.locator('.token-bank');slots=p.locator('.fill-slot')
    tok=bank.locator('.token-chip').first;tok.click();slots.nth(0).click();assert slots.nth(0).locator('.token-chip').count()==1
    assert slots.nth(0).get_attribute('role') is None and slots.nth(0).get_attribute('tabindex') is None
    assert slots.nth(0).evaluate('e=>getComputedStyle(e).borderTopStyle')=='none'
    bank.locator('.token-chip').first.click();slots.nth(1).click();old=slots.nth(1).locator('.token-chip').get_attribute('data-token-id')
    replacement=bank.locator('.token-chip').first;rid=replacement.get_attribute('data-token-id');touch_drag(p,replacement,slots.nth(1));assert slots.nth(1).locator('.token-chip').get_attribute('data-token-id')==rid and bank.locator(f'.token-chip[data-token-id="{old}"]').count()==1
    # Common card radius/border language across manipulable families.
    radii=[]
    for vid,selector in [('matching-b','.match-card'),('order-b','.order-b-card'),('classify-b','.classify-card'),('fill-b','.token-chip')]:
        p.select_option('#variant',vid);r=p.locator(selector).first.evaluate('e=>getComputedStyle(e).borderRadius');radii.append(r)
    assert len(set(radii))==1,radii
    p.close()

    # No nested actual buttons in any candidate DOM and no stale movement text.
    p=make_page(ctx)
    for vid in ['matching-b','order-b','classify-b','fill-b']:
        p.select_option('#variant',vid);assert p.locator('button button').count()==0;assert 'Déplacer «' not in p.locator('#stage').inner_text()
    p.close();browser.close()
print('PRODUCTION_AUDIT_V5: PASS')
