#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path
import hashlib
import json
import os
import re

ROOT = Path(__file__).resolve().parent


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_build_time(manifest: dict, explicit: str | None) -> str:
    fixed = explicit or os.environ.get("LEARNIT_BUILD_TIME") or os.environ.get("SOURCE_DATE_EPOCH")
    if fixed:
        if fixed.isdigit():
            return datetime.fromtimestamp(int(fixed), UTC).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
        return fixed
    configured = manifest.get("build_timestamp")
    if not configured:
        raise RuntimeError("source_manifest.json must define build_timestamp for a deterministic default build")
    return str(configured)



def minify_css_conservative(text: str) -> str:
    """Remove comments and non-semantic whitespace without changing token boundaries.

    This deliberately avoids aggressive value rewriting (notably calc() operators,
    custom properties and quoted content). It is deterministic and dependency-free.
    """
    out: list[str] = []
    i = 0
    quote: str | None = None
    pending_space = False
    no_space_before = set("{}:;,>")
    no_space_after = set("{}:;,>")
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if quote:
            out.append(char)
            if char == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if char == quote:
                quote = None
            i += 1
            continue
        if char == "/" and nxt == "*":
            end = text.find("*/", i + 2)
            pending_space = True
            i = len(text) if end < 0 else end + 2
            continue
        if char in {"'", '"'}:
            if pending_space and out and out[-1] not in no_space_after:
                out.append(" ")
            pending_space = False
            quote = char
            out.append(char)
            i += 1
            continue
        if char.isspace():
            pending_space = True
            i += 1
            continue
        if pending_space and out and out[-1] not in no_space_after and char not in no_space_before:
            out.append(" ")
        pending_space = False
        if char in no_space_before and out and out[-1] == " ":
            out.pop()
        out.append(char)
        i += 1
    return "".join(out).strip()

def main() -> int:
    parser = ArgumentParser(description="Build the single-file Learn-it application from manifest-owned source.")
    parser.add_argument("--output", default="dist/learnit.html", help="Output HTML path, relative to repository root by default.")
    parser.add_argument("--report", default="reports/build_report.json", help="Build report path.")
    parser.add_argument("--build-time", default=None, help="Explicit ISO timestamp or epoch; defaults to manifest build_timestamp.")
    args = parser.parse_args()

    manifest_path = ROOT / "source_manifest.json"
    manifest = read_json(manifest_path)
    template = (ROOT / manifest["template"]).read_text(encoding="utf-8")

    def read_rel(rel: str) -> str:
        path = ROOT / rel
        if not path.exists():
            raise FileNotFoundError(rel)
        return path.read_text(encoding="utf-8").rstrip()

    def style_entries() -> list[str]:
        chunks: list[str] = []
        for entry in manifest.get("styles", []):
            if entry.get("path"):
                chunks.append(f"/* source: {entry['path']} */\n{read_rel(entry['path'])}")
            else:
                chunks.append(f"/* bundle: {entry.get('bundle', 'style_bundle')} */")
                for rel in entry.get("paths", []):
                    chunks.append(f"/* source: {rel} */\n{read_rel(rel)}")
        return chunks

    def script_entries() -> list[str]:
        chunks: list[str] = []
        for entry in sorted(manifest.get("scripts", []), key=lambda item: item.get("order", 0)):
            if entry.get("path"):
                chunks.append(f'<script data-source="{entry["path"]}">\n{read_rel(entry["path"])}\n</script>')
            else:
                bundle_name = entry.get("bundle", "script_bundle")
                body = [f"/* bundle: {bundle_name} */"]
                for rel in entry.get("paths", []):
                    body.append(f"\n/* source: {rel} */\n{read_rel(rel)}")
                chunks.append(f'<script data-bundle="{bundle_name}">\n{"".join(body).rstrip()}\n</script>')
        return chunks

    def contract_entries() -> list[str]:
        chunks: list[str] = []
        for entry in manifest.get("contracts", []):
            rel = entry["path"]
            payload = read_json(ROOT / rel)
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("</", "<\\/")
            chunks.append(f'<script type="application/json" id="{entry["dom_id"]}" data-source="{rel}" data-sha256="{sha256(ROOT / rel)}">{body}</script>')
        return chunks

    style_source = "\n\n".join(style_entries())
    compiled_style = minify_css_conservative(style_source)
    html = template.replace("{{STYLES_FROM_MANIFEST}}", compiled_style)
    html = html.replace("{{CONTRACTS_FROM_MANIFEST}}", "\n".join(contract_entries()))
    html = html.replace("{{SCRIPTS_FROM_MANIFEST}}", "\n\n".join(script_entries()))
    unresolved = sorted(set(re.findall(r"\{\{[^}]+\}\}", html)))
    if unresolved:
        raise RuntimeError(f"unresolved build placeholders: {unresolved}")

    built_at = resolve_build_time(manifest, args.build_time)
    stamp = f"<!-- Built from {manifest.get('rc', 'RC')} modular source at {built_at} -->"
    html = html.replace("</head>", f"  {stamp}\n</head>", 1)

    out = Path(args.output)
    if not out.is_absolute():
        out = ROOT / out
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = ROOT / report_path
    out.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    manifest_script_paths: list[str] = []
    for entry in sorted(manifest.get("scripts", []), key=lambda item: item.get("order", 0)):
        if entry.get("path"):
            manifest_script_paths.append(entry["path"])
        else:
            manifest_script_paths.extend(entry.get("paths", []))

    report = {
        "schema": f"learnit.{str(manifest.get('rc', 'rc')).lower()}.build_report.v2",
        "ok": True,
        "deterministicDefault": True,
        "builtAt": built_at,
        "output": str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else out.name,
        "bytes": out.stat().st_size,
        "sha256": sha256(out),
        "sourceStyleBytes": len(style_source.encode("utf-8")),
        "compiledStyleBytes": len(compiled_style.encode("utf-8")),
        "styleSavingsBytes": len(style_source.encode("utf-8")) - len(compiled_style.encode("utf-8")),
        "styleCount": html.count("<style>"),
        "scriptStartCount": len(re.findall(r"<script(?:\s|>)", html)),
        "scriptEndCount": len(re.findall(r"</script>", html)),
        "manifestScriptCount": len(manifest_script_paths),
        "sourceManifestSha256": sha256(manifest_path),
        "releaseConfigSha256": manifest.get("release_config_sha256", ""),
        "manifestOwnsAllScripts": True,
        "styleBundleCount": sum(1 for entry in manifest.get("styles", []) if entry.get("bundle")),
        "scriptBundleCount": sum(1 for entry in manifest.get("scripts", []) if entry.get("bundle")),
        "unresolvedPlaceholders": unresolved,
        "contractCount": len(manifest.get("contracts", [])),
        "contracts": [{"path": entry["path"], "domId": entry["dom_id"], "sha256": sha256(ROOT / entry["path"])} for entry in manifest.get("contracts", [])],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
