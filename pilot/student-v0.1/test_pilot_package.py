#!/usr/bin/env python3
"""Static/determinism qualification for the Student V0.1 pilot archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "pilot" / "student-v0.1" / "build_pilot_package.py"
PREFIX = "student-v01-pilot/"
EXPECTED = [
    PREFIX + "START_HERE.html",
    PREFIX + "course.learnit.json",
    PREFIX + "learnit-next.html",
    PREFIX + "pilot_manifest.json",
]
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
EXPECTED_MODE = 0o100644


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(app: Path, kit: Path, output: Path) -> None:
    subprocess.run(
        [sys.executable, "-B", str(BUILDER), "--app", str(app), "--kit", str(kit), "--output", str(output)],
        cwd=ROOT,
        check=True,
    )


def assert_safe_name(name: str) -> None:
    path = Path(name)
    assert not path.is_absolute(), name
    assert ".." not in path.parts, name
    assert name.startswith(PREFIX), name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--kit", type=Path, required=True)
    args = parser.parse_args()
    app_bytes = args.app.read_bytes()
    kit_bytes = args.kit.read_bytes()

    builder_text = BUILDER.read_text(encoding="utf-8")
    assert "make_valid_v4" not in builder_text, "generic package builder must not depend on qualification generator"

    with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
        first = Path(first_dir) / "pilot.zip"
        second = Path(second_dir) / "pilot.zip"
        build(args.app, args.kit, first)
        build(args.app, args.kit, second)
        raw_first = first.read_bytes()
        raw_second = second.read_bytes()
        assert raw_first == raw_second, "identical inputs must produce byte-identical archives"

        with zipfile.ZipFile(first) as archive:
            infos = archive.infolist()
            assert archive.comment == b""
            names = [info.filename for info in infos]
            assert names == EXPECTED, names
            assert names == sorted(names), names
            for info in infos:
                assert_safe_name(info.filename)
                assert info.date_time == ZIP_TIME, (info.filename, info.date_time)
                assert info.compress_type == zipfile.ZIP_STORED, info.filename
                assert info.extra == b"", info.filename
                assert info.comment == b"", info.filename
                assert ((info.external_attr >> 16) & 0o177777) == EXPECTED_MODE, (info.filename, oct(info.external_attr >> 16))
            extracted_app = archive.read(PREFIX + "learnit-next.html")
            extracted_kit = archive.read(PREFIX + "course.learnit.json")
            start = archive.read(PREFIX + "START_HERE.html")
            manifest_raw = archive.read(PREFIX + "pilot_manifest.json")

        assert extracted_app == app_bytes
        assert extracted_kit == kit_bytes
        manifest = json.loads(manifest_raw.decode("utf-8"))
        assert manifest["schema"] == "student.v0.1.pilot-package.v1"
        assert manifest["app"] == {
            "filename": "learnit-next.html",
            "bytes": len(app_bytes),
            "sha256": sha256(app_bytes),
        }
        assert manifest["kit"]["filename"] == "course.learnit.json"
        assert manifest["kit"]["bytes"] == len(kit_bytes)
        assert manifest["kit"]["sha256"] == sha256(kit_bytes)
        assert manifest["kit"]["contract"] == "learnit.kit.v4"
        assert manifest["start"] == {"filename": "START_HERE.html", "mode": "DIRECT_FILE"}
        assert manifest["localOffline"] is True

        start_text = start.decode("utf-8")
        lowered = start_text.lower()
        assert 'href="learnit-next.html"' in start_text
        assert "http://" not in lowered and "https://" not in lowered
        assert "Actions obligatoires jusqu’au démarrage du cours : 6." in start_text

        extract_root = Path(first_dir) / "extract"
        with zipfile.ZipFile(first) as archive:
            for info in archive.infolist():
                assert_safe_name(info.filename)
            archive.extractall(extract_root)
        root = extract_root / "student-v01-pilot"
        assert (root / "learnit-next.html").read_bytes() == app_bytes
        assert (root / "course.learnit.json").read_bytes() == kit_bytes

        invalid = Path(first_dir) / "invalid.json"
        invalid.write_text('{"contract":"learnit.kit.v4"}\n', encoding="utf-8")
        rejected = subprocess.run(
            [sys.executable, "-B", str(BUILDER), "--app", str(args.app), "--kit", str(invalid), "--output", str(Path(first_dir) / "invalid.zip")],
            cwd=ROOT,
        )
        assert rejected.returncode != 0, "builder must fail closed on non-canonical V4 JSON"

        print(f"PILOT_PACKAGE_BYTES={len(raw_first)}")
        print(f"PILOT_PACKAGE_SHA256={sha256(raw_first)}")
        print("STUDENT_V01_JOB07_R2_PACKAGE_MANIFEST_BINDING=PASS")
        print("STUDENT_V01_JOB07_R2_PACKAGE_DETERMINISM=PASS")
        print("STUDENT_V01_JOB07_R2_PACKAGE_INTEGRITY=PASS")
        print("STUDENT_V01_JOB07_R2_START_INSTRUCTIONS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
