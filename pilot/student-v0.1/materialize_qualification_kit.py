#!/usr/bin/env python3
"""Materialize the exact ephemeral canonical V4 qualification kit for JOB07 R2."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.v4.tests.test_validate_v4 import make_valid_v4

FAMILIES = ["lesson", "flashcard", "matching", "order", "classify", "qcm", "fill", "constructed"]
GENERATOR = ROOT / "authoring" / "v4" / "tests" / "test_validate_v4.py"
VALIDATOR = ROOT / "authoring" / "v4" / "validate_kit.py"

def serialize(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = make_valid_v4()
    activities = payload["courses"][0]["activities"]
    families = [item["type"] for item in activities]
    if families != FAMILIES:
        raise SystemExit(f"unexpected family sequence: {families!r}")
    assets = payload.get("assets", [])
    if not any(item.get("format") == "svg" and str(item.get("data", "")).lstrip().startswith("<svg") for item in assets):
        raise SystemExit("canonical generated kit has no inline SVG asset")
    media_refs = sum(len(item.get("media", [])) for item in activities)
    if media_refs < 1:
        raise SystemExit("canonical generated kit has no media reference")
    raw = serialize(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    validation = subprocess.run(
        [sys.executable, "-B", str(VALIDATOR), str(args.output), "--format=json"],
        cwd=ROOT, text=True, capture_output=True,
    )
    if validation.returncode != 0:
        sys.stderr.write(validation.stdout)
        sys.stderr.write(validation.stderr)
        raise SystemExit(validation.returncode)
    report = json.loads(validation.stdout)
    if not report.get("ok"):
        raise SystemExit("canonical validator did not return ok=true")
    print("STUDENT_V01_JOB07_R2_CANONICAL_GENERATOR=PASS")
    print(f"GENERATOR_PATH={GENERATOR.relative_to(ROOT).as_posix()}")
    print(f"GENERATED_KIT_BYTES={len(raw)}")
    print(f"GENERATED_KIT_SHA256={hashlib.sha256(raw).hexdigest()}")
    print(f"PACKAGE_REVISION_DIGEST={payload['packageRevisionDigest']}")
    print(f"COURSE_REVISION_DIGEST={payload['courses'][0]['courseRevisionDigest']}")
    print("ACTIVITY_FAMILIES=" + ",".join(families))
    print(f"ASSET_COUNT={len(assets)}")
    print(f"MEDIA_REFERENCE_COUNT={media_refs}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
