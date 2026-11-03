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
    receipt = {'status':'LOCAL_PLAN_ONLY_NOT_ADMITTED','authority':False,
            'release_sha256':'sha256:'+hashlib.sha256(archive_raw).hexdigest(),
            'factory_run_ids':run_ids,'plan':result['plan'],
            'members_sha256':result['members_sha'],
            'remote_mutation':False,'automatic_hook_installed':False}
    receipt['manual_handoff'] = build_command(receipt,archive)
    return receipt


# Human-reviewed, read-only handoff adapted from local manual-publication V1.
HEX64 = re.compile(r"^[a-f0-9]{64}$")
HASH = re.compile(r"^sha256:[a-f0-9]{64}$")
UUID = re.compile(r"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$")
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,139}\.json$")
ACTIONS = {"PREFLIGHT_REMOTE_AND_CREATE_ONLY_IF_AUTHORIZED",
           "VERIFY_EXISTING_REMOTE_BYTES_AND_ACL_NO_WRITE"}

def must(ok: bool, why: str) -> None:
    if not ok:
        raise Hold(why)


def digest_file(path: pathlib.Path) -> tuple[str, int]:
    h=hashlib.sha256()
    n=0
    with path.open("rb") as f:
        while True:
            block=f.read(1024*1024)
            if not block: break
            n+=len(block)
            must(n<=200_000_000,"RELEASE_TOO_LARGE")
            h.update(block)
    return h.hexdigest(),n


