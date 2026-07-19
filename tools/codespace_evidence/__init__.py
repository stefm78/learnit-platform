"""Portable Gate 0 Codespace Evidence Bridge."""

from __future__ import annotations

SCHEMA_VERSION = "learnit.codespace-evidence.request.v1"
OUTCOME_SCHEMA_VERSION = "learnit.codespace-evidence.outcome.v1"
REQUEST_MARKER = "AI_CODESPACE_REQUEST_V1"
OUTCOME_MARKER = "AI_CODESPACE_OUTCOME_V1"
STATEMENT = "Evidence only. This outcome is not a governor decision."
PUBLICATION_LIMIT_BYTES = 58_000

OPERATIONS = frozenset(
    {
        "pr-snapshot",
        "pr-governor-evidence",
        "run-repository-validation",
        "run-test-profile",
    }
)

CLASSIFICATIONS = frozenset(
    {
        "DIAGNOSTIC",
        "TEST_RESULT",
        "EVIDENCE_CANDIDATE",
        "STALE_TARGET",
        "STALE_AFTER_EXECUTION",
        "FAIL_ENVIRONMENT",
        "FAIL_HARNESS",
        "FAIL_TOPOLOGY",
        "FAIL_PRODUCT",
        "INCONCLUSIVE",
    }
)

__all__ = [
    "CLASSIFICATIONS",
    "OPERATIONS",
    "OUTCOME_MARKER",
    "OUTCOME_SCHEMA_VERSION",
    "PUBLICATION_LIMIT_BYTES",
    "REQUEST_MARKER",
    "SCHEMA_VERSION",
    "STATEMENT",
]
