#!/usr/bin/env python3
"""Bounded private kit copy executor. NOT a Factory hook or public publisher.

Invoke only after `private_kit_intake_bridge` has called the clean-checkout,
canonical V6 verifier. The service `port` must implement genuine provider-side
create-only / conflict-fail; a read-before-write check is NOT sufficient.
No derived index or navigation is updated here; caller must separately qualify
CAS for each pre-existing file. Partial success is a durable HOLD for reconciliation.
"""
from __future__ import annotations
import hashlib
import re
import time
from typing import Protocol

from private_kit_intake_bridge import SCHEMA, Hold, UUID, FILENAME, digest

SAFE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,139}(?:\.json)?$')

class ProviderPort(Protocol):
    def child(self, parent_id: str, name: str) -> dict | None: ...
    def create_folder_fail(self, parent_id: str, name: str) -> dict: ...
    def create_file_fail(self, parent_id: str, name: str, raw: bytes) -> dict: ...
    def content(self, item_id: str) -> bytes: ...
    def permissions(self, item_id: str) -> list[dict]: ...


def is_owner_only(rows: list[dict]) -> bool:
    return bool(rows) and all(isinstance(p, dict) and p.get('roles') == ['owner']
                              and not p.get('link') and not p.get('grantedToIdentitiesV2')
                              for p in rows)


def require_private(port: ProviderPort, item_id: str) -> None:
    if not is_owner_only(port.permissions(item_id)):
        raise Hold('ACL_NOT_OWNER_ONLY')


def verify_item(port: ProviderPort, item: dict, expected_name: str, raw: bytes) -> dict:
    if (not isinstance(item, dict) or not isinstance(item.get('id'),str) or
        item.get('name') != expected_name or item.get('size') != len(raw) or
        'file' not in item):
        raise Hold('REMOTE_ITEM_METADATA_MISMATCH')
    require_private(port, item['id'])
    data=port.content(item['id'])
    if not isinstance(data,bytes) or len(data)!=len(raw) or hashlib.sha256(data).digest()!=hashlib.sha256(raw).digest():
        raise Hold('REMOTE_READBACK_SHA256_MISMATCH')
    return {'id':item['id'], 'name':expected_name,'bytes':len(raw),'sha256':digest(raw),
            'private':'OWNER_ONLY_AT_VERIFICATION'}


def _folder(port: ProviderPort, parent: str, name: str, *, allow_create: bool) -> dict:
    if not SAFE_NAME.fullmatch(name): raise Hold('FOLDER_NAME_UNSAFE')
    item=port.child(parent,name)
    if item is None:
        if not allow_create:raise Hold('EXPECTED_FOLDER_ABSENT')
        # ProviderPort must implement atomic create-only; NEVER retry a conflict.
        item=port.create_folder_fail(parent,name)
    if not isinstance(item,dict) or item.get('name')!=name or 'folder' not in item or not isinstance(item.get('id'),str):
        raise Hold('FOLDER_METADATA_MISMATCH')
    require_private(port,item['id'])
    return item


