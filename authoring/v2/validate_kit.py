#!/usr/bin/env python3
"""Validate frozen learnit.kit.v2 packages and Wave A learning-loop authoring."""
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
    """Deterministic authoring-tool failure."""


@dataclass
class Report:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    revisions: list[dict[str, Any]] = field(default_factory=list)
    objective_loops: list[dict[str, Any]] = field(default_factory=list)
    ids: int = 0
    objective_refs: int = 0
    qcm: int = 0
    fill: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ToolError(f"duplicate JSON object key: {key!r}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except FileNotFoundError as exc:
        raise ToolError(f"file not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ToolError(f"file is not UTF-8: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ToolError(
            f"invalid JSON line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def normalize(value: Any, path: str = "$") -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise ToolError(f"{path}: floats are outside the canonical JSON profile")
    if isinstance(value, list):
        return [normalize(item, f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ToolError(f"{path}: non-string object key")
            key = unicodedata.normalize("NFC", key)
            if key in out:
                raise ToolError(f"{path}: keys collide after NFC normalization: {key!r}")
            out[key] = normalize(item, f"{path}.{key}")
        return out
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
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest(), text


def json_path(parts: Any) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def rendered(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return repr(value)


def diagnostic(path: str, cause: str, value: Any) -> str:
    return f"{path}: {cause}; value={rendered(value)}"


def schema_errors(document: Any, schema: dict[str, Any]) -> list[str]:
    if Draft202012Validator is None:
        raise ToolError(f"jsonschema>=4.18 is required: {JSONSCHEMA_ERROR}")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    return [
        diagnostic("schema " + json_path(error.absolute_path), error.message, error.instance)
        for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    ]


def define(defs: dict[str, str], value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        return
    if value in defs:
        errors.append(diagnostic(path, f"duplicate canonical ID; first declared at {defs[value]}", value))
    else:
        defs[value] = path


def loop_records(course: dict[str, Any], cp: str) -> list[dict[str, Any]]:
    activities = course.get("activities", [])
    records: list[dict[str, Any]] = []
    for oi, objective in enumerate(course.get("objectives", [])):
        if not isinstance(objective, dict) or not isinstance(objective.get("objectiveId"), str):
            continue
        oid = objective["objectiveId"]
        training: list[dict[str, Any]] = []
        validation: list[dict[str, Any]] = []
        for ai, activity in enumerate(activities):
            if not isinstance(activity, dict) or oid not in activity.get("objectiveIds", []):
                continue
            item = {
                "index": ai,
                "path": f"{cp}.activities[{ai}]",
                "activityLineageId": activity.get("activityLineageId"),
                "learningPhase": activity.get("learningPhase"),
                "assessmentRole": activity.get("assessmentRole"),
            }
            phase, role = activity.get("learningPhase"), activity.get("assessmentRole")
            if role == "practice" and phase != "validation":
                training.append(item)
            if role == "validation" and phase == "validation":
                validation.append(item)
        pairs = [
            {"training": train["path"], "validation": valid["path"]}
            for train in training for valid in validation if train["index"] < valid["index"]
        ]
        records.append({
            "objectivePath": f"{cp}.objectives[{oi}].objectiveId",
            "objectiveId": oid,
            "trainingActivities": training,
            "validationActivities": validation,
            "orderedDistinctPairs": pairs,
            "complete": bool(pairs),
        })
    return records


def add_loop_errors(records: list[dict[str, Any]], errors: list[str]) -> None:
    if any(record["complete"] for record in records):
        return
    for record in records:
        value = {
            "objectiveId": record["objectiveId"],
            "trainingActivityPaths": [item["path"] for item in record["trainingActivities"]],
            "validationActivityPaths": [item["path"] for item in record["validationActivities"]],
        }
        if not record["trainingActivities"]:
            cause = "objective has no training activity with assessmentRole='practice' outside learningPhase='validation'"
        elif not record["validationActivities"]:
            cause = "objective has no validation activity with learningPhase='validation' and assessmentRole='validation'"
        else:
            cause = "validation must follow a distinct training activity for the same objective"
        errors.append(diagnostic(record["objectivePath"], cause, value))


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
        for oi, objective in enumerate(objectives if isinstance(objectives, list) else []):
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
                report.errors.append(diagnostic(
                    ap,
                    "validation learningPhase and assessmentRole must match",
                    {"learningPhase": phase, "assessmentRole": role},
                ))
            explanation = activity.get("explanation")
            if isinstance(explanation, str) and len(explanation.strip()) < 35:
                report.warnings.append(diagnostic(ap + ".explanation", "explanation is unusually short", explanation))

            refs = activity.get("objectiveIds", [])
            if isinstance(refs, list):
                for ri, oid in enumerate(refs):
                    report.objective_refs += 1
                    if isinstance(oid, str): uses[oid] += 1
                    if oid not in objective_ids:
                        report.errors.append(diagnostic(
                            f"{ap}.objectiveIds[{ri}]", "missing objective reference", oid
                        ))

            if activity.get("type") == "qcm":
                report.qcm += 1
                choices: set[str] = set()
                for xi, choice in enumerate(activity.get("choices", [])):
                    if not isinstance(choice, dict): continue
                    cid = choice.get("choiceId")
                    loc = f"{ap}.choices[{xi}].choiceId"
                    define(defs, cid, loc, report.errors)
                    if isinstance(cid, str):
                        if cid in choices:
                            report.errors.append(diagnostic(loc, "duplicate choiceId in activity", cid))
                        choices.add(cid)
                correct = activity.get("correctChoiceId")
                if correct not in choices:
                    report.errors.append(diagnostic(
                        ap + ".correctChoiceId", "does not reference a declared choice", correct
                    ))

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
                        if previous_slot:
                            report.warnings.append(diagnostic(ap, "adjacent fill slots may be ambiguous", slots[-2:]))
                    previous_slot = is_slot
                if len(slots) != len(set(slots)):
                    report.errors.append(diagnostic(ap + ".segments", "duplicate slotId", slots))

                tokens: set[str] = set()
                maxima: dict[str, int] = {}
                for ti, token in enumerate(activity.get("tokens", [])):
                    if not isinstance(token, dict): continue
                    tid = token.get("tokenId")
                    loc = f"{ap}.tokens[{ti}].tokenId"
                    define(defs, tid, loc, report.errors)
                    if isinstance(tid, str):
                        if tid in tokens:
                            report.errors.append(diagnostic(loc, "duplicate tokenId in activity", tid))
                        tokens.add(tid)
                        if isinstance(token.get("maxUses"), int): maxima[tid] = token["maxUses"]

                answered: set[str] = set()
                token_uses: Counter[str] = Counter()
                for ni, answer in enumerate(activity.get("answers", [])):
                    if not isinstance(answer, dict): continue
                    sid, tid = answer.get("slotId"), answer.get("tokenId")
                    loc = f"{ap}.answers[{ni}]"
                    if sid not in slots:
                        report.errors.append(diagnostic(loc + ".slotId", "does not reference a declared slot", sid))
                    if sid in answered:
                        report.errors.append(diagnostic(loc + ".slotId", "duplicate answer for slot", sid))
                    if isinstance(sid, str): answered.add(sid)
                    if tid not in tokens:
                        report.errors.append(diagnostic(loc + ".tokenId", "does not reference a declared token", tid))
                    if isinstance(tid, str): token_uses[tid] += 1
                missing = sorted(set(slots) - answered)
                if missing:
                    report.errors.append(diagnostic(ap + ".answers", "slots without answers", missing))
                for tid, count in token_uses.items():
                    if tid in maxima and count > maxima[tid]:
                        report.errors.append(diagnostic(
                            ap + ".answers", f"token use count exceeds maxUses={maxima[tid]}",
                            {"tokenId": tid, "uses": count},
                        ))

        for oid in objective_ids:
            if uses[oid] == 0:
                report.errors.append(diagnostic(cp + ".objectives", "objective is not referenced", oid))

        records = loop_records(course, cp)
        report.objective_loops.extend(records)
        if foundation:
            qcms = sum(isinstance(a, dict) and a.get("type") == "qcm" for a in activities)
            fills = sum(isinstance(a, dict) and a.get("type") == "fill" for a in activities)
            checks = [
                (len(objectives) >= 2, cp + ".objectives", "foundation profile requires at least 2 objectives", len(objectives)),
                (len(activities) >= 6, cp + ".activities", "foundation profile requires at least 6 activities", len(activities)),
                (qcms >= 3, cp + ".activities", "foundation profile requires at least 3 QCM", qcms),
                (fills >= 2, cp + ".activities", "foundation profile requires at least 2 fill activities", fills),
                (any(p in {"application", "transfer"} for p in phases), cp + ".activities", "foundation profile requires application or transfer", phases),
                ("validation" in phases and "validation" in roles, cp + ".activities", "foundation profile requires validation phase and role", {"learningPhases": phases, "assessmentRoles": roles}),
            ]
            for ok, path, cause, value in checks:
                if not ok: report.errors.append(diagnostic(path, cause, value))
            add_loop_errors(records, report.errors)
    report.ids = len(defs)


def add_digest_records(document: dict[str, Any], report: Report) -> None:
    for ci, course in enumerate(document.get("courses", [])):
        if not isinstance(course, dict): continue
        for ai, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict): continue
            path = f"$.courses[{ci}].activities[{ai}]"
            calculated, text = digest(activity, "activityRevisionDigest")
            declared = activity.get("activityRevisionDigest")
            report.revisions.append({
                "level": "activity", "path": path,
                "revisionId": activity.get("activityRevisionId"),
                "declared": declared, "calculated": calculated,
                "bytes": len(text.encode()), "canonical": text,
            })
            if declared != calculated:
                report.errors.append(diagnostic(path + ".activityRevisionDigest", "declared digest differs from calculated digest", {"declared": declared, "calculated": calculated}))
        path = f"$.courses[{ci}]"
        calculated, text = digest(course, "courseRevisionDigest")
        declared = course.get("courseRevisionDigest")
        report.revisions.append({
            "level": "course", "path": path,
            "revisionId": course.get("courseRevisionId"),
            "declared": declared, "calculated": calculated,
            "bytes": len(text.encode()), "canonical": text,
        })
        if declared != calculated:
            report.errors.append(diagnostic(path + ".courseRevisionDigest", "declared digest differs from calculated digest", {"declared": declared, "calculated": calculated}))
    calculated, text = digest(document, "packageRevisionDigest")
    declared = document.get("packageRevisionDigest")
    report.revisions.append({
        "level": "package", "path": "$", "revisionId": document.get("packageRevisionId"),
        "declared": declared, "calculated": calculated,
        "bytes": len(text.encode()), "canonical": text,
    })
    if declared != calculated:
        report.errors.append(diagnostic("$.packageRevisionDigest", "declared digest differs from calculated digest", {"declared": declared, "calculated": calculated}))


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
            if current in (None, "", ZERO_DIGEST):
                activity["activityRevisionDigest"] = calculated
            elif current != calculated:
                errors.append(diagnostic(
                    f"$.courses[{ci}].activities[{ai}]",
                    "non-zero digest mismatch; allocate a new activityRevisionId and reset its digest",
                    {"activityRevisionId": activity.get("activityRevisionId"), "declared": current, "calculated": calculated},
                ))
        calculated, _ = digest(course, "courseRevisionDigest")
        current = course.get("courseRevisionDigest")
        if current in (None, "", ZERO_DIGEST):
            course["courseRevisionDigest"] = calculated
        elif current != calculated:
            errors.append(diagnostic(
                f"$.courses[{ci}]",
                "non-zero digest mismatch; allocate a new courseRevisionId and reset its digest",
                {"courseRevisionId": course.get("courseRevisionId"), "declared": current, "calculated": calculated},
            ))
    calculated, _ = digest(document, "packageRevisionDigest")
    current = document.get("packageRevisionDigest")
    if current in (None, "", ZERO_DIGEST):
        document["packageRevisionDigest"] = calculated
    elif current != calculated:
        errors.append(diagnostic(
            "$", "non-zero digest mismatch; allocate a new packageRevisionId and reset its digest",
            {"packageRevisionId": document.get("packageRevisionId"), "declared": current, "calculated": calculated},
        ))
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
                errors.append(diagnostic(
                    location,
                    f"revisionId is associated with different content or digest; first seen at {seen[rid][3]}",
                    rid,
                ))
            else:
                seen[rid] = (*signature, location)
    return errors


def render_json(reports: list[Report], cross: list[str], show: bool) -> str:
    files = []
    for report in reports:
        revisions = []
        for record in report.revisions:
            item = {key: value for key, value in record.items() if key != "canonical"}
            if show: item["canonicalJson"] = record["canonical"]
            revisions.append(item)
        files.append({
            "path": str(report.path), "ok": report.ok,
            "errors": report.errors, "warnings": report.warnings,
            "idsDefined": report.ids, "objectiveReferences": report.objective_refs,
            "activities": {"qcm": report.qcm, "fill": report.fill},
            "objectiveLoops": report.objective_loops, "revisions": revisions,
        })
    return json.dumps({
        "ok": all(report.ok for report in reports) and not cross,
        "crossFileErrors": cross, "files": files,
    }, ensure_ascii=False, indent=2)


def render_human(reports: list[Report], cross: list[str], show: bool) -> str:
    lines: list[str] = []
    for report in reports:
        complete = sum(record["complete"] for record in report.objective_loops)
        lines += [
            f"FILE {report.path}", f"  status: {'PASS' if report.ok else 'FAIL'}",
            f"  semantic IDs defined: {report.ids}",
            f"  objective references checked: {report.objective_refs}",
            f"  activities: qcm={report.qcm}, fill={report.fill}",
            f"  objective loops: complete={complete}/{len(report.objective_loops)}",
        ]
        for record in report.revisions:
            lines.append(f"  {record['level']} {record['path']} revision={record['revisionId']} bytes={record['bytes']} digest={record['calculated']}")
            if show: lines.append(f"    canonical={record['canonical']}")
        lines += [f"  WARNING: {warning}" for warning in report.warnings]
        lines += [f"  ERROR: {error}" for error in report.errors]
    lines += [f"CROSS-FILE ERROR: {error}" for error in cross]
    lines.append(f"OVERALL {'PASS' if all(report.ok for report in reports) and not cross else 'FAIL'}")
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    argp = argparse.ArgumentParser(description="Validate frozen learnit.kit.v2 packages.")
    argp.add_argument("kits", nargs="+", type=Path)
    argp.add_argument(
        "--schema", type=Path,
        default=Path(__file__).resolve().parents[2] / "contracts/learnit-kit-v2.schema.json",
    )
    argp.add_argument("--foundation-profile", action="store_true")
    argp.add_argument("--write-digests", action="store_true")
    argp.add_argument("--show-canonical", action="store_true")
    argp.add_argument("--format", choices=("human", "json"), default="human")
    return argp


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        schema = load(args.schema)
        if not isinstance(schema, dict):
            raise ToolError("schema root must be an object")
        documents: list[tuple[Path, dict[str, Any]]] = []
        write_errors: list[str] = []
        for path in args.kits:
            document = load(path)
            if not isinstance(document, dict):
                raise ToolError(f"{path}: kit root must be an object")
            if args.write_digests:
                document = copy.deepcopy(document)
                write_errors += [f"{path}: {error}" for error in fill_new_digests(document)]
            documents.append((path, document))
        reports = [validate(path, document, schema, args.foundation_profile) for path, document in documents]
        cross = cross_file_errors(reports) + write_errors
        if args.write_digests and all(report.ok for report in reports) and not cross:
            for path, document in documents:
                path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            render_json(reports, cross, args.show_canonical)
            if args.format == "json"
            else render_human(reports, cross, args.show_canonical)
        )
        return 0 if all(report.ok for report in reports) and not cross else 1
    except ToolError as exc:
        print(f"TOOL ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
