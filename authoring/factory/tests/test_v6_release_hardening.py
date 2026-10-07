#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from authoring.factory import release_set, release_set_v6, reliability_v6, v6_gate
from authoring.v6 import validator_runtime

ZERO = "sha256:" + "0" * 64
DEFAULT_COMMIT = "1" * 40


def uid(n: int) -> str:
    return str(uuid.UUID(int=n, version=4))


def productive(seed: int = 100, media: bool = False) -> dict:
    value = {
        "activityLineageId": uid(seed),
        "activityRevisionId": uid(seed + 1),
        "activityRevisionDigest": ZERO,
        "objectiveIds": [uid(10)],
        "type": "productive",
        "prompt": "Calculez la valeur numérique demandée et indiquez votre résultat.",
        "explanation": "Le calcul attendu applique directement la relation explicitée par la source autorisée.",
        "difficulty": "medium",
        "learningPhase": "validation",
        "assessmentRole": "validation",
        "validationSlot": "A",
        "parts": [{"partId": uid(seed + 2), "label": "Valeur", "responseKind": "number"}],
        "scoring": {
            "aggregation": "all",
            "evaluators": [{
                "partId": uid(seed + 2),
                "kind": "numeric-tolerance",
                "expected": {"numerator": 4, "denominator": 1},
                "absoluteTolerance": {"numerator": 0, "denominator": 1},
            }],
        },
    }
    if media:
        value["media"] = [{"assetId": uid(900), "placement": "prompt", "display": "contained", "zoomable": True}]
    return value


def constructed(seed: int = 200, objective: int = 10) -> dict:
    return {
        "activityLineageId": uid(seed),
        "activityRevisionId": uid(seed + 1),
        "activityRevisionDigest": ZERO,
        "objectiveIds": [uid(objective)],
        "type": "constructed",
        "prompt": "Donnez la réponse attendue.",
        "explanation": "La réponse est explicitement justifiée par la source de cours.",
        "difficulty": "medium",
        "learningPhase": "validation",
        "assessmentRole": "validation",
        "validationSlot": "A",
        "acceptedResponses": ["4"],
    }


def base_course(activities: list[dict]) -> dict:
    return {
        "courseLineageId": uid(20),
        "courseRevisionId": uid(21),
        "courseRevisionDigest": ZERO,
        "title": "Cours principal",
        "estimatedMinutes": 20,
        "objectives": [{"objectiveId": uid(10), "label": "Résoudre une situation conforme à la source."}],
        "activities": activities,
    }


def make_kit(*, constructed_first: bool = False, constructed_later: bool = False, media: bool = False) -> dict:
    activities = [productive(media=media)]
    if constructed_first:
        activities.insert(0, constructed())
    courses = [base_course(activities)]
    if constructed_later:
        courses.append({
            "courseLineageId": uid(30),
            "courseRevisionId": uid(31),
            "courseRevisionDigest": ZERO,
            "title": "Cours secondaire",
            "estimatedMinutes": 10,
            "objectives": [{"objectiveId": uid(11), "label": "Vérifier une deuxième situation."}],
            "activities": [constructed(300, 11)],
        })
    kit = {
        "contract": "learnit.kit.v6",
        "packageLineageId": uid(1),
        "packageRevisionId": uid(2),
        "packageRevisionDigest": ZERO,
        "title": "Kit V6 de qualification",
        "versionLabel": "v6-test-r1",
        "language": "fr-FR",
        "courses": courses,
    }
    if media:
        kit["assets"] = [{
            "assetId": uid(900),
            "type": "image",
            "format": "svg",
            "alt": "Schéma diagonal à interpréter pour résoudre l'activité.",
            "pedagogicalRole": "diagram_to_interpret",
            "data": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0 L10 10"/></svg>',
        }]
    errors = validator_runtime.fill_new_digests(kit)
    if errors:
        raise AssertionError(errors)
    return kit


def brief() -> dict:
    return {"schema": "learnit.atlas.learner_brief.v1", "audience": "élève", "goal": "Maîtriser la relation de la source", "language": "fr-FR", "timeBudgetMinutes": 30}


def manifest(source_raw: bytes, *, visual_required: bool = False, hidden_role_a: bool = False) -> dict:
    return {
        "schema": v6_gate.SOURCE_MANIFEST_SCHEMA,
        "roleB": [{
            "sourceId": "course-source", "bytes": len(source_raw), "sha256": v6_gate.sha256(source_raw),
            "authorized": True, "provenance": "fixture://authorized/course-source", "kind": "provided",
            "admittedAtAuthoring": True, "claimIds": ["claim.answer", "claim.visual"],
        }],
        "roleA": ([{"url": "https://example.edu/reference", "authorized": True, "supplemental": True, "usedAsSourceTruth": True}] if hidden_role_a else []),
        "visualRequirement": {"required": visual_required, "basis": "Le besoin visuel est déclaré explicitement par l'admission de source."},
    }


