#!/usr/bin/env python3
"""LearnIT V6 private-library admission PLANNER (no Graph/GitHub writes).

Trust boundary: rely on the already-pinned canonical
`authoring.factory.release_set_v6.verify_release_archive` verifier, never on
verdict strings from untrusted manifests alone. Output is a preflight plan,
NOT a permission, proof of live OneDrive state or completed registration.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib
import json
import os
import subprocess
import re
import stat
import sys
import zipfile
from pathlib import Path
from urllib.parse import quote

SCHEMA = 'learnit.private-kit-intake-plan.v1'
RELEASE_PASS = 'PASS_QUALIFIED_RELEASE_SET_V6_VERIFICATION_R1'
VERIFIED_SCHEMA = 'learnit.atlas.qualified_release_set.v2'
UUID = re.compile(r'^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$')
SHA = re.compile(r'^sha256:[0-9a-f]{64}$')
FILENAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,139}\.json$')

class Hold(ValueError):
    """Fail closed; no mutation has been initiated."""


def digest(raw: bytes) -> str:
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def _no_duplicate_json_pairs(pairs):
    d={}
    for key,value in pairs:
        if key in d:raise Hold('JSON_DUPLICATE_KEY:'+str(key))
        d[key]=value
    return d


def read_object(raw: bytes, label: str) -> dict:
    try:
        obj = json.loads(raw.decode('utf-8'),object_pairs_hook=_no_duplicate_json_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Hold(f'{label}: INVALID_UTF8_JSON') from exc
    if not isinstance(obj, dict):
        raise Hold(f'{label}: INVALID_ROOT')
    return obj


def canonical_name(name: str) -> bool:
    return isinstance(name, str) and FILENAME.fullmatch(name) is not None and name not in ('PRIVATE_INDEX.json', 'NAVIGUER_KITS.html')


def load_checked_archive(archive: Path) -> dict[str, bytes]:
    """Defense-in-depth; canonical release verification is performed separately."""
    members: dict[str,bytes] = {}
    total_bytes=0
    try:
        with zipfile.ZipFile(archive) as z:
            if len(z.infolist()) > 3001:raise Hold('RELEASE_TOO_MANY_MEMBERS')
            for info in z.infolist():
                n = info.filename
                mode = (info.external_attr >> 16) & 0o170000
                if (not n or n.startswith('/') or '\\' in n or
                    any(x in ('', '.', '..') for x in n.split('/')) or
                    mode not in (0, stat.S_IFREG) or n in members or n.endswith('/') or
                    info.file_size > 40_000_000):
                    raise Hold('RELEASE_UNSAFE_ARCHIVE_MEMBER')
                total_bytes += info.file_size
                if total_bytes > 200_000_000:raise Hold('RELEASE_TOO_LARGE')
                members[n] = z.read(info)
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        raise Hold('RELEASE_UNREADABLE') from exc
    return members


def prepare(archive: Path, verified: dict, existing_index: dict | None = None,
            filenames: dict[str, str] | None = None, existing_index_raw: bytes | None = None) -> tuple[dict, dict[str, bytes]]:
    """Plan only, given a *genuine result* from the canonical release checker.

    Passing a dictionary here programmatically is not trust: the CLI enforces
    a canonical verifier invocation before calling this function.
    """
    if not isinstance(verified, dict) or verified.get('verdict') != RELEASE_PASS or verified.get('schema') != 'learnit.atlas.qualified_release_set_result.v2':
        raise Hold('CANONICAL_RELEASE_VERIFICATION_REQUIRED')
    archive_raw = archive.read_bytes()
    if verified.get('releaseSha256') != digest(archive_raw) or verified.get('releaseBytes') != len(archive_raw):
        raise Hold('RELEASE_ARCHIVE_CHANGED_AFTER_VERIFICATION')
    manifest = verified.get('manifest')
    if not isinstance(manifest, dict) or manifest.get('schema') != VERIFIED_SCHEMA or not isinstance(manifest.get('entries'), list):
        raise Hold('VERIFIED_MANIFEST_INVALID')
    if not manifest['entries'] or len(manifest['entries']) > 1000:
        raise Hold('INVALID_RELEASE_ENTRY_COUNT')
    members = load_checked_archive(archive)
    existing = {}
    if existing_index_raw is not None and (existing_index is None or read_object(existing_index_raw,'index') != existing_index):
        raise Hold('EXISTING_INDEX_RAW_MISMATCH')
    if existing_index_raw is not None and existing_index is None:
        raise Hold('EXISTING_INDEX_MISSING_PARSED_VALUE')
    if existing_index is not None:
        if (existing_index.get('schema') != 'learnit.private-kit-index.verification-snapshot.v1' or
            existing_index.get('authority') is not False or
            existing_index.get('distribution_authorized') is not False or
            not isinstance(existing_index.get('entries'), list)):
            raise Hold('EXISTING_INDEX_INVALID')
        for row in existing_index['entries']:
            if not isinstance(row, dict):raise Hold('EXISTING_INDEX_ROW_INVALID')
            pair = (row.get('lineage_id'), row.get('revision_id'))
            if pair in existing: raise Hold('EXISTING_INDEX_DUPLICATE_IDENTITY')
            existing[pair] = row
    files: dict[str, bytes] = {}
    plan_entries = []
    seen = set()
    filenames = filenames or {}
    for entry in manifest['entries']:
        lineage, revision = entry.get('packageLineageId'), entry.get('packageRevisionId')
        if not UUID.fullmatch(str(lineage)) or not UUID.fullmatch(str(revision)) or (lineage, revision) in seen:
            raise Hold('RELEASE_DUPLICATE_OR_BAD_IDENTITY')
        seen.add((lineage, revision))
        kit = entry.get('kit')
        if not isinstance(kit, dict) or not SHA.fullmatch(str(kit.get('sha256'))) or type(kit.get('bytes')) is not int or kit['bytes'] <= 0:
            raise Hold('RELEASE_KIT_IDENTITY_MISSING')
        src = f'kits/{lineage}/{revision}.json'
        raw = members.get(src)
        if raw is None or len(raw) != kit['bytes'] or digest(raw) != kit['sha256']:
            raise Hold('RELEASE_KIT_BYTES_MISMATCH')
        obj = read_object(raw, 'kit')
        if (obj.get('contract') != 'learnit.kit.v6' or obj.get('packageLineageId') != lineage or
            obj.get('packageRevisionId') != revision or obj.get('packageRevisionDigest') != entry.get('packageRevisionDigest')):
            raise Hold('KIT_LOGICAL_IDENTITY_MISMATCH')
        if not isinstance(obj.get('courses'),list) or not obj['courses']:
            raise Hold('KIT_NO_COURSES')
        activities = 0
        for course in obj['courses']:
            if not isinstance(course,dict) or not isinstance(course.get('activities'),list):
                raise Hold('KIT_COURSE_INVALID')
            activities += len(course['activities'])
        if activities < 1: raise Hold('KIT_NO_ACTIVITIES')
        already = existing.get((lineage,revision))
        if already:
            # Never invent an alternate filename for an already stored revision.
            # The private index is only a snapshot; the executor must still
            # independently re-read the exact remote path, raw bytes and ACL.
            rel = already.get('relative_path')
            parts = rel.split('/') if isinstance(rel, str) else []
            if (len(parts) != 3 or parts[:2] != [lineage, revision] or
                not canonical_name(parts[2]) or '\\' in rel):
                raise Hold('EXISTING_DESTINATION_UNSAFE_OR_UNKNOWN')
            path = '20_KITS/' + rel
            if (already.get('kit_sha256') != kit['sha256'][7:] or
                already.get('private_copy_sha256_verified') not in (None, kit['sha256'][7:]) or
                already.get('private_storage_status') != 'STORED_PRIVATE_VERIFIED' or
                already.get('private_copy_access') not in ('OWNER_ONLY_AT_VERIFICATION', None)):
                raise Hold('EXISTING_IDENTITY_CONFLICT')
            action = 'VERIFY_EXISTING_REMOTE_BYTES_AND_ACL_NO_WRITE'
        else:
            name = filenames.get(lineage, f'{revision}.json')
            if not canonical_name(name): raise Hold('DESTINATION_UNSAFE_FILENAME')
            path = f'20_KITS/{lineage}/{revision}/{name}'
            action = 'PREFLIGHT_REMOTE_AND_CREATE_ONLY_IF_AUTHORIZED'
            files[path] = raw
        plan_entries.append({'lineage_id':lineage,'revision_id':revision,'title':obj.get('title'),'activities':activities,
                            'content_sha256':kit['sha256'],'content_bytes':len(raw),'destination':path,
                            'action':action,'factory_run_id':entry.get('factoryRun',{}).get('runId'),
                            'distribution_status':'NOT_AUTHORIZED'})
    # Fail rather than silently reconcile unknown current index collisions.
    if len(set(x['destination'] for x in plan_entries)) != len(plan_entries):
        raise Hold('DESTINATION_PATH_CONFLICT')
    plan = {'schema':SCHEMA,'status':'LOCAL_PREPARED_READ_ONLY_NOT_ADMITTED','authority':False,
            'release_id':manifest.get('releaseSetId'),'release_sha256':verified['releaseSha256'],
            'implementation_authority':manifest.get('factoryAuthority'),
            # Only original bytes from the remote object can be used as a preimage.
            'baseline_index_sha256':digest(existing_index_raw) if existing_index_raw is not None else None,
            'entries':plan_entries,'write_permissions_conferred':False,
            'remote_preconditions':['fresh UCP/HEAD and Operations admission','exact live remote catalogue and index preimage',
                'source identity/permissions readback','create-only conflict=fail','post-upload SHA256 readback and owner-only ACL',
                'CAS or explicitly risk-accepted controlled index update','no public distribution or Factory gate mutation'],
            'remaining_integration':'Human-governed code/CI integration and remote writer registration; no live hook installed'}
    return plan, files


def require_frozen_checkout(checkout: Path, expected_commit: str) -> None:
    """Check the trusted, human-governed exact commit and unchanged worktree."""
    if not re.fullmatch(r'[0-9a-f]{40}',expected_commit):raise Hold('EXPECTED_COMMIT_INVALID')
    try:
        head=subprocess.run(['git','-C',str(checkout),'rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=8).stdout.strip()
        dirty=subprocess.run(['git','-C',str(checkout),'status','--porcelain','--untracked-files=all'],capture_output=True,text=True,check=True,timeout=8).stdout.strip()
    except (OSError,subprocess.SubprocessError) as exc:
        raise Hold('CANONICAL_CHECKOUT_NOT_VERIFIABLE') from exc
    if head != expected_commit or dirty:
        raise Hold('CANONICAL_CHECKOUT_COMMIT_OR_WORKTREE_MISMATCH')


def verified_release(archive: Path, checkout: Path) -> dict:
    """Use repository's actual frozen V6 release verifier: no substitute PASS flags."""
    if not (checkout/'authoring/factory/release_set_v6.py').is_file():
        raise Hold('CANONICAL_RELEASE_VERIFIER_NOT_AVAILABLE')
    abs_checkout = str(checkout.resolve())
    sys.path.insert(0, abs_checkout)
    try:
        from authoring.factory import release_set_v6
        result = release_set_v6.verify_release_archive(archive)
    except Exception as exc:
        raise Hold('CANONICAL_RELEASE_VERIFICATION_FAILED:'+type(exc).__name__) from exc
    finally:
        sys.path.remove(abs_checkout)
    return result


