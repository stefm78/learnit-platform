#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

from support import ROOT, active_script_paths, active_style_paths, load_manifest

REPORT = ROOT / "reports" / "contract_source_tree_report.json"
GENERATED_DIRS = {"dist", "reports", "release", "release_baseline", "__pycache__", ".pytest_cache", ".git"}


def runtime_fingerprint() -> str:
    manifest = load_manifest()
    paths = [manifest["template"], *active_script_paths(), *active_style_paths()]
    digest = hashlib.sha256()
    for rel in sorted(set(paths)):
        digest.update(rel.encode("utf-8") + b"\0" + (ROOT / rel).read_bytes())
    return digest.hexdigest()


def canonical_css(text: str) -> str:
    out: list[str] = []
    i = 0
    quote: str | None = None
    while i < len(text):
        if quote:
            char = text[i]
            out.append(char)
            if char == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if char == quote:
                quote = None
            i += 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end < 0 else end + 2
            continue
        char = text[i]
        if char in {"'", '"'}:
            quote = char
            out.append(char)
        elif not char.isspace():
            out.append(char)
        i += 1
    return "".join(out)


def css_semantic_fingerprint(config: dict | None = None) -> str:
    eq = (config or {}).get("baseline_equivalence", {})
    ignored = set(eq.get("ignored_style_paths", []))
    text = "".join((ROOT / rel).read_text(encoding="utf-8") for rel in active_style_paths() if rel not in ignored)
    return hashlib.sha256(canonical_css(text).encode("utf-8")).hexdigest()


def normalized_runtime_js_fingerprint(config: dict) -> str:
    eq = config.get("baseline_equivalence", {})
    digest = hashlib.sha256()
    ignored = set(eq.get("ignored_script_paths", []))
    for rel in active_script_paths():
        if rel in ignored:
            continue
        text = (ROOT / rel).read_text(encoding="utf-8")
        text = text.replace(str(eq.get("current_version_label", "")), str(eq.get("baseline_version_label", "")))
        text = text.replace(str(eq.get("current_build", "")), str(eq.get("baseline_build", "")))
        digest.update(rel.encode("utf-8") + b"\0" + text.encode("utf-8"))
    return digest.hexdigest()


def main() -> int:
    registry = json.loads((ROOT / "dev" / "checks_registry.json").read_text(encoding="utf-8"))
    checks: list[dict] = []

    def add(code: str, ok: bool, detail: str = "") -> None:
        checks.append({"code": code, "ok": bool(ok), "detail": detail})

    working = [
        path for path in ROOT.rglob("*")
        if path.is_file() and not any(part in GENERATED_DIRS for part in path.relative_to(ROOT).parts)
    ]
    docs = [path for path in (ROOT / "docs").glob("*.md") if path.is_file()]
    source_files = [path for path in (ROOT / "src").rglob("*") if path.is_file()]
    manifested = {ROOT / load_manifest()["template"]}
    manifested.update(ROOT / rel for rel in active_script_paths() + active_style_paths())
    active_tests = set(registry.get("mandatory", []) + registry.get("browser", []))
    test_files = {
        str(path.relative_to(ROOT)) for path in (ROOT / "tests").glob("*.py")
        if path.name != "support.py"
    }

    add("working-file-budget", len(working) <= 150, str(len(working)))
    add("canonical-doc-budget", sorted(path.name for path in docs) == ["ENGINEERING.md", "HUMAN_VALIDATION.md"], str(sorted(path.name for path in docs)))
    add("no-history-directory", not (ROOT / "history").exists())
    add("no-legacy-or-quarantine", not (ROOT / "legacy").exists() and not (ROOT / "src/scripts/enhancements_quarantine").exists())
    add("no-inactive-monoliths", not (ROOT / "src/scripts/core/00_app_runtime_monolith.js").exists() and not (ROOT / "src/styles/app.css").exists())
    add("all-src-files-manifest-owned", set(source_files) == manifested, f"unowned={sorted(str(p.relative_to(ROOT)) for p in set(source_files)-manifested)}")
    add("all-tests-registered", test_files == active_tests, f"unregistered={sorted(test_files-active_tests)}, missing={sorted(active_tests-test_files)}")
    config = json.loads((ROOT / 'dev' / 'release_config.json').read_text(encoding='utf-8'))
    expected_fingerprint = str(config.get('runtime_fingerprint') or '')
    current_fingerprint = runtime_fingerprint()
    add("runtime-fingerprint-declared", bool(expected_fingerprint) and current_fingerprint == expected_fingerprint, current_fingerprint)
    equivalence = config.get("baseline_equivalence", {})
    css_fp = css_semantic_fingerprint(config)
    js_fp = normalized_runtime_js_fingerprint(config)
    add("protected-css-semantics-preserved-outside-authorized-style-files", css_fp == equivalence.get("css_semantic_sha256"), css_fp)
    add("protected-runtime-js-preserved-outside-authorized-owner-files", js_fp == equivalence.get("runtime_js_normalized_sha256"), js_fp)
    add("generated-dirs-gitignored", all(name + "/" in (ROOT / ".gitignore").read_text(encoding="utf-8") for name in ["dist", "reports", "release"]))

    ok = all(item["ok"] for item in checks)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"schema": "learnit.rc712.source_tree.v1", "ok": ok, "checks": checks}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "passed": sum(item["ok"] for item in checks), "total": len(checks), "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
