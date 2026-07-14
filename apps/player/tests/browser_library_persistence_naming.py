#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path

from support import ROOT

OUT = ROOT / 'reports' / 'browser_library_persistence_naming_report.json'


def package(title: str = 'Titre source') -> dict:
    return {
        'kind': 'learnit-course-package',
        'schema_version': 'learnit.import.v1.1',
        'packageId': 'rc715-persistence-name-probe',
        'source': 'automated browser test',
        'assets': [],
        'generation_report': {},
        'courses': [{
            'schemaVersion': 'learnit-content-v2',
            'contentVersion': 'rc715-probe-v1',
            'title': title,
            'sequence': 'Persistance et nommage',
            'objectives': ['Vérifier la persistance'],
            'activities': [{
                'id': 'probe-q1',
                'type': 'qcm',
                'objective': 'Vérifier la persistance',
                'question': 'La bibliothèque doit-elle revenir après réouverture ?',
                'choices': ['Oui', 'Non'],
                'answer': 0,
                'why': 'La bibliothèque durable doit être restaurée.',
                'remediation': 'Relire le contrat de persistance.',
                'difficulty': 'medium',
                'learning_phase': 'validation',
                'assessment_role': 'validation',
                'common_errors': ['supposer que le stockage mémoire est durable']
            }]
        }]
    }


