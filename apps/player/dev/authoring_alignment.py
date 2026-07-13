#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "authoring_alignment_report.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.validate_kit import validate_payload  # noqa: E402


def read_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def schema_enum(schema: dict, activity_type: str, field: str) -> list[str]:
    return list(schema["$defs"][activity_type]["properties"][field]["enum"])


def course_metrics(payload: dict) -> dict:
    activities = [activity for course in payload.get("courses", []) for activity in course.get("activities", [])]
    assets = {asset.get("id") for asset in payload.get("assets", []) if isinstance(asset, dict)}
    used_assets = {
        media.get("assetId")
        for activity in activities
        for media in activity.get("media", [])
        if isinstance(media, dict) and media.get("assetId")
    }
    objectives = Counter(activity.get("objective") for activity in activities)
    return {
        "courses": len(payload.get("courses", [])),
        "activities": len(activities),
        "activityTypes": sorted({activity.get("type") for activity in activities}),
        "learningPhases": sorted({activity.get("learning_phase") for activity in activities}),
        "assessmentRoles": sorted({activity.get("assessment_role") for activity in activities}),
        "objectives": len(objectives),
        "objectiveEvidenceCounts": dict(objectives),
        "assets": len(assets),
        "usedAssets": len(used_assets),
        "unusedAssets": sorted(assets - used_assets),
        "transferProbes": sum(activity.get("transfer_probe") is True for activity in activities),
        "farTransferProbes": sum(activity.get("transfer_probe") is True and activity.get("transfer_distance") == "far" for activity in activities),
        "farValidationObjectives": sorted({activity.get("objective") for activity in activities if activity.get("transfer_probe") is True and activity.get("transfer_distance") == "far" and activity.get("assessment_role") == "validation"}),
    }


