#!/usr/bin/env python3
"""Rebuild exactly 52 known LearnIT files from frozen Git refs (NOT deployable).

No API writes. The independent expected byte manifest is frozen in source.
Historical site reconstructed by historical.py from pinned commits.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path, PurePosixPath

PIN='c7f7587c9e5beb29a123e5139c17b6448229a0cc'
V6='92115133901b50509880c2e7ad9d76816f74e30443b5f52d1cf35d935dac953b'
V6_BYTES=627042
LOCAL_DIR=Path(__file__).resolve().parent
EXPECTED=LOCAL_DIR/'expected_files.json'
IDENTITY=LOCAL_DIR/'v6_identity_frozen.json'

def sha(b): return hashlib.sha256(b).hexdigest()
def run(*argv, cwd=None):
    p=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace')
    if p.returncode: raise RuntimeError('HOLD: command error '+str(argv[:4])+' '+p.stderr[-1300:]+' '+p.stdout[-500:])
    return p.stdout.strip()
def assert_safe(s):
    p=PurePosixPath(s)
    if not s or s.startswith('/') or '\\' in s or ':' in s or p.as_posix()!=s or any(x in ('.','..','') for x in s.split('/')):
        raise RuntimeError('HOLD: unsafe site path '+repr(s))
    return p

def assemble(repo: Path, output: Path, manifest_out: Path):
    repo=repo.resolve(strict=True)
    if run('git','rev-parse',PIN+'^{commit}',cwd=repo)!=PIN:
        raise RuntimeError('HOLD: missing frozen base commit')
    expected=json.loads(EXPECTED.read_text(encoding='utf-8'))
    if expected.get('base')!=PIN or len(expected.get('files',[]))!=52:
        raise RuntimeError('HOLD: invalid frozen 52-file manifest')
    entries={x['path']:x for x in expected['files']}
    if len(entries)!=52: raise RuntimeError('HOLD: duplicate expected site path')
    for p in entries: assert_safe(p)
    if sha(IDENTITY.read_bytes())!='be26dee5ce130478dd0c022679db2bb6c4d49408d910d199083b61f13a661003':
        raise RuntimeError('HOLD: frozen V6 identity fingerprint mismatch')
    if output.exists() or manifest_out.exists():
        raise RuntimeError('HOLD: create-only candidate output already exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    root=Path(tempfile.mkdtemp(prefix='learnit-r6-build-',dir=output.parent))
    clean=None
    try:
        pinned=root/'frozen-repo'
        run('git','-c','core.autocrlf=false','-c','core.eol=lf',
            'worktree','add','--detach',str(pinned),PIN,cwd=repo)
        try:
            stdout=run(sys.executable,'-B',str(LOCAL_DIR/'historical.py'),
                       '--skip-http','--repo',str(pinned),cwd=pinned)
            lines=dict(line.split('=',1) for line in stdout.splitlines() if '=' in line and '\n' not in line)
            if lines.get('LOCAL_RECONSTRUCTED_FILES')!='49' or 'SITE' not in lines:
                raise RuntimeError('HOLD: historical reconstruction incomplete: '+stdout[-1200:])
            old=Path(lines['SITE']).resolve(strict=True)
            scratch=old.parent
            if not scratch.name.startswith('learnit-s1-full-'):
                raise RuntimeError('HOLD: unexpected historical scratch path')
            clean=scratch
            site=root/'candidate'
            shutil.copytree(old,site)
            hist_files={p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()}
            if len(hist_files)!=49:
                raise RuntimeError('HOLD: historical tree contains unexpected file count')
            v6=site/'human-replay'/PIN/'index.html'
            blob=v6.read_bytes()
            if sha(blob)!=V6 or len(blob)!=V6_BYTES:
                raise RuntimeError('HOLD: V6 build mismatch')
            for rel,data in (
                (f'human-replay/{PIN}/identity.json',IDENTITY.read_bytes()),
                (f'human-replay/{PIN}/learnit-next.html',blob),
                ('index.html',blob),('learnit-next.html',blob),
                ('recovery/v3/index.html',blob),
            ):
                dst=site/assert_safe(rel)
                dst.parent.mkdir(parents=True,exist_ok=True)
                dst.write_bytes(data)
            files=sorted(p for p in site.rglob('*') if p.is_file())
            if len(files)!=52: raise RuntimeError('HOLD: candidate file count != 52')
            actual={}
            for path in files:
                if path.is_symlink() or not path.resolve().is_relative_to(site.resolve()):
                    raise RuntimeError('HOLD: escaped site path '+str(path))
                rel=path.relative_to(site).as_posix()
                b=path.read_bytes()
                actual[rel]={'path':rel,'bytes':len(b),'sha256':sha(b)}
            if set(actual)!=set(entries):
                raise RuntimeError('HOLD: site file inventory drift missing='+repr(sorted(set(entries)-set(actual)))+' extra='+repr(sorted(set(actual)-set(entries))))
            for rel,record in actual.items():
                exp=entries[rel]
                if record['sha256']!=exp['sha256'] or record['bytes']!=exp['bytes']:
                    raise RuntimeError('HOLD: candidate byte drift '+rel)
            data={'schema':'learnit.v6.integrated.site-manifest.r1',
                  'base':PIN,'known_files':52,'files':[actual[x] for x in sorted(actual)],
                  'history_exhaustive':False,'release_authorized':False,
                  'limitations':['49-file R15 reconstructed baseline + 2 observed V6 companions; two main root aliases replaced and 1 new recovery route',
                    'Does not prove historical ZIP/archive exhaustiveness or unknown externally consumed URLs',
                    'Same-origin recovery cannot survive complete Pages/domain outage']}
            output.parent.mkdir(parents=True,exist_ok=True)
            site.rename(output)
            manifest_out.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\n')
            print('PASS_INTEGRATED_BUILD=52/52')
            print('PASS_V6_SHA='+V6)
            print('SITE_MANIFEST_SHA256='+sha(manifest_out.read_bytes()))
            print('SITE='+str(output))
            print('MANIFEST='+str(manifest_out))
        finally:
            subprocess.run(['git','worktree','remove','--force',str(pinned)],cwd=repo,capture_output=True)
    finally:
        if clean and clean.exists():
            shutil.rmtree(clean,ignore_errors=True)
        if root.exists():
            shutil.rmtree(root,ignore_errors=True)

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--repo',type=Path,default=Path.cwd())
    a.add_argument('--output',type=Path,required=True)
    a.add_argument('--manifest',type=Path,required=True)
    x=a.parse_args()
    try: assemble(x.repo,x.output,x.manifest);return 0
    except Exception as ex:
        print('HOLD: '+type(ex).__name__+': '+str(ex),file=sys.stderr,flush=True)
        return 2
if __name__=='__main__':raise SystemExit(main())
