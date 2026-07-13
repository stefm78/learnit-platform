#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import zipfile

from release_utils import ROOT, load_manifest, rc_slug, sha256_file, utc_now


def main() -> int:
    parser = ArgumentParser(description="Verify component hashes and bundle membership for a packaged Learn-it release.")
    parser.add_argument("--output-dir", default="release")
    args = parser.parse_args()
    manifest = load_manifest()
    slug = rc_slug(manifest["rc"])
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    artifact_manifest_path = output_dir / "ARTIFACT_MANIFEST.json"
    package_report_path = output_dir / f"learnit_{slug}_package_report.json"
    rows = []

    def add(code: str, ok: bool, detail: str = ""):
        rows.append({"code": code, "ok": bool(ok), "detail": detail})

    add("artifact-manifest-exists", artifact_manifest_path.exists(), artifact_manifest_path.name)
    add("package-report-exists", package_report_path.exists(), package_report_path.name)
    package = json.loads(package_report_path.read_text(encoding="utf-8")) if package_report_path.exists() else {}
    bundle_name = ((package.get("bundle") or {}).get("name") or "")
    bundle_path = output_dir / bundle_name if bundle_name else output_dir / "missing-bundle.zip"
    add("bundle-exists", bundle_path.exists(), bundle_path.name)

    manifest_data = json.loads(artifact_manifest_path.read_text(encoding="utf-8")) if artifact_manifest_path.exists() else {}
    add("tested-equals-packaged", bool(manifest_data.get("testedEqualsPackaged")), str(manifest_data.get("testedArtifact", {})))
    component_names = set()
    for item in manifest_data.get("components", []):
        path = output_dir / item["name"]
        component_names.add(item["name"])
        add(f"component-{item['name']}", path.exists() and sha256_file(path) == item["sha256"], item.get("role", ""))

    if bundle_path.exists():
        with zipfile.ZipFile(bundle_path) as archive:
            names = set(Path(name).name for name in archive.namelist() if not name.endswith("/"))
        required = component_names | {"ARTIFACT_MANIFEST.json", f"learnit_{slug}_integrity_report.json"}
        add("bundle-required-members", required.issubset(names), f"missing={sorted(required - names)}")
        add("bundle-no-unknown-hardcoded-rc-entry", not any(name.startswith("HANDOVER_RC508_") for name in names), str(sorted(name for name in names if name.startswith("HANDOVER_"))))

    ok = all(row["ok"] for row in rows)
    report = {
        "schema": f"learnit.{slug}.external_bundle_verification.v2",
        "ok": ok,
        "generatedAt": utc_now(),
        "checks": rows,
    }
    out = output_dir / f"learnit_{slug}_external_bundle_verification.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
