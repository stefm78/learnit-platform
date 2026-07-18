"""Explicit argv execution, timeout handling and secret-safe command records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping

SENSITIVE_KEY_RE = re.compile(
    r"(?i)(token|secret|password|authorization|cookie|credential|private[_-]?key|client[_-]?secret)"
)
BEARER_RE = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+")
GITHUB_TOKEN_RE = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
KEY_VALUE_RE = re.compile(
    r"(?i)\b([A-Za-z0-9_.-]*(?:token|secret|password|authorization|cookie|credential)[A-Za-z0-9_.-]*)\s*[:=]\s*([^\s,;]+)"
)
URL_CREDENTIAL_RE = re.compile(r"(?i)(https?://)([^/\s:@]+):([^@/\s]+)@")


class ExecutionError(RuntimeError):
    """Raised for deterministic execution-layer failures."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact_text(value: str) -> str:
    value = URL_CREDENTIAL_RE.sub(lambda match: f"{match.group(1)}[REDACTED]@[", value)
    value = value.replace("@[", "@")
    value = BEARER_RE.sub(lambda match: f"{match.group(1)} [REDACTED]", value)
    value = GITHUB_TOKEN_RE.sub("[REDACTED_TOKEN]", value)
    value = KEY_VALUE_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    return value


def redact_value(value: Any, key: str | None = None) -> Any:
    if key is not None and SENSITIVE_KEY_RE.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): redact_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_argv(argv: Iterable[str]) -> list[str]:
    result: list[str] = []
    hide_next = False
    for item in argv:
        text = str(item)
        if hide_next:
            result.append("[REDACTED]")
            hide_next = False
            continue
        if text.startswith("-") and SENSITIVE_KEY_RE.search(text):
            if "=" in text:
                result.append(text.split("=", 1)[0] + "=[REDACTED]")
            else:
                result.append(text)
                hide_next = True
            continue
        result.append(redact_text(text))
    return result


def safe_environment(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    if extra:
        for key, value in extra.items():
            if SENSITIVE_KEY_RE.search(key):
                raise ExecutionError(f"refusing sensitive environment override: {key}")
            env[str(key)] = str(value)
    return env


@dataclass
class CommandRecord:
    id: str
    argv: list[str]
    cwd: str
    started_at: str
    completed_at: str
    duration_seconds: float
    return_code: int
    timed_out: bool
    stdout: str
    stderr: str
    stdout_bytes: int
    stderr_bytes: int
    stdout_sha256: str
    stderr_sha256: str

    def summary(self, *, excerpt_bytes: int = 4096) -> dict[str, Any]:
        stdout_excerpt = self.stdout.encode("utf-8")[:excerpt_bytes].decode("utf-8", "ignore")
        stderr_excerpt = self.stderr.encode("utf-8")[:excerpt_bytes].decode("utf-8", "ignore")
        return {
            "id": self.id,
            "argv": self.argv,
            "cwd": self.cwd,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": round(self.duration_seconds, 3),
            "return_code": self.return_code,
            "timed_out": self.timed_out,
            "stdout": {
                "bytes": self.stdout_bytes,
                "sha256": self.stdout_sha256,
                "excerpt": stdout_excerpt,
                "truncated": self.stdout_bytes > len(stdout_excerpt.encode("utf-8")),
            },
            "stderr": {
                "bytes": self.stderr_bytes,
                "sha256": self.stderr_sha256,
                "excerpt": stderr_excerpt,
                "truncated": self.stderr_bytes > len(stderr_excerpt.encode("utf-8")),
            },
        }


@dataclass
class CommandRunner:
    records: list[CommandRecord] = field(default_factory=list)
    _counter: int = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"cmd-{self._counter:03d}"

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout_seconds: int = 300,
        extra_env: Mapping[str, str] | None = None,
        check: bool = False,
    ) -> CommandRecord:
        if not argv or not all(isinstance(item, str) and item for item in argv):
            raise ExecutionError("argv must be a non-empty list of non-empty strings")
        if timeout_seconds <= 0:
            raise ExecutionError("timeout_seconds must be positive")
        command_id = self._next_id()
        started_at = utc_now()
        start = time.monotonic()
        process = subprocess.Popen(
            argv,
            cwd=str(cwd),
            env=safe_environment(extra_env),
            text=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=(os.name != "nt"),
        )
        timed_out = False
        try:
            stdout_b, stderr_b = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    stdout_b, stderr_b = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    stdout_b, stderr_b = process.communicate()
            else:
                process.kill()
                stdout_b, stderr_b = process.communicate()
        completed_at = utc_now()
        duration = time.monotonic() - start
        stdout = redact_text(stdout_b.decode("utf-8", "replace"))
        stderr = redact_text(stderr_b.decode("utf-8", "replace"))
        stdout_redacted_b = stdout.encode("utf-8")
        stderr_redacted_b = stderr.encode("utf-8")
        record = CommandRecord(
            id=command_id,
            argv=redact_argv(argv),
            cwd=str(cwd.resolve()),
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            return_code=process.returncode if process.returncode is not None else -1,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            stdout_bytes=len(stdout_redacted_b),
            stderr_bytes=len(stderr_redacted_b),
            stdout_sha256=sha256_bytes(stdout_redacted_b),
            stderr_sha256=sha256_bytes(stderr_redacted_b),
        )
        self.records.append(record)
        if check and (record.return_code != 0 or record.timed_out):
            state = "timed out" if record.timed_out else f"failed ({record.return_code})"
            raise ExecutionError(f"command {command_id} {state}: {' '.join(record.argv)}")
        return record

    def records_summary(self, *, excerpt_bytes: int = 4096) -> list[dict[str, Any]]:
        return [record.summary(excerpt_bytes=excerpt_bytes) for record in self.records]

    def combined_stdout(self) -> str:
        return "\n".join(f"## {record.id}\n{record.stdout}" for record in self.records if record.stdout)

    def combined_stderr(self) -> str:
        return "\n".join(f"## {record.id}\n{record.stderr}" for record in self.records if record.stderr)


def executable_version(runner: CommandRunner, executable: str, args: list[str], cwd: Path) -> dict[str, Any]:
    path = shutil.which(executable)
    if path is None:
        return {"available": False, "path": None, "version": None}
    record = runner.run([executable, *args], cwd=cwd, timeout_seconds=30)
    version = (record.stdout or record.stderr).strip().splitlines()
    return {
        "available": True,
        "path": path,
        "version": version[0] if version else "",
        "return_code": record.return_code,
    }


def collect_environment(runner: CommandRunner, repository_root: Path) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "repository_root": str(repository_root.resolve()),
        "codespace": {
            "present": bool(os.environ.get("CODESPACE_NAME")),
            "name": redact_text(os.environ.get("CODESPACE_NAME", "")) or None,
        },
    }
    for name, args in (("git", ["--version"]), ("gh", ["--version"]), ("node", ["--version"])):
        facts[name] = executable_version(runner, name, args, repository_root)
    return facts
