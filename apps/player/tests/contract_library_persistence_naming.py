#!/usr/bin/env python3
from __future__ import annotations

import json
from support import ROOT, load_manifest, load_runtime_core

OUT = ROOT / 'reports' / 'contract_library_persistence_naming_report.json'


def main() -> int:
    manifest = load_manifest()
    runtime = load_runtime_core()
    composer = (ROOT / 'src/scripts/core/runtime_parts/68_library_navigation_shell_composer.js').read_text(encoding='utf-8')
    route_composer = (ROOT / 'src/scripts/core/runtime_parts/66_route_view_composer.js').read_text(encoding='utf-8')
    preview = (ROOT / 'src/scripts/core/runtime_parts/52_import_diagnostic_views.js').read_text(encoding='utf-8')
    dispatcher = (ROOT / 'src/scripts/core/runtime_parts/62_app_action_dispatcher.js').read_text(encoding='utf-8')
    store = (ROOT / 'src/scripts/core/runtime_parts/10_content_store_and_state.js').read_text(encoding='utf-8')
    rows = []

    def add(code: str, ok: bool, detail='') -> None:
        rows.append({'code': code, 'ok': bool(ok), 'detail': detail})

    runtime_paths = []
    for entry in manifest.get('scripts', []):
        if entry.get('bundle') == 'runtime_core':
            runtime_paths = entry.get('paths', [])
            break

    add('rc718-metadata', manifest.get('rc') == 'RC718' and 'RC718' in (ROOT / 'src/template.html').read_text(encoding='utf-8'))
    add('durable-owner-in-manifest', 'src/scripts/core/runtime_parts/05_durable_library_store.js' in runtime_paths)
    add('indexeddb-durable-store', all(token in runtime for token in ['indexedDB.open', 'DURABLE_LIBRARY_RECORD_ID', 'hydrateDurableLibrary', 'scheduleDurableCommit']))
    add('local-cache-plus-durable-report', all(token in runtime for token in ['memory-fallback', 'persistenceReport()', 'localCacheError']))
    add('stable-imported-course-identity', all(token in runtime for token in ['localCourseId', 'courseSlugFromTitle', 'renameImportedCourse']))
    add('import-title-editable', 'import-title-override' in preview and 'setImportTitleOverride' in runtime)
    add('post-import-rename-surface', 'library-rename-course' in composer and 'courseRenameInput' in composer)
    add('post-import-rename-actions', all(token in dispatcher for token in ["action==='library-rename-course'", "action==='library-rename-save'", "action==='library-rename-cancel'"]))
    add('import-plan-title-editable', 'import-plan-title-override' in preview and 'setImportPlanTitleOverride' in runtime)
    add('post-import-plan-rename-store', all(token in store for token in ['renameImportedCollection', 'importCollectionTitle', 'collection-rename']))
    add('post-import-plan-rename-surface', all(token in route_composer for token in ['library-rename-collection', 'collectionRenameInput', 'Nom du plan']))
    add('post-import-plan-rename-actions', all(token in dispatcher for token in ["action==='library-rename-collection'", "action==='library-rename-collection-save'", "action==='library-rename-collection-cancel'"]))
    add('durable-ui-import-path', 'applyImportDraftDurably' in dispatcher and 'bibliothèque enregistrée sur cet appareil' in dispatcher)
    add('progress-safe-id-contract', "function courseIdFromContent(content){const stable=" in runtime)

    ok = all(row['ok'] for row in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'schema': 'learnit.rc715.library_persistence_naming_contract.v1', 'ok': ok, 'checks': rows}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': ok, 'passed': sum(r['ok'] for r in rows), 'total': len(rows), 'report': str(OUT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
