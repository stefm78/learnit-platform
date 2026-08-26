"""Gate 1 — GitHub-authoritative sequential multi-AI queue.

This package is an operational coordinator above the accepted Gate 0 evidence
bridge.  It deliberately does not expose repository writes, arbitrary commands,
Codespace start/restart, merge, release, promotion, fan-in, or parallel execution.
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
