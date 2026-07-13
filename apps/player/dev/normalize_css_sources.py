#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import re

import tinycss2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "css_normalization_report.json"
CONTEXT_AT_RULES = {"media", "supports", "layer", "container", "scope", "document"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def style_paths() -> list[str]:
    manifest = json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))
    result: list[str] = []
    for entry in manifest.get("styles", []):
        if entry.get("path"):
            result.append(entry["path"])
        result.extend(entry.get("paths", []))
    return result


def normalize_token_text(value: str) -> str:
    return " ".join(value.split())


def main() -> int:
    parser = ArgumentParser(description="Remove provably shadowed CSS declarations and normalize excessive indentation.")
    parser.add_argument("--write", action="store_true", help="Write normalized sources. Default is dry-run audit.")
    parser.add_argument("--indent-cap", type=int, default=2, choices=range(0, 9))
    args = parser.parse_args()

    paths = style_paths()
    texts = {rel: (ROOT / rel).read_text(encoding="utf-8") for rel in paths}

    chunks: list[str] = []
    file_ranges: list[tuple[int, int, str]] = []
    offset = 0
    for index, rel in enumerate(paths):
        text = texts[rel]
        start = offset
        chunks.append(text)
        offset += len(text)
        file_ranges.append((start, offset, rel))
        if index < len(paths) - 1:
            chunks.append("\n\n")
            offset += 2
    css = "".join(chunks)

    line_starts = [0]
    line_starts.extend(match.end() for match in re.finditer("\n", css))

    def line_col_offset(line: int, column: int) -> int:
        return line_starts[line - 1] + column - 1

    def file_position(absolute_offset: int) -> tuple[str, int]:
        for start, end, rel in file_ranges:
            if start <= absolute_offset < end:
                return rel, absolute_offset - start
        raise ValueError(f"offset is outside style files: {absolute_offset}")

    def declaration_end(start: int) -> int:
        index = start
        quote: str | None = None
        in_comment = False
        parens = 0
        brackets = 0
        while index < len(css):
            char = css[index]
            nxt = css[index + 1] if index + 1 < len(css) else ""
            if in_comment:
                if char == "*" and nxt == "/":
                    in_comment = False
                    index += 2
                    continue
                index += 1
                continue
            if quote:
                if char == "\\":
                    index += 2
                    continue
                if char == quote:
                    quote = None
                index += 1
                continue
            if char == "/" and nxt == "*":
                in_comment = True
                index += 2
                continue
            if char in {"'", '"'}:
                quote = char
                index += 1
                continue
            if char == "(":
                parens += 1
            elif char == ")":
                parens = max(0, parens - 1)
            elif char == "[":
                brackets += 1
            elif char == "]":
                brackets = max(0, brackets - 1)
            elif parens == 0 and brackets == 0 and char == ";":
                return index + 1
            elif parens == 0 and brackets == 0 and char == "}":
                return index
            index += 1
        return index

    declarations: list[dict] = []

    def walk(nodes: list, context: tuple = ()) -> None:
        for node in nodes:
            if node.type == "qualified-rule":
                selector = normalize_token_text(tinycss2.serialize(node.prelude))
                for declaration in tinycss2.parse_declaration_list(node.content, skip_whitespace=True, skip_comments=True):
                    if declaration.type != "declaration":
                        continue
                    property_name = declaration.name if declaration.name.startswith("--") else declaration.lower_name
                    start = line_col_offset(declaration.source_line, declaration.source_column)
                    end = declaration_end(start)
                    rel, local_start = file_position(start)
                    rel_end, local_last = file_position(max(start, end - 1))
                    if rel != rel_end:
                        raise RuntimeError(f"declaration crosses a source boundary: {rel} -> {rel_end}")
                    declarations.append(
                        {
                            "context": context,
                            "selector": selector,
                            "property": property_name,
                            "value": normalize_token_text(tinycss2.serialize(declaration.value)),
                            "important": bool(declaration.important),
                            "path": rel,
                            "start": local_start,
                            "end": local_last + 1,
                            "sourceLine": declaration.source_line,
                        }
                    )
            elif node.type == "at-rule" and node.content is not None and node.lower_at_keyword in CONTEXT_AT_RULES:
                prelude = normalize_token_text(tinycss2.serialize(node.prelude))
                nested = tinycss2.parse_rule_list(node.content, skip_whitespace=True, skip_comments=True)
                walk(nested, context + ((node.lower_at_keyword, prelude),))

    stylesheet = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
    parse_errors = [tinycss2.serialize([item]) for item in stylesheet if item.type == "error"]
    if parse_errors:
        raise RuntimeError(f"cannot normalize invalid stylesheet: {parse_errors[:5]}")
    walk(stylesheet)

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in declarations:
        groups[(row["context"], row["selector"], row["property"])].append(row)

    removals: list[dict] = []
    for rows in groups.values():
        if len(rows) < 2:
            continue
        important_rows = [row for row in rows if row["important"]]
        keeper = important_rows[-1] if important_rows else rows[-1]
        for row in rows:
            if row is keeper:
                continue
            removals.append({**row, "effectivePath": keeper["path"], "effectiveLine": keeper["sourceLine"], "effectiveValue": keeper["value"]})

    removals_by_file: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for row in removals:
        removals_by_file[row["path"]].append((row["start"], row["end"]))

    normalized: dict[str, str] = {}
    file_rows: list[dict] = []
    for rel in paths:
        before = texts[rel]
        after = before
        for start, end in sorted(removals_by_file.get(rel, []), reverse=True):
            after = after[:start] + after[end:]
        # Empty rules can remain after removing every declaration from an obsolete rule.
        after = re.sub(r"([^{}]+)\{\s*\}", "", after)
        normalized_lines: list[str] = []
        for line in after.split("\n"):
            indentation = len(line) - len(line.lstrip(" \t"))
            if indentation > args.indent_cap:
                line = (" " * args.indent_cap) + line.lstrip(" \t")
            normalized_lines.append(line.rstrip())
        after = "\n".join(normalized_lines)
        after = re.sub(r"\n{3,}", "\n\n", after)
        normalized[rel] = after
        file_rows.append(
            {
                "path": rel,
                "beforeBytes": len(before.encode("utf-8")),
                "afterBytes": len(after.encode("utf-8")),
                "savedBytes": len(before.encode("utf-8")) - len(after.encode("utf-8")),
                "beforeSha256": sha256_text(before),
                "afterSha256": sha256_text(after),
                "removedDeclarations": len(removals_by_file.get(rel, [])),
            }
        )

    normalized_bundle = "\n\n".join(normalized[rel] for rel in paths)
    normalized_errors = [item for item in tinycss2.parse_stylesheet(normalized_bundle, skip_whitespace=True, skip_comments=True) if item.type == "error"]
    before_bytes = sum(len(text.encode("utf-8")) for text in texts.values())
    after_bytes = sum(len(text.encode("utf-8")) for text in normalized.values())
    changed = any(texts[rel] != normalized[rel] for rel in paths)
    checks = [
        {"code": "input-bundle-valid", "ok": not parse_errors},
        {"code": "normalized-bundle-valid", "ok": not normalized_errors, "detail": [tinycss2.serialize([item]) for item in normalized_errors[:5]]},
        {"code": "normalization-does-not-grow-source", "ok": after_bytes <= before_bytes, "detail": {"before": before_bytes, "after": after_bytes}},
        {"code": "target-source-budget", "ok": after_bytes < 180_000, "detail": after_bytes},
        {"code": "only-same-selector-property-shadow-removals", "ok": all(row["effectivePath"] for row in removals)},
    ]
    ok = all(check["ok"] for check in checks)
    if args.write and ok:
        for rel, text in normalized.items():
            (ROOT / rel).write_text(text, encoding="utf-8")

    report = {
        "schema": "learnit.rc649.css_normalization.v1",
        "ok": ok,
        "mode": "write" if args.write else "dry-run",
        "changed": changed,
        "policy": "Only declarations shadowed by a later declaration with the same selector, at-rule context and exact property are removed. Source indentation is capped, not minified.",
        "beforeBytes": before_bytes,
        "afterBytes": after_bytes,
        "savedBytes": before_bytes - after_bytes,
        "removedDeclarations": len(removals),
        "indentCap": args.indent_cap,
        "files": file_rows,
        "checks": checks,
        "removals": removals,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("ok", "mode", "changed", "beforeBytes", "afterBytes", "savedBytes", "removedDeclarations")}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