def cli(argv=None) -> int:
    p=argparse.ArgumentParser(description='Prepare V6 private library intake (no remote write)')
    p.add_argument('--release',required=True,type=Path)
    p.add_argument('--verified-repository-checkout',required=True,type=Path,
                   help='Already-governance-verified canonical learnit-platform checkout')
    p.add_argument('--expected-repository-commit',required=True,
                   help='Exact governance-approved full Git commit SHA (not inferred from file content)')
    p.add_argument('--current-index',type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        require_frozen_checkout(a.verified_repository_checkout,a.expected_repository_commit)
        evidence=verified_release(a.release,a.verified_repository_checkout)
        index_raw=a.current_index.read_bytes() if a.current_index else None
        idx=read_object(index_raw,'index') if index_raw is not None else None
        plan, members=prepare(a.release,evidence,idx,existing_index_raw=index_raw)
        if a.output.exists(): raise Hold('OUTPUT_EXISTS_FAIL_CLOSED')
        a.output.parent.mkdir(parents=True,exist_ok=True)
        # No kit copies are created in ordinary mode; plan is only recommendation.
        payload=(json.dumps(plan,ensure_ascii=False,indent=2)+'\n').encode()
        with a.output.open('xb') as f:f.write(payload)
        print(json.dumps({'status':'PREPARED_READ_ONLY','entries':len(plan['entries']),
                          'candidate_new_copies':len(members),'plan_sha256':digest(payload)},ensure_ascii=False))
        return 0
    except (Hold,OSError) as exc:
        print('HOLD:',exc,file=sys.stderr)
        return 8

if __name__=='__main__':raise SystemExit(cli())
