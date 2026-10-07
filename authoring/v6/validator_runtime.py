#!/usr/bin/env python3
"""Runtime adapter that executes the exact historical V6 validator on current main."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
V6_VALIDATOR = ROOT / "authoring/v6/validate_kit.py"
V6_SCHEMA = ROOT / "contracts/learnit-kit-v6.schema.json"
COMPAT_V4 = ROOT / "authoring/v6/_compat/v4_validate_kit.py"
COMPAT_V5 = ROOT / "authoring/v6/_compat/v5_validate_kit.py"
V6_SCHEMA_BLOB = "0b61612ce711a5a6bd0e278385204188f130818b"
V6_VALIDATOR_BLOB = "1650d550810c50b5fdf64d14cbff42c9c94c4202"
COMPAT_V4_BLOB = "4ef561dfc1137aa436b4d8c8820db421ab6e1861"
COMPAT_V5_BLOB = "0b93925eb22058878f13bc86554126846d2923d1"


class V6RuntimeError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - Git object identity is SHA-1 by contract.


def _assert_blob(path: Path, expected: str, label: str) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise V6RuntimeError(f"{label}: cannot read {path}: {exc}") from exc
    actual = git_blob_sha(data)
    if actual != expected:
        raise V6RuntimeError(f"{label}: git blob mismatch expected={expected} actual={actual}")
    return data


def assert_exact_identities() -> dict[str, str]:
    _assert_blob(V6_SCHEMA, V6_SCHEMA_BLOB, "V6 schema")
    _assert_blob(V6_VALIDATOR, V6_VALIDATOR_BLOB, "V6 validator")
    _assert_blob(COMPAT_V4, COMPAT_V4_BLOB, "V4 compatibility source")
    _assert_blob(COMPAT_V5, COMPAT_V5_BLOB, "V5 compatibility source")
    return {
        "schemaBlob": V6_SCHEMA_BLOB,
        "validatorBlob": V6_VALIDATOR_BLOB,
        "compatV4Blob": COMPAT_V4_BLOB,
        "compatV5Blob": COMPAT_V5_BLOB,
    }


def _ensure_package(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = []  # type: ignore[attr-defined]
        sys.modules[name] = module
    return module


def _load(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V6RuntimeError(f"cannot load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise V6RuntimeError(f"cannot execute {name}: {exc}") from exc
    return module


def load_exact_validator() -> types.ModuleType:
    """Load the exact V6 validator with exact historical V4/V5 semantics isolated under V6."""
    assert_exact_identities()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    pkg_v4 = _ensure_package("authoring.v4")
    v4 = _load("authoring.v4.validate_kit", COMPAT_V4)
    setattr(pkg_v4, "validate_kit", v4)

    pkg_v5 = _ensure_package("authoring.v5")
    v5 = _load("authoring.v5.validate_kit", COMPAT_V5)
    setattr(pkg_v5, "validate_kit", v5)

    return _load("learnit_v6_exact_validator", V6_VALIDATOR)


def validate_document(document: dict[str, Any], label: str = "kit") -> Any:
    v6 = load_exact_validator()
    schema = v6.load(V6_SCHEMA)
    if not isinstance(schema, dict):
        raise V6RuntimeError("V6 schema root must be an object")
    return v6.validate(Path(label), document, schema)


def fill_new_digests(document: dict[str, Any]) -> list[str]:
    return list(load_exact_validator().fill_new_digests(document))
