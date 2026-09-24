from pathlib import Path
from playwright.sync_api import sync_playwright
import json

ROOT=Path(__file__).parent
raw=(ROOT/'index.html').read_text(encoding='utf-8')
mods=['lab_core.js','lab_baselines.js','lab_v6_helpers.js','lab_v6_flash.js','lab_v6_matching.js','lab_v7_order.js','lab_v6_classify.js','lab_v6_fill.js','lab_bootstrap.js']
html=raw.replace('<link rel="stylesheet" href="styles.css">','')
for n in mods: html=html.replace(f'<script src="{n}"></script>','')
css=(ROOT/'styles.css').read_text(encoding='utf-8')
scripts=[(ROOT/n).read_text(encoding='utf-8') for n in mods]
errors=[]; external=[]

def page(ctx):
    p=ctx.new_page()
    p.on('pageerror',lambda e:errors.append(str(e)))
    p.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) else None)
    p.set_content(html); p.add_style_tag(content=css)
    for s in scripts:p.add_script_tag(content=s)
    return p

def boxes(loc):
    return loc.evaluate_all('(xs)=>xs.map(x=>{const r=x.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})')

def same(a,b,t=.8):
    return len(a)==len(b) and all(abs(x-y)<=t for A,B in zip(a,b) for x,y in zip(A,B))

def touch_drag(p,src,dst):
    src.scroll_into_view_if_needed();dst.scroll_into_view_if_needed();p.wait_for_timeout(30)
    a=src.bounding_box();b=dst.bounding_box(); assert a and b
    sx,sy=a['x']+a['width']/2,a['y']+a['height']/2; dx,dy=b['x']+b['width']/2,b['y']+b['height']/2
    c=p.context.new_cdp_session(p)
    c.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'force':1,'id':1}]})
    for q in (.25,.5,.75,1):
        c.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+(dx-sx)*q,'y':sy+(dy-sy)*q,'force':1,'id':1}]});p.wait_for_timeout(25)
    return c

with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    c=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)

    p=page(c);p.select_option('#variant','flashcard-b');p.locator('.flash-b-card').click();p.get_by_role('button',name='Continuer').click();assert json.loads(p.locator('#response').text_content())=={'revealed':True};p.close()

    p=page(c);p.select_option('#variant','matching-b');cards=p.locator('.match-card');targets=p.locator('.pair-target');before=boxes(cards)+boxes(targets);cards.first.click();p.wait_for_timeout(40);assert same(before,boxes(cards)+boxes(targets));assert p.locator('.pair-target.eligible-destination').count()==3;targets.first.click();assert p.locator('.eligible-destination').count()==0 and p.locator('.pair-slot .match-card').count()==1;p.close()

    p=page(c);p.select_option('#variant','order-b');cards=p.locator('.order-b-card');lst=p.locator('.order-b-list');before=boxes(cards);h=lst.evaluate('e=>e.getBoundingClientRect().height');order0=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');cards.nth(1).click();p.wait_for_timeout(40);assert same(before,boxes(cards));assert abs(h-lst.evaluate('e=>e.getBoundingClientRect().height'))<1;slots=p.locator('.order-insert-slot');assert slots.count()==4 and all(slots.nth(i).bounding_box()['height']>=24 for i in range(4));slots.last.click();assert cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')!=order0
    p.select_option('#variant','order-b');cards=p.locator('.order-b-card');src=cards.nth(2);dst=cards.nth(0);order0=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');cdp=touch_drag(p,src,dst);assert p.locator('.order-ghost').count()==1 and p.locator('.order-placeholder.active-destination').count()==1;g=p.locator('.order-ghost').bounding_box();assert g;cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});p.wait_for_timeout(60);assert cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')!=order0;p.close()

    p=page(c);p.select_option('#variant','classify-b');cards=p.locator('.classify-card');buckets=p.locator('.bucket');before=boxes(cards)+boxes(buckets);cards.first.click();p.wait_for_timeout(30);assert same(before,boxes(cards)+boxes(buckets));assert p.locator('.classify-destination.eligible-destination').count()==2;cid=cards.first.get_attribute('data-card-id');buckets.first.locator('.classify-destination').click();assert buckets.first.locator(f'.classify-card[data-card-id="{cid}"]').count()==1 and p.locator('.eligible-destination').count()==0;p.close()

    p=page(c);p.select_option('#variant','fill-b');tokens=p.locator('.token-chip');slots=p.locator('.fill-slot');before=boxes(tokens)+boxes(slots);tokens.first.click();p.wait_for_timeout(30);assert same(before,boxes(tokens)+boxes(slots));assert p.locator('.fill-slot.eligible-destination').count()==2;tid=tokens.first.get_attribute('data-token-id');slots.first.click();assert slots.first.locator(f'.token-chip[data-token-id="{tid}"]').count()==1 and slots.first.evaluate('e=>getComputedStyle(e).borderTopStyle')=='none';p.close()

    assert not errors,errors; assert not external,external
    b.close()
print('BROWSER_LAB_V7_DESTINATION_FEEDBACK_AUDIT: PASS')
