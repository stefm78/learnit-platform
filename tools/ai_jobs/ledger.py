"""Append-only Gate 1 ledger reconstruction and rendering."""
from __future__ import annotations

import hashlib
import json
from typing import Iterable

from . import LEDGER_MARKER, MAX_RECORDS_PER_GENERATION
from .contracts import ContractError, LedgerRecord, canonical_json_bytes


def validate_chain(records: Iterable[LedgerRecord]) -> tuple[LedgerRecord, ...]:
    ordered = tuple(sorted(records, key=lambda item: item.sequence))
    if len(ordered) > MAX_RECORDS_PER_GENERATION:
        raise ContractError("ledger record count exceeds global bound")
    previous: str | None = None
    expected_sequence = 1
    seen: set[str] = set()
    for record in ordered:
        if record.sequence != expected_sequence:
            raise ContractError("ledger sequence is not contiguous")
        if record.previous_record_sha256 != previous:
            raise ContractError("ledger previous-record binding mismatch")
        if record.record_sha256 in seen:
            raise ContractError("duplicate ledger record digest")
        material = record.as_dict()
        claimed = material.pop("record_sha256")
        actual = hashlib.sha256(canonical_json_bytes(material)).hexdigest()
        if claimed != actual:
            raise ContractError("ledger record digest is invalid")
        seen.add(claimed)
        previous = claimed
        expected_sequence += 1
    return ordered


def render_record(record: LedgerRecord) -> str:
    payload = record.as_dict()
    body = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    )
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return (
        f"{LEDGER_MARKER}\n"
        f"payload_sha256: {digest}\n"
        "```json\n"
        f"{body}\n"
        "```"
    )
