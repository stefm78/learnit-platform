#!/usr/bin/env python3
"""Build and optionally serve the isolated Atlas controlled-time candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
BUILD_SCRIPT = APP / "build.py"
INJECT_SCRIPT = Path(__file__).with_name("controlled_time_inject.js")
CANONICAL_ARTIFACT = APP / "dist/learnit-next.html"
DEFAULT_OUTPUT = APP / "dist/learnit-next-controlled-time.html"
DIST = APP / "dist"

CANONICAL_BYTES = 366_412
CANONICAL_SHA256 = "4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7"
INJECTION_MARKER = "LEARNIT_CONTROLLED_TIME_INJECT_V1"
MODULE_OPEN = '<script type="module">\n'
SOURCES_OPEN = "const __sources=Object.freeze("
SOURCES_CLOSE = ");\nconst __dependencies=Object.freeze("
SURFACE_MODULE = "apps/learnit-next/src/integration/atlas/surface.js"
SESSION_MODULE = "apps/learnit-next/src/integration/atlas/session.js"
DEV_DATABASES = (
    "learnit_dev_controlled_time_next_v1",
    "learnit_dev_controlled_time_atlas_m1_v2",
)
DEV_LOCAL_STORAGE_PREFIX = "learnit.dev.controlled-time.next.v1."


class NavigatorError(RuntimeError):
    """The controlled-time candidate contract was violated."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_identity(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def verify_canonical(data: bytes) -> dict[str, Any]:
    identity = artifact_identity(data)
    expected = {"bytes": CANONICAL_BYTES, "sha256": CANONICAL_SHA256}
    if identity != expected:
        raise NavigatorError(
            "CANONICAL_ARTIFACT_IDENTITY_MISMATCH: "
            + json.dumps({"actual": identity, "expected": expected}, sort_keys=True)
        )
    return identity


