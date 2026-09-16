#!/usr/bin/env python3
"""Deterministic semantic validator for frozen ``learnit.kit.v4`` packages."""
from __future__ import annotations

import argparse
import copy
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoring.v2 import validate_kit as v2

SCHEMA_PATH = ROOT / "contracts/learnit-kit-v4.schema.json"
ZERO_DIGEST = v2.ZERO_DIGEST
EVALUATED_TYPES = {"qcm", "fill", "constructed", "matching", "order", "classify"}
NON_SCORED_TYPES = {"lesson", "flashcard"}
PLACEHOLDER = re.compile(
    r"^(?:todo|tbd|placeholder|lorem(?:\s+ipsum)?|à\s+compl[eé]ter|a\s+completer|n/?a)$",
    re.IGNORECASE,
)
REMOTE_PREFIX = re.compile(r"^(?:https?:|javascript:|file:|blob:|//)", re.IGNORECASE)
URL_CALL = re.compile(r"url\(\s*([^)]*?)\s*\)", re.IGNORECASE)
FORBIDDEN_SVG_TAGS = {"script", "foreignobject", "iframe", "object", "embed", "image", "use"}


class V4ValidationError(ValueError):
    """Input or authority failure for the v4 authoring validator."""


@dataclass
class Report:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    revisions: list[dict[str, Any]] = field(default_factory=list)
    ids: int = 0
    objective_refs: int = 0
    activities: Counter[str] = field(default_factory=Counter)
    assets: int = 0
    media_refs: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def load(path: Path) -> Any:
    return v2.load(path)


def digest(value: dict[str, Any], field_name: str) -> tuple[str, str]:
    return v2.digest(value, field_name)


def diagnostic(path: str, cause: str, value: Any) -> str:
    return v2.diagnostic(path, cause, value)


def _define(defs: dict[str, str], value: Any, path: str, errors: list[str]) -> None:
    v2.define(defs, value, path, errors)


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].lower()


def _placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(PLACEHOLDER.fullmatch(value.strip()))


def _svg_errors(data: str, path: str) -> list[str]:
    errors: list[str] = []
    stripped = data.strip()
    if "<!DOCTYPE" in stripped.upper() or "<!ENTITY" in stripped.upper():
        return [diagnostic(path, "SVG declarations/entities are forbidden", "declaration")]
    if not (stripped.startswith("<svg") or stripped.startswith("<?xml")):
        return [diagnostic(path, "SVG data must be inspectable inline XML", stripped[:80])]
    try:
        root = ET.fromstring(stripped)
    except ET.ParseError as exc:
        return [diagnostic(path, "malformed SVG", str(exc))]
    if _local_name(root.tag) != "svg":
        errors.append(diagnostic(path, "SVG root element must be <svg>", root.tag))
    for element in root.iter():
        tag = _local_name(element.tag)
        if tag in FORBIDDEN_SVG_TAGS:
            errors.append(diagnostic(path, f"unsafe SVG element <{tag}> is forbidden", tag))
        for raw_name, raw_value in element.attrib.items():
            name = _local_name(raw_name)
            value = str(raw_value).strip()
            lowered = value.lower()
            if name.startswith("on"):
                errors.append(diagnostic(path, f"SVG event attribute {name!r} is forbidden", value))
            if name == "style":
                errors.append(diagnostic(path, "SVG style attributes are forbidden by the fail-closed authoring profile", value))
            if name == "href":
                errors.append(diagnostic(path, "SVG href/xlink:href references are forbidden", value))
            if REMOTE_PREFIX.match(lowered):
                errors.append(diagnostic(path, "SVG external/active URI is forbidden", value))
            for match in URL_CALL.finditer(value):
                target = match.group(1).strip().strip("\"'")
                if not target.startswith("#"):
                    errors.append(diagnostic(path, "SVG url(...) must reference a local fragment only", target))
    return errors


