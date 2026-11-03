#!/usr/bin/env python3
"""Byte-bound, replayable V6 package assembly; NEVER grants Factory PASS.

Two separate commands are required:
  python -m authoring.factory.forward_v6 freeze --kit R1.json --brief BRIEF.json \
      --sources SOURCE_MANIFEST.json --manifest immutable.json
  python -m authoring.factory.forward_v6 assemble --kit R1.json --brief BRIEF.json \
      --sources SOURCE_MANIFEST.json --manifest immutable.json \
      --manifest-sha256 <freeze stdout SHA-256> --out candidate.json

Run `assemble` twice from the frozen manifest into independent output paths.
Only independently reviewed Factory evidence can later make a kit releasable.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = "learnit.atlas.forward_v6_build_manifest.v1"
ZERO_DIGEST = "sha256:" + "0" * 64
SHA = re.compile(r"[0-9a-f]{64}\Z")


class ForwardV6Error(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _unique_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in items:
        if key in result:
            raise ForwardV6Error("duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ForwardV6Error(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ForwardV6Error(f"JSON root must be an object: {path}")
    return value, raw


def require_uuid4(value: Any) -> None:
    try:
        parsed = uuid.UUID(value)
        if not isinstance(value, str) or str(parsed) != value or parsed.version != 4 or parsed.variant != uuid.RFC_4122:
            raise ValueError("not canonical RFC4122 UUID4")
    except (ValueError, AttributeError, TypeError) as exc:
        raise ForwardV6Error("invalid CSPRNG UUID4 in frozen manifest") from exc


def fingerprint(kit: dict[str, Any]) -> dict[str, int]:
    courses = kit.get("courses")
    assets = kit.get("assets")
    if not isinstance(courses, list) or not isinstance(assets, list):
        raise ForwardV6Error("source kit has invalid courses/assets")
    if any(not isinstance(c, dict) or not isinstance(c.get("objectives"), list) or not isinstance(c.get("activities"), list) for c in courses):
        raise ForwardV6Error("source kit has invalid module structure")
    return {
        "courses": len(courses),
        "objectives": sum(len(c["objectives"]) for c in courses),
        "activities": sum(len(c["activities"]) for c in courses),
        "assets": len(assets),
        "validationActivities": sum(a.get("assessmentRole") == "validation" for c in courses for a in c["activities"] if isinstance(a, dict)),
    }


def _known_ids(kit: Any) -> set[str]:
    seen: set[str] = set()
    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for key, item in v.items():
                if key.endswith("Id") and isinstance(item, str):
                    seen.add(item)
                walk(item)
        elif isinstance(v, list):
            for item in v:
                walk(item)
    walk(kit)
    return seen


def freeze(kit_path: Path, brief_path: Path, sources_path: Path) -> dict[str, Any]:
    kit, kit_raw = read_json(kit_path)
    brief, brief_raw = read_json(brief_path)
    sources, sources_raw = read_json(sources_path)
    if kit.get("contract") != "learnit.kit.v6" or sources.get("schema") != "learnit.atlas.v6_source_manifest.v1" or brief.get("schema") != "learnit.atlas.learner_brief.v1":
        raise ForwardV6Error("upstream contract/brief/source manifest identity mismatch")
    existing = _known_ids(kit)
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]  # OS CSPRNG; minted once, never on replay
    if ids[0] == ids[1] or any(x in existing for x in ids):
        raise ForwardV6Error("CSPRNG ID collision")
    for item in ids:
        require_uuid4(item)
    return {
        "schema": MANIFEST_SCHEMA,
        "sourceKitSha256": sha(kit_raw),
        "learnerBriefSha256": sha(brief_raw),
        "sourceManifestSha256": sha(sources_raw),
        "priorPackageLineageId": kit["packageLineageId"],
        "priorPackageRevisionId": kit["packageRevisionId"],
        "packageLineageId": ids[0],
        "packageRevisionId": ids[1],
        "structuralFingerprint": fingerprint(kit),
        "qualification": "CANDIDATE_ONLY_T2_REQUIRED",
    }


def assemble(kit_path: Path, brief_path: Path, sources_path: Path, manifest_path: Path, manifest_sha256: str) -> tuple[bytes, dict[str, Any]]:
    if not isinstance(manifest_sha256, str) or not SHA.fullmatch(manifest_sha256):
        raise ForwardV6Error("manifest SHA-256 must be an exact lowercase 64-digit digest")
    manifest, manifest_raw = read_json(manifest_path)
    if sha(manifest_raw) != manifest_sha256:
        raise ForwardV6Error("manifest exact-byte SHA-256 mismatch")
    required = {"schema", "sourceKitSha256", "learnerBriefSha256", "sourceManifestSha256", "priorPackageLineageId", "priorPackageRevisionId", "packageLineageId", "packageRevisionId", "structuralFingerprint", "qualification"}
    if set(manifest) != required or manifest["schema"] != MANIFEST_SCHEMA or manifest["qualification"] != "CANDIDATE_ONLY_T2_REQUIRED":
        raise ForwardV6Error("frozen manifest schema or scope mismatch")
    require_uuid4(manifest["packageLineageId"])
    require_uuid4(manifest["packageRevisionId"])
    if manifest["packageLineageId"] == manifest["packageRevisionId"]:
        raise ForwardV6Error("duplicate package UUID4")
    kit, kit_raw = read_json(kit_path)
    brief, brief_raw = read_json(brief_path)
    sources, sources_raw = read_json(sources_path)
    if sha(kit_raw) != manifest["sourceKitSha256"] or sha(brief_raw) != manifest["learnerBriefSha256"] or sha(sources_raw) != manifest["sourceManifestSha256"]:
        raise ForwardV6Error("frozen kit / brief / source manifest exact-byte drift")
    if kit.get("contract") != "learnit.kit.v6" or brief.get("schema") != "learnit.atlas.learner_brief.v1" or sources.get("schema") != "learnit.atlas.v6_source_manifest.v1":
        raise ForwardV6Error("upstream contract identity drift")
    if (kit.get("packageLineageId"), kit.get("packageRevisionId")) != (manifest["priorPackageLineageId"], manifest["priorPackageRevisionId"]):
        raise ForwardV6Error("unbound predecessor lineage/revision")
    if fingerprint(kit) != manifest["structuralFingerprint"]:
        raise ForwardV6Error("upstream module/activity counts drift")
    if manifest["packageLineageId"] in _known_ids(kit) or manifest["packageRevisionId"] in _known_ids(kit):
        raise ForwardV6Error("package UUID4 collides with nested or predecessor ID")
    successor = copy.deepcopy(kit)
    successor["packageLineageId"] = manifest["packageLineageId"]
    successor["packageRevisionId"] = manifest["packageRevisionId"]
    successor["packageRevisionDigest"] = ZERO_DIGEST
    # The checked-in adapter loads *exact pinned* historical V4/V5/V6 validators.
    from authoring.v6 import validator_runtime
    errors = validator_runtime.fill_new_digests(successor)
    if errors:
        raise ForwardV6Error("nested or package digest failure: " + "; ".join(errors))
    if successor["courses"] != kit["courses"] or successor["assets"] != kit["assets"]:
        raise ForwardV6Error("module/objective/activity/media drift")
    for key in kit:
        if key not in {"packageLineageId", "packageRevisionId", "packageRevisionDigest"} and successor[key] != kit[key]:
            raise ForwardV6Error("unexpected kit root change: " + key)
    if successor["packageRevisionDigest"] == kit["packageRevisionDigest"]:
        raise ForwardV6Error("package revision digest was not renewed")
    report = validator_runtime.validate_document(successor, "forward-v6-successor")
    if not report.ok:
        raise ForwardV6Error("pinned V6 canonical validation HOLD: " + "; ".join(report.errors))
    return canonical(successor), successor


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("freeze", "assemble"):
        q = sub.add_parser(name)
        for opt in ("kit", "brief", "sources"):
            q.add_argument("--" + opt, type=Path, required=True)
        q.add_argument("--manifest", type=Path, required=True)
        if name == "assemble":
            q.add_argument("--manifest-sha256", required=True)
            q.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        if a.command == "freeze":
            raw = canonical(freeze(a.kit, a.brief, a.sources))
            with a.manifest.open("xb") as out:
                out.write(raw)
            print(json.dumps({"status": "FROZEN_CANDIDATE_ONLY", "manifestSha256": sha(raw), "manifestBytes": len(raw)}))
        else:
            raw, successor = assemble(a.kit, a.brief, a.sources, a.manifest, a.manifest_sha256)
            with a.out.open("xb") as out:
                out.write(raw)
            print(json.dumps({"status": "UNQUALIFIED_CANDIDATE_T2_REQUIRED", "kitSha256": sha(raw), "kitBytes": len(raw), "packageRevisionDigest": successor["packageRevisionDigest"]}))
        return 0
    except (OSError, KeyError, TypeError, ForwardV6Error) as exc:
        p.exit(2, "HOLD_FORWARD_V6: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
