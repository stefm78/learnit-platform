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
            assert k not in forbidden,k; walk(v)
    elif isinstance(x,list):
        for v in x: walk(v)
walk(fixtures)
js='\n'.join((ROOT/n).read_text(encoding='utf-8') for n in ['lab_core.js','lab_baselines.js','lab_v6_helpers.js','lab_v6_flash.js','lab_v6_matching.js','lab_v7_order.js','lab_v6_classify.js','lab_v6_fill.js','lab_bootstrap.js'])
css=(ROOT/'styles.css').read_text(encoding='utf-8')
for marker in ['pointerdown','pointermove','pointerup','setPointerCapture','beginAttempt','shuffled','__LAB_TEST_SEEDS__']:
    assert marker in js
for bad in ['dragstart','ondragstart','.draggable','localStorage','sessionStorage','XMLHttpRequest','WebSocket','fetch(']:
    assert bad not in js
for fn in ['flashB','matchingB','orderB','classifyB','fillB']:
    assert f'function {fn}' in js
for marker in ['.manip-card[aria-pressed="true"]','.eligible-destination','.active-destination','.eligible-zone','.order-insert-overlay','.order-placeholder','.pair-slot.filled','.fill-slot.filled','prefers-reduced-motion:reduce']:
    assert marker in css
assert 'position:absolute;inset:0' in css
assert 'transform:translateY(-50%)' in css
assert '.move-panel' not in css
assert 'Déplacer «' not in js
assert "title.addEventListener('click'" in js
assert "slot.addEventListener('click'" in js and "bankTitle.addEventListener('click'" in js
assert 's.ghost.style.left=`${s.fixedLeft}px`' in js
assert "list.insertBefore(s.placeholder,other)" in js
assert "classList.add('eligible-destination')" in js
print('STATIC_LAB_V7_TESTS: PASS')

assert 'lab_v7_order.js' in html
assert 'lab_v6_order.js' not in html
order_js=(ROOT/'lab_v7_order.js').read_text(encoding='utf-8')
assert "row.style.position='absolute'" in order_js
assert "placeholder.style.width=" in order_js
assert "placeholder.style.height=" in order_js
assert "placeholder.style.minHeight=" in order_js
assert "placeholder.style.maxHeight=" in order_js
assert "restoreRowStyle(row,s)" in order_js
assert 'min-height:54px' not in css
assert '.order-placeholder{box-sizing:border-box;min-height:0!important' in css
print('STATIC_LAB_V7_GEOMETRY_INVARIANTS: PASS')