def _check_media(document: dict[str, Any], defs: dict[str, str], report: Report) -> None:
    assets = document.get("assets", [])
    asset_ids: set[str] = set()
    used: Counter[str] = Counter()
    if isinstance(assets, list):
        for index, asset in enumerate(assets):
            if not isinstance(asset, dict):
                continue
            ap = f"$.assets[{index}]"
            aid = asset.get("assetId")
            _define(defs, aid, ap + ".assetId", report.errors)
            if isinstance(aid, str):
                asset_ids.add(aid)
            report.assets += 1
            data = asset.get("data")
            if isinstance(data, str):
                stripped = data.strip()
                if REMOTE_PREFIX.match(stripped):
                    report.errors.append(diagnostic(ap + ".data", "remote/active media locations are forbidden; assets must be embedded", stripped[:120]))
                if asset.get("format") == "svg":
                    report.errors.extend(_svg_errors(data, ap + ".data"))
            if _placeholder(asset.get("alt")):
                report.errors.append(diagnostic(ap + ".alt", "placeholder alt text is not learner-safe authoring", asset.get("alt")))

    for ci, course in enumerate(document.get("courses", [])):
        if not isinstance(course, dict):
            continue
        for ai, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict):
                continue
            media = activity.get("media", [])
            if not isinstance(media, list):
                continue
            for mi, ref in enumerate(media):
                if not isinstance(ref, dict):
                    continue
                rp = f"$.courses[{ci}].activities[{ai}].media[{mi}].assetId"
                aid = ref.get("assetId")
                report.media_refs += 1
                if aid not in asset_ids:
                    report.errors.append(diagnostic(rp, "media reference does not resolve to a package asset", aid))
                elif isinstance(aid, str):
                    used[aid] += 1
    for index, asset in enumerate(assets if isinstance(assets, list) else []):
        if isinstance(asset, dict) and isinstance(asset.get("assetId"), str) and used[asset["assetId"]] == 0:
            report.warnings.append(diagnostic(f"$.assets[{index}].assetId", "unused package media should be removed", asset["assetId"]))


def _check_role_phase(activity: dict[str, Any], path: str, report: Report) -> None:
    activity_type = activity.get("type")
    phase = activity.get("learningPhase")
    role = activity.get("assessmentRole")
    if activity_type in NON_SCORED_TYPES:
        if role is not None:
            report.errors.append(diagnostic(path + ".assessmentRole", f"{activity_type} is non-scored and cannot have an assessment role", role))
        if phase in {"diagnostic", "validation"}:
            report.errors.append(diagnostic(path + ".learningPhase", f"{activity_type} is exposure/activation and cannot provide diagnostic or validation evidence", phase))
        return
    if activity_type not in EVALUATED_TYPES:
        return
    if (phase == "validation") != (role == "validation"):
        report.errors.append(diagnostic(path, "validation learningPhase and assessmentRole must match", {"learningPhase": phase, "assessmentRole": role}))
    if (phase == "diagnostic") != (role == "diagnostic"):
        report.errors.append(diagnostic(path, "diagnostic learningPhase and assessmentRole must match", {"learningPhase": phase, "assessmentRole": role}))


def _check_qcm(activity: dict[str, Any], path: str, defs: dict[str, str], report: Report) -> None:
    choices: set[str] = set()
    for index, choice in enumerate(activity.get("choices", [])):
        if not isinstance(choice, dict):
            continue
        cid = choice.get("choiceId")
        cp = f"{path}.choices[{index}].choiceId"
        _define(defs, cid, cp, report.errors)
        if isinstance(cid, str):
            if cid in choices:
                report.errors.append(diagnostic(cp, "duplicate choiceId in activity", cid))
            choices.add(cid)
    if activity.get("correctChoiceId") not in choices:
        report.errors.append(diagnostic(path + ".correctChoiceId", "does not reference a declared choice", activity.get("correctChoiceId")))


