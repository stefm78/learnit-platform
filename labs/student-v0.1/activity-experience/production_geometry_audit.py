from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).parent
raw=(ROOT/'index.html').read_text(encoding='utf-8')
mods=['lab_core.js','lab_baselines.js','lab_v6_helpers.js','lab_v6_flash.js','lab_v6_matching.js','lab_v7_order.js','lab_v6_classify.js','lab_v6_fill.js','lab_bootstrap.js']
html=raw.replace('<link rel="stylesheet" href="styles.css">','')
for n in mods:
    html=html.replace(f'<script src="{n}"></script>','')
css=(ROOT/'styles.css').read_text(encoding='utf-8')
order_js=(ROOT/'lab_v7_order.js').read_text(encoding='utf-8')
scripts=[(ROOT/n).read_text(encoding='utf-8') for n in mods]

assert 'min-height:54px' not in css
assert '.order-placeholder{box-sizing:border-box;min-height:0!important' in css
assert "row.style.position='absolute'" in order_js
assert "placeholder.style.width=`${s.width}px`" in order_js
assert "placeholder.style.height=`${s.height}px`" in order_js
assert "restoreRowStyle(row,s)" in order_js

def close(a,b,t=1.0): return abs(a-b)<=t
def box(loc):
    r=loc.bounding_box(); assert r; return r
def list_h(page): return box(page.locator('.order-b-list'))['height']

def make_page(ctx,long=False):
    p=ctx.new_page();p.set_content(html,wait_until='load');p.add_style_tag(content=css)
    for s in scripts:p.add_script_tag(content=s)
    p.select_option('#variant','order-b')
    if long:
        p.evaluate("()=>{document.querySelector('.order-b-label').textContent='Un libellé volontairement beaucoup plus long, sur plusieurs lignes, afin de provoquer une hauteur variable et de vérifier qu’aucune hypothèse de hauteur fixe ne subsiste.'}")
        p.wait_for_timeout(30)
    return p

def drag(page,source_i,target_i,cancel=False):
    cards=page.locator('.order-b-card')
    ids0=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')
    src=cards.nth(source_i);dst=cards.nth(target_i)
    s=box(src);d=box(dst);H=list_h(page)
    sx,sy=s['x']+s['width']/2,s['y']+s['height']/2
    c=page.context.new_cdp_session(page)
    c.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'force':1,'id':1}]})
    page.wait_for_timeout(15)
    c.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+30,'y':sy+8,'force':1,'id':1}]})
    page.wait_for_timeout(60)

    ph=box(page.locator('.order-placeholder'))
    assert close(ph['width'],s['width']) and close(ph['height'],s['height']),(ph,s)
    assert close(list_h(page),H),(list_h(page),H)
    assert src.evaluate("e=>getComputedStyle(e).position")=='absolute'

    reps=page.locator('.order-b-list').evaluate("""e=>[...e.children].filter(x=>x.classList.contains('order-placeholder')||(x.classList.contains('order-b-card')&&getComputedStyle(x).position!=='absolute')).length""")
    assert reps==len(ids0),reps

    target_y=(d['y']+2) if target_i<source_i else (d['y']+d['height']-2)
    c.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+120,'y':target_y,'force':1,'id':1}]})
    page.wait_for_timeout(70)
    assert close(list_h(page),H)

    flow=page.locator('.order-b-list').evaluate("""e=>[...e.children].filter(x=>x.classList.contains('order-placeholder')||(x.classList.contains('order-b-card')&&getComputedStyle(x).position!=='absolute')).map(x=>{const r=x.getBoundingClientRect();return {y:r.y,b:r.bottom}}).sort((a,b)=>a.y-b.y)""")
    gap=float(page.locator('.order-b-list').evaluate("e=>getComputedStyle(e).rowGap").replace('px',''))
    for a,b in zip(flow,flow[1:]):
        assert close(b['y']-a['b'],gap),(flow,gap)

    c.send('Input.dispatchTouchEvent',{'type':'touchCancel' if cancel else 'touchEnd','touchPoints':[]})
    page.wait_for_timeout(60)

    assert page.locator('.order-placeholder').count()==0
    assert page.locator('.order-ghost').count()==0
    assert src.evaluate("e=>getComputedStyle(e).position")!='absolute'
    assert src.get_attribute('style') in (None,'')
    assert close(list_h(page),H)

    ids1=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')
    if cancel:
        assert ids1==ids0,(ids0,ids1)
    return ids0,ids1

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)

    p=make_page(ctx)
    for source_i,target_i in [(0,2),(2,0),(1,0),(1,2)]:
        ids0,ids1=drag(p,source_i,target_i,False)
        assert ids0!=ids1,(source_i,target_i,ids0,ids1)
    p.close()

    p=make_page(ctx,long=True)
    drag(p,0,2,False)
    drag(p,2,0,True)
    p.close()

    p=make_page(ctx,long=True)
    p.set_viewport_size({'width':320,'height':844})
    drag(p,0,2,False)
    p.close()

    browser.close()

print('ADVERSARIAL_PRODUCTION_GEOMETRY_AUDIT_V7: PASS')
