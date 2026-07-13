#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from support import ROOT

OUT = ROOT / 'reports' / 'browser_media_security_report.json'


def main() -> int:
    from playwright.sync_api import sync_playwright
    rows=[]; errors=[]
    def add(code,ok,detail=''): rows.append({'code':code,'ok':bool(ok),'detail':detail})
    html=(ROOT/'dist'/'learnit.html').read_text(encoding='utf-8')
    chromium=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    malicious_svg='''<svg viewBox="0 0 20 20" onload="alert(1)"><script>alert(2)</script><foreignObject><iframe src="https://evil.invalid"></iframe></foreignObject><rect width="20" height="20" style="fill:red" fill="url(https://evil.invalid/x)"/><a href="javascript:alert(3)"><text>bad</text></a></svg>'''
    safe_svg='<svg viewBox="0 0 20 20"><title>Safe</title><rect x="1" y="1" width="18" height="18" rx="2" fill="#fff" stroke="#111" stroke-width="1"/></svg>'
    payload={'kind':'learnit-course-package','schema_version':'learnit.import.v1.1','packageId':'security-probe','source':'automated security probe','assets':[],'generation_report':{},'courses':[{'schemaVersion':'learnit-content-v2','contentVersion':'security-probe-v1','title':'Security probe','sequence':'Probe','objectives':['Tester un média'],'assets':[{'id':'bad','type':'image','format':'svg','source':'generated','alt':'Bad','pedagogical_role':'question_stimulus','data':malicious_svg}],'activities':[{'id':'q1','type':'qcm','objective':'Tester un média','question':'Question ?','choices':['Oui','Non'],'answer':0,'why':'Oui.','remediation':'Revoir.','media':[{'assetId':'bad','placement':'question'}]}]}]}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=chromium) if chromium else p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':900,'height':800}); page.set_default_timeout(8000)
            page.on('pageerror',lambda exc: errors.append(f'pageerror:{exc}'))
            page.on('console',lambda msg: errors.append(f'console:{msg.type}:{msg.text}') if msg.type=='error' else None)
            page.set_content(html,wait_until='domcontentloaded'); page.wait_for_timeout(400)
            schema=page.evaluate('()=>window.LearnItMediaSecurityModel&&window.LearnItMediaSecurityModel.schema')
            add('security-model-loaded',schema=='learnit.media_security.rc684.v1',schema)
            self_test=page.evaluate('()=>window.LearnItMediaSecurityModel.selfTest()')
            add('security-self-test',self_test.get('ok') is True,self_test)
            safe=page.evaluate('(svg)=>window.LearnItMediaSecurityModel.sanitizeSvg(svg,{alt:"Safe visual"})',safe_svg)
            add('safe-svg-accepted',safe.get('ok') is True and 'role="img"' in safe.get('svg','') and 'aria-label="Safe visual"' in safe.get('svg',''),safe)
            bad=page.evaluate('(svg)=>window.LearnItMediaSecurityModel.sanitizeSvg(svg)',malicious_svg)
            cleaned=bad.get('svg','').lower()
            add('unsafe-svg-fails-closed',bad.get('ok') is False and bad.get('changed') is True,bad)
            add('active-svg-content-removed',all(token not in cleaned for token in ['<script','foreignobject','<iframe','javascript:','onload=','style=','https://evil.invalid']),cleaned)
            urls=page.evaluate('''()=>({
              raster:LearnItMediaSecurityModel.safeImageSource('data:image/png;base64,iVBORw0KGgo='),
              svgData:LearnItMediaSecurityModel.safeImageSource('data:image/svg+xml;base64,PHN2Zz48L3N2Zz4='),
              http:LearnItMediaSecurityModel.safeImageSource('http://example.com/image.png'),
              credential:LearnItMediaSecurityModel.safeImageSource('https://user:pass@example.com/image.png'),
              https:LearnItMediaSecurityModel.safeImageSource('https://example.com/image.png')
            })''')
            add('raster-data-only',urls['raster']['ok'] and not urls['svgData']['ok'],urls)
            add('remote-https-only',not urls['http']['ok'] and not urls['credential']['ok'] and urls['https']['ok'],urls)
            plan=page.evaluate('payload=>window.__LEARNIT_TEST__.importPlan([JSON.stringify(payload)],{})',payload)
            detail=json.dumps(plan,ensure_ascii=False)
            add('unsafe-import-blocked',plan.get('ok') is False and 'asset média non sûr' in detail,plan)
            diagnostics=page.evaluate('payload=>window.__LEARNIT_TEST__.kitDiagnostics(JSON.stringify(payload))',payload)
            diag_text=json.dumps(diagnostics,ensure_ascii=False)
            add('unsafe-diagnostic-blocker','svg-unsafe' in diag_text or 'asset-source-unsafe' in diag_text,diagnostics)
            add('no-browser-errors',not errors,' | '.join(errors[-10:]))
        finally:
            browser.close()
    ok=all(row['ok'] for row in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({'schema':'learnit.rc684.media_security_matrix.v1','ok':ok,'checks':rows,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(row['ok'] for row in rows),'total':len(rows),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__':
    raise SystemExit(main())
