#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import subprocess
import sys

from release_utils import ROOT, load_manifest, rc_slug, sha256_file, utc_now


def run(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> int:
    parser = ArgumentParser(description="Build once, test exact bytes, package without rebuilding, then verify the bundle.")
    parser.add_argument("--output-dir", default="release")
    args = parser.parse_args()

    run(["dev/update_manifest.py"])
    run(["build.py"])
    artifact = ROOT / "dist" / "learnit.html"
    built_hash = sha256_file(artifact)
    run(["dev/run_all_checks.py", "--skip-build", "--include-browser", "--artifact", "dist/learnit.html"])
    tested_hash = sha256_file(artifact)
    if built_hash != tested_hash:
        raise RuntimeError("artifact changed between build and test completion")
    run(["dev/package_release.py", "--output-dir", args.output_dir])
    run(["dev/verify_release_bundle.py", "--output-dir", args.output_dir])

    manifest = load_manifest()
    slug = rc_slug(manifest["rc"])
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    package_report = json.loads((output_dir / f"learnit_{slug}_package_report.json").read_text(encoding="utf-8"))
    report = {
        "schema": f"learnit.{slug}.release_pipeline_report.v1",
        "ok": True,
        "generatedAt": utc_now(),
        "buildCount": 1,
        "artifactSha256": built_hash,
        "testedArtifactSha256": package_report["testedArtifactSha256"],
        "packagedArtifactSha256": package_report["packagedArtifactSha256"],
        "allArtifactHashesEqual": len({built_hash, package_report["testedArtifactSha256"], package_report["packagedArtifactSha256"]}) == 1,
        "outputDirectory": output_dir.name,
        "bundle": package_report["bundle"],
        "humanValidation": package_report.get("humanValidation", {}),
    }
    out = output_dir / f"learnit_{slug}_release_pipeline_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
