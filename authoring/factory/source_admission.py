#!/usr/bin/env python3
"""Fail-closed source admission before any ATLAS Factory model ingestion.

This module does not infer law from hostnames and does not fetch the web.
It evaluates explicit, curated rights/provenance metadata from the source
catalog, then (only after admission prerequisites pass) binds exact local bytes
to a path-free SourceAdmission record.
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

CATALOG_SCHEMA = "learnit.atlas.source_catalog.v1"
CATALOG_PROFILE = "atlas.real-benchmark-sources.v1"
ADMISSION_SCHEMA = "learnit.atlas.source_admission.v1"
ADMISSION_PROFILE = "atlas.source-admission.v1"

PASS = "PASS_SOURCE_ADMISSION_V1"
HOLD_PERMISSION = "HOLD_SOURCE_PERMISSION_REQUIRED"
HOLD_PROHIBITED = "HOLD_SOURCE_PROHIBITED"
HOLD_UNKNOWN = "HOLD_SOURCE_RIGHTS_UNKNOWN"
HOLD_CONTEXT = "HOLD_SOURCE_CONTEXT_NOT_ALLOWED"
HOLD_THIRD_PARTY = "HOLD_SOURCE_THIRD_PARTY_UNRESOLVED"
HOLD_CONDITIONS = "HOLD_SOURCE_CONDITIONS_UNACCEPTED"
HOLD_VERSION = "HOLD_SOURCE_VERSION_UNBOUND"
HOLD_BYTES = "HOLD_SOURCE_BYTES_REQUIRED"
HOLD_INPUT = "HOLD_SOURCE_ADMISSION_INPUT"

EXIT_PASS = 0
EXIT_HOLD = 6

REQUIRED_DOMAINS = {
    "mathematics",
    "physics",
    "computer-science",
    "history",
    "law",
    "medicine",
    "literature",
    "management",
}
USE_CONTEXTS = {
    "internal-rd-noncommercial",
    "commercial-product",
    "public-demo",
}
RIGHTS_STATUSES = {"allowed", "conditional", "permission-required", "prohibited", "unknown"}
THIRD_PARTY_STATUSES = {"none-declared", "excluded", "present-unresolved"}
BENCHMARK_ROLES = {"primary", "support", "negative-control"}
VERSION_STRATEGIES = {"fixed", "caller"}
SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
TOKEN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


class SourceAdmissionError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return factory.canonical_json_bytes(value)


def digest(value: Any) -> str:
    return factory.sha256_bytes(canonical(value))


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = set(value) if isinstance(value, dict) else set()
        raise SourceAdmissionError(
            f"{label} fields mismatch; missing={sorted(keys-actual)} extra={sorted(actual-keys)}"
        )
    return value


def nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceAdmissionError(f"{label} must be a non-empty string")
    return value


def string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise SourceAdmissionError(f"{label} must be a {'non-empty ' if not allow_empty else ''}list")
    out: list[str] = []
    for item in value:
        out.append(nonempty(item, label))
    if len(out) != len(set(out)):
        raise SourceAdmissionError(f"{label} must not contain duplicates")
    return out


def load_catalog(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceAdmissionError(f"catalog: {exc}") from exc
    catalog = validate_catalog(value)
    return catalog, factory.sha256_bytes(raw)


def validate_version(value: Any, source_id: str) -> dict[str, Any]:
    version = exact(value, {"strategy", "value", "rule"}, f"{source_id}.version")
    if version["strategy"] not in VERSION_STRATEGIES:
        raise SourceAdmissionError(f"{source_id}.version.strategy unsupported")
    rule = nonempty(version["rule"], f"{source_id}.version.rule")
    if version["strategy"] == "fixed":
        nonempty(version["value"], f"{source_id}.version.value")
    elif version["value"] is not None:
        raise SourceAdmissionError(f"{source_id}.version.value must be null for caller strategy")
    return {"strategy": version["strategy"], "value": version["value"], "rule": rule}


def validate_rights(value: Any, source_id: str) -> dict[str, Any]:
    rights = exact(
        value,
        {
            "status",
            "license",
            "allowedUseContexts",
            "thirdPartyContentStatus",
            "conditions",
            "evidence",
        },
        f"{source_id}.rights",
    )
    if rights["status"] not in RIGHTS_STATUSES:
        raise SourceAdmissionError(f"{source_id}.rights.status unsupported")
    if rights["thirdPartyContentStatus"] not in THIRD_PARTY_STATUSES:
        raise SourceAdmissionError(f"{source_id}.rights.thirdPartyContentStatus unsupported")
    nonempty(rights["license"], f"{source_id}.rights.license")
    contexts = string_list(rights["allowedUseContexts"], f"{source_id}.rights.allowedUseContexts")
    for context in contexts:
        if context not in USE_CONTEXTS:
            raise SourceAdmissionError(f"{source_id}: unsupported use context {context!r}")
    conditions = string_list(rights["conditions"], f"{source_id}.rights.conditions")
    for condition in conditions:
        if not TOKEN.fullmatch(condition):
            raise SourceAdmissionError(f"{source_id}: invalid condition code {condition!r}")
    evidence = rights["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise SourceAdmissionError(f"{source_id}.rights.evidence must be a non-empty list")
    normalized_evidence = []
    for index, item in enumerate(evidence):
        item = exact(item, {"url", "basis"}, f"{source_id}.rights.evidence[{index}]")
        url = nonempty(item["url"], f"{source_id}.rights.evidence[{index}].url")
        basis = nonempty(item["basis"], f"{source_id}.rights.evidence[{index}].basis")
        if not url.startswith("https://"):
            raise SourceAdmissionError(f"{source_id}: rights evidence URL must use https")
        normalized_evidence.append({"url": url, "basis": basis})
    return {
        "status": rights["status"],
        "license": rights["license"],
        "allowedUseContexts": contexts,
        "thirdPartyContentStatus": rights["thirdPartyContentStatus"],
        "conditions": conditions,
        "evidence": normalized_evidence,
    }


def validate_source(value: Any, index: int) -> dict[str, Any]:
    source = exact(
        value,
        {
            "sourceId",
            "domain",
            "benchmarkRole",
            "title",
            "authority",
            "sourceUrl",
            "rightsUrl",
            "version",
            "rights",
            "benchmarkFocus",
        },
        f"sources[{index}]",
    )
    source_id = nonempty(source["sourceId"], f"sources[{index}].sourceId")
    if not SOURCE_ID.fullmatch(source_id):
        raise SourceAdmissionError(f"invalid sourceId {source_id!r}")
    domain = nonempty(source["domain"], f"{source_id}.domain")
    if domain not in REQUIRED_DOMAINS:
        raise SourceAdmissionError(f"{source_id}: unsupported benchmark domain {domain!r}")
    if source["benchmarkRole"] not in BENCHMARK_ROLES:
        raise SourceAdmissionError(f"{source_id}: unsupported benchmarkRole")
    for key in ("title", "authority", "sourceUrl", "rightsUrl", "benchmarkFocus"):
        nonempty(source[key], f"{source_id}.{key}")
    if not source["sourceUrl"].startswith("https://") or not source["rightsUrl"].startswith("https://"):
        raise SourceAdmissionError(f"{source_id}: source/rights URLs must use https")
    return {
        **source,
        "version": validate_version(source["version"], source_id),
        "rights": validate_rights(source["rights"], source_id),
    }


def validate_catalog(value: Any) -> dict[str, Any]:
    catalog = exact(
        value,
        {"schema", "profile", "defaultUseContext", "requiredDomains", "sources"},
        "catalog",
    )
    if catalog["schema"] != CATALOG_SCHEMA or catalog["profile"] != CATALOG_PROFILE:
        raise SourceAdmissionError("unsupported source catalog schema/profile")
    if catalog["defaultUseContext"] not in USE_CONTEXTS:
        raise SourceAdmissionError("unsupported defaultUseContext")
    required_domains = string_list(catalog["requiredDomains"], "requiredDomains", allow_empty=False)
    if set(required_domains) != REQUIRED_DOMAINS:
        raise SourceAdmissionError(
            f"requiredDomains mismatch; expected={sorted(REQUIRED_DOMAINS)} actual={sorted(required_domains)}"
        )
    if not isinstance(catalog["sources"], list) or not catalog["sources"]:
        raise SourceAdmissionError("sources must be a non-empty list")
    sources = [validate_source(item, i) for i, item in enumerate(catalog["sources"])]
    ids = [item["sourceId"] for item in sources]
    if len(ids) != len(set(ids)):
        raise SourceAdmissionError("sourceId values must be unique")
    primary_domains = {item["domain"] for item in sources if item["benchmarkRole"] == "primary"}
    if primary_domains != REQUIRED_DOMAINS:
        raise SourceAdmissionError(
            f"primary domain coverage mismatch; missing={sorted(REQUIRED_DOMAINS-primary_domains)}"
        )
    negative = [item for item in sources if item["benchmarkRole"] == "negative-control"]
    if len(negative) < 2:
        raise SourceAdmissionError("at least two negative-control sources are required")
    if not all(item["rights"]["status"] in {"permission-required", "prohibited", "unknown"} for item in negative):
        raise SourceAdmissionError("negative controls must be blocked by rights state")
    return {**catalog, "sources": sources}


def source_by_id(catalog: dict[str, Any], source_id: str) -> dict[str, Any]:
    for source in catalog["sources"]:
        if source["sourceId"] == source_id:
            return source
    raise SourceAdmissionError(f"unknown sourceId {source_id!r}")


def resolve_version(source: dict[str, Any], supplied: str | None) -> tuple[str | None, str | None]:
    version = source["version"]
    if version["strategy"] == "fixed":
        if supplied is not None and supplied != version["value"]:
            return None, f"fixed version mismatch: expected {version['value']!r}"
        return version["value"], None
    if supplied is None or not supplied.strip():
        return None, "caller-bound version is required"
    return supplied.strip(), None


def pre_ingestion_decision(
    source: dict[str, Any],
    use_context: str,
    accepted_conditions: set[str],
    supplied_version: str | None,
) -> tuple[str, list[str], str | None]:
    rights = source["rights"]
    status = rights["status"]
    reasons: list[str] = []
    version, version_problem = resolve_version(source, supplied_version)

    if status == "permission-required":
        return HOLD_PERMISSION, ["SOURCE_PERMISSION_REQUIRED"], version
    if status == "prohibited":
        return HOLD_PROHIBITED, ["SOURCE_USE_PROHIBITED"], version
    if status == "unknown":
        return HOLD_UNKNOWN, ["SOURCE_RIGHTS_UNKNOWN"], version
    if rights["thirdPartyContentStatus"] == "present-unresolved":
        return HOLD_THIRD_PARTY, ["SOURCE_THIRD_PARTY_RIGHTS_UNRESOLVED"], version
    if use_context not in rights["allowedUseContexts"]:
        return HOLD_CONTEXT, [f"SOURCE_CONTEXT_NOT_ALLOWED:{use_context}"], version
    missing = sorted(set(rights["conditions"]) - accepted_conditions)
    if missing:
        reasons.extend(f"SOURCE_CONDITION_UNACCEPTED:{item}" for item in missing)
        return HOLD_CONDITIONS, reasons, version
    if version_problem:
        return HOLD_VERSION, ["SOURCE_VERSION_UNBOUND:" + version_problem], version
    return PASS, [], version


def build_admission(
    catalog: dict[str, Any],
    catalog_sha256: str,
    source_id: str,
    use_context: str,
    file_path: Path | None,
    accepted_conditions: list[str],
    supplied_version: str | None,
) -> dict[str, Any]:
    if use_context not in USE_CONTEXTS:
        raise SourceAdmissionError(f"unsupported use context {use_context!r}")
    accepted = sorted(set(accepted_conditions))
    if len(accepted) != len(accepted_conditions):
        raise SourceAdmissionError("accepted condition codes must not contain duplicates")
    for item in accepted:
        if not TOKEN.fullmatch(item):
            raise SourceAdmissionError(f"invalid accepted condition code {item!r}")

    source = source_by_id(catalog, source_id)
    verdict, reasons, version = pre_ingestion_decision(
        source, use_context, set(accepted), supplied_version
    )
    content: dict[str, Any] | None = None
    pre_ingestion = verdict != PASS

    if verdict == PASS:
        if file_path is None:
            verdict = HOLD_BYTES
            reasons = ["SOURCE_BYTES_REQUIRED"]
            pre_ingestion = True
        else:
            try:
                data = file_path.read_bytes()
            except OSError as exc:
                raise SourceAdmissionError(f"source bytes: {exc}") from exc
            content = {
                "bytes": len(data),
                "sha256": factory.sha256_bytes(data),
            }
            pre_ingestion = False

    source_snapshot = {
        "sourceId": source["sourceId"],
        "domain": source["domain"],
        "benchmarkRole": source["benchmarkRole"],
        "title": source["title"],
        "authority": source["authority"],
        "sourceUrl": source["sourceUrl"],
        "rightsUrl": source["rightsUrl"],
        "version": version,
        "versionRule": source["version"]["rule"],
        "rights": source["rights"],
        "benchmarkFocus": source["benchmarkFocus"],
    }
    decision = {"verdict": verdict, "reasons": reasons}
    core = {
        "schema": ADMISSION_SCHEMA,
        "profile": ADMISSION_PROFILE,
        "catalogSha256": catalog_sha256,
        "source": source_snapshot,
        "useContext": use_context,
        "acceptedConditions": accepted,
        "content": content,
        "preIngestionHold": pre_ingestion,
        "decision": decision,
    }
    return {**core, "admissionId": digest(core)}


def verify_admission(value: Any) -> dict[str, Any]:
    record = exact(
        value,
        {
            "schema",
            "profile",
            "catalogSha256",
            "source",
            "useContext",
            "acceptedConditions",
            "content",
            "preIngestionHold",
            "decision",
            "admissionId",
        },
        "SourceAdmission",
    )
    if record["schema"] != ADMISSION_SCHEMA or record["profile"] != ADMISSION_PROFILE:
        raise SourceAdmissionError("unsupported SourceAdmission schema/profile")
    if not isinstance(record["catalogSha256"], str) or not SHA256.fullmatch(record["catalogSha256"]):
        raise SourceAdmissionError("invalid catalogSha256")
    if record["useContext"] not in USE_CONTEXTS:
        raise SourceAdmissionError("invalid useContext")
    accepted = string_list(record["acceptedConditions"], "acceptedConditions")
    for item in accepted:
        if not TOKEN.fullmatch(item):
            raise SourceAdmissionError("invalid accepted condition code")
    if not isinstance(record["preIngestionHold"], bool):
        raise SourceAdmissionError("preIngestionHold must be boolean")
    source = exact(
        record["source"],
        {
            "sourceId",
            "domain",
            "benchmarkRole",
            "title",
            "authority",
            "sourceUrl",
            "rightsUrl",
            "version",
            "versionRule",
            "rights",
            "benchmarkFocus",
        },
        "SourceAdmission.source",
    )
    if not SOURCE_ID.fullmatch(nonempty(source["sourceId"], "sourceId")):
        raise SourceAdmissionError("invalid sourceId")
    if source["domain"] not in REQUIRED_DOMAINS or source["benchmarkRole"] not in BENCHMARK_ROLES:
        raise SourceAdmissionError("invalid source domain/role")
    validate_rights(source["rights"], source["sourceId"])
    if source["version"] is not None:
        nonempty(source["version"], "source.version")
    nonempty(source["versionRule"], "source.versionRule")
    decision = exact(record["decision"], {"verdict", "reasons"}, "decision")
    nonempty(decision["verdict"], "decision.verdict")
    string_list(decision["reasons"], "decision.reasons")

    if decision["verdict"] == PASS:
        if record["preIngestionHold"]:
            raise SourceAdmissionError("PASS cannot be marked pre-ingestion HOLD")
        content = exact(record["content"], {"bytes", "sha256"}, "content")
        if isinstance(content["bytes"], bool) or not isinstance(content["bytes"], int) or content["bytes"] < 0:
            raise SourceAdmissionError("content.bytes must be integer >= 0")
        if not isinstance(content["sha256"], str) or not SHA256.fullmatch(content["sha256"]):
            raise SourceAdmissionError("content.sha256 invalid")
    else:
        if not record["preIngestionHold"]:
            raise SourceAdmissionError("HOLD must be marked preIngestionHold")
        if record["content"] is not None:
            raise SourceAdmissionError("pre-ingestion HOLD must not bind/read content bytes")
        if not decision["reasons"]:
            raise SourceAdmissionError("HOLD requires reasons")

    core = {k: v for k, v in record.items() if k != "admissionId"}
    if record["admissionId"] != digest(core):
        raise SourceAdmissionError("admissionId mismatch")
    return record


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Atlas source admission")
    sub = root.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-catalog")
    validate.add_argument("--catalog", type=Path, required=True)

    admit = sub.add_parser("admit")
    admit.add_argument("--catalog", type=Path, required=True)
    admit.add_argument("--source-id", required=True)
    admit.add_argument("--use-context")
    admit.add_argument("--file", type=Path)
    admit.add_argument("--version")
    admit.add_argument("--accept-condition", action="append", default=[])

    verify = sub.add_parser("verify-admission")
    verify.add_argument("--record", type=Path, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "validate-catalog":
            catalog, sha = load_catalog(args.catalog)
            result = {
                "verdict": "PASS_SOURCE_CATALOG_V1",
                "catalogSha256": sha,
                "primaryDomains": sorted({
                    item["domain"] for item in catalog["sources"]
                    if item["benchmarkRole"] == "primary"
                }),
                "sourceCount": len(catalog["sources"]),
            }
            sys.stdout.write(canonical(result).decode("utf-8") + "\n")
            return EXIT_PASS

        if args.command == "verify-admission":
            try:
                raw = json.loads(args.record.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SourceAdmissionError(f"record: {exc}") from exc
            record = verify_admission(raw)
            sys.stdout.write(canonical({
                "verdict": "PASS_SOURCE_ADMISSION_VERIFICATION_V1",
                "admissionId": record["admissionId"],
            }).decode("utf-8") + "\n")
            return EXIT_PASS

        catalog, sha = load_catalog(args.catalog)
        use_context = args.use_context or catalog["defaultUseContext"]
        record = build_admission(
            catalog,
            sha,
            args.source_id,
            use_context,
            args.file,
            args.accept_condition,
            args.version,
        )
        verify_admission(record)
        sys.stdout.write(canonical(record).decode("utf-8") + "\n")
        return EXIT_PASS if record["decision"]["verdict"] == PASS else EXIT_HOLD
    except SourceAdmissionError as exc:
        sys.stdout.write(canonical({
            "verdict": HOLD_INPUT,
            "cause": str(exc),
        }).decode("utf-8") + "\n")
        return EXIT_HOLD


if __name__ == "__main__":
    raise SystemExit(main())