def build_command(receipt: dict, release: pathlib.Path) -> str:
    """Formatting only: no Graph calls, auth, token access, subprocess or mutation."""
    must(isinstance(receipt,dict),"RECEIPT_INVALID")
    must(receipt.get("status")=="LOCAL_PLAN_ONLY_NOT_ADMITTED" and
         receipt.get("authority") is False and receipt.get("remote_mutation") is False and
         receipt.get("automatic_hook_installed") is False,"NOT_A_READ_ONLY_POST_PASS_RECEIPT")
    plan=receipt.get("plan")
    must(isinstance(plan,dict) and plan.get("schema")=="learnit.private-kit-intake-plan.v1" and
         plan.get("status")=="LOCAL_PREPARED_READ_ONLY_NOT_ADMITTED" and
         plan.get("authority") is False and plan.get("write_permissions_conferred") is False,
         "PLAN_NOT_READ_ONLY")
    h=receipt.get("release_sha256")
    must(isinstance(h,str) and HASH.fullmatch(h) is not None and
         plan.get("release_sha256")==h[7:],"RELEASE_IDENTITY_MISMATCH")
    real_hash,real_size=digest_file(release)
    must(real_hash==h[7:] and real_size>0,"RELEASE_ARCHIVE_BYTES_CHANGED")
    idx=plan.get("baseline_index_sha256")
    must(isinstance(idx,str) and HEX64.fullmatch(idx) is not None,
         "FRESH_RAW_PRIVATE_INDEX_NOT_BOUND")
    release_id=plan.get("release_id")
    must(isinstance(release_id,str) and HASH.fullmatch(release_id),
         "CANONICAL_RELEASE_SET_ID_MISSING")
    authority=plan.get("implementation_authority")
    must(isinstance(authority,str) and re.fullmatch(r"[a-f0-9]{40}",authority),
         "CANONICAL_FACTORY_IMPLEMENTATION_AUTHORITY_MISSING")
    runs=receipt.get("factory_run_ids")
    must(isinstance(runs,(list,tuple)) and len(runs)>0 and
         all(isinstance(x,str) and HASH.fullmatch(x) for x in runs) and
         len(set(runs))==len(runs),"FACTORY_RUN_IDENTITIES_INVALID")
    es=plan.get("entries")
    must(isinstance(es,list) and 0<len(es)<=1000,"PLAN_ENTRIES_INVALID")
    members=receipt.get("members_sha256")
    must(isinstance(members,dict),"MEMBER_DIGESTS_ABSENT")
    pairs=set(); paths=set(); new_paths=set(); rows=[]
    for e in es:
        must(isinstance(e,dict),"PLAN_ENTRY_INVALID")
        line,rev=e.get("lineage_id"),e.get("revision_id")
        must(isinstance(line,str) and UUID.fullmatch(line) and
             isinstance(rev,str) and UUID.fullmatch(rev),"BAD_KIT_IDENTITY")
        must((line,rev) not in pairs,"DUPLICATE_KIT_IDENTITY")
        pairs.add((line,rev))
        path=e.get("destination")
        parts=path.split("/") if isinstance(path,str) else []
        must(len(parts)==4 and parts[:3]==["20_KITS",line,rev] and
             SAFE_NAME.fullmatch(parts[3]) is not None and path not in paths,
             "UNSAFE_OR_DUPLICATE_DESTINATION")
        paths.add(path)
        act=e.get("action")
        must(act in ACTIONS,"UNKNOWN_ACTION")
        run=e.get("factory_run_id")
        must(isinstance(run,str) and run in runs,"UNBOUND_FACTORY_RUN")
        content=e.get("content_sha256")
        must(isinstance(content,str) and HASH.fullmatch(content),"KIT_HASH_INVALID")
        must(type(e.get("content_bytes")) is int and e["content_bytes"]>0,
             "KIT_BYTES_INVALID")
        if act=="PREFLIGHT_REMOTE_AND_CREATE_ONLY_IF_AUTHORIZED":
            must(members.get(path)==content[7:],"NEW_KIT_SOURCE_DIGEST_MISMATCH")
            new_paths.add(path)
        else:
            must(path not in members,"EXISTING_KIT_MUST_BE_VERIFY_ONLY")
        rows.append((line,rev,path,content,act))
    must(set(members)==new_paths,"UNBOUND_OR_EXTRA_MEMBER")
    must({e["factory_run_id"] for e in es}==set(runs),"FACTORY_RUN_SET_INCOMPLETE_OR_EXTRA")
    count_new=sum(a=="PREFLIGHT_REMOTE_AND_CREATE_ONLY_IF_AUTHORIZED" for *_,a in rows)
    count_old=len(rows)-count_new
    if count_new == 0:
        return ("# LearnIT — aucun nouveau kit à enregistrer\n\n"
                "Release vérifiée : `sha256:"+real_hash+"` ; toutes les versions sont déjà référencées. "
                "Un contrôle des copies et des permissions en lecture seule peut être proposé, "
                "mais AUCUNE commande de modification OneDrive ne doit être émise.\n")
    summary="\n".join(f"- `{path}` — `{action}` — `{kit_hash}`" for _,_,path,kit_hash,action in rows)
    # The request is deliberately self-contained, and its exact-source identifier
    # must be resolved from the real release archive by the operator/executor.
    return f"""# LearnIT — demande d'action humaine de publication PRIVÉE

**ETAT : À SOUMETTRE, NON EXÉCUTÉ.** Ce document n'est ni une attestation
Factory, ni une délégation de droits, ni une autorisation de distribution.

Vérification préalable externe obligatoire : exécuter les validateurs V6 canoniques,
avec un checkout Git gouverné, puis `post_pass_factory_step.py` avec l'événement
durable exact. Une copie de JSON fabriquée ne constitue jamais une preuve.

## Identités figées pour l'opération proposée

- Archive V6 : `sha256:{real_hash}` ({real_size} octets)
- `releaseSetId` canonique : `{release_id}`
- Autorité Git Factory déclarée : `{authority}` (à revalider)
- Base de l'index privé à recontrôler : `sha256:{idx}`
- FactoryRun(s) : {len(runs)} — {', '.join(f'`{r}`' for r in sorted(runs))}
- Entrées : {len(rows)} ; nouveaux : {count_new} ; déjà référencés : {count_old}
{summary}

## Commande à envoyer explicitement dans ChatGPT

> GO CONDITIONNEL — LearnIT, rangement privé MANUEL de la release V6
> `sha256:{real_hash}` uniquement. Revalide UCP ancrée, HEAD,
> autorisations Operations/Factory, provenance et octets ZIP exacts, puis
> recalcule le plan depuis le `PRIVATE_INDEX.json` courant de OneDrive.
> Les identités ci-dessus sont des contraintes de sélection, pas une preuve.
> Si le ZIP ne peut pas être retrouvé par son identité exacte : HOLD.
> Exécute seulement les créations de kits réellement nouveaux avec
> `conflict=fail`, contrôle SHA-256 et permissions après copie ; les kits déjà
> référencés sont VERIFICATION_ONLY sans écriture. Aucun renommage ni écrasement.
> Ne mets à jour `PRIVATE_INDEX.json` puis `NAVIGUER_KITS.html` qu'après
> vérification des copies ET preuve d'un mécanisme de concurrence sûr ; en cas
> de remplacement non atomique, demande une acceptation humaine distincte
> du risque résiduel avant écriture. En cas de désaccord/échec partiel : HOLD
> et réconciliation, aucun retry aveugle.
> Après enregistrement privé confirmé, reconstruis éventuellement les vues
> du catalogue général avec le script CANONIQUE GitHub
> `tools/refresh_onedrive_catalogue.py` (PAS la copie historique V1) ; contrôle
> les quatre résultats et n'écris les pages de `05_CATALOGUE` que sous
> autorisation exacte et vérification des conflits.
> Aucune publication élèves, ACL, GitHub, Factory, Pages ni données élèves.
> Rends les liens privés, le verdict et les empreintes réellement relues.

**STOP si un prérequis n'est pas vérifié.** Un GO textuel ne supplante jamais
les autorités actives, l'admission du nouveau kit ou les contrôles de concurrence.
"""




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
