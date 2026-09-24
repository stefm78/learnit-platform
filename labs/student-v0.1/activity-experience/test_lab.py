from pathlib import Path
import json,re
ROOT=Path(__file__).parent
html=(ROOT/'index.html').read_text(encoding='utf-8')
fixtures=json.loads(re.search(r'<script id="fixtures" type="application/json">\s*(.*?)\s*</script>',html,re.S).group(1))
variants=json.loads(re.search(r'<script id="variants" type="application/json">\s*(.*?)\s*</script>',html,re.S).group(1))
assert set(fixtures)=={'lesson','flashcard','matching','order','classify','qcm','fill'}
ids=[v['id'] for v in variants]
assert ids==['lesson-a','flashcard-a','flashcard-b','matching-a','matching-b','order-a','order-b','classify-a','classify-b','qcm-a','fill-a','fill-b']
forbidden={'correctChoiceId','answers','acceptedResponses','matches','correctOrder','assignments'}
def walk(x):
    if isinstance(x,dict):
        for k,v in x.items():
            assert k not in forbidden, k
            walk(v)
    elif isinstance(x,list):
        for v in x: walk(v)
walk(fixtures)
js='\n'.join((ROOT/n).read_text(encoding='utf-8') for n in ['lab_core.js','lab_baselines.js','lab_candidates.js','lab_bootstrap.js'])
css=(ROOT/'styles.css').read_text(encoding='utf-8')
for marker in ['pointerdown','pointermove','pointerup','setPointerCapture','beginAttempt','shuffled','__LAB_TEST_SEEDS__']:
    assert marker in js
for bad in ['dragstart','ondragstart','.draggable','localStorage','sessionStorage','XMLHttpRequest','WebSocket','fetch(']:
    assert bad not in js
for fn in ['flashB','matchingB','orderB','classifyB','fillB']:
    assert f'function {fn}' in js
for marker in ['.order-ghost','.drag-origin','.move-panel','.fill-slot.filled','.flash-answer','text-align:left','overflow-wrap:anywhere','prefers-reduced-motion:reduce']:
    assert marker in css
# Buckets/slots are not mutation buttons in V4 candidates.
assert "bucket.addEventListener('click'" not in js
assert "slot.onclick" not in js
print('STATIC_LAB_V4_TESTS: PASS')
