#!/usr/bin/env python3
from pathlib import Path
import json, re
from support import load_runtime_core
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def add(code, ok, detail=''):
    checks.append({'code':code,'ok':bool(ok),'detail':detail})
def read(rel): return (ROOT/rel).read_text(encoding='utf-8')
manifest=json.loads(read('source_manifest.json'))
styles=[]; scripts=[]
for e in manifest.get('styles',[]): styles += e.get('paths',[])
for e in manifest.get('scripts',[]):
    if e.get('path'): scripts.append(e['path'])
    scripts += e.get('paths',[])
runtime=load_runtime_core()
gesture=read('src/scripts/core/runtime_parts/69_gesture_orchestrator.js')
composer=read('src/scripts/core/runtime_parts/68_library_navigation_shell_composer.js')
css_detail=read('src/styles/parts/64_library_chapter_comfort.css')
a11y=read('src/scripts/core/runtime_parts/71_accessibility_resilience_runtime.js')
template=read('src/template.html')
state=read('src/scripts/core/runtime_parts/10_content_store_and_state.js')
active_text='\n'.join(read(p) for p in styles+scripts if (ROOT/p).exists())
add('active-manifest-no-chapter-swipe-script', all('chapter_swipe' not in p and 'chapter-swipe' not in p for p in scripts), str(scripts))
add('active-manifest-no-chapter-snap-script', all('chapter_snap' not in p and 'chapter-snap' not in p for p in scripts), str(scripts))
add('active-manifest-no-chapter-snap-css', all('chapter_snap' not in p and 'chapter-snap' not in p and 'library_chapter_swipe' not in p for p in styles), str(styles))
add('runtime-no-body-position-fixed', "body.style.position = 'fixed'" not in runtime and 'body.style.position = "fixed"' not in runtime, 'no body fixed lock')
add('runtime-modal-lock-class-only', "classList.toggle('learnit-modal-scroll-lock'" in runtime and 'body.style.position' not in runtime, 'class-only scroll lock')
add('composer-layered-dialog-sheet', 'role="dialog"' in composer and 'aria-modal="true"' in composer and 'data-library-modal-shell="rc663"' in composer, 'layered detail sheet')
add('composer-content-exclusion-present', 'data-route-swipe-exclusion="content"' in composer, 'content zones excluded')
add('gesture-no-content-route-capture', 'isContentExclusion(event.target)' in gesture and 'beginRouteCarouselTransaction' in gesture and gesture.index('isContentExclusion(event.target)') < gesture.index('beginRouteCarouselTransaction'), 'content abort before route transaction')
detail_css_before_a11y=css_detail.split('/* RC613-RC623',1)[0]
add('detail-css-fixed-sheet-only', '.book-detail-shell.book-detail-sheet' in detail_css_before_a11y and 'position:fixed' in detail_css_before_a11y, 'fixed viewport sheet')
add('detail-css-sheet-body-scroll', '.book-detail-sheet .book-modal-body' in css_detail and 'touch-action:pan-y' in css_detail, 'sheet body owns native vertical scroll')
add('active-no-custom-chapter-runtime-patterns', 'installLibraryChapterSwipeNavigation=function(){return false;}' in gesture and 'ChapterCarouselModel' not in active_text and 'chapter-snap-shell' not in active_text, 'no nested runtime active')
add('android-scroll-contract-report', 'scrollOwnershipContract:true' in gesture and 'routeSwipeBoundaryContract:true' in gesture, 'runtime reports contracts')
route_runtime=read('src/scripts/core/runtime_parts/65_mobile_swipe_runtime.js')
all_runtime='\n'.join(read(path) for path in scripts if (ROOT/path).exists())
add('desktop-window-owner-markup', 'data-desktop-scroll-contract="rc688-window-owner"' in route_runtime and 'data-desktop-scroll-owner="window"' in route_runtime, 'fine-pointer document owner')
add('desktop-window-owner-css', '@media (hover:hover) and (pointer:fine)' in css_detail and 'overscroll-behavior-y:auto!important' in css_detail and '.route-panel.is-inactive[data-desktop-scroll-owner="window"]' in css_detail, 'wheel chain and inactive height')
add('desktop-no-wheel-interceptor', "addEventListener('wheel'" not in all_runtime and 'addEventListener("wheel"' not in all_runtime, 'native browser wheel path')

add('accessibility-skip-link-live-region', 'class="skip-link"' in template and 'href="#contenu"' in template and 'id="learnit-status"' in template and 'aria-live="polite"' in template, 'skip and live regions')
add('inactive-routes-inert', 'panel.inert=!active' in a11y and "panel.setAttribute('aria-hidden',active?'false':'true')" in a11y, 'inactive route focus is excluded')
add('keyboard-route-alternative', "Digit[1-4]" in a11y and "ArrowLeft" in a11y and "ArrowRight" in a11y and 'keyboardAlternative:true' in a11y, 'keyboard alternative to swipe')
add('keyboard-five-activities', all(token in a11y for token in ['data-qcm-choice','data-fill-slot','data-drag-match-right','data-drag-order-token','flashcard']), 'all five activity families covered')
add('focus-restoration-contract', 'captureFocus' in a11y and 'restoreFocus' in a11y and 'focusRouteHeading' in a11y, 'deterministic focus')
add('checkpoint-and-interruption-recovery', all(token in a11y for token in ['pagehide','visibilitychange','RESILIENCE_META_KEY']), 'checkpoint events')
add('versioned-state-recovery', 'STATE_SCHEMA_VERSION' in state and 'sanitizeSession' in state and 'state_migrated' in state and 'state_recovered' in state, 'state v3 migration and reset')
add('focus-reflow-reduced-motion-css', '.skip-link' in css_detail and ':focus-visible' in css_detail and '@media (prefers-reduced-motion:reduce)' in css_detail and '@media (forced-colors:active)' in css_detail, 'focus/reflow/motion contracts')

report={'schema':'learnit.rc688.accessibility_scroll_resilience_gate.v1','ok':all(c['ok'] for c in checks),'checks':checks,'summary':{'total':len(checks),'passed':sum(1 for c in checks if c['ok']),'failed':sum(1 for c in checks if not c['ok'])}}
(ROOT/'reports').mkdir(exist_ok=True)
(ROOT/'reports/contract_android_scroll_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