def _check_fill(activity: dict[str, Any], path: str, defs: dict[str, str], report: Report) -> None:
    slots: list[str] = []
    for si, segment in enumerate(activity.get("segments", [])):
        if isinstance(segment, dict) and "slotId" in segment:
            sid = segment.get("slotId")
            _define(defs, sid, f"{path}.segments[{si}].slotId", report.errors)
            if isinstance(sid, str):
                slots.append(sid)
    if len(slots) != len(set(slots)):
        report.errors.append(diagnostic(path + ".segments", "duplicate slotId", slots))
    tokens: set[str] = set()
    maxima: dict[str, int] = {}
    for ti, token in enumerate(activity.get("tokens", [])):
        if not isinstance(token, dict):
            continue
        tid = token.get("tokenId")
        _define(defs, tid, f"{path}.tokens[{ti}].tokenId", report.errors)
        if isinstance(tid, str):
            if tid in tokens:
                report.errors.append(diagnostic(f"{path}.tokens[{ti}].tokenId", "duplicate tokenId in activity", tid))
            tokens.add(tid)
            if isinstance(token.get("maxUses"), int):
                maxima[tid] = token["maxUses"]
    answered: set[str] = set()
    uses: Counter[str] = Counter()
    for ai, answer in enumerate(activity.get("answers", [])):
        if not isinstance(answer, dict):
            continue
        sid, tid = answer.get("slotId"), answer.get("tokenId")
        ap = f"{path}.answers[{ai}]"
        if sid not in slots:
            report.errors.append(diagnostic(ap + ".slotId", "does not reference a declared slot", sid))
        if sid in answered:
            report.errors.append(diagnostic(ap + ".slotId", "duplicate answer for slot", sid))
        if isinstance(sid, str):
            answered.add(sid)
        if tid not in tokens:
            report.errors.append(diagnostic(ap + ".tokenId", "does not reference a declared token", tid))
        if isinstance(tid, str):
            uses[tid] += 1
    missing = sorted(set(slots) - answered)
    if missing:
        report.errors.append(diagnostic(path + ".answers", "slots without answers", missing))
    for tid, count in uses.items():
        if tid in maxima and count > maxima[tid]:
            report.errors.append(diagnostic(path + ".answers", f"token use count exceeds maxUses={maxima[tid]}", {"tokenId": tid, "uses": count}))


def canonical_constructed_text(value: str) -> str:
    normalized = v2.normalize(value)
    if not isinstance(normalized, str):
        return ""
    return " ".join(normalized.strip().split())


def _check_constructed(activity: dict[str, Any], path: str, report: Report) -> None:
    seen: set[str] = set()
    for index, response in enumerate(activity.get("acceptedResponses", [])):
        if not isinstance(response, str):
            continue
        normalized = canonical_constructed_text(response)
        rp = f"{path}.acceptedResponses[{index}]"
        if not normalized:
            report.errors.append(diagnostic(rp, "accepted response is empty under canonical-text-match-v1 normalization", response))
        elif normalized in seen:
            report.errors.append(diagnostic(rp, "duplicate accepted response under canonical-text-match-v1 normalization", normalized))
        seen.add(normalized)


def _unique_items(items: Any, path: str, defs: dict[str, str], report: Report) -> tuple[list[str], set[str]]:
    ids: list[str] = []
    local: set[str] = set()
    for index, item in enumerate(items if isinstance(items, list) else []):
        if not isinstance(item, dict):
            continue
        iid = item.get("itemId")
        ip = f"{path}[{index}].itemId"
        _define(defs, iid, ip, report.errors)
        if isinstance(iid, str):
            if iid in local:
                report.errors.append(diagnostic(ip, "duplicate itemId in activity collection", iid))
            ids.append(iid)
            local.add(iid)
    return ids, local


def _check_matching(activity: dict[str, Any], path: str, defs: dict[str, str], report: Report) -> None:
    left_list, left = _unique_items(activity.get("leftItems"), path + ".leftItems", defs, report)
    right_list, right = _unique_items(activity.get("rightItems"), path + ".rightItems", defs, report)
    left_used: list[str] = []
    right_used: list[str] = []
    for index, match in enumerate(activity.get("matches", [])):
        if not isinstance(match, dict):
            continue
        lp, rp = match.get("leftItemId"), match.get("rightItemId")
        mp = f"{path}.matches[{index}]"
        if lp not in left:
            report.errors.append(diagnostic(mp + ".leftItemId", "unknown matching left item", lp))
        if rp not in right:
            report.errors.append(diagnostic(mp + ".rightItemId", "unknown matching right item", rp))
        if isinstance(lp, str):
            left_used.append(lp)
        if isinstance(rp, str):
            right_used.append(rp)
    if len(left_list) != len(right_list):
        report.errors.append(diagnostic(path, "matching must have equally sized left/right sets for a complete one-to-one solution", {"left": len(left_list), "right": len(right_list)}))
    if Counter(left_used) != Counter({item: 1 for item in left_list}):
        report.errors.append(diagnostic(path + ".matches", "every left item must participate exactly once", left_used))
    if Counter(right_used) != Counter({item: 1 for item in right_list}):
        report.errors.append(diagnostic(path + ".matches", "every right item must participate exactly once", right_used))


