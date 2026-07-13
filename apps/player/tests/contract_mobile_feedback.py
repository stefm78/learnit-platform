#!/usr/bin/env python3
from pathlib import Path
import json
from support import ROOT, load_runtime_core

checks=[]
def add(code,ok,detail=''): checks.append({'code':code,'ok':bool(ok),'detail':detail})
def read(rel): return (ROOT/rel).read_text(encoding='utf-8')
fill=read('src/activities/fill.js')
order=read('src/activities/order.js')
view=read('src/scripts/core/runtime_parts/63_route_view_fallbacks.js')
composer=read('src/scripts/core/runtime_parts/68_library_navigation_shell_composer.js')
routes=read('src/scripts/core/runtime_parts/66_route_view_composer.js')
runtime=load_runtime_core()
css='\n'.join(read(p) for p in [
  'src/styles/parts/10_layout_surfaces.css',
  'src/styles/parts/30_activities_session.css',
  'src/styles/parts/64_library_chapter_comfort.css'])
add('fill-capacity-from-answer', 'tokenCapacities' in fill and 'Math.max(capacity.get(token) || 0, needed)' in fill)
add('fill-repeated-token-visible', 'remainingCount' in fill and 'token-remaining' in runtime and 'effectiveTokens' in runtime)
add('order-upward-direction-threshold', 'direction < 0 ? 0.64' in order and 'computeIndexFromRects' in order)
add('session-compact-mode-banner', 'session-mode-banner compact' in view and 'Nouveau sujet · apprendre pas à pas' not in view)
add('session-objective-wrap', 'activity-objective' in view and '.activity-meta-row' in css and 'white-space:normal' in css)
add('library-layered-sheet', 'book-detail-sheet' in composer and 'aria-modal="true"' in composer and 'position:fixed' in css)
add('library-sheet-root-ownership', 'rc163 rc198 rc468-library-nav-shell' in composer and 'sheet-body-owner' in composer)
add('library-search-caret-preservation', 'librarySearchSelection' in runtime and 'setSelectionRange' in runtime and 'librarySearchTimer' in runtime)
add('library-search-clear-action', 'library-clear-search' in routes and "action==='library-clear-search'" in runtime)
add('mobile-nav-no-wrap', '.nav button{min-width:0;white-space:nowrap' in css and 'overflow-wrap:normal!important' in css)
add('cover-contrast', '.book-detail-sheet .cover-title{color:#fff!important' in css and 'rgba(6,18,52,.98)' in css)
add('plan-list-first-composer', 'data-chapter-nav-contract="list-first"' in composer and 'role="listbox"' in composer and 'chapter-reading-head' not in composer and 'library-prev-chapter' not in composer and 'library-next-chapter' not in composer)
add('plan-single-contextual-action', 'data-plan-action-owner="selected-chapter"' in composer and 'chapter-action-sticky' in composer)
add('plan-no-course-stepper', "const nav=!planMode&&courseNav" in composer)
add('plan-list-first-css', '.book-modal.plan-mode .book-modal-head' in css and '.plan-mode .chapter-action-sticky' in css and '.chapter[aria-selected="true"]' in css)
add('plan-dead-stepper-runtime-removed', 'renderLibraryV2ChapterNav' not in view and 'library-prev-chapter' not in runtime and 'library-next-chapter' not in runtime and 'library-chapter-top' not in runtime)
add('library-native-route-scroll-contract', 'data-library-scroll-contract="native-route-panel"' in routes and 'data-route-swipe-intent="observable"' in routes and 'data-route-swipe-exclusion="content"' not in routes and '.route-panel.route-view-library.is-active' in css and 'touch-action:pan-y pinch-zoom' in css)
add('library-sheet-native-scroll-contract', '.book-detail-sheet .book-modal-body' in css and 'overflow-y:scroll' in css and '.book-sheet-backdrop' in css and 'touch-action:none' in css)
add('library-sheet-scroll-state-preserved', 'librarySheetScrollTop' in runtime and 'saveLibrarySheetScroll' in runtime and 'restoreLibrarySheetScroll' in runtime)
report={'schema':'learnit.rc677.mobile_feedback_contract.v1','ok':all(c['ok'] for c in checks),'checks':checks,'summary':{'total':len(checks),'passed':sum(c['ok'] for c in checks)}}
(ROOT/'reports').mkdir(exist_ok=True)
(ROOT/'reports/contract_mobile_feedback_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
