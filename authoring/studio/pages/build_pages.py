#!/usr/bin/env python3
"""Build a static GitHub Pages surface for the frozen M3.0 authoring core."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "authoring" / "studio" / "web"
PAGES = ROOT / "authoring" / "studio" / "pages"

AUTHORITY = {
    "authoring/studio/core.py": ROOT / "authoring" / "studio" / "core.py",
    "authoring/v2/validate_kit.py": ROOT / "authoring" / "v2" / "validate_kit.py",
    "authoring/v2/atlas/validate_atlas_content.py": ROOT / "authoring" / "v2" / "atlas" / "validate_atlas_content.py",
    "contracts/learnit-kit-v2.schema.json": ROOT / "contracts" / "learnit-kit-v2.schema.json",
}

UI_FILES = ("index.html", "studio.css", "studio.js")
INJECTION = '  <script src="pages-bootstrap.js"></script>\n  <script src="studio.js"></script>'
SOURCE_SCRIPT = '  <script src="studio.js"></script>'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> dict:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    for name in UI_FILES:
        source = WEB / name
        if not source.is_file():
            raise SystemExit(f"missing frozen UI source: {source}")
        shutil.copy2(source, output / name)

    index = (output / "index.html").read_text(encoding="utf-8")
    if index.count(SOURCE_SCRIPT) != 1:
        raise SystemExit("frozen index script boundary changed")
    (output / "index.html").write_text(index.replace(SOURCE_SCRIPT, INJECTION), encoding="utf-8")
    shutil.copy2(PAGES / "pages-bootstrap.js", output / "pages-bootstrap.js")

    authority_root = output / "_authority"
    for relative, source in AUTHORITY.items():
        target = authority_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    evidence = {
        "schema": "learnit.atlas.m3.pages.bundle.v1",
        "mode": "STATIC_BROWSER_PYTHON_AUTHORITY",
        "pyodideVersion": "0.29.4",
        "pyodideBaseUrl": "https://cdn.jsdelivr.net/pyodide/v0.29.4/full/",
        "authoringStorageNamespace": "learnit.authoring.m3.v1",
        "externalAuthoringDataTransfer": False,
        "authority": {relative: {"sha256": sha256(source), "bytes": source.stat().st_size}
                      for relative, source in sorted(AUTHORITY.items())},
        "frozenUi": {name: {"sha256": sha256(WEB / name), "bytes": (WEB / name).stat().st_size}
                     for name in UI_FILES},
    }
    (output / "pages-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    evidence = build(args.output.resolve())
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
