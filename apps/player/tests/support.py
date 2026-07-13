from __future__ import annotations
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]

def load_manifest() -> dict:
    return json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))

def active_script_paths() -> list[str]:
    out=[]
    for entry in sorted(load_manifest().get("scripts", []), key=lambda x: x.get("order", 0)):
        if entry.get("path"):
            out.append(entry["path"])
        else:
            out.extend(entry.get("paths", []))
    return out

def active_style_paths() -> list[str]:
    out=[]
    for entry in load_manifest().get("styles", []):
        if entry.get("path"):
            out.append(entry["path"])
        else:
            out.extend(entry.get("paths", []))
    return out

def load_runtime_core() -> str:
    chunks=[]
    for entry in sorted(load_manifest().get("scripts", []), key=lambda x: x.get("order", 0)):
        paths = entry.get("paths") if entry.get("bundle") == "runtime_core" else None
        if paths:
            for rel in paths:
                chunks.append((ROOT / rel).read_text(encoding="utf-8"))
    if not chunks:
        legacy = ROOT / "src/scripts/core/00_app_runtime_monolith.js"
        if legacy.exists():
            return legacy.read_text(encoding="utf-8")
    return "\n".join(chunks)
