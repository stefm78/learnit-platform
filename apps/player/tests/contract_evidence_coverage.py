#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "dev/checks_registry.json").read_text(encoding="utf-8"))
MAP = json.loads((ROOT / "dev/evidence_coverage.json").read_text(encoding="utf-8"))
active = set(REGISTRY.get("mandatory", [])) | set(REGISTRY.get("browser", []))
mapped = {item for items in MAP.get("surfaces", {}).values() for item in items}
checks = [
    {"code": "all-mapped-tests-exist", "ok": all((ROOT / item).exists() for item in mapped)},
    {"code": "all-active-tests-mapped", "ok": active <= mapped, "detail": sorted(active - mapped)},
    {"code": "no-stale-mapped-tests", "ok": mapped <= active, "detail": sorted(mapped - active)},
    {"code": "human-authority-explicit", "ok": bool(MAP.get("human_only_or_partially_automated")) and "RC715" in MAP.get("policy", "") and "human" in MAP.get("policy", "").lower()},
]
ok = all(check["ok"] for check in checks)
out = ROOT / "reports/contract_evidence_coverage_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({"schema": "learnit.rc712.evidence_coverage_gate.v1", "ok": ok, "checks": checks, "surfaces": MAP.get("surfaces", {})}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"ok": ok, "passed": sum(c["ok"] for c in checks), "total": len(checks), "report": str(out.relative_to(ROOT))}, ensure_ascii=False, indent=2))
raise SystemExit(0 if ok else 1)
