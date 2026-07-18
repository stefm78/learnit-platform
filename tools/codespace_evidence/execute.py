"""Explicit argv execution, timeout handling and secret-safe command records."""

from __future__ import annotations

from contextlib import nullcontext
import ctypes
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
import tempfile
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

SAFE_PROCESS_ENV_KEYS = frozenset(
    {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TERM",
        "TZ",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        "NO_COLOR",
    }
)
USER_CONFIG_ENV_KEYS = frozenset(
    {
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "XDG_CONFIG_HOME",
        "GH_CONFIG_DIR",
        "GH_HOST",
    }
)
GITHUB_AUTH_ENV_KEYS = frozenset(
    {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"}
)
ISOLATED_CONFIG_OVERRIDE_KEYS = frozenset(
    {
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "XDG_CONFIG_HOME",
        "GH_CONFIG_DIR",
        "TMPDIR",
        "TMP",
        "TEMP",
    }
)

_LANDLOCK_CREATE_RULESET_VERSION = 1
_LANDLOCK_RULE_PATH_BENEATH = 1
_PR_SET_NO_NEW_PRIVS = 38
_LL_EXECUTE = 1 << 0
_LL_WRITE_FILE = 1 << 1
_LL_READ_FILE = 1 << 2
_LL_READ_DIR = 1 << 3
_LL_REMOVE_DIR = 1 << 4
_LL_REMOVE_FILE = 1 << 5
_LL_MAKE_CHAR = 1 << 6
_LL_MAKE_DIR = 1 << 7
_LL_MAKE_REG = 1 << 8
_LL_MAKE_SOCK = 1 << 9
_LL_MAKE_FIFO = 1 << 10
_LL_MAKE_BLOCK = 1 << 11
_LL_MAKE_SYM = 1 << 12
_LL_REFER = 1 << 13
_LL_TRUNCATE = 1 << 14
_SANDBOX_MARKER = "--codespace-evidence-landlock-exec"
_MOUNT_SANDBOX_MARKER = "--codespace-evidence-mount-sandbox-exec"


class ExecutionError(RuntimeError):
    """Raised for deterministic execution-layer failures."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ambient_secret_values() -> tuple[str, ...]:
    values = {
        value
        for key, value in os.environ.items()
        if value and (SENSITIVE_KEY_RE.search(key) or key in GITHUB_AUTH_ENV_KEYS)
    }
    return tuple(sorted(values, key=len, reverse=True))


def redact_text(value: str, secret_values: Iterable[str] = ()) -> str:
    value = URL_CREDENTIAL_RE.sub(lambda match: f"{match.group(1)}[REDACTED]@", value)
    value = BEARER_RE.sub(lambda match: f"{match.group(1)} [REDACTED]", value)
    value = GITHUB_TOKEN_RE.sub("[REDACTED_TOKEN]", value)
    value = KEY_VALUE_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    for secret in sorted({item for item in secret_values if item}, key=len, reverse=True):
        value = value.replace(secret, "[REDACTED_AMBIENT_SECRET]")
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


def redact_argv(argv: Iterable[str], secret_values: Iterable[str] = ()) -> list[str]:
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
        result.append(redact_text(text, secret_values))
    return result


def _isolated_config_environment(root: Path) -> dict[str, str]:
    home = root / "home"
    xdg = root / "xdg"
    gh = root / "gh"
    appdata = root / "appdata"
    local_appdata = root / "local-appdata"
    temp = root / "tmp"
    for path in (home, xdg, gh, appdata, local_appdata, temp):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "XDG_CONFIG_HOME": str(xdg),
        "GH_CONFIG_DIR": str(gh),
        "APPDATA": str(appdata),
        "LOCALAPPDATA": str(local_appdata),
        "TMPDIR": str(temp),
        "TMP": str(temp),
        "TEMP": str(temp),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }


def safe_environment(
    extra: Mapping[str, str] | None = None,
    *,
    include_github_auth: bool = False,
    isolated_config_root: Path | None = None,
) -> dict[str, str]:
    """Build a strict subprocess environment.

    Ordinary validators and tests receive fresh private configuration and temp
    directories. Only trusted GitHub transport receives the operator's actual
    GitHub authentication and configuration locations.
    """

    env: dict[str, str] = {}
    for key, value in os.environ.items():
        if key in SAFE_PROCESS_ENV_KEYS or key.startswith("LC_"):
            env[key] = value
    if include_github_auth:
        for key in USER_CONFIG_ENV_KEYS | GITHUB_AUTH_ENV_KEYS:
            value = os.environ.get(key)
            if value:
                env[key] = value
        for key in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value:
                env[key] = value
    else:
        if isolated_config_root is None:
            raise ExecutionError("isolated_config_root is required for non-GitHub subprocesses")
        env.update(_isolated_config_environment(isolated_config_root))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    if extra:
        for key, value in extra.items():
            if SENSITIVE_KEY_RE.search(key):
                raise ExecutionError(f"refusing sensitive environment override: {key}")
            if not include_github_auth and key in ISOLATED_CONFIG_OVERRIDE_KEYS:
                raise ExecutionError(f"refusing user-config environment override: {key}")
            env[str(key)] = str(value)
    return env


class _RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _PathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
        ("reserved", ctypes.c_uint32),
    ]


def _landlock_syscall_numbers() -> tuple[int, int, int]:
    if platform.system() != "Linux":
        raise ExecutionError("filesystem confinement requires Linux Landlock")
    return 444, 445, 446


def _landlock_supported_mask(abi: int) -> int:
    mask = (
        _LL_EXECUTE
        | _LL_WRITE_FILE
        | _LL_READ_FILE
        | _LL_READ_DIR
        | _LL_REMOVE_DIR
        | _LL_REMOVE_FILE
        | _LL_MAKE_CHAR
        | _LL_MAKE_DIR
        | _LL_MAKE_REG
        | _LL_MAKE_SOCK
        | _LL_MAKE_FIFO
        | _LL_MAKE_BLOCK
        | _LL_MAKE_SYM
    )
    if abi >= 2:
        mask |= _LL_REFER
    if abi >= 3:
        mask |= _LL_TRUNCATE
    return mask


def _add_landlock_path_rule(
    libc: ctypes.CDLL,
    add_rule_nr: int,
    ruleset_fd: int,
    path: Path,
    access: int,
) -> None:
    try:
        fd = os.open(path, getattr(os, "O_PATH", 0o10000000) | os.O_CLOEXEC)
    except FileNotFoundError:
        return
    try:
        attr = _PathBeneathAttr(access, fd, 0)
        result = libc.syscall(
            add_rule_nr,
            ruleset_fd,
            _LANDLOCK_RULE_PATH_BENEATH,
            ctypes.byref(attr),
            0,
        )
        if result != 0:
            error = ctypes.get_errno()
            raise ExecutionError(f"Landlock path rule failed for {path}: errno {error}")
    finally:
        os.close(fd)


def _apply_landlock(isolated_root: Path, workspace_root: Path | None) -> None:
    create_nr, add_rule_nr, restrict_nr = _landlock_syscall_numbers()
    libc = ctypes.CDLL(None, use_errno=True)
    abi = libc.syscall(create_nr, 0, 0, _LANDLOCK_CREATE_RULESET_VERSION)
    if abi < 1:
        error = ctypes.get_errno()
        raise ExecutionError(f"Linux Landlock unavailable: errno {error}")
    handled = _landlock_supported_mask(int(abi))
    ruleset_attr = _RulesetAttr(handled)
    ruleset_fd = libc.syscall(create_nr, ctypes.byref(ruleset_attr), ctypes.sizeof(ruleset_attr), 0)
    if ruleset_fd < 0:
        error = ctypes.get_errno()
        raise ExecutionError(f"cannot create Landlock ruleset: errno {error}")
    try:
        read_exec = _LL_EXECUTE | _LL_READ_FILE | _LL_READ_DIR
        full = handled
        for system_root in (
            Path("/usr"),
            Path("/bin"),
            Path("/sbin"),
            Path("/lib"),
            Path("/lib64"),
            Path("/etc"),
            Path("/proc"),
            Path("/sys"),
            Path("/opt"),
        ):
            _add_landlock_path_rule(libc, add_rule_nr, ruleset_fd, system_root, read_exec)
        for device in (Path("/dev/null"), Path("/dev/urandom"), Path("/dev/random")):
            _add_landlock_path_rule(
                libc,
                add_rule_nr,
                ruleset_fd,
                device,
                _LL_READ_FILE | _LL_WRITE_FILE,
            )
        _add_landlock_path_rule(libc, add_rule_nr, ruleset_fd, isolated_root, full)
        if workspace_root is not None:
            _add_landlock_path_rule(libc, add_rule_nr, ruleset_fd, workspace_root, full)
        if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            error = ctypes.get_errno()
            raise ExecutionError(f"cannot set no_new_privs: errno {error}")
        if libc.syscall(restrict_nr, ruleset_fd, 0) != 0:
            error = ctypes.get_errno()
            raise ExecutionError(f"cannot enforce Landlock ruleset: errno {error}")
    finally:
        os.close(ruleset_fd)


def _parse_sandbox_request(argv: list[str]) -> tuple[Path, Path | None, list[str]]:
    if "--" not in argv:
        raise ExecutionError("sandbox wrapper: missing command separator")
    separator = argv.index("--")
    options = argv[:separator]
    command = argv[separator + 1 :]
    isolated_root: Path | None = None
    workspace_root: Path | None = None
    index = 0
    while index < len(options):
        option = options[index]
        if option == "--isolated-root" and index + 1 < len(options):
            isolated_root = Path(options[index + 1]).resolve()
            index += 2
        elif option == "--workspace-root" and index + 1 < len(options):
            workspace_root = Path(options[index + 1]).resolve()
            index += 2
        else:
            raise ExecutionError(f"sandbox wrapper: invalid option {option}")
    if isolated_root is None or not command:
        raise ExecutionError("sandbox wrapper: incomplete request")
    return isolated_root, workspace_root, command


def _mount(args: list[str]) -> None:
    completed = subprocess.run(args, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", "replace").strip()
        raise ExecutionError(message or f"mount command failed: {' '.join(args)}")


def _mount_sandbox_exec_main(argv: list[str]) -> int:
    try:
        isolated_root, workspace_root, command = _parse_sandbox_request(argv)
        rootfs = isolated_root / "rootfs"
        rootfs.mkdir(parents=True, exist_ok=True)
        _mount(["mount", "--make-rprivate", "/"])
        _mount(["mount", "-t", "tmpfs", "tmpfs", str(rootfs)])

        for source in ("/usr", "/bin", "/sbin", "/lib", "/lib64", "/etc", "/opt"):
            source_path = Path(source)
            if not source_path.exists():
                continue
            target = rootfs / source.lstrip("/")
            target.mkdir(parents=True, exist_ok=True)
            _mount(["mount", "--rbind", source, str(target)])

        (rootfs / "dev").mkdir(parents=True, exist_ok=True)
        for source in ("/dev/null", "/dev/urandom", "/dev/random"):
            target = rootfs / source.lstrip("/")
            target.touch(exist_ok=True)
            _mount(["mount", "--bind", source, str(target)])
        (rootfs / "proc").mkdir(parents=True, exist_ok=True)
        _mount(["mount", "-t", "proc", "proc", str(rootfs / "proc")])

        sandbox_state = rootfs / "sandbox"
        sandbox_state.mkdir(parents=True, exist_ok=True)
        state_names = {
            "HOME": "home",
            "USERPROFILE": "home",
            "XDG_CONFIG_HOME": "xdg",
            "GH_CONFIG_DIR": "gh",
            "APPDATA": "appdata",
            "LOCALAPPDATA": "local-appdata",
            "TMPDIR": "tmp",
            "TMP": "tmp",
            "TEMP": "tmp",
        }
        for name in sorted(set(state_names.values())):
            source = isolated_root / name
            source.mkdir(parents=True, exist_ok=True)
            target = sandbox_state / name
            target.mkdir(parents=True, exist_ok=True)
            _mount(["mount", "--bind", str(source), str(target)])

        if workspace_root is not None:
            workspace_target = rootfs / "workspace"
            workspace_target.mkdir(parents=True, exist_ok=True)
            _mount(["mount", "--bind", str(workspace_root), str(workspace_target)])
            workdir = "/workspace"
        else:
            workdir = "/sandbox/tmp"

        environment = dict(os.environ)
        for key, name in state_names.items():
            environment[key] = f"/sandbox/{name}"
        os.chroot(rootfs)
        os.chdir(workdir)
        os.execvpe(command[0], command, environment)
    except Exception as exc:
        print(f"filesystem sandbox unavailable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 126


def _sandbox_exec_main(argv: list[str]) -> int:
    try:
        isolated_root, workspace_root, command = _parse_sandbox_request(argv)
        _apply_landlock(isolated_root, workspace_root)
        os.execvpe(command[0], command, os.environ)
    except ExecutionError as landlock_error:
        unshare = shutil.which("unshare")
        if unshare is None or platform.system() != "Linux":
            print(f"filesystem sandbox unavailable: {landlock_error}", file=sys.stderr)
            return 126
        fallback = [
            unshare,
            "--user",
            "--map-root-user",
            "--mount",
            "--pid",
            "--fork",
            sys.executable,
            str(Path(__file__).resolve()),
            _MOUNT_SANDBOX_MARKER,
            "--isolated-root",
            str(isolated_root),
        ]
        if workspace_root is not None:
            fallback.extend(["--workspace-root", str(workspace_root)])
        fallback.extend(["--", *command])
        try:
            os.execvpe(fallback[0], fallback, os.environ)
        except Exception as exc:
            print(f"filesystem sandbox unavailable: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 126
    except Exception as exc:
        print(f"filesystem sandbox unavailable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 126


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
        github_credentials: bool = False,
        filesystem_root: Path | None = None,
    ) -> CommandRecord:
        if not argv or not all(isinstance(item, str) and item for item in argv):
            raise ExecutionError("argv must be a non-empty list of non-empty strings")
        if timeout_seconds <= 0:
            raise ExecutionError("timeout_seconds must be positive")
        command_id = self._next_id()
        started_at = utc_now()
        start = time.monotonic()
        executable = Path(argv[0]).name.lower()
        include_github_auth = github_credentials or executable in {"gh", "gh.exe"}
        trusted_infrastructure_git = executable in {"git", "git.exe"}
        ambient_secrets = _ambient_secret_values()
        config_context = (
            nullcontext(None)
            if include_github_auth
            else tempfile.TemporaryDirectory(prefix="codespace-evidence-env-")
        )
        with config_context as isolated_directory:
            isolated_root = Path(isolated_directory).resolve() if isolated_directory is not None else None
            environment = safe_environment(
                extra_env,
                include_github_auth=include_github_auth,
                isolated_config_root=isolated_root,
            )
            effective_filesystem_root = filesystem_root
            if (
                effective_filesystem_root is None
                and cwd.name == "repository"
                and cwd.parent.name.startswith("codespace-evidence-")
                and (cwd / ".git").exists()
            ):
                effective_filesystem_root = cwd
            launch_argv = list(argv)
            if not include_github_auth and not trusted_infrastructure_git:
                assert isolated_root is not None
                launch_argv = [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    _SANDBOX_MARKER,
                    "--isolated-root",
                    str(isolated_root),
                ]
                if effective_filesystem_root is not None:
                    launch_argv.extend(["--workspace-root", str(effective_filesystem_root.resolve())])
                launch_argv.extend(["--", *argv])
            process = subprocess.Popen(
                launch_argv,
                cwd=str(cwd),
                env=environment,
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
        stdout = redact_text(stdout_b.decode("utf-8", "replace"), ambient_secrets)
        stderr = redact_text(stderr_b.decode("utf-8", "replace"), ambient_secrets)
        stdout_redacted_b = stdout.encode("utf-8")
        stderr_redacted_b = stderr.encode("utf-8")
        record = CommandRecord(
            id=command_id,
            argv=redact_argv(argv, ambient_secrets),
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
        "python": {"version": sys.version.split()[0], "executable": sys.executable},
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


if __name__ == "__main__" and len(sys.argv) >= 2:
    if sys.argv[1] == _SANDBOX_MARKER:
        raise SystemExit(_sandbox_exec_main(sys.argv[2:]))
    if sys.argv[1] == _MOUNT_SANDBOX_MARKER:
        raise SystemExit(_mount_sandbox_exec_main(sys.argv[2:]))
