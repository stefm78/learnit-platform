from pathlib import Path
from playwright.sync_api import sync_playwright
import math

ROOT=Path(__file__).parent
mods=['lab_core.js','lab_baselines.js','lab_v6_helpers.js','lab_v6_flash.js','lab_v6_matching.js','lab_v7_order.js','lab_v6_classify.js','lab_v6_fill.js','lab_bootstrap.js']
raw=(ROOT/'index.html').read_text(encoding='utf-8')
html=raw.replace('<link rel="stylesheet" href="styles.css">','')
for n in mods: html=html.replace(f'<script src="{n}"></script>','')
css=(ROOT/'styles.css').read_text(encoding='utf-8')
scripts=[(ROOT/n).read_text(encoding='utf-8') for n in mods]

def make_page(ctx):
    p=ctx.new_page();p.set_content(html,wait_until='load');p.add_style_tag(content=css)
    for s in scripts:p.add_script_tag(content=s)
    p.select_option('#variant','order-b')
    return p

def rect(loc):
    r=loc.bounding_box(); assert r; return r

def close(a,b,tol=1.0):
    return abs(a-b)<=tol

def assert_rect_equal(a,b,tol=1.0):
    for k in ('x','y','width','height'):
        assert close(a[k],b[k],tol),(k,a,b)

def row_state(page):
    return page.locator('.order-b-card').evaluate_all('(xs)=>xs.map(x=>({id:x.dataset.id,rect:(()=>{const r=x.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})(),position:getComputedStyle(x).position,style:x.getAttribute("style")||""}))')

def list_height(page):
    return page.locator('.order-b-list').evaluate('e=>e.getBoundingClientRect().height')

def gap_px(page):
    s=page.locator('.order-b-list').evaluate('e=>getComputedStyle(e).rowGap')
    return float(s.replace('px',''))

def touch_start_move(page,src,dx=20,dy=9):
    src.scroll_into_view_if_needed();page.wait_for_timeout(40)
    b=rect(src);sx,sy=b['x']+b['width']/2,b['y']+b['height']/2
    cdp=page.context.new_cdp_session(page)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'force':1,'id':1}]})
    page.wait_for_timeout(20)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+dx,'y':sy+dy,'force':1,'id':1}]})
    page.wait_for_timeout(80)
    return cdp,(sx,sy)

def touch_move(cdp,x,y):
    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y,'force':1,'id':1}]})

def touch_end(cdp):
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})

def touch_cancel(cdp):
    cdp.send('Input.dispatchTouchEvent',{'type':'touchCancel','touchPoints':[]})

def assert_flow_geometry(page,expected_count):
    ph=page.locator('.order-placeholder');assert ph.count()==1
    reps=page.locator('.order-b-list').evaluate('''e=>{
      const xs=[...e.children].filter(x=>x.classList.contains('order-placeholder') || (x.classList.contains('order-b-card') && getComputedStyle(x).position!=='absolute'));
      return xs.map(x=>{const r=x.getBoundingClientRect();return {kind:x.classList.contains('order-placeholder')?'placeholder':'card',y:r.y,b:r.bottom,h:r.height}})
    }''')
    assert len(reps)==expected_count,reps
    reps=sorted(reps,key=lambda x:x['y']);g=gap_px(page)
    for a,b in zip(reps,reps[1:]):
        assert close(b['y']-a['b'],g,1.0),(reps,g)

def exact_activation_case(page,source_index):
    cards=page.locator('.order-b-card')
    before=row_state(page);lh0=list_height(page)
    src=cards.nth(source_index);src_before=rect(src)
    others_before={x['id']:x['rect'] for x in before if x['id']!=src.get_attribute('data-id')}
    cdp,start=touch_start_move(page,src)
    ph=rect(page.locator('.order-placeholder'))
    assert_rect_equal(ph,src_before,1.0)
    assert close(list_height(page),lh0,1.0),(list_height(page),lh0)
    during=row_state(page);source_id=src.get_attribute('data-id')
    src_state=[x for x in during if x['id']==source_id][0]
    assert src_state['position']=='absolute',src_state
    for x in during:
        if x['id']!=source_id:
            assert_rect_equal(x['rect'],others_before[x['id']],1.0)
    assert_flow_geometry(page,len(before))
    return cdp,start,src_before,lh0,before

