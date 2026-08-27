"""Independent contradictory credential, capability and pilot effect-boundary tests."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.ai_jobs.contracts import ContractError, QueueJob, SessionGrant, canonical_json_bytes
import tools.ai_jobs.credential_boundary as boundary
from tools.ai_jobs.credential_boundary import (
    EffectCapabilityExpectation,
    EffectCapabilityVerifier,
    acquire_session_process_fence,
    final_effect_guard,
    require_runtime_identity,
)
import tools.ai_jobs.gate0_adapter as adapter


NOW = datetime(2026, 8, 26, 13, 0, 0, tzinfo=timezone.utc)


def job() -> QueueJob:
    return QueueJob(
        repository="stefm78/learnit-platform", origin_type="issue", origin_number=170,
        request_comment_id=200, request_author="stefm78",
        created_at="2026-08-26T13:00:00Z", job_id="J-1", operation="pr-snapshot",
        target_type="commit", target_number=None, target_sha="1" * 40,
        request_digest="b" * 64,
    )


def grant(generation: int = 1) -> SessionGrant:
    return SessionGrant(
        repository="stefm78/learnit-platform", authority_issue=160,
        session_id=f"G1S-QA{generation}", codespace_name="qa-codespace",
        generation=generation, granted_by="stefm78",
        created_at="2026-08-26T13:00:00Z", grant_comment_id=100 + generation,
        grant_digest=("a" if generation == 1 else "c") * 64,
    )


def source_comment() -> dict:
    return {
        "id": 200,
        "issue_url": "https://api.github.com/repos/stefm78/learnit-platform/issues/170",
        "html_url": "https://github.com/stefm78/learnit-platform/issues/170#issuecomment-200",
        "body": "request",
        "created_at": "2026-08-26T13:00:00Z",
        "updated_at": "2026-08-26T13:00:00Z",
        "user": {"id": 1, "login": "stefm78", "node_id": "U_1"},
    }


def expectation(*, generation: int = 1) -> EffectCapabilityExpectation:
    return EffectCapabilityExpectation(
        method="POST", route="repos/stefm78/learnit-platform/read-only-effect",
        parameters={"operation": "pr-snapshot"},
        target={"type": "commit", "number": None, "sha": "1" * 40},
        body_sha256="d" * 64, generation=generation,
    )


class SignedCapabilityFixture:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="g1qa-ed25519-")
        self.root = Path(self.tmp.name)
        self.private = self.root / "private.pem"
        self.public = self.root / "public.pem"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(self.private)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(self.private), "-pubout", "-out", str(self.public)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.verifier = EffectCapabilityVerifier(
            repository_root=self.root,
            issuer_public_key_pem=self.public.read_bytes(),
            issuer_key_id="qa-issuer",
        )

    def close(self) -> None:
        self.tmp.cleanup()

    def capability(
        self,
        *,
        expected: EffectCapabilityExpectation | None = None,
        nonce: str = "nonce-000000000001",
        expires_at: str = "2026-08-26T14:00:00Z",
        overrides: dict | None = None,
    ) -> dict:
        exp = expected or expectation()
        unsigned = {
            "schema": "learnit.gate1.v6.effect-capability.v1",
            "key_id": "qa-issuer",
            "algorithm": "Ed25519",
            "method": exp.method,
            "route": exp.route,
            "parameters": dict(exp.parameters),
            "target": dict(exp.target),
            "body_sha256": exp.body_sha256,
            "generation": exp.generation,
            "nonce": nonce,
            "expires_at": expires_at,
        }
        if overrides:
            unsigned.update(overrides)
        message = self.root / "message.bin"
        signature = self.root / "signature.bin"
        message.write_bytes(boundary._CAPABILITY_DOMAIN + canonical_json_bytes(unsigned))
        subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(self.private),
             "-in", str(message), "-out", str(signature)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return {**unsigned, "signature_hex": signature.read_bytes().hex()}


class CredentialBoundaryTests(unittest.TestCase):
    def test_final_effect_guard_accepts_exact_fresh_authorized_request(self) -> None:
        final_effect_guard(
            job=job(), request_comment=source_comment(), current_target_sha="1" * 40,
            permission="write", suspended=False,
        )

    def test_edited_or_deleted_source_request_is_rejected(self) -> None:
        edited = source_comment(); edited["updated_at"] = "2026-08-26T13:00:01Z"
        deleted = source_comment(); deleted["body"] = None
        for raw in (edited, deleted):
            with self.subTest(raw=raw):
                with self.assertRaises(ContractError):
                    final_effect_guard(job=job(), request_comment=raw, current_target_sha="1" * 40, permission="write", suspended=False)

    def test_moved_comment_origin_or_repository_is_rejected(self) -> None:
        moved_id = source_comment(); moved_id["id"] = 201
        moved_origin = source_comment(); moved_origin["issue_url"] = "https://api.github.com/repos/stefm78/learnit-platform/issues/171"
        moved_repo = source_comment(); moved_repo["html_url"] = "https://github.com/other/repo/issues/170#issuecomment-200"
        for raw in (moved_id, moved_origin, moved_repo):
            with self.subTest(raw=raw):
                with self.assertRaises(ContractError):
                    final_effect_guard(job=job(), request_comment=raw, current_target_sha="1" * 40, permission="write", suspended=False)

    def test_source_author_identity_change_is_rejected(self) -> None:
        raw = source_comment(); raw["user"] = {"id": 2, "login": "other", "node_id": "U_2"}
        with self.assertRaises(ContractError):
            final_effect_guard(job=job(), request_comment=raw, current_target_sha="1" * 40, permission="write", suspended=False)

    def test_request_author_losing_permission_is_rejected(self) -> None:
        for permission in ("read", "triage", "", "unknown"):
            with self.subTest(permission=permission):
                with self.assertRaises(ContractError):
                    final_effect_guard(job=job(), request_comment=source_comment(), current_target_sha="1" * 40, permission=permission, suspended=False)

    def test_target_sha_movement_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            final_effect_guard(job=job(), request_comment=source_comment(), current_target_sha="2" * 40, permission="write", suspended=False)

    def test_suspension_immediately_before_effect_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            final_effect_guard(job=job(), request_comment=source_comment(), current_target_sha="1" * 40, permission="write", suspended=True)

    def test_runtime_identity_binds_login_host_repo_raw_r5_and_codespace(self) -> None:
        g = grant()
        good = {
            "authenticated_login": "stefm78", "authenticated_host": "github.com",
            "checkout_repository": g.repository, "raw_r5_readback": True,
        }
        with patch.dict(os.environ, {"CODESPACE_NAME": g.codespace_name}, clear=False):
            self.assertEqual(require_runtime_identity(preflight=good, grant=g), "stefm78")
            for key, bad in (
                ("authenticated_login", "other"), ("authenticated_host", "example.com"),
                ("checkout_repository", "other/repo"), ("raw_r5_readback", False),
            ):
                altered = dict(good); altered[key] = bad
                with self.subTest(key=key):
                    with self.assertRaises(ContractError):
                        require_runtime_identity(preflight=altered, grant=g)
            with self.assertRaises(ContractError):
                require_runtime_identity(preflight=good, grant=g, codespace_name="other-space")

    def test_two_processes_for_same_authority_cannot_hold_fence(self) -> None:
        first = acquire_session_process_fence(grant(1))
        try:
            with self.assertRaises(ContractError):
                acquire_session_process_fence(grant(2))
        finally:
            first.close()

    def test_full_v6_requires_external_capability_verifier_and_expectation(self) -> None:
        with self.assertRaises(ContractError):
            adapter._verify_effect_capability(job=job(), capability=None, verifier=None, expectation=None)

    def test_full_v6_valid_ed25519_capability_passes(self) -> None:
        fixture = SignedCapabilityFixture()
        try:
            exp = expectation()
            fixture.verifier.verify_and_consume(capability=fixture.capability(expected=exp), expected=exp, now=NOW)
        finally:
            fixture.close()

    def test_full_v6_expired_capability_is_rejected(self) -> None:
        fixture = SignedCapabilityFixture()
        try:
            exp = expectation()
            with self.assertRaises(ContractError):
                fixture.verifier.verify_and_consume(
                    capability=fixture.capability(expected=exp, expires_at="2026-08-26T12:59:59Z"),
                    expected=exp, now=NOW,
                )
        finally:
            fixture.close()

    def test_full_v6_replay_is_rejected(self) -> None:
        fixture = SignedCapabilityFixture()
        try:
            exp = expectation(); cap = fixture.capability(expected=exp, nonce="nonce-000000000002")
            fixture.verifier.verify_and_consume(capability=cap, expected=exp, now=NOW)
            with self.assertRaises(ContractError):
                fixture.verifier.verify_and_consume(capability=cap, expected=exp, now=NOW)
        finally:
            fixture.close()

    def test_full_v6_tampered_or_wrong_target_is_rejected(self) -> None:
        fixture = SignedCapabilityFixture()
        try:
            exp = expectation(); cap = fixture.capability(expected=exp)
            tampered = dict(cap); tampered["body_sha256"] = "e" * 64
            with self.assertRaises(ContractError):
                fixture.verifier.verify_and_consume(capability=tampered, expected=exp, now=NOW)
            wrong_target = fixture.capability(expected=exp, nonce="nonce-000000000003", overrides={"target": {"type": "commit", "number": None, "sha": "2" * 40}})
            with self.assertRaises(ContractError):
                fixture.verifier.verify_and_consume(capability=wrong_target, expected=exp, now=NOW)
        finally:
            fixture.close()

    def test_full_v6_wrong_generation_is_rejected(self) -> None:
        fixture = SignedCapabilityFixture()
        try:
            exp = expectation(generation=1)
            cap = fixture.capability(expected=exp, overrides={"generation": 2})
            with self.assertRaises(ContractError):
                fixture.verifier.verify_and_consume(capability=cap, expected=exp, now=NOW)
        finally:
            fixture.close()

    def test_full_v6_invalid_signature_is_rejected(self) -> None:
        fixture = SignedCapabilityFixture()
        try:
            exp = expectation(); cap = fixture.capability(expected=exp)
            cap["signature_hex"] = "00" * 64
            with self.assertRaises(ContractError):
                fixture.verifier.verify_and_consume(capability=cap, expected=exp, now=NOW)
        finally:
            fixture.close()

    def test_pilot_permit_is_required_and_profile_mixing_is_explicitly_rejected(self) -> None:
        with self.assertRaises(ContractError):
            adapter._verify_pilot_permit(job=job(), permit=None, gateway=object())
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        self.assertIn("pilot profile cannot masquerade as signed V6 authority", source)
        self.assertIn("pilot permit cannot be mixed with FULL_V6_SECURITY", source)
        self.assertIn("unknown Gate 1 security profile", source)

    def test_pilot_permit_live_authority_binds_generation_started_digest_and_sequence(self) -> None:
        j = job(); g = grant(1)
        authoritative_digest = "f" * 64
        good = adapter.PilotEffectPermit.build(
            repository=j.repository, authority_issue=160, session_id=g.session_id,
            generation=1, job=j, started_record_sha256=authoritative_digest,
            started_sequence=4, issued_at="2026-08-26T13:00:00Z",
        )
        tail = SimpleNamespace(
            record_sha256=authoritative_digest, sequence=4, record_type="JOB_STARTED",
            payload={"job_id": j.job_id, "request_digest": j.request_digest,
                     "request_comment_id": j.request_comment_id, "target_sha": j.target_sha},
        )
        projection = SimpleNamespace(state="JOB_STARTED", last_record=tail, active_job_digest=j.request_digest)
        gateway = SimpleNamespace(comments=lambda _issue: [])
        patches = (
            patch.object(adapter, "stable_double_scan", return_value=SimpleNamespace(comments=(object(),))),
            patch.object(adapter, "_snapshot_comment_for_parser", return_value={}),
            patch.object(adapter, "grant_from_comment", return_value=g),
            patch.object(
                adapter,
                "ledger_from_comment",
                return_value=SimpleNamespace(session_id=g.session_id, generation=g.generation),
            ),
            patch.object(adapter, "require_exclusive_session", return_value=None),
            patch.object(adapter, "project", return_value=projection),
        )
        for p in patches: p.start()
        try:
            adapter._verify_pilot_permit_authority(gateway=gateway, job=j, permit=good)
            bad_permits = (
                adapter.PilotEffectPermit.build(repository=j.repository, authority_issue=160, session_id="G1S-QA2", generation=2, job=j, started_record_sha256=authoritative_digest, started_sequence=4, issued_at="2026-08-26T13:00:00Z"),
                adapter.PilotEffectPermit.build(repository=j.repository, authority_issue=160, session_id=g.session_id, generation=1, job=j, started_record_sha256="e" * 64, started_sequence=4, issued_at="2026-08-26T13:00:00Z"),
                adapter.PilotEffectPermit.build(repository=j.repository, authority_issue=160, session_id=g.session_id, generation=1, job=j, started_record_sha256=authoritative_digest, started_sequence=5, issued_at="2026-08-26T13:00:00Z"),
            )
            for permit in bad_permits:
                with self.subTest(generation=permit.generation, digest=permit.started_record_sha256, sequence=permit.started_sequence):
                    with self.assertRaises(ContractError):
                        adapter._verify_pilot_permit_authority(gateway=gateway, job=j, permit=permit)
        finally:
            for p in reversed(patches): p.stop()


if __name__ == "__main__":
    unittest.main()