def review(context: dict, *, answer_hold: bool = False, hint_hold: bool = False, productive_check: str = "pass", visual_check: str = "not_applicable", role_b_check: str = "pass", bad_claim: bool = False) -> dict:
    evidence = [{"sourceId": "course-source", "claimId": "claim.missing" if bad_claim else "claim.answer", "locator": "fixture:1"}]
    dims = {}
    for name in v6_gate.CORE_DIMENSIONS:
        dims[name] = {"status": "hold" if answer_hold and name == "answerCorrectness" else "pass", "summary": f"{name} vérifié sur la source autorisée.", "evidence": copy.deepcopy(evidence)}
    checks = {
        "reviewerSkill": "pass", "hintProgression": "pass", "hintAnswerLeak": "hold" if hint_hold else "pass",
        "roleAReferenceUsefulness": "pass", "roleBClaimMapping": role_b_check,
        "productiveCorrectness": productive_check, "visualAdequacy": visual_check,
    }
    semantic_hold = answer_hold or hint_hold or role_b_check == "hold" or productive_check == "hold" or visual_check == "hold"
    return {
        "schema": v6_gate.SEMANTIC_REVIEW_SCHEMA, "profile": v6_gate.SEMANTIC_REVIEW_PROFILE,
        "target": {key: context[key] for key in ("contextDigest", "kitSha256", "sourceSetDigest", "briefSha256")},
        "independence": {"authorScratchpadSeen": False, "authorActiveContextReused": False},
        "dimensions": dims, "findings": [], "limitations": [], "v6Checks": checks,
        "verdict": v6_gate.SEMANTIC_HOLD if semantic_hold else v6_gate.SEMANTIC_PASS,
    }