def run() -> dict:
    capabilities = read_json("contract/learnit-capabilities.json")
    schema = read_json("contract/learnit-import.schema.json")
    taxonomy = read_json("contract/pedagogical-taxonomy.json")
    skill = (ROOT / "authoring/SKILL_CURRENT.md").read_text(encoding="utf-8")
    validator = (ROOT / "tools/validate_kit.py").read_text(encoding="utf-8")
    stable_types = sorted(name for name, row in capabilities["activity_types"].items() if row.get("status") == "stable")

    type_test_map = {
        "qcm": "tests/activity_qcm_flashcard.py",
        "flashcard": "tests/activity_qcm_flashcard.py",
        "fill": "tests/activity_fill.py",
        "matching": "tests/activity_matching.py",
        "order": "tests/activity_order.py",
    }
    type_matrix = []
    for activity_type in stable_types:
        definition = schema.get("$defs", {}).get(activity_type, {})
        schema_const = definition.get("properties", {}).get("type", {}).get("const")
        module = ROOT / "src/activities" / f"{activity_type}.js"
        test = ROOT / type_test_map[activity_type]
        row = {
            "activityType": activity_type,
            "status": capabilities["activity_types"][activity_type].get("status"),
            "schema": schema_const == activity_type,
            "rendererModule": module.exists(),
            "unitContract": test.exists(),
            "skill": bool(re.search(rf"`?{re.escape(activity_type)}`?", skill, flags=re.I)),
            "validator": activity_type in validator or schema_const == activity_type,
        }
        row["ok"] = all(value for key, value in row.items() if key not in {"activityType", "status", "ok"}) and row["status"] == "stable"
        type_matrix.append(row)

    taxonomy_matrix = []
    for field in ("difficulty", "learning_phase", "assessment_role", "transfer_distance"):
        expected = list(taxonomy[field])
        by_type = {activity_type: schema_enum(schema, activity_type, field) for activity_type in stable_types}
        taxonomy_matrix.append({"field": field, "expected": expected, "byType": by_type, "ok": all(values == expected for values in by_type.values())})
    for field, definition, schema_path in (
        ("pedagogical_role", schema["$defs"]["asset"]["properties"]["pedagogical_role"]["enum"], taxonomy["pedagogical_role"]),
        ("media_placement", schema["$defs"]["mediaRef"]["properties"]["placement"]["enum"], taxonomy["media_placement"]),
        ("media_display", schema["$defs"]["mediaRef"]["properties"]["display"]["enum"], taxonomy["media_display"]),
    ):
        taxonomy_matrix.append({"field": field, "expected": schema_path, "schema": definition, "ok": list(definition) == list(schema_path)})

    evidence_paths = []
    for name, rel in capabilities.get("evidence", {}).items():
        if not isinstance(rel, str) or not ("/" in rel or rel.endswith(".py") or rel.endswith(".json") or rel.endswith(".md")):
            continue
        evidence_paths.append({"name": name, "path": rel, "exists": (ROOT / rel).exists()})

    golden_rows = []
    for path in sorted((ROOT / "data/golden-kits").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        validation = validate_payload(payload)
        metrics = course_metrics(payload)
        is_real_probe = path.name in {"golden_nombres_complexes.json", "golden_signaux_electriques.json"}
        quality_ok = (
            validation["ok"]
            and (not is_real_probe or validation["summary"] == {"errors": 0, "warnings": 0})
            and (not is_real_probe or set(metrics["activityTypes"]) == set(stable_types))
            and (not is_real_probe or {"transfer", "remediation"} <= set(metrics["learningPhases"]))
            and (not is_real_probe or {"practice", "diagnostic", "validation", "remediation"} <= set(metrics["assessmentRoles"]))
            and not metrics["unusedAssets"]
            and (not is_real_probe or metrics["farTransferProbes"] >= metrics["objectives"])
            and (not is_real_probe or len(metrics["farValidationObjectives"]) == metrics["objectives"])
        )
        golden_rows.append({"path": str(path.relative_to(ROOT)), "realCourseProbe": is_real_probe, "validation": validation["summary"], "metrics": metrics, "ok": quality_ok})

    semantic_diagnostic_codes = [
        "objective-single-evidence",
        "objective-no-validation",
        "objective-no-remediation",
        "objective-no-transfer",
        "course-format-imbalance",
        "question-exact-duplicate",
        "asset-unused",
        "objective-no-far-transfer-probe",
        "objective-no-higher-order-assessment",
    ]
    diagnostic_matrix = [{"code": code, "implemented": code in validator} for code in semantic_diagnostic_codes]

    checks = [
        {"code": "stable-activity-capability-matrix", "ok": all(row["ok"] for row in type_matrix)},
        {"code": "taxonomy-schema-exact", "ok": all(row["ok"] for row in taxonomy_matrix)},
        {"code": "capability-evidence-paths-exist", "ok": all(row["exists"] for row in evidence_paths), "detail": [row for row in evidence_paths if not row["exists"]]},
        {"code": "semantic-diagnostics-implemented", "ok": all(row["implemented"] for row in diagnostic_matrix)},
        {"code": "golden-kits-valid", "ok": bool(golden_rows) and all(row["ok"] for row in golden_rows if row["realCourseProbe"])},
        {"code": "two-real-course-golden-probes", "ok": sum(row["realCourseProbe"] and row["ok"] for row in golden_rows) == 2},
        {"code": "skill-contract-version-aligned", "ok": capabilities["contract_version"] in skill},
        {"code": "skill-version-aligned", "ok": capabilities["authoring_skill_version"] in skill},
    ]
    ok = all(check["ok"] for check in checks)
    report = {
        "schema": "learnit.rc712.authoring_alignment.v1",
        "ok": ok,
        "policy": "Read-only authoring evidence. It does not change runtime import, learner workflow or pedagogical decisions.",
        "contractVersion": capabilities["contract_version"],
        "applicationBaseline": capabilities["application_baseline"],
        "authoringSkillVersion": capabilities["authoring_skill_version"],
        "activityCapabilityMatrix": type_matrix,
        "taxonomyMatrix": taxonomy_matrix,
        "evidencePaths": evidence_paths,
        "semanticDiagnosticMatrix": diagnostic_matrix,
        "goldenKits": golden_rows,
        "checks": checks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    report = run()
    print(json.dumps({"ok": report["ok"], "report": str(OUT.relative_to(ROOT)), "passed": sum(row["ok"] for row in report["checks"]), "total": len(report["checks"])}, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
