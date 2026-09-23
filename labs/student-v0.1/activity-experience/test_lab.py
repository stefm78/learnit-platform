from pathlib import Path
import json,re
ROOT=Path(__file__).parent
fixtures=json.loads((ROOT/'fixtures.json').read_text(encoding='utf-8')) if (ROOT/'fixtures.json').exists() else json.loads(re.search(r'<script id="fixtures" type="application/json">(.*?)</script>',(ROOT/'index.html').read_text(encoding='utf-8'),re.S).group(1))
variants=json.loads((ROOT/'variants.json').read_text(encoding='utf-8')) if (ROOT/'variants.json').exists() else json.loads(re.search(r'<script id="variants" type="application/json">(.*?)</script>',(ROOT/'index.html').read_text(encoding='utf-8'),re.S).group(1))
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
counts={f:sum(v['family']==f for v in variants) for f in fixtures}
assert counts=={'lesson':1,'flashcard':2,'matching':2,'order':2,'classify':2,'qcm':1,'fill':1}
js=(ROOT/'lab_v2_touch.js').read_text(encoding='utf-8')
assert 'pointerdown' in js and 'pointermove' in js and 'pointerup' in js
assert 'setPointerCapture' in js
assert 'dragstart' not in js and '.draggable' not in js and "draggable:" not in js
for bad in ['correctChoiceId','acceptedResponses','correctOrder']:
    assert bad not in js
assert 'fetch(' not in js and 'XMLHttpRequest' not in js and 'WebSocket' not in js
assert 'eval(' not in js and 'localStorage' not in js and 'sessionStorage' not in js
# Discriminating implementation paths must not collapse A and B.
for name in ['flashB','matchingB','orderB','classifyB']:
    assert f'function {name}' in js
css=(ROOT/'styles.css').read_text(encoding='utf-8')
for marker in ['.flash-b-card','.matching-b-board','.order-b-list','.classify-b-board','touch-action:none','prefers-reduced-motion:reduce']:
    assert marker in css
html=(ROOT/'index.html').read_text(encoding='utf-8')
assert 'viewport' in html and 'ActivityResponse' in html
print('STATIC_LAB_V2_TESTS: PASS')