def execute_verified_plan(plan: dict, members: dict[str, bytes], port: ProviderPort,
                          course_root_id: str, authorization: bool = False,
                          observe=None) -> dict:
    """Only exact new bytes and verify-only existing paths; no indexed publication.

    This function is a transport-independent operation engine, NOT an authorization
    source. Production caller must validate UCP/HEAD/Operations mandate and bind
    `members` to the actual canonical V6 verifier before setting authorization.
    """
    started=time.monotonic()
    if authorization is not True:raise Hold('FRESH_GOVERNED_AUTHORIZATION_REQUIRED')
    if (not isinstance(plan,dict) or plan.get('schema')!=SCHEMA or
        plan.get('status')!='LOCAL_PREPARED_READ_ONLY_NOT_ADMITTED' or
        plan.get('authority') is not False or plan.get('write_permissions_conferred') is not False or
        not isinstance(plan.get('entries'),list) or not plan['entries']):
        raise Hold('UNTRUSTED_PLAN')
    actions={'PREFLIGHT_REMOTE_AND_CREATE_ONLY_IF_AUTHORIZED', 'VERIFY_EXISTING_REMOTE_BYTES_AND_ACL_NO_WRITE'}
    expected_new={e.get('destination') for e in plan['entries'] if e.get('action')=='PREFLIGHT_REMOTE_AND_CREATE_ONLY_IF_AUTHORIZED'}
    if set(members)!=expected_new or len(expected_new)!=len(members):raise Hold('PLAN_MEMBERS_NOT_EXACT')
    destinations=[e.get('destination') for e in plan['entries']]
    if len(set(destinations)) != len(destinations):raise Hold('PLAN_DUPLICATE_DESTINATION')
    for e in plan['entries']:
        path=e.get('destination');parts=path.split('/') if isinstance(path,str) else []
        if (len(parts)!=4 or parts[0]!='20_KITS' or not UUID.fullmatch(parts[1]) or
            not UUID.fullmatch(parts[2]) or not FILENAME.fullmatch(parts[3]) or
            e.get('lineage_id')!=parts[1] or e.get('revision_id')!=parts[2] or
            e.get('action') not in actions or not re.fullmatch(r'sha256:[a-f0-9]{64}',str(e.get('content_sha256')))):
            raise Hold('PLAN_PATH_OR_IDENTITY_INVALID')
        if e['action'] in actions and path in members and digest(members[path])!=e['content_sha256']:
            raise Hold('PLAN_MEMBER_SHA256_MISMATCH')
    if not isinstance(course_root_id,str) or not course_root_id:raise Hold('COURSE_ROOT_ID_REQUIRED')
    root=_folder(port,course_root_id,'20_KITS',allow_create=False)
    verified=[]
    for e in plan['entries']:
        path=e['destination'];parts=path.split('/')
        existing=e['action']=='VERIFY_EXISTING_REMOTE_BYTES_AND_ACL_NO_WRITE'
        parent=root['id']
        for name in parts[1:3]:
            parent=_folder(port,parent,name,allow_create=not existing)['id']
        name=parts[3]
        item=port.child(parent,name)
        if existing:
            if item is None:raise Hold('KNOWN_KIT_NOT_PRESENT')
            # The planner keeps historical bytes out of members. The source
            # bytes for verification MUST be an exact canonical release member
            # passed through a separate verified-content lookup; no blind PASS.
            if not isinstance(e.get('content_sha256'),str):raise Hold('KNOWN_KIT_DIGEST_MISSING')
            require_private(port,item['id'])
            data=port.content(item['id'])
            if not isinstance(data,bytes) or digest(data)!=e['content_sha256'] or item.get('name')!=name:
                raise Hold('KNOWN_KIT_REMOTE_MISMATCH')
            record={'id':item['id'],'name':name,'bytes':len(data),'sha256':digest(data),
                    'private':'OWNER_ONLY_AT_VERIFICATION','mode':'VERIFIED_EXISTING_NO_WRITE'}
        else:
            if item is not None:raise Hold('NEW_KIT_DESTINATION_CONFLICT_NO_OVERWRITE')
            data=members[path]
            created=port.create_file_fail(parent,name,data)
            record=verify_item(port,created,name,data)
            record['mode']='CREATED_PRIVATE_VERIFIED'
        record['destination']=path
        verified.append(record)
        if observe:observe({'completed':len(verified),'total':len(plan['entries']),'destination':path,
                            'mode':record['mode'],'elapsed_seconds':round(time.monotonic()-started,3)})
    return {'status':'PASS_PRIVATE_COPIES_VERIFIED_INDEX_NOT_COMMITTED',
            'entries':verified,'count':len(verified),'elapsed_seconds':round(time.monotonic()-started,3),
            'public_distribution':False,'index_and_navigator':'UNMODIFIED_REQUIRE_SEPARATE_CAS_AND_READBACK'}
