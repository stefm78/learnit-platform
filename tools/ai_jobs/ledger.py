"""Append-only Gate 1 ledger reconstruction and canonical rendering."""
from __future__ import annotations

import hashlib
from typing import Iterable

from . import LEDGER_MARKER, MAX_RECORDS_PER_GENERATION
from .contracts import ContractError, LedgerRecord, canonical_json_bytes, exact_int


def validate_chain(records: Iterable[LedgerRecord]) -> tuple[LedgerRecord, ...]:
    items = tuple(records)
    exact_int(
        len(items),
        "record_count",
        minimum=0,
        maximum=MAX_RECORDS_PER_GENERATION,
    )
    ordered = tuple(sorted(items, key=lambda item: item.sequence))
    if not ordered:
        return ordered

    identity = (
        ordered[0].repository,
        ordered[0].authority_issue,
        ordered[0].session_id,
        ordered[0].generation,
    )
    previous: str | None = None
    expected_sequence = 1
    seen_digests: set[str] = set()
    seen_sequences: set[int] = set()

    for record in ordered:
        if (
            record.repository,
            record.authority_issue,
            record.session_id,
            record.generation,
        ) != identity:
            raise ContractError(
                "ledger chain mixes repository/authority/session/generation identities"
            )
        if record.sequence in seen_sequences:
            raise ContractError("duplicate ledger sequence")
        if record.sequence != expected_sequence:
            raise ContractError("ledger sequence is not contiguous")
        if record.previous_record_sha256 != previous:
            raise ContractError("ledger previous-record binding mismatch")
        if record.record_sha256 in seen_digests:
            raise ContractError("duplicate ledger record digest")

        material = record.as_dict()
        claimed = material.pop("record_sha256")
        actual = hashlib.sha256(canonical_json_bytes(material)).hexdigest()
        if claimed != actual:
            raise ContractError("ledger record digest is invalid")

        seen_sequences.add(record.sequence)
        seen_digests.add(claimed)
        previous = claimed
        expected_sequence += 1

    return ordered


def render_record(record: LedgerRecord) -> str:
    payload = record.as_dict()
    body_bytes = canonical_json_bytes(payload)
    body = body_bytes.decode("utf-8")
    digest = hashlib.sha256(body_bytes).hexdigest()
    return (
        f"{LEDGER_MARKER}\n"
        f"payload_sha256: {digest}\n"
        "```json\n"
        f"{body}\n"
        "```"
    )
