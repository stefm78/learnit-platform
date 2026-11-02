"""Read-only post-Factory qualified-release binding (PR #511 candidate).

The existing ChatGPT-operated Factory process can invoke this AFTER its
canonical V6 release archive is durable. No timer, scheduler or parallel Factory.
This adapter does not install a hook, obtain Graph credentials or write remotely.
Runtime integration and live provider qualification remain distinct human gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

class Hold(RuntimeError):pass
SHA40=re.compile(r'^[0-9a-f]{40}$')
SHA256=re.compile(r'^sha256:[a-f0-9]{64}$')
RUN_ID=re.compile(r'^sha256:[a-f0-9]{64}$')


def validate_event(event: dict, archive_raw: bytes, commit: str, verified: dict) -> tuple[str,...]:
    """Bind the trigger to the canonical verifier output, never vice versa.

    `verified` MUST be the *fresh* result of canonical release verifier from an
    exact clean, independently approved checkout. Directly supplying a dict as
    proof is forbidden to production callers; CLI below runs the verifier.
    """
    if (not isinstance(event,dict) or event.get('type')!='FACTORY_V6_QUALIFIED_RELEASE_DURABLE' or
            event.get('distribution_authorized') is not False):
        raise Hold('UNTRUSTED_POST_PASS_EVENT')
    if not isinstance(commit,str) or not SHA40.fullmatch(commit) or event.get('canonical_verifier_commit')!=commit:
        raise Hold('VERIFIER_COMMIT_NOT_EXACT')
    actual='sha256:'+hashlib.sha256(archive_raw).hexdigest()
    if (event.get('release_sha256') != actual or verified.get('releaseSha256')!=actual or
            verified.get('releaseBytes')!=len(archive_raw) or
            verified.get('schema')!='learnit.atlas.qualified_release_set_result.v2' or
            verified.get('verdict')!='PASS_QUALIFIED_RELEASE_SET_V6_VERIFICATION_R1'):
        raise Hold('CANONICAL_RELEASE_NOT_EXACT_PASS')
    manifest=verified.get('manifest')
    if not isinstance(manifest,dict) or not isinstance(manifest.get('entries'),list) or not manifest['entries']:
        raise Hold('CANONICAL_RELEASE_MANIFEST_MISSING')
    canonical=[]
    for entry in manifest['entries']:
        run=(entry.get('factoryRun') or {}).get('runId') if isinstance(entry,dict) else None
        if not isinstance(run,str) or not RUN_ID.fullmatch(run):
            raise Hold('CANONICAL_RUN_ID_INVALID')
        canonical.append(run)
    claimed=event.get('factory_run_ids')
    if (not isinstance(claimed,list) or len(claimed)!=len(canonical) or
            not all(isinstance(x,str) and RUN_ID.fullmatch(x) for x in claimed) or
            sorted(claimed)!=sorted(canonical) or len(set(canonical))!=len(canonical)):
        raise Hold('FACTORY_RUN_EVENT_MISMATCH')
    return tuple(sorted(canonical))


def require_exact_checkout(checkout: pathlib.Path, commit: str) -> None:
    if not SHA40.fullmatch(commit):raise Hold('BAD_GIT_COMMIT')
    try:
        head=subprocess.run(['git','-C',str(checkout),'rev-parse','HEAD'],check=True,
                            capture_output=True,text=True,timeout=8).stdout.strip()
        dirty=subprocess.run(['git','-C',str(checkout),'status','--porcelain','--untracked-files=all'],
                             check=True,capture_output=True,text=True,timeout=8).stdout.strip()
    except (OSError,subprocess.SubprocessError) as e:
        raise Hold('GIT_CHECKOUT_UNVERIFIABLE') from e
    if head!=commit or dirty:raise Hold('GIT_COMMIT_OR_WORKTREE_STALE')
    if not (checkout/'authoring/factory/release_set_v6.py').is_file():
        raise Hold('CANONICAL_VERIFIER_ABSENT')
    if not (checkout/'tools/private_kit_intake_bridge.py').is_file():
        raise Hold('PR511_BRIDGE_ABSENT')


def prepare_read_only(archive: pathlib.Path, checkout: pathlib.Path,
                      commit: str, index_raw: bytes, event: dict) -> dict:
    """Use the REAL repository's canonical checker in a clean checkout.

    A production caller must supply index_raw just retrieved from live Graph,
    exact governance admission and a separately qualified execution context.
    This function does NOT confer any authority or perform writes.
    """
    require_exact_checkout(checkout,commit)
    archive_raw=archive.read_bytes()
    try:
        index=json.loads(index_raw.decode('utf-8'))
    except (UnicodeError,ValueError) as e:raise Hold('INDEX_BYTES_INVALID') from e
    # Use a dedicated Python process to reduce module-cache/source-shadowing risk.
    code=('import json,sys,pathlib; root=pathlib.Path(sys.argv[1]);'
          'sys.path.insert(0,str(root));sys.path.insert(0,str(root/"tools"));'
          'import private_kit_intake_bridge as b;'
          'arc=pathlib.Path(sys.argv[2]);raw=pathlib.Path(sys.argv[3]).read_bytes();'
          'verified=b.verified_release(arc,root);'
          'i=b.read_object(raw,"index");plan,members=b.prepare(arc,verified,i,existing_index_raw=raw);'
          'print(json.dumps({"verified":verified,"plan":plan,"members_sha":'
          '{k:b.digest(v) for k,v in members.items()}},separators=(",",":")))')
    import tempfile
    with tempfile.TemporaryDirectory(prefix='learnit_pr511_private_index_') as tmp:
        snapshot=pathlib.Path(tmp)/'PRIVATE_INDEX.json';snapshot.write_bytes(index_raw)
        try:
            output=subprocess.run([sys.executable,'-I','-c',code,str(checkout.resolve()),
                                   str(archive.resolve()),str(snapshot)],cwd=checkout,
                                   check=True,capture_output=True,text=True,timeout=120)
        except (OSError,subprocess.SubprocessError) as e:
            raise Hold('CANONICAL_VERIFICATION_OR_PLANNER_FAILED') from e
    try: result=json.loads(output.stdout)
    except (ValueError,UnicodeError) as e:raise Hold('VERIFIER_OUTPUT_NOT_JSON') from e
    run_ids=validate_event(event,archive_raw,commit,result['verified'])
    return {'status':'LOCAL_PLAN_ONLY_NOT_ADMITTED','authority':False,
            'release_sha256':'sha256:'+hashlib.sha256(archive_raw).hexdigest(),
            'factory_run_ids':run_ids,'plan':result['plan'],
            'members_sha256':result['members_sha'],
            'remote_mutation':False,'automatic_hook_installed':False}


def main(argv=None):
    p=argparse.ArgumentParser(description='Bind canonical Factory event to a private plan, read-only')
    p.add_argument('--release',required=True,type=pathlib.Path)
    p.add_argument('--checkout',required=True,type=pathlib.Path)
    p.add_argument('--commit',required=True)
    p.add_argument('--index-raw',required=True,type=pathlib.Path)
    p.add_argument('--event',required=True,type=pathlib.Path)
    a=p.parse_args(argv)
    try:
        res=prepare_read_only(a.release,a.checkout,a.commit,a.index_raw.read_bytes(),
                              json.loads(a.event.read_text('utf-8')))
        print(json.dumps(res,indent=2,ensure_ascii=False))
        return 0
    except (Hold,ValueError,OSError) as exc:
        print('HOLD: '+str(exc),file=sys.stderr)
        return 8

if __name__=='__main__':raise SystemExit(main())
