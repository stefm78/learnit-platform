"""Draft Graph conflict=fail upload-session adapter for PR #511.

Microsoft Graph `createUploadSession` documents conflict=fail in the item body.
This code intentionally requires an externally qualified, independently authenticated
transport and never reads or exports credentials. Upload URLs are credentials: do
not log them, put them in exceptions or forward Bearer tokens to upload hosts.

LOCAL CANDIDATE ONLY. A unit mock is NOT proof of live Graph semantics.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote, urlsplit

SAFE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,139}\.json$')
DRIVE = re.compile(r'^[A-Za-z0-9!._-]+$')

class Hold(RuntimeError): pass

class QualifiedSessionTransport(Protocol):
    def assert_real_provider_and_scoped_authorization(self) -> None:
        """Must fail if real auth, exact drive, create-only semantics unproven."""
        ...
    def post_graph_json(self, url: str, body: bytes) -> tuple[int, bytes]: ...
    def upload_without_bearer(self, upload_url: str, content: bytes) -> tuple[int, bytes]:
        """Perform complete bounded upload session, not a simple PUT/content.

        For a single chunk, send Content-Length and Content-Range 0-(N-1)/N.
        Verify upload URL against trusted tenant/provider rules; never log it.
        Enforce no Authorization header on upload endpoint. On ambiguous
        transport status do NOT auto-retry the create; reconcile exact remote path.
        """
        ...

@dataclass(frozen=True)
class SessionCreateFile:
    drive_id: str
    transport: QualifiedSessionTransport

    def __post_init__(self):
        if not isinstance(self.drive_id,str) or not DRIVE.fullmatch(self.drive_id):
            raise Hold('INVALID_DRIVE')

    def create_file_fail(self, parent_id: str, name: str, raw: bytes) -> dict:
        self.transport.assert_real_provider_and_scoped_authorization()
        if (not isinstance(parent_id,str) or not DRIVE.fullmatch(parent_id) or
                not isinstance(name,str) or not SAFE.fullmatch(name) or
                not isinstance(raw,bytes) or not raw or len(raw)>10_485_760):
            raise Hold('INVALID_PARENT_NAME_OR_SIZE')
        url = ('https://graph.microsoft.com/v1.0/drives/'+quote(self.drive_id,safe='')+
               '/items/'+quote(parent_id,safe='')+':/'+quote(name,safe='')+':/createUploadSession')
        request = json.dumps({'item':{'name':name,'@microsoft.graph.conflictBehavior':'fail'}},
                             separators=(',',':')).encode('utf-8')
        status, response = self.transport.post_graph_json(url,request)
        if status not in (200,201):
            raise Hold('GRAPH_CREATE_SESSION_FAILED_'+str(status))
        try: session=json.loads(response.decode('utf-8'))
        except (UnicodeError, ValueError) as exc:raise Hold('GRAPH_SESSION_UNREADABLE') from exc
        if not isinstance(session,dict) or not isinstance(session.get('uploadUrl'),str):
            raise Hold('GRAPH_SESSION_URL_MISSING')
        # URL is a bearer-like capability and must never appear in a diagnostic.
        parsed=urlsplit(session['uploadUrl'])
        if (parsed.scheme!='https' or not parsed.netloc or parsed.username is not None or
                parsed.password is not None or parsed.fragment or
                parsed.hostname in ('localhost','127.0.0.1')):
            raise Hold('GRAPH_SESSION_URL_UNTRUSTED')
        code, completed = self.transport.upload_without_bearer(session['uploadUrl'],raw)
        if code!=201:
            # 200 could reflect an update, not a provably fresh creation.
            raise Hold('GRAPH_NEW_OBJECT_NOT_EXCLUSIVELY_CREATED_'+str(code))
        try: obj=json.loads(completed.decode('utf-8'))
        except (UnicodeError,ValueError) as exc:raise Hold('GRAPH_CREATED_OBJECT_UNREADABLE') from exc
        if (not isinstance(obj,dict) or obj.get('name')!=name or
                obj.get('size')!=len(raw) or not isinstance(obj.get('id'),str) or
                not isinstance(obj.get('file'),dict) or not obj['id']):
            raise Hold('GRAPH_CREATED_OBJECT_MISMATCH')
        return obj
