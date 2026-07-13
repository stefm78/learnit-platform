#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import json
import re
import sys

try:
    import tinycss2
except Exception as exc:  # pragma: no cover - explicit release failure
    raise SystemExit(f"tinycss2 is required for CSS audit: {exc}")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "css_semantic_audit.json"
CONTEXT_AT_RULES = {"media", "supports", "layer", "container", "scope", "document"}


def load_style_paths() -> list[str]:
    manifest = json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))
    paths: list[str] = []
    for entry in manifest.get("styles", []):
        if entry.get("path"):
            paths.append(entry["path"])
        paths.extend(entry.get("paths", []))
    return paths


def normalize(value: str) -> str:
    return " ".join(value.split())


def strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def main() -> int:
    paths = load_style_paths()
    chunks: list[str] = []
    line_ranges: list[tuple[int, int, str]] = []
    current_line = 1
    file_rows: list[dict] = []
    cumulative_delta = 0

    for index, rel in enumerate(paths):
        text = (ROOT / rel).read_text(encoding="utf-8")
        cleaned = strip_comments(text)
        delta = cleaned.count("{") - cleaned.count("}")
        cumulative_delta += delta
        lines = text.splitlines(True)
        leading_indent_bytes = sum(len(re.match(r"[ \t]*", line).group()) for line in lines)
        comments = re.findall(r"/\*.*?\*/", text, flags=re.S)
        start = current_line
        end = current_line + text.count("\n")
        line_ranges.append((start, end, rel))
        file_rows.append(
            {
                "path": rel,
                "bytes": len(text.encode("utf-8")),
                "lines": len(lines),
                "braceDelta": delta,
                "cumulativeBraceDelta": cumulative_delta,
                "leadingIndentBytes": leading_indent_bytes,
                "commentBytes": sum(len(comment.encode("utf-8")) for comment in comments),
            }
        )
        chunks.append(text)
        current_line = end
        if index < len(paths) - 1:
            chunks.append("\n\n")
            current_line += 2

    css = "".join(chunks)

    def source_location(line: int) -> dict:
        for start, end, rel in line_ranges:
            if start <= line <= end:
                return {"path": rel, "line": line - start + 1}
        return {"path": "<bundle-boundary>", "line": line}

    rules = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
    parse_errors = [tinycss2.serialize([item]) for item in rules if item.type == "error"]
    qualified_rows: list[dict] = []
    declaration_rows: list[dict] = []

    def walk(nodes: list, context: tuple = ()) -> None:
        for node in nodes:
            if node.type == "qualified-rule":
                selector = normalize(tinycss2.serialize(node.prelude))
                declarations = tinycss2.parse_declaration_list(node.content, skip_whitespace=True, skip_comments=True)
                declaration_payload: list[dict] = []
                for declaration in declarations:
                    if declaration.type != "declaration":
                        continue
                    value = normalize(tinycss2.serialize(declaration.value))
                    row = {
                        "context": context,
                        "selector": selector,
                        "property": declaration.lower_name,
                        "value": value,
                        "important": bool(declaration.important),
                        "source": source_location(declaration.source_line),
                        "serializedBytes": len(tinycss2.serialize([declaration]).encode("utf-8")),
                    }
                    declaration_rows.append(row)
                    declaration_payload.append(row)
                qualified_rows.append(
                    {
                        "context": context,
                        "selector": selector,
                        "body": normalize(tinycss2.serialize(node.content)),
                        "source": source_location(node.source_line),
                        "serializedBytes": len(tinycss2.serialize([node]).encode("utf-8")),
                        "declarationCount": len(declaration_payload),
                    }
                )
            elif node.type == "at-rule" and node.content is not None and node.lower_at_keyword in CONTEXT_AT_RULES:
                prelude = normalize(tinycss2.serialize(node.prelude))
                nested = tinycss2.parse_rule_list(node.content, skip_whitespace=True, skip_comments=True)
                walk(nested, context + ((node.lower_at_keyword, prelude),))

    walk(rules)

    exact_rule_groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in qualified_rows:
        exact_rule_groups[(row["context"], row["selector"], row["body"])].append(row)
    duplicate_rule_groups = [rows for rows in exact_rule_groups.values() if len(rows) > 1]

    declaration_groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in declaration_rows:
        declaration_groups[(row["context"], row["selector"], row["property"])].append(row)

    shadowed: list[dict] = []
    for rows in declaration_groups.values():
        if len(rows) < 2:
            continue
        important_rows = [row for row in rows if row["important"]]
        keeper = important_rows[-1] if important_rows else rows[-1]
        for row in rows:
            if row is keeper:
                continue
            shadowed.append({**row, "effectiveDeclaration": keeper["source"], "effectiveValue": keeper["value"]})

    selector_prefixes = Counter()
    for row in qualified_rows:
        match = re.match(r"\.([A-Za-z0-9_-]+)", row["selector"])
        if match:
            selector_prefixes[match.group(1).split("-")[0]] += 1

    totals = {
        "activeCssBytes": sum(row["bytes"] for row in file_rows),
        "files": len(file_rows),
        "qualifiedRules": len(qualified_rows),
        "declarations": len(declaration_rows),
        "exactDuplicateRuleGroups": len(duplicate_rule_groups),
        "exactDuplicateRuleInstances": sum(len(rows) - 1 for rows in duplicate_rule_groups),
        "shadowedSameSelectorPropertyDeclarations": len(shadowed),
        "estimatedShadowedDeclarationBytes": sum(row["serializedBytes"] for row in shadowed),
        "leadingIndentBytes": sum(row["leadingIndentBytes"] for row in file_rows),
        "commentBytes": sum(row["commentBytes"] for row in file_rows),
    }

    checks = [
        {"code": "all-style-files-present", "ok": bool(paths) and all((ROOT / path).exists() for path in paths)},
        {"code": "bundle-parse-has-no-top-level-errors", "ok": not parse_errors, "detail": parse_errors[:10]},
        {"code": "bundle-final-brace-balance", "ok": cumulative_delta == 0, "detail": cumulative_delta},
        {"code": "audit-locates-every-declaration", "ok": all(row["source"]["path"] != "<bundle-boundary>" for row in declaration_rows)},
        {"code": "css-source-budget-classified", "ok": True, "detail": {"bytes": totals["activeCssBytes"], "status": "within-target" if totals["activeCssBytes"] < 180_000 else "near-limit"}},
        {"code": "cleanup-candidates-classified", "ok": True, "detail": totals["shadowedSameSelectorPropertyDeclarations"]},
    ]
    ok = all(check["ok"] for check in checks)
    report = {
        "schema": "learnit.rc648.css_semantic_audit.v1",
        "ok": ok,
        "policy": "Audit only. No selector, declaration or learner-visible behavior is modified by this tool.",
        "files": file_rows,
        "totals": totals,
        "checks": checks,
        "duplicateRules": duplicate_rule_groups,
        "shadowedDeclarations": shadowed,
        "dominantSelectorPrefixes": selector_prefixes.most_common(20),
        "recommendedActions": [
            "Remove only declarations shadowed by a later declaration with the same selector, at-rule context and property.",
            "Normalize excessive indentation without minifying declarations or selectors.",
            "Repair file boundaries that split a declaration or at-rule before renaming legacy owners.",
            "Prove the resulting artifact with mandatory, browser and RC637 visual-equivalence gates.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "report": str(OUT.relative_to(ROOT)), "totals": totals}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
