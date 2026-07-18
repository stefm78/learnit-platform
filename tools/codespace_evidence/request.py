"""Fail-closed request parsing and verified GitHub-origin binding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable

from . import OPERATIONS, REQUEST_MARKER, SCHEMA_VERSION

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
JOB_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,79}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PROFILE_NAMES = frozenset({"repository", "learnit-next-strict", "player-fast", "player-full"})
ORIGIN_TYPES = frozenset({"issue", "pull_request"})
TARGET_TYPES = frozenset({"commit", "pull_request"})

LAUNCH_FIELDS = frozenset({"repository", "origin_type", "origin_number", "request_comment_id"})
REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "job_id",
        "operation",
        "repository",
        "target_type",
        "target_number",
        "target_sha",
        "origin",
        "created_at",
        "timeout_seconds",
        "parameters",
        "allow_new_attempt",
    }
)
ORIGIN_FIELDS = frozenset({"type", "number", "request_comment_id"})
PARAMETER_FIELDS = frozenset({"test_profile", "required_checks", "include_logs", "include_artifacts"})


class RequestError(RuntimeError):
    """Raised when a request or launch descriptor is not exactly valid."""


class DuplicateKeyError(RequestError):
    """Raised when JSON contains duplicate object keys."""


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_exact(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_no_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(RequestError(f"invalid JSON constant: {value}")),
        )
    except DuplicateKeyError:
        raise
    except RequestError:
        raise
    except json.JSONDecodeError as exc:
        raise RequestError(f"invalid JSON: {exc}") from exc


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON used for request digests."""
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RequestError(f"request is not canonically serializable: {exc}") from exc
    return text.encode("utf-8")


