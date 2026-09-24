from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).parent
mods=['lab_core.js','lab_baselines.js','lab_v6_helpers.js','lab_v6_flash.js','lab_v6_matching.js','lab_v6_order.js','lab_v6_classify.js','lab_v6_fill.js','lab_bootstrap.js']
raw=(ROOT/'index.html').read_text();html=raw.replace('<link rel="stylesheet" href="styles.css">','')
for n in mods:html=html.replace(f'<script src="{n}"></script>','')
css=(ROOT/'styles.css').read_text();scripts=[(ROOT/n).read_text() for n in mods]
def page(ctx):
 p=ctx.new_page();p.set_content(html);p.add_style_tag(content=css)
 for s in scripts:p.add_script_tag(content=s)
 return p
def boxes(loc):return loc.evaluate_all('(xs)=>xs.map(x=>{const r=x.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})')
def same(a,b,t=.75):return len(a)==len(b) and all(abs(x-y)<=t for A,B in zip(a,b) for x,y in zip(A,B))
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox']);c=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
 # Order: no selection reflow, overlay outside row flow, bounded overlap, other card still clickable.
 p=page(c);p.select_option('#variant','order-b');cards=p.locator('.order-b-card');lst=p.locator('.order-b-list');before=boxes(cards);h=lst.bounding_box()['height'];cards.nth(1).click();after=boxes(cards);assert same(before,after) and abs(h-lst.bounding_box()['height'])<.75;assert p.locator('.order-b-list > .order-insert-slot').count()==0;assert p.locator('.order-insert-overlay').evaluate('e=>getComputedStyle(e).position')=='absolute';slots=p.locator('.order-insert-slot');assert slots.count()==4
 for i in range(4):
  sb=slots.nth(i).bounding_box();lb=slots.nth(i).locator('.order-insert-line').bounding_box();assert sb and lb and sb['height']>=24 and lb['height']<=4
  for cb in after:
   overlap=max(0,min(sb['y']+sb['height'],cb[1]+cb[3])-max(sb['y'],cb[1]));assert overlap/cb[3]<=.36
 tb=cards.first.bounding_box();cards.first.click(position={'x':tb['width']/2,'y':tb['height']/2});assert cards.first.get_attribute('aria-pressed')=='true' and cards.nth(1).get_attribute('aria-pressed')=='false';p.close()
 # Matching: selected vs eligible visually distinct, no stacked frame, state clears after destination.
 p=page(c);p.select_option('#variant','matching-b');card=p.locator('.match-card').first;targets=p.locator('.pair-target');card.click();p.wait_for_timeout(150);assert p.locator('.pair-target.eligible-destination').count()==3;ss=card.evaluate('e=>[getComputedStyle(e).backgroundColor,getComputedStyle(e).borderColor]');es=targets.first.evaluate('e=>[getComputedStyle(e).backgroundColor,getComputedStyle(e).borderColor]');assert ss!=es;targets.first.click();assert p.locator('.eligible-destination').count()==0;assert p.locator('.pair-row').first.evaluate('e=>getComputedStyle(e).borderTopStyle')=='none';assert p.locator('.pair-slot').first.evaluate('e=>getComputedStyle(e).borderTopStyle')=='none';p.close()
 # Classify: selection only; valid direct destination titles; no stale move panel.
 p=page(c);p.select_option('#variant','classify-b');cards=p.locator('.classify-card');buckets=p.locator('.bucket');state=lambda:p.locator('.classify-card').evaluate_all('(xs)=>Object.fromEntries(xs.map(x=>[x.dataset.cardId,x.closest(".bucket")?.dataset.dropZone||"source"]))');s=state();cards.first.click();cards.nth(1).click();assert state()==s;assert p.locator('.classify-destination.eligible-destination').count()==2;assert p.locator('.move-panel').count()==0 and 'Déplacer «' not in p.locator('#stage').inner_text();p.close()
 # Fill: empty slots only; placed token exposes bank + remaining empty slot; filled shell removed.
 p=page(c);p.select_option('#variant','fill-b');tokens=p.locator('.token-chip');slots=p.locator('.fill-slot');tokens.first.click();assert p.locator('.fill-slot.eligible-destination').count()==2 and p.locator('.fill-bank-title.eligible-destination').count()==0;slots.first.click();assert slots.first.evaluate('e=>getComputedStyle(e).borderTopStyle')=='none' and slots.first.get_attribute('role') is None;slots.first.locator('.token-chip').click();assert p.locator('.fill-bank-title.eligible-destination').count()==1 and p.locator('.fill-slot.eligible-destination').count()==1;p.close()
 # Common look-and-feel and DOM sanity.
 p=page(c);radii=[]
 for vid,sel in [('matching-b','.match-card'),('order-b','.order-b-card'),('classify-b','.classify-card'),('fill-b','.token-chip')]:
  p.select_option('#variant',vid);radii.append(p.locator(sel).first.evaluate('e=>getComputedStyle(e).borderRadius'));assert p.locator('button button').count()==0
 assert len(set(radii))==1 and '.eligible-destination' in css and '.active-destination' in css and ':focus-visible' in css;p.close();b.close()
print('PRODUCTION_AUDIT_V6: PASS')
