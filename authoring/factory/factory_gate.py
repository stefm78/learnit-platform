#!/usr/bin/env python3
"""Deterministic M3.2 AI Kit Factory context and release gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.v2.atlas import pedagogical_quality as quality

CONTEXT_SCHEMA = "learnit.atlas.ai_kit_factory_context.v1"
EVIDENCE_SCHEMA = "learnit.atlas.ai_kit_factory_evidence.v1"
ERROR_SCHEMA = "learnit.atlas.ai_kit_factory_error.v1"
BRIEF_SCHEMA = "learnit.atlas.learner_brief.v1"
REVIEW_SCHEMA = "learnit.atlas.semantic_review.v1"
FACTORY_PROFILE = "atlas.ai-kit-factory.v1"
REVIEW_PROFILE = "atlas.semantic-review.v1"
SOURCE_ID = re.compile(r"^[A-Za-z0-9._-]+$")
REQUIRED_DIMENSIONS = (
    "sourceFidelity",
    "answerCorrectness",
    "ambiguity",
    "objectiveCoverage",
    "validationTransfer",
    "learnerFit",
)
EVIDENCE_REQUIRED_DIMENSIONS = {
    "sourceFidelity",
    "answerCorrectness",
    "objectiveCoverage",
    "validationTransfer",
}
FINDING_SEVERITIES = ("blocking", "major", "minor", "advice")
SEMANTIC_PASS = "PASS_SEMANTIC_REVIEW_V1"
SEMANTIC_HOLD = "HOLD_SEMANTIC_REVIEW_V1"

EXIT_CODES = {
    "PASS_AI_KIT_FACTORY_V1": 0,
    "HOLD_FACTORY_CANONICAL_INVALID": 2,
    "HOLD_FACTORY_PEDAGOGICAL_WARNING": 3,
    "HOLD_FACTORY_INPUT": 4,
    "HOLD_FACTORY_REVIEW_BINDING": 5,
    "HOLD_FACTORY_SEMANTIC_REVIEW": 6,
}


class FactoryInputError(ValueError):
    """Malformed or unreadable factory input."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_json(path: Path, label: str) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise FactoryInputError(f"{label}: cannot read {path}: {exc}") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FactoryInputError(f"{label}: invalid UTF-8 JSON: {exc}") from exc
    return value, raw


def validate_brief(brief: Any) -> dict[str, Any]:
    if not isinstance(brief, dict):
        raise FactoryInputError("learner brief must be a JSON object")
    if brief.get("schema") != BRIEF_SCHEMA:
        raise FactoryInputError(f"learner brief schema must be {BRIEF_SCHEMA}")
    for key in ("audience", "goal", "language"):
        value = brief.get(key)
        if not isinstance(value, str) or not value.strip():
            raise FactoryInputError(f"learner brief {key} must be a non-empty string")
    minutes = brief.get("timeBudgetMinutes")
    if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
        raise FactoryInputError("learner brief timeBudgetMinutes must be an integer > 0")
    return brief


def parse_sources(specs: list[str]) -> list[dict[str, Any]]:
    if not specs:
        raise FactoryInputError("at least one --source SOURCE_ID=PATH is required")
    seen: set[str] = set()
    inventory: list[dict[str, Any]] = []
    for spec in specs:
        if "=" not in spec:
            raise FactoryInputError(f"invalid source specification {spec!r}; expected SOURCE_ID=PATH")
        source_id, raw_path = spec.split("=", 1)
        if not SOURCE_ID.fullmatch(source_id):
            raise FactoryInputError(f"invalid sourceId {source_id!r}")
        if source_id in seen:
            raise FactoryInputError(f"duplicate sourceId {source_id!r}")
        seen.add(source_id)
        path = Path(raw_path)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise FactoryInputError(f"source {source_id}: cannot read {path}: {exc}") from exc
        inventory.append(
            {
                "sourceId": source_id,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
            }
        )
    inventory.sort(key=lambda item: item["sourceId"])
    return inventory


def build_context(kit_path: Path, brief_path: Path, source_specs: list[str]) -> dict[str, Any]:
    kit, kit_raw = load_json(kit_path, "kit")
    if not isinstance(kit, dict):
        raise FactoryInputError("kit root must be a JSON object")
    brief, _ = load_json(brief_path, "learner brief")
    validate_brief(brief)
    sources = parse_sources(source_specs)
    source_set_digest = sha256_bytes(canonical_json_bytes(sources))
    brief_digest = sha256_bytes(canonical_json_bytes(brief))
    kit_digest = sha256_bytes(kit_raw)
    digest_input = {
        "profile": FACTORY_PROFILE,
        "kitSha256": kit_digest,
        "briefSha256": brief_digest,
        "sourceSetDigest": source_set_digest,
    }
    context_digest = sha256_bytes(canonical_json_bytes(digest_input))
    return {
        "schema": CONTEXT_SCHEMA,
        "profile": FACTORY_PROFILE,
        "kitSha256": kit_digest,
        "briefSha256": brief_digest,
        "sources": sources,
        "sourceSetDigest": source_set_digest,
        "contextDigest": context_digest,
    }


