#!/usr/bin/env python3
"""Deterministic validator for opt-in learnit.kit.v6 mastery packages."""
from __future__ import annotations
import argparse, copy, sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from authoring.v5 import validate_kit as v5

SCHEMA_PATH=ROOT/"contracts/learnit-kit-v6.schema.json"
Report=v5.Report
load=v5.load
digest=v5.digest
diagnostic=v5.diagnostic
fill_new_digests=v5.fill_new_digests
cross_file_errors=v5.cross_file_errors
render_json=v5.render_json
render_human=v5.render_human

class V6ValidationError(ValueError): pass

def _v6_errors(document:dict[str,Any])->list[str]:
    errors=[]
    for ci,course in enumerate(document.get("courses",[])):
        if not isinstance(course,dict): continue
        for ai,activity in enumerate(course.get("activities",[])):
            if not isinstance(activity,dict): continue
            ap=f"$.courses[{ci}].activities[{ai}]"
            if activity.get("assessmentRole")=="validation":
                if len(activity.get("objectiveIds",[]))!=1:
                    errors.append(diagnostic(ap+".objectiveIds","V6 validation must target exactly one objective",activity.get("objectiveIds")))
                if activity.get("validationSlot") not in {"A","B"}:
                    errors.append(diagnostic(ap+".validationSlot","V6 validation requires slot A or B",activity.get("validationSlot")))
            elif "validationSlot" in activity:
                errors.append(diagnostic(ap+".validationSlot","validationSlot is validation-only",activity.get("validationSlot")))
            if activity.get("type")!="productive": continue
            parts=activity.get("parts",[])
            evaluators=activity.get("scoring",{}).get("evaluators",[])
            part_by_id={p.get("partId"):p for p in parts if isinstance(p,dict)}
            seen=set()
            for ei,evaluator in enumerate(evaluators):
                if not isinstance(evaluator,dict): continue
                ep=f"{ap}.scoring.evaluators[{ei}]"
                pid=evaluator.get("partId")
                if pid in seen: errors.append(diagnostic(ep+".partId","duplicate evaluator partId",pid))
                seen.add(pid)
                part=part_by_id.get(pid)
                if part is None:
                    errors.append(diagnostic(ep+".partId","evaluator references unknown productive part",pid)); continue
                expected={"numeric-tolerance":"number","canonical-expression-set":"expression","required-concepts":"text"}.get(evaluator.get("kind"))
                if expected!=part.get("responseKind"):
                    errors.append(diagnostic(ep+".kind","evaluator kind does not match part responseKind",evaluator.get("kind")))
            if set(part_by_id)!=seen:
                errors.append(diagnostic(ap+".scoring.evaluators","every productive part requires exactly one evaluator",sorted(set(part_by_id)-seen)))
    return errors

def validate(path:Path,document:dict[str,Any],schema:dict[str,Any])->Report:
    report=Report(path)
    report.errors.extend(v5.v4.v2.schema_errors(document,schema))
    if isinstance(document,dict):
        v5.v4.semantic_checks(document,report)
        v5._check_v5_extensions(document,report)
        report.errors.extend(_v6_errors(document))
        v5.v4.add_digest_records(document,report)
    return report

def parser()->argparse.ArgumentParser:
    p=argparse.ArgumentParser(description="Validate explicit learnit.kit.v6 packages.")
    p.add_argument("kits",nargs="+",type=Path);p.add_argument("--schema",type=Path,default=SCHEMA_PATH)
    p.add_argument("--write-digests",action="store_true");p.add_argument("--show-canonical",action="store_true")
    p.add_argument("--format",choices=("human","json"),default="human");return p

def main(argv:list[str]|None=None)->int:
    args=parser().parse_args(argv)
    try:
        schema=load(args.schema)
        if not isinstance(schema,dict): raise V6ValidationError("schema root must be an object")
        documents=[];write_errors=[]
        for path in args.kits:
            document=load(path)
            if not isinstance(document,dict): raise V6ValidationError(f"{path}: kit root must be a JSON object")
            if args.write_digests:
                document=copy.deepcopy(document);write_errors += [f"{path}: {error}" for error in fill_new_digests(document)]
            documents.append((path,document))
        reports=[validate(path,document,schema) for path,document in documents]
        cross=cross_file_errors(reports)+write_errors
        if args.write_digests and all(report.ok for report in reports) and not cross:
            import json
            for path,document in documents:path.write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(render_json(reports,cross,args.show_canonical) if args.format=="json" else render_human(reports,cross,args.show_canonical))
        return 0 if all(report.ok for report in reports) and not cross else 1
    except (v5.v4.v2.ToolError,V6ValidationError) as exc:
        print(f"TOOL ERROR: {exc}",file=sys.stderr);return 2
if __name__=="__main__": raise SystemExit(main())