def request_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _exact_fields(value: dict[str, Any], allowed: frozenset[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise RequestError(f"{label} contains unknown fields: {', '.join(unknown)}")


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RequestError(f"{label} must be a positive integer")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise RequestError(f"{label} must be a non-empty string")
    return value


@dataclass(frozen=True)
class LaunchDescriptor:
    repository: str
    origin_type: str
    origin_number: int
    request_comment_id: int

    @classmethod
    def from_path(cls, path: Path) -> "LaunchDescriptor":
        value = loads_exact(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RequestError("launch descriptor must be a JSON object")
        _exact_fields(value, LAUNCH_FIELDS, "launch descriptor")
        missing = sorted(LAUNCH_FIELDS - set(value))
        if missing:
            raise RequestError(f"launch descriptor is missing fields: {', '.join(missing)}")
        repository = _string(value["repository"], "repository")
        if not REPOSITORY_RE.fullmatch(repository):
            raise RequestError("repository must use owner/name form")
        origin_type = _string(value["origin_type"], "origin_type")
        if origin_type not in ORIGIN_TYPES:
            raise RequestError("origin_type must be issue or pull_request")
        return cls(
            repository=repository,
            origin_type=origin_type,
            origin_number=_positive_int(value["origin_number"], "origin_number"),
            request_comment_id=_positive_int(value["request_comment_id"], "request_comment_id"),
        )


@dataclass(frozen=True)
class Origin:
    type: str
    number: int
    request_comment_id: int


@dataclass(frozen=True)
class Parameters:
    test_profile: str | None
    required_checks: tuple[str, ...]
    include_logs: bool
    include_artifacts: bool


@dataclass(frozen=True)
class EvidenceRequest:
    schema_version: str
    job_id: str
    operation: str
    repository: str
    target_type: str
    target_number: int | None
    target_sha: str
    origin: Origin
    created_at: str
    timeout_seconds: int
    parameters: Parameters
    allow_new_attempt: bool
    digest_sha256: str
    raw: dict[str, Any]

    @classmethod
    def from_value(cls, value: Any, digest: str) -> "EvidenceRequest":
        if not isinstance(value, dict):
            raise RequestError("request must be a JSON object")
        _exact_fields(value, REQUEST_FIELDS, "request")
        required = REQUEST_FIELDS - {"target_number", "allow_new_attempt"}
        missing = sorted(required - set(value))
        if missing:
            raise RequestError(f"request is missing fields: {', '.join(missing)}")

        schema_version = _string(value["schema_version"], "schema_version")
        if schema_version != SCHEMA_VERSION:
            raise RequestError(f"unsupported schema_version: {schema_version}")

        job_id = _string(value["job_id"], "job_id")
        if not JOB_ID_RE.fullmatch(job_id):
            raise RequestError("job_id has an invalid format")

        operation = _string(value["operation"], "operation")
        if operation not in OPERATIONS:
            raise RequestError(f"unsupported operation: {operation}")

        repository = _string(value["repository"], "repository")
        if not REPOSITORY_RE.fullmatch(repository):
            raise RequestError("repository must use owner/name form")

        target_type = _string(value["target_type"], "target_type")
        if target_type not in TARGET_TYPES:
            raise RequestError("target_type must be commit or pull_request")

        target_sha_value = value["target_sha"]
        if not isinstance(target_sha_value, str) or not SHA_RE.fullmatch(target_sha_value):
            raise RequestError("target_sha must be a full lowercase 40-character SHA")
        target_sha = target_sha_value

        target_number_value = value.get("target_number")
        target_number = None if target_number_value is None else _positive_int(target_number_value, "target_number")

        origin_value = value["origin"]
        if not isinstance(origin_value, dict):
            raise RequestError("origin must be an object")
        _exact_fields(origin_value, ORIGIN_FIELDS, "origin")
        missing_origin = sorted(ORIGIN_FIELDS - set(origin_value))
        if missing_origin:
            raise RequestError(f"origin is missing fields: {', '.join(missing_origin)}")
        origin_type = _string(origin_value["type"], "origin.type")
        if origin_type not in ORIGIN_TYPES:
            raise RequestError("origin.type must be issue or pull_request")
        origin = Origin(
            type=origin_type,
            number=_positive_int(origin_value["number"], "origin.number"),
            request_comment_id=_positive_int(origin_value["request_comment_id"], "origin.request_comment_id"),
        )

        created_at = _string(value["created_at"], "created_at")
        try:
            parsed_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RequestError("created_at must be an ISO-8601 timestamp") from exc
        if parsed_at.tzinfo is None:
            raise RequestError("created_at must include a timezone")
        parsed_at.astimezone(timezone.utc)

        timeout_seconds = value["timeout_seconds"]
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 30 <= timeout_seconds <= 3600:
            raise RequestError("timeout_seconds must be an integer between 30 and 3600")

        parameters_value = value["parameters"]
        if not isinstance(parameters_value, dict):
            raise RequestError("parameters must be an object")
        _exact_fields(parameters_value, PARAMETER_FIELDS, "parameters")
        test_profile = parameters_value.get("test_profile")
        if test_profile is not None:
            test_profile = _string(test_profile, "parameters.test_profile")
            if test_profile not in PROFILE_NAMES:
                raise RequestError(f"unsupported test profile: {test_profile}")
        required_checks_value = parameters_value.get("required_checks", [])
        if not isinstance(required_checks_value, list) or not all(isinstance(item, str) and item for item in required_checks_value):
            raise RequestError("parameters.required_checks must be a string list")
        if len(set(required_checks_value)) != len(required_checks_value):
            raise RequestError("parameters.required_checks contains duplicates")
        include_logs = parameters_value.get("include_logs", False)
        include_artifacts = parameters_value.get("include_artifacts", False)
        if not isinstance(include_logs, bool) or not isinstance(include_artifacts, bool):
            raise RequestError("include_logs and include_artifacts must be booleans")
        parameters = Parameters(
            test_profile=test_profile,
            required_checks=tuple(required_checks_value),
            include_logs=include_logs,
            include_artifacts=include_artifacts,
        )

        allow_new_attempt = value.get("allow_new_attempt", False)
        if not isinstance(allow_new_attempt, bool):
            raise RequestError("allow_new_attempt must be boolean")

        if operation in {"pr-snapshot", "pr-governor-evidence"}:
            if target_type != "pull_request" or target_number is None:
                raise RequestError(f"{operation} requires target_type=pull_request and target_number")
            if test_profile is not None:
                raise RequestError(f"{operation} does not accept test_profile")
        else:
            if target_type != "commit" or target_number is not None:
                raise RequestError(f"{operation} requires target_type=commit and no target_number")
            if operation == "run-test-profile" and test_profile is None:
                raise RequestError("run-test-profile requires parameters.test_profile")
            if operation == "run-repository-validation" and test_profile is not None:
                raise RequestError("run-repository-validation does not accept test_profile")
            if required_checks_value or include_logs or include_artifacts:
                raise RequestError(f"{operation} does not accept GitHub evidence parameters")

        return cls(
            schema_version=schema_version,
            job_id=job_id,
            operation=operation,
            repository=repository,
            target_type=target_type,
            target_number=target_number,
            target_sha=target_sha,
            origin=origin,
            created_at=created_at,
            timeout_seconds=timeout_seconds,
            parameters=parameters,
            allow_new_attempt=allow_new_attempt,
            digest_sha256=digest,
            raw=value,
        )


def parse_request_envelope(body: str) -> tuple[dict[str, Any], str]:
    if body.count(REQUEST_MARKER) != 1:
        raise RequestError(f"expected exactly one {REQUEST_MARKER} marker")
    digest_matches = re.findall(r"(?m)^request_sha256:\s*([0-9a-f]{64})\s*$", body)
    if len(digest_matches) != 1:
        raise RequestError("expected exactly one lowercase request_sha256 line")
    fences = re.findall(r"```json\s*\n(.*?)\n```", body, flags=re.DOTALL)
    if len(fences) != 1:
        raise RequestError("expected exactly one fenced JSON request")
    value = loads_exact(fences[0])
    if not isinstance(value, dict):
        raise RequestError("fenced request must be a JSON object")
    actual = request_digest(value)
    expected = digest_matches[0]
    if actual != expected:
        raise RequestError(f"request digest mismatch: expected {expected}, calculated {actual}")
    return value, actual


def verify_bound_request(
    descriptor: LaunchDescriptor,
    comment: dict[str, Any],
    *,
    expected_issue_url: str,
) -> EvidenceRequest:
    issue_url = comment.get("issue_url")
    if issue_url != expected_issue_url:
        raise RequestError("request comment is not attached to the declared origin object")
    comment_id = comment.get("id")
    if comment_id != descriptor.request_comment_id:
        raise RequestError("request comment identity mismatch")
    body = comment.get("body")
    if not isinstance(body, str):
        raise RequestError("request comment has no text body")
    value, digest = parse_request_envelope(body)
    request = EvidenceRequest.from_value(value, digest)
    if request.repository != descriptor.repository:
        raise RequestError("request repository differs from launch descriptor")
    if request.origin.type != descriptor.origin_type:
        raise RequestError("request origin type differs from launch descriptor")
    if request.origin.number != descriptor.origin_number:
        raise RequestError("request origin number differs from launch descriptor")
    if request.origin.request_comment_id != descriptor.request_comment_id:
        raise RequestError("request comment id differs from launch descriptor")
    return request


def verify_request_with_fetcher(
    descriptor: LaunchDescriptor,
    fetcher: Callable[[str, int], dict[str, Any]],
) -> EvidenceRequest:
    expected_issue_url = f"https://api.github.com/repos/{descriptor.repository}/issues/{descriptor.origin_number}"
    comment = fetcher(descriptor.repository, descriptor.request_comment_id)
    return verify_bound_request(descriptor, comment, expected_issue_url=expected_issue_url)
