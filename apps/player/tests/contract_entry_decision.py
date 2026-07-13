#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

from support import ROOT

MODEL = ROOT / "src/learning/session_mode_model.js"
REPORT = ROOT / "reports/contract_entry_decision_report.json"

node = f"""
global.window=global;
window.LearnItRemediationModel={{buildDuePlan:()=>({{queue:[]}})}};
eval(require('fs').readFileSync({json.dumps(str(MODEL))},'utf8'));
const M=window.LearnItSessionModeModel;
const course={{activities:[
  {{id:'fc',type:'flashcard',objective:'Définir',assessment_role:'practice'}},
  {{id:'qv',type:'qcm',objective:'Valider',assessment_role:'validation'}},
  {{id:'qd',type:'qcm',objective:'Diagnostiquer',assessment_role:'diagnostic'}},
  {{id:'or',type:'order',objective:'Méthode',assessment_role:'remediation'}},
  {{id:'ma',type:'matching',objective:'Associer',assessment_role:'practice'}}
]}};
const allCorrect=Object.fromEntries(course.activities.map(a=>[a.id,{{seen:true,correct:true}}]));
const lowComplete=Object.fromEntries(course.activities.map((a,i)=>[a.id,{{seen:true,correct:i<2}}]));
const scenarios={{
  new:M.entryRecommendation(course,{{}},{{}}),
  active:M.entryRecommendation(course,{{qv:{{seen:true,correct:false,review:true}}}},{{status:'active',mode:'training',currentIndex:1,queue:['qv','ma']}}),
  review:M.entryRecommendation(course,{{qv:{{seen:true,correct:false,review:true,failureStreak:1}}}},{{}}),
  ready:M.entryRecommendation(course,allCorrect,{{}}),
  inProgress:M.entryRecommendation(course,{{qd:{{seen:true,correct:true}}}},{{}}),
  lowComplete:M.entryRecommendation(course,lowComplete,{{}}),
  activePrecedence:M.entryRecommendation(course,allCorrect,{{status:'active',mode:'review',currentIndex:0,queue:['qv']}}),
  reviewPrecedence:M.entryRecommendation(course,{{...allCorrect,qv:{{seen:true,correct:false,review:true,failureStreak:1}}}},{{}})
}};
const policies=Object.fromEntries(M.PUBLIC_MODE_IDS.map(id=>[id,M.resolve(id)]));
console.log(JSON.stringify({{scenarios,policies}}));
"""
proc = subprocess.run(["node", "-e", node], cwd=ROOT, capture_output=True, text=True)
checks: list[dict] = []

def add(code: str, ok: bool, detail="") -> None:
    checks.append({"code": code, "ok": bool(ok), "detail": detail})

if proc.returncode != 0:
    add("model-executes", False, (proc.stderr or proc.stdout)[-2000:])
    payload = {"scenarios": {}, "policies": {}}
else:
    add("model-executes", True)
    payload = json.loads(proc.stdout)

s = payload.get("scenarios", {})
p = payload.get("policies", {})
expected = {
    "new": ("new", "discovery", "diagnostic"),
    "active": ("active", "training", None),
    "review": ("review", "review", "training"),
    "ready": ("ready-to-validate", "validation", "training"),
    "inProgress": ("in-progress", "training", "diagnostic"),
    "lowComplete": ("in-progress", "training", "diagnostic"),
    "activePrecedence": ("active", "review", None),
    "reviewPrecedence": ("review", "review", "training"),
}
for name, (state, mode, secondary_mode) in expected.items():
    row = s.get(name, {})
    actual_secondary = (row.get("secondary") or {}).get("mode")
    add(
        f"scenario-{name}",
        row.get("state") == state and row.get("mode") == mode and actual_secondary == secondary_mode,
        {"state": row.get("state"), "mode": row.get("mode"), "secondary": actual_secondary},
    )

add(
    "one-primary-at-most-one-secondary",
    all(row.get("primaryLabel") and (row.get("secondary") is None or isinstance(row.get("secondary"), dict)) for row in s.values()),
)
add(
    "diagnostic-validation-boundary-explicit",
    all("Diagnostic au début" in row.get("boundaryNote", "") and "Validation à la fin" in row.get("boundaryNote", "") for row in s.values()),
)
add(
    "assessment-boundary-policy",
    p.get("diagnostic", {}).get("assessment") is True
    and p.get("diagnostic", {}).get("recordProgress") is False
    and p.get("validation", {}).get("assessment") is True
    and p.get("validation", {}).get("recordProgress") is True
    and p.get("diagnostic", {}).get("feedbackTiming") == "deferred"
    and p.get("validation", {}).get("feedbackTiming") == "deferred",
)
add(
    "practice-modes-immediate",
    all(p.get(mode, {}).get("feedbackTiming") == "immediate" and p.get(mode, {}).get("recordProgress") is True for mode in ["discovery", "training", "review"]),
)

ok = all(check["ok"] for check in checks)
report = {
    "schema": "learnit.rc659.entry_decision_contract.v1",
    "ok": ok,
    "policy": "Pure decision-contract evidence remains the policy source; RC658/RC659 only change its visible presentation and accessibility, not the mode decisions.",
    "checks": checks,
    "scenarios": s,
    "policies": p,
}
REPORT.parent.mkdir(exist_ok=True)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"ok": ok, "passed": sum(c["ok"] for c in checks), "total": len(checks), "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
sys.exit(0 if ok else 1)
