#!/usr/bin/env python3
"""Native canonical UI hint preview qualification; static local ES modules, no network."""
from __future__ import annotations
import json, os
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[3]
INJECTION = '<script>window.XSS_HIT = true</script>'

def qcm(n, hints):
    return {
      'activityLineageId':f'hints-{n}', 'activityRevisionId':f'revision-{n}',
      'type':'qcm','learningPhase':'application','assessmentRole':'practice',
      'prompt':f'Indice {n} ?', 'hints':hints,
      'choices':[{'choiceId':f'{n}-yes','label':'Oui'}, {'choiceId':f'{n}-no','label':'Non'}],
      'correctChoiceId':f'{n}-yes',
    }

KIT={'contract':'learnit.kit.v6','title':'Synthetic private-free hint preview smoke',
     'courses':[{'courseLineageId':'course-hints','title':'Test hints',
     'activities':[qcm(0,[]),qcm(1,['premier']),qcm(2,['un','deux']),qcm(3,['alpha','beta',INJECTION])]}]}

def main():
    with sync_playwright() as p:
        options={'headless':True}
        binary=os.environ.get('CHROMIUM_EXECUTABLE')
        if binary: options['executable_path']=binary
        elif os.name=='nt': options['channel']='msedge'
        browser=p.chromium.launch(**options)
        page=browser.new_page(viewport={'width':1280,'height':800})
        failures=[]
        page.on('pageerror',lambda err:failures.append(str(err)))
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        http=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(REPO)))
        Thread(target=http.serve_forever,daemon=True).start()
        page.goto(f'http://127.0.0.1:{http.server_port}/tools/activity-explorer/index.html')
        page.locator('#kit-file').set_input_files({'name':'synthetic.json','mimeType':'application/json','buffer':json.dumps(KIT).encode()})
        page.locator('#activity-progress').get_by_text('1 sur 4').wait_for()
        def advance():page.locator('#next-top').click()
        def hints():return page.locator('[data-activity-hint-rank]')
        def button():return page.locator('[data-activity-hint-next]')
        assert hints().count()==0 and button().count()==0
        advance(); assert button().count()==1 and button().inner_text()=='Afficher un indice (1/1)'
        button().focus();page.keyboard.press('Enter');assert hints().count()==1 and hints().first.inner_text()=='premier'
        assert button().count()==0
        advance();assert button().count()==1 and button().inner_text()=='Afficher un indice (1/2)'
        button().focus();page.keyboard.press('Space');assert [x.inner_text() for x in hints().all()]==['un']
        assert button().inner_text()=='Afficher un indice (2/2)'
        assert button().bounding_box()['y']>hints().last.bounding_box()['y']
        button().click();assert [x.inner_text() for x in hints().all()]==['un','deux'] and button().count()==0
        page.locator('#reset-preview').click();assert hints().count()==0 and button().inner_text()=='Afficher un indice (1/2)'
        advance();assert hints().count()==0 and button().inner_text()=='Afficher un indice (1/3)'
        assert page.locator('[data-activity-hint-preview]').count()==1
        assert page.locator('[data-activity-hint-preview] script').count()==0
        for n in (1,2,3):
            assert button().inner_text()==f'Afficher un indice ({n}/3)'
            button().click()
            assert hints().count()==n
        assert hints().last.inner_text()==INJECTION
        assert page.evaluate('window.XSS_HIT === true') is False
        assert button().count()==0
        page.locator('#prev-top').click()
        assert hints().count()==0 and button().inner_text()=='Afficher un indice (1/2)'
        page.locator('#activity-type').select_option('qcm')
        assert button().inner_text()=='Afficher un indice (1/2)'
        page.locator('#activity-search').fill('Indice 0')
        assert button().count()==0 and hints().count()==0
        assert not failures,failures
        browser.close()
        http.shutdown();http.server_close()
        print('PASS canonical Chromium: 0/1/2/3 progressive, keyboard, bottom button, reset/navigation/filter, text-only XSS, no errors')

if __name__=='__main__':main()
