#!/usr/bin/env python3
"""Bounded V6 factory admission for the P2R3ENGINE successor contract."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from authoring.factory import factory_gate as factory
from authoring.v2.atlas import pedagogical_quality as legacy_quality
from authoring.v5 import authoring_policy
from authoring.v6 import validate_kit as v6

PASS="PASS_AI_KIT_FACTORY_V6_R1"
HOLD="HOLD_V6_FACTORY_ADMISSION"

def run_gate(kit_path:Path,brief_path:Path,source_specs:list[str])->dict[str,Any]:
    context=factory.build_context(kit_path,brief_path,source_specs)
    kit,_=factory.load_json(kit_path,"kit")
    if not isinstance(kit,dict) or kit.get("contract")!="learnit.kit.v6":
        return {"schema":"learnit.atlas.ai_kit_factory_v6_evidence.r1","verdict":HOLD,"reasons":["V6_CONTRACT_REQUIRED"]}
    report=v6.validate(Path("<factory-v6>"),kit,v6.load(v6.SCHEMA_PATH))
    policy=authoring_policy.analyze(kit)
    diagnostics=legacy_quality._quality_diagnostics_v4(kit) if report.ok else []
    counts=legacy_quality._counts(diagnostics) if report.ok else {"blocking":len(report.errors),"warning":0,"advice":0}
    band=legacy_quality._band(counts["warning"],counts["advice"],counts["blocking"]) if report.ok else "BLOCKED"
    reasons=[]
    if not report.ok: reasons.append("CANONICAL_V6_INVALID")
    if report.ok and band not in {"STRONG","EXCELLENT_BY_PROFILE"}: reasons.append("PEDAGOGICAL_QUALITY_BAND:"+band)
    if policy["verdict"]!=authoring_policy.PASS: reasons.extend(policy["reasons"])
    return {"schema":"learnit.atlas.ai_kit_factory_v6_evidence.r1","profile":"atlas.ai-kit-factory.v6-r1","context":context,
            "canonicalValid":report.ok,"pedagogicalQuality":{"qualityBand":band,"counts":counts},
            "authoringPolicy":policy,"verdict":PASS if not reasons else HOLD,"reasons":sorted(set(reasons))}

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--kit",type=Path,required=True);p.add_argument("--brief",type=Path,required=True);p.add_argument("--source",action="append",default=[])
    a=p.parse_args(argv)
    try:e=run_gate(a.kit,a.brief,a.source)
    except Exception as exc:e={"schema":"learnit.atlas.ai_kit_factory_v6_evidence.r1","verdict":HOLD,"reasons":[str(exc)]}
    print(factory.canonical_output(e),end="");return 0 if e["verdict"]==PASS else 4
if __name__=="__main__":raise SystemExit(main())
