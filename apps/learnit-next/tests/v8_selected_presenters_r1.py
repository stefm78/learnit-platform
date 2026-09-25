from pathlib import Path
import contextlib,http.server,socket,socketserver,subprocess,threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
HOST='127.0.0.1'

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*_): pass
def free_port():
    with contextlib.closing(socket.socket()) as sock:
        sock.bind((HOST,0)); return sock.getsockname()[1]
def serve(port):
    handler=lambda *a,**k:Quiet(*a,directory=str(ROOT),**k)
    server=socketserver.TCPServer((HOST,port),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start(); return server
def rects(locator):
    return locator.evaluate_all('(xs)=>xs.map(x=>{const r=x.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})')
def same(a,b,t=.8):
    return len(a)==len(b) and all(abs(x-y)<=t for A,B in zip(a,b) for x,y in zip(A,B))
def touch(page,src,dst=None,cancel=False,keep=False):
    src.scroll_into_view_if_needed()
    if dst is not None: dst.scroll_into_view_if_needed()
    page.wait_for_timeout(30); a=src.bounding_box(); assert a
    sx,sy=a['x']+a['width']/2,a['y']+a['height']/2
    if dst is None: dx,dy=sx,sy+32
    else:
        b=dst.bounding_box(); assert b; dx,dy=b['x']+b['width']/2,b['y']+b['height']/2
    c=page.context.new_cdp_session(page)
    c.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy,'force':1,'id':1}]})
    for q in (.2,.4,.6,.8,1):
        c.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx+(dx-sx)*q,'y':sy+(dy-sy)*q,'force':1,'id':1}]});page.wait_for_timeout(20)
    if keep:return c
    c.send('Input.dispatchTouchEvent',{'type':'touchCancel' if cancel else 'touchEnd','touchPoints':[]});page.wait_for_timeout(40)
def render(page,kind):
    page.evaluate('(k)=>window.v8.render(k)',kind);page.wait_for_timeout(20)
    assert page.locator('[data-activity-media-placement-group="prompt"]').count()==1
    assert page.locator('[data-activity-media-placement-group="content"]').count()==1
    assert page.locator('[data-activity-media-placement="feedback"]').count()==0
    details=page.locator('details.activity-references');assert details.count()==1 and not details.evaluate('e=>e.open')
    link=details.locator('a');assert link.get_attribute('target')=='_blank' and link.get_attribute('rel')=='noopener noreferrer'
    assert 'Lien externe' in link.get_attribute('aria-label')
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
def shapes(page):
    render(page,'qcm');page.locator('[data-activity-choice="true"]').first.check();assert set(page.evaluate('window.v8.response("qcm")'))=={'choiceId'}
    render(page,'lesson');page.locator('[data-activity-continue="lesson"]').click();assert page.evaluate('window.v8.response("lesson")')=={'acknowledged':True}
    render(page,'flashcard');page.locator('.activity-flash-card').click();page.locator('[data-activity-continue="flashcard"]').click();assert page.evaluate('window.v8.response("flashcard")')=={'revealed':True}
    render(page,'matching')
    while page.locator('.activity-match-source>.activity-match-card').count():
        page.locator('.activity-match-source>.activity-match-card').first.click();page.locator('.activity-pair-target.eligible-destination').first.click()
    r=page.evaluate('window.v8.response("matching")');assert set(r)=={'associations'} and {x['leftItemId'] for x in r['associations']}=={'l1','l2','l3'}
    render(page,'order');r=page.evaluate('window.v8.response("order")');assert set(r)=={'orderedItemIds'} and set(r['orderedItemIds'])=={'o1','o2','o3','o4'}
    render(page,'classify')
    while page.locator('.activity-classify-source-cards>.activity-classify-card').count():
        page.locator('.activity-classify-source-cards>.activity-classify-card').first.click();page.locator('.activity-bucket-title.eligible-destination').first.click()
    r=page.evaluate('window.v8.response("classify")');assert set(r)=={'assignments'} and {x['itemId'] for x in r['assignments']}=={'c1','c2','c3'}
    render(page,'fill')
    while page.locator('.activity-token-bank>.activity-token-chip').count():
        page.locator('.activity-token-bank>.activity-token-chip').first.click();page.locator('.activity-fill-b-slot.eligible-destination').first.click()
    r=page.evaluate('window.v8.response("fill")');assert set(r)=={'s1','s2'} and set(r.values())=={'t1','t2'}