def main() -> int:
    from playwright.sync_api import sync_playwright

    rows: list[dict] = []
    errors: list[str] = []

    def add(code: str, ok: bool, detail='') -> None:
        rows.append({'code': code, 'ok': bool(ok), 'detail': detail})

    html = (ROOT / 'dist' / 'learnit.html').read_text(encoding='utf-8')
    chromium = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={'width': 1100, 'height': 900})
            page.set_default_timeout(10000)
            page.on('pageerror', lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console', lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type == 'error' else None)
            page.set_content(html, wait_until='domcontentloaded')
            page.wait_for_function('window.__LEARNIT_TEST__ && window.__LEARNIT_TEST__.runtime')

            result = page.evaluate('''async payload=>{
              const rt=window.__LEARNIT_TEST__.runtime;
              const store=rt.contentStore;
              // set_content uses an opaque origin in this harness. Inject a deterministic
              // successful durable backend result, while the separate contract test proves
              // that production uses IndexedDB. This exercises the full import/rename and
              // snapshot restoration paths without pretending to prove browser-origin life.
              store.scheduleDurableCommit=async function(reason='test'){
                this.libraryRevision=Math.max(this.libraryRevision+1,1);
                this.durableLastResult={ok:true,operation:'write',revision:this.libraryRevision,reason};
                return this.durableLastResult;
              };
              store.flushDurable=async function(){return this.durableLastResult||{ok:true,operation:'idle'};};
              store.imported=[];
              store.load();

              const text=JSON.stringify(payload);
              const key=store.importTitleOverrideKey('JSON collé',0,payload.courses[0]);
              store.setImportTitleOverride(key,'Nom choisi à l’import');
              store.setImportPlanTitleOverride('Plan choisi à l’import');
              const plan=store.previewImport(text,{});
              store.importDraft=text;
              store.importPreviewPlan=plan;
              store.importPreviewConfirmed=true;
              rt.go('tools');
              const importTitleInput=!!document.querySelector('.import-title-override');
              const importTitleValue=document.querySelector('.import-title-override')?.value||'';
              const importPlanTitleInput=!!document.querySelector('.import-plan-title-override');
              const importPlanTitleValue=document.querySelector('.import-plan-title-override')?.value||'';
              const applied=await store.applyImportDraftDurably(text,{plan});
              if(!applied.ok)return {applied,importTitleInput,importTitleValue,importPlanTitleInput,importPlanTitleValue};

              const id=applied.report.rows[0].courseId;
              store.setActiveCourse(id);
              rt.appState.alignWithContent();
              rt.appState.recordActivityProgress('probe-q1',{correct:true},store.content,{mode:'training'});
              rt.appState.save();
              const progressBefore=JSON.parse(JSON.stringify(rt.appState.courseProgress(id)));

              const renamed=await store.renameImportedCourse(id,'Nom modifié après import');
              const collectionKey='import:'+applied.report.packageId;
              const collectionRenamed=await store.renameImportedCollection(collectionKey,'Plan modifié après import');
              rt.appState.alignWithContent();
              const snapshot=store.durableSnapshot('browser-roundtrip');

              // Simulated fresh runtime state: erase current in-memory library and learner
              // state, then exercise the same snapshot restoration method used by IndexedDB.
              store.imported=[];
              store.lastAppliedImport=null;
              store.load();
              rt.appState.state=rt.appState.initial();
              rt.appState.save();
              const restored=store.restoreDurableSnapshot(snapshot,'automated-snapshot-roundtrip');
              rt.appState.state=rt.appState.load();
              rt.appState.ensureCourseState();
              rt.appState.alignWithContent();
              rt.libraryOverlayCourseId=id;
              rt.go('library');

              return {
                applied,renamed,collectionRenamed,collectionKey,restored,id,snapshot,importTitleInput,importTitleValue,importPlanTitleInput,importPlanTitleValue,
                title:store.courseById(id).title,
                ids:store.imported.map(c=>c.localCourseId),
                progressBefore,
                progressAfter:rt.appState.courseProgress(id),
                renameButton:!!document.querySelector('[data-action="library-rename-course"]'),
                collectionRenameButton:!!document.querySelector('[data-action="library-rename-collection"]'),
                collectionLabels:[...document.querySelectorAll('details.collection')].map(el=>({
                  key:el.dataset.collectionKey||'',
                  label:(el.querySelector('.collection-title strong')||{}).textContent||''
                })),
                report:store.persistenceReport(),
                uiText:document.body.innerText
              };
            }''', package())

            applied = result.get('applied', {})
            report = applied.get('report', {}) if isinstance(applied, dict) else {}
            imported_rows = report.get('rows', []) if isinstance(report, dict) else []
            add('import-transaction-succeeds', applied.get('ok') is True, result)
            add('import-title-editor-visible-before-apply', result.get('importTitleInput') is True and result.get('importTitleValue') == 'Nom choisi à l’import', {'visible': result.get('importTitleInput'), 'value': result.get('importTitleValue')})
            add('import-title-override-applied', bool(imported_rows) and imported_rows[0].get('title') == 'Nom choisi à l’import', imported_rows)
            add('import-plan-title-editor-visible-before-apply', result.get('importPlanTitleInput') is True and result.get('importPlanTitleValue') == 'Plan choisi à l’import', {'visible': result.get('importPlanTitleInput'), 'value': result.get('importPlanTitleValue')})
            add('import-plan-title-override-applied', bool(imported_rows) and imported_rows[0].get('collectionTitle') == 'Plan choisi à l’import' and report.get('collectionTitle') == 'Plan choisi à l’import', {'rows': imported_rows, 'reportTitle': report.get('collectionTitle')})
            add('post-import-rename-applied', result.get('renamed', {}).get('ok') is True and result.get('title') == 'Nom modifié après import', result.get('renamed'))
            add('post-import-plan-rename-applied', result.get('collectionRenamed', {}).get('ok') is True and any(g.get('key') == result.get('collectionKey') and g.get('label') == 'Plan modifié après import' for g in result.get('collectionLabels', [])), {'rename': result.get('collectionRenamed'), 'groups': result.get('collectionLabels')})
            add('stable-course-id-after-rename', result.get('id') in result.get('ids', []) and result.get('renamed', {}).get('courseId') == result.get('id'), {'id': result.get('id'), 'ids': result.get('ids')})
            add('durable-snapshot-carries-library', any(c.get('localCourseId') == result.get('id') and c.get('title') == 'Nom modifié après import' and c.get('importCollectionTitle') == 'Plan modifié après import' for c in result.get('snapshot', {}).get('imported', [])), result.get('snapshot', {}).get('reason'))
            add('durable-snapshot-carries-learner-state', bool(result.get('snapshot', {}).get('learnerStatePayload')), 'learnerStatePayload present')
            add('snapshot-roundtrip-restores-library', result.get('restored', {}).get('ok') is True and result.get('id') in result.get('ids', []), result.get('restored'))
            add('progress-preserved-through-rename-and-roundtrip', result.get('progressBefore') == result.get('progressAfter') and result.get('progressAfter', {}).get('probe-q1', {}).get('correct') is True, {'before': result.get('progressBefore'), 'after': result.get('progressAfter')})
            add('rename-action-visible-in-library', result.get('renameButton') is True, 'rename button present')
            add('plan-rename-action-visible-in-library', result.get('collectionRenameButton') is True, 'plan rename button present')
            add('renamed-plan-visible-in-library', 'Plan modifié après import' in result.get('uiText', ''), result.get('uiText', '')[:400])
            add('renamed-title-visible-in-library', 'Nom modifié après import' in result.get('uiText', ''), result.get('uiText', '')[:400])
            add('persistence-report-exposed', result.get('report', {}).get('schema') == 'learnit.library_persistence_report.rc715.v1', result.get('report'))
            add('no-unexpected-browser-errors', not errors, ' | '.join(errors[-10:]))
        finally:
            browser.close()

    ok = all(row['ok'] for row in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'schema': 'learnit.rc715.browser_library_persistence_naming.v1',
        'ok': ok,
        'scope': 'Deterministic import/rename/stable-id/durable-snapshot restoration. Real browser close/reopen remains the RC716 human gate because the automated environment blocks navigable origins.',
        'checks': rows,
        'errors': errors
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': ok, 'passed': sum(r['ok'] for r in rows), 'total': len(rows), 'report': str(OUT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