class Fixture:
    def __init__(self, root: Path, kit: dict, *, visual_required: bool = False, hidden_role_a: bool = False, review_kwargs: dict | None = None):
        self.kit = root / "kit.json"; self.brief = root / "brief.json"; self.source = root / "source.txt"
        self.source_manifest = root / "source-manifest.json"; self.review = root / "review.json"; self.run = root / "run.json"; self.release = root / "release.zip"
        source_raw = "La source autorisée établit la valeur attendue à 4 et décrit le schéma utile.".encode("utf-8")
        self.kit.write_text(json.dumps(kit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.brief.write_text(json.dumps(brief(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.source.write_bytes(source_raw)
        source_value = manifest(source_raw, visual_required=visual_required, hidden_role_a=hidden_role_a)
        self.source_manifest.write_text(json.dumps(source_value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        normalized = v6_gate.validate_source_manifest(source_value, self.source_manifest.read_bytes(), {"course-source": source_raw})
        context = v6_gate.build_context(self.kit.read_bytes(), self.brief.read_bytes(), normalized)
        review_value = review(context, **(review_kwargs or {}))
        self.review.write_text(json.dumps(review_value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @property
    def sources(self) -> list[str]: return [f"course-source={self.source}"]
    def gate(self, commit: str = DEFAULT_COMMIT) -> dict: return v6_gate.run_gate(self.kit, self.brief, self.review, self.source_manifest, self.sources, commit)
    def run_value(self, commit: str = DEFAULT_COMMIT) -> dict:
        value = reliability_v6.build_run(self.kit, self.brief, self.review, self.source_manifest, self.sources, commit)
        self.run.write_bytes(v6_gate.canonical(value) + b"\n"); return value


class V6ReleaseHardeningTests(unittest.TestCase):
    def test_exact_historical_identities_and_v1_wrapped_bytes(self):
        identities = validator_runtime.assert_exact_identities()
        self.assertEqual("0b61612ce711a5a6bd0e278385204188f130818b", identities["schemaBlob"])
        self.assertEqual("1650d550810c50b5fdf64d14cbff42c9c94c4202", identities["validatorBlob"])
        root = Path(__file__).resolve().parents[3]
        self.assertEqual("285c037b5e430ca2f75d61583d9d22c23073f7f7", validator_runtime.git_blob_sha((root / "authoring/factory/_reliability_v1.py").read_bytes()))
        self.assertEqual("10be3727243e8dc66d10c1a11731c7f61ed2c8e8", validator_runtime.git_blob_sha((root / "authoring/factory/_release_set_v1.py").read_bytes()))

    def test_positive_productive_chain_binds_exact_pr_head(self):
        commit = os.environ.get("IMPLEMENTATION_COMMIT", DEFAULT_COMMIT)
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), make_kit())
            self.assertEqual(v6_gate.FACTORY_PASS, f.gate(commit)["verdict"])
            run = f.run_value(commit); self.assertEqual("PASS", reliability_v6.decision_class(reliability_v6.verify_run(run)))
            built = release_set_v6.build_release_archive([f"{f.run}={f.kit}"], f.release)
            self.assertEqual(commit, built["factoryAuthority"])
            verified = release_set_v6.verify_release_archive(f.release)
            self.assertEqual(commit, verified["manifest"]["factoryAuthority"])

    def test_constructed_first_course_holds_exact_reason(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), make_kit(constructed_first=True)); gate = f.gate()
            self.assertEqual(v6_gate.FACTORY_HOLD, gate["verdict"]); self.assertIn(v6_gate.CONSTRUCTED_REASON, gate["reasons"])

    def test_constructed_later_course_cannot_escape_scan(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), make_kit(constructed_later=True)); gate = f.gate()
            self.assertEqual(1, gate["productionPolicy"]["counts"]["constructed"]); self.assertIn(v6_gate.CONSTRUCTED_REASON, gate["reasons"])

    def test_validation_must_target_exactly_one_objective(self):
        kit = make_kit(); kit["courses"][0]["objectives"].append({"objectiveId": uid(12), "label": "Deuxième objectif"})
        a = kit["courses"][0]["activities"][0]; a["objectiveIds"] = [uid(10), uid(12)]
        a["activityRevisionDigest"] = ZERO; kit["courses"][0]["courseRevisionDigest"] = ZERO; kit["packageRevisionDigest"] = ZERO
        self.assertFalse(validator_runtime.validate_document(kit).ok)

    def test_wrong_productive_evaluator_family_is_rejected(self):
        kit = make_kit(); a = kit["courses"][0]["activities"][0]
        a["scoring"]["evaluators"][0] = {"partId": a["parts"][0]["partId"], "kind": "required-concepts", "requiredConceptGroups": [["valeur"]]}
        a["activityRevisionDigest"] = ZERO; kit["courses"][0]["courseRevisionDigest"] = ZERO; kit["packageRevisionDigest"] = ZERO
        self.assertFalse(validator_runtime.validate_document(kit).ok)

    def test_non_validation_slot_is_rejected(self):
        kit = make_kit(); a = kit["courses"][0]["activities"][0]; a["assessmentRole"] = "practice"; a["learningPhase"] = "application"
        a["activityRevisionDigest"] = ZERO; kit["courses"][0]["courseRevisionDigest"] = ZERO; kit["packageRevisionDigest"] = ZERO
        self.assertFalse(validator_runtime.validate_document(kit).ok)

    def test_missing_productive_scoring_holds_canonical_gate(self):
        kit = make_kit(); del kit["courses"][0]["activities"][0]["scoring"]
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), kit); self.assertIn("CANONICAL_V6_INVALID", f.gate()["reasons"])

    def test_hint_answer_leak_review_holds(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), make_kit(), review_kwargs={"hint_hold": True}); self.assertIn("V6_CHECK_HOLD:hintAnswerLeak", f.gate()["reasons"])

    def test_role_a_cannot_be_hidden_source_truth(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), make_kit(), hidden_role_a=True); self.assertTrue(any(x.startswith("ROLE_A_HIDDEN_SOURCE_TRUTH:") for x in f.gate()["reasons"]))

    def test_role_b_claim_mapping_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), make_kit(), review_kwargs={"bad_claim": True})
            with self.assertRaises(v6_gate.V6FactoryInputError): f.gate()

    def test_text_only_cannot_bypass_declared_visual_requirement(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), make_kit(), visual_required=True, review_kwargs={"visual_check": "pass"})
            self.assertIn("VISUAL_REQUIRED_MEDIA_ABSENT", f.gate()["reasons"])

    def test_visual_requirement_passes_with_embedded_media_and_review(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), make_kit(media=True), visual_required=True, review_kwargs={"visual_check": "pass"})
            self.assertEqual(v6_gate.FACTORY_PASS, f.gate()["verdict"])

    def test_cross_version_release_admission_is_closed(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td), make_kit()); run = f.run_value(); raw = v6_gate.canonical(run)
            with self.assertRaises(release_set_v6.V6ReleaseSetInputError): release_set_v6.entry_from_bytes(b'{"schema":"learnit.atlas.factory_run.v1"}', f.kit.read_bytes(), "v1")
            with self.assertRaises(Exception): release_set.entry_from_bytes(raw, f.kit.read_bytes(), "v6-into-v1")


if __name__ == "__main__": unittest.main(verbosity=2)