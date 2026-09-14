#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

TARGET="TARGET_COVERAGE"
REP="REPRESENTED"
EXC="EXPLICITLY_EXCLUDED"
ALLOWED_ROLES={"TARGET_COVERAGE","CONTEXT_ONLY","PREREQUISITE","ASSESSMENT_SOURCE","OUT_OF_SCOPE"}

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def knowledge_refs(knowledge):
    refs=set()
    for concept in knowledge.get("concepts",[]):
        cid=concept.get("id")
        if not isinstance(cid,str) or not cid:
            continue
        refs.add(cid)
        for claim in concept.get("claims",[]):
            q=claim.get("id")
            if isinstance(q,str) and q:
                refs.add(f"{cid}#{q}")
    return refs

def check(ledger, knowledge):
    errors=[]
    refs=knowledge_refs(knowledge)
    seen=set()
    for i,item in enumerate(ledger.get("items",[])):
        p=f"items[{i}]"
        sid=item.get("sourceItemId")
        if not isinstance(sid,str) or not sid:
            errors.append({"code":"SOURCE_ITEM_ID_REQUIRED","path":p})
            continue
        if sid in seen:
            errors.append({"code":"DUPLICATE_SOURCE_ITEM","path":p,"sourceItemId":sid})
        seen.add(sid)
        role=item.get("scopeRole")
        if role not in ALLOWED_ROLES:
            errors.append({"code":"INVALID_SCOPE_ROLE","path":p,"sourceItemId":sid})
            continue
        if role != TARGET:
            continue
        disp=item.get("coverageDisposition")
        if disp not in {REP,EXC}:
            errors.append({"code":"TARGET_DISPOSITION_REQUIRED","path":p,"sourceItemId":sid})
            continue
        if disp == REP:
            krefs=item.get("knowledgeRefs")
            if not isinstance(krefs,list) or not krefs:
                errors.append({"code":"KNOWLEDGE_REF_REQUIRED","path":p,"sourceItemId":sid})
                continue
            for ref in krefs:
                if ref not in refs:
                    errors.append({"code":"KNOWLEDGE_REF_NOT_FOUND","path":p,"sourceItemId":sid,"knowledgeRef":ref})
        else:
            reason=item.get("reason")
            if not isinstance(reason,str) or not reason.strip():
                errors.append({"code":"EXCLUSION_REASON_REQUIRED","path":p,"sourceItemId":sid})
    return {"schema":"learnit.coverage-check.result.v1-experimental",
            "result":"PASS" if not errors else "FAIL","errors":errors}

def compare(ledger, knowledge):
    refs=knowledge_refs(knowledge)
    rows=[]
    for item in ledger.get("items",[]):
        if item.get("scopeRole") != TARGET:
            continue
        if item.get("coverageDisposition")==EXC and isinstance(item.get("reason"),str) and item["reason"].strip():
            state="EXPLICITLY_EXCLUDED"
        elif item.get("coverageDisposition")==REP and item.get("knowledgeRefs") and all(r in refs for r in item["knowledgeRefs"]):
            state="REPRESENTED"
        else:
            state="MISSING_SILENTLY"
        rows.append({"sourceItemId":item.get("sourceItemId"),"state":state,
                     "knowledgeRefs":item.get("knowledgeRefs",[])})
    return {"schema":"learnit.coverage-loss-report.v1-experimental",
            "summary":{
                "REPRESENTED":sum(r["state"]=="REPRESENTED" for r in rows),
                "EXPLICITLY_EXCLUDED":sum(r["state"]=="EXPLICITLY_EXCLUDED" for r in rows),
                "MISSING_SILENTLY":sum(r["state"]=="MISSING_SILENTLY" for r in rows)},
            "items":rows}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("ledger"); ap.add_argument("knowledge")
    ap.add_argument("--compare",action="store_true")
    args=ap.parse_args()
    l,k=load(args.ledger),load(args.knowledge)
    result=compare(l,k) if args.compare else check(l,k)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":")))
    raise SystemExit(0 if args.compare or result["result"]=="PASS" else 1)
if __name__=="__main__": main()
