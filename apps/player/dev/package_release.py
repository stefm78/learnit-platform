#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import shutil
import zipfile

from release_utils import ROOT, load_config, load_manifest, load_registry, rc_slug, sha256_file, utc_now

GENERATED_DIRS = {"dist", "reports", "release", "__pycache__", ".pytest_cache", ".git"}


def iter_source_files(base: Path):
    for path in sorted(base.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(base)
        if any(part in GENERATED_DIRS for part in rel.parts) or path.suffix == ".pyc":
            continue
        yield path


def zip_paths(output: Path, members: list[tuple[Path, Path]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in members:
            archive.write(source, arcname)


def component(path: Path, role: str) -> dict:
    return {"name": path.name, "role": role, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def main() -> int:
    parser = ArgumentParser(description="Package the exact tested artifact and minimal continuation source.")
    parser.add_argument("--output-dir", default="release")
    args = parser.parse_args()

    config, manifest, registry = load_config(), load_manifest(), load_registry()
    slug = rc_slug(manifest["rc"])
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    aggregate_path = ROOT / registry["reports"]["aggregate"]
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    if not aggregate.get("automationReady", aggregate.get("releaseReady")):
        raise RuntimeError("aggregate report is not release-ready")
    tested = aggregate["testedArtifact"]
    artifact = ROOT / tested["path"]
    if sha256_file(artifact) != tested["sha256"]:
        raise RuntimeError("tested artifact hash mismatch")

    dist_out = output_dir / f"learnit_{slug}_dist.html"
    aggregate_out = output_dir / f"learnit_{slug}_aggregate_report.json"
    metrics_out = output_dir / f"learnit_{slug}_source_tree_metrics.json"
    source_zip = output_dir / f"learnit_{slug}_minimal_source.zip"
    handover_out = output_dir / f"HANDOVER_{manifest['rc']}_MINIMAL.md"
    authoring_pack = output_dir / "learnit-kit-authoring-pack.zip"
    evidence_bundle = output_dir / f"learnit_{slug}_evidence_bundle.zip"

    shutil.copy2(artifact, dist_out)
    shutil.copy2(aggregate_path, aggregate_out)
    metrics_source = ROOT / registry["reports"]["cleanliness"]
    if metrics_source.exists():
        shutil.copy2(metrics_source, metrics_out)
    handover_out.write_text((ROOT / "README.md").read_text(encoding="utf-8"), encoding="utf-8")

    prefix = Path(f"learnit_{slug}_source")
    members = [(path, prefix / path.relative_to(ROOT)) for path in iter_source_files(ROOT)]
    zip_paths(source_zip, members)
    authoring_members = []
    for rel in manifest.get("authoring_pack", {}).get("paths", []):
        source = ROOT / rel
        if not source.exists():
            raise FileNotFoundError(rel)
        authoring_members.append((source, Path("learnit-kit-authoring-pack") / rel))
    zip_paths(authoring_pack, authoring_members)

    evidence_members = []
    reports_dir = ROOT / "reports"
    for report_path in sorted(reports_dir.glob("*.json")):
        evidence_members.append((report_path, Path(f"learnit_{slug}_evidence") / report_path.name))
    progress_log = reports_dir / "check_progress.log"
    if progress_log.exists():
        evidence_members.append((progress_log, Path(f"learnit_{slug}_evidence") / progress_log.name))
    zip_paths(evidence_bundle, evidence_members)

    components = [
        component(dist_out, "exact-tested-application"),
        component(aggregate_out, "automated-evidence"),
        component(source_zip, "minimal-continuation-source"),
        component(handover_out, "handover-entry-point"),
        component(authoring_pack, "kit-authoring-contract-pack"),
        component(evidence_bundle, "fresh-bound-test-evidence"),
    ]
    if metrics_out.exists():
        components.append(component(metrics_out, "source-tree-evidence"))

    artifact_manifest = {
        "schema": f"learnit.{slug}.artifact_manifest.v1",
        "rc": manifest["rc"],
        "generatedAt": utc_now(),
        "testedArtifact": tested,
        "packagedArtifact": component(dist_out, "exact-tested-application"),
        "testedEqualsPackaged": tested["sha256"] == sha256_file(dist_out),
        "automationReady": bool(aggregate.get("automationReady", aggregate.get("releaseReady"))),
        "promotionReady": bool(aggregate.get("promotionReady")),
        "humanValidation": config.get("human_validation", {}),
        "historyPolicy": "Historical material is external to the active source and default release bundle.",
        "contractVersion": json.loads((ROOT / "contract/learnit-capabilities.json").read_text(encoding="utf-8"))["contract_version"],
        "components": components,
    }
    if not artifact_manifest["testedEqualsPackaged"]:
        raise RuntimeError("packaged artifact is not byte-identical to tested artifact")
    artifact_manifest_path = output_dir / "ARTIFACT_MANIFEST.json"
    artifact_manifest_path.write_text(json.dumps(artifact_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    integrity_path = output_dir / f"learnit_{slug}_integrity_report.json"
    integrity = {
        "schema": f"learnit.{slug}.integrity_report.v1",
        "ok": all((output_dir / item["name"]).exists() and sha256_file(output_dir / item["name"]) == item["sha256"] for item in components),
        "componentCount": len(components),
        "testedEqualsPackaged": artifact_manifest["testedEqualsPackaged"],
    }
    integrity_path.write_text(json.dumps(integrity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not integrity["ok"]:
        raise RuntimeError("component integrity failure")

    bundle = output_dir / f"learnit_{slug}_{config.get('bundle_label', 'release_bundle')}.zip"
    bundle_files = [*[(output_dir / item["name"]) for item in components], artifact_manifest_path, integrity_path]
    zip_paths(bundle, [(path, Path(f"learnit_{slug}_release") / path.name) for path in bundle_files])

    package_report = {
        "schema": f"learnit.{slug}.package_report.v1",
        "ok": True,
        "generatedAt": utc_now(),
        "testedArtifactSha256": tested["sha256"],
        "packagedArtifactSha256": sha256_file(dist_out),
        "testedEqualsPackaged": tested["sha256"] == sha256_file(dist_out),
        "components": components,
        "artifactManifest": component(artifact_manifest_path, "component-index"),
        "integrityReport": component(integrity_path, "integrity-evidence"),
        "bundle": component(bundle, "minimal-release-bundle"),
        "automationReady": bool(aggregate.get("automationReady", aggregate.get("releaseReady"))),
        "promotionReady": bool(aggregate.get("promotionReady")),
        "humanValidation": config.get("human_validation", {}),
    }
    package_report_path = output_dir / f"learnit_{slug}_package_report.json"
    package_report_path.write_text(json.dumps(package_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target = ROOT / registry["reports"]["package"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(package_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(package_report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
