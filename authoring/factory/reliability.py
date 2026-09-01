#!/usr/bin/env python3
"""M3.2.5 reliability layer around the promoted M3.2 factory gate.

Adds logical resource identity, deterministic/self-verifying FactoryRun records,
and a benchmark gate. No source ingestion, network, model call or output write.
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

RESOURCE_SCHEMA = "learnit.atlas.resource_identity.v1"
RUN_SCHEMA = "learnit.atlas.factory_run.v1"
BUNDLE_SCHEMA = "learnit.atlas.factory_evidence_bundle.v1"
BENCHMARK_CONTRACT_SCHEMA = "learnit.atlas.factory_benchmark_contract.v1"
BENCHMARK_MANIFEST_SCHEMA = "learnit.atlas.factory_benchmark_manifest.v1"
BENCHMARK_REPORT_SCHEMA = "learnit.atlas.factory_benchmark_report.v1"
RELIABILITY_PROFILE = "atlas.factory-reliability.v1"
BENCHMARK_PROFILE = "atlas.factory-benchmark.v1"
DEFAULT_BENCHMARK_CONTRACT = ROOT / "authoring/factory/benchmark_contract.json"
VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
BENCHMARK_EXIT = 7


class ReliabilityInputError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return factory.canonical_json_bytes(value)


def digest(value: Any) -> str:
    return factory.sha256_bytes(canonical(value))


def load_json(path: Path, label: str) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
        return json.loads(raw.decode("utf-8")), raw
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReliabilityInputError(f"{label}: {exc}") from exc


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = set(value) if isinstance(value, dict) else set()
        raise ReliabilityInputError(
            f"{label} fields mismatch; missing={sorted(keys-actual)} extra={sorted(actual-keys)}"
        )
    return value


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReliabilityInputError(f"{label} must be a non-empty string")
    return value


def parse_resources(specs: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """Return path-free identities plus private M3.2 SOURCE_ID=PATH bindings."""
    if not specs:
        raise ReliabilityInputError("at least one --resource RESOURCE_ID@VERSION=PATH is required")
    rows: list[tuple[dict[str, Any], str]] = []
    seen: set[str] = set()
    for spec in specs:
        if "=" not in spec or "@" not in spec.split("=", 1)[0]:
            raise ReliabilityInputError(f"invalid resource specification {spec!r}")
        logical, raw_path = spec.split("=", 1)
        resource_id, version = logical.rsplit("@", 1)
        if not factory.SOURCE_ID.fullmatch(resource_id):
            raise ReliabilityInputError(f"invalid resourceId {resource_id!r}")
        if not VERSION.fullmatch(version):
            raise ReliabilityInputError(f"invalid resource version {version!r}")
        if resource_id in seen:
            raise ReliabilityInputError(f"duplicate resourceId {resource_id!r}")
        seen.add(resource_id)
        path = Path(raw_path)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ReliabilityInputError(f"resource {resource_id}: {exc}") from exc
        rows.append(({
            "schema": RESOURCE_SCHEMA,
            "resourceId": resource_id,
            "version": version,
            "bytes": len(data),
            "sha256": factory.sha256_bytes(data),
        }, f"{resource_id}={path}"))
    rows.sort(key=lambda row: row[0]["resourceId"])
    return [row[0] for row in rows], [row[1] for row in rows]


def build_run(kit: Path, brief: Path, review: Path, specs: list[str]) -> dict[str, Any]:
    resources, source_specs = parse_resources(specs)
    try:
        gate = factory.run_gate(kit, brief, review, source_specs)
    except factory.FactoryInputError as exc:
        raise ReliabilityInputError(str(exc)) from exc
    _, kit_raw = load_json(kit, "kit")
    _, brief_raw = load_json(brief, "learner brief")
    _, review_raw = load_json(review, "semantic review")
    resource_digest = digest(resources)
    decision = {"verdict": gate["verdict"], "reasons": list(gate["reasons"])}
    bundle_core = {
        "schema": BUNDLE_SCHEMA,
        "resources": resources,
        "resourceSetDigest": resource_digest,
        "artifacts": {
            "learnerBrief": {
                "bytes": len(brief_raw),
                "sha256": factory.sha256_bytes(brief_raw),
                "canonicalSha256": gate["context"]["briefSha256"],
            },
            "generatedKit": {"bytes": len(kit_raw), "sha256": gate["context"]["kitSha256"]},
            "semanticReview": {"bytes": len(review_raw), "sha256": gate["semanticReview"]["sha256"]},
        },
        "validators": {
            "canonicalValid": bool(gate["canonicalValid"]),
            "pedagogicalQuality": gate["pedagogicalQuality"],
            "semanticReview": gate["semanticReview"],
        },
        "factoryEvidence": gate,
        "factoryEvidenceSha256": digest(gate),
        "finalDecision": decision,
    }
    bundle = {**bundle_core, "bundleSha256": digest(bundle_core)}
    run_core = {
        "schema": RUN_SCHEMA,
        "profile": RELIABILITY_PROFILE,
        "resourceSetDigest": resource_digest,
        "factoryContextDigest": gate["context"]["contextDigest"],
        "evidenceBundle": bundle,
        "decision": decision,
    }
    return {**run_core, "runId": digest(run_core)}


def verify_run(value: Any) -> dict[str, Any]:
    run = exact(value, {
        "schema", "profile", "resourceSetDigest", "factoryContextDigest",
        "evidenceBundle", "decision", "runId",
    }, "FactoryRun")
    if run["schema"] != RUN_SCHEMA or run["profile"] != RELIABILITY_PROFILE:
        raise ReliabilityInputError("unsupported FactoryRun schema/profile")
    bundle = exact(run["evidenceBundle"], {
        "schema", "resources", "resourceSetDigest", "artifacts", "validators",
        "factoryEvidence", "factoryEvidenceSha256", "finalDecision", "bundleSha256",
    }, "evidenceBundle")
    if bundle["schema"] != BUNDLE_SCHEMA:
        raise ReliabilityInputError("unsupported evidence bundle schema")
    resources = bundle["resources"]
    if not isinstance(resources, list) or not resources:
        raise ReliabilityInputError("resources must be a non-empty list")
    ids: set[str] = set()
    for item in resources:
        exact(item, {"schema", "resourceId", "version", "bytes", "sha256"}, "resource")
        rid = text(item["resourceId"], "resourceId")
        if item["schema"] != RESOURCE_SCHEMA or not factory.SOURCE_ID.fullmatch(rid):
            raise ReliabilityInputError("invalid resource identity")
        if rid in ids or not VERSION.fullmatch(text(item["version"], "resource.version")):
            raise ReliabilityInputError("duplicate resourceId or invalid version")
        ids.add(rid)
    if resources != sorted(resources, key=lambda item: item["resourceId"]):
        raise ReliabilityInputError("resources must be sorted")
    resource_digest = digest(resources)
    if run["resourceSetDigest"] != resource_digest or bundle["resourceSetDigest"] != resource_digest:
        raise ReliabilityInputError("resourceSetDigest mismatch")

    gate = exact(bundle["factoryEvidence"], {
        "schema", "profile", "context", "canonicalValid", "pedagogicalQuality",
        "semanticReview", "verdict", "reasons",
    }, "factoryEvidence")
    context = exact(gate["context"], {
        "schema", "profile", "kitSha256", "briefSha256", "sources",
        "sourceSetDigest", "contextDigest",
    }, "factoryEvidence.context")
    semantic = exact(gate["semanticReview"], {"sha256", "verdict", "counts"}, "semanticReview")
    if bundle["factoryEvidenceSha256"] != digest(gate):
        raise ReliabilityInputError("factoryEvidenceSha256 mismatch")
    if run["factoryContextDigest"] != context["contextDigest"]:
        raise ReliabilityInputError("factoryContextDigest mismatch")
    source_rows = {x["sourceId"]: (x["bytes"], x["sha256"]) for x in context["sources"]}
    resource_rows = {x["resourceId"]: (x["bytes"], x["sha256"]) for x in resources}
    if source_rows != resource_rows:
        raise ReliabilityInputError("resource/M3.2 source binding mismatch")

    artifacts = exact(bundle["artifacts"], {"learnerBrief", "generatedKit", "semanticReview"}, "artifacts")
    if artifacts["learnerBrief"]["canonicalSha256"] != context["briefSha256"]:
        raise ReliabilityInputError("brief hash mismatch")
    if artifacts["generatedKit"]["sha256"] != context["kitSha256"]:
        raise ReliabilityInputError("kit hash mismatch")
    if artifacts["semanticReview"]["sha256"] != semantic["sha256"]:
        raise ReliabilityInputError("review hash mismatch")
    validators = exact(bundle["validators"], {"canonicalValid", "pedagogicalQuality", "semanticReview"}, "validators")
    if validators != {
        "canonicalValid": gate["canonicalValid"],
        "pedagogicalQuality": gate["pedagogicalQuality"],
        "semanticReview": gate["semanticReview"],
    }:
        raise ReliabilityInputError("validator evidence mismatch")
    decision = {"verdict": gate["verdict"], "reasons": list(gate["reasons"])}
    if run["decision"] != decision or bundle["finalDecision"] != decision:
        raise ReliabilityInputError("final decision mismatch")
    bundle_core = {k: v for k, v in bundle.items() if k != "bundleSha256"}
    if bundle["bundleSha256"] != digest(bundle_core):
        raise ReliabilityInputError("bundleSha256 mismatch")
    run_core = {k: v for k, v in run.items() if k != "runId"}
    if run["runId"] != digest(run_core):
        raise ReliabilityInputError("runId mismatch")
    return run


def decision_class(run: dict[str, Any]) -> str:
    verdict = run["decision"]["verdict"]
    if isinstance(verdict, str) and verdict.startswith("PASS_"):
        return "PASS"
    if isinstance(verdict, str) and verdict.startswith("HOLD_"):
        return "HOLD"
    raise ReliabilityInputError(f"unsupported decision {verdict!r}")


def validate_benchmark_contract(value: Any) -> dict[str, Any]:
    contract = exact(value, {
        "schema", "profile", "requiredDomains", "minimumRuns", "minimumPass",
        "minimumHold", "maximumHumanEscalationRate",
    }, "benchmark contract")
    if contract["schema"] != BENCHMARK_CONTRACT_SCHEMA or contract["profile"] != BENCHMARK_PROFILE:
        raise ReliabilityInputError("unsupported benchmark contract")
    domains = contract["requiredDomains"]
    if not isinstance(domains, list) or not domains or len(domains) != len(set(domains)):
        raise ReliabilityInputError("requiredDomains must be a unique non-empty list")
    for key in ("minimumRuns", "minimumPass", "minimumHold"):
        if isinstance(contract[key], bool) or not isinstance(contract[key], int) or contract[key] < 1:
            raise ReliabilityInputError(f"{key} must be >= 1")
    rate = contract["maximumHumanEscalationRate"]
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not 0 <= rate <= 1:
        raise ReliabilityInputError("maximumHumanEscalationRate must be between 0 and 1")
    return contract


def run_benchmark(contract_path: Path, manifest_path: Path) -> dict[str, Any]:
    contract, _ = load_json(contract_path, "benchmark contract")
    contract = validate_benchmark_contract(contract)
    manifest, _ = load_json(manifest_path, "benchmark manifest")
    manifest = exact(manifest, {"schema", "cases"}, "benchmark manifest")
    if manifest["schema"] != BENCHMARK_MANIFEST_SCHEMA or not isinstance(manifest["cases"], list):
        raise ReliabilityInputError("invalid benchmark manifest")
    rows: list[dict[str, Any]] = []
    case_ids: set[str] = set(); run_ids: set[str] = set(); reasons: list[str] = []
    for case in manifest["cases"]:
        case = exact(case, {"caseId", "domain", "run", "expectedDecision", "humanEscalation"}, "benchmark case")
        case_id = text(case["caseId"], "caseId"); domain = text(case["domain"], "domain")
        if case_id in case_ids or case["expectedDecision"] not in {"PASS", "HOLD", "ANY"}:
            raise ReliabilityInputError("duplicate caseId or invalid expectedDecision")
        if not isinstance(case["humanEscalation"], bool):
            raise ReliabilityInputError("humanEscalation must be boolean")
        case_ids.add(case_id)
        run, _ = load_json(Path(text(case["run"], "case.run")), f"FactoryRun {case_id}")
        run = verify_run(run); actual = decision_class(run)
        if run["runId"] in run_ids:
            raise ReliabilityInputError(f"duplicate FactoryRun identity {run['runId']}")
        run_ids.add(run["runId"])
        if case["expectedDecision"] != "ANY" and case["expectedDecision"] != actual:
            reasons.append(f"BENCHMARK_EXPECTATION_MISMATCH:{case_id}:expected={case['expectedDecision']}:actual={actual}")
        if actual == "HOLD" and not run["decision"]["reasons"]:
            reasons.append(f"BENCHMARK_HOLD_UNJUSTIFIED:{case_id}")
        rows.append({
            "caseId": case_id, "domain": domain, "runId": run["runId"],
            "decision": actual, "verdict": run["decision"]["verdict"],
            "humanEscalation": case["humanEscalation"],
        })
    passed = sum(x["decision"] == "PASS" for x in rows); held = sum(x["decision"] == "HOLD" for x in rows)
    covered = sorted({x["domain"] for x in rows}); human = sum(x["humanEscalation"] for x in rows)
    rate = human / len(rows) if rows else 0.0
    if len(rows) < contract["minimumRuns"]: reasons.append(f"BENCHMARK_TOO_FEW_RUNS:{len(rows)}<{contract['minimumRuns']}")
    if passed < contract["minimumPass"]: reasons.append(f"BENCHMARK_TOO_FEW_PASS:{passed}<{contract['minimumPass']}")
    if held < contract["minimumHold"]: reasons.append(f"BENCHMARK_TOO_FEW_HOLD:{held}<{contract['minimumHold']}")
    for domain in contract["requiredDomains"]:
        if domain not in covered: reasons.append("BENCHMARK_DOMAIN_MISSING:" + domain)
    if rate > contract["maximumHumanEscalationRate"]:
        reasons.append(f"BENCHMARK_HUMAN_ESCALATION_RATE:{rate:.6f}>{contract['maximumHumanEscalationRate']:.6f}")
    reasons = sorted(set(reasons))
    return {
        "schema": BENCHMARK_REPORT_SCHEMA,
        "profile": BENCHMARK_PROFILE,
        "contractSha256": digest(contract),
        "metrics": {"runs": len(rows), "pass": passed, "hold": held, "humanEscalations": human,
                    "humanEscalationRate": round(rate, 6), "domainsCovered": covered},
        "cases": rows,
        "verdict": "PASS_FACTORY_BENCHMARK_V1" if not reasons else "HOLD_FACTORY_BENCHMARK_V1",
        "reasons": reasons,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Atlas M3.2.5 Factory Reliability")
    sub = root.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run"); run.add_argument("--kit", type=Path, required=True); run.add_argument("--brief", type=Path, required=True); run.add_argument("--review", type=Path, required=True); run.add_argument("--resource", action="append", default=[])
    verify = sub.add_parser("verify-run"); verify.add_argument("--run", type=Path, required=True)
    benchmark = sub.add_parser("benchmark"); benchmark.add_argument("--manifest", type=Path, required=True); benchmark.add_argument("--contract", type=Path, default=DEFAULT_BENCHMARK_CONTRACT)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "run":
            run = build_run(args.kit, args.brief, args.review, args.resource); verify_run(run)
            sys.stdout.write(canonical(run).decode("utf-8") + "\n")
            return factory.EXIT_CODES[run["decision"]["verdict"]]
        if args.command == "verify-run":
            run, _ = load_json(args.run, "FactoryRun"); run = verify_run(run)
            sys.stdout.write(canonical({"verdict": "PASS_FACTORY_RUN_VERIFICATION_V1", "runId": run["runId"]}).decode("utf-8") + "\n")
            return 0
        report = run_benchmark(args.contract, args.manifest)
        sys.stdout.write(canonical(report).decode("utf-8") + "\n")
        return 0 if report["verdict"] == "PASS_FACTORY_BENCHMARK_V1" else BENCHMARK_EXIT
    except ReliabilityInputError as exc:
        sys.stdout.write(canonical({"verdict": "HOLD_FACTORY_RELIABILITY_INPUT", "cause": str(exc)}).decode("utf-8") + "\n")
        return factory.EXIT_CODES["HOLD_FACTORY_INPUT"]


if __name__ == "__main__":
    raise SystemExit(main())
