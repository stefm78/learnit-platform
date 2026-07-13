#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from support import ROOT, active_script_paths

OUT=ROOT/'reports'/'contract_media_security_report.json'

def main()->int:
    checks=[]
    def add(code,ok,detail=''):checks.append({'code':code,'ok':bool(ok),'detail':detail})
    scripts=active_script_paths()
    model='src/learning/media_security_model.js'
    add('media-security-model-manifest-owned',model in scripts,str(scripts.index(model) if model in scripts else -1))
    runtime_first=min((i for i,p in enumerate(scripts) if p.startswith('src/scripts/core/runtime_parts/')),default=10**6)
    add('media-security-loads-before-runtime',model in scripts and scripts.index(model)<runtime_first,f'model={scripts.index(model) if model in scripts else -1} runtime={runtime_first}')
    source=(ROOT/model).read_text(encoding='utf-8')
    add('svg-allowlist-fail-closed',all(token in source for token in ['ALLOWED_TAGS','ALLOWED_ATTRS','unsafe-svg-content-removed','missing-svg-root']), '')
    add('raster-and-https-policy',all(token in source for token in ['data-image-type-or-encoding-rejected','https-required','credentials-forbidden','MAX_DATA_URL_CHARS']), '')
    render=(ROOT/'src/scripts/core/runtime_parts/20_session_answer_activity_rendering.js').read_text(encoding='utf-8')
    jacket=(ROOT/'src/scripts/core/runtime_parts/30_navigation_library_plan_models.js').read_text(encoding='utf-8')
    validator=(ROOT/'src/scripts/core/runtime_parts/10_content_store_and_state.js').read_text(encoding='utf-8')
    diagnostics=(ROOT/'src/scripts/core/runtime_parts/50_diagnostics_import_quality.js').read_text(encoding='utf-8')
    add('single-svg-sanitizer-owner',' safeSvg(' not in render and 'rc180SafeSvg' not in jacket and 'function sanitizeSvg' not in render and 'function sanitizeSvg' not in jacket and render.count('sanitizeSvg')>=2 and jacket.count('sanitizeSvg')>=2,'')
    add('all-media-renderers-use-security-model','LearnItMediaSecurityModel' in render and 'LearnItMediaSecurityModel' in jacket,'')
    add('import-validator-blocks-unsafe-media','auditAsset(asset)' in validator and 'asset média non sûr' in validator,'')
    add('diagnostics-explain-unsafe-media','auditAsset(a)' in diagnostics and 'Média non sûr détecté' in diagnostics,'')
    tool=(ROOT/'tools/validate_kit.py').read_text(encoding='utf-8')
    add('strict-validator-aligned','media_security_error' in tool and 'SAFE_RASTER_DATA' in tool and 'unsafe-remote-image' in tool,'')
    capabilities=json.loads((ROOT/'contract/learnit-capabilities.json').read_text(encoding='utf-8'))
    security=capabilities.get('media',{}).get('security',{})
    add('capability-contract-publishes-policy',security.get('status')=='stable' and security.get('tested') is True and security.get('remote_image_policy','').startswith('HTTPS'),security)
    skill=(ROOT/'authoring/SKILL_CURRENT.md').read_text(encoding='utf-8')
    add('authoring-skill-aligned',all(token in skill for token in ['allowlist et fail-closed','data:image/svg+xml','URL HTTPS uniquement','url(#identifiant-local)']),'')
    ok=all(row['ok'] for row in checks)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps({'schema':'learnit.rc688.media_security_contract.v1','ok':ok,'checks':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':ok,'passed':sum(row['ok'] for row in checks),'total':len(checks),'report':str(OUT.relative_to(ROOT))},ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
