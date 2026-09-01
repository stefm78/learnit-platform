#!/usr/bin/env python3
"""Trusted snapshot runner for the ATLAS real-source benchmark.

The source catalog and source-admission policy remain authoritative. This
runner performs the separate network/retrieval step, writes exact source bytes
outside Git, creates SourceAdmission records, and emits a path-free manifest.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.factory import factory_gate as factory
from authoring.factory import source_admission as admission

SNAPSHOT_SCHEMA = "learnit.atlas.source_snapshot_manifest.v1"
SNAPSHOT_PROFILE = "atlas.real-source-snapshot.v1"
PASS = "PASS_REAL_SOURCE_SNAPSHOT_V1"
HOLD = "HOLD_REAL_SOURCE_SNAPSHOT_V1"
USER_AGENT = "Learnit-Atlas-Source-Snapshot/1.0 (+https://github.com/stefm78/learnit-platform)"
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class SnapshotError(ValueError):
    pass


def safe_name(source_id: str) -> str:
    name = SAFE_NAME.sub("_", source_id).strip("._")
    return name or "source"


def extension_for(url: str, media_type: str | None) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix and len(suffix) <= 10:
        return suffix
    guessed = mimetypes.guess_extension((media_type or "").split(";", 1)[0].strip())
    return guessed or ".bin"


def fetch_url(url: str, timeout: int = 60) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if not isinstance(status, int) or status < 200 or status >= 300:
                raise SnapshotError(f"HTTP status {status} for {url}")
            data = response.read()
            media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            final_url = response.geturl()
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        raise SnapshotError(f"download failed for {url}: {exc}") from exc

    if not data:
        raise SnapshotError(f"empty response for {url}")

    expected_suffix = Path(urlparse(url).path).suffix.lower()
    if expected_suffix in {".pdf", ".zip"} and media_type in {"text/html", "application/xhtml+xml"}:
        raise SnapshotError(
            f"content-type mismatch for {url}: expected {expected_suffix}, got {media_type}"
        )
    return {
        "bytes": data,
        "mediaType": media_type or "application/octet-stream",
        "finalUrl": final_url,
        "etag": etag,
        "lastModified": last_modified,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(factory.canonical_json_bytes(value) + b"\n")


def snapshot_catalog(
    catalog_path: Path,
    output_dir: Path,
    snapshot_date: str,
    *,
    use_context: str | None = None,
    fetcher: Callable[[str], dict[str, Any]] = fetch_url,
) -> dict[str, Any]:
    catalog, catalog_sha = admission.load_catalog(catalog_path)
    context = use_context or catalog["defaultUseContext"]
    if context not in admission.USE_CONTEXTS:
        raise SnapshotError(f"unsupported use context {context!r}")
    if not isinstance(snapshot_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", snapshot_date):
        raise SnapshotError("snapshot_date must be YYYY-MM-DD")

    sources_dir = output_dir / "sources"
    admissions_dir = output_dir / "admissions"
    sources_dir.mkdir(parents=True, exist_ok=True)
    admissions_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    reasons: list[str] = []
    primary_content: dict[str, str] = {}

    for source in catalog["sources"]:
        source_id = source["sourceId"]
        supplied_version = snapshot_date if source["version"]["strategy"] == "caller" else None
        accepted = list(source["rights"]["conditions"])
        pre_verdict, pre_reasons, _ = admission.pre_ingestion_decision(
            source,
            context,
            set(accepted),
            supplied_version,
        )
        is_negative = source["benchmarkRole"] == "negative-control"

        if pre_verdict != admission.PASS:
            record = admission.build_admission(
                catalog,
                catalog_sha,
                source_id,
                context,
                None,
                accepted,
                supplied_version,
            )
            admission.verify_admission(record)
            write_json(admissions_dir / f"{safe_name(source_id)}.json", record)
            row = {
                "sourceId": source_id,
                "domain": source["domain"],
                "benchmarkRole": source["benchmarkRole"],
                "retrieval": "not-attempted",
                "mediaType": None,
                "bytes": None,
                "sha256": None,
                "admissionId": record["admissionId"],
                "admissionVerdict": record["decision"]["verdict"],
                "artifactFile": None,
            }
            rows.append(row)
            if not is_negative:
                reasons.append(
                    f"SOURCE_PRE_INGESTION_HOLD:{source_id}:{record['decision']['verdict']}"
                )
            continue

        if is_negative:
            reasons.append(f"NEGATIVE_CONTROL_UNEXPECTEDLY_ADMISSIBLE:{source_id}")
            rows.append({
                "sourceId": source_id,
                "domain": source["domain"],
                "benchmarkRole": source["benchmarkRole"],
                "retrieval": "not-attempted",
                "mediaType": None,
                "bytes": None,
                "sha256": None,
                "admissionId": None,
                "admissionVerdict": "ERROR_NEGATIVE_CONTROL_ADMISSIBLE",
                "artifactFile": None,
            })
            continue

        try:
            fetched = fetcher(source["sourceUrl"])
        except Exception as exc:
            rows.append({
                "sourceId": source_id,
                "domain": source["domain"],
                "benchmarkRole": source["benchmarkRole"],
                "retrieval": "failed",
                "mediaType": None,
                "bytes": None,
                "sha256": None,
                "admissionId": None,
                "admissionVerdict": None,
                "artifactFile": None,
            })
            reasons.append(f"SOURCE_RETRIEVAL_FAILED:{source_id}:{exc}")
            continue

        data = fetched.get("bytes")
        if not isinstance(data, (bytes, bytearray)) or not data:
            rows.append({
                "sourceId": source_id,
                "domain": source["domain"],
                "benchmarkRole": source["benchmarkRole"],
                "retrieval": "failed",
                "mediaType": None,
                "bytes": None,
                "sha256": None,
                "admissionId": None,
                "admissionVerdict": None,
                "artifactFile": None,
            })
            reasons.append(f"SOURCE_RETRIEVAL_INVALID_BYTES:{source_id}")
            continue

        media_type = str(fetched.get("mediaType") or "application/octet-stream")
        ext = extension_for(source["sourceUrl"], media_type)
        relative_file = f"sources/{safe_name(source_id)}{ext}"
        file_path = output_dir / relative_file
        file_path.write_bytes(bytes(data))

        record = admission.build_admission(
            catalog,
            catalog_sha,
            source_id,
            context,
            file_path,
            accepted,
            supplied_version,
        )
        admission.verify_admission(record)
        write_json(admissions_dir / f"{safe_name(source_id)}.json", record)

        content_sha = record["content"]["sha256"] if record["content"] else None
        if source["benchmarkRole"] == "primary" and content_sha:
            previous = primary_content.get(content_sha)
            if previous and previous != source_id:
                reasons.append(
                    f"DUPLICATE_PRIMARY_SOURCE_CONTENT:{previous}:{source_id}:{content_sha}"
                )
            primary_content[content_sha] = source_id

        rows.append({
            "sourceId": source_id,
            "domain": source["domain"],
            "benchmarkRole": source["benchmarkRole"],
            "retrieval": "downloaded",
            "mediaType": media_type,
            "bytes": record["content"]["bytes"] if record["content"] else None,
            "sha256": content_sha,
            "admissionId": record["admissionId"],
            "admissionVerdict": record["decision"]["verdict"],
            "artifactFile": relative_file,
        })

    primary_rows = [row for row in rows if row["benchmarkRole"] == "primary"]
    if {row["domain"] for row in primary_rows} != admission.REQUIRED_DOMAINS:
        reasons.append("PRIMARY_DOMAIN_COVERAGE_MISMATCH")
    for row in primary_rows:
        if row["retrieval"] != "downloaded":
            reasons.append(f"PRIMARY_SOURCE_NOT_DOWNLOADED:{row['sourceId']}")
        if row["admissionVerdict"] != admission.PASS:
            reasons.append(f"PRIMARY_SOURCE_NOT_ADMITTED:{row['sourceId']}")

    for row in rows:
        if row["benchmarkRole"] == "negative-control":
            if row["retrieval"] != "not-attempted":
                reasons.append(f"NEGATIVE_CONTROL_WAS_DOWNLOADED:{row['sourceId']}")
            if row["admissionVerdict"] not in {
                admission.HOLD_PERMISSION,
                admission.HOLD_PROHIBITED,
                admission.HOLD_UNKNOWN,
            }:
                reasons.append(f"NEGATIVE_CONTROL_NOT_BLOCKED:{row['sourceId']}")

    reasons = sorted(set(reasons))
    core = {
        "schema": SNAPSHOT_SCHEMA,
        "profile": SNAPSHOT_PROFILE,
        "catalogSha256": catalog_sha,
        "snapshotDate": snapshot_date,
        "useContext": context,
        "sources": rows,
        "verdict": PASS if not reasons else HOLD,
        "reasons": reasons,
    }
    manifest = {**core, "snapshotId": admission.digest(core)}
    write_json(output_dir / "source_snapshot_manifest.json", manifest)
    return manifest


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Snapshot admitted ATLAS benchmark sources")
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--snapshot-date", required=True)
    p.add_argument("--use-context")
    p.add_argument("--timeout", type=int, default=60)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        def network_fetch(url: str) -> dict[str, Any]:
            return fetch_url(url, timeout=args.timeout)

        manifest = snapshot_catalog(
            args.catalog,
            args.output,
            args.snapshot_date,
            use_context=args.use_context,
            fetcher=network_fetch,
        )
        sys.stdout.write(factory.canonical_json_bytes(manifest).decode("utf-8") + "\n")
        return 0 if manifest["verdict"] == PASS else 8
    except (SnapshotError, admission.SourceAdmissionError) as exc:
        sys.stdout.write(factory.canonical_json_bytes({
            "verdict": HOLD,
            "reasons": [f"SNAPSHOT_INPUT_ERROR:{exc}"],
        }).decode("utf-8") + "\n")
        return 8


if __name__ == "__main__":
    raise SystemExit(main())
