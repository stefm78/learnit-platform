#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import re

from support import ROOT, load_manifest

REPORT = ROOT / "reports" / "contract_skill_sync_report.json"


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def load_validator():
    path = ROOT / "tools" / "validate_kit.py"
    spec = importlib.util.spec_from_file_location("learnit_validate_kit", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    capabilities = load("contract/learnit-capabilities.json")
    schema = load("contract/learnit-import.schema.json")
    taxonomy = load("contract/pedagogical-taxonomy.json")
    fixtures = load("authoring/contract-fixtures.json")
    manifest = load_manifest()
    skill = (ROOT / "authoring" / "SKILL_CURRENT.md").read_text(encoding="utf-8")
    validator = load_validator()
    checks: list[dict] = []
    skill_lower = skill.lower()

    def add(code: str, ok: bool, detail=""):
        checks.append({"code": code, "ok": bool(ok), "detail": detail})

    expected_contract = capabilities["contract_version"]
    package_const = schema["$defs"]["package"]["properties"]["schema_version"]["const"]
    add("contract-version-aligned", expected_contract == package_const == taxonomy["contract_version"] == fixtures["contract_version"], expected_contract)
    expected_baseline = capabilities["application_baseline"]
    skill_version = capabilities.get("authoring_skill_version")
    add("skill-declares-contract", expected_contract in skill and f"Learn-it {expected_baseline}" in skill and f"V{skill_version}" in skill, f"{expected_baseline}/V{skill_version}")

    stable_types = {name for name, row in capabilities["activity_types"].items() if row["status"] == "stable"}
    schema_types = {ref["$ref"].rsplit("/", 1)[-1] for ref in schema["$defs"]["activity"]["oneOf"]}
    runtime_types = {path.stem for path in (ROOT / "src" / "activities").glob("*.js")}
    add("activity-types-three-way", stable_types == schema_types == runtime_types, f"cap={sorted(stable_types)} schema={sorted(schema_types)} runtime={sorted(runtime_types)}")
    add("stable-types-proven", all(all(row.get(flag) is True for flag in ["imported", "persisted", "rendered", "interactive", "diagnosed", "tested"]) for row in capabilities["activity_types"].values()))
    add("experimental-not-default", all(row.get("status") == "stable" or not row.get("generated_by_default") for row in capabilities["pedagogical_fields"].values()))

    learning_capabilities = capabilities.get("learning_capabilities", {})
    spaced = learning_capabilities.get("spaced_review", {})
    add("spaced-review-runtime-owned", spaced.get("status") == "stable" and spaced.get("authoring_fields") == [] and spaced.get("schedule_owner") == "runtime" and "Ne jamais ajouter dans les kits" in skill)
    variety = learning_capabilities.get("pedagogical_variety", {})
    add("variety-runtime-owned", variety.get("status") == "stable" and variety.get("authoring_fields") == [] and variety.get("tested") is True and "Ne jamais ajouter au kit de seed" in skill)
    session_modes = learning_capabilities.get("session_modes", {})
    add("session-modes-runtime-owned", session_modes.get("status") == "stable" and session_modes.get("authoring_fields") == [] and session_modes.get("policy_owner") == "runtime" and session_modes.get("modes") == ["discovery", "training", "review", "validation", "diagnostic"] and session_modes.get("tested") is True)
    add("session-entry-guidance-runtime-owned", session_modes.get("entry_guidance_owner") == "runtime" and session_modes.get("learner_intents") == ["new-topic", "prior-knowledge", "continue-learning"] and "le kit ne doit contenir aucune instruction de collision ou de transaction" in skill_lower)
    add("skill-explains-mode-boundary", "révision espacée et modes de séance" in skill_lower and "champ `mode`" in skill_lower and "flashcards sont exclues des modes d’évaluation" in skill_lower)
    explainable = learning_capabilities.get("explainable_learning_evidence", {})
    add("explainable-evidence-runtime-owned", explainable.get("status") == "stable" and explainable.get("authoring_fields") == ["objective"] and explainable.get("evidence_owner") == "runtime" and explainable.get("tested") is True)
    add("explainable-evidence-no-false-score", "arbitrary_mastery_percentage" in explainable.get("forbidden_outputs", []) and explainable.get("readable_statuses") == ["not-started", "discovered", "in-progress", "fragile", "consolidated"])
    add("skill-explains-evidence-boundary", "pourcentage de maîtrise" in skill_lower and "résultat ou statut apprenant" in skill_lower and "preuve" in skill_lower)
    add("mode-ready-fixture-present", any(case.get("id") == "positive-mode-ready-course" and case.get("expected") == "pass" for case in fixtures.get("cases", [])))

    workflow = capabilities.get("import_workflow", {})
    add("import-workflow-stable", workflow.get("status") == "stable" and workflow.get("tested") is True)
    add("import-preview-no-write", workflow.get("preview_owner") == "runtime" and workflow.get("preview_writes_state") is False and "prévisualise sans écrire" in skill_lower)
    add("import-transactional", workflow.get("transactional_apply") is True and workflow.get("rollback_on_failure") is True and workflow.get("interrupted_transaction_recovery") is True and "transaction" in skill_lower and "état précédent est restauré" in skill_lower)
    add("import-multifile-collisions", workflow.get("multi_file") is True and workflow.get("collision_policies") == ["rename", "replace", "skip", "reject"] and all(word in skill_lower for word in ["renommer", "remplacer", "ignorer", "bloquer"]))
    add("import-builtins-protected", workflow.get("built_in_replacement_allowed") is False and "parcours natifs" in skill_lower)
    add("diagnostic-severities-aligned", workflow.get("diagnostic_severities") == ["blocker", "warning", "advice"] and all(word in skill_lower for word in ["blocage", "avertissement", "conseil"]))

    qcm_difficulty = set(schema["$defs"]["qcm"]["properties"]["difficulty"]["enum"])
    qcm_phase = set(schema["$defs"]["qcm"]["properties"]["learning_phase"]["enum"])
    qcm_role = set(schema["$defs"]["qcm"]["properties"]["assessment_role"]["enum"])
    asset_roles = set(schema["$defs"]["asset"]["properties"]["pedagogical_role"]["enum"])
    add("taxonomy-schema-aligned", qcm_difficulty == set(taxonomy["difficulty"]) and qcm_phase == set(taxonomy["learning_phase"]) and qcm_role == set(taxonomy["assessment_role"]) and asset_roles == set(taxonomy["pedagogical_role"]))

    manifest_contracts = {row["path"] for row in manifest.get("contracts", [])}
    expected_contract_files = {"contract/learnit-capabilities.json", "contract/learnit-import.schema.json", "contract/pedagogical-taxonomy.json"}
    add("manifest-publishes-contracts", manifest_contracts == expected_contract_files, str(sorted(manifest_contracts)))
    authoring_paths = set(manifest.get("authoring_pack", {}).get("paths", []))
    expected_authoring = expected_contract_files | {
        "authoring/SKILL_CURRENT.md",
        "authoring/contract-fixtures.json",
        "tools/validate_kit.py",
        "dev/authoring_alignment.py",
        "data/golden-kits/golden_nombres_complexes.json",
        "data/golden-kits/golden_signaux_electriques.json",
    }
    add("authoring-pack-minimal-complete", authoring_paths == expected_authoring, str(sorted(authoring_paths)))

    fixture_rows = []
    for case in fixtures["cases"]:
        report = validator.validate_payload(case["payload"])
        expected_ok = case["expected"] == "pass"
        codes = {item["code"] for item in report["errors"]}
        code_ok = all(code in codes for code in case.get("expected_codes", []))
        row_ok = report["ok"] == expected_ok and code_ok
        fixture_rows.append({"id": case["id"], "ok": row_ok, "expected": case["expected"], "actual": report["ok"], "codes": sorted(codes)})
    add("contract-fixtures", all(row["ok"] for row in fixture_rows), json.dumps(fixture_rows, ensure_ascii=False))

    diagnostic_rows = []
    for case in fixtures.get("diagnostic_cases", []):
        report = validator.validate_payload(case["payload"])
        findings = [*report.get("errors", []), *report.get("warnings", [])]
        code_to_severity = {item.get("code"): item.get("severity") for item in findings}
        expected_codes = case.get("expected_codes", [])
        expected_severity = case.get("expected_severity")
        row_ok = all(code_to_severity.get(code) == expected_severity for code in expected_codes)
        diagnostic_rows.append({"id": case["id"], "ok": row_ok, "expectedCodes": expected_codes, "expectedSeverity": expected_severity, "actual": code_to_severity})
    add("diagnostic-golden-fixtures", bool(diagnostic_rows) and all(row["ok"] for row in diagnostic_rows), json.dumps(diagnostic_rows, ensure_ascii=False))

    forbidden = re.compile(r"\b(?:TODO|DEBUG|undefined|NaN)\b|\[BLANK", re.I)
    authored_text = "\n".join((ROOT / rel).read_text(encoding="utf-8") for rel in expected_authoring if (ROOT / rel).suffix in {".md", ".json"})
    add("authoring-pack-no-visible-markers", not forbidden.search(authored_text))

    ok = all(item["ok"] for item in checks)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"schema": "learnit.rc659.skill_contract_sync.v1", "ok": ok, "gate": "SKILL_CONTRACT_SYNC", "checks": checks, "fixtures": fixture_rows, "diagnosticFixtures": diagnostic_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "passed": sum(row["ok"] for row in checks), "total": len(checks), "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
