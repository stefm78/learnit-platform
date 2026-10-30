#!/usr/bin/env python3
"""Create-only local staging of a new CSP V6 root with exact 50-route preservation.

This does NOT deploy, edit a repository, contact APIs, or authorize publication.
The production CLI pins the existing site root's SHA-256 and 52-route count.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo

OLD_ROOT_SHA = '92115133901b50509880c2e7ad9d76816f74e30443b5f52d1cf35d935dac953b'
FROZEN_MANIFEST_GIT_BLOB = '4eaa95e026b112fc201a167d982831d96850a5e8'
PINNED_BASE = 'c7f7587c9e5beb29a123e5139c17b6448229a0cc'
ROOT_ALIASES = frozenset(('index.html', 'learnit-next.html'))

class StageError(RuntimeError):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git_blob(data: bytes) -> str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode('ascii')+data).hexdigest()

def utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_path(name: str) -> Path:
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or name.startswith('/'):
        raise StageError('unsafe manifest path')
    segments = name.split('/')
    if any(seg in ('', '.', '..') for seg in segments) or PurePosixPath(name).as_posix() != name:
        raise StageError('non-canonical manifest path')
    return Path(*segments)

def validate_csp_html(html: bytes):
    try:
        s = html.decode('utf-8')
    except UnicodeDecodeError as ex:
        raise StageError('candidate HTML is not UTF-8') from ex
    if s.count('<head>') != 1:
        raise StageError('head anchor ambiguous')
    p = re.findall(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">',s)
    script = re.findall(r'<script type="module">(.*?)</script>',s,re.S)
    styles = re.findall(r'<style>(.*?)</style>',s,re.S)
    if len(p)!=1 or len(script)!=1 or len(styles)!=1:
        raise StageError('exact CSP meta, one module script, one CSS style required')
    if not s.index('<head>') < s.index('http-equiv="Content-Security-Policy"') < s.index('<style>') < s.index('<script type="module">'):
        raise StageError('CSP is not applied before active resources')
    policy=p[0]
    expected_script="'sha256-"+base64.b64encode(hashlib.sha256(script[0].encode('utf-8')).digest()).decode('ascii')+"'"
    expected_style="'sha256-"+base64.b64encode(hashlib.sha256(styles[0].encode('utf-8')).digest()).decode('ascii')+"'"
    # A hash appearing in an unrelated directive is not authorization!
    directives={}
    for raw in policy.split(';'):
        fields=raw.strip().split()
        if not fields or fields[0] in directives:
            raise StageError('malformed or duplicate CSP directive')
        directives[fields[0]]=fields[1:]
    mandatory={
        'default-src': ["'none'"], 'script-src-attr': ["'none'"],
        'style-src-attr': ["'none'"], 'connect-src': ["'none'"],
        'object-src': ["'none'"], 'base-uri': ["'none'"],
        'form-action': ["'none'"], 'worker-src': ["'none'"],
        'frame-src': ["'none'"],
        'img-src': ["'self'", 'data:', 'blob:'],
        'font-src': ["'self'", 'data:']}
    if any(directives.get(k)!=v for k,v in mandatory.items()):
        raise StageError('CSP required directive differs')
    if directives.get('script-src') != [expected_script, 'blob:']:
        raise StageError('CSP module hash or blob loader policy differs')
    css=directives.get('style-src',[])
    if not (len(css)==2 and css[0]==expected_style and
            re.fullmatch(r"'sha256-[A-Za-z0-9+/]{43}='",css[1])):
        raise StageError('CSP stylesheet hash or runtime style hash differs')
    if set(directives) != set(mandatory)|{'script-src','style-src'}:
        raise StageError('undeclared CSP directive, manual review required')
    # Duplicate or alternate forms of CSP meta are treated as ambiguity, not silently ignored.
    if len(re.findall(r"""<meta\b[^>]*http-equiv\s*=\s*['"]?Content-Security-Policy""",s,re.I))!=1:
        raise StageError('duplicate or ambiguous CSP meta')
    if "'unsafe-inline'" in policy or "'unsafe-eval'" in policy or 'new Function(' in s or re.search(r'\beval\s*\(',script[0]):
        raise StageError('unsafe dynamic execution or broad exemption')
    if '__atlasCjsFactories' not in script[0]:
        raise StageError('static CommonJS factories absent')
    if not s.rstrip().endswith('</html>'):
        raise StageError('candidate HTML incomplete')
    return {'module_sha256':sha(script[0].encode('utf-8')),'style_sha256':sha(styles[0].encode('utf-8')),
            'csp_policy_sha256':sha(policy.encode('utf-8'))}

def verify_double_build(source_checkout: Path, source_commit: str, candidate_html: bytes) -> dict:
    """Mandatory proof that the candidate came from the exact clean source checkout."""
    repo = source_checkout.resolve(strict=True)
    if not re.fullmatch(r'[0-9a-f]{40}', source_commit):
        raise StageError('source commit must be exact lowercase SHA1')
    def git(*args):
        p = subprocess.run(['git',*args],cwd=repo,capture_output=True,text=True)
        if p.returncode:raise StageError('Git source verification failed: '+(p.stderr or '')[-180:])
        return p.stdout.strip()
    if git('rev-parse','HEAD')!=source_commit or git('status','--porcelain'):
        raise StageError('source checkout is not clean and pinned to exact SHA')
    builder=repo/'apps/learnit-next/build.py'
    if not builder.is_file():raise StageError('canonical builder unavailable in checkout')
    with tempfile.TemporaryDirectory(prefix='learnit-v6-source-build-') as scratch:
        paths=[Path(scratch)/'a.html',Path(scratch)/'b.html']
        for out in paths:
            proc=subprocess.run([sys.executable,'-B',str(builder),'--output',str(out)],cwd=repo,capture_output=True,text=True,timeout=120)
            if proc.returncode!=0 or not out.is_file():
                raise StageError('official source build failed: '+(proc.stderr or proc.stdout)[-240:])
        build_a,build_b=(p.read_bytes() for p in paths)
    if build_a!=build_b or build_a!=candidate_html:
        raise StageError('two canonical builds differ or candidate is not source-derived')
    if git('status','--porcelain'):
        raise StageError('canonical build unexpectedly modified source checkout')
    return {'source_commit':source_commit,'canonical_double_build_sha256':sha(build_a),'canonical_build_bytes':len(build_a)}

def commit_noreplace(staged:Path,output:Path):
    """Atomic no-overwrite publish of one directory; fail closed if unsupported."""
    if sys.platform.startswith('linux'):
        libc=ctypes.CDLL(None,use_errno=True)
        fn=getattr(libc,'renameat2',None)
        if fn is None:
            raise StageError('atomic RENAME_NOREPLACE unavailable')
        # Linux renameat2(AT_FDCWD, old, AT_FDCWD, new, RENAME_NOREPLACE)
        fn.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        fn.restype=ctypes.c_int
        if fn(-100,os.fsencode(staged),-100,os.fsencode(output),1)!=0:
            err=ctypes.get_errno()
            raise StageError('atomic create-only stage failed: '+os.strerror(err))
    elif os.name=='nt':
        # Windows rename into an existing directory fails, even when empty.
        if output.exists():raise StageError('create-only conflict')
        staged.rename(output)
    else:
        raise StageError('atomic no-replace directory rename unsupported')

def stage(baseline_site: Path, frozen_manifest: Path, candidate_html: Path,
          output: Path, candidate_sha256: str, source_checkout: Path, source_commit: str,
          *, baseline_sha256: str=OLD_ROOT_SHA, frozen_manifest_sha: str=FROZEN_MANIFEST_GIT_BLOB):
    start_ns=time.monotonic_ns()
    started=utc()
    site = baseline_site.resolve(strict=True)
    if not site.is_dir():raise StageError('baseline is not directory')
    output=output.absolute()
    if output.exists() or output.is_symlink():raise StageError('create-only output conflict')
    # Reject output inside source, including obvious nested paths.
    if output == site or site in output.parents or source_checkout.resolve(strict=True) in output.parents:
        raise StageError('output cannot be inside source or baseline')
    if not re.fullmatch(r'[0-9a-f]{64}',candidate_sha256):raise StageError('candidate digest must be exact lowercase SHA256')
    raw_manifest=frozen_manifest.read_bytes()
    if git_blob(raw_manifest)!=frozen_manifest_sha:
        raise StageError('frozen expected-files manifest Git blob changed')
    manifest=json.loads(raw_manifest)
    files=manifest.get('files')
    if manifest.get('schema')!='learnit.v6.site.expected-files.r1' or manifest.get('base')!=PINNED_BASE or not isinstance(files,list) or len(files)!=52:
        raise StageError('not the current frozen 52-file expected manifest')
    entries={}
    for entry in files:
        path=entry.get('path')
        safe_path(path)
        if path in entries or not isinstance(entry.get('bytes'),int) or entry['bytes']<0 or not re.fullmatch(r'[0-9a-f]{64}',entry.get('sha256','')):
            raise StageError('invalid or duplicate manifest entry')
        entries[path]=entry
    if len(entries)!=52 or not ROOT_ALIASES.issubset(entries):raise StageError('unexpected site inventory')
    for name in ROOT_ALIASES:
        if entries[name]['sha256']!=baseline_sha256:raise StageError('frozen baseline root identity drift')
    replay='human-replay/'+PINNED_BASE+'/index.html'
    if replay not in entries or entries[replay]['sha256']!=baseline_sha256:raise StageError('frozen replay route drift')
    actual={}
    for path in site.rglob('*'):
        if path.is_symlink():raise StageError('symlink in historic site')
        if path.is_dir():continue
        if not path.is_file():raise StageError('unexpected non-file site entry')
        key=path.relative_to(site).as_posix()
        if key not in entries:raise StageError('undeclared public route '+key)
        data=path.read_bytes(); actual[key]={'path':key,'bytes':len(data),'sha256':sha(data)}
    if set(actual)!=set(entries) or len(actual)!=52:raise StageError('site file inventory drift')
    for key in entries:
        if any(actual[key][k]!=entries[key][k] for k in ('bytes','sha256')):
            raise StageError('frozen site SHA256 differs: '+key)
    blob=candidate_html.read_bytes()
    if sha(blob)!=candidate_sha256:raise StageError('candidate SHA256 mismatch')
    if candidate_sha256==baseline_sha256:raise StageError('candidate is same as published baseline')
    csp=validate_csp_html(blob)
    source_evidence=verify_double_build(source_checkout,source_commit,blob)
    out_entries={key:dict(actual[key]) for key in actual}
    for name in ROOT_ALIASES:
        out_entries[name]={'path':name,'bytes':len(blob),'sha256':candidate_sha256}
    # Copy into a single temporary folder, then atomically rename the complete
    # bundle. Staging includes site and evidence, with no extra public route.
    output.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.v6-csp-stage-',dir=output.parent))
    try:
        staged_site=staging/'site'
        shutil.copytree(site,staged_site)
        for alias in ROOT_ALIASES:(staged_site/alias).write_bytes(blob)
        checked={}
        for fp in staged_site.rglob('*'):
            if fp.is_symlink():raise StageError('staging symlink not allowed')
            if not fp.is_file():continue
            key=fp.relative_to(staged_site).as_posix()
            data=fp.read_bytes()
            checked[key]={'path':key,'bytes':len(data),'sha256':sha(data)}
        if checked!=out_entries:raise StageError('staging mismatch or historic file changed')
        if {x for x in entries if entries[x]['sha256']!=checked[x]['sha256']} != ROOT_ALIASES:
            raise StageError('staging changed paths other than two roots')
        completed=utc()
        report={'schema':'learnit.v6.local-release-stage.v1','mode':'LOCAL_ONLY_NO_DEPLOY',
            'started_utc':started,'completed_utc':completed,
            'completed_paris':datetime.now(timezone.utc).astimezone(ZoneInfo('Europe/Paris')).isoformat(),
            'duration_monotonic_seconds':round((time.monotonic_ns()-start_ns)/1e9,6),
            'frozen_base':PINNED_BASE,'baseline_sha256':baseline_sha256,
            'frozen_manifest_git_blob':frozen_manifest_sha,
            'candidate_sha256':candidate_sha256,'candidate_bytes':len(blob),
            'source_provenance':source_evidence,
            'routes_checked':52,'routes_preserved_identically':50,
            'changed_routes':sorted(ROOT_ALIASES),'preserved_replay_route':replay,'csp':csp,
            'files':[out_entries[k] for k in sorted(out_entries)],
            'verdict':'PASS_LOCAL_STAGING_ONLY','remaining_gates':['real 64-file source build',
               'CSP browser tests on integrated V6', 'GitHub CI & scope review',
               'screen-reader/a11y assessment', 'separate human release approval']}
        (staging/'release-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        # Single destination atomic create: no partial published site directory.
        if output.exists():raise StageError('create-only conflict at commit')
        commit_noreplace(staging,output)
        return report
    except BaseException:
        shutil.rmtree(staging,ignore_errors=True)
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-site',required=True,type=Path)
    p.add_argument('--frozen-manifest',required=True,type=Path)
    p.add_argument('--candidate-html',required=True,type=Path)
    p.add_argument('--candidate-sha256',required=True)
    p.add_argument('--source-checkout',required=True,type=Path)
    p.add_argument('--source-commit',required=True)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    try:
        result=stage(args.baseline_site,args.frozen_manifest,args.candidate_html,args.output,args.candidate_sha256,args.source_checkout,args.source_commit)
        print(json.dumps({k:result[k] for k in ('verdict','routes_checked','routes_preserved_identically','candidate_sha256','duration_monotonic_seconds')},ensure_ascii=False))
    except (StageError,OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as e:
        print('HOLD_NO_OUTPUT:',e,flush=True)
        raise SystemExit(2)
if __name__=='__main__':main()
