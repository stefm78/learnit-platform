#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dev"))
from authoring_alignment import run  # noqa: E402

report = run()
print(json.dumps({"ok": report["ok"], "passed": sum(row["ok"] for row in report["checks"]), "total": len(report["checks"]), "report": "reports/authoring_alignment_report.json"}, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["ok"] else 1)
