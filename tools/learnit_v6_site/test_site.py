#!/usr/bin/env python3
"""Bounded byte-exact integrated site qualification. Not an exhaustive release test."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path,PurePosixPath

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--site',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--expected',type=Path,default=Path(__file__).with_name('expected_files.json'))
    a=p.parse_args();root=a.site.resolve(strict=True)
    mf=json.loads(a.manifest.read_text(encoding='utf-8'))
    expected=json.loads(a.expected.read_text(encoding='utf-8'))
    rows={r['path']:r for r in expected['files']}
    assert mf['base']==expected['base'] and len(rows)==52 and mf['known_files']==52
    files={p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file()}
    assert len(files)==52 and set(files)==set(rows), 'HOLD: site paths drift'
    for rel,path in files.items():
        assert not path.is_symlink() and path.resolve().is_relative_to(root),rel
        b=path.read_bytes()
        assert len(b)==rows[rel]['bytes'] and sha(b)==rows[rel]['sha256'],rel
    ver='92115133901b50509880c2e7ad9d76816f74e30443b5f52d1cf35d935dac953b'
    for rel in ('index.html','learnit-next.html','recovery/v3/index.html',
                'human-replay/c7f7587c9e5beb29a123e5139c17b6448229a0cc/index.html'):
        assert sha(files[rel].read_bytes())==ver,rel
    # Static relative asset references only. Dynamic JS fetches are outside this bounded checker.
    from html.parser import HTMLParser
    from urllib.parse import urlsplit,unquote
    class Parser(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            d=dict(attrs)
            for attr in ('src','href'):
                if d.get(attr):self.links.append(d[attr])
    checked=0;unknown=[]
    for rel,path in files.items():
        if not rel.endswith('.html'):continue
        parser=Parser();parser.feed(path.read_text(encoding='utf-8'))
        for link in parser.links:
            p=urlsplit(link)
            if p.scheme or p.netloc or not p.path or p.path.startswith(('data:','javascript:','#')):continue
            if p.path.startswith('/learnit-platform/'):
                target=PurePosixPath(p.path[len('/learnit-platform/'):])
            elif p.path.startswith('/'):
                unknown.append((rel,link));continue
            else: target=PurePosixPath(rel).parent.joinpath(unquote(p.path))
            parts=[]
            for segment in target.parts:
                if segment=='..':
                    if not parts:unknown.append((rel,link));break
                    parts.pop()
                elif segment not in ('.',''):parts.append(segment)
            else:
                key='/'.join(parts)
                candidates=[key,key+'/index.html' if key else 'index.html']
                if not any(k in files for k in candidates):unknown.append((rel,link))
                checked+=1
    print('PASS_SITE_BYTES=52/52')
    print('PASS_STATIC_LINKS='+str(checked-len(unknown))+'/'+str(checked))
    if unknown:
        print('HOLD_STATIC_LINKS='+repr(unknown[:15]));return 2
    # The old R15 deployment-evidence JSON is preserved byte-for-byte, but
    # it attests to the old stable V2 root, NOT the new V6 candidate root.
    legacy=json.loads(files['deployment-evidence.json'].read_text(encoding='utf-8'))
    assert legacy.get('learnerArtifactSha256')=='4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7', \
        'HOLD: legacy deployment evidence unexpectedly changed'
    assert legacy.get('learnerArtifactSha256') != ver, \
        'HOLD: legacy deployment evidence wrongly claimed V6 root'
    print('LEGACY_DEPLOYMENT_EVIDENCE=HISTORICAL_V2_ONLY__NOT_V6_RELEASE_PROOF')
    print('PASS_BYTE_CONTRACT_LOCAL_ONLY=YES')
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as e:print('HOLD_SITE_TEST='+str(e),file=sys.stderr);raise SystemExit(2)