def run_canonical_build(output: Path) -> bytes:
    completed = subprocess.run(
        [sys.executable, "-B", str(BUILD_SCRIPT), "--output", str(output)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=900,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise NavigatorError(f"CANONICAL_BUILD_FAILED: {detail}")
    try:
        data = output.read_bytes()
    except OSError as exc:
        raise NavigatorError(f"CANONICAL_BUILD_OUTPUT_MISSING: {exc}") from exc
    verify_canonical(data)
    return data


def injection_source() -> str:
    try:
        source = INJECT_SCRIPT.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise NavigatorError(f"CONTROLLED_TIME_INJECTION_UNREADABLE: {exc}") from exc
    if source.count(INJECTION_MARKER) != 1:
        raise NavigatorError("CONTROLLED_TIME_INJECTION_MARKER_INVALID")
    if "</script" in source.lower():
        raise NavigatorError("CONTROLLED_TIME_INJECTION_SCRIPT_ESCAPE_FORBIDDEN")
    forbidden = ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource")
    hits = [token for token in forbidden if token in source]
    if hits:
        raise NavigatorError(f"CONTROLLED_TIME_OUTBOUND_API_FORBIDDEN: {hits}")
    return source.rstrip() + "\n"


def safe_json(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def route_integration_clock(artifact: str) -> str:
    if artifact.count(SOURCES_OPEN) != 1 or artifact.count(SOURCES_CLOSE) != 1:
        raise NavigatorError("CANONICAL_MODULE_SOURCE_TABLE_NOT_UNIQUE")
    before, remainder = artifact.split(SOURCES_OPEN, 1)
    encoded, after = remainder.split(SOURCES_CLOSE, 1)
    try:
        sources = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise NavigatorError("CANONICAL_MODULE_SOURCE_TABLE_INVALID") from exc
    if not isinstance(sources, dict):
        raise NavigatorError("CANONICAL_MODULE_SOURCE_TABLE_INVALID")

    replacements = {
        SURFACE_MODULE: (
            "const now = new Date().toISOString();",
            "const now = globalThis.__LEARNIT_ATLAS_CLOCK__.now();",
        ),
        SESSION_MODULE: (
            "return new Date().toISOString();",
            "return globalThis.__LEARNIT_ATLAS_CLOCK__.now();",
        ),
    }
    for module, (ambient, injected) in replacements.items():
        source = sources.get(module)
        if not isinstance(source, str) or source.count(ambient) != 1:
            raise NavigatorError(f"CANONICAL_CLOCK_SEAM_DRIFT: {module}")
        sources[module] = source.replace(ambient, injected, 1)
    return before + SOURCES_OPEN + safe_json(sources) + SOURCES_CLOSE + after


def render_candidate(canonical: bytes, injection: str) -> bytes:
    verify_canonical(canonical)
    try:
        artifact = canonical.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise NavigatorError("CANONICAL_ARTIFACT_NOT_UTF8") from exc
    if artifact.count(MODULE_OPEN) != 1:
        raise NavigatorError("CANONICAL_MODULE_BOOTSTRAP_NOT_UNIQUE")
    if INJECTION_MARKER in artifact:
        raise NavigatorError("CANONICAL_ARTIFACT_ALREADY_INJECTED")
    candidate = route_integration_clock(artifact)
    candidate = candidate.replace(MODULE_OPEN, MODULE_OPEN + injection, 1)
    if candidate.count(INJECTION_MARKER) != 1:
        raise NavigatorError("CONTROLLED_TIME_INJECTION_FAILED")
    return candidate.encode("utf-8")


def normalized_output(path: Path) -> Path:
    output = path if path.is_absolute() else ROOT / path
    output = output.resolve()
    protected = {
        CANONICAL_ARTIFACT.resolve(),
        BUILD_SCRIPT.resolve(),
        INJECT_SCRIPT.resolve(),
    }
    if output in protected:
        raise NavigatorError("CONTROLLED_TIME_OUTPUT_TARGET_PROTECTED")
    if output.is_relative_to(ROOT) and not output.is_relative_to(DIST.resolve()):
        raise NavigatorError("CONTROLLED_TIME_REPOSITORY_OUTPUT_OUTSIDE_DIST")
    if output.suffix.lower() != ".html":
        raise NavigatorError("CONTROLLED_TIME_OUTPUT_MUST_BE_HTML")
    return output


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
    try:
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def generate(output: Path) -> dict[str, Any]:
    target = normalized_output(output)
    with tempfile.TemporaryDirectory(prefix="learnit-controlled-time-") as directory:
        canonical_path = Path(directory) / "learnit-next-canonical.html"
        canonical = run_canonical_build(canonical_path)
    candidate = render_candidate(canonical, injection_source())
    atomic_write(target, candidate)
    result = {
        "schema": "learnit.atlas.controlled-time-candidate.v1",
        "canonical": artifact_identity(canonical),
        "candidate": {
            **artifact_identity(candidate),
            "path": (
                target.relative_to(ROOT).as_posix()
                if target.is_relative_to(ROOT)
                else target.as_posix()
            ),
        },
        "simulationMarker": INJECTION_MARKER,
        "storage": {
            "indexedDbNames": list(DEV_DATABASES),
            "localStoragePrefix": DEV_LOCAL_STORAGE_PREFIX,
            "isolated": True,
        },
        "networkRequired": False,
        "publishedToNormalPages": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


class LoopbackHandler(SimpleHTTPRequestHandler):
    """Serve one local directory without CORS or permissive Host handling."""

    allowed_hosts = frozenset({"127.0.0.1", "localhost", "[::1]"})

    def _host_allowed(self) -> bool:
        value = self.headers.get("Host", "")
        host = value.rsplit(":", 1)[0] if value.count(":") <= 1 else value
        return host in self.allowed_hosts

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        if not self._host_allowed():
            self.send_error(403, "Loopback Host required")
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib handler contract
        if not self._host_allowed():
            self.send_error(403, "Loopback Host required")
            return
        super().do_HEAD()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()


def serve(output: Path, port: int) -> None:
    target = normalized_output(output)
    if not target.is_file():
        raise NavigatorError("CONTROLLED_TIME_CANDIDATE_MISSING")
    if not 0 <= port <= 65_535:
        raise NavigatorError("CONTROLLED_TIME_PORT_INVALID")

    class BoundHandler(LoopbackHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(target.parent), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", port), BoundHandler)
    actual_port = server.server_address[1]
    print(f"CONTROLLED_TIME_URL=http://127.0.0.1:{actual_port}/{target.name}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an isolated, visibly simulated Atlas time candidate.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    try:
        generate(args.output)
        if args.serve:
            serve(args.output, args.port)
        return 0
    except Exception as exc:
        print(f"CONTROLLED_TIME_NAVIGATOR_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