def _exact_keys(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise FactoryInputError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise FactoryInputError(f"{label} fields mismatch; missing={missing} extra={extra}")


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FactoryInputError(f"{label} must be a non-empty string")
    return value


def _validate_evidence(
    evidence: Any,
    label: str,
    known_sources: set[str],
    require_nonempty: bool,
) -> list[dict[str, str]]:
    if not isinstance(evidence, list):
        raise FactoryInputError(f"{label} must be a list")
    if require_nonempty and not evidence:
        raise FactoryInputError(f"{label} must be non-empty")
    result: list[dict[str, str]] = []
    for index, item in enumerate(evidence):
        item_label = f"{label}[{index}]"
        _exact_keys(item, {"sourceId", "locator", "basis"}, item_label)
        source_id = _nonempty_string(item["sourceId"], item_label + ".sourceId")
        if source_id not in known_sources:
            raise FactoryInputError(f"{item_label}.sourceId references unknown source {source_id!r}")
        locator = _nonempty_string(item["locator"], item_label + ".locator")
        basis = _nonempty_string(item["basis"], item_label + ".basis")
        result.append({"sourceId": source_id, "locator": locator, "basis": basis})
    return result


def validate_review(review: Any, context: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(
        review,
        {"schema", "profile", "target", "independence", "dimensions", "findings", "limitations", "verdict"},
        "semantic review",
    )
    if review["schema"] != REVIEW_SCHEMA:
        raise FactoryInputError(f"semantic review schema must be {REVIEW_SCHEMA}")
    if review["profile"] != REVIEW_PROFILE:
        raise FactoryInputError(f"semantic review profile must be {REVIEW_PROFILE}")

    _exact_keys(
        review["target"],
        {"contextDigest", "kitSha256", "sourceSetDigest", "briefSha256"},
        "semantic review target",
    )
    for key in ("contextDigest", "kitSha256", "sourceSetDigest", "briefSha256"):
        _nonempty_string(review["target"][key], "semantic review target." + key)

    _exact_keys(
        review["independence"],
        {"authorScratchpadSeen", "authorActiveContextReused"},
        "semantic review independence",
    )
    for key in ("authorScratchpadSeen", "authorActiveContextReused"):
        if not isinstance(review["independence"][key], bool):
            raise FactoryInputError(f"semantic review independence.{key} must be boolean")

    dimensions = review["dimensions"]
    _exact_keys(dimensions, set(REQUIRED_DIMENSIONS), "semantic review dimensions")
    known_sources = {item["sourceId"] for item in context["sources"]}
    for name in REQUIRED_DIMENSIONS:
        dimension = dimensions[name]
        _exact_keys(dimension, {"status", "summary", "evidence"}, f"dimension {name}")
        if dimension["status"] not in ("pass", "hold"):
            raise FactoryInputError(f"dimension {name}.status must be pass or hold")
        _nonempty_string(dimension["summary"], f"dimension {name}.summary")
        _validate_evidence(
            dimension["evidence"],
            f"dimension {name}.evidence",
            known_sources,
            name in EVIDENCE_REQUIRED_DIMENSIONS,
        )

    findings = review["findings"]
    if not isinstance(findings, list):
        raise FactoryInputError("semantic review findings must be a list")
    finding_ids: set[str] = set()
    for index, finding in enumerate(findings):
        label = f"semantic review findings[{index}]"
        _exact_keys(
            finding,
            {"id", "severity", "dimension", "path", "problem", "impact", "fix", "evidence"},
            label,
        )
        finding_id = _nonempty_string(finding["id"], label + ".id")
        if finding_id in finding_ids:
            raise FactoryInputError(f"duplicate semantic finding id {finding_id!r}")
        finding_ids.add(finding_id)
        if finding["severity"] not in FINDING_SEVERITIES:
            raise FactoryInputError(f"{label}.severity is unsupported")
        if finding["dimension"] not in REQUIRED_DIMENSIONS:
            raise FactoryInputError(f"{label}.dimension is unsupported")
        for key in ("path", "problem", "impact", "fix"):
            _nonempty_string(finding[key], label + "." + key)
        _validate_evidence(finding["evidence"], label + ".evidence", known_sources, False)

    limitations = review["limitations"]
    if not isinstance(limitations, list):
        raise FactoryInputError("semantic review limitations must be a list")
    for index, limitation in enumerate(limitations):
        _nonempty_string(limitation, f"semantic review limitations[{index}]")

    if review["verdict"] not in (SEMANTIC_PASS, SEMANTIC_HOLD):
        raise FactoryInputError("semantic review verdict is unsupported")
    return review


def semantic_reasons(review: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if review["independence"]["authorScratchpadSeen"]:
        reasons.append("REVIEWER_SAW_AUTHOR_SCRATCHPAD")
    if review["independence"]["authorActiveContextReused"]:
        reasons.append("REVIEWER_REUSED_AUTHOR_ACTIVE_CONTEXT")
    for name in REQUIRED_DIMENSIONS:
        if review["dimensions"][name]["status"] != "pass":
            reasons.append("DIMENSION_HOLD:" + name)
    for finding in review["findings"]:
        if finding["severity"] in ("blocking", "major"):
            reasons.append(f"{finding['severity'].upper()}_FINDING:{finding['id']}")
    semantic_pass = not reasons
    expected = SEMANTIC_PASS if semantic_pass else SEMANTIC_HOLD
    if review["verdict"] != expected:
        reasons.append(f"INCONSISTENT_REVIEW_VERDICT:expected={expected}")
    return sorted(reasons)


def binding_reasons(review: dict[str, Any], context: dict[str, Any]) -> list[str]:
    expected = {
        "contextDigest": context["contextDigest"],
        "kitSha256": context["kitSha256"],
        "sourceSetDigest": context["sourceSetDigest"],
        "briefSha256": context["briefSha256"],
    }
    return sorted(
        f"REVIEW_TARGET_MISMATCH:{key}"
        for key, value in expected.items()
        if review["target"].get(key) != value
    )


def _semantic_counts(review: dict[str, Any]) -> dict[str, int]:
    return {
        severity: sum(finding["severity"] == severity for finding in review["findings"])
        for severity in FINDING_SEVERITIES
    }


def run_gate(
    kit_path: Path,
    brief_path: Path,
    review_path: Path,
    source_specs: list[str],
) -> dict[str, Any]:
    context = build_context(kit_path, brief_path, source_specs)
    kit, _ = load_json(kit_path, "kit")
    quality_report = quality.analyze_package(kit)

    review, review_raw = load_json(review_path, "semantic review")
    review = validate_review(review, context)
    bindings = binding_reasons(review, context)
    semantics = semantic_reasons(review)

    if not quality_report["canonicalValid"]:
        verdict = "HOLD_FACTORY_CANONICAL_INVALID"
        reasons = ["CANONICAL_INVALID"]
    elif quality_report["qualityBand"] not in ("STRONG", "EXCELLENT_BY_PROFILE"):
        verdict = "HOLD_FACTORY_PEDAGOGICAL_WARNING"
        reasons = ["PEDAGOGICAL_QUALITY_BAND:" + str(quality_report["qualityBand"])]
    elif bindings:
        verdict = "HOLD_FACTORY_REVIEW_BINDING"
        reasons = bindings
    elif semantics:
        verdict = "HOLD_FACTORY_SEMANTIC_REVIEW"
        reasons = semantics
    else:
        verdict = "PASS_AI_KIT_FACTORY_V1"
        reasons = []

    return {
        "schema": EVIDENCE_SCHEMA,
        "profile": FACTORY_PROFILE,
        "context": context,
        "canonicalValid": bool(quality_report["canonicalValid"]),
        "pedagogicalQuality": {
            "verdict": quality_report["verdict"],
            "qualityBand": quality_report["qualityBand"],
            "counts": quality_report["counts"],
        },
        "semanticReview": {
            "sha256": sha256_bytes(review_raw),
            "verdict": review["verdict"],
            "counts": _semantic_counts(review),
        },
        "verdict": verdict,
        "reasons": reasons,
    }


def canonical_output(value: dict[str, Any]) -> str:
    return canonical_json_bytes(value).decode("utf-8") + "\n"


def render_human(evidence: dict[str, Any]) -> str:
    quality_band = evidence["pedagogicalQuality"]["qualityBand"]
    semantic = evidence["semanticReview"]["verdict"]
    lines = [
        f"AI KIT FACTORY: {evidence['verdict']}",
        f"Pedagogical quality: {quality_band}",
        f"Semantic review: {semantic}",
    ]
    for reason in evidence["reasons"]:
        lines.append("- " + reason)
    return "\n".join(lines)


def _add_common(parser: argparse.ArgumentParser, include_review: bool) -> None:
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="SOURCE_ID=PATH",
        help="Bind one source file. Repeat for multiple sources.",
    )
    if include_review:
        parser.add_argument("--review", type=Path, required=True)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Learn-it Atlas M3.2 AI Kit Factory gate.")
    sub = root.add_subparsers(dest="command", required=True)

    context = sub.add_parser("context", help="Emit deterministic source/brief/kit context JSON.")
    _add_common(context, False)

    gate = sub.add_parser("gate", help="Run the final deterministic AI Kit Factory gate.")
    _add_common(gate, True)
    gate.add_argument("--json", action="store_true", dest="as_json")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "context":
            context = build_context(args.kit, args.brief, args.source)
            sys.stdout.write(canonical_output(context))
            return 0
        evidence = run_gate(args.kit, args.brief, args.review, args.source)
    except FactoryInputError as exc:
        error = {
            "schema": ERROR_SCHEMA,
            "verdict": "HOLD_FACTORY_INPUT",
            "cause": str(exc),
        }
        if getattr(args, "as_json", False) or args.command == "context":
            sys.stdout.write(canonical_output(error))
        else:
            print(f"AI KIT FACTORY: HOLD_FACTORY_INPUT\n- {exc}", file=sys.stderr)
        return EXIT_CODES["HOLD_FACTORY_INPUT"]

    if args.as_json:
        sys.stdout.write(canonical_output(evidence))
    else:
        print(render_human(evidence))
    return EXIT_CODES[evidence["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