def geometry_keyboard(page):
    render(page,'qcm');radio=page.locator('[data-activity-choice="true"]').first;label=page.locator('.activity-qcm-label').first;rb,lb=radio.bounding_box(),label.bounding_box();assert rb and lb and abs(rb['y']-lb['y'])<=8
    radio.focus();page.keyboard.press('Space');assert radio.is_checked()
    for kind,card,target in [('matching','.activity-match-card','.activity-pair-target'),('classify','.activity-classify-card','.activity-bucket-title'),('fill','.activity-token-chip','.activity-fill-b-slot')]:
        render(page,kind);cards=page.locator(card);targets=page.locator(target);before=rects(cards)+rects(targets);cards.first.focus();page.keyboard.press('Enter');page.wait_for_timeout(20);assert same(before,rects(cards)+rects(targets));assert page.locator('.eligible-destination').count()>0
    render(page,'order');cards=page.locator('.activity-order-b-card');lst=page.locator('.activity-order-b-list');before=rects(cards);h=lst.evaluate('e=>e.getBoundingClientRect().height');cards.nth(1).focus();page.keyboard.press('Enter');page.wait_for_timeout(20);assert same(before,rects(cards));assert abs(h-lst.evaluate('e=>e.getBoundingClientRect().height'))<=.8;assert page.locator('.activity-order-insert-slot').count()==cards.count()+1
    render(page,'flashcard');card=page.locator('.activity-flash-card');card.focus();page.keyboard.press('Enter');assert card.get_attribute('aria-pressed')=='true'
def pointer_paths(page):
    render(page,'matching');touch(page,page.locator('.activity-match-card').first,page.locator('.activity-pair-row').first);assert page.locator('.activity-pair-slot .activity-match-card').count()==1
    render(page,'classify');touch(page,page.locator('.activity-classify-card').first,page.locator('.activity-bucket').first);assert page.locator('.activity-bucket .activity-classify-card').count()==1
    render(page,'fill');touch(page,page.locator('.activity-token-chip').first,page.locator('.activity-fill-b-slot').first);assert page.locator('.activity-fill-b-slot .activity-token-chip').count()==1
    render(page,'order');cards=page.locator('.activity-order-b-card');lst=page.locator('.activity-order-b-list');src=cards.nth(1).bounding_box();assert src;h=lst.evaluate('e=>e.getBoundingClientRect().height');client=touch(page,cards.nth(1),cards.last,keep=True);page.wait_for_timeout(30);assert page.locator('.activity-order-placeholder').count()==1 and page.locator('.activity-order-ghost').count()==1;ph=page.locator('.activity-order-placeholder').bounding_box();gh=page.locator('.activity-order-ghost').bounding_box();assert ph and gh;assert abs(ph['width']-src['width'])<=1 and abs(ph['height']-src['height'])<=1 and abs(gh['x']-src['x'])<=1 and abs(lst.evaluate('e=>e.getBoundingClientRect().height')-h)<=1;client.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(40);assert page.locator('.activity-order-placeholder').count()==0
    render(page,'order');cards=page.locator('.activity-order-b-card');lst=page.locator('.activity-order-b-list');ids=cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.orderItem)');h=lst.evaluate('e=>e.getBoundingClientRect().height');touch(page,cards.nth(1),cards.last,cancel=True);assert cards.evaluate_all('(xs)=>xs.map(x=>x.dataset.orderItem)')==ids and abs(lst.evaluate('e=>e.getBoundingClientRect().height')-h)<=1 and cards.nth(1).get_attribute('style') is None
