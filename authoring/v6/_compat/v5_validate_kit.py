#!/usr/bin/env python3
"""Deterministic semantic validator for explicit ``learnit.kit.v5`` packages."""
from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.v4 import validate_kit as v4

SCHEMA_PATH = ROOT / "contracts/learnit-kit-v5.schema.json"
ZERO_DIGEST = v4.ZERO_DIGEST
CONTROL_OR_SPACE = re.compile(r"[\x00-\x20\x7f]")
BACKSLASH = re.compile(r"\\")


class V5ValidationError(ValueError):
    """Input or authority failure for the v5 authoring validator."""


Report = v4.Report
load = v4.load
digest = v4.digest
diagnostic = v4.diagnostic
fill_new_digests = v4.fill_new_digests
cross_file_errors = v4.cross_file_errors
render_json = v4.render_json
render_human = v4.render_human


def _reference_url_errors(url: str, path: str) -> list[str]:
    errors: list[str] = []
    if url != url.strip() or CONTROL_OR_SPACE.search(url):
        errors.append(diagnostic(path, "reference URL cannot contain surrounding whitespace, spaces, or control characters", url))
        return errors
    if BACKSLASH.search(url):
        errors.append(diagnostic(path, "reference URL backslashes are forbidden", url))
        return errors
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        return [diagnostic(path, "malformed reference URL", str(exc))]
    if parts.scheme.lower() != "https":
        errors.append(diagnostic(path, "reference URL scheme must be https", parts.scheme))
    if not parts.netloc or not parts.hostname:
        errors.append(diagnostic(path, "reference URL must contain an ordinary web host", url))
    if parts.username is not None or parts.password is not None:
        errors.append(diagnostic(path, "reference URL credentials/userinfo are forbidden", parts.netloc))
    try:
        _ = parts.port
    except ValueError as exc:
        errors.append(diagnostic(path, "reference URL port is invalid", str(exc)))
    return errors


def _check_v5_extensions(document: dict[str, Any], report: Report) -> None:
    for ci, course in enumerate(document.get("courses", [])):
        if not isinstance(course, dict):
            continue
        for ai, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict):
                continue
            ap = f"$.courses[{ci}].activities[{ai}]"
            hints = activity.get("hints", [])
            if isinstance(hints, list):
                for hi, hint in enumerate(hints):
                    if isinstance(hint, str) and not hint.strip():
                        report.errors.append(diagnostic(f"{ap}.hints[{hi}]", "hint must contain non-whitespace learner-facing text", hint))
            references = activity.get("references", [])
            if not isinstance(references, list):
                continue
            for ri, reference in enumerate(references):
                if not isinstance(reference, dict):
                    continue
                rp = f"{ap}.references[{ri}]"
                url = reference.get("url")
                if isinstance(url, str):
                    report.errors.extend(_reference_url_errors(url, rp + ".url"))
                for field_name in ("label", "hook"):
                    value = reference.get(field_name)
                    if isinstance(value, str) and not value.strip():
                        report.errors.append(diagnostic(rp + "." + field_name, f"reference {field_name} must contain non-whitespace learner-facing text", value))


def validate(path: Path, document: dict[str, Any], schema: dict[str, Any]) -> Report:
    report = Report(path)
    report.errors.extend(v4.v2.schema_errors(document, schema))
    if isinstance(document, dict):
        v4.semantic_checks(document, report)
        _check_v5_extensions(document, report)
        v4.add_digest_records(document, report)
    return report


def parser() -> argparse.ArgumentParser:
    argp = argparse.ArgumentParser(description="Validate explicit learnit.kit.v5 packages.")
    argp.add_argument("kits", nargs="+", type=Path)
    argp.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    argp.add_argument("--write-digests", action="store_true")
    argp.add_argument("--show-canonical", action="store_true")
    argp.add_argument("--format", choices=("human", "json"), default="human")
    return argp


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        schema = load(args.schema)
        if not isinstance(schema, dict):
            raise V5ValidationError("schema root must be an object")
        documents: list[tuple[Path, dict[str, Any]]] = []
        write_errors: list[str] = []
        for path in args.kits:
            document = load(path)
            if not isinstance(document, dict):
                raise V5ValidationError(f"{path}: kit root must be a JSON object")
            if args.write_digests:
                document = copy.deepcopy(document)
                write_errors += [f"{path}: {error}" for error in fill_new_digests(document)]
            documents.append((path, document))
        reports = [validate(path, document, schema) for path, document in documents]
        cross = cross_file_errors(reports) + write_errors
        if args.write_digests and all(report.ok for report in reports) and not cross:
            import json
            for path, document in documents:
                path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(render_json(reports, cross, args.show_canonical) if args.format == "json" else render_human(reports, cross, args.show_canonical))
        return 0 if all(report.ok for report in reports) and not cross else 1
    except (v4.v2.ToolError, V5ValidationError) as exc:
        print(f"TOOL ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
