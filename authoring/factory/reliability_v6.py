#!/usr/bin/env python3
"""Self-verifying FactoryRun support for exact PASSAGE V6 Factory evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from authoring.factory import v6_gate

RUN_SCHEMA = "learnit.atlas.factory_run.v2"
RUN_PROFILE = "atlas.factory-reliability.v6-r1"
BUNDLE_SCHEMA = "learnit.atlas.factory_evidence_bundle.v2"
PASS_VERIFY = "PASS_FACTORY_RUN_V6_VERIFICATION_R1"
HOLD_INPUT = "HOLD_FACTORY_RUN_V6_INPUT_R1"
EXIT_HOLD = 7


class V6ReliabilityInputError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return v6_gate.canonical(value)


def digest(value: Any) -> str:
    return v6_gate.digest(value)


def load_json(path: Path, label: str) -> tuple[Any, bytes]:
    return v6_gate.load_json(path, label)


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    try:
        return v6_gate.exact(value, keys, label)
    except v6_gate.V6FactoryInputError as exc:
        raise V6ReliabilityInputError(str(exc)) from exc


def build_run(
    kit: Path,
    brief: Path,
    review: Path,
    source_manifest: Path,
    source_specs: list[str],
    git_commit: str,
) -> dict[str, Any]:
    try:
        gate = v6_gate.run_gate(kit, brief, review, source_manifest, source_specs, git_commit)
    except v6_gate.V6FactoryInputError as exc:
        raise V6ReliabilityInputError(str(exc)) from exc
    _, kit_raw = load_json(kit, "kit")
    _, brief_raw = load_json(brief, "learner brief")
    _, review_raw = load_json(review, "semantic review")
    _, source_manifest_raw = load_json(source_manifest, "source manifest")
    decision = {"verdict": gate["verdict"], "reasons": list(gate["reasons"])}
    bundle_core = {
        "schema": BUNDLE_SCHEMA,
        "artifacts": {
            "generatedKit": {"bytes": len(kit_raw), "sha256": v6_gate.sha256(kit_raw)},
            "learnerBrief": {"bytes": len(brief_raw), "sha256": v6_gate.sha256(brief_raw)},
            "semanticReview": {"bytes": len(review_raw), "sha256": v6_gate.sha256(review_raw)},
            "sourceManifest": {"bytes": len(source_manifest_raw), "sha256": v6_gate.sha256(source_manifest_raw)},
        },
        "factoryEvidence": gate,
        "factoryEvidenceSha256": digest(gate),
        "implementationAuthority": dict(gate["implementationAuthority"]),
        "finalDecision": decision,
    }
    bundle = {**bundle_core, "bundleSha256": digest(bundle_core)}
    run_core = {
        "schema": RUN_SCHEMA,
        "profile": RUN_PROFILE,
        "factoryContextDigest": gate["context"]["contextDigest"],
        "implementationAuthority": dict(gate["implementationAuthority"]),
        "evidenceBundle": bundle,
        "decision": decision,
    }
    return {**run_core, "runId": digest(run_core)}


def _artifact(value: Any, label: str) -> dict[str, Any]:
    row = exact(value, {"bytes", "sha256"}, label)
    v6_gate.nonnegative_int(row["bytes"], label + ".bytes")
    if not isinstance(row["sha256"], str) or not v6_gate.SHA256.fullmatch(row["sha256"]):
        raise V6ReliabilityInputError(label + ".sha256 is invalid")
    return row


def verify_run(value: Any) -> dict[str, Any]:
    run = exact(value, {"schema", "profile", "factoryContextDigest", "implementationAuthority", "evidenceBundle", "decision", "runId"}, "V6 FactoryRun")
    if run["schema"] != RUN_SCHEMA or run["profile"] != RUN_PROFILE:
        raise V6ReliabilityInputError("unsupported V6 FactoryRun schema/profile")
    bundle = exact(run["evidenceBundle"], {"schema", "artifacts", "factoryEvidence", "factoryEvidenceSha256", "implementationAuthority", "finalDecision", "bundleSha256"}, "V6 evidence bundle")
    if bundle["schema"] != BUNDLE_SCHEMA:
        raise V6ReliabilityInputError("unsupported V6 evidence bundle schema")
    artifacts = exact(bundle["artifacts"], {"generatedKit", "learnerBrief", "semanticReview", "sourceManifest"}, "V6 artifacts")
    for name in artifacts:
        _artifact(artifacts[name], "V6 artifacts." + name)
    try:
        gate = v6_gate.verify_evidence(bundle["factoryEvidence"])
    except v6_gate.V6FactoryInputError as exc:
        raise V6ReliabilityInputError(f"factory evidence: {exc}") from exc
    if bundle["factoryEvidenceSha256"] != digest(gate):
        raise V6ReliabilityInputError("factoryEvidenceSha256 mismatch")
    if run["factoryContextDigest"] != gate["context"]["contextDigest"]:
        raise V6ReliabilityInputError("factoryContextDigest mismatch")
    if artifacts["generatedKit"]["sha256"] != gate["context"]["kitSha256"]:
        raise V6ReliabilityInputError("generatedKit SHA mismatch")
    if artifacts["learnerBrief"]["sha256"] != gate["context"]["briefSha256"]:
        raise V6ReliabilityInputError("learnerBrief SHA mismatch")
    if artifacts["semanticReview"]["sha256"] != gate["semanticReview"]["sha256"]:
        raise V6ReliabilityInputError("semanticReview SHA mismatch")
    if artifacts["sourceManifest"]["sha256"] != gate["sourceGovernance"]["manifestSha256"]:
        raise V6ReliabilityInputError("sourceManifest SHA mismatch")
    if run["implementationAuthority"] != gate["implementationAuthority"] or bundle["implementationAuthority"] != gate["implementationAuthority"]:
        raise V6ReliabilityInputError("implementationAuthority mismatch")
    decision = {"verdict": gate["verdict"], "reasons": list(gate["reasons"])}
    if run["decision"] != decision or bundle["finalDecision"] != decision:
        raise V6ReliabilityInputError("final decision mismatch")
    bundle_core = {key: val for key, val in bundle.items() if key != "bundleSha256"}
    if bundle["bundleSha256"] != digest(bundle_core):
        raise V6ReliabilityInputError("bundleSha256 mismatch")
    run_core = {key: val for key, val in run.items() if key != "runId"}
    if run["runId"] != digest(run_core):
        raise V6ReliabilityInputError("runId mismatch")
    return run


def decision_class(run: dict[str, Any]) -> str:
    verdict = run["decision"]["verdict"]
    if verdict == v6_gate.FACTORY_PASS:
        return "PASS"
    if verdict == v6_gate.FACTORY_HOLD:
        return "HOLD"
    raise V6ReliabilityInputError(f"unsupported V6 decision {verdict!r}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="PASSAGE V6 Factory reliability")
    sub = root.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--kit", type=Path, required=True)
    run.add_argument("--brief", type=Path, required=True)
    run.add_argument("--review", type=Path, required=True)
    run.add_argument("--source-manifest", type=Path, required=True)
    run.add_argument("--source", action="append", default=[])
    run.add_argument("--git-commit", required=True)
    verify = sub.add_parser("verify-run")
    verify.add_argument("--run", type=Path, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "run":
            run = build_run(args.kit, args.brief, args.review, args.source_manifest, args.source, args.git_commit)
            verify_run(run)
            sys.stdout.write(canonical(run).decode("utf-8") + "\n")
            return 0 if decision_class(run) == "PASS" else EXIT_HOLD
        run, _ = load_json(args.run, "V6 FactoryRun")
        verified = verify_run(run)
        sys.stdout.write(canonical({"verdict": PASS_VERIFY, "runId": verified["runId"]}).decode("utf-8") + "\n")
        return 0
    except (V6ReliabilityInputError, v6_gate.V6FactoryInputError) as exc:
        sys.stdout.write(canonical({"verdict": HOLD_INPUT, "cause": str(exc)}).decode("utf-8") + "\n")
        return EXIT_HOLD


if __name__ == "__main__":
    raise SystemExit(main())