def static_contracts():
    def blob(path):return subprocess.check_output(['git','hash-object',str(ROOT/path)],text=True).strip()
    exact={
      'contracts/learnit-kit-v5.schema.json':'15e708f9b57ea1b35ff50ad3b3854bd49d5cadc7',
      'authoring/v5/validate_kit.py':'0b93925eb22058878f13bc86554126846d2923d1',
      'contracts/learnit-kit-v4.schema.json':'e141bd5fafa75dda88a49e8a2094e4589bb4306e',
      'authoring/v4/validate_kit.py':'4ef561dfc1137aa436b4d8c8820db421ab6e1861',
      'apps/learnit-next/src/core/activity_semantics.js':'07c4595332419da1da0473a9715f09894620f6bd',
      'apps/learnit-next/src/ports/atlas_storage.js':'8def176ac7b96748a2384af97f23183016a4a4be',
      'apps/learnit-next/src/integration/atlas/activity_projection.js':'06025e76b6b60d1dc3bee3af43e661689da99d08'}
    for path,expected in exact.items():assert blob(path)==expected,(path,blob(path),expected)
    p=(ROOT/'apps/learnit-next/src/ui/activity_presenters.js').read_text();s=(ROOT/'apps/learnit-next/src/integration/atlas/session.js').read_text();pr=(ROOT/'apps/learnit-next/src/integration/atlas/activity_projection.js').read_text()
    for bad in ('dragstart','ondragstart','XMLHttpRequest','fetch('):assert bad not in p
    assert 'projectFeedbackMedia' in s and 'transitionAuthorized: true' in s and 'requestNextAtlasV5Hint' in s and 'reconstructAtlasHintPrefix' in s
    assert 'Relisez la règle demandée' not in s and 'Repérez la forme attendue' not in s and 'authoredV5Hints.length' in s
    assert "ref => !v5 || ref.placement !== 'feedback'" in pr
    selection=subprocess.check_output(['git','rev-parse','577aa6cde9dfc58663a4935545e48bf8953c902b:qualification/STUDENT_V01_ACTIVITY_LAB_SELECTION.md'],text=True).strip();assert selection=='947d0b20fbae356c47acd560fab584f9d4aa5199'
    assert subprocess.check_output(['git','merge-base','HEAD','1bd57ee49f39ebc993af6198d24ebd54cd0ddbab'],text=True).strip()=='1bd57ee49f39ebc993af6198d24ebd54cd0ddbab'
def main():
    static_contracts();port=free_port();server=serve(port);errors=[];external=[]
    try:
      with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for width in (390,320):
          c=browser.new_context(viewport={'width':width,'height':844},has_touch=True,is_mobile=True);page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http://','https://')) and HOST not in r.url else None);page.goto(f'http://{HOST}:{port}/apps/learnit-next/tests/v8_selected_presenters_harness.html',wait_until='networkidle')
          for kind in ('qcm','fill','lesson','flashcard','matching','order','classify'):render(page,kind)
          if width==390:shapes(page);geometry_keyboard(page);pointer_paths(page);page.emulate_media(reduced_motion='reduce');render(page,'flashcard');page.locator('.activity-flash-card').click();assert page.locator('.activity-flash-inner').evaluate('e=>getComputedStyle(e).transform')=='none'
          c.close()
        c=browser.new_context(viewport={'width':1280,'height':900});page=c.new_page();page.goto(f'http://{HOST}:{port}/apps/learnit-next/tests/v8_selected_presenters_harness.html',wait_until='networkidle');shapes(page);c.close();browser.close()
    finally:server.shutdown();server.server_close()
    assert not errors,errors;assert not external,external
    print('V8_SELECTED_PRESENTERS_BROWSER: PASS');print('V8_VIEWPORTS_DESKTOP_390_320: PASS');print('V8_KEYBOARD_POINTER_TOUCH: PASS');print('V8_ORDER_NUMERIC_GEOMETRY: PASS');print('V8_REDUCED_MOTION_OVERFLOW: PASS');print('REFERENCES_RUNTIME_FETCH: NONE')
if __name__=='__main__':main()
