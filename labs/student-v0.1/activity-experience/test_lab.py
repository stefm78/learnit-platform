from pathlib import Path
import json,re,hashlib
ROOT=Path(__file__).parent
fixtures=json.loads((ROOT/'fixtures.json').read_text(encoding='utf-8'))
variants=json.loads((ROOT/'variants.json').read_text(encoding='utf-8'))
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
js=(ROOT/'lab.js').read_text(encoding='utf-8')
for bad in ['correctChoiceId','acceptedResponses','correctOrder']:
    assert bad not in js
assert 'fetch(' not in js and 'XMLHttpRequest' not in js and 'WebSocket' not in js
assert 'eval(' not in js and 'localStorage' not in js and 'sessionStorage' not in js
html=(ROOT/'index.html').read_text(encoding='utf-8')
assert 'viewport' in html and 'ActivityResponse' in html
css=(ROOT/'styles.css').read_text(encoding='utf-8')
assert '@media(max-width:390px)' in css and 'prefers-reduced-motion:reduce' in css
print('STATIC_LAB_TESTS: PASS')

