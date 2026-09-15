#!/usr/bin/env python3
"""Deterministic pedagogical-quality analysis for canonical Atlas kits."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "contracts/learnit-kit-v2.schema.json"
V2_VALIDATOR_PATH = ROOT / "authoring/v2/validate_kit.py"
ATLAS_VALIDATOR_PATH = ROOT / "authoring/v2/atlas/validate_atlas_content.py"
V4_VALIDATOR_PATH = ROOT / "authoring/v4/validate_kit.py"
REPORT_SCHEMA = "learnit.atlas.pedagogical_quality_report.v1"
PROFILE = "atlas.pedagogy.v1"
V4_PROFILE = "atlas.pedagogy.student-v0.1.v4"
ENGINE_VERSION = "1.0.0"
V4_ENGINE_VERSION = "1.1.0"
SEVERITY_ORDER = {"blocking": 0, "warning": 1, "advice": 2}
DIFFICULTY_RANK = {"easy": 0, "medium": 1, "advanced": 2, "expert": 3}
NON_SCORED = {"lesson", "flashcard"}
EVALUATED = {"qcm", "fill", "constructed", "matching", "order", "classify"}
HIGHER_ORDER = re.compile(
    r"\b(?:explain|expliquer|explique|justif|d[eé]montr|derive|d[eé]riv|calcul|compare|analys|raisonn|reason|constru|formul|prove|prouv)\w*",
    re.IGNORECASE,
)


class QualityError(ValueError):
    """Deterministic quality-engine input or authority failure."""


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise QualityError(f"cannot load authority: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_V2 = None
_ATLAS = None
_V4 = None


def authorities():
    global _V2, _ATLAS
    if _V2 is None:
        _V2 = _load_module("learnit_m3_1_v2_authority", V2_VALIDATOR_PATH)
    if _ATLAS is None:
        _ATLAS = _load_module("learnit_m3_1_atlas_authority", ATLAS_VALIDATOR_PATH)
    return _V2, _ATLAS


def v4_authority():
    global _V4
    if _V4 is None:
        _V4 = _load_module("learnit_student_v01_v4_authority", V4_VALIDATOR_PATH)
    return _V4


def _split_general(message: str) -> tuple[str, str]:
    if ": " in message:
        path, cause = message.split(": ", 1)
        return path.strip(), cause.strip()
    return "$", message


def _refs(package: dict[str, Any], course: dict[str, Any] | None = None, objective: dict[str, Any] | None = None, activity: dict[str, Any] | None = None) -> dict[str, str]:
    result = {"packageLineageId": str(package.get("packageLineageId", ""))}
    if course is not None:
        result["courseLineageId"] = str(course.get("courseLineageId", ""))
    if objective is not None:
        result["objectiveId"] = str(objective.get("objectiveId", ""))
    if activity is not None:
        result["activityLineageId"] = str(activity.get("activityLineageId", ""))
    return result


def _diagnostic(code: str, severity: str, path: str, cause: str, impact: str, fix: str, refs: dict[str, str], evidence: Any = None) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "severity": severity, "path": path, "refs": refs, "cause": cause, "impact": impact, "fix": fix}
    if evidence is not None:
        item["evidence"] = evidence
    return item


def _band(warnings: int, advice: int, blocking: int = 0) -> str:
    if blocking:
        return "BLOCKED"
    if warnings:
        return "COMPLETE"
    if advice:
        return "STRONG"
    return "EXCELLENT_BY_PROFILE"


def _counts(diagnostics: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "blocking": sum(item["severity"] == "blocking" for item in diagnostics),
        "warning": sum(item["severity"] == "warning" for item in diagnostics),
        "advice": sum(item["severity"] == "advice" for item in diagnostics),
    }


def _sort_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(diagnostics, key=lambda item: (SEVERITY_ORDER.get(item.get("severity"), 99), item.get("path", "$"), item.get("code", "")))


def _canonical_diagnostics_v4(package: dict[str, Any]) -> list[dict[str, Any]]:
    v4 = v4_authority()
    diagnostics: list[dict[str, Any]] = []
    try:
        schema = v4.load(v4.SCHEMA_PATH)
        if not isinstance(schema, dict):
            raise QualityError("v4 schema root must be an object")
        report = v4.validate(Path("<pedagogical-quality-v4>"), package, schema)
    except Exception as exc:
        diagnostics.append(_diagnostic(
            "CANONICAL_V4_INVALID", "blocking", "$", str(exc),
            "The v4 candidate cannot enter pedagogical-quality analysis.",
            "Fix the candidate against the frozen v4 schema and authoring validator.", _refs(package),
        ))
    else:
        for message in report.errors:
            path, cause = _split_general(message)
            diagnostics.append(_diagnostic(
                "CANONICAL_V4_INVALID", "blocking", path, cause,
                "The v4 candidate violates frozen structural or semantic authoring invariants.",
                "Fix the candidate without changing the frozen v4 contract.", _refs(package),
            ))
    return _sort_diagnostics(diagnostics)


def _canonical_diagnostics(package: dict[str, Any]) -> list[dict[str, Any]]:
    if package.get("contract") == "learnit.kit.v4":
        return _canonical_diagnostics_v4(package)
    v2, atlas = authorities()
    diagnostics: list[dict[str, Any]] = []
    schema = v2.load(SCHEMA_PATH)
    if not isinstance(schema, dict):
        raise QualityError("canonical schema root must be an object")
    try:
        report = v2.validate(Path("<pedagogical-quality>"), package, schema, False)
    except Exception as exc:
        diagnostics.append(_diagnostic("CANONICAL_V2_INVALID", "blocking", "$", str(exc), "Le kit ne peut pas être accepté par le validateur Learn-it canonique.", "Corriger d'abord la structure ou le contenu canonique avec le schéma et le validateur v2 existants.", _refs(package)))
    else:
        for message in report.errors:
            path, cause = _split_general(message)
            diagnostics.append(_diagnostic("CANONICAL_V2_INVALID", "blocking", path, cause, "Le kit n'est pas valide selon le contrat Learn-it canonique.", "Corriger d'abord cette erreur avec le schéma et le validateur v2 existants.", _refs(package)))
    try:
        atlas.validate_package(package)
    except Exception as exc:
        diagnostics.append(_diagnostic("CANONICAL_ATLAS_INVALID", "blocking", "$", str(exc), "Le profil éditorial Atlas canonique rejette ce kit.", "Corriger le kit sans modifier le validateur Atlas ni le contrat.", _refs(package)))
    return _sort_diagnostics(diagnostics)


def _objective_rows(course: dict[str, Any], objective_id: str, atlas: Any) -> list[tuple[int, str, dict[str, Any]]]:
    rows: list[tuple[int, str, dict[str, Any]]] = []
    for index, activity in enumerate(course.get("activities", [])):
        if activity.get("objectiveIds") != [objective_id]:
            continue
        cls = atlas.CLASS.get((activity.get("learningPhase"), activity.get("assessmentRole")))
        if cls is not None:
            rows.append((index, cls, activity))
    return rows


def _quality_diagnostics_v2(package: dict[str, Any]) -> list[dict[str, Any]]:
    _, atlas = authorities()
    diagnostics: list[dict[str, Any]] = []
    for ci, course in enumerate(package.get("courses", [])):
        cp = f"$.courses[{ci}]"
        activities = course.get("activities", [])
        declared = course.get("estimatedMinutes")
        authored = sum(activity.get("estimatedMinutes", 0) for activity in activities)
        if declared != authored:
            diagnostics.append(_diagnostic("PQ_COURSE_DURATION_MISMATCH", "warning", cp + ".estimatedMinutes", f"La durée du parcours est {declared} min alors que ses activités totalisent {authored} min.", "La durée annoncée peut être incohérente avec le contenu réel.", "Aligner la durée du parcours sur la somme des activités.", _refs(package, course), {"declaredMinutes": declared, "activityMinutes": authored}))
        claims = course.get("atlasValidationIndependenceClaims", [])
        for oi, objective in enumerate(course.get("objectives", [])):
            oid = objective.get("objectiveId")
            op = f"{cp}.objectives[{oi}]"
            rows = _objective_rows(course, oid, atlas)
            if len(rows) != 5:
                continue
            objective_claims = [claim for claim in claims if claim.get("objectiveId") == oid]
            refs = _refs(package, course, objective)
            seen: dict[str, tuple[int, dict[str, Any]]] = {}
            for ai, _, activity in rows:
                stimulus_digest = atlas.stimulus(activity)
                if stimulus_digest in seen:
                    first_index, first_activity = seen[stimulus_digest]
                    diagnostics.append(_diagnostic("PQ_OBJECTIVE_DUPLICATE_STIMULUS", "warning", f"{cp}.activities[{ai}]", "Deux activités du même objectif produisent exactement le même stimulus normalisé.", "La répétition exacte réduit la valeur d'une validation ou d'un transfert indépendant.", "Modifier le contexte, la représentation ou l'opération demandée.", _refs(package, course, objective, activity), {"stimulusDigest": stimulus_digest, "firstActivityIndex": first_index, "firstActivityLineageId": first_activity.get("activityLineageId")}))
                else:
                    seen[stimulus_digest] = (ai, activity)
            first_practice = rows[0][2]
            transfer = rows[4][2]
            if DIFFICULTY_RANK.get(transfer.get("difficulty"), -1) <= DIFFICULTY_RANK.get(first_practice.get("difficulty"), -1):
                diagnostics.append(_diagnostic("PQ_TRANSFER_NOT_HARDER", "warning", f"{cp}.activities[{rows[4][0]}].difficulty", "L'activité de transfert n'est pas plus difficile que la première pratique de l'objectif.", "Le transfert risque de ne pas exiger une mobilisation plus autonome.", "Augmenter la difficulté du transfert si le contenu source le justifie.", _refs(package, course, objective, transfer), {"practiceDifficulty": first_practice.get("difficulty"), "transferDifficulty": transfer.get("difficulty")}))
            first_validation, second_validation = rows[2][2], rows[3][2]
            expected = (
                (first_practice.get("activityLineageId"), first_validation.get("activityLineageId"), {"new-instance", "alternate-representation"}),
                (first_validation.get("activityLineageId"), second_validation.get("activityLineageId"), {"new-context", "alternate-representation"}),
            )
            chain_ok = True
            chain_evidence = []
            for source, target, allowed in expected:
                match = next((claim for claim in objective_claims if claim.get("sourceActivityLineageId") == source and claim.get("targetActivityLineageId") == target), None)
                chain_evidence.append({"sourceActivityLineageId": source, "targetActivityLineageId": target, "basisCode": None if match is None else match.get("basisCode"), "allowedBasisCodes": sorted(allowed)})
                if match is None or match.get("basisCode") not in allowed:
                    chain_ok = False
            if not chain_ok:
                diagnostics.append(_diagnostic("PQ_VALIDATION_CHAIN_WEAK", "warning", cp + ".atlasValidationIndependenceClaims", "Les deux claims d'indépendance ne suivent pas la chaîne Atlas attendue pratique → validation 1 → validation 2.", "La preuve d'indépendance est moins structurée que le profil M3.1.", "Conserver exactement deux claims et la chaîne attendue.", refs, {"expectedChain": chain_evidence, "claimCount": len(objective_claims)}))
            types = [activity.get("type") for _, _, activity in rows]
            if len(set(types)) == 1:
                diagnostics.append(_diagnostic("PQ_OBJECTIVE_SINGLE_ACTIVITY_TYPE", "advice", op, "Toutes les activités de cet objectif utilisent le même type d'interaction.", "Une seule mécanique peut limiter la variété de récupération.", "Diversifier uniquement lorsque le contenu s'y prête.", refs, {"activityType": types[0]}))
            validation_types = [first_validation.get("type"), second_validation.get("type")]
            if validation_types[0] == validation_types[1]:
                diagnostics.append(_diagnostic("PQ_VALIDATIONS_SAME_ACTIVITY_TYPE", "advice", op, "Les deux validations indépendantes utilisent le même type d'interaction.", "Une autre mécanique peut réduire la dépendance à un format unique.", "Diversifier si cela teste le même objectif.", refs, {"validationTypes": validation_types}))
            if not any(claim.get("basisCode") == "alternate-representation" for claim in objective_claims):
                diagnostics.append(_diagnostic("PQ_NO_ALTERNATE_REPRESENTATION", "advice", cp + ".atlasValidationIndependenceClaims", "Aucun des deux claims d'indépendance n'utilise une représentation alternative.", "Le profil ne démontre pas la reconnaissance sous une représentation différente.", "Utiliser alternate-representation uniquement si justifié.", refs, {"basisCodes": [claim.get("basisCode") for claim in objective_claims]}))
    return _sort_diagnostics(diagnostics)


def _quality_diagnostics_v4(package: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for ci, course in enumerate(package.get("courses", [])):
        cp = f"$.courses[{ci}]"
        activities = [a for a in course.get("activities", []) if isinstance(a, dict)]
        if activities and all(isinstance(a.get("estimatedMinutes"), int) for a in activities):
            authored = sum(a["estimatedMinutes"] for a in activities)
            if course.get("estimatedMinutes") != authored:
                diagnostics.append(_diagnostic("PQ_COURSE_DURATION_MISMATCH", "warning", cp + ".estimatedMinutes", "Course duration differs from the sum of authored activity durations.", "Learner time expectations can drift from authored content.", "Align the course duration or activity estimates.", _refs(package, course), {"declaredMinutes": course.get("estimatedMinutes"), "activityMinutes": authored}))
        for oi, objective in enumerate(course.get("objectives", [])):
            if not isinstance(objective, dict):
                continue
            oid = objective.get("objectiveId")
            op = f"{cp}.objectives[{oi}]"
            related = [(idx, activity) for idx, activity in enumerate(activities) if oid in activity.get("objectiveIds", [])]
            exposure = [(idx, a) for idx, a in related if a.get("type") in NON_SCORED]
            evaluated = [(idx, a) for idx, a in related if a.get("type") in EVALUATED]
            practice = [(idx, a) for idx, a in evaluated if a.get("assessmentRole") == "practice"]
            validation = [(idx, a) for idx, a in evaluated if a.get("assessmentRole") == "validation" and a.get("learningPhase") == "validation"]
            refs = _refs(package, course, objective)
            if exposure and not practice:
                diagnostics.append(_diagnostic("PQ_V4_EXPOSURE_WITHOUT_PRACTICE", "warning", op, "This objective exposes content but has no scored practice activity.", "Exposure alone does not establish retrieval or application practice.", "Add source-supported practice when the learning goal requires it; do not turn lesson/flashcard into scored evidence.", refs))
            if exposure and not validation:
                diagnostics.append(_diagnostic("PQ_V4_EXPOSURE_WITHOUT_VALIDATION", "warning", op, "This objective exposes content but has no evaluated validation activity.", "Lesson/flashcard completion cannot establish validation evidence.", "Add an appropriate evaluated validation activity when validation is part of the objective.", refs))
            if not exposure and evaluated and len(evaluated) >= 2 and not practice and all(a.get("assessmentRole") in {"diagnostic", "validation"} for _, a in evaluated):
                diagnostics.append(_diagnostic("PQ_V4_ASSESSMENT_ONLY_OBJECTIVE", "warning", op, "This objective contains only diagnostic/validation assessment and no learning exposure or practice.", "A genuinely new topic can become a quiz-only experience.", "For new material, add source-supported exposition or practice; for prior-knowledge checks, keep the lean assessment design.", refs))
            evaluated_types = [a.get("type") for _, a in evaluated]
            if len(evaluated_types) >= 3 and len(set(evaluated_types)) == 1:
                diagnostics.append(_diagnostic("PQ_V4_REPETITIVE_OPERATION", "advice", op, "Three or more evaluated activities repeat the same interaction family.", "The learner may rehearse the interface rather than the intended operation.", "Vary the operation only when pedagogy and source material justify it; there is no activity-type quota.", refs, {"activityType": evaluated_types[0], "count": len(evaluated_types)}))
        for ai, activity in enumerate(activities):
            ap = f"{cp}.activities[{ai}]"
            refs = _refs(package, course, None, activity)
            if activity.get("type") == "classify":
                assignments = activity.get("assignments", [])
                buckets = activity.get("buckets", [])
                counts = Counter(item.get("bucketId") for item in assignments if isinstance(item, dict))
                if len(activity.get("items", [])) == len(buckets) and buckets and all(counts.get(bucket.get("bucketId"), 0) == 1 for bucket in buckets if isinstance(bucket, dict)):
                    diagnostics.append(_diagnostic("PQ_V4_CLASSIFY_ONE_ITEM_PER_BUCKET", "advice", ap, "Each classify bucket contains exactly one item.", "The task can collapse into a disguised one-to-one choice/matching operation rather than category formation.", "Use classify when multiple examples must genuinely be sorted into conceptual categories; otherwise prefer a simpler family.", refs))
            if activity.get("type") == "constructed" and activity.get("assessmentRole") in {"diagnostic", "validation"}:
                prompt = str(activity.get("prompt", ""))
                if not HIGHER_ORDER.search(prompt):
                    diagnostics.append(_diagnostic("PQ_V4_CONSTRUCTED_LOW_OPERATION_SIGNAL", "advice", ap + ".prompt", "The constructed-response prompt does not contain a clear construction/reasoning operation signal.", "Free text alone is not evidence of higher-order thinking.", "Use constructed only when the learner must produce a bounded response or reasoning; otherwise prefer qcm/fill/matching/order/classify.", refs))
    return _sort_diagnostics(diagnostics)


def _quality_diagnostics(package: dict[str, Any]) -> list[dict[str, Any]]:
    if package.get("contract") == "learnit.kit.v4":
        return _quality_diagnostics_v4(package)
    return _quality_diagnostics_v2(package)


def _summaries(package: dict[str, Any], diagnostics: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    courses: list[dict[str, Any]] = []
    objectives: list[dict[str, Any]] = []
    for ci, course in enumerate(package.get("courses", [])):
        course_id = course.get("courseLineageId")
        related_course = [d for d in diagnostics if d.get("refs", {}).get("courseLineageId") == course_id]
        cc = _counts(related_course)
        courses.append({"path": f"$.courses[{ci}]", "courseLineageId": course_id, "title": course.get("title"), "counts": cc, "qualityBand": _band(cc["warning"], cc["advice"], cc["blocking"])})
        for oi, objective in enumerate(course.get("objectives", [])):
            objective_id = objective.get("objectiveId")
            related = [d for d in diagnostics if d.get("refs", {}).get("objectiveId") == objective_id and d.get("refs", {}).get("courseLineageId") == course_id]
            oc = _counts(related)
            objectives.append({"path": f"$.courses[{ci}].objectives[{oi}]", "courseLineageId": course_id, "objectiveId": objective_id, "label": objective.get("label"), "counts": oc, "qualityBand": _band(oc["warning"], oc["advice"], oc["blocking"])})
    return courses, objectives


def analyze_package(package: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(package, dict):
        raise QualityError("kit root must be a JSON object")
    is_v4 = package.get("contract") == "learnit.kit.v4"
    profile = V4_PROFILE if is_v4 else PROFILE
    engine_version = V4_ENGINE_VERSION if is_v4 else ENGINE_VERSION
    canonical = _canonical_diagnostics(package)
    if canonical:
        return {"schema": REPORT_SCHEMA, "profile": profile, "engineVersion": engine_version, "canonicalValid": False, "verdict": "HOLD_CANONICAL_INVALID", "qualityBand": "BLOCKED", "counts": _counts(canonical), "diagnostics": canonical, "courses": [], "objectives": []}
    diagnostics = _quality_diagnostics(package)
    counts = _counts(diagnostics)
    courses, objectives = _summaries(package, diagnostics)
    return {"schema": REPORT_SCHEMA, "profile": profile, "engineVersion": engine_version, "canonicalValid": True, "verdict": "PASS_ATLAS_PEDAGOGICAL_PROFILE_V1", "qualityBand": _band(counts["warning"], counts["advice"], counts["blocking"]), "counts": counts, "diagnostics": diagnostics, "courses": courses, "objectives": objectives}


def canonical_report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def report_bytes(report: dict[str, Any]) -> bytes:
    return canonical_report_json(report).encode("utf-8")


def render_human(report: dict[str, Any]) -> str:
    lines = [f"ATLAS PEDAGOGICAL QUALITY: {report['qualityBand']}", f"Canonical: {'PASS' if report['canonicalValid'] else 'FAIL'}", f"Verdict: {report['verdict']}", "Diagnostics: blocking={blocking} warning={warning} advice={advice}".format(**report["counts"])]
    for item in report["diagnostics"]:
        lines.append(f"- {item['severity'].upper()} {item['code']} {item['path']}: {item['cause']}")
        lines.append(f"  Fix: {item['fix']}")
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    argp = argparse.ArgumentParser(description="Validate deterministic Atlas pedagogical quality for canonical v2/v4 kits.")
    argp.add_argument("kit", type=Path)
    argp.add_argument("--json", action="store_true", dest="as_json")
    argp.add_argument("--require-excellent", action="store_true")
    return argp


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        v2, _ = authorities()
        document = v2.load(args.kit)
        if not isinstance(document, dict):
            raise QualityError("kit root must be a JSON object")
        report = analyze_package(document)
    except Exception as exc:
        if args.as_json:
            print(json.dumps({"schema": "learnit.atlas.pedagogical_quality_error.v1", "error": "INPUT_OR_AUTHORITY_FAILURE", "cause": str(exc)}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        else:
            print(f"QUALITY ENGINE ERROR: {exc}", file=sys.stderr)
        return 4
    if args.as_json:
        sys.stdout.write(canonical_report_json(report))
    else:
        print(render_human(report))
    if not report["canonicalValid"]:
        return 2
    if args.require_excellent and report["qualityBand"] != "EXCELLENT_BY_PROFILE":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
