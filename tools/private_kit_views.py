"""Candidate private index + navigator coordinator for PR #511.

NOT a deployed Microsoft Graph CAS/lease implementation. External adapters must
prove a real provider-enforced conditional update OR a qualified exclusive writer.
No web access, credential handling, remote mutation or self-granted authority.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import urlencode

INDEX_SCHEMA = 'learnit.private-kit-index.verification-snapshot.v1'
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
SHA = re.compile(r'^[0-9a-f]{64}$')
SAFE_FILE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,139}\.json$')

class Hold(RuntimeError):
    pass

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode('utf-8')

def unique_object(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, val in items:
            if key in result:
                raise Hold('DUPLICATE_JSON_KEY')
            result[key] = val
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs)
    except (UnicodeError, ValueError) as exc:
        raise Hold('INDEX_INVALID_JSON') from exc
    if not isinstance(value, dict):
        raise Hold('INDEX_ROOT_INVALID')
    return value

@dataclass(frozen=True)
class Snapshot:
    raw: bytes
    etag: str

class ConditionalViewPort(Protocol):
    """External implementation must establish concurrency safety separately.

    `commit_conditional` must guarantee that stale ETag causes NO mutation.
    A local mock alone cannot establish any provider-side property.
    """
    def read(self, name: str) -> Snapshot: ...
    def assert_live_conditional_write_qualified(self) -> None: ...
    def commit_conditional(self, name: str, prior_etag: str, raw: bytes) -> None: ...


def validate_index(index: dict) -> dict[tuple[str, str], dict]:
    if (index.get('schema') != INDEX_SCHEMA or index.get('authority') is not False or
            index.get('distribution_authorized') is not False or
            index.get('public_access_authorized') is not False or
            not isinstance(index.get('entries'), list)):
        raise Hold('INDEX_CONTRACT_OR_DISTRIBUTION_INVALID')
    identities = {}
    paths = set()
    item_ids = set()
    for row in index['entries']:
        if not isinstance(row, dict): raise Hold('INDEX_ENTRY_INVALID')
        lineage, revision = row.get('lineage_id'), row.get('revision_id')
        key = (lineage, revision)
        relative = row.get('relative_path')
        p = relative.split('/') if isinstance(relative, str) else []
        if (not all(isinstance(x, str) and UUID.fullmatch(x) for x in key) or
                len(p) != 3 or p[:2] != [lineage, revision] or
                not SAFE_FILE.fullmatch(p[2]) or key in identities or relative in paths):
            raise Hold('INDEX_PATH_OR_IDENTITY_COLLISION')
        if (not isinstance(row.get('title'), str) or not row['title'].strip() or
                row.get('course_group') is not None and not isinstance(row['course_group'],str) or
                row.get('activities') is not None and (type(row['activities']) is not int or row['activities'] < 0)):
            raise Hold('INDEX_DISPLAY_METADATA_INVALID')
        item_id = row.get('private_copy_id')
        sha = row.get('private_copy_sha256_verified')
        if (not isinstance(item_id, str) or not item_id or item_id in item_ids or
                '/' in item_id or '\\' in item_id or
                not isinstance(sha, str) or not SHA.fullmatch(sha) or
                row.get('kit_sha256') != sha):
            raise Hold('INDEX_REMOTE_ID_OR_SHA_INVALID')
        if (row.get('private_copy_access') != 'OWNER_ONLY_AT_VERIFICATION' or
                row.get('distribution_status') != 'NOT_AUTHORIZED'):
            raise Hold('INDEX_ACCESS_OR_DISTRIBUTION_INVALID')
        identities[key] = row
        item_ids.add(item_id)
        paths.add(relative)
    if index.get('kit_count') != len(identities):
        raise Hold('INDEX_KIT_COUNT_INVALID')
    return identities


def validated_added_entry(entry: dict) -> tuple[str, str]:
    template = {'schema': INDEX_SCHEMA, 'authority': False,
                'distribution_authorized': False, 'public_access_authorized': False,
                'kit_count': 1, 'entries': [entry]}
    return next(iter(validate_index(template)))


def update_index(index: dict, entry: dict) -> tuple[dict, bool]:
    prior = validate_index(index)
    identity = validated_added_entry(entry)
    found = prior.get(identity)
    if found is not None:
        # Replayed event may only confirm the exact SAME stored kit identity.
        if any(found.get(field) != entry.get(field) for field in
               ('relative_path', 'private_copy_id', 'kit_sha256', 'private_copy_sha256_verified')):
            raise Hold('EXISTING_IDENTITY_CONFLICT')
        return copy.deepcopy(index), False
    if any(x.get('private_copy_id') == entry.get('private_copy_id') or
           x.get('relative_path') == entry.get('relative_path') for x in prior.values()):
        raise Hold('DESTINATION_REUSED_FOR_NEW_IDENTITY')
    out = copy.deepcopy(index)
    out['entries'].append(copy.deepcopy(entry))
    out['entries'].sort(key=lambda x: (x['lineage_id'], x['revision_id']))
    out['kit_count'] = len(out['entries'])
    out['current_remote_status'] = 'VERIFIED_AS_OF_PER_ENTRY_TIMESTAMPS_NOT_LIVE'
    out['status'] = 'PRIVATE_INDEX_DERIVED_SNAPSHOT_NOT_DISTRIBUTED'
    # Historical aggregate verification counts are NOT incremented unless ALL
    # existing kits were actually rechecked. Preserve the original snapshot.
    out['notes'] = ('Vue dérivée privée, non autoritaire. Chaque entrée porte '
                    'sa propre date de vérification. Aucune publication élèves.')
    validate_index(out)
    return out, True


def render_navigation(index: dict, drive_id: str) -> bytes:
    """Derived static navigator; preserves grouped cards and search UX.

    All variable content is escaped in HTML. The search script is constant,
    reads DOM text only and never executes or fetches user-supplied content.
    """
    validate_index(index)
    if not isinstance(drive_id, str) or not re.fullmatch(r'[A-Za-z0-9!._-]+', drive_id):
        raise Hold('DRIVE_ID_INVALID')
    groups: dict[str, list[dict]] = {}
    for entry in index['entries']:
        groups.setdefault(entry.get('course_group') or 'Autres kits', []).append(entry)
    blocks = []
    for group in sorted(groups, key=str.casefold):
        cards = []
        for row in sorted(groups[group], key=lambda x: (x['title'].casefold(),x['lineage_id'])):
            title = html.escape(row['title'],quote=True)
            link = 'https://onedrive.live.com?' + urlencode({'cid':drive_id,'id':row['private_copy_id']})
            when = html.escape(str(row.get('private_copy_verified_utc','UNKNOWN')),quote=True)
            activities = row.get('activities')
            count = str(activities) + ' activités' if type(activities) is int else 'Nombre d’activités non vérifié'
            cards.append('<article class="kit"><h3>'+title+'</h3><p>'+html.escape(count)+' · diffusion aux élèves non autorisée</p>'
                         '<p><a href="'+html.escape(link,quote=True)+'" rel="noopener noreferrer" target="_blank">Ouvrir le kit privé</a></p>'
                         '<small>SHA-256 : '+html.escape(row['private_copy_sha256_verified'])+' · contrôlé '+when+'</small></article>')
        blocks.append('<section><h2>'+html.escape(group,quote=True)+'</h2><div class="grid">'+''.join(cards)+'</div></section>')
    style = ('<style>body{font-family:system-ui,sans-serif;max-width:1024px;margin:2rem auto;padding:0 1rem;'
             'line-height:1.5;color:#17283c}input{padding:.75rem;width:100%;box-sizing:border-box;max-width:600px}'
             '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}'
             'article{border:1px solid #ccd5e0;border-radius:10px;padding:1rem;overflow-wrap:anywhere}'
             'small{color:#51606d}a{color:#154d92} .kit[hidden]{display:none}</style>')
    script = ("<script>const q=document.getElementById('search'),cards=[...document.querySelectorAll('.kit')],"
              "count=document.getElementById('count');q.addEventListener('input',()=>{"
              "let n=0;const s=q.value.toLocaleLowerCase('fr').trim();for(const c of cards){"
              "const group=c.closest('section').querySelector('h2').textContent;"
              "const ok=(c.textContent+' '+group).toLocaleLowerCase('fr').includes(s);"
              "c.hidden=!ok;if(ok)n++;}count.textContent=n+' kit(s) trouvé(s)';});</script>")
    doc = ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>Bibliothèque privée LearnIT</title>'+style+'</head><body><main>'
           '<h1>Bibliothèque pédagogique privée LearnIT</h1>'
           '<p>Index dérivé, non autoritaire. Vérifications datées par kit, non temps réel. '
           'Authentification OneDrive requise ; aucune publication élèves.</p>'
           '<label for="search">Rechercher un kit</label><input id="search" type="search" '
           'placeholder="Matière, sujet, module…"><p id="count">'+str(len(index['entries']))+' kit(s) trouvé(s)</p>'
           +''.join(blocks)+script+'</main></body></html>')
    return doc.encode('utf-8')

def reconcile_views(port: ConditionalViewPort, entry: dict, drive_id: str,
                    *, qualification_verified: bool, kit_remote_verified: bool) -> dict:
    """Safe two-view bounded commit, with replay/partial-failure reconciliation.

    No claim of atomicity across both objects. If index succeeds but navigator
    fails, HOLD. A new invocation can regenerate the navigator from the index.
    Caller must ensure event/source authorization and single writer or REAL CAS.
    """
    if qualification_verified is not True or kit_remote_verified is not True:
        raise Hold('CANONICAL_OR_REMOTE_KIT_EVIDENCE_NOT_VERIFIED')
    port.assert_live_conditional_write_qualified()
    i0 = port.read('PRIVATE_INDEX.json')
    n0 = port.read('NAVIGUER_KITS.html')
    if not isinstance(i0, Snapshot) or not isinstance(n0, Snapshot) or not i0.etag or not n0.etag:
        raise Hold('VIEW_PREIMAGE_NOT_VERIFIABLE')
    original = unique_object(i0.raw)
    updated, newly_registered = update_index(original, entry)
    i1_raw = canonical(updated) if newly_registered else i0.raw
    n1_raw = render_navigation(updated, drive_id)
    # Only if necessary; never assume read-before-write is a CAS guarantee.
    if i0.raw != i1_raw:
        port.commit_conditional('PRIVATE_INDEX.json', i0.etag, i1_raw)
        if port.read('PRIVATE_INDEX.json').raw != i1_raw:
            raise Hold('INDEX_POSTWRITE_READBACK_MISMATCH')
    if n0.raw != n1_raw:
        port.commit_conditional('NAVIGUER_KITS.html', n0.etag, n1_raw)
        if port.read('NAVIGUER_KITS.html').raw != n1_raw:
            raise Hold('NAV_POSTWRITE_READBACK_MISMATCH')
    if (port.read('PRIVATE_INDEX.json').raw != i1_raw or
            port.read('NAVIGUER_KITS.html').raw != n1_raw):
        raise Hold('VIEWS_FINAL_DRIFT')
    return {'status':'VIEWS_CONSISTENT_PRIVATELY_NOT_PUBLIC',
            'new_registration':newly_registered,
            'kit_count':len(updated['entries']),
            'index_sha256':digest(i1_raw),'navigator_sha256':digest(n1_raw),
            'note':'External qualification and owner-only ACL required; not a final Factory E2E PASS'}
