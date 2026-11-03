#!/usr/bin/env python3
"""Real shared V6 media module: desktop/touch modal zoom and security, fully offline."""
from __future__ import annotations
import base64
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
MODULE = 'data:text/javascript;base64,' + base64.b64encode(
    (ROOT / 'apps/learnit-next/src/ui/media.js').read_bytes()
).decode('ascii')
STYLES = (ROOT / 'apps/learnit-next/src/styles.css').read_text(encoding='utf-8')
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><rect width="800" height="600" fill="white"/><path d="M0 0 L800 600" stroke="navy"/></svg>'
PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP8//8/AwMDEwMDAwMDAwAkBgMB/DXemwAAAABJRU5ErkJggg=='


def mount(page, media):
    return page.evaluate('''async ({uri,media}) => {
      const {renderEmbeddedMedia,validateSvg} = await import(uri);
      document.querySelector('#host').replaceChildren(renderEmbeddedMedia(media));
      return {svgValidatorRejectsScripts:!validateSvg('<svg onload="alert(1)"></svg>').ok};
    }''', {'uri': MODULE, 'media': media})


def run_desktop(browser):
    page = browser.new_page(viewport={'width': 1120, 'height': 750})
    failures = []
    page.on('pageerror', lambda error: failures.append(str(error)))
    page.set_content('<main id="host"></main>')
    page.add_style_tag(content=STYLES)
    media = {'assetId': 'diagram', 'format': 'svg', 'alt': 'Diagramme P–V', 'data': SVG,
             'caption': 'Pression volume', 'zoomable': True}
    assert mount(page, media)['svgValidatorRejectsScripts']
    assert page.locator('[data-activity-media-image="svg"]').count() == 1
    button = page.locator('[data-activity-media-open]')
    assert button.count() == 1
    button.click()
    dialog = page.locator('[data-activity-media-viewer]')
    assert dialog.count() == 1 and dialog.get_attribute('aria-modal') == 'true'
    assert page.locator('[data-activity-media-zoom-percent]').inner_text() == '100 %'
    page.wait_for_function('document.querySelector("[data-activity-media-viewer-image]").naturalWidth>0')
    page.locator('[data-activity-media-zoom-in]').click()
    assert float(dialog.get_attribute('data-zoom')) == 1.5
    for _ in range(12):
        page.locator('[data-activity-media-zoom-in]').click()
    assert float(dialog.get_attribute('data-zoom')) == 8, '8x limit'
    stage = page.locator('[data-activity-media-stage]')
    box = stage.bounding_box()
    cx, cy = box['x'] + box['width']/2, box['y'] + box['height']/2
    page.mouse.move(cx,cy)
    page.mouse.down()
    page.mouse.move(cx+2500,cy+2500,steps=4)
    page.mouse.up()
    bounds = page.evaluate('''() => {
      const st=document.querySelector('[data-activity-media-stage]');
      const im=document.querySelector('[data-activity-media-viewer-image]');
      const d=document.querySelector('[data-activity-media-viewer]');
      const fit=Math.min(st.clientWidth/im.naturalWidth,st.clientHeight/im.naturalHeight);
      return {x:Math.abs(+d.dataset.panX),y:Math.abs(+d.dataset.panY),
        mx:Math.max(0,(im.naturalWidth*fit*(+d.dataset.zoom)-st.clientWidth)/2),
        my:Math.max(0,(im.naturalHeight*fit*(+d.dataset.zoom)-st.clientHeight)/2)};
    }''')
    assert bounds['x'] <= bounds['mx']+1 and bounds['y'] <= bounds['my']+1, bounds
    page.locator('[data-activity-media-fit]').click()
    assert float(dialog.get_attribute('data-zoom')) == 1
    assert float(dialog.get_attribute('data-pan-x')) == float(dialog.get_attribute('data-pan-y')) == 0
    stage.hover()
    page.mouse.wheel(0,-90)
    assert float(dialog.get_attribute('data-zoom')) > 1, 'wheel zoom'
    page.keyboard.press('0')
    assert float(dialog.get_attribute('data-zoom')) == 1, 'keyboard reset'
    page.keyboard.press('+')
    assert float(dialog.get_attribute('data-zoom')) > 1, 'keyboard zoom'
    page.keyboard.press('Escape')
    assert dialog.count() == 0 and button.evaluate('(el)=>document.activeElement===el')
    assert page.evaluate('document.body.style.overflow') == ''
    # Native SVG sanitization, non-zoomable media and stale-dialog teardown.
    assert mount(page, {'assetId':'bad','format':'svg','alt':'Bad','data':'<svg onload="alert(1)"></svg>', 'zoomable':True})['svgValidatorRejectsScripts']
    assert page.locator('[data-activity-media-rejected]').count() == 1
    mount(page, {**media, 'zoomable':False})
    assert page.locator('[data-activity-media-open]').count() == 0
    mount(page, media)
    page.locator('[data-activity-media-open]').click()
    page.evaluate("document.querySelector('#host').replaceChildren()")
    page.wait_for_function("!document.querySelector('[data-activity-media-viewer]')")
    assert not failures, failures
    page.close()


def run_touch(browser):
    page = browser.new_page(viewport={'width': 375, 'height': 700}, has_touch=True, is_mobile=True)
    page.set_content('<main id="host"></main>')
    page.add_style_tag(content=STYLES)
    media = {'assetId':'raster','format':'png','alt':'Image tactile', 'data':PNG, 'zoomable':True}
    mount(page, media)
    page.locator('[data-activity-media-open]').tap()
    dialog = page.locator('[data-activity-media-viewer]')
    assert dialog.count() == 1
    page.wait_for_function('document.querySelector("[data-activity-media-viewer-image]").naturalWidth===2')
    stage = page.locator('[data-activity-media-stage]')
    box = stage.bounding_box()
    x, y = box['x']+box['width']/2, box['y']+box['height']/2
    # Synthetic pointer geometry exercises pinch calculation; native tap is tested above.
    page.evaluate('''({x,y}) => {
      const stage=document.querySelector('[data-activity-media-stage]');
      stage.setPointerCapture=()=>{};stage.hasPointerCapture=()=>false;
      for(const [type,id,dx,dy] of [
        ['pointerdown',1,-30,0],['pointerdown',2,30,0],
        ['pointermove',1,-80,0],['pointermove',2,80,0]]) {
        stage.dispatchEvent(new PointerEvent(type,{bubbles:true,pointerType:'touch',pointerId:id,
          clientX:x+dx,clientY:y+dy}));
      }
    }''', {'x':x,'y':y})
    assert float(dialog.get_attribute('data-zoom')) > 1.5, 'pinch zoom'
    page.locator('[data-activity-media-fit]').tap()
    assert dialog.get_attribute('data-zoom') == '1'
    page.locator('[data-activity-media-close]').tap()
    assert dialog.count() == 0
    page.close()


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True,
            executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
        run_desktop(browser)
        run_touch(browser)
        browser.close()
    print('PASS shared V6 image viewer: SVG and PNG, 800%, clamp, mouse wheel, drag, pinch, focus, keyboard, reset, teardown, sanitization')

if __name__ == '__main__':
    main()
