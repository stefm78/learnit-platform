#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "contract_css_bundle_report.json"
checks = []


def add(code: str, ok: bool, detail: str = "") -> None:
    checks.append({"code": code, "ok": bool(ok), "detail": detail})


def strip_css(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", "", text)


def delta(text: str) -> int:
    cleaned = strip_css(text)
    return cleaned.count("{") - cleaned.count("}")


manifest = json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))
paths = []
for entry in manifest.get("styles", []):
    if entry.get("path"):
        paths.append(entry["path"])
    paths.extend(entry.get("paths", []))
add("active-style-files-present", bool(paths) and all((ROOT / rel).exists() for rel in paths), str(paths))

cumulative = 0
boundary_rows = []
joined = []
for rel in paths:
    text = (ROOT / rel).read_text(encoding="utf-8")
    file_delta = delta(text)
    cumulative += file_delta
    boundary_rows.append({"path": rel, "delta": file_delta, "cumulative": cumulative})
    joined.append(text)
add("bundle-boundaries-never-negative", all(row["cumulative"] >= 0 for row in boundary_rows), json.dumps(boundary_rows, ensure_ascii=False))
add("bundle-finally-balanced", cumulative == 0 and delta("\n".join(joined)) == 0, json.dumps(boundary_rows, ensure_ascii=False))
add("all-style-owner-files-balanced", all(row["delta"] == 0 for row in boundary_rows), json.dumps(boundary_rows, ensure_ascii=False))
add("no-cross-file-css-fragments", all(row["cumulative"] == 0 for row in boundary_rows), "Every style owner closes its own rules and at-rules.")
qcm_css = (ROOT / "src/styles/parts/64_library_chapter_comfort.css").read_text(encoding="utf-8")
add("qcm-rules-in-balanced-terminal-file", ".activity-qcm .choice::before" in qcm_css and "@media (hover:none), (pointer:coarse)" in qcm_css and delta(qcm_css) == 0, "touch-safe QCM rules are contained in the balanced library/chapter bundle")

ok = all(item["ok"] for item in checks)
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps({"schema": "learnit.rc514.css_bundle_integrity.v2", "ok": ok, "checks": checks}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"ok": ok, "report": str(REPORT.relative_to(ROOT)), "passed": sum(item["ok"] for item in checks), "total": len(checks)}, ensure_ascii=False, indent=2))
raise SystemExit(0 if ok else 1)