def _check_order(activity: dict[str, Any], path: str, defs: dict[str, str], report: Report) -> None:
    item_order, item_ids = _unique_items(activity.get("items"), path + ".items", defs, report)
    correct = activity.get("correctOrder", [])
    if isinstance(correct, list):
        if len(correct) != len(item_order) or set(correct) != item_ids:
            report.errors.append(diagnostic(path + ".correctOrder", "correctOrder must contain every authored item exactly once", correct))
        if item_order == correct:
            report.errors.append(diagnostic(path + ".items", "authored initial item order exposes correctOrder", item_order))


def _check_classify(activity: dict[str, Any], path: str, defs: dict[str, str], report: Report) -> None:
    buckets: set[str] = set()
    for index, bucket in enumerate(activity.get("buckets", [])):
        if not isinstance(bucket, dict):
            continue
        bid = bucket.get("bucketId")
        bp = f"{path}.buckets[{index}].bucketId"
        _define(defs, bid, bp, report.errors)
        if isinstance(bid, str):
            if bid in buckets:
                report.errors.append(diagnostic(bp, "duplicate bucketId in classify activity", bid))
            buckets.add(bid)
    item_list, items = _unique_items(activity.get("items"), path + ".items", defs, report)
    assigned: list[str] = []
    for index, assignment in enumerate(activity.get("assignments", [])):
        if not isinstance(assignment, dict):
            continue
        iid, bid = assignment.get("itemId"), assignment.get("bucketId")
        ap = f"{path}.assignments[{index}]"
        if iid not in items:
            report.errors.append(diagnostic(ap + ".itemId", "unknown classify item", iid))
        if bid not in buckets:
            report.errors.append(diagnostic(ap + ".bucketId", "unknown classify bucket", bid))
        if isinstance(iid, str):
            assigned.append(iid)
    counts = Counter(assigned)
    if set(counts) != set(item_list):
        report.errors.append(diagnostic(path + ".assignments", "classify assignments must cover every item", sorted(counts)))
    duplicates = sorted(item for item, count in counts.items() if count != 1)
    if duplicates:
        report.errors.append(diagnostic(path + ".assignments", "Student V0.1 classify is single-label: every item must be assigned exactly once", duplicates))


def _check_lesson(activity: dict[str, Any], path: str, report: Report) -> None:
    body = activity.get("body")
    if isinstance(body, str):
        words = re.findall(r"\w+", body, flags=re.UNICODE)
        if len(body.strip()) < 40 or len(words) < 6:
            report.errors.append(diagnostic(path + ".body", "lesson body is too small to be substantive learner-facing exposition", body))
        if _placeholder(body):
            report.errors.append(diagnostic(path + ".body", "placeholder lesson content is forbidden", body))
    for index, point in enumerate(activity.get("keyPoints", [])):
        if _placeholder(point):
            report.errors.append(diagnostic(f"{path}.keyPoints[{index}]", "placeholder key point is forbidden", point))
    if _placeholder(activity.get("contextNote")):
        report.errors.append(diagnostic(path + ".contextNote", "placeholder context note is forbidden", activity.get("contextNote")))


def _check_flashcard(activity: dict[str, Any], path: str, report: Report) -> None:
    for field_name in ("front", "back", "explanation"):
        if _placeholder(activity.get(field_name)):
            report.errors.append(diagnostic(path + "." + field_name, "placeholder flashcard content is forbidden", activity.get(field_name)))


