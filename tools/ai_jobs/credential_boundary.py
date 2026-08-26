"""Credential/effect-boundary guards immediately before Gate 0 invocation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
from typing import Any, BinaryIO, Mapping

from . import MAX_CHUNK_BYTES
from .contracts import (
    ContractError,
    QueueJob,
    SHA_RE,
    SessionGrant,
    canonical_json_bytes,
    exact_int,
    iso_utc,
)


_CAPABILITY_SCHEMA = "learnit.gate1.v6.effect-capability.v1"
_CAPABILITY_ALGORITHM = "Ed25519"
_CAPABILITY_DOMAIN = b"LEARNIT/G1/V6/EFFECT_CAPABILITY\x00"
_CAPABILITY_FIELDS = frozenset({
    "schema",
    "key_id",
    "algorithm",
    "method",
    "route",
    "parameters",
    "target",
    "body_sha256",
    "generation",
    "nonce",
    "expires_at",
    "signature_hex",
})
_KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", re.ASCII)
_NONCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,255}$", re.ASCII)
_SIGNATURE_RE = re.compile(r"^[0-9a-f]{128}$", re.ASCII)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


@dataclass
class SessionProcessFence:
    """Held file descriptor for same-Codespace Gate 1 exclusivity."""

    handle: BinaryIO
    path: Path

    def close(self) -> None:
        if not self.handle.closed:
            self.handle.close()


@dataclass(frozen=True)
class EffectCapabilityExpectation:
    """Exact effect binding supplied by the non-credential-owning coordinator."""

    method: str
    route: str
    parameters: Mapping[str, Any]
    target: Mapping[str, Any]
    body_sha256: str
    generation: int

    def __post_init__(self) -> None:
        _bounded_ascii(self.method, "capability expectation method", maximum=64)
        _bounded_ascii(self.route, "capability expectation route", maximum=1024)
        if not isinstance(self.parameters, Mapping):
            raise ContractError("capability expectation parameters must be an object")
        if not isinstance(self.target, Mapping):
            raise ContractError("capability expectation target must be an object")
        canonical_json_bytes(dict(self.parameters))
        canonical_json_bytes(dict(self.target))
        if not isinstance(self.body_sha256, str) or _SHA256_RE.fullmatch(self.body_sha256) is None:
            raise ContractError("capability expectation body_sha256 is invalid")
        exact_int(self.generation, "capability expectation generation", minimum=1)


class EffectCapabilityVerifier:
    """Verify externally-issued Ed25519 capabilities and consume nonces once.

    The verifier never creates capabilities, private keys, or local authority.
    Its trusted public key and key id must be supplied by the parent authority
    path outside the token-owning EFFECT_GATEWAY. Replay consumption is recorded
    with an exclusive same-Codespace marker keyed by issuer, generation and nonce,
    so a new verifier process cannot silently reuse an already-consumed capability.
    """

    def __init__(
        self,
        *,
        repository_root: Path,
        issuer_public_key_pem: bytes,
        issuer_key_id: str,
    ) -> None:
        if not isinstance(issuer_public_key_pem, bytes) or not issuer_public_key_pem:
            raise ContractError("capability issuer public key is unavailable")
        if len(issuer_public_key_pem) > 8192:
            raise ContractError("capability issuer public key exceeds the bounded size")
        if not isinstance(issuer_key_id, str) or _KEY_ID_RE.fullmatch(issuer_key_id) is None:
            raise ContractError("capability issuer key_id is invalid")

        executable = shutil.which("openssl")
        if executable is None:
            raise ContractError("OpenSSL Ed25519 verifier is unavailable")
        openssl = Path(executable).resolve()
        root = repository_root.resolve()
        try:
            openssl.relative_to(root)
        except ValueError:
            pass
        else:
            raise ContractError("refusing a workspace-provided OpenSSL executable")

        self._repository_root = root
        self._openssl = openssl
        self._issuer_public_key_pem = bytes(issuer_public_key_pem)
        self._issuer_key_id = issuer_key_id
        replay_scope = hashlib.sha256(
            self._issuer_public_key_pem + b"\x00" + issuer_key_id.encode("ascii")
        ).hexdigest()
        self._replay_root = (
            Path(tempfile.gettempdir()) / f"learnit-g1-capability-nonces-{replay_scope}"
        )
        self._replay_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(self._replay_root, 0o700)
        except OSError as exc:
            raise ContractError("effect capability replay fence cannot be secured") from exc

    @property
    def issuer_key_id(self) -> str:
        return self._issuer_key_id

    def verify_and_consume(
        self,
        *,
        capability: Mapping[str, Any],
        expected: EffectCapabilityExpectation,
        now: datetime | None = None,
    ) -> None:
        """Verify one exact capability and atomically consume its generation nonce."""
        if not isinstance(capability, Mapping):
            raise ContractError("effect capability is absent or malformed")
        value = dict(capability)
        if set(value) != _CAPABILITY_FIELDS:
            raise ContractError("effect capability field set is not closed")
        if value.get("schema") != _CAPABILITY_SCHEMA:
            raise ContractError("effect capability schema is invalid")
        if value.get("algorithm") != _CAPABILITY_ALGORITHM:
            raise ContractError("effect capability algorithm is invalid")
        if value.get("key_id") != self._issuer_key_id:
            raise ContractError("effect capability key_id is not the trusted issuer")

        method = _bounded_ascii(value.get("method"), "effect capability method", maximum=64)
        route = _bounded_ascii(value.get("route"), "effect capability route", maximum=1024)
        parameters = value.get("parameters")
        target = value.get("target")
        if not isinstance(parameters, Mapping):
            raise ContractError("effect capability parameters must be an object")
        if not isinstance(target, Mapping):
            raise ContractError("effect capability target must be an object")
        parameters_bytes = canonical_json_bytes(dict(parameters))
        target_bytes = canonical_json_bytes(dict(target))

        body_sha256 = value.get("body_sha256")
        if not isinstance(body_sha256, str) or _SHA256_RE.fullmatch(body_sha256) is None:
            raise ContractError("effect capability body_sha256 is invalid")
        generation = exact_int(value.get("generation"), "effect capability generation", minimum=1)
        nonce = value.get("nonce")
        if not isinstance(nonce, str) or _NONCE_RE.fullmatch(nonce) is None:
            raise ContractError("effect capability nonce is invalid")
        expires_at = iso_utc(value.get("expires_at"), "effect capability expires_at")
        signature_hex = value.get("signature_hex")
        if not isinstance(signature_hex, str) or _SIGNATURE_RE.fullmatch(signature_hex) is None:
            raise ContractError("effect capability signature is invalid")

        if method != expected.method:
            raise ContractError("effect capability method binding mismatch")
        if route != expected.route:
            raise ContractError("effect capability route binding mismatch")
        if parameters_bytes != canonical_json_bytes(dict(expected.parameters)):
            raise ContractError("effect capability parameters binding mismatch")
        if target_bytes != canonical_json_bytes(dict(expected.target)):
            raise ContractError("effect capability target binding mismatch")
        if body_sha256 != expected.body_sha256:
            raise ContractError("effect capability body digest binding mismatch")
        if generation != expected.generation:
            raise ContractError("effect capability generation binding mismatch")

        current = now if now is not None else datetime.now(timezone.utc)
        if not isinstance(current, datetime) or current.tzinfo is None:
            raise ContractError("capability verification clock must be timezone-aware")
        current = current.astimezone(timezone.utc)
        expiry = datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if current >= expiry:
            raise ContractError("effect capability is expired")

        unsigned = {key: value[key] for key in _CAPABILITY_FIELDS if key != "signature_hex"}
        signed_bytes = _CAPABILITY_DOMAIN + canonical_json_bytes(unsigned)
        if len(signed_bytes) > MAX_CHUNK_BYTES:
            raise ContractError("effect capability signed bytes exceed the canonical chunk bound")
        signature = bytes.fromhex(signature_hex)
        self._verify_ed25519(signed_bytes=signed_bytes, signature=signature)

        # Consumption occurs only after the full binding and signature checks.
        # Exclusive marker creation is race-safe across verifier processes in
        # the same Codespace. If the subsequent effect fails, the marker remains
        # so the gateway never creates a blind replay path.
        self._consume_nonce(generation=generation, nonce=nonce)

    def _consume_nonce(self, *, generation: int, nonce: str) -> None:
        material = f"{generation}|{nonce}".encode("ascii")
        marker = self._replay_root / hashlib.sha256(material).hexdigest()
        try:
            descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ContractError(
                "effect capability nonce was already consumed in this generation"
            ) from exc
        except OSError as exc:
            raise ContractError("effect capability nonce consumption failed closed") from exc
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(hashlib.sha256(material).hexdigest().encode("ascii") + b"\n")
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            # The marker is intentionally retained on a write failure: a nonce
            # whose durable consumption is uncertain must never become reusable.
            raise ContractError("effect capability nonce consumption became ambiguous")

    def _verify_ed25519(self, *, signed_bytes: bytes, signature: bytes) -> None:
        with tempfile.TemporaryDirectory(prefix="learnit-g1-capability-") as tmp:
            directory = Path(tmp)
            os.chmod(directory, 0o700)
            key_path = directory / "issuer-public.pem"
            message_path = directory / "capability.bin"
            signature_path = directory / "signature.bin"
            _write_private_file(key_path, self._issuer_public_key_pem)
            _write_private_file(message_path, signed_bytes)
            _write_private_file(signature_path, signature)
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "LANG": "C",
                "LC_ALL": "C",
            }
            try:
                completed = subprocess.run(
                    [
                        str(self._openssl),
                        "pkeyutl",
                        "-verify",
                        "-rawin",
                        "-pubin",
                        "-inkey",
                        str(key_path),
                        "-in",
                        str(message_path),
                        "-sigfile",
                        str(signature_path),
                    ],
                    cwd=str(self._repository_root),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                    check=False,
                    timeout=30,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ContractError("Ed25519 capability verification could not execute") from exc
            if completed.returncode != 0:
                raise ContractError("effect capability Ed25519 signature verification failed")


def _bounded_ascii(value: Any, label: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ContractError(f"{label} is unavailable or outside the bound")
    if value != value.strip() or any(ord(char) < 0x21 or ord(char) > 0x7E for char in value):
        raise ContractError(f"{label} must be canonical printable ASCII without edge whitespace")
    return value


def _write_private_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def acquire_session_process_fence(grant: SessionGrant) -> SessionProcessFence:
    """Acquire a non-blocking fence for the whole authority in this Codespace."""
    if platform.system() != "Linux":
        raise ContractError("Gate 1 process fencing requires the Linux Codespace runtime")
    try:
        import fcntl
    except ImportError as exc:  # pragma: no cover - Linux Codespaces provide fcntl
        raise ContractError("Gate 1 process fencing requires fcntl") from exc

    material = (
        f"{grant.repository}|{grant.authority_issue}|{grant.codespace_name}"
    ).encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    path = Path(tempfile.gettempdir()) / f"learnit-gate1-authority-{digest}.lock"
    handle = path.open("a+b")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise ContractError(
            "another Gate 1 coordinator process already holds this authority fence"
        ) from exc
    except OSError as exc:
        handle.close()
        raise ContractError(f"Gate 1 process fence failed: {exc}") from exc
    return SessionProcessFence(handle=handle, path=path)


def require_runtime_identity(
    *,
    preflight: dict[str, Any],
    grant: SessionGrant,
    codespace_name: str | None = None,
) -> str:
    login = preflight.get("authenticated_login")
    if not isinstance(login, str) or not login:
        raise ContractError("authenticated GitHub identity is unavailable")
    if login != grant.granted_by:
        raise ContractError("authenticated GitHub identity differs from the human session grant")
    if preflight.get("authenticated_host") != "github.com":
        raise ContractError("Gate 1 authenticated host differs from canonical github.com")
    if preflight.get("checkout_repository") != grant.repository:
        raise ContractError("Gate 1 checkout repository differs from the human session grant")
    if preflight.get("raw_r5_readback") is not True:
        raise ContractError("Gate 1 raw R5 GitHub read-back is not active")

    observed_codespace = os.environ.get("CODESPACE_NAME")
    if not isinstance(observed_codespace, str) or not observed_codespace:
        raise ContractError("Gate 1 must run inside the human-started GitHub Codespace")
    if codespace_name is not None and codespace_name != observed_codespace:
        raise ContractError("explicit Codespace assertion differs from the runtime environment")
    if observed_codespace != grant.codespace_name:
        raise ContractError("Codespace identity differs from the human grant")
    return login


def require_request_authority(permission: str) -> None:
    if permission not in {"write", "maintain", "admin"}:
        raise ContractError("request author lacks Gate 1 execution authority")


def _validate_effect_comment(job: QueueJob, request_comment: dict[str, Any]) -> None:
    """Bind the final observation to the exact GitHub origin and real author."""
    if not isinstance(request_comment, dict):
        raise ContractError("source request comment is unavailable at the effect boundary")
    if exact_int(request_comment.get("id"), "request_comment.id", minimum=1) != job.request_comment_id:
        raise ContractError("source request comment identity moved")

    expected_issue_url = (
        f"https://api.github.com/repos/{job.repository}/issues/{job.origin_number}"
    )
    if request_comment.get("issue_url") != expected_issue_url:
        raise ContractError("source request comment origin moved")
    html_url = request_comment.get("html_url")
    expected_html_prefix = f"https://github.com/{job.repository}/"
    if not isinstance(html_url, str) or not html_url.startswith(expected_html_prefix):
        raise ContractError("source request comment canonical repository moved")

    body = request_comment.get("body")
    if not isinstance(body, str):
        raise ContractError("source request comment disappeared")

    created_at = iso_utc(request_comment.get("created_at"), "request_comment.created_at")
    updated_at = iso_utc(request_comment.get("updated_at"), "request_comment.updated_at")
    if created_at != updated_at:
        raise ContractError("source request comment was edited")
    if created_at != job.created_at:
        raise ContractError("source request comment timestamp differs from selected job identity")

    user = request_comment.get("user")
    if not isinstance(user, dict):
        raise ContractError("source request comment author is unavailable")
    exact_int(user.get("id"), "request_comment.user.id", minimum=1)
    if user.get("login") != job.request_author:
        raise ContractError("source request comment author differs from selected job identity")
    if not isinstance(user.get("node_id"), str) or not user["node_id"]:
        raise ContractError("source request comment author node_id is unavailable")


def final_effect_guard(
    *,
    job: QueueJob,
    request_comment: dict[str, Any],
    current_target_sha: str,
    permission: str,
    suspended: bool,
) -> None:
    """Revalidate every mutable authority immediately at the effect boundary."""
    if suspended:
        raise ContractError("Gate 1 is suspended at the invocation boundary")
    require_request_authority(permission)
    _validate_effect_comment(job, request_comment)

    if not isinstance(job.target_sha, str) or SHA_RE.fullmatch(job.target_sha) is None:
        raise ContractError("selected target SHA is not an exact lowercase SHA")
    if not isinstance(current_target_sha, str) or SHA_RE.fullmatch(current_target_sha) is None:
        raise ContractError("current target SHA is not an exact lowercase SHA")
    if current_target_sha != job.target_sha:
        raise ContractError("target SHA moved before Gate 0 invocation")
