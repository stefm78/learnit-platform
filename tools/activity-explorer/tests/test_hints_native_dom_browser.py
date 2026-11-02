#!/usr/bin/env python3
"""Offline Chromium DOM test of exact canonical ES modules; no HTTP permitted/needed."""
from pathlib import Path
import base64, os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3]
def data_url(source):return 'data:text/javascript;base64,'+base64.b64encode(source.encode()).decode()
MEDIA=data_url((ROOT/'apps/learnit-next/src/ui/media.js').read_text())
PRESENTER=data_url((ROOT/'apps/learnit-next/src/ui/activity_presenters.js').read_text().replace("from './media.js'",f"from '{MEDIA}'"))
PROJECTION=data_url((ROOT/'apps/learnit-next/src/integration/atlas/activity_projection.js').read_text())

JS=r'''async ({presentationUrl,projectionUrl}) => {
  const {projectActivityPresentation} = await import(projectionUrl);
  const {renderActivityPresentation} = await import(presentationUrl);
  const inUI = (act,n=undefined) => projectActivityPresentation(act,{contract:'learnit.kit.v6',readOnlyHintPreview:true});
  const activity = hints => ({type:'qcm',prompt:'Question',hints,choices:[{choiceId:'a',label:'Oui'}],correctChoiceId:'a'});
  const assert = (v,m) => {if(!v)throw new Error(m)};
  const mount = p => {const node=renderActivityPresentation(p);document.body.replaceChildren(node);return node};
  const hintNodes=()=>[...document.querySelectorAll('[data-activity-hint-rank]')];
  const button=()=>document.querySelector('[data-activity-hint-next]');
  let count=0;
  for (let n=0;n<=3;n++) {
    const all=Array.from({length:n},(_,i)=>`hint-${i+1}`);
    const p=inUI(activity(all));
    assert(Object.isFrozen(p.hintPreview),'preview freeze');
    const learner=projectActivityPresentation(activity(all),{contract:'learnit.kit.v6'});
    assert(!Object.hasOwn(learner,'hintPreview'),'learner leak');
    const root=mount(p);
    assert(hintNodes().length===0,'pre-exposure');
    assert(Boolean(button())===(n>0),'zero/all button');
    for(let i=0;i<n;i++) {
      const b=button();assert(b.textContent===`Afficher un indice (${i+1}/${n})`,'label');
      assert(b.getAttribute('aria-label')===b.textContent,'aria label');
      b.click();count++;
      assert(hintNodes().length===i+1,'sequential count');
      assert(hintNodes().map(x=>x.textContent).join('|')===all.slice(0,i+1).join('|'),'authored order');
      if(button())assert(root.querySelector('[data-activity-hint-preview]').lastElementChild===button(),'button below last');
    }
    assert(!button(),'hide after last');
    if(n)assert(document.activeElement===hintNodes()[n-1],'focus preserved on last hint');
  }
  const xss='<script>window.HACKED=true</script>';
  mount(inUI(activity([xss])));button().click();
  assert(hintNodes()[0].textContent===xss,'xss literal');
  assert(!window.HACKED,'xss execution');
  assert(document.querySelectorAll('script').length===0,'xss DOM node');
  const old=hintNodes()[0];
  mount(inUI(activity(['new'])));
  assert(!document.body.contains(old)&&hintNodes().length===0,'cross activity reset');
  for(const bad of [[1],[''],[' a',' b',' c',' d']]) {
    let threw=false;
    try{inUI(activity(bad))}catch(e){threw=true};assert(threw,'invalid hints rejected');
  }
  let rejectedV5=false;
  try{projectActivityPresentation(activity(['h']),{contract:'learnit.kit.v5',readOnlyHintPreview:true})}catch(e){rejectedV5=true}
  assert(rejectedV5,'V5 preview rejected');
  return {status:'PASS',cases:count+7,checks:'native DOM and 0-3 progressive ordering, no pre-exposure, no learner projection leak, XSS text-only, stale reset, validation'};
}'''

def main():
 with sync_playwright() as p:
  args={'headless':True}
  if os.environ.get('CHROMIUM_EXECUTABLE'):args['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
  elif os.name=='nt':args['channel']='msedge'
  b=p.chromium.launch(**args)
  pg=b.new_page()
  pg.set_content('<main id="root"></main>')
  print(pg.evaluate(JS,{'presentationUrl':PRESENTER,'projectionUrl':PROJECTION}))
  b.close()
if __name__=='__main__':main()
