#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from support import ROOT, active_script_paths

RUNTIME = ROOT / "src/scripts/core/runtime_parts"
BOOT = RUNTIME / "00_runtime_boot_and_content_library.js"
PORT = RUNTIME / "04_local_storage_port.js"
DURABLE = RUNTIME / "05_durable_library_store.js"
PORT_REL = "src/scripts/core/runtime_parts/04_local_storage_port.js"
EXPECTED_PORT_SHA = "ac552c7daad97daab2a436170416324557bc5bd6a83944a1b144e5985a7567c3"
EXPECTED_RUNTIME_FP = "a2baa53db1c4d232073b79bf4f08c7245b756182dc3a98b830187fdddee32fca"
EXPECTED_NORMALIZED_FP = "d9d078c482250ccdc63042823a7dcab9662d117135d504c686fbb9eefdec2d73"
FROZEN_KEYS = (
    "learnit_clean_state_v2", "learnit_clean_journal_v2", "learnit_content_patches_v2",
    "learnit_active_course_v1", "learnit_field_evidence_v1", "learnit_imported_courses_v1",
    "learnit_import_history_v1", "learnit_import_last_applied_v1", "learnit_import_transaction_v1",
    "learnit_recovery_report_v1", "learnit_resilience_meta_v1", "learnit_library_revision_v1",
    "learnit_library_persistence_meta_v1",
)


def main() -> int:
    boot = BOOT.read_text(encoding="utf-8")
    port_bytes = PORT.read_bytes() if PORT.exists() else b""
    port = port_bytes.decode("utf-8") if port_bytes else ""
    durable = DURABLE.read_text(encoding="utf-8")
    owners = json.loads((ROOT / "docs/OWNER_MAP.json").read_text(encoding="utf-8"))["owners"]
    registry = json.loads((ROOT / "dev/checks_registry.json").read_text(encoding="utf-8"))
    release = json.loads((ROOT / "dev/release_config.json").read_text(encoding="utf-8"))
    sources = {path.name: path.read_text(encoding="utf-8") for path in sorted(RUNTIME.glob("*.js"))}
    paths = active_script_paths()
    boundary = [
        "src/scripts/core/runtime_parts/00_runtime_boot_and_content_library.js",
        PORT_REL,
        "src/scripts/core/runtime_parts/05_durable_library_store.js",
        "src/scripts/core/runtime_parts/10_content_store_and_state.js",
    ]
    start = paths.index(boundary[0]) if boundary[0] in paths else -1
    local_owners = sorted(name for name, text in sources.items() if "window.localStorage" in text)
    indexeddb_owners = sorted(name for name, text in sources.items() if "indexedDB" in text)
    port_sha = hashlib.sha256(port_bytes).hexdigest()
    missing_keys = sorted(key for key in FROZEN_KEYS if key not in boot + durable)
    ignored = release.get("baseline_equivalence", {}).get("ignored_script_paths", [])
    banned = [token for token in ("indexedDB", "fetch(", "XMLHttpRequest", "WebSocket", "http://", "https://") if token in port]
    checks = [
        {"code": "sole-localstorage-owner", "ok": local_owners == [PORT.name], "detail": local_owners},
        {"code": "sole-indexeddb-owner", "ok": indexeddb_owners == [DURABLE.name], "detail": indexeddb_owners},
        {"code": "boot-no-inline-adapter", "ok": "const storage = (()=>{" not in boot},
        {"code": "adapter-byte-equivalent", "ok": port_sha == EXPECTED_PORT_SHA, "detail": port_sha},
        {"code": "frozen-key-set-present", "ok": not missing_keys, "detail": missing_keys},
        {"code": "manifest-boundary-order", "ok": start >= 0 and paths[start:start + 4] == boundary, "detail": paths[start:start + 4] if start >= 0 else []},
        {"code": "owner-map-port", "ok": owners.get(PORT_REL) == "synchronous-local-storage-port-memory-fallback-telemetry-and-fault-injection", "detail": owners.get(PORT_REL)},
        {"code": "focused-test-registered-once", "ok": registry.get("mandatory", []).count("tests/contract_storage_boundary.py") == 1, "detail": registry.get("mandatory", []).count("tests/contract_storage_boundary.py")},
        {"code": "port-ignored-once", "ok": ignored.count(PORT_REL) == 1, "detail": ignored.count(PORT_REL)},
        {"code": "runtime-fingerprint-bound", "ok": release.get("runtime_fingerprint") == EXPECTED_RUNTIME_FP, "detail": release.get("runtime_fingerprint")},
        {"code": "normalized-fingerprint-frozen", "ok": release.get("baseline_equivalence", {}).get("runtime_js_normalized_sha256") == EXPECTED_NORMALIZED_FP, "detail": release.get("baseline_equivalence", {}).get("runtime_js_normalized_sha256")},
        {"code": "no-new-storage-or-network", "ok": not banned, "detail": banned},
    ]
    payload = {"schema": "learnit.first_storage_seam_observability.v1", "ok": all(item["ok"] for item in checks), "checks": checks}
    self_path = Path(__file__)
    self_path.write_text(self_path.read_text(encoding="utf-8") + "\n# DIAGNOSTIC_RESULT=" + json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# DIAGNOSTIC_RESULT={"checks":[{"code":"sole-localstorage-owner","detail":["04_local_storage_port.js"],"ok":true},{"code":"sole-indexeddb-owner","detail":["05_durable_library_store.js","10_content_store_and_state.js"],"ok":false},{"code":"boot-no-inline-adapter","ok":true},{"code":"adapter-byte-equivalent","detail":"ac552c7daad97daab2a436170416324557bc5bd6a83944a1b144e5985a7567c3","ok":true},{"code":"frozen-key-set-present","detail":[],"ok":true},{"code":"manifest-boundary-order","detail":["src/scripts/core/runtime_parts/00_runtime_boot_and_content_library.js","src/scripts/core/runtime_parts/04_local_storage_port.js","src/scripts/core/runtime_parts/05_durable_library_store.js","src/scripts/core/runtime_parts/10_content_store_and_state.js"],"ok":true},{"code":"owner-map-port","detail":"synchronous-local-storage-port-memory-fallback-telemetry-and-fault-injection","ok":true},{"code":"focused-test-registered-once","detail":1,"ok":true},{"code":"port-ignored-once","detail":1,"ok":true},{"code":"runtime-fingerprint-bound","detail":"a2baa53db1c4d232073b79bf4f08c7245b756182dc3a98b830187fdddee32fca","ok":true},{"code":"normalized-fingerprint-frozen","detail":"d9d078c482250ccdc63042823a7dcab9662d117135d504c686fbb9eefdec2d73","ok":true},{"code":"no-new-storage-or-network","detail":[],"ok":true}],"ok":false,"schema":"learnit.first_storage_seam_observability.v1"}
