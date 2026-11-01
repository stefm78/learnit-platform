#!/usr/bin/env python3
"""Real native renderer smoke. Requires playwright+chromium; never substitutes mocks."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[3]
ID = lambda n: f'id-{n}'
svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><rect width="100" height="80" fill="white"/><circle cx="35" cy="40" r="22" fill="blue"/></svg>'
KIT = {
 'contract':'learnit.kit.v6','title':'V6 integration regression sample',
 'assets':[{'assetId':ID('media'), 'type':'image','format':'svg','alt':'SVG de test', 'data':svg, 'caption':'Cercle sur fond blanc', 'pedagogicalRole':'concept_visual'}],
 'courses':[{'courseLineageId':ID('course'),'title':'Cours avec catégories et images', 'activities':[
  {'activityLineageId':ID('qcm'),'type':'qcm','learningPhase':'validation','assessmentRole':'validation',
   'prompt':'Question et image SVG ?', 'choices':[{'choiceId':ID('one'),'label':'Oui'},{'choiceId':ID('two'),'label':'Non'}],
   'correctChoiceId':ID('one'), 'media':[{'assetId':ID('media'),'placement':'prompt','zoomable':True}]},
  {'activityLineageId':ID('classify'),'type':'classify','learningPhase':'application','assessmentRole':'practice','prompt':'Classer le contenu',
   'buckets':[{'bucketId':ID('bucket-1'),'label':'Catégorie A'}, {'bucketId':ID('bucket-2'),'label':'Catégorie B'}],
   'items':[{'itemId':ID('item'),'label':'Élément'}], 'assignments':[{'itemId':ID('item'),'bucketId':ID('bucket-1')}]},
  {'activityLineageId':ID('fill'),'type':'fill','learningPhase':'application','assessmentRole':'practice',
   'prompt':'Complétez', 'segments':[{'text':'La réponse est '},{'slotId':ID('slot')}],
   'tokens':[{'tokenId':ID('token'),'label':'Oui', 'maxUses':1}], 'answers':[{'slotId':ID('slot'),'tokenId':ID('token')}]},
  {'activityLineageId':ID('order'),'type':'order','learningPhase':'application','assessmentRole':'practice',
   'prompt':'Ordonner', 'items':[{'itemId':ID('first'),'label':'Première'},{'itemId':ID('second'),'label':'Deuxième'}],
   'correctOrder':[ID('first'),ID('second')]},
 ]}]
}


def main():
  with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width': 1440, 'height': 940})
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    # Direct static-file fulfillment: runs real unchanged ES modules from repo,
    # without network access or a remote service and under the actual page CSP.
    def route(req):
      name=urlsplit(req.request.url).path.lstrip('/')
      target=REPO/name
      if target.is_file() and target.resolve().is_relative_to(REPO):
        mime={'.html':'text/html', '.js':'text/javascript', '.css':'text/css'}.get(target.suffix,'application/octet-stream')
        req.fulfill(status=200, body=target.read_bytes(), content_type=mime)
      else: req.fulfill(status=404,body='Not found')
    page.route('https://explorer.test/**', route)
    page.goto('https://explorer.test/tools/activity-explorer/index.html')
    page.locator('#kit-file').set_input_files({'name':'fixture.json','mimeType':'application/json','buffer':json.dumps(KIT).encode()})
    page.locator('#activity-progress').get_by_text('1 sur 4').wait_for()
    assert page.locator('[data-activity-presentation="qcm"]').count()==1
    assert page.locator('img[data-activity-media-image="svg"]').count()==1
    img=page.locator('img[data-activity-media-image="svg"]').first
    page.wait_for_function('(img) => img.complete && img.naturalWidth > 0',arg=img.element_handle())
    assert page.locator('.activity-media-zoom summary').count()==1
    assert page.locator('#activity-meta').inner_text().count('Validation') >= 1
    page.locator('#next-top').click()
    assert page.locator('[data-activity-presentation="classify"]').count()==1
    assert 'Classement' in page.locator('#activity-meta').inner_text()
    assert 'Application' in page.locator('#activity-meta').inner_text()
    assert 'Entraînement' in page.locator('#activity-meta').inner_text()
    page.locator('#next-bottom').click()
    assert page.locator('[data-activity-presentation="fill"]').count()==1
    page.locator('#next-bottom').click()
    assert page.locator('[data-activity-presentation="order"]').count()==1
    page.locator('#prev-top').click()
    assert page.locator('[data-activity-presentation="fill"]').count()==1
    page.locator('#activity-type').select_option('qcm')
    assert page.locator('.activity-row').count()==1
    assert page.locator('[data-activity-presentation="qcm"]').count()==1
    assert not errors, errors
    browser.close()
  print('PASS native canonical modules + SVG naturalWidth + zoom + categories + navigation + filters')

if __name__=='__main__': main()
