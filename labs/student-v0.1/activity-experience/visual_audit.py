from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).parent
raw=(ROOT/'index.html').read_text();html=raw.replace('<link rel="stylesheet" href="styles.css">','')
for n in ['lab_core.js','lab_baselines.js','lab_candidates.js','lab_bootstrap.js']:html=html.replace(f'<script src="{n}"></script>','')
css=(ROOT/'styles.css').read_text();scripts=[(ROOT/n).read_text() for n in ['lab_core.js','lab_baselines.js','lab_candidates.js','lab_bootstrap.js']]

def page(ctx):
 p=ctx.new_page();p.set_content(html);p.add_style_tag(content=css)
 for s in scripts:p.add_script_tag(content=s)
 return p
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 ctx=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
 # matching fully placed by tap
 p=page(ctx);p.select_option('#variant','matching-b');src=p.locator('.match-source');rows=p.locator('.pair-row')
 for i in range(3): src.locator('.match-card').first.click();rows.nth(i).locator('.pair-target').click()
 p.screenshot(path=str(ROOT/'audit_matching.png'),full_page=True);p.close()
 # order selected / intercalaires
 p=page(ctx);p.select_option('#variant','order-b');p.locator('.order-b-card').nth(1).click();p.screenshot(path=str(ROOT/'audit_order_selected.png'),full_page=True);p.close()
 # classify one selected and two placed
 p=page(ctx);p.select_option('#variant','classify-b');src=p.locator('.classify-source-cards');b=p.locator('.bucket')
 src.locator('.classify-card').first.click();b.nth(0).locator('.classify-destination').click();src.locator('.classify-card').first.click();b.nth(1).locator('.classify-destination').click();src.locator('.classify-card').first.click();p.screenshot(path=str(ROOT/'audit_classify.png'),full_page=True);p.close()
 # fill one placed one selected
 p=page(ctx);p.select_option('#variant','fill-b');bank=p.locator('.token-bank');slots=p.locator('.fill-slot');bank.locator('.token-chip').first.click();slots.nth(0).click();bank.locator('.token-chip').first.click();p.screenshot(path=str(ROOT/'audit_fill.png'),full_page=True);p.close();browser.close()
