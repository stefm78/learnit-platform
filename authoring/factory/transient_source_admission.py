#!/usr/bin/env python3
"""Fail-closed admission for transient private user-provided ATLAS sources.

This authority is intentionally separate from the curated benchmark
SourceAdmission path. It does not infer legal rights, provenance or permission
from filenames, URLs, institutions or source content.

A PASS means only that:
- the user/operator supplied an explicit declaration for private personal
  learning;
- source retention is transient-only;
- source redistribution is prohibited;
- legal rights are explicitly not claimed as verified by Learn-it; and
- the exact caller-bound source bytes/version are cryptographically bound.

The source bytes remain caller-owned/transient inputs. This module creates no
repository corpus, persistent catalog, network call or durable source store.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory

DECLARATION_SCHEMA = "learnit.atlas.transient_source_declaration.v1"
DECLARATION_PROFILE = "atlas.user-provided-private-learning.v1"
DECLARATION_VERSION = "learnit.private-source-user-declaration.v1"

ADMISSION_SCHEMA = "learnit.atlas.transient_source_admission.v1"
ADMISSION_PROFILE = "atlas.transient-user-source-admission.v1"

PASS = "PASS_TRANSIENT_SOURCE_ADMISSION_V1"
HOLD_DECLARATION = "HOLD_TRANSIENT_SOURCE_USER_DECLARATION_REQUIRED"
HOLD_CONTEXT = "HOLD_TRANSIENT_SOURCE_CONTEXT_NOT_ALLOWED"
HOLD_RETENTION = "HOLD_TRANSIENT_SOURCE_RETENTION_NOT_TRANSIENT"
HOLD_REDISTRIBUTION = "HOLD_TRANSIENT_SOURCE_REDISTRIBUTION_NOT_PROHIBITED"
HOLD_LEGAL_CLAIM = "HOLD_TRANSIENT_SOURCE_LEGAL_VERIFICATION_CLAIM"
HOLD_BYTES = "HOLD_TRANSIENT_SOURCE_BYTES_REQUIRED"
HOLD_INPUT = "HOLD_TRANSIENT_SOURCE_ADMISSION_INPUT_V1"

EXIT_PASS = 0
EXIT_HOLD = 6

PROCESSING_CONTEXT = "private-personal-learning"
PROVENANCE = "user-provided"
AUTHORIZATION_BASIS = "user-declaration"
RETENTION = "transient-only"
REDISTRIBUTION = "prohibited"

SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
WINDOWS_RESERVED_SOURCE_STEMS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}


class TransientSourceAdmissionError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return factory.canonical_json_bytes(value)


def digest(value: Any) -> str:
    return factory.sha256_bytes(canonical(value))


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = set(value) if isinstance(value, dict) else set()
        raise TransientSourceAdmissionError(
            f"{label} fields mismatch; missing={sorted(keys-actual)} extra={sorted(actual-keys)}"
        )
    return value


def nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransientSourceAdmissionError(f"{label} must be a non-empty string")
    return value


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransientSourceAdmissionError(f"{label}: {exc}") from exc


def validate_declaration(value: Any) -> dict[str, Any]:
    declaration = exact(
        value,
        {
            "schema",
            "profile",
            "declarationVersion",
            "sourceId",
            "version",
            "provenance",
            "processingContext",
            "authorizationBasis",
            "userDeclarationAccepted",
            "retention",
            "redistribution",
            "legalRightsVerified",
        },
        "TransientSourceDeclaration",
    )
    if (
        declaration["schema"] != DECLARATION_SCHEMA
        or declaration["profile"] != DECLARATION_PROFILE
        or declaration["declarationVersion"] != DECLARATION_VERSION
    ):
        raise TransientSourceAdmissionError(
            "unsupported transient source declaration schema/profile/version"
        )
    source_id = nonempty(declaration["sourceId"], "sourceId")
    version = nonempty(declaration["version"], "version")
    if not SOURCE_ID.fullmatch(source_id):
        raise TransientSourceAdmissionError("invalid sourceId")
    source_stem = source_id.split(".", 1)[0].upper()
    if source_stem in WINDOWS_RESERVED_SOURCE_STEMS:
        raise TransientSourceAdmissionError("sourceId is not portable on Windows")
    if not VERSION.fullmatch(version):
        raise TransientSourceAdmissionError("invalid version")
    if not isinstance(declaration["userDeclarationAccepted"], bool):
        raise TransientSourceAdmissionError("userDeclarationAccepted must be boolean")
    if not isinstance(declaration["legalRightsVerified"], bool):
        raise TransientSourceAdmissionError("legalRightsVerified must be boolean")
    for key in (
        "provenance",
        "processingContext",
        "authorizationBasis",
        "retention",
        "redistribution",
    ):
        nonempty(declaration[key], key)
    return declaration


def pre_ingestion_decision(declaration: dict[str, Any]) -> tuple[str, list[str]]:
    if declaration["provenance"] != PROVENANCE:
        return HOLD_DECLARATION, ["TRANSIENT_SOURCE_PROVENANCE_MUST_BE_USER_PROVIDED"]
    if declaration["authorizationBasis"] != AUTHORIZATION_BASIS:
        return HOLD_DECLARATION, ["TRANSIENT_SOURCE_AUTHORIZATION_BASIS_MUST_BE_USER_DECLARATION"]
    if declaration["userDeclarationAccepted"] is not True:
        return HOLD_DECLARATION, ["TRANSIENT_SOURCE_USER_DECLARATION_REQUIRED"]
    if declaration["processingContext"] != PROCESSING_CONTEXT:
        return HOLD_CONTEXT, [
            f"TRANSIENT_SOURCE_CONTEXT_NOT_ALLOWED:{declaration['processingContext']}"
        ]
    if declaration["retention"] != RETENTION:
        return HOLD_RETENTION, [
            f"TRANSIENT_SOURCE_RETENTION_NOT_ALLOWED:{declaration['retention']}"
        ]
    if declaration["redistribution"] != REDISTRIBUTION:
        return HOLD_REDISTRIBUTION, [
            f"TRANSIENT_SOURCE_REDISTRIBUTION_NOT_ALLOWED:{declaration['redistribution']}"
        ]
    if declaration["legalRightsVerified"] is not False:
        return HOLD_LEGAL_CLAIM, ["TRANSIENT_SOURCE_LEGAL_RIGHTS_MUST_NOT_BE_CLAIMED_VERIFIED"]
    return PASS, []


def build_admission(
    declaration_value: Any,
    file_path: Path | None,
) -> dict[str, Any]:
    declaration = validate_declaration(declaration_value)
    verdict, reasons = pre_ingestion_decision(declaration)
    content: dict[str, Any] | None = None
    pre_ingestion_hold = verdict != PASS

    if verdict == PASS:
        if file_path is None:
            verdict = HOLD_BYTES
            reasons = ["TRANSIENT_SOURCE_BYTES_REQUIRED"]
            pre_ingestion_hold = True
        else:
            try:
                data = file_path.read_bytes()
            except OSError as exc:
                raise TransientSourceAdmissionError(f"source bytes: {exc}") from exc
            content = {
                "bytes": len(data),
                "sha256": factory.sha256_bytes(data),
            }
            pre_ingestion_hold = False

    core = {
        "schema": ADMISSION_SCHEMA,
        "profile": ADMISSION_PROFILE,
        "declaration": declaration,
        "declarationDigest": digest(declaration),
        "content": content,
        "preIngestionHold": pre_ingestion_hold,
        "decision": {
            "verdict": verdict,
            "reasons": reasons,
        },
    }
    return {**core, "admissionId": digest(core)}


def verify_admission(value: Any) -> dict[str, Any]:
    record = exact(
        value,
        {
            "schema",
            "profile",
            "declaration",
            "declarationDigest",
            "content",
            "preIngestionHold",
            "decision",
            "admissionId",
        },
        "TransientSourceAdmission",
    )
    if record["schema"] != ADMISSION_SCHEMA or record["profile"] != ADMISSION_PROFILE:
        raise TransientSourceAdmissionError("unsupported transient source admission schema/profile")

    declaration = validate_declaration(record["declaration"])
    if (
        not isinstance(record["declarationDigest"], str)
        or not SHA256.fullmatch(record["declarationDigest"])
        or record["declarationDigest"] != digest(declaration)
    ):
        raise TransientSourceAdmissionError("declarationDigest mismatch")

    if not isinstance(record["preIngestionHold"], bool):
        raise TransientSourceAdmissionError("preIngestionHold must be boolean")

    decision = exact(record["decision"], {"verdict", "reasons"}, "decision")
    nonempty(decision["verdict"], "decision.verdict")
    if (
        not isinstance(decision["reasons"], list)
        or any(not isinstance(item, str) or not item for item in decision["reasons"])
    ):
        raise TransientSourceAdmissionError("decision.reasons must be a list of strings")

    expected_verdict, expected_reasons = pre_ingestion_decision(declaration)

    if decision["verdict"] == PASS:
        if expected_verdict != PASS:
            raise TransientSourceAdmissionError("PASS contradicts declaration policy")
        if record["preIngestionHold"]:
            raise TransientSourceAdmissionError("PASS cannot be pre-ingestion HOLD")
        if decision["reasons"]:
            raise TransientSourceAdmissionError("PASS must have no reasons")
        content = exact(record["content"], {"bytes", "sha256"}, "content")
        if (
            isinstance(content["bytes"], bool)
            or not isinstance(content["bytes"], int)
            or content["bytes"] < 0
        ):
            raise TransientSourceAdmissionError("content.bytes must be integer >= 0")
        if not isinstance(content["sha256"], str) or not SHA256.fullmatch(content["sha256"]):
            raise TransientSourceAdmissionError("content.sha256 invalid")
    else:
        if not record["preIngestionHold"]:
            raise TransientSourceAdmissionError("HOLD must be pre-ingestion HOLD")
        if record["content"] is not None:
            raise TransientSourceAdmissionError("pre-ingestion HOLD must not bind source bytes")
        if not decision["reasons"]:
            raise TransientSourceAdmissionError("HOLD requires reasons")
        if expected_verdict == PASS:
            if decision["verdict"] != HOLD_BYTES:
                raise TransientSourceAdmissionError("unexpected HOLD for policy-valid declaration")
        elif (
            decision["verdict"] != expected_verdict
            or decision["reasons"] != expected_reasons
        ):
            raise TransientSourceAdmissionError("HOLD decision contradicts declaration policy")

    core = {key: item for key, item in record.items() if key != "admissionId"}
    if record["admissionId"] != digest(core):
        raise TransientSourceAdmissionError("admissionId mismatch")
    return record


def reproduce_admission(record_value: Any, file_path: Path) -> dict[str, Any]:
    record = verify_admission(record_value)
    rebuilt = build_admission(record["declaration"], file_path)
    if rebuilt != record:
        raise TransientSourceAdmissionError(
            "admission is not reproducible from declaration and exact source bytes"
        )
    return record


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Atlas transient private user-source admission")
    sub = root.add_subparsers(dest="command", required=True)

    admit = sub.add_parser("admit")
    admit.add_argument("--declaration", type=Path, required=True)
    admit.add_argument("--file", type=Path)

    verify = sub.add_parser("verify-admission")
    verify.add_argument("--record", type=Path, required=True)
    verify.add_argument("--file", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "admit":
            declaration = load_json(args.declaration, "declaration")
            result = build_admission(declaration, args.file)
        else:
            result = verify_admission(load_json(args.record, "admission"))
            if args.file is not None:
                result = reproduce_admission(result, args.file)

        sys.stdout.write(canonical(result).decode("utf-8") + "\n")
        return EXIT_PASS if result["decision"]["verdict"] == PASS else EXIT_HOLD
    except TransientSourceAdmissionError as exc:
        sys.stdout.write(
            canonical(
                {
                    "schema": "learnit.atlas.transient_source_admission_result.v1",
                    "verdict": HOLD_INPUT,
                    "cause": str(exc),
                }
            ).decode("utf-8")
            + "\n"
        )
        return EXIT_HOLD


if __name__ == "__main__":
    raise SystemExit(main())