def run_geometry(ctx,width,long_label=False):
    p=make_page(ctx);p.set_viewport_size({'width':width,'height':844})
    if long_label:
        long='Formuler une hypothèse extrêmement détaillée qui occupe volontairement plusieurs lignes afin de vérifier la géométrie exacte du cadre de dépôt pendant le déplacement tactile.'
        p.evaluate('(s)=>{window.__LAB__.fixtures.order.items[0].label=s;window.__LAB_TEST_SEEDS__=[17];document.querySelector("#variant").value="order-b";window.__LAB__.render()}',long)
        hs=p.locator('.order-b-card').evaluate_all('(xs)=>xs.map(x=>({id:x.dataset.id,h:x.getBoundingClientRect().height}))')
        sid=max(hs,key=lambda x:x['h'])['id'];src=p.locator(f'.order-b-card[data-id="{sid}"]');idx=p.locator('.order-b-card').evaluate_all('(xs,id)=>xs.findIndex(x=>x.dataset.id===id)',sid)
    else:
        idx=1;src=p.locator('.order-b-card').nth(idx)

    cdp,start,src_before,lh0,before=exact_activation_case(p,idx)
    ph0=rect(p.locator('.order-placeholder'))
    cards=p.locator('.order-b-card')
    first=rect(cards.nth(0))
    touch_move(cdp,start[0]+90,first['y']+4);p.wait_for_timeout(100)
    ph1=rect(p.locator('.order-placeholder'))
    assert abs(ph1['y']-ph0['y'])>4,(ph0,ph1)
    assert close(list_height(p),lh0,1.0)
    assert close(ph1['width'],src_before['width'],1.0) and close(ph1['height'],src_before['height'],1.0)
    assert_flow_geometry(p,len(before))
    touch_end(cdp);p.wait_for_timeout(80)
    assert p.locator('.order-placeholder').count()==0 and p.locator('.order-ghost').count()==0
    assert all(x['position']!='absolute' and x['style']=='' for x in row_state(p)),row_state(p)
    assert close(list_height(p),lh0,1.0)
    p.close()

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)

    # T1/T2/T3/T4 short-label geometry and flow accounting.
    run_geometry(ctx,390,False)

    # T5 pointer cancel restores original order/styles/height.
    p=make_page(ctx);before_ids=p.locator('.order-b-card').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');lh0=list_height(p)
    cdp,start,_,_,_=exact_activation_case(p,1);touch_cancel(cdp);p.wait_for_timeout(80)
    assert p.locator('.order-placeholder').count()==0 and p.locator('.order-ghost').count()==0
    assert p.locator('.order-b-card').evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')==before_ids
    assert all(x['position']!='absolute' and x['style']=='' for x in row_state(p)),row_state(p)
    assert close(list_height(p),lh0,1.0);p.close()

    # T6 multi-line source.
    run_geometry(ctx,390,True)

    # T7 narrow mobile width.
    run_geometry(ctx,320,True)

    # T8 non-drag overlay still zero-reflow and functional.
    p=make_page(ctx);cards=p.locator('.order-b-card');before=row_state(p);lh0=list_height(p);ids0=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)')
    cards.nth(1).click();p.wait_for_timeout(40);after=row_state(p)
    for a,b in zip(before,after):assert_rect_equal(a['rect'],b['rect'],1.0)
    assert close(list_height(p),lh0,1.0);slots=p.locator('.order-insert-slot');assert slots.count()==4
    slots.last.click();p.wait_for_timeout(30);ids1=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.id)');assert ids1!=ids0;p.close()

    # T9 repeated drags do not accumulate inline style residue.
    p=make_page(ctx)
    for source_i,target_i in [(0,2),(2,0),(1,0),(1,2)]:
        cards=p.locator('.order-b-card');src=cards.nth(source_i);dst=cards.nth(target_i);src.scroll_into_view_if_needed();dst.scroll_into_view_if_needed();page_before=list_height(p)
        sb=rect(src);db=rect(dst);sx,sy=sb['x']+sb['width']/2,sb['y']+sb['height']/2
        c=p.context.new_cdp_session(p);c.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'force':1,'id':1}]})
        c.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+40,'y':sy+9,'force':1,'id':1}]});p.wait_for_timeout(60)
        c.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+100,'y':db['y']+4,'force':1,'id':1}]});p.wait_for_timeout(60)
        assert close(list_height(p),page_before,1.0);c.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});p.wait_for_timeout(60)
        assert all(x['position']!='absolute' and x['style']=='' for x in row_state(p)),row_state(p)
    p.close();browser.close()

print('ORDER_B_V7_EXACT_GEOMETRY_AUDIT: PASS')
