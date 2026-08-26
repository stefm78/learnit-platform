"""Independent contradictory tests for Gate 1 closed scalar/global contracts."""
from __future__ import annotations

import unittest

import tools.ai_jobs as gate1
from tools.ai_jobs.contracts import (
    ContractError,
    LedgerRecord,
    canonical_json_bytes,
    exact_int,
    iso_utc,
    loads_closed_json,
    validate_global_bounds,
)


class ClosedScalarContractTests(unittest.TestCase):
    def test_exact_integer_accepts_only_plain_int_inside_closed_range(self) -> None:
        self.assertEqual(exact_int(7, "value", minimum=1, maximum=7), 7)
        for value in (True, False, 1.0, -1, 8):
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    exact_int(value, "value", minimum=0, maximum=7)

    def test_closed_json_rejects_float_nan_infinity_and_duplicate_keys(self) -> None:
        for text in (
            '{"n":1.0}', '{"n":1e3}', '{"n":NaN}', '{"n":Infinity}',
            '{"n":-Infinity}', '{"a":1,"a":2}',
        ):
            with self.subTest(text=text):
                with self.assertRaises(ContractError):
                    loads_closed_json(text)

    def test_canonical_json_rejects_python_float_recursively(self) -> None:
        for value in (1.0, {"x": [1, 2.0]}, {"x": float("nan")}):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ContractError):
                    canonical_json_bytes(value)
        self.assertEqual(canonical_json_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}')

    def test_utc_seconds_accepts_real_calendar_instants_only(self) -> None:
        for value in (
            "2000-01-01T00:00:00Z",
            "2000-02-29T12:34:56Z",
            "2100-12-31T23:59:59Z",
        ):
            with self.subTest(value=value):
                self.assertEqual(iso_utc(value, "t"), value)

    def test_utc_seconds_rejects_fractional_invalid_and_out_of_domain_values(self) -> None:
        for value in (
            "1999-12-31T23:59:59Z", "2101-01-01T00:00:00Z",
            "2100-02-29T00:00:00Z", "2026-02-30T00:00:00Z",
            "2026-13-01T00:00:00Z", "2026-01-01T24:00:00Z",
            "2026-01-01T23:59:60Z", "2026-01-01T00:00:00.0Z",
            "2026-01-01T00:00:00.000001Z", "2026-01-01T00:00:00+00:00",
            "2026-01-01t00:00:00z", "+2026-01-01T00:00:00Z",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    iso_utc(value, "t")

    def test_global_bounds_are_exact_r5_values(self) -> None:
        self.assertEqual(gate1.MAX_ISSUES_PER_GENERATION, 8)
        self.assertEqual(gate1.MAX_LEDGERS_PER_GENERATION, 8)
        self.assertEqual(gate1.MAX_COMMENTS_PER_ISSUE, 10_000)
        self.assertEqual(gate1.MAX_RECORDS_PER_GENERATION, 50_000)
        self.assertEqual(gate1.MAX_SNAPSHOT_BYTES, 16_777_216)
        self.assertEqual(gate1.MAX_CHUNK_BYTES, 1_048_576)
        self.assertEqual(gate1.MAX_GENERATION, 4_096)

    def test_all_global_bounds_accept_maxima_and_reject_overflow_bool_float(self) -> None:
        maxima = {
            "generation": gate1.MAX_GENERATION,
            "issue_count": gate1.MAX_ISSUES_PER_GENERATION,
            "comment_count": gate1.MAX_COMMENTS_PER_ISSUE,
            "ledger_count": gate1.MAX_LEDGERS_PER_GENERATION,
            "record_count": gate1.MAX_RECORDS_PER_GENERATION,
            "snapshot_size_bytes": gate1.MAX_SNAPSHOT_BYTES,
            "max_chunk_size_bytes": gate1.MAX_CHUNK_BYTES,
        }
        self.assertEqual(dict(validate_global_bounds(**maxima)), maxima)
        for name, maximum in maxima.items():
            for bad in (maximum + 1, True, float(maximum)):
                values = dict(maxima)
                values[name] = bad
                with self.subTest(name=name, bad=bad):
                    with self.assertRaises(ContractError):
                        validate_global_bounds(**values)

    def test_generation_and_record_sequence_overflow_fail_closed(self) -> None:
        common = dict(
            record_type="SESSION_GRANT",
            repository="stefm78/learnit-platform",
            authority_issue=160,
            session_id="G1S-QA1",
            previous_record_sha256=None,
            created_at="2026-08-26T13:00:00Z",
            payload={
                "grant_comment_id": 100,
                "grant_digest": "a" * 64,
                "request_issue": 170,
            },
        )
        with self.assertRaises(ContractError):
            LedgerRecord.build(**common, generation=gate1.MAX_GENERATION + 1, sequence=1)
        with self.assertRaises(ContractError):
            LedgerRecord.build(
                **common,
                generation=1,
                sequence=gate1.MAX_RECORDS_PER_GENERATION + 1,
            )


if __name__ == "__main__":
    unittest.main()
