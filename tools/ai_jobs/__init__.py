"""Credential-free deterministic core for Gate 1 sequential coordination.

The package constants are data-only.  Privileged GitHub transport, credentials
and Gate 0 effects live outside this core.
"""
from __future__ import annotations

SCHEMA_VERSION = "learnit.gate1.queue.v1"
LEDGER_MARKER = "AI_GATE1_LEDGER_V1"
GRANT_MARKER = "AI_GATE1_SESSION_GRANT_V1"
SUSPEND_MARKER = "AI_GATE1_SUSPEND_V1"

MAX_COMMENTS_PER_ISSUE = 10_000
MAX_ISSUES_PER_GENERATION = 8
MAX_LEDGERS_PER_GENERATION = 8
MAX_RECORDS_PER_GENERATION = 50_000
MAX_GENERATION = 4_096
MAX_CHUNK_BYTES = 1_048_576
MAX_SNAPSHOT_BYTES = 16_777_216

GLOBAL_BOUND_LIMITS = {
    "generation": MAX_GENERATION,
    "issue_count": MAX_ISSUES_PER_GENERATION,
    "comment_count": MAX_COMMENTS_PER_ISSUE,
    "ledger_count": MAX_LEDGERS_PER_GENERATION,
    "record_count": MAX_RECORDS_PER_GENERATION,
    "snapshot_size_bytes": MAX_SNAPSHOT_BYTES,
    "max_chunk_size_bytes": MAX_CHUNK_BYTES,
}

GATE0_OPERATIONS = frozenset({
    "pr-snapshot",
    "pr-governor-evidence",
    "run-repository-validation",
    "run-test-profile",
})

FORBIDDEN_RUNTIME_CAPABILITIES = frozenset({
    "codespace-create",
    "codespace-start",
    "codespace-restart",
    "generic-shell",
    "branch-create",
    "commit",
    "push",
    "workflow-dispatch",
    "merge",
    "release",
    "promotion",
    "governor-decision",
    "gate2-fan-in",
    "gate3-repository-write-job",
    "gate4-parallel-execution",
})