def semantic_checks(document: dict[str, Any], report: Report) -> None:
    defs: dict[str, str] = {}
    _define(defs, document.get("packageLineageId"), "$.packageLineageId", report.errors)
    _define(defs, document.get("packageRevisionId"), "$.packageRevisionId", report.errors)
    courses = document.get("courses", [])
    if not isinstance(courses, list):
        return
    for ci, course in enumerate(courses):
        if not isinstance(course, dict):
            continue
        cp = f"$.courses[{ci}]"
        _define(defs, course.get("courseLineageId"), cp + ".courseLineageId", report.errors)
        _define(defs, course.get("courseRevisionId"), cp + ".courseRevisionId", report.errors)
        objective_ids: set[str] = set()
        objective_uses: Counter[str] = Counter()
        for oi, objective in enumerate(course.get("objectives", [])):
            if not isinstance(objective, dict):
                continue
            oid = objective.get("objectiveId")
            _define(defs, oid, f"{cp}.objectives[{oi}].objectiveId", report.errors)
            if isinstance(oid, str):
                objective_ids.add(oid)
        for ai, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict):
                continue
            ap = f"{cp}.activities[{ai}]"
            activity_type = activity.get("type")
            if isinstance(activity_type, str):
                report.activities[activity_type] += 1
            _define(defs, activity.get("activityLineageId"), ap + ".activityLineageId", report.errors)
            _define(defs, activity.get("activityRevisionId"), ap + ".activityRevisionId", report.errors)
            for ri, oid in enumerate(activity.get("objectiveIds", [])):
                report.objective_refs += 1
                if isinstance(oid, str):
                    objective_uses[oid] += 1
                if oid not in objective_ids:
                    report.errors.append(diagnostic(f"{ap}.objectiveIds[{ri}]", "missing objective reference", oid))
            _check_role_phase(activity, ap, report)
            if activity_type == "qcm":
                _check_qcm(activity, ap, defs, report)
            elif activity_type == "fill":
                _check_fill(activity, ap, defs, report)
            elif activity_type == "constructed":
                _check_constructed(activity, ap, report)
            elif activity_type == "lesson":
                _check_lesson(activity, ap, report)
            elif activity_type == "flashcard":
                _check_flashcard(activity, ap, report)
            elif activity_type == "matching":
                _check_matching(activity, ap, defs, report)
            elif activity_type == "order":
                _check_order(activity, ap, defs, report)
            elif activity_type == "classify":
                _check_classify(activity, ap, defs, report)
        for oid in objective_ids:
            if objective_uses[oid] == 0:
                report.errors.append(diagnostic(cp + ".objectives", "objective is not referenced", oid))
    _check_media(document, defs, report)
    report.ids = len(defs)


def add_digest_records(document: dict[str, Any], report: Report) -> None:
    for ci, course in enumerate(document.get("courses", [])):
        if not isinstance(course, dict):
            continue
        for ai, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict):
                continue
            path = f"$.courses[{ci}].activities[{ai}]"
            calculated, canonical = digest(activity, "activityRevisionDigest")
            declared = activity.get("activityRevisionDigest")
            report.revisions.append({"level": "activity", "path": path, "revisionId": activity.get("activityRevisionId"), "declared": declared, "calculated": calculated, "canonical": canonical})
            if declared != calculated:
                report.errors.append(diagnostic(path + ".activityRevisionDigest", "declared digest differs from calculated digest", {"declared": declared, "calculated": calculated}))
        path = f"$.courses[{ci}]"
        calculated, canonical = digest(course, "courseRevisionDigest")
        declared = course.get("courseRevisionDigest")
        report.revisions.append({"level": "course", "path": path, "revisionId": course.get("courseRevisionId"), "declared": declared, "calculated": calculated, "canonical": canonical})
        if declared != calculated:
            report.errors.append(diagnostic(path + ".courseRevisionDigest", "declared digest differs from calculated digest", {"declared": declared, "calculated": calculated}))
    calculated, canonical = digest(document, "packageRevisionDigest")
    declared = document.get("packageRevisionDigest")
    report.revisions.append({"level": "package", "path": "$", "revisionId": document.get("packageRevisionId"), "declared": declared, "calculated": calculated, "canonical": canonical})
    if declared != calculated:
        report.errors.append(diagnostic("$.packageRevisionDigest", "declared digest differs from calculated digest", {"declared": declared, "calculated": calculated}))


