#!/usr/bin/env python3
"""Validate learnit.kit.v2 structure, semantics, identities and revision digests."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover
    Draft202012Validator = None  # type: ignore[assignment]
    JSONSCHEMA_ERROR = exc
else:
    JSONSCHEMA_ERROR = None

ZERO_DIGEST = "sha256:" + "0" * 64


class ToolError(ValueError):
    pass


@dataclass
class Report:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    revisions: list[dict[str, Any]] = field(default_factory=list)
    ids: int = 0
    objective_refs: int = 0
    qcm: int = 0
    fill: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ToolError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except FileNotFoundError as exc:
        raise ToolError(f"file not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ToolError(f"file is not UTF-8: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ToolError(f"invalid JSON line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc


def normalize(value: Any, path: str = "$") -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise ToolError(f"{path}: floats are outside the canonical JSON profile")
    if isinstance(value, list):
        return [normalize(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ToolError(f"{path}: non-string object key")
            nkey = unicodedata.normalize("NFC", key)
            if nkey in result:
                raise ToolError(f"{path}: keys collide after NFC normalization: {nkey!r}")
            result[nkey] = normalize(item, f"{path}.{nkey}")
        return result
    raise ToolError(f"{path}: unsupported canonical value {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        normalize(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )


def digest(value: dict[str, Any], field_name: str) -> tuple[str, str]:
    payload = copy.deepcopy(value)
    payload.pop(field_name, None)
    text = canonical_json(payload)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(), text


def json_path(parts: Any) -> str:
    value = "$"
    for part in parts:
        value += f"[{part}]" if isinstance(part, int) else f".{part}"
    return value


def schema_errors(document: Any, schema: dict[str, Any]) -> list[str]:
    if Draft202012Validator is None:
        raise ToolError(f"jsonschema>=4.18 is required: {JSONSCHEMA_ERROR}")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    return [
        f"schema {json_path(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    ]


def define(defs: dict[str, str], value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        return
    if value in defs:
        errors.append(f"duplicate canonical ID {value}: {defs[value]} and {location}")
    else:
        defs[value] = location


def semantic_checks(document: dict[str, Any], report: Report, foundation: bool) -> None:
    defs: dict[str, str] = {}
    define(defs, document.get("packageLineageId"), "$.packageLineageId", report.errors)
    define(defs, document.get("packageRevisionId"), "$.packageRevisionId", report.errors)
    courses = document.get("courses", [])
    if not isinstance(courses, list):
        return

    for ci, course in enumerate(courses):
        if not isinstance(course, dict):
            continue
        cp = f"$.courses[{ci}]"
        define(defs, course.get("courseLineageId"), cp + ".courseLineageId", report.errors)
        define(defs, course.get("courseRevisionId"), cp + ".courseRevisionId", report.errors)
        objectives = course.get("objectives", [])
        objective_ids: set[str] = set()
        uses: Counter[str] = Counter()
        if isinstance(objectives, list):
            for oi, objective in enumerate(objectives):
                if not isinstance(objective, dict):
                    continue
                oid = objective.get("objectiveId")
                define(defs, oid, f"{cp}.objectives[{oi}].objectiveId", report.errors)
                if isinstance(oid, str):
                    objective_ids.add(oid)

        activities = course.get("activities", [])
        if not isinstance(activities, list):
            continue
        phases: list[str] = []
        roles: list[str] = []
        for ai, activity in enumerate(activities):
            if not isinstance(activity, dict):
                continue
            ap = f"{cp}.activities[{ai}]"
            define(defs, activity.get("activityLineageId"), ap + ".activityLineageId", report.errors)
            define(defs, activity.get("activityRevisionId"), ap + ".activityRevisionId", report.errors)
            phase, role = activity.get("learningPhase"), activity.get("assessmentRole")
            if isinstance(phase, str): phases.append(phase)
            if isinstance(role, str): roles.append(role)
            if (phase == "validation") != (role == "validation"):
                report.errors.append(f"{ap}: validation learningPhase and assessmentRole must match")
            explanation = activity.get("explanation")
            if isinstance(explanation, str) and len(explanation.strip()) < 35:
                report.warnings.append(f"{ap}.explanation is unusually short")

            refs = activity.get("objectiveIds", [])
            if isinstance(refs, list):
                for ri, oid in enumerate(refs):
                    report.objective_refs += 1
                    if isinstance(oid, str): uses[oid] += 1
                    if oid not in objective_ids:
                        report.errors.append(f"{ap}.objectiveIds[{ri}]: missing objective reference {oid!r}")

            if activity.get("type") == "qcm":
                report.qcm += 1
                choice_ids: set[str] = set()
                for xi, choice in enumerate(activity.get("choices", [])):
                    if not isinstance(choice, dict):
                        continue
                    cid = choice.get("choiceId")
                    loc = f"{ap}.choices[{xi}].choiceId"
                    define(defs, cid, loc, report.errors)
                    if isinstance(cid, str):
                        if cid in choice_ids: report.errors.append(f"{loc}: duplicate choiceId")
                        choice_ids.add(cid)
                correct = activity.get("correctChoiceId")
                if correct not in choice_ids:
                    report.errors.append(f"{ap}.correctChoiceId: {correct!r} does not reference a declared choice")

            elif activity.get("type") == "fill":
                report.fill += 1
                slots: list[str] = []
                previous_slot = False
                for si, segment in enumerate(activity.get("segments", [])):
                    is_slot = isinstance(segment, dict) and "slotId" in segment
                    if is_slot:
                        sid = segment.get("slotId")
                        define(defs, sid, f"{ap}.segments[{si}].slotId", report.errors)
                        if isinstance(sid, str): slots.append(sid)
                        if previous_slot: report.warnings.append(f"{ap}: adjacent fill slots may be ambiguous")
                    previous_slot = is_slot
                if len(slots) != len(set(slots)): report.errors.append(f"{ap}: duplicate slotId in segments")

                token_ids: set[str] = set()
                maxima: dict[str, int] = {}
                for ti, token in enumerate(activity.get("tokens", [])):
                    if not isinstance(token, dict):
                        continue
                    tid = token.get("tokenId")
                    loc = f"{ap}.tokens[{ti}].tokenId"
                    define(defs, tid, loc, report.errors)
                    if isinstance(tid, str):
                        if tid in token_ids: report.errors.append(f"{loc}: duplicate tokenId")
                        token_ids.add(tid)
                        if isinstance(token.get("maxUses"), int): maxima[tid] = token["maxUses"]

                answered: set[str] = set()
                token_uses: Counter[str] = Counter()
                for ni, answer in enumerate(activity.get("answers", [])):
                    if not isinstance(answer, dict):
                        continue
                    sid, tid = answer.get("slotId"), answer.get("tokenId")
                    loc = f"{ap}.answers[{ni}]"
                    if sid not in slots: report.errors.append(f"{loc}.slotId: {sid!r} does not reference a declared slot")
                    if sid in answered: report.errors.append(f"{loc}.slotId: duplicate answer for slot {sid!r}")
                    if isinstance(sid, str): answered.add(sid)
                    if tid not in token_ids: report.errors.append(f"{loc}.tokenId: {tid!r} does not reference a declared token")
                    if isinstance(tid, str): token_uses[tid] += 1
                missing = set(slots) - answered
                if missing: report.errors.append(f"{ap}: slots without answers: {', '.join(sorted(missing))}")
                for tid, count in token_uses.items():
                    if tid in maxima and count > maxima[tid]:
                        report.errors.append(f"{ap}: token {tid} used {count} times, exceeding maxUses={maxima[tid]}")

        for oid in objective_ids:
            if uses[oid] == 0: report.errors.append(f"{cp}: objective {oid} is not referenced")
        if foundation:
            qcms = sum(isinstance(a, dict) and a.get("type") == "qcm" for a in activities)
            fills = sum(isinstance(a, dict) and a.get("type") == "fill" for a in activities)
            if len(objectives) < 2: report.errors.append(f"{cp}: foundation profile requires 2 objectives")
            if len(activities) < 6: report.errors.append(f"{cp}: foundation profile requires 6 activities")
            if qcms < 3: report.errors.append(f"{cp}: foundation profile requires 3 QCM")
            if fills < 2: report.errors.append(f"{cp}: foundation profile requires 2 fill")
            if not any(p in {"application", "transfer"} for p in phases):
                report.errors.append(f"{cp}: foundation profile requires application or transfer")
            if "validation" not in phases or "validation" not in roles:
                report.errors.append(f"{cp}: foundation profile requires validation")
    report.ids = len(defs)


def add_digest_records(document: dict[str, Any], report: Report) -> None:
    for ci, course in enumerate(document.get("courses", [])):
        if not isinstance(course, dict): continue
        for ai, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict): continue
            path = f"$.courses[{ci}].activities[{ai}]"
            calculated, text = digest(activity, "activityRevisionDigest")
            declared = activity.get("activityRevisionDigest")
            report.revisions.append({"level":"activity","path":path,"revisionId":activity.get("activityRevisionId"),"declared":declared,"calculated":calculated,"bytes":len(text.encode()),"canonical":text})
            if declared != calculated: report.errors.append(f"{path}.activityRevisionDigest: declared {declared!r}, calculated {calculated}")
        path = f"$.courses[{ci}]"
        calculated, text = digest(course, "courseRevisionDigest")
        declared = course.get("courseRevisionDigest")
        report.revisions.append({"level":"course","path":path,"revisionId":course.get("courseRevisionId"),"declared":declared,"calculated":calculated,"bytes":len(text.encode()),"canonical":text})
        if declared != calculated: report.errors.append(f"{path}.courseRevisionDigest: declared {declared!r}, calculated {calculated}")
    calculated, text = digest(document, "packageRevisionDigest")
    declared = document.get("packageRevisionDigest")
    report.revisions.append({"level":"package","path":"$","revisionId":document.get("packageRevisionId"),"declared":declared,"calculated":calculated,"bytes":len(text.encode()),"canonical":text})
    if declared != calculated: report.errors.append(f"$.packageRevisionDigest: declared {declared!r}, calculated {calculated}")


def validate(path: Path, document: dict[str, Any], schema: dict[str, Any], foundation: bool) -> Report:
    report = Report(path)
    report.errors.extend(schema_errors(document, schema))
    semantic_checks(document, report, foundation)
    add_digest_records(document, report)
    return report


def fill_new_digests(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for ci, course in enumerate(document.get("courses", [])):
        if not isinstance(course, dict): continue
        for ai, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict): continue
            calculated, _ = digest(activity, "activityRevisionDigest")
            current = activity.get("activityRevisionDigest")
            if current in (None, "", ZERO_DIGEST): activity["activityRevisionDigest"] = calculated
            elif current != calculated: errors.append(f"$.courses[{ci}].activities[{ai}]: non-zero digest mismatch; allocate a new activityRevisionId and reset its digest")
        calculated, _ = digest(course, "courseRevisionDigest")
        current = course.get("courseRevisionDigest")
        if current in (None, "", ZERO_DIGEST): course["courseRevisionDigest"] = calculated
        elif current != calculated: errors.append(f"$.courses[{ci}]: non-zero digest mismatch; allocate a new courseRevisionId and reset its digest")
    calculated, _ = digest(document, "packageRevisionDigest")
    current = document.get("packageRevisionDigest")
    if current in (None, "", ZERO_DIGEST): document["packageRevisionDigest"] = calculated
    elif current != calculated: errors.append("$: non-zero digest mismatch; allocate a new packageRevisionId and reset its digest")
    return errors


def cross_file_errors(reports: list[Report]) -> list[str]:
    seen: dict[str, tuple[str, str, str, str]] = {}
    errors: list[str] = []
    for report in reports:
        for record in report.revisions:
            rid = record.get("revisionId")
            if not isinstance(rid, str): continue
            signature = (record["calculated"], str(record["declared"]), record["canonical"])
            location = f"{report.path}:{record['path']}"
            if rid in seen and seen[rid][:3] != signature:
                errors.append(f"revisionId {rid} is associated with different content or digest at {seen[rid][3]} and {location}")
            else:
                seen[rid] = (*signature, location)
    return errors


def render_human(reports: list[Report], cross: list[str], show: bool) -> str:
    lines: list[str] = []
    for report in reports:
        lines += [f"FILE {report.path}", f"  status: {'PASS' if report.ok else 'FAIL'}", f"  semantic IDs defined: {report.ids}", f"  objective references checked: {report.objective_refs}", f"  activities: qcm={report.qcm}, fill={report.fill}"]
        for record in report.revisions:
            lines.append(f"  {record['level']} {record['path']} revision={record['revisionId']} bytes={record['bytes']} digest={record['calculated']}")
            if show: lines.append(f"    canonical={record['canonical']}")
        lines += [f"  WARNING: {warning}" for warning in report.warnings]
        lines += [f"  ERROR: {error}" for error in report.errors]
    lines += [f"CROSS-FILE ERROR: {error}" for error in cross]
    lines.append(f"OVERALL {'PASS' if all(r.ok for r in reports) and not cross else 'FAIL'}")
    return "\n".join(lines)


def render_json(reports: list[Report], cross: list[str], show: bool) -> str:
    files = []
    for report in reports:
        revisions = []
        for record in report.revisions:
            item = {k:v for k,v in record.items() if k != "canonical"}
            if show: item["canonicalJson"] = record["canonical"]
            revisions.append(item)
        files.append({"path":str(report.path),"ok":report.ok,"errors":report.errors,"warnings":report.warnings,"idsDefined":report.ids,"objectiveReferences":report.objective_refs,"activities":{"qcm":report.qcm,"fill":report.fill},"revisions":revisions})
    return json.dumps({"ok":all(r.ok for r in reports) and not cross,"crossFileErrors":cross,"files":files}, ensure_ascii=False, indent=2)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate frozen learnit.kit.v2 packages.")
    p.add_argument("kits", nargs="+", type=Path)
    p.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[2] / "contracts" / "learnit-kit-v2.schema.json")
    p.add_argument("--foundation-profile", action="store_true")
    p.add_argument("--write-digests", action="store_true", help="fill only missing/all-zero digests; refuse non-zero mismatches")
    p.add_argument("--show-canonical", action="store_true")
    p.add_argument("--format", choices=("human","json"), default="human")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        schema = load(args.schema)
        if not isinstance(schema, dict): raise ToolError("schema root must be an object")
        documents: list[tuple[Path, dict[str, Any]]] = []
        write_errors: list[str] = []
        for path in args.kits:
            document = load(path)
            if not isinstance(document, dict): raise ToolError(f"{path}: kit root must be an object")
            if args.write_digests:
                document = copy.deepcopy(document)
                write_errors += [f"{path}: {error}" for error in fill_new_digests(document)]
            documents.append((path, document))
        reports = [validate(path, document, schema, args.foundation_profile) for path, document in documents]
        cross = cross_file_errors(reports) + write_errors
        if args.write_digests and all(r.ok for r in reports) and not cross:
            for path, document in documents:
                path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(render_json(reports, cross, args.show_canonical) if args.format == "json" else render_human(reports, cross, args.show_canonical))
        return 0 if all(r.ok for r in reports) and not cross else 1
    except ToolError as exc:
        print(f"TOOL ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
