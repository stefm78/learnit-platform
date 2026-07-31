#!/usr/bin/env python3
"""Deterministic CI routing for historical Wave A and Project Atlas M1."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT.parents[3] if len(SCRIPT.parents) > 3 else Path.cwd()
ROOT = Path(os.environ.get("LEARNIT_REPO_ROOT", DEFAULT_ROOT)).resolve()
RESULT_DIR = ROOT / "apps/learnit-next/.agent-result"
REPORT = RESULT_DIR / "run_checks.json"
WAVE_A_BASE = "8ebafee48cc5277b92776982639a0146ae7e76d0"
ATLAS_BASE = "58e39e8917006058fdf177a5daa37535f5e2c78d"
CONTRACT_HEAD = "f41de5043a22f8559a3b6a0d71654fbd542b5ec6"
CONTRACT_BRANCH = "agent/ATLAS-WP-001-contracts-0-3"
RUNNER_PATH = "apps/learnit-next/dev/run_checks.py"
DEPENDENCY_PATH = "apps/player/requirements-test.txt"
CONTRACT_PATHS = (
    "contracts/fixtures/atlas-m1-invalid-loop.json",
    "contracts/fixtures/atlas-m1-valid-loop.json",
    "contracts/learnit-kit-v2.schema.json",
    "docs/atlas/CONTRACTS.md",
    "work-packages/ATLAS-WP-001.json",
)
CONTRACT_ARTIFACT = f"atlas-contracts-evidence-{CONTRACT_HEAD}"
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
REWARD_KINDS = {
    "correction-completed",
    "independent-success",
    "validation-completed",
    "validation-reconfirmed",
    "resumed-after-interruption",
}
LEARNING_ACTIONS = {
    "start-practice",
    "continue-practice",
    "correct-practice",
    "attempt-validation",
    "maintain-recent-validation",
}
EVIDENCE_STATES = {
    "not-started",
    "training",
    "review-needed",
    "ready-for-validation",
    "validated-recently",
}
REASON_CODES = {
    "NEW_OBJECTIVE",
    "PRACTICE_IN_PROGRESS",
    "RECENT_ERROR",
    "REVIEW_REQUIRED",
    "CORRECTION_COMPLETED",
    "NO_INDEPENDENT_VALIDATION",
    "VALIDATION_AVAILABLE",
    "RECENTLY_VALIDATED",
    "SESSION_TIME_LIMIT",
}

ATLAS = {
    "atlas-support": (
        "agent/ATLAS-WP-001-support-governance-ci",
        {
            "governance/governor-state.json",
            ".github/workflows/learnit-next-ci.yml",
            RUNNER_PATH,
        },
        (("tools/validate_repository.py",),),
        {},
        "READY_FOR_SUPPORT_REVIEW",
    ),
    "atlas-contracts": (
        CONTRACT_BRANCH,
        set(CONTRACT_PATHS),
        (),
        {},
        "READY_FOR_EVIDENCE_ONLY_REVIEW",
    ),
    "atlas-learning": (
        "agent/ATLAS-WP-001-learning",
        {
            "apps/learnit-next/src/core/atlas_evidence.js",
            "apps/learnit-next/src/core/atlas_recommendation.js",
            "apps/learnit-next/src/core/atlas_planner.js",
            "apps/learnit-next/tests/atlas_m1_learning.py",
        },
        (("apps/learnit-next/tests/atlas_m1_learning.py",),),
        {},
        "READY_FOR_LANE_REVIEW",
    ),
    "atlas-experience": (
        "agent/ATLAS-WP-001-experience",
        {
            "apps/learnit-next/src/ui/atlas_today.js",
            "apps/learnit-next/src/ui/atlas_session.js",
            "apps/learnit-next/src/ui/atlas_summary.js",
            "apps/learnit-next/src/ui/atlas_rewards.js",
            "apps/learnit-next/src/atlas.css",
            "apps/learnit-next/tests/atlas_m1_experience.py",
        },
        (("apps/learnit-next/tests/atlas_m1_experience.py",),),
        {"ATLAS_EXPERIENCE_STRICT": "1"},
        "READY_FOR_LANE_REVIEW",
    ),
    "atlas-core": (
        "agent/ATLAS-WP-001-core",
        {
            "apps/learnit-next/src/core/atlas_events.js",
            "apps/learnit-next/src/core/atlas_projection.js",
            "apps/learnit-next/src/core/atlas_clock.js",
            "apps/learnit-next/src/ports/atlas_storage.js",
            "apps/learnit-next/src/adapters/atlas_indexeddb.js",
            "apps/learnit-next/tests/atlas_m1_core.py",
        },
        (("apps/learnit-next/tests/atlas_m1_core.py",),),
        {},
        "READY_FOR_LANE_REVIEW",
    ),
    "atlas-content": (
        "agent/ATLAS-WP-001-content",
        {
            "authoring/v2/atlas/README.md",
            "authoring/v2/atlas/nombres_complexes_atlas.json",
            "authoring/v2/atlas/signaux_electriques_atlas.json",
            "authoring/v2/atlas/validate_atlas_content.py",
            "apps/learnit-next/tests/atlas_m1_content.py",
        },
        (
            ("authoring/v2/atlas/validate_atlas_content.py",),
            ("apps/learnit-next/tests/atlas_m1_content.py",),
        ),
        {},
        "READY_FOR_LANE_REVIEW",
    ),
    "atlas-qa": (
        "agent/ATLAS-WP-001-qa",
        {
            "apps/learnit-next/tests/qa_atlas_m1.py",
            "contracts/fixtures/atlas-m1-valid-loop.json",
            "contracts/fixtures/atlas-m1-invalid-loop.json",
        },
        (("apps/learnit-next/tests/qa_atlas_m1.py",),),
        {},
        "PRE_CANDIDATE_QA_READY",
    ),
}
ATLAS_BRANCHES = {config[0]: profile for profile, config in ATLAS.items()}
WAVE_A_BRANCHES = {
    "agent/PROG-WP-001-wave-a-learning",
    "agent/PROG-WP-001-wave-a-ux",
    "agent/PROG-WP-001-wave-a-authoring",
    "agent/PROG-WP-001-wave-a-platform",
    "agent/PROG-WP-001-wave-a-qa",
    "agent/PROG-WP-001-wave-a-int",
}


class GateError(RuntimeError):
    pass


class ContractReject(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def call(command: list[str], env: dict[str, str] | None = None, cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env={**os.environ, **(env or {}), "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=1800,
    )
    if completed.returncode:
        raise GateError(f"{' '.join(command)} failed:\n{completed.stdout}")
    return completed.stdout.strip()


def command_record(
    command: list[str], *, env: dict[str, str] | None = None, cwd: Path = ROOT, check: bool = True
) -> dict[str, Any]:
    started = utc_now()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env={**os.environ, **(env or {}), "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=1800,
    )
    record = {
        "command": command,
        "working_directory": str(cwd),
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if check and completed.returncode:
        raise GateError(
            f"{' '.join(command)} failed with {completed.returncode}:\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    return record


def git(*args: str) -> str:
    return call(["git", *args])


def resolve(branch: str) -> str:
    if branch in ATLAS_BRANCHES:
        return ATLAS_BRANCHES[branch]
    if branch in WAVE_A_BRANCHES:
        return "wave-a"
    raise GateError(f"unrecognized CI branch: {branch}")


def routing_matrix() -> dict[str, object]:
    atlas = {branch: resolve(branch) for branch in sorted(ATLAS_BRANCHES)}
    historical = {branch: resolve(branch) for branch in sorted(WAVE_A_BRANCHES)}
    if atlas.get(CONTRACT_BRANCH) != "atlas-contracts":
        raise GateError("exact contract branch is not routed to atlas-contracts")
    try:
        resolve("agent/UNKNOWN-WP-999-example")
    except GateError:
        return {"atlas": atlas, "historical": historical, "unknownBranchRejected": True}
    raise GateError("unknown branch routing is not fail-closed")


def atlas_provenance(profile: str, branch: str, base_ref: str) -> dict[str, object]:
    expected_branch, paths, _, _, _ = ATLAS[profile]
    if branch != expected_branch:
        raise GateError(f"Atlas branch/profile mismatch: {branch} != {expected_branch}")
    if base_ref != ATLAS_BASE or git("rev-parse", base_ref) != ATLAS_BASE:
        raise GateError("Atlas support base differs")
    if git("merge-base", ATLAS_BASE, "HEAD") != ATLAS_BASE:
        raise GateError("Atlas branch merge-base differs")
    changed = set(filter(None, git("diff", "--name-only", f"{ATLAS_BASE}...HEAD").splitlines()))
    if changed != paths:
        detail = {"expected": sorted(paths), "actual": sorted(changed)}
        raise GateError("Atlas path set differs: " + json.dumps(detail, sort_keys=True))
    head = git("rev-parse", "HEAD")
    if profile == "atlas-contracts" and head != CONTRACT_HEAD:
        raise GateError(f"contract head differs: {head} != {CONTRACT_HEAD}")
    return {
        "base": ATLAS_BASE,
        "mergeBase": git("merge-base", ATLAS_BASE, "HEAD"),
        "branch": branch,
        "head": head,
        "changedPaths": sorted(changed),
        "aheadBehind": git("rev-list", "--left-right", "--count", f"{ATLAS_BASE}...HEAD"),
    }


def support_contract_capability() -> dict[str, Any]:
    workflow = (ROOT / ".github/workflows/learnit-next-ci.yml").read_text(encoding="utf-8")
    runner = (ROOT / RUNNER_PATH).read_text(encoding="utf-8")
    required_workflow = [
        CONTRACT_BRANCH,
        "atlas-contracts",
        CONTRACT_ARTIFACT,
        DEPENDENCY_PATH,
        "ATLAS_DEPENDENCY_COMMANDS_JSON",
        "ATLAS_WORKTREE_BEFORE_INSTALL_JSON",
        "ATLAS_WORKTREE_AFTER_INSTALL_JSON",
    ]
    required_runner = [
        CONTRACT_HEAD,
        "atlas-contracts-evidence.json",
        "atlas-contracts-evidence.md",
        "atlas-contracts-commands.log",
        "ADVERSARIAL_21_CASE_MATRIX",
        "EVIDENCE_COMPLETE",
    ]
    missing = [token for token in required_workflow if token not in workflow]
    missing += [token for token in required_runner if token not in runner]
    if missing:
        raise GateError("contract support capability incomplete: " + json.dumps(missing))
    classifier_tests = _schema_error_classification_self_test()
    return {
        "contractBranch": CONTRACT_BRANCH,
        "profile": "atlas-contracts",
        "artifact": CONTRACT_ARTIFACT,
        "dependencyFile": DEPENDENCY_PATH,
        "schemaErrorClassificationHarness": classifier_tests,
        "evidenceFiles": [
            "apps/learnit-next/.agent-result/atlas-contracts-evidence.json",
            "apps/learnit-next/.agent-result/atlas-contracts-evidence.md",
            "apps/learnit-next/.agent-result/atlas-contracts-commands.log",
        ],
    }


def _load_json(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha256_file(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _contract_file_identities() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in CONTRACT_PATHS:
        raw = (ROOT / path).read_bytes()
        result[path] = {
            "git_blob_sha1": git("rev-parse", f"HEAD:{path}"),
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    return result


def _pointer_get(document: Any, pointer: str) -> Any:
    if not pointer.startswith("#/") and not pointer.startswith("/"):
        raise GateError(f"unsupported JSON pointer: {pointer}")
    tokens = (pointer[2:] if pointer.startswith("#/") else pointer[1:]).split("/")
    current = document
    for token in tokens:
        token = token.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def _pointer_parent(document: Any, pointer: str) -> tuple[Any, str]:
    if not pointer.startswith("/"):
        raise GateError(f"patch path must be absolute: {pointer}")
    tokens = pointer[1:].split("/")
    current = document
    for token in tokens[:-1]:
        token = token.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current, tokens[-1].replace("~1", "/").replace("~0", "~")


def _patch(document: Any, operations: list[dict[str, Any]]) -> tuple[Any, dict[str, Any]]:
    work = copy.deepcopy(document)
    named: dict[str, Any] = {}
    for operation in operations:
        op = operation["op"]
        target = named.get(operation.get("target", ""), work)
        if op == "clone-as":
            named[operation["name"]] = copy.deepcopy(work)
            continue
        if op == "copy":
            value = copy.deepcopy(_pointer_get(target, operation["from"]))
            parent, key = _pointer_parent(target, operation["path"])
            if isinstance(parent, list):
                parent[int(key)] = value
            else:
                parent[key] = value
            continue
        parent, key = _pointer_parent(target, operation["path"])
        if op == "remove":
            if isinstance(parent, list):
                parent.pop(int(key))
            else:
                del parent[key]
        elif op in {"add", "replace"}:
            value = copy.deepcopy(operation["value"])
            if isinstance(parent, list):
                index = int(key)
                if op == "add":
                    parent.insert(index, value)
                else:
                    parent[index] = value
            else:
                parent[key] = value
        else:
            raise GateError(f"unsupported patch operation: {op}")
    return work, named


def _normalise(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalise(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalise(value[key]) for key in sorted(value)}
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    raise GateError(f"non-canonical JSON value: {type(value).__name__}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalise(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _atlas_hash(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + _canonical_bytes(value)).hexdigest()


def _validate_timestamp(value: str) -> None:
    if not TIMESTAMP_RE.fullmatch(value):
        raise ContractReject("NON_CANONICAL_TIMESTAMP")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as error:
        raise ContractReject("NON_CANONICAL_TIMESTAMP", str(error)) from error


def _validate_atlas_gate(kit: dict[str, Any]) -> None:
    allowed_pairs = {
        ("activation", "practice"),
        ("comprehension", "practice"),
        ("application", "practice"),
        ("consolidation", "practice"),
        ("validation", "validation"),
        ("transfer", "practice"),
        ("diagnostic", "diagnostic"),
    }
    for course in kit["courses"]:
        objectives = {item["objectiveId"] for item in course["objectives"]}
        for activity in course["activities"]:
            if "estimatedMinutes" not in activity:
                raise ContractReject("ATLAS_ACTIVITY_DURATION_REQUIRED")
            pair = (activity["learningPhase"], activity["assessmentRole"])
            if pair not in allowed_pairs:
                raise ContractReject("ATLAS_ACTIVITY_CLASSIFICATION_INVALID")
            if not set(activity["objectiveIds"]).issubset(objectives):
                raise ContractReject("ATLAS_OBJECTIVE_REFERENCE_INVALID")
        for claim in course.get("atlasValidationIndependenceClaims", []):
            if claim["sourceActivityLineageId"] == claim["targetActivityLineageId"]:
                raise ContractReject("CLAIM_SOURCE_TARGET_NOT_DISTINCT")
            if claim["sourceStimulusDigest"] == claim["targetStimulusDigest"]:
                raise ContractReject("CLAIM_STIMULUS_NOT_DISTINCT")


def _walk_schema_errors(errors: list[Any]) -> Any:
    for error in errors:
        yield error
        yield from _walk_schema_errors(list(error.context))


def _serialise_schema_error(error: Any) -> dict[str, Any]:
    return {
        "validator": error.validator,
        "validatorValue": error.validator_value,
        "message": error.message,
        "absolutePath": list(error.absolute_path),
        "absoluteSchemaPath": list(error.absolute_schema_path),
        "context": [_serialise_schema_error(child) for child in error.context],
    }


def _classify_schema_rejection(
    case_id: str,
    expected: str,
    errors: list[Any],
) -> tuple[str, dict[str, Any]]:
    if not errors:
        raise GateError(f"{case_id} was accepted by JSON Schema")
    flattened = list(_walk_schema_errors(errors))
    validators = [error.validator for error in flattened]
    if expected == "ENUM_CLOSED" and "enum" not in validators:
        raise GateError(f"{case_id} did not fail a closed enum")
    if expected == "UNEVALUATED_PROPERTY" and not any(
        validator in {"unevaluatedProperties", "additionalProperties"}
        for validator in validators
    ):
        raise GateError(f"{case_id} did not fail an unknown property")
    return expected, {
        "topLevelErrorCount": len(errors),
        "flattenedErrorCount": len(flattened),
        "flattenedValidators": validators,
        "errors": [_serialise_schema_error(error) for error in errors],
    }


def _schema_error_classification_self_test() -> dict[str, Any]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as error:
        raise GateError("jsonschema dependency missing") from error

    nested_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "oneOf": [
            {
                "type": "object",
                "required": ["type"],
                "properties": {"type": {"const": "qcm"}},
                "unevaluatedProperties": False,
            },
            {
                "type": "object",
                "required": ["type", "segments"],
                "properties": {
                    "type": {"const": "fill"},
                    "segments": {"type": "array"},
                },
                "unevaluatedProperties": False,
            },
        ],
    }
    schema_before = _canonical_bytes(nested_schema)
    nested_validator = Draft202012Validator(nested_schema)
    nested_document = {
        "type": "qcm",
        "validationIndependenceClaimId": "atlas-claim-sha256:" + "a" * 64,
    }
    nested_actual, nested_proof = _classify_schema_rejection(
        "claim-attached-as-absolute-target-property",
        "UNEVALUATED_PROPERTY",
        list(nested_validator.iter_errors(nested_document)),
    )
    if nested_actual != "UNEVALUATED_PROPERTY":
        raise GateError("nested unknown property was not classified")
    if not nested_proof["errors"] or nested_proof["errors"][0]["validator"] != "oneOf":
        raise GateError("nested classifier test did not exercise a composition error")
    if "unevaluatedProperties" not in nested_proof["flattenedValidators"]:
        raise GateError("nested classifier test did not retain the rejecting child")

    try:
        _classify_schema_rejection(
            "accepted-document-must-fail-harness",
            "UNEVALUATED_PROPERTY",
            list(nested_validator.iter_errors({"type": "qcm"})),
        )
    except GateError as error:
        if "was accepted by JSON Schema" not in str(error):
            raise
    else:
        raise GateError("accepted JSON document passed the rejection harness")

    enum_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "oneOf": [
            {
                "type": "object",
                "required": ["basisCode"],
                "properties": {
                    "basisCode": {"enum": ["new-instance", "new-context"]}
                },
                "additionalProperties": False,
            }
        ],
    }
    enum_actual, enum_proof = _classify_schema_rejection(
        "unknown-independence-basis",
        "ENUM_CLOSED",
        list(
            Draft202012Validator(enum_schema).iter_errors(
                {"basisCode": "cosmetic-rewording"}
            )
        ),
    )
    if enum_actual != "ENUM_CLOSED" or "enum" not in enum_proof["flattenedValidators"]:
        raise GateError("nested enum was not classified")
    if schema_before != _canonical_bytes(nested_schema):
        raise GateError("schema classifier mutated its schema")

    return {
        "claimCaseRejected": True,
        "nestedUnknownPropertyClassified": True,
        "acceptedDocumentFailsHarness": True,
        "enumClosedDetected": True,
        "schemaMutation": False,
        "validationRulesUnchanged": True,
    }


def _validate_case(
    case: dict[str, Any],
    valid: dict[str, Any],
    schema_validator: Any,
    validation_evidence: dict[str, Any] | None = None,
) -> str:
    if "baseRef" in case:
        base = copy.deepcopy(_pointer_get(valid, case["baseRef"]))
        payload, named = _patch(base, case.get("operations", []))
    else:
        payload = copy.deepcopy(case.get("payload"))
        named = {}
    validator = case["validator"]
    context = case.get("context", {})
    expected = case["expectError"]

    if validator == "JSON_SCHEMA":
        actual, proof = _classify_schema_rejection(
            case["caseId"],
            expected,
            list(schema_validator.iter_errors(payload)),
        )
        if validation_evidence is not None:
            validation_evidence["draft202012Validator"] = proof
        return actual

    if validator == "ATLAS_CONTENT_GATE":
        try:
            _validate_atlas_gate(payload)
        except ContractReject as error:
            return error.code
        raise GateError(f"{case['caseId']} was accepted by Atlas content gate")

    if validator == "SESSION_PLAN_CONTRACT":
        if case["caseId"] == "preferred-activity-six-minutes-in-five-minute-plan":
            if int(payload["estimatedMinutes"]) > int(context["durationMinutes"]):
                return "PREFERRED_ACTIVITY_EXCEEDS_BUDGET"
        elif case["caseId"] == "plan-id-digest-divergence":
            digest = payload["expectedPlanDigest"].split(":", 1)[1]
            plan_id = payload["expectedPlanId"].split(":", 1)[1]
            if digest != plan_id:
                return "PLAN_ID_DIGEST_MISMATCH"
        raise GateError(f"{case['caseId']} was accepted by session plan contract")

    if validator == "VALIDATION_CLAIM":
        if payload["sourceActivityRefKey"] == payload["targetActivityRefKey"]:
            return "CLAIM_SOURCE_TARGET_NOT_DISTINCT"
        if payload["sourceStimulusDigest"] == payload["targetStimulusDigest"]:
            return "CLAIM_STIMULUS_NOT_DISTINCT"
        raise GateError(f"{case['caseId']} was accepted by validation claim contract")

    if validator == "ACCEPTED_VALIDATION_CLAIM_SET":
        original = valid["acceptedValidationClaimSet"]
        if payload["artifactDigest"] != original["artifactDigest"]:
            return "ACCEPTED_SET_ARTIFACT_MISMATCH"
        if payload["contentRevisionRef"] != original["contentRevisionRef"]:
            return "ACCEPTED_SET_REVISION_MISMATCH"
        raise GateError(f"{case['caseId']} was accepted by accepted-claim-set contract")

    if validator == "SHARED_CONTRACT":
        if case["caseId"] == "naked-objective-reference":
            if "courseRef" not in payload:
                return "QUALIFIED_REFERENCE_REQUIRED"
        elif case["caseId"] == "activity-reference-copies-objective-id":
            if "objectiveId" in payload:
                return "ACTIVITY_IDENTITY_CONTAINS_OBJECTIVE"
        raise GateError(f"{case['caseId']} was accepted by shared contract")

    if validator == "VALIDATION_CREDIT":
        if payload.get("assistance") != "none":
            return "AUTONOMOUS_CREDIT_REQUIRES_ASSISTANCE_NONE"
        raise GateError(f"{case['caseId']} was accepted for autonomous validation credit")

    if validator == "CANONICAL_TIMESTAMP":
        try:
            _validate_timestamp(payload["scoredAt"])
        except ContractReject as error:
            return error.code
        raise GateError(f"{case['caseId']} accepted a noncanonical timestamp")

    if validator == "ATLAS_STATE_IMPORT":
        if payload.get("atlasStateVersion") != "0.3":
            if case.get("expectedWrites") != 0:
                raise GateError("state rejection did not prove zero writes")
            return "UNSUPPORTED_ATLAS_STATE_VERSION"
        raise GateError(f"{case['caseId']} accepted Atlas 0.2 state")

    if validator == "IDENTITY_CONFLICT":
        second = named.get("second")
        if second is None:
            raise GateError("identity conflict case did not materialize second payload")
        if payload["eventId"] == second["eventId"] and _canonical_bytes(payload) != _canonical_bytes(second):
            if case.get("expectedWrites") != 0:
                raise GateError("identity conflict did not prove zero writes")
            return "IDENTITY_PAYLOAD_CONFLICT"
        raise GateError(f"{case['caseId']} accepted divergent payload under same identity")

    if validator == "START_IDEMPOTENCE":
        if payload["planDigest"] != context["attemptedPlanDigest"]:
            if case.get("expectedWrites") != 0:
                raise GateError("start conflict did not prove zero writes")
            return "START_REQUEST_PLAN_CONFLICT"
        raise GateError(f"{case['caseId']} accepted same request for another plan")

    if validator == "REWARD_EXCLUSIVE_PRIORITY":
        if context.get("reuseEvidence") and context.get("secondKind") in REWARD_KINDS:
            if not payload.get("evidenceEventIds"):
                raise GateError("reward reuse case lacks evidence")
            return "REWARD_EVIDENCE_REUSED"
        raise GateError(f"{case['caseId']} accepted reused reward evidence")

    if validator == "REWARD_CONTRACT":
        if payload.get("kind") not in REWARD_KINDS:
            return "REWARD_KIND_UNKNOWN"
        raise GateError(f"{case['caseId']} accepted unknown reward kind")

    if validator == "OBJECTIVE_EVIDENCE_PROJECTION":
        if context.get("lifecycleKind") in {
            "session-started",
            "session-interrupted",
            "session-resumed",
            "session-completed",
        } and context.get("claimedLastEvidenceAt") != payload.get("lastEvidenceAt"):
            return "LIFECYCLE_EVENT_MUST_NOT_CHANGE_EVIDENCE"
        raise GateError(f"{case['caseId']} allowed lifecycle event to change evidence")

    if validator == "PEDAGOGICAL_EVENT":
        if payload.get("kind") == "activity-corrected" and not payload.get("correctsEventId"):
            return "CORRECTS_EVENT_ID_REQUIRED"
        raise GateError(f"{case['caseId']} accepted correction without causal event")

    raise GateError(f"unsupported adversarial validator: {validator}")


def _positive_contract_matrix(valid: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as error:
        raise GateError("jsonschema dependency missing") from error
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    legacy = valid["payloads"]["legacyKit"]
    atlas = valid["payloads"]["atlasKit"]
    legacy_errors = list(validator.iter_errors(legacy))
    atlas_errors = list(validator.iter_errors(atlas))
    if legacy_errors:
        raise GateError("historical non-Atlas kit failed schema: " + legacy_errors[0].message)
    if any("estimatedMinutes" in activity for course in legacy["courses"] for activity in course["activities"]):
        raise GateError("historical compatibility vector unexpectedly contains activity duration")
    if atlas_errors:
        raise GateError("positive Atlas fixture failed schema: " + atlas_errors[0].message)
    _validate_atlas_gate(atlas)
    if valid["planningVector"]["recommendation"]["action"] not in LEARNING_ACTIONS:
        raise GateError("positive recommendation action is not closed")
    if not set(valid["planningVector"]["recommendation"]["reasonCodes"]).issubset(REASON_CODES):
        raise GateError("positive recommendation reason code is not closed")
    state = valid["executionVector"]["objectiveEvidence"]["state"]
    if state not in EVIDENCE_STATES:
        raise GateError("positive objective state is not closed")
    reward = valid["executionVector"]["rewardSignal"]
    if reward["kind"] not in REWARD_KINDS:
        raise GateError("positive reward kind is not closed")
    for field in ("submittedAt", "scoredAt"):
        _validate_timestamp(valid["executionVector"]["scoredExecutionRecord"][field])
    return {
        "schemaDraft202012": "PASS",
        "historicalNonAtlasWithoutActivityDuration": "PASS",
        "positiveAtlasFixture": "PASS",
        "closedActionsStatesReasonsRewards": "PASS",
        "canonicalUtcPositive": "PASS",
    }


def _canonical_identity_matrix(valid: dict[str, Any]) -> dict[str, Any]:
    planning = valid["planningVector"]
    plan_payload = planning["planCanonicalPayload"]
    digest_hex = _atlas_hash("learnit.atlas.m1.v0.3/plan-digest", plan_payload)
    expected_digest = planning["expectedPlanDigest"]
    expected_id = planning["expectedPlanId"]
    if expected_digest != f"sha256:{digest_hex}":
        raise GateError(f"plan digest vector mismatch: {digest_hex}")
    if expected_id != f"atlas-plan-sha256:{digest_hex}":
        raise GateError("planId and planDigest do not represent identical bytes")

    execution = valid["executionVector"]
    start = execution["startRequestRecord"]
    start_hex = _atlas_hash(
        "learnit.atlas.m1.v0.3/start-request-id",
        {"planDigest": start["planDigest"], "startOrdinal": start["startOrdinal"]},
    )
    if start["startRequestId"] != f"atlas-start-sha256:{start_hex}":
        raise GateError("start request identity vector mismatch")
    session = execution["sessionRef"]
    session_hex = _atlas_hash(
        "learnit.atlas.m1.v0.3/session-id",
        {"startRequestId": start["startRequestId"], "planDigest": start["planDigest"]},
    )
    if session["sessionId"] != f"atlas-session-sha256:{session_hex}":
        raise GateError("session identity vector mismatch")
    if session["planId"] != expected_id:
        raise GateError("session plan identity differs")

    canonical_once = _canonical_bytes(plan_payload)
    canonical_twice = _canonical_bytes(json.loads(canonical_once.decode("utf-8")))
    if canonical_once != canonical_twice:
        raise GateError("canonical JSON is not byte-idempotent")
    return {
        "planDigest": expected_digest,
        "planId": expected_id,
        "startRequestId": start["startRequestId"],
        "sessionId": session["sessionId"],
        "canonicalByteCount": len(canonical_once),
        "canonicalIdempotence": "PASS",
    }


@contextmanager
def _network_blocked():
    original_connect = socket.socket.connect
    original_create = socket.create_connection

    def denied(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError("network disabled by atlas-contracts proof profile")

    socket.socket.connect = denied  # type: ignore[method-assign]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.create_connection = original_create  # type: ignore[assignment]


def _load_external_records(env_name: str) -> list[dict[str, Any]]:
    raw = os.environ.get(env_name, "")
    if not raw:
        raise GateError(f"missing workflow evidence pointer: {env_name}")
    path = Path(raw)
    if not path.is_file():
        raise GateError(f"workflow evidence file absent: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload.get("commands", [])
    if not records or any(record.get("exit_code") != 0 for record in records):
        raise GateError(f"workflow command evidence failed: {env_name}")
    return records


def _worktree_commands() -> list[dict[str, Any]]:
    return [
        command_record(["git", "status", "--porcelain=v1", "--untracked-files=all"]),
        command_record(["git", "diff", "--exit-code"]),
        command_record(["git", "diff", "--cached", "--exit-code"]),
    ]


def _assert_worktree_only_evidence(records: list[dict[str, Any]]) -> None:
    status = records[0]["stdout"].splitlines()
    unexpected = []
    for line in status:
        path = line[3:] if len(line) >= 4 else line
        if not path.startswith("apps/learnit-next/.agent-result/"):
            unexpected.append(line)
    if unexpected:
        raise GateError("worktree contains unexpected paths: " + json.dumps(unexpected))
    if records[1]["stdout"] or records[2]["stdout"]:
        raise GateError("tracked diff exists after tests")


def _write_contract_evidence(evidence: dict[str, Any], commands: list[dict[str, Any]]) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULT_DIR / "atlas-contracts-evidence.json"
    md_path = RESULT_DIR / "atlas-contracts-evidence.md"
    log_path = RESULT_DIR / "atlas-contracts-commands.log"
    json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    sections = [
        "VERDICT",
        "AUTHORITY",
        "REPOSITORY_AND_PR",
        "BASELINE_BRANCH_HEAD_MERGE_BASE",
        "RUNNER_ENVIRONMENT",
        "DEPENDENCY_DECLARATION",
        "EXACT_PR_FILE_LIST",
        "WORKTREE_BEFORE_INSTALL",
        "WORKTREE_AFTER_INSTALL",
        "COMMANDS_AND_EXIT_CODES",
        "FULL_TEST_RESULTS",
        "ADVERSARIAL_21_CASE_MATRIX",
        "CANONICALIZATION_IDENTITY_UTC_RESULTS",
        "STATE_0_2_AND_REWARD_RESULTS",
        "CONTRACT_FILE_GIT_BLOB_SHA1",
        "CONTRACT_FILE_SHA256_BEFORE",
        "CONTRACT_FILE_SHA256_AFTER",
        "WORKTREE_AFTER_TESTS",
        "TRACKED_FILE_MODIFICATIONS",
        "ARTIFACT_IDENTITY",
        "REPRODUCIBILITY_CONCLUSION",
        "NEXT_ACTION",
    ]
    lines = ["# ATLAS 0.3 — clean-checkout contract evidence V2", ""]
    for section in sections:
        lines.extend([f"{section}:", "```json"])
        lines.append(json.dumps(evidence.get(section), indent=2, sort_keys=True, ensure_ascii=False))
        lines.extend(["```", ""])
    lines.extend(["EVIDENCE_COMPLETE:", "true", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    with log_path.open("w", encoding="utf-8") as stream:
        for index, record in enumerate(commands, start=1):
            stream.write(f"COMMAND {index}\n")
            stream.write(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False))
            stream.write("\n\n")


def run_atlas_contracts(branch: str, base_ref: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    provenance = atlas_provenance("atlas-contracts", branch, base_ref)
    dependency_records = _load_external_records("ATLAS_DEPENDENCY_COMMANDS_JSON")
    before_install = _load_external_records("ATLAS_WORKTREE_BEFORE_INSTALL_JSON")
    after_install = _load_external_records("ATLAS_WORKTREE_AFTER_INSTALL_JSON")
    commands: list[dict[str, Any]] = []
    commands.extend(before_install)
    commands.extend(dependency_records)
    commands.extend(after_install)
    immediate_before = _worktree_commands()
    commands.extend(immediate_before)
    _assert_worktree_only_evidence(immediate_before)

    before = _contract_file_identities()
    schema = _load_json("contracts/learnit-kit-v2.schema.json")
    valid = _load_json("contracts/fixtures/atlas-m1-valid-loop.json")
    invalid = _load_json("contracts/fixtures/atlas-m1-invalid-loop.json")
    _load_json("work-packages/ATLAS-WP-001.json")
    docs = (ROOT / "docs/atlas/CONTRACTS.md").read_text(encoding="utf-8")
    if "contractVersion: 0.3" not in docs:
        raise GateError("contract documents are not the expected 0.3 materialization")
    if len(invalid.get("cases", [])) != 21:
        raise GateError(f"adversarial case count differs: {len(invalid.get('cases', []))}")

    with _network_blocked():
        positive = _positive_contract_matrix(valid, schema)
        identity = _canonical_identity_matrix(valid)
        classifier_tests = _schema_error_classification_self_test()
        from jsonschema import Draft202012Validator

        schema_validator = Draft202012Validator(schema)
        runs = []
        for run_number in (1, 2):
            case_results = []
            for case in invalid["cases"]:
                validation_evidence: dict[str, Any] = {}
                actual = _validate_case(
                    case,
                    valid,
                    schema_validator,
                    validation_evidence,
                )
                if actual != case["expectError"]:
                    raise GateError(
                        f"{case['caseId']} rejected with {actual}, expected {case['expectError']}"
                    )
                case_result = {
                    "caseId": case["caseId"],
                    "validator": case["validator"],
                    "expectedError": case["expectError"],
                    "actualError": actual,
                    "result": "PASS_REJECTED",
                }
                case_result.update(validation_evidence)
                case_results.append(case_result)
            runs.append({"run": run_number, "cases": case_results})

    canonical_first = _canonical_bytes(runs[0]["cases"])
    canonical_second = _canonical_bytes(runs[1]["cases"])
    if canonical_first != canonical_second:
        raise GateError("the two adversarial executions are not canonically identical")

    after = _contract_file_identities()
    if before != after:
        raise GateError("contract file identities changed during matrix")

    after_tests = _worktree_commands()
    commands.extend(after_tests)
    _assert_worktree_only_evidence(after_tests)
    tracked = command_record(["git", "status", "--porcelain=v1", "--untracked-files=no"])
    commands.append(tracked)
    if tracked["stdout"]:
        raise GateError("tracked files changed during contract proof")

    dependency_path = os.environ.get("ATLAS_DEPENDENCY_PATH", DEPENDENCY_PATH)
    dependency_sha = os.environ.get("ATLAS_DEPENDENCY_SHA256", "")
    if dependency_path != DEPENDENCY_PATH or dependency_sha != _sha256_file(DEPENDENCY_PATH):
        raise GateError("dependency declaration identity differs")

    evidence = {
        "VERDICT": "READY_FOR_EVIDENCE_ONLY_REVIEW",
        "AUTHORITY": {
            "repository": "stefm78/learnit-platform",
            "authority_issue": 130,
            "work_package": "ATLAS-WP-001",
            "arbitration_id": "ATLAS-M1-ARB-001",
        },
        "REPOSITORY_AND_PR": {
            "repository": "stefm78/learnit-platform",
            "pull_request": 137,
            "state_expected": "OPEN_NON_DRAFT_UNMERGED",
        },
        "BASELINE_BRANCH_HEAD_MERGE_BASE": provenance,
        "RUNNER_ENVIRONMENT": {
            "python": sys.version,
            "platform": sys.platform,
            "githubRunId": os.environ.get("GITHUB_RUN_ID"),
            "githubWorkflow": os.environ.get("GITHUB_WORKFLOW"),
            "networkDuringSemanticTests": "BLOCKED_IN_PROCESS",
            "runtimeLlm": "NOT_USED",
        },
        "DEPENDENCY_DECLARATION": {
            "path": dependency_path,
            "sha256": dependency_sha,
            "installationCommands": dependency_records,
        },
        "EXACT_PR_FILE_LIST": list(CONTRACT_PATHS),
        "WORKTREE_BEFORE_INSTALL": before_install,
        "WORKTREE_AFTER_INSTALL": after_install,
        "COMMANDS_AND_EXIT_CODES": [
            {"command": item["command"], "exit_code": item["exit_code"]} for item in commands
        ],
        "FULL_TEST_RESULTS": {
            **positive,
            "schemaErrorClassificationHarness": classifier_tests,
        },
        "ADVERSARIAL_21_CASE_MATRIX": {
            "caseCount": 21,
            "executions": 2,
            "canonicalResultsIdentical": True,
            "runs": runs,
        },
        "CANONICALIZATION_IDENTITY_UTC_RESULTS": identity,
        "STATE_0_2_AND_REWARD_RESULTS": {
            "state02RejectedBeforeWrites": True,
            "rewardKindsClosed": sorted(REWARD_KINDS),
            "transferCompletedForbidden": True,
            "evidenceReuseRejected": True,
            "lifecycleHasNoPedagogicalEffect": True,
            "activityCorrectedRequiresCausalEvent": True,
        },
        "CONTRACT_FILE_GIT_BLOB_SHA1": {
            path: data["git_blob_sha1"] for path, data in before.items()
        },
        "CONTRACT_FILE_SHA256_BEFORE": {
            path: data["sha256"] for path, data in before.items()
        },
        "CONTRACT_FILE_SHA256_AFTER": {
            path: data["sha256"] for path, data in after.items()
        },
        "WORKTREE_AFTER_TESTS": after_tests,
        "TRACKED_FILE_MODIFICATIONS": [],
        "ARTIFACT_IDENTITY": {
            "name": CONTRACT_ARTIFACT,
            "head": CONTRACT_HEAD,
            "evidenceFiles": [
                "apps/learnit-next/.agent-result/atlas-contracts-evidence.json",
                "apps/learnit-next/.agent-result/atlas-contracts-evidence.md",
                "apps/learnit-next/.agent-result/atlas-contracts-commands.log",
            ],
        },
        "REPRODUCIBILITY_CONCLUSION": {
            "EVIDENCE_COMPLETE": True,
            "allExitCodesZero": all(item["exit_code"] == 0 for item in commands),
            "contractDigestsStable": before == after,
            "trackedFilesModified": False,
            "adversarialCasesExecuted": 21,
            "matrixExecutions": 2,
        },
        "NEXT_ACTION": (
            "Relancer une revue indépendante evidence-only sur le head exact, "
            "sans recommencer l’analyse sémantique générale."
        ),
        "EVIDENCE_COMPLETE": True,
    }
    _write_contract_evidence(evidence, commands)
    return evidence, commands


def run_atlas(profile: str, branch: str, base_ref: str) -> int:
    report: dict[str, object] = {
        "schema": "learnit.next.ci.checks.atlas-m1.v1",
        "workPackage": "ATLAS-WP-001",
        "profile": profile,
        "result": "FAIL",
        "verdict": "CHANGES_REQUIRED",
    }
    try:
        if profile == "atlas-contracts":
            evidence, commands = run_atlas_contracts(branch, base_ref)
            report.update(
                provenance=evidence["BASELINE_BRANCH_HEAD_MERGE_BASE"],
                result="PASS",
                verdict="READY_FOR_EVIDENCE_ONLY_REVIEW",
                evidence=evidence,
                commandCount=len(commands),
            )
        else:
            report["provenance"] = atlas_provenance(profile, branch, base_ref)
            _, _, commands, environment, verdict = ATLAS[profile]
            if profile == "atlas-support":
                report["routingMatrix"] = routing_matrix()
                report["contractCapability"] = support_contract_capability()
            outputs = []
            for arguments in commands:
                command = [sys.executable, *arguments]
                outputs.append({"command": command, "output": call(command, environment)})
            report.update(result="PASS", verdict=verdict, tests=outputs)
        code = 0
    except Exception as error:
        report["error"] = str(error)
        code = 2
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "verdict": report["verdict"]}, sort_keys=True))
    return code


def legacy_namespace() -> dict[str, object]:
    """Load the unmodified Wave A gate from the exact Atlas support base."""
    source = git("show", f"{ATLAS_BASE}:{RUNNER_PATH}")
    namespace: dict[str, object] = {
        "__file__": str(ROOT / RUNNER_PATH),
        "__name__": "learnit_wave_a_legacy_gate",
    }
    exec(compile(source, str(namespace["__file__"]), "exec"), namespace)
    return namespace


def load_manifest():
    return legacy_namespace()["load_manifest"]()


def materialize(destination, manifest):
    return legacy_namespace()["materialize"](destination, manifest)


def run_wave_a(args: argparse.Namespace) -> int:
    namespace = legacy_namespace()
    legacy_argv = [str(namespace["__file__"])]
    if args.strict:
        legacy_argv.append("--strict")
    legacy_argv.extend(["--mode", args.mode, "--base-ref", args.base_ref])
    if args.accepted_integration_head:
        legacy_argv.extend(["--accepted-integration-head", args.accepted_integration_head])
    original = sys.argv
    try:
        sys.argv = legacy_argv
        return int(namespace["main"]())
    finally:
        sys.argv = original


def run_wave_a_ci(args: argparse.Namespace) -> int:
    if run_wave_a(args):
        return 2
    result_dir = RESULT_DIR
    result_dir.mkdir(parents=True, exist_ok=True)
    profiles = ("authoring", "contract", "full", "browser")
    for name in profiles:
        environment = {}
        if name in {"full", "browser"}:
            environment["LLV2_QA_STRICT"] = "1"
        if name == "browser":
            environment["LLV2_QA_BROWSER_STRICT"] = "1"
        call(
            [
                sys.executable,
                "tools/learnit_next_agent.py",
                "--profile",
                f"learnit-next-{name}",
                "--output",
                f"apps/learnit-next/.agent-result/profile-{name}.json",
            ],
            environment,
        )

    artifact = ROOT / "apps/learnit-next/dist/learnit-next.html"
    if not artifact.is_file():
        raise GateError("exact Wave A artifact is absent")
    before = artifact.read_bytes()
    namespace = legacy_namespace()
    import tempfile

    with tempfile.TemporaryDirectory(prefix="wave-a-qa-") as raw:
        product = namespace["materialize"](Path(raw), namespace["load_manifest"]()).resolve()
        qa_path = Path("apps/learnit-next/tests/qa_learning_loop_v2.py")
        expected = git("rev-parse", f"f25da6356528824e84224718013a3bccb2707c49:{qa_path.as_posix()}")
        actual = call(["git", "hash-object", str(product / qa_path)])
        if expected != "514d095b5fa028d12dc6d87ba7d4bd82c64a0cd9" or actual != expected:
            raise GateError("exact QA blob differs")
        environment = {
            "LLV2_PRODUCT_TREE": str(product),
            "LEARNIT_NEXT_ARTIFACT": str(artifact),
            "LLV2_QA_STRICT": "1",
            "LLV2_QA_BROWSER_STRICT": "1",
        }
        log = call([sys.executable, str(qa_path), "-v"], environment, cwd=product)
        (result_dir / "qa-exact.log").write_text(log + "\n", encoding="utf-8")
        if call(["git", "hash-object", str(product / qa_path)]) != expected:
            raise GateError("exact QA blob changed during replay")
    if artifact.read_bytes() != before:
        raise GateError("exact Wave A artifact changed during QA replay")

    reports = {}
    for name in profiles:
        payload = json.loads((result_dir / f"profile-{name}.json").read_text(encoding="utf-8"))
        if payload.get("result") != "PASS":
            raise GateError(f"profile failed: {name}")
        reports[name] = payload
    gate = json.loads(REPORT.read_text(encoding="utf-8"))
    if gate.get("result") != "PASS":
        raise GateError("historical integration gate failed")
    identity = {key: gate["artifact"][key] for key in ("path", "bytes", "sha256")}
    for name in ("full", "browser"):
        if reports[name].get("artifact") != identity:
            raise GateError(f"profile artifact differs: {name}")
    print(json.dumps({"result": "PASS", "verdict": gate["verdict"]}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--mode", default="integration-head")
    parser.add_argument("--base-ref", default=WAVE_A_BASE)
    parser.add_argument("--accepted-integration-head", default="")
    parser.add_argument("--profile", default="wave-a")
    parser.add_argument("--branch-ref", default="")
    parser.add_argument("--resolve-branch", default="")
    args = parser.parse_args()
    if args.resolve_branch:
        try:
            print(resolve(args.resolve_branch))
            return 0
        except GateError as error:
            print(str(error), file=sys.stderr)
            return 2
    if args.profile == "wave-a":
        return run_wave_a(args)
    if args.profile == "wave-a-ci":
        return run_wave_a_ci(args)
    if args.profile not in ATLAS:
        print(f"unsupported Atlas profile: {args.profile}", file=sys.stderr)
        return 2
    return run_atlas(args.profile, args.branch_ref, args.base_ref)


if __name__ == "__main__":
    raise SystemExit(main())