def validate(path: Path, document: dict[str, Any], schema: dict[str, Any]) -> Report:
    report = Report(path)
    report.errors.extend(v2.schema_errors(document, schema))
    if isinstance(document, dict):
        semantic_checks(document, report)
        add_digest_records(document, report)
    return report


def fill_new_digests(document: dict[str, Any]) -> list[str]:
    return v2.fill_new_digests(document)


def cross_file_errors(reports: list[Report]) -> list[str]:
    return v2.cross_file_errors(reports)  # type: ignore[arg-type]


def render_json(reports: list[Report], cross: list[str], show: bool) -> str:
    files: list[dict[str, Any]] = []
    for report in reports:
        revisions = []
        for record in report.revisions:
            item = {key: value for key, value in record.items() if key != "canonical"}
            if show:
                item["canonicalJson"] = record["canonical"]
            revisions.append(item)
        files.append({
            "path": str(report.path),
            "ok": report.ok,
            "errors": report.errors,
            "warnings": report.warnings,
            "idsDefined": report.ids,
            "objectiveReferences": report.objective_refs,
            "activities": dict(sorted(report.activities.items())),
            "assets": report.assets,
            "mediaReferences": report.media_refs,
            "revisions": revisions,
        })
    import json
    return json.dumps({"ok": all(report.ok for report in reports) and not cross, "crossFileErrors": cross, "files": files}, ensure_ascii=False, indent=2)


def render_human(reports: list[Report], cross: list[str], show: bool) -> str:
    lines: list[str] = []
    for report in reports:
        lines += [
            f"FILE {report.path}",
            f"  status: {'PASS' if report.ok else 'FAIL'}",
            f"  semantic IDs defined: {report.ids}",
            f"  objective references checked: {report.objective_refs}",
            f"  activities: {dict(sorted(report.activities.items()))}",
            f"  assets: {report.assets}, media refs: {report.media_refs}",
        ]
        for record in report.revisions:
            lines.append(f"  {record['level']} {record['path']} revision={record['revisionId']} digest={record['calculated']}")
            if show:
                lines.append(f"    canonical={record['canonical']}")
        lines += [f"  WARNING: {warning}" for warning in report.warnings]
        lines += [f"  ERROR: {error}" for error in report.errors]
    lines += [f"CROSS-FILE ERROR: {error}" for error in cross]
    lines.append(f"OVERALL {'PASS' if all(report.ok for report in reports) and not cross else 'FAIL'}")
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    argp = argparse.ArgumentParser(description="Validate frozen learnit.kit.v4 packages.")
    argp.add_argument("kits", nargs="+", type=Path)
    argp.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    argp.add_argument("--write-digests", action="store_true")
    argp.add_argument("--show-canonical", action="store_true")
    argp.add_argument("--format", choices=("human", "json"), default="human")
    return argp


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        schema = load(args.schema)
        if not isinstance(schema, dict):
            raise V4ValidationError("schema root must be an object")
        documents: list[tuple[Path, dict[str, Any]]] = []
        write_errors: list[str] = []
        for path in args.kits:
            document = load(path)
            if not isinstance(document, dict):
                raise V4ValidationError(f"{path}: kit root must be a JSON object")
            if args.write_digests:
                document = copy.deepcopy(document)
                write_errors += [f"{path}: {error}" for error in fill_new_digests(document)]
            documents.append((path, document))
        reports = [validate(path, document, schema) for path, document in documents]
        cross = cross_file_errors(reports) + write_errors
        if args.write_digests and all(report.ok for report in reports) and not cross:
            import json
            for path, document in documents:
                path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(render_json(reports, cross, args.show_canonical) if args.format == "json" else render_human(reports, cross, args.show_canonical))
        return 0 if all(report.ok for report in reports) and not cross else 1
    except (v2.ToolError, V4ValidationError) as exc:
        print(f"TOOL ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
