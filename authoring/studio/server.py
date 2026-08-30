#!/usr/bin/env python3
"""Loopback-only HTTP server for the M3.0 Authoring Foundation."""
from __future__ import annotations

import argparse
import ipaddress
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from .core import AuthoringError, apply_edit, build_preview, create_draft, export_draft, validate_draft
except ImportError:
    from core import AuthoringError, apply_edit, build_preview, create_draft, export_draft, validate_draft

WEB_ROOT = Path(__file__).resolve().parent / "web"
MAX_REQUEST_BYTES = 3_000_000


def loopback_host(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Authoring Studio host must be a numeric loopback address") from exc
    if not address.is_loopback:
        raise argparse.ArgumentTypeError("Authoring Studio may bind only to a loopback address")
    return value


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "LearnitAuthoringM3/1"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[authoring-studio] {self.address_string()} - {format % args}")

    def end_headers(self) -> None:
        # Cross-origin access is deliberately not enabled.
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

    def _body(self) -> bytes:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "0")
        except ValueError as exc:
            raise AuthoringError("HTTP_LENGTH", "Invalid Content-Length") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise AuthoringError("HTTP_SIZE", "Request body exceeds 3 MB")
        return self.rfile.read(length)

    def _json_body(self) -> dict[str, Any]:
        raw = self._body()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuthoringError("HTTP_JSON", "Request body must be valid UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise AuthoringError("HTTP_JSON", "Request JSON root must be an object")
        return value

    def _send_json(self, status: int, value: Any) -> None:
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, status: int, exc: Exception) -> None:
        if isinstance(exc, AuthoringError):
            diagnostic = exc.diagnostic()
        else:
            diagnostic = {
                "severity": "blocking",
                "code": "SERVER_FAILURE",
                "path": "$",
                "cause": str(exc),
            }
        self._send_json(status, {"ok": False, "diagnostic": diagnostic})

    def do_OPTIONS(self) -> None:
        self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"ok": False, "cause": "CORS is not enabled"})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"ok": True, "scope": "loopback-only", "network": "offline"})
            return
        if path == "/":
            path = "/index.html"
        relative = path.lstrip("/")
        if relative not in {"index.html", "studio.css", "studio.js"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "cause": "Not found"})
            return
        file_path = WEB_ROOT / relative
        if not file_path.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "cause": "Not found"})
            return
        data = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/import":
                raw = self._body()
                source_name = self.headers.get("X-Learnit-Source-Name", "kit.json")
                draft = create_draft(raw, source_name)
                self._send_json(HTTPStatus.OK, {"ok": True, "draft": draft, "validation": validate_draft(draft)})
                return
            if path == "/api/edit":
                request = self._json_body()
                draft = apply_edit(request.get("draft"), request.get("path"), request.get("value"))
                self._send_json(HTTPStatus.OK, {"ok": True, "draft": draft, "validation": validate_draft(draft)})
                return
            if path == "/api/validate":
                request = self._json_body()
                self._send_json(HTTPStatus.OK, {"ok": True, "validation": validate_draft(request.get("draft"))})
                return
            if path == "/api/preview":
                request = self._json_body()
                preview = build_preview(
                    request.get("draft"), request.get("courseIndex"), request.get("activityIndex")
                )
                self._send_json(HTTPStatus.OK, {"ok": True, "preview": preview})
                return
            if path == "/api/export":
                request = self._json_body()
                data, digest = export_draft(request.get("draft"))
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="learnit-atlas-export.json"')
                self.send_header("X-Learnit-Sha256", digest)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "cause": "Not found"})
        except AuthoringError as exc:
            self._error(HTTPStatus.UNPROCESSABLE_ENTITY, exc)
        except Exception as exc:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, exc)


def parser() -> argparse.ArgumentParser:
    argp = argparse.ArgumentParser(description="Learn-it M3.0 local/offline Authoring Studio")
    argp.add_argument("--host", default="127.0.0.1", type=loopback_host)
    argp.add_argument("--port", default=8765, type=int)
    return argp


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not (0 <= args.port <= 65535):
        raise SystemExit("port must be between 0 and 65535")
    server = ThreadingHTTPServer((args.host, args.port), StudioHandler)
    actual_host, actual_port = server.server_address[:2]
    print(f"Learn-it M3.0 Authoring Studio: http://{actual_host}:{actual_port}/")
    print("Local/offline only. Stop with Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
