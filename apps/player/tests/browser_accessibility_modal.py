#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil

from support import ROOT

OUT = ROOT / 'reports' / 'browser_accessibility_modal_report.json'


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
            page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            page.set_default_timeout(8000)
            page.on('pageerror', lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console', lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type == 'error' else None)
            page.set_content(html, wait_until='domcontentloaded')
            page.wait_for_timeout(600)
            page.locator('nav.nav button[data-nav="library"]').click()
            page.wait_for_timeout(420)

            opener = page.locator('.book-row.is-selected button.book-open-main').first
            opener.focus()
            opener_key = page.evaluate('document.activeElement.dataset.a11yFocusKey')
            opener.click()
            page.wait_for_timeout(450)

            dialog = page.locator('.book-detail-sheet [role="dialog"][aria-modal="true"]')
            add('modal-dialog-open', dialog.count() == 1, str(dialog.count()))
            focused_inside = page.evaluate("!!document.querySelector('.book-detail-sheet [role=dialog]').contains(document.activeElement)")
            add('focus-enters-dialog', focused_inside, page.evaluate('document.activeElement && document.activeElement.dataset.action'))

            background = page.evaluate("""Array.from(document.querySelector('#app').children)
              .filter(el=>!el.classList.contains('book-detail-sheet'))
              .map(el=>({tag:el.tagName,inert:el.inert,aria:el.getAttribute('aria-hidden'),marked:el.dataset.modalBackgroundInert}))""")
            add('background-is-inert-and-hidden', len(background) >= 3 and all(row['inert'] and row['aria'] == 'true' and row['marked'] == 'true' for row in background), background)

            report = page.evaluate('window.__LEARNIT_TEST__.accessibilityReport()')
            add('runtime-accessibility-contract', report.get('modalOpen') is True and report.get('modalFocusTrap') is True and report.get('modalBackgroundInert') is True and report.get('modalEscape') is True and report.get('modalFocusReturn') is True, report)

            focusable = page.locator('.book-detail-sheet [role="dialog"] button:not([disabled]):not([tabindex="-1"])')
            first = focusable.first
            last = focusable.last
            first.focus()
            page.keyboard.press('Shift+Tab')
            add('shift-tab-wraps-to-last', last.evaluate('el=>document.activeElement===el'), page.evaluate('document.activeElement && document.activeElement.dataset.action'))
            last.focus()
            page.keyboard.press('Tab')
            add('tab-wraps-to-first', first.evaluate('el=>document.activeElement===el'), page.evaluate('document.activeElement && document.activeElement.dataset.action'))

            page.get_by_role('button', name='Plan').click()
            page.wait_for_timeout(320)
            add('plan-remains-modal', page.locator('.book-detail-sheet .book-modal.plan-mode[role="dialog"]').count() == 1)
            page.keyboard.press('Escape')
            page.wait_for_timeout(320)
            add('escape-closes-plan-level-only', page.locator('.book-detail-sheet .book-modal.plan-mode').count() == 0 and page.locator('.book-detail-sheet [role="dialog"]').count() == 1)
            page.keyboard.press('Escape')
            page.wait_for_timeout(420)
            add('escape-closes-detail', page.locator('.book-detail-sheet').count() == 0)
            restored_key = page.evaluate('document.activeElement && document.activeElement.dataset.a11yFocusKey')
            add('focus-returns-to-opener', restored_key == opener_key, {'expected': opener_key, 'actual': restored_key})
            add('background-restored', page.locator('#app > [data-modal-background-inert="true"]').count() == 0 and not page.locator('main#contenu').evaluate('el=>el.inert'))
            add('no-browser-errors', not errors, ' | '.join(errors[-10:]))
        finally:
            browser.close()

    ok = all(row['ok'] for row in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'schema': 'learnit.rc673.accessibility_modal_matrix.v1', 'ok': ok, 'checks': rows, 'errors': errors}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': ok, 'passed': sum(row['ok'] for row in rows), 'total': len(rows), 'report': str(OUT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
