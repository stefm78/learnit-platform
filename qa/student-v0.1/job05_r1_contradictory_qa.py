#!/usr/bin/env python3
"""Independent non-browser contradictory QA for Student V0.1 JOB05 R1."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
FIXTURE = Path(__file__).with_name("JOB05_CANONICAL_V4_FIXTURE.json")
DIST = ROOT / "apps" / "learnit-next" / "dist" / "learnit-next.html"
EXPECTED_FIXTURE_BLOB = "c190fc4f04a7cee5731627e4f6276ee08e39d746"
EXPECTED_BYTES = 478657
EXPECTED_SHA256 = "85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e"
ZERO_DIGEST = "sha256:" + ("0" * 64)
FAMILIES = ["lesson", "flashcard", "matching", "order", "classify", "qcm", "fill", "constructed"]


def command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)


def require_ok(proc: subprocess.CompletedProcess[str], label: str) -> None:
    if proc.returncode != 0:
        raise AssertionError(f"{label} failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")


def fixture_identity_and_validation() -> dict:
    blob = command("git", "hash-object", str(FIXTURE.relative_to(ROOT)))
    require_ok(blob, "git hash-object frozen fixture")
    actual_blob = blob.stdout.strip()
    assert actual_blob == EXPECTED_FIXTURE_BLOB, (actual_blob, EXPECTED_FIXTURE_BLOB)

    validate = command(
        sys.executable, "-B", "authoring/v4/validate_kit.py",
        str(FIXTURE.relative_to(ROOT)), "--format=json",
    )
    require_ok(validate, "canonical V4 validator")
    report = json.loads(validate.stdout)
    assert report["ok"] is True, report

    kit = json.loads(FIXTURE.read_text(encoding="utf-8"))
    actual_families = [item["type"] for item in kit["courses"][0]["activities"]]
    assert actual_families == FAMILIES, actual_families
    assert "assessmentRole" not in kit["courses"][0]["activities"][0]
    assert "assessmentRole" not in kit["courses"][0]["activities"][1]
    return {"blob": actual_blob, "families": actual_families, "validator": "PASS"}


def exact_build_identity() -> dict:
    DIST.parent.mkdir(parents=True, exist_ok=True)
    first = command(sys.executable, "-B", "apps/learnit-next/build.py")
    require_ok(first, "canonical build 1")
    first_bytes = DIST.read_bytes()
    with tempfile.TemporaryDirectory(prefix="job05-r1-build-") as tmp:
        second_path = Path(tmp) / "learnit-next-second.html"
        second = command(
            sys.executable, "-B", "apps/learnit-next/build.py",
            "--output", str(second_path),
        )
        require_ok(second, "canonical build 2")
        second_bytes = second_path.read_bytes()
    evidence = []
    for data in (first_bytes, second_bytes):
        evidence.append({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    assert evidence[0] == evidence[1], evidence
    assert evidence[0] == {"bytes": EXPECTED_BYTES, "sha256": EXPECTED_SHA256}, evidence
    return {"builds": evidence}


def old_blocker_closed() -> dict:
    main = (ROOT / "apps/learnit-next/src/main.js").read_text(encoding="utf-8")
    render = (ROOT / "apps/learnit-next/src/ui/render.js").read_text(encoding="utf-8")
    surface = (ROOT / "apps/learnit-next/src/integration/atlas/surface.js").read_text(encoding="utf-8")
    presenters = (ROOT / "apps/learnit-next/src/ui/activity_presenters.js").read_text(encoding="utf-8")

    assert "presentation: projectActivityPresentation" in main
    assert "projectLearnerSession(await sessions.startCourse" in main
    assert "projectLearnerAnswer(await sessions.answer" in main

    start = render.index("function renderSessionSnapshot")
    end = render.index("function renderFeedback", start)
    served_slice = render[start:end]
    assert "renderServedActivityForm(" in served_slice
    assert "renderQcmForm(" not in served_slice
    assert "renderFillForm(" not in served_slice
    assert "readActivityResponse(form, presentation)" in render
    assert "result.scored === true" in render

    assert "ATLAS_SUPPORTED_ACTIVITY_TYPES = new Set(['qcm', 'fill'])" in surface
    assert "ATLAS_SUPPORTED_ACTIVITY_TYPES.has(activity.type)" in surface
    for family in FAMILIES:
        assert f"case '{family}'" in presenters, family

    return {
        "classicGenericPresenter": True,
        "learnerProjectionBoundary": True,
        "atlasExplicitQcmFillGate": True,
        "familiesInGenericPresenter": FAMILIES,
    }


def rewrite_package_revision(payload: dict, prefix: str) -> None:
    payload["packageRevisionId"] = prefix + payload["packageRevisionId"][8:]
    payload["packageRevisionDigest"] = ZERO_DIGEST


def valid_digest_hostile_payload(svg: str, prefix: str) -> dict:
    from authoring.v4 import validate_kit as v4

    payload = copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8")))
    payload["assets"][0]["data"] = svg
    rewrite_package_revision(payload, prefix)
    errors = v4.fill_new_digests(payload)
    assert errors == [], errors
    assert payload["packageRevisionDigest"] != ZERO_DIGEST
    return payload


def media_fail_closed_authoring() -> dict:
    cases = {
        "active": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<script>alert(1)</script><rect width="10" height="10"/></svg>',
            "30000000",
        ),
        "remote": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<image href="https://example.invalid/remote.png" width="10" height="10"/></svg>',
            "40000000",
        ),
    }
    results = {}
    with tempfile.TemporaryDirectory(prefix="job05-r1-media-") as tmp:
        for name, (svg, prefix) in cases.items():
            payload = valid_digest_hostile_payload(svg, prefix)
            path = Path(tmp) / f"{name}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            proc = command(
                sys.executable, "-B", "authoring/v4/validate_kit.py",
                str(path), "--format=json",
            )
            assert proc.returncode == 1, (name, proc.returncode, proc.stdout, proc.stderr)
            report = json.loads(proc.stdout)
            serialized = json.dumps(report, ensure_ascii=False)
            assert report["ok"] is False, report
            assert "digest differs" not in serialized.lower(), serialized
            assert "svg" in serialized.lower(), serialized
            results[name] = {
                "rejected": True,
                "digestAttributable": True,
                "packageRevisionDigest": payload["packageRevisionDigest"],
            }
    return results


def main() -> int:
    evidence = {
        "fixture": fixture_identity_and_validation(),
        "build": exact_build_identity(),
        "oldBlocker": old_blocker_closed(),
        "authoringMediaNegative": media_fail_closed_authoring(),
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    for marker in (
        "JOB05_R1_FROZEN_FIXTURE_IDENTITY=PASS",
        "JOB05_R1_CANONICAL_V4_FIXTURE=PASS",
        "JOB05_R1_BUILD_IDENTITY_EXACT_REPAIR=PASS",
        "JOB05_R1_OLD_BLOCKER_STATIC_CLOSED=PASS",
        "JOB05_R1_MEDIA_AUTHORING_FAIL_CLOSED=PASS",
    ):
        print(marker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
