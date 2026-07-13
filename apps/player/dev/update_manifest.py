#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import json

from release_utils import ROOT, CONFIG_PATH, MANIFEST_PATH, load_config


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_entry(entry: dict) -> dict:
    out = {key: value for key, value in entry.items() if key not in {"bytes", "sha256", "files"}}
    if entry.get("path"):
        path = ROOT / entry["path"]
        if not path.exists():
            raise FileNotFoundError(entry["path"])
        out["bytes"] = path.stat().st_size
        out["sha256"] = sha256(path)
    if entry.get("paths"):
        refreshed = []
        total = 0
        joined = hashlib.sha256()
        for rel in entry["paths"]:
            path = ROOT / rel
            if not path.exists():
                raise FileNotFoundError(rel)
            data = path.read_bytes()
            joined.update(rel.encode("utf-8") + b"\0" + data)
            refreshed.append({"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            total += len(data)
        out["files"] = refreshed
        out["bytes"] = total
        out["sha256"] = joined.hexdigest()
    return out


def main() -> None:
    config = load_config()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    slug = str(config["rc"]).lower()
    manifest.update({
        "schema": f"learnit.{slug}.source_manifest.v1",
        "rc": config["rc"],
        "base": config["base"],
        "build": config["build"],
        "principle": config["principle"],
        "build_timestamp": config["build_timestamp"],
        "release_config_sha256": sha256(CONFIG_PATH),
    })
    manifest["template_sha256"] = sha256(ROOT / manifest["template"])
    manifest["styles"] = [refresh_entry(entry) for entry in manifest.get("styles", [])]
    manifest["scripts"] = [refresh_entry(entry) for entry in sorted(manifest.get("scripts", []), key=lambda item: item.get("order", 0))]
    manifest["contracts"] = [refresh_entry(entry) for entry in manifest.get("contracts", [])]
    manifest["dev"] = {
        "schema": f"learnit.{slug}.dev_manifest.v1",
        "releaseConfig": "dev/release_config.json",
        "engineeringContract": "docs/ENGINEERING.md",
        "checksRegistry": "dev/checks_registry.json",
        "runAllChecks": "dev/run_all_checks.py",
        "updateManifest": "dev/update_manifest.py",
        "releasePipeline": "dev/release_pipeline.py",
        "packageRelease": "dev/package_release.py",
        "verifyBundle": "dev/verify_release_bundle.py",
        "handover": "README.md"
    }
    manifest["human_validation"] = config.get("human_validation", {})
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(MANIFEST_PATH.relative_to(ROOT)), "rc": config["rc"], "scripts": len(manifest.get("scripts", [])), "styleEntries": len(manifest.get("styles", [])), "buildTimestamp": manifest["build_timestamp"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
