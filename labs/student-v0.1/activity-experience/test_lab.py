from pathlib import Path
import json,re
ROOT=Path(__file__).parent
html=(ROOT/'index.html').read_text(encoding='utf-8')
fixtures=json.loads(re.search(r'<script id="fixtures" type="application/json">\s*(.*?)\s*</script>',html,re.S).group(1))
variants=json.loads(re.search(r'<script id="variants" type="application/json">\s*(.*?)\s*</script>',html,re.S).group(1))
forbidden={'correctChoiceId','answers','acceptedResponses','matches','correctOrder','assignments'}
def walk(x,path=''):
    if isinstance(x,dict):
        for k,v in x.items():
            assert k not in forbidden, f'secret key {k} at {path}'
            walk(v,path+'/'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x): walk(v,f'{path}/{i}')
walk(fixtures)
assert set(fixtures)=={'lesson','flashcard','matching','order','classify','qcm','fill'}
ids=[v['id'] for v in variants]
assert ids==['lesson-a','flashcard-a','flashcard-b','matching-a','matching-b','order-a','order-b','classify-a','classify-b','qcm-a','fill-a','fill-b']
js='\n'.join((ROOT/n).read_text(encoding='utf-8') for n in ['lab_core.js','lab_baselines.js','lab_candidates_a.js','lab_candidates_b.js','lab_candidates_c.js','lab_bootstrap.js'])
css=(ROOT/'styles.css').read_text(encoding='utf-8')
for marker in ['pointerdown','pointermove','pointerup','setPointerCapture']:
    assert marker in js
for forbidden_js in ['dragstart','ondragstart','.draggable','localStorage','sessionStorage','XMLHttpRequest','WebSocket','fetch(']:
    assert forbidden_js not in js
for forbidden_authority in ['correctChoiceId','acceptedResponses','correctOrder']:
    assert forbidden_authority not in js
for fn in ['flashB','matchingB','orderB','classifyB','fillB']:
    assert f'function {fn}' in js
for marker in ['.flash-question-repeat','.pair-row','.order-b-card','.bucket-grid','.fill-slot','overflow-wrap:anywhere','prefers-reduced-motion:reduce']:
    assert marker in css
assert 'lab_v2_touch.js' not in html
print('STATIC_LAB_V3_TESTS: PASS')
