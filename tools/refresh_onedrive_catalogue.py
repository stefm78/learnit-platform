#!/usr/bin/env python3
"""Refresh LearnIT's derived OneDrive course/kit catalogues. Non-authoritative."""
from __future__ import annotations
import argparse,csv,hashlib,html,json,zipfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

PASS="PASS_AI_KIT_FACTORY_V1"
PASS_V6={"PASS_AI_KIT_FACTORY_V6_R2","PASS_AI_KIT_FACTORY_V6_R3"}
V6_STATUS="USABLE_FACTORY_PASS_V6"
SOURCE="https://github.com/stefm78/learnit-platform/blob/main/tools/refresh_onedrive_catalogue.py"

def J(p): return json.loads(p.read_text(encoding="utf-8"))
def H(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def B(x): return x[7:] if isinstance(x,str) and x.startswith("sha256:") else x

def web(item):
    if not item or "!" not in item:return None
    cid,x=item.split("!",1); x=x[1:] if x.startswith("s") else x; c=x.replace("-","")
    if len(c)==32 and all(v in "0123456789abcdefABCDEF" for v in c):
        x=f"{c[:8]}-{c[8:12]}-{c[12:16]}-{c[16:20]}-{c[20:]}"
    return f"https://onedrive.live.com/?id={quote(x,safe='-')}&cid={quote(cid,safe='')}"

def item_locator_matches(record):
    """Bind displayed OneDrive item ID to the exact canonical Graph item URL."""
    if not isinstance(record, dict):
        return False
    item_id = record.get("item_id")
    graph = record.get("graph_locator") or record.get("graph_url")
    if not isinstance(item_id, str) or not isinstance(graph, str) or web(item_id) is None:
        return False
    if "!" not in item_id:
        return False
    drive, item = item_id.split("!", 1)
    if len(drive) != 16 or any(c not in "0123456789abcdefABCDEF" for c in drive):
        return False
    if len(item) != 33 or item[0] != "s" or any(c not in "0123456789abcdefABCDEF" for c in item[1:]):
        return False
    try:
        parsed = urlsplit(graph)
        return (parsed.scheme == "https" and parsed.hostname == "graph.microsoft.com"
                and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
                and unquote(parsed.path) == f"/v1.0/drives/{drive}/items/{item_id}")
    except ValueError:
        return False

def latest(mp,m):
    root=mp.parent.parent/(m.get("state_log",{}).get("relative_path") or "20_MANIFEST/STATELOG")
    ev={}; dup=set()
    for p in root.rglob("*.json") if root.exists() else []:
        try:e=J(p); r=e.get("revision")
        except Exception:continue
        if not isinstance(r,int):continue
        if r in ev:dup.add(r)
        ev[r]=e
    if not ev:return None,"STATELOG_ABSENT"
    if dup:return None,"STATELOG_DUPLICATE_REVISION:"+",".join(map(str,sorted(dup)))
    a=m.get("state_log",{}).get("initial_revision",min(ev)); z=max(ev)
    miss=sorted(set(range(a,z+1))-set(ev))
    if miss:return None,"STATELOG_GAP:"+",".join(map(str,miss))
    for r in range(a+1,z+1):
        if ev[r].get("previous_revision") not in (None,r-1):return None,f"STATELOG_BAD_PREVIOUS_REVISION:{r}"
    return ev[z],None

def courses(root):
    out=[]
    for mp in sorted((root/"10_COURSES").glob("*/*/*/*/20_MANIFEST/course_manifest.json")):
        m=J(mp); e,err=latest(mp,m); s=(e or {}).get("resulting_state") or (e or {}).get("state") or {}; folder=mp.parent.parent
        out.append(dict(course_key=m.get("course_key",folder.name),title=m.get("title") or m.get("course_key") or folder.name,academic_year=m.get("academic_year"),relative_path=folder.relative_to(root).as_posix(),stage=s.get("stage") if not err else "RECONSTRUCTION_HOLD",status=s.get("status") if not err else "HOLD",revision=e.get("revision") if e and not err else None,limitations=(e or {}).get("limitations") or [],error=err))
    return out

def legacy_kits(root,by):
    out=[]; diag=[]; base=root/"80_CONTROL/REVIEW_HANDOFFS"
    if not base.exists():return out,["REVIEW_HANDOFFS_ABSENT"]
    for lp in sorted(base.glob("*/HANDOFF_LOCATOR.json")):
        try:l=J(lp)
        except Exception:diag.append(f"UNREADABLE_LOCATOR:{lp.parent.name}");continue
        key=l.get("course_key"); a=next((x for x in l.get("artifacts",[]) if x.get("name")=="generated-kit.json"),None)
        if not key or not a:continue
        if not item_locator_matches(a):diag.append(f"LEGACY_ITEM_BINDING_INVALID:{key}");continue
        kp=lp.parent/"generated-kit.json"; fp=lp.parent.parent/(lp.parent.name+"_OUTPUTS")/"factory-run.json"
        if not kp.exists() or not fp.exists():diag.append(f"INCOMPLETE_KIT_EVIDENCE:{key}");continue
        f=J(fp); expected=B(a.get("sha256")); fhash=B(f.get("evidenceBundle",{}).get("artifacts",{}).get("generatedKit",{}).get("sha256")); verdict=f.get("finalDecision",{}).get("verdict") or f.get("decision",{}).get("verdict") or f.get("evidenceBundle",{}).get("finalDecision",{}).get("verdict")
        if verdict!=PASS or not expected or H(kp)!=expected or fhash!=expected:diag.append(f"KIT_NOT_USABLE:{key}:{verdict or 'NO_VERDICT'}");continue
        k=J(kp); acts=[a for c in k.get("courses",[]) for a in c.get("activities",[])]; types=Counter(a.get("type","unknown") for a in acts); c=by.get(key,{})
        out.append(dict(course_key=key,course_title=c.get("title") or key,kit_title=k.get("title") or c.get("title") or key,sha256=expected,bytes=a.get("size_bytes") or kp.stat().st_size,activities=len(acts),types=dict(sorted(types.items())),factory_verdict=verdict,item_id=a.get("item_id"),web_url=web(a.get("item_id")),evidence=lp.relative_to(root).as_posix()))
    return out,diag

def _unique_by_hash(root, filename, expected):
    if not filename or not expected:return None,"MISSING_IDENTITY"
    hits=[]
    for p in root.rglob(filename):
        if p.is_file() and H(p)==expected:hits.append(p)
    if len(hits)!=1:return None,f"IDENTITY_MATCH_COUNT:{len(hits)}"
    return hits[0],None

def v6_kits(root,by):
    out=[]; diag=[]; base=root/"80_CONTROL/PROGRAM/JOBS"
    if not base.exists():return out,diag
    for lp in sorted(base.rglob("USABLE_KIT_LOCATOR.json")):
        tag=lp.parent.name
        try:l=J(lp)
        except Exception:diag.append(f"V6_UNREADABLE_LOCATOR:{tag}");continue
        if l.get("status")!=V6_STATUS:
            diag.append(f"V6_LOCATOR_NOT_USABLE:{tag}:{l.get('status') or 'NO_STATUS'}");continue
        try:
            key=l["course_key"]; kit=l["kit"]; rel=l["release"]; fac=l["factory"]
            kit_sha=B(kit["sha256"]); kit_bytes=int(kit["bytes"]); kit_name=kit["filename"]
            rel_sha=B(rel["sha256"]); rel_bytes=int(rel["bytes"]); rel_name=rel["filename"]
            verdict=fac["verdict"]
            result=fac["result"]; evidence=fac["evidence"]; attestation=fac["attestation"]
        except Exception:
            diag.append(f"V6_LOCATOR_INCOMPLETE:{tag}");continue
        if verdict not in PASS_V6 or not kit_sha or not rel_sha:
            diag.append(f"V6_LOCATOR_BINDING_INVALID:{tag}");continue
        if not item_locator_matches(kit) or not item_locator_matches(rel):
            diag.append(f"V6_ITEM_BINDING_INVALID:{tag}");continue
        kp,kerr=_unique_by_hash(root,kit_name,kit_sha)
        if kerr or not kp or kp.stat().st_size!=kit_bytes:
            diag.append(f"V6_KIT_IDENTITY_INVALID:{tag}:{kerr or 'BYTE_COUNT'}");continue
        rp=lp.parent/rel_name
        if not rp.is_file() or H(rp)!=rel_sha or rp.stat().st_size!=rel_bytes:
            diag.append(f"V6_RELEASE_IDENTITY_INVALID:{tag}");continue
        bound=[]; invalid=False
        for label,node in (("RESULT",result),("EVIDENCE",evidence),("ATTESTATION",attestation)):
            p,err=_unique_by_hash(root,node.get("filename"),B(node.get("sha256")))
            if err or not p:
                diag.append(f"V6_FACTORY_{label}_IDENTITY_INVALID:{tag}:{err or 'NOT_FOUND'}"); invalid=True; break
            bound.append((label,p))
        if invalid:continue
        try:rj=J(bound[0][1])
        except Exception:diag.append(f"V6_FACTORY_RESULT_UNREADABLE:{tag}");continue
        rverdict=rj.get("factory_gate",{}).get("verdict") or rj.get("factoryGate",{}).get("verdict") or rj.get("verdict")
        if rverdict!=verdict:
            diag.append(f"V6_FACTORY_VERDICT_INVALID:{tag}:{rverdict or 'NO_VERDICT'}");continue
        try:
            with zipfile.ZipFile(rp,"r") as z:
                matches=[]
                for n in z.namelist():
                    if n.endswith("/"):continue
                    data=z.read(n)
                    if hashlib.sha256(data).hexdigest()==kit_sha:matches.append(n)
                if len(matches)!=1:
                    diag.append(f"V6_RELEASE_KIT_MATCH_COUNT:{tag}:{len(matches)}");continue
        except Exception:
            diag.append(f"V6_RELEASE_UNREADABLE:{tag}");continue
        try:k=J(kp)
        except Exception:diag.append(f"V6_KIT_UNREADABLE:{tag}");continue
        acts=[a for c in k.get("courses",[]) for a in c.get("activities",[])]; types=Counter(a.get("type","unknown") for a in acts); c=by.get(key,{})
        out.append(dict(course_key=key,course_title=c.get("title") or key,kit_title=k.get("title") or c.get("title") or key,sha256=kit_sha,bytes=kit_bytes,activities=len(acts),types=dict(sorted(types.items())),factory_verdict=verdict,item_id=kit.get("item_id"),web_url=web(kit.get("item_id")),evidence=lp.relative_to(root).as_posix()))
    return out,diag

def kits(root,by):
    legacy,diag=legacy_kits(root,by); v6,v6diag=v6_kits(root,by)
    return legacy+v6,diag+v6diag

CSS="body{font-family:system-ui,sans-serif;max-width:1150px;margin:0 auto;padding:24px;line-height:1.45}code{overflow-wrap:anywhere}.note,.card{border:1px solid #9997;border-radius:10px;padding:14px;margin:14px 0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px}.button{display:inline-block;border:1px solid currentColor;border-radius:8px;padding:8px 12px;text-decoration:none;font-weight:700}.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:850px}th,td{border-bottom:1px solid #9997;padding:9px;text-align:left;vertical-align:top}.muted{opacity:.7}"
def shell(title,body,stamp):return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{CSS}</style></head><body><h1>{html.escape(title)}</h1><p class="muted">Vue humaine dérivée — non autoritaire.</p><div class="note">Les manifests, STATELOG et preuves exactes restent les autorités. Cette vue est régénérable et ne modifie aucun état.</div>{body}<p class="muted"><small>Rafraîchi : {html.escape(stamp)} · <a href="{SOURCE}">générateur canonique</a></small></p></body></html>\n'''

def emit(root,cs,ks,diag,stamp,commit):
    out=root/"05_CATALOGUE"; out.mkdir(parents=True,exist_ok=True); count=Counter(k["course_key"] for k in ks)
    rows=[]
    for c in cs:
        lim=c["error"] or ("; ".join(c["limitations"]) if c["limitations"] else "—")
        rows.append(f'''<tr><td>{html.escape(str(c['title']))}</td><td><code>{html.escape(c['course_key'])}</code></td><td>{html.escape(str(c['academic_year'] or '—'))}</td><td><code>{html.escape(str(c['stage'] or '—'))}/{html.escape(str(c['status'] or '—'))}</code></td><td>{c['revision'] if c['revision'] is not None else '—'}</td><td>{html.escape(lim)}</td><td>{count[c['course_key']]}</td><td><code>{html.escape(c['relative_path'])}</code></td></tr>''')
    body=f'''<p><strong>{len(cs)}</strong> cours canoniques reconstruits.</p><p><a class="button" href="CATALOGUE_KITS.html">Voir les kits disponibles</a></p><div class="wrap"><table><thead><tr><th>Cours</th><th>Course key</th><th>Année</th><th>État</th><th>Rév.</th><th>Limitation</th><th>Kits Factory PASS</th><th>Chemin</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>'''
    ch=out/"CATALOGUE_COURS.html"; ch.write_text(shell("Catalogue des cours LearnIT",body,stamp),encoding="utf-8")
    cards=[]
    for k in ks:
        typ=", ".join(f"{v} {t}" for t,v in k["types"].items()) or "—"; link=f'<a class="button" href="{html.escape(k["web_url"])}">Ouvrir le JSON importable</a>' if k["web_url"] else "Lien OneDrive absent"
        cards.append(f'''<article class="card"><h2>{html.escape(k['kit_title'])}</h2><p><strong>✓ Factory PASS</strong></p><p><strong>Cours :</strong> {html.escape(k['course_title'])}<br><strong>Course key :</strong> <code>{html.escape(k['course_key'])}</code><br><strong>Activités :</strong> {k['activities']} ({html.escape(typ)})<br><strong>Taille :</strong> {k['bytes']} octets</p><p><strong>SHA-256 exact :</strong><br><code>{k['sha256']}</code></p>{link}</article>''')
    intro=f"<p><strong>{len(ks)}</strong> kit(s) dont les bytes exacts sont reliés à une preuve Factory PASS.</p>" if ks else "<p><strong>Aucun kit Factory PASS détecté par cette reconstruction.</strong></p>"
    detail="<details><summary>Diagnostics</summary><ul>"+"".join(f"<li><code>{html.escape(x)}</code></li>" for x in diag)+"</ul></details>" if diag else ""
    kh=out/"CATALOGUE_KITS.html"; kh.write_text(shell("Kits LearnIT disponibles",intro+'<p><a class="button" href="CATALOGUE_COURS.html">Voir tous les cours</a></p><section class="cards">'+"".join(cards)+"</section>"+detail,stamp),encoding="utf-8")
    cp=out/"CATALOGUE_COURS.csv"
    with cp.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f); w.writerow(["title","course_key","academic_year","stage","status","revision","usable_factory_pass_kits","relative_path"])
        for c in cs:w.writerow([c["title"],c["course_key"],c["academic_year"] or "",c["stage"] or "",c["status"] or "",c["revision"] if c["revision"] is not None else "",count[c["course_key"]],c["relative_path"]])
    m={"schema":"learnit.human-navigation.catalogue-manifest.v2","schema_version":2,"authority":False,"view_type":"DERIVED_NON_AUTHORITATIVE","generated_at":stamp,"generator":{"canonical_source":SOURCE,"commit":commit},"course_count":len(cs),"usable_factory_pass_kit_count":len(ks),"courses":[{"course_key":c["course_key"],"title":c["title"],"state":{"stage":c["stage"],"status":c["status"],"revision":c["revision"]},"relative_path":c["relative_path"],"reconstruction_error":c["error"],"usable_factory_pass_kits":count[c["course_key"]]} for c in cs],"usable_kits":[{"course_key":k["course_key"],"sha256":"sha256:"+k["sha256"],"bytes":k["bytes"],"activities":k["activities"],"types":k["types"],"factory_verdict":k["factory_verdict"],"item_id":k["item_id"],"web_url":k["web_url"],"evidence_locator":k["evidence"]} for k in ks],"diagnostics":diag,"outputs":{"course_html":{"file":ch.name,"sha256":"sha256:"+H(ch)},"course_csv":{"file":cp.name,"sha256":"sha256:"+H(cp)},"kit_html":{"file":kh.name,"sha256":"sha256:"+H(kh)}},"stale_view_semantics":"If this view disagrees with canonical manifests, STATELOGs or exact Factory evidence, canonical evidence wins and this view must be rebuilt."}
    (out/"CATALOGUE_MANIFEST.json").write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main():
    a=argparse.ArgumentParser(); a.add_argument("root",nargs="?",type=Path); a.add_argument("--generated-at"); a.add_argument("--generator-commit"); x=a.parse_args(); root=(x.root or Path(__file__).resolve().parent.parent).resolve()
    if not (root/"10_COURSES").exists() or not (root/"80_CONTROL").exists():raise SystemExit(f"Not a Cours_source root: {root}")
    cs=courses(root); ks,d=kits(root,{c["course_key"]:c for c in cs}); stamp=x.generated_at or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"); emit(root,cs,ks,d,stamp,x.generator_commit); print(json.dumps({"course_count":len(cs),"usable_kit_count":len(ks),"diagnostics":d},ensure_ascii=False))
if __name__=="__main__":main()
