from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).parent
raw=(ROOT/'index.html').read_text();html=raw.replace('<link rel="stylesheet" href="styles.css">','')
for n in ['lab_core.js','lab_baselines.js','lab_v6_helpers.js','lab_v6_flash.js','lab_v6_matching.js','lab_v6_order.js','lab_v6_classify.js','lab_v6_fill.js','lab_bootstrap.js']:html=html.replace(f'<script src="{n}"></script>','')
css=(ROOT/'styles.css').read_text();scripts=[(ROOT/n).read_text() for n in ['lab_core.js','lab_baselines.js','lab_v6_helpers.js','lab_v6_flash.js','lab_v6_matching.js','lab_v6_order.js','lab_v6_classify.js','lab_v6_fill.js','lab_bootstrap.js']]
def page(ctx):
 p=ctx.new_page();p.set_content(html);p.add_style_tag(content=css)
 for s in scripts:p.add_script_tag(content=s)
 return p
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 c=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
 p=page(c);p.select_option('#variant','order-b');p.screenshot(path=str(ROOT/'audit_order_before.png'),full_page=True);p.locator('.order-b-card').nth(1).click();p.screenshot(path=str(ROOT/'audit_order_selected.png'),full_page=True);p.close()
 p=page(c);p.select_option('#variant','matching-b');p.locator('.match-card').first.click();p.screenshot(path=str(ROOT/'audit_matching_selected.png'),full_page=True);p.locator('.pair-target').first.click();p.screenshot(path=str(ROOT/'audit_matching_placed.png'),full_page=True);p.close()
 p=page(c);p.select_option('#variant','classify-b');p.locator('.classify-card').first.click();p.screenshot(path=str(ROOT/'audit_classify_selected.png'),full_page=True);p.close()
 p=page(c);p.select_option('#variant','fill-b');p.locator('.token-chip').first.click();p.screenshot(path=str(ROOT/'audit_fill_selected.png'),full_page=True);p.close();b.close()
print('VISUAL_AUDIT_CAPTURE_V6: PASS')
