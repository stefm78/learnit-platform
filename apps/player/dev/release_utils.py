#!/usr/bin/env python3
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "dev" / "release_config.json"
MANIFEST_PATH = ROOT / "source_manifest.json"
REGISTRY_PATH = ROOT / "dev" / "checks_registry.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config() -> dict:
    return load_json(CONFIG_PATH)


def load_manifest() -> dict:
    return load_json(MANIFEST_PATH)


def load_registry() -> dict:
    return load_json(REGISTRY_PATH)


def rc_slug(rc: str) -> str:
    value = str(rc).strip().lower()
    return value if value.startswith("rc") else f"rc{value}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def relative_or_name(path: Path, base: Path = ROOT) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return path.name
