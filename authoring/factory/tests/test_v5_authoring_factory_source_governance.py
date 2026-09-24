#!/usr/bin/env python3
"""Qualification oracle for ATLAS-WP-056 V5 authoring/Factory/source governance."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock

from authoring.factory import factory_gate as factory
from authoring.factory import v5_factory_gate as v5_factory
from authoring.factory import v5_web_admission as web
from authoring.v5 import authoring_policy
from authoring.v5.tests.test_validate_v5 import (
    activity,
    make_valid_v5,
    refresh_v5,
    validate_v5,
)

CHECKED_AT = "2026-09-24T17:00:00Z"
PUBLIC_IP = "93.184.216.34"


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fake_pass_admission(
    url: str,
    body: bytes = b"reference content",
    *,
    purpose: str = "learner-reference",
) -> dict:
    def resolver(host: str, port: int):
        return [PUBLIC_IP]

    def transport(current: str, ips, connect_timeout: float, read_timeout: float, max_bytes: int):
        return web.Response(200, {"content-type": "text/html; charset=utf-8"}, body)

    record = web.admit(
        url,
        purpose=purpose,
        checked_at=CHECKED_AT,
        resolver=resolver,
        transport=transport,
    )
    web.verify(record)
    return record


def review_for(
    context: dict,
    *,
    hold_dimension: str | None = None,
    hold_v5_check: str | None = None,
) -> dict:
    source_id = context["sources"][0]["sourceId"]
    dimensions = {}
    for name in factory.REQUIRED_DIMENSIONS:
        evidence = []
        if name in factory.EVIDENCE_REQUIRED_DIMENSIONS:
            evidence = [{
                "sourceId": source_id,
                "locator": "fixture:1",
                "basis": f"Exact Role B source evidence checked for {name}.",
            }]
        dimensions[name] = {
            "status": "hold" if name == hold_dimension else "pass",
            "summary": f"Independent {name} review completed.",
            "evidence": evidence,
        }
    checks = {
        "reviewerSkill": v5_factory.REVIEWER_SKILL,
        "hintProgression": "pass",
        "hintAnswerLeak": "pass",
        "roleAReferenceUsefulness": "pass",
        "roleBClaimMapping": "pass",
    }
    if hold_v5_check:
        checks[hold_v5_check] = "hold"
    has_hold = hold_dimension is not None or hold_v5_check is not None
    return {
        "schema": v5_factory.REVIEW_SCHEMA,
        "profile": v5_factory.REVIEW_PROFILE,
        "target": {
            "contextDigest": context["contextDigest"],
            "kitSha256": context["kitSha256"],
            "sourceSetDigest": context["sourceSetDigest"],
            "briefSha256": context["briefSha256"],
        },
        "independence": {
            "authorScratchpadSeen": False,
            "authorActiveContextReused": False,
        },
        "dimensions": dimensions,
        "findings": [],
        "limitations": [],
        "v5Checks": checks,
        "verdict": v5_factory.SEMANTIC_HOLD if has_hold else v5_factory.SEMANTIC_PASS,
    }


def role_b_manifest(source: Path, source_id: str = "source", *, allowed: bool = True) -> dict:
    data = source.read_bytes()
    return {
        "schema": v5_factory.ROLE_B_SCHEMA,
        "profile": v5_factory.ROLE_B_PROFILE,
        "sources": [{
            "sourceId": source_id,
            "authorization": {
                "allowed": allowed,
                "basis": "synthetic-test-fixture",
                "provenance": "test-owned-local-source",
            },
            "origin": {
                "kind": "local-file",
                "submittedUrl": None,
                "finalUrl": None,
                "checkedAt": CHECKED_AT,
                "contentType": "text/plain",
                "webAdmissionId": None,
            },
            "capture": {
                "bytes": len(data),
                "sha256": factory.sha256_bytes(data),
            },
            "claimMappings": [{
                "kitPath": "$.courses[0].objectives[0]",
                "basis": "The synthetic source states the bounded conservation relation used by the fixture.",
            }],
        }],
    }


class Workspace:
    def __init__(self, root: Path, package: dict | None = None):
        self.root = root
        self.kit = root / "candidate-v5.json"
        self.brief = root / "brief.json"
        self.source = root / "source.txt"
        self.review = root / "review.json"
        self.role_b = root / "role-b.json"
        self.source.write_text(
            "The total remains conserved in the bounded system when no contribution enters or leaves.\n",
            encoding="utf-8",
        )
        self.package = package or make_valid_v5()
        self.write_package(self.package)
        write_json(self.brief, {
            "schema": factory.BRIEF_SCHEMA,
            "audience": "Student V0.1 learner",
            "goal": "Understand and apply the bounded source relation",
            "language": "en",
            "timeBudgetMinutes": 30,
        })
        self.write_role_b()
        self.write_review()

    @property
    def sources(self) -> list[str]:
        return [f"source={self.source}"]

    def context(self) -> dict:
        return factory.build_context(self.kit, self.brief, self.sources)

    def write_package(self, package: dict) -> None:
        self.package = package
        self.kit.write_text(
            json.dumps(package, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_role_b(self, *, allowed: bool = True) -> None:
        write_json(self.role_b, role_b_manifest(self.source, allowed=allowed))

    def write_review(
        self,
        *,
        hold_dimension: str | None = None,
        hold_v5_check: str | None = None,
    ) -> None:
        write_json(
            self.review,
            review_for(
                self.context(),
                hold_dimension=hold_dimension,
                hold_v5_check=hold_v5_check,
            ),
        )

    def gate(
        self,
        *,
        role_a: list[Path] | None = None,
        role_b_web: list[Path] | None = None,
        review: Path | None = None,
    ):
        return v5_factory.run_gate(
            self.kit,
            self.brief,
            review or self.review,
            self.sources,
            role_a or [],
            self.role_b,
            role_b_web or [],
        )


class WebAdmissionTests(unittest.TestCase):
    def test_injected_public_https_admission_has_exact_evidence_without_network(self):
        with (
            mock.patch.object(socket, "getaddrinfo", side_effect=AssertionError("public DNS attempted")),
            mock.patch.object(socket, "create_connection", side_effect=AssertionError("socket attempted")),
        ):
            record = fake_pass_admission("https://example.org/reference")
        self.assertEqual(web.PASS, record["decision"]["verdict"])
        self.assertEqual("https://example.org/reference", record["submittedUrl"])
        self.assertEqual("https://example.org/reference", record["finalUrl"])
        self.assertEqual(0, record["redirectCount"])
        self.assertEqual("public-anonymous", record["accessClassification"])
        self.assertEqual(
            factory.sha256_bytes(b"reference content"),
            record["content"]["sha256"],
        )

    def test_unsafe_initial_urls_and_non_public_destinations_hold(self):
        cases = [
            ("http://example.org/x", lambda host, port: [PUBLIC_IP]),
            ("https://user:secret@example.org/x", lambda host, port: [PUBLIC_IP]),
            ("https://example.org/x", lambda host, port: ["127.0.0.1"]),
            ("https://example.org/x", lambda host, port: ["10.0.0.5"]),
            ("https://example.org/x", lambda host, port: ["169.254.1.2"]),
            ("https://example.org/x", lambda host, port: ["224.0.0.1"]),
        ]
        for url, resolver in cases:
            with self.subTest(url=url, result=resolver("x", 443)[0]):
                record = web.admit(
                    url,
                    purpose="learner-reference",
                    checked_at=CHECKED_AT,
                    resolver=resolver,
                    transport=lambda *args: self.fail("unsafe URL reached transport"),
                )
                self.assertEqual(web.HOLD, record["decision"]["verdict"])

    def test_redirect_http_private_and_sixth_hop_hold(self):
        def public_resolver(host: str, port: int):
            if host in {"127.0.0.1", "localhost"}:
                return ["127.0.0.1"]
            return [PUBLIC_IP]

        def private_redirect(url, ips, *args):
            return web.Response(302, {"location": "https://127.0.0.1/secret"}, b"")

        private = web.admit(
            "https://example.org/start",
            purpose="learner-reference",
            checked_at=CHECKED_AT,
            resolver=public_resolver,
            transport=private_redirect,
        )
        self.assertEqual(web.HOLD, private["decision"]["verdict"])

        def downgrade(url, ips, *args):
            return web.Response(302, {"location": "http://example.org/plain"}, b"")

        http = web.admit(
            "https://example.org/start",
            purpose="learner-reference",
            checked_at=CHECKED_AT,
            resolver=lambda h, p: [PUBLIC_IP],
            transport=downgrade,
        )
        self.assertEqual(web.HOLD, http["decision"]["verdict"])

        def endless(url, ips, *args):
            path = url.rsplit("/", 1)[-1]
            n = int(path) if path.isdigit() else 0
            return web.Response(302, {"location": f"https://example.org/{n + 1}"}, b"")

        bounded = web.admit(
            "https://example.org/0",
            purpose="learner-reference",
            checked_at=CHECKED_AT,
            resolver=lambda h, p: [PUBLIC_IP],
            transport=endless,
        )
        self.assertEqual(web.HOLD, bounded["decision"]["verdict"])
        self.assertEqual(5, bounded["redirectCount"])

    def test_404_410_auth_executable_and_download_only_hold(self):
        cases = [
            web.Response(404, {"content-type": "text/html"}, b"missing"),
            web.Response(410, {"content-type": "text/html"}, b"gone"),
            web.Response(401, {"content-type": "text/html"}, b"auth"),
            web.Response(403, {"content-type": "text/html"}, b"forbidden"),
            web.Response(200, {"content-type": "application/x-executable"}, b"binary"),
            web.Response(200, {"content-type": "application/octet-stream"}, b"download"),
            web.Response(
                200,
                {"content-type": "text/plain", "content-disposition": "attachment; filename=x.txt"},
                b"download",
            ),
        ]
        for response in cases:
            record = web.admit(
                "https://example.org/resource",
                purpose="learner-reference",
                checked_at=CHECKED_AT,
                resolver=lambda h, p: [PUBLIC_IP],
                transport=lambda *args, response=response: response,
            )
            self.assertEqual(web.HOLD, record["decision"]["verdict"], response)


class V5FactoryGovernanceTests(unittest.TestCase):
    def test_zero_hints_and_references_has_no_artificial_requirement_and_factory_passes(self):
        with tempfile.TemporaryDirectory() as td:
            w = Workspace(Path(td))
            evidence = w.gate()
            self.assertEqual("PASS_AI_KIT_FACTORY_V5_R2", evidence["verdict"], evidence)
            self.assertEqual(0, evidence["authoringPolicy"]["hintCount"])
            self.assertEqual([], evidence["roleAReferences"]["requiredUrls"])

    def test_useful_progressive_hints_pass_without_scoring_change(self):
        with tempfile.TemporaryDirectory() as td:
            package = make_valid_v5()
            qcm = activity(package, "qcm")
            scoring = copy.deepcopy({
                "choices": qcm["choices"],
                "correctChoiceId": qcm["correctChoiceId"],
            })
            qcm["hints"] = [
                "Recall the source assumptions before comparing the alternatives.",
                "Check which alternative preserves the same bounded quantity.",
            ]
            package = refresh_v5(package)
            self.assertEqual(
                scoring,
                {
                    "choices": activity(package, "qcm")["choices"],
                    "correctChoiceId": activity(package, "qcm")["correctChoiceId"],
                },
            )
            w = Workspace(Path(td), package)
            self.assertEqual(
                authoring_policy.PASS,
                authoring_policy.analyze(package)["verdict"],
            )
            self.assertEqual("PASS_AI_KIT_FACTORY_V5_R2", w.gate()["verdict"])

    def test_obvious_answer_revealing_hint_cannot_be_semantically_certified(self):
        with tempfile.TemporaryDirectory() as td:
            package = make_valid_v5()
            qcm = activity(package, "qcm")
            correct = next(
                choice["label"]
                for choice in qcm["choices"]
                if choice["choiceId"] == qcm["correctChoiceId"]
            )
            qcm["hints"] = [f"Choose this answer: {correct}"]
            package = refresh_v5(package)
            w = Workspace(Path(td), package)
            self.assertEqual(
                authoring_policy.HOLD,
                authoring_policy.analyze(package)["verdict"],
            )
            evidence = w.gate()
            self.assertEqual("HOLD_V5_FACTORY_AUTHORING_POLICY", evidence["verdict"], evidence)

    def test_semantic_reviewer_answer_leak_hold_blocks_even_when_regex_does_not(self):
        with tempfile.TemporaryDirectory() as td:
            package = make_valid_v5()
            activity(package, "qcm")["hints"] = [
                "Use the first law to decide between the two statements."
            ]
            package = refresh_v5(package)
            w = Workspace(Path(td), package)
            w.write_review(hold_v5_check="hintAnswerLeak")
            evidence = w.gate()
            self.assertEqual("HOLD_V5_FACTORY_SEMANTIC_REVIEW", evidence["verdict"], evidence)

    def test_unsupported_external_fact_semantic_hold_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            w = Workspace(Path(td))
            w.write_review(hold_dimension="sourceFidelity")
            evidence = w.gate()
            self.assertEqual("HOLD_V5_FACTORY_SEMANTIC_REVIEW", evidence["verdict"], evidence)

    def test_role_a_exact_external_admission_and_learner_shape(self):
        with tempfile.TemporaryDirectory() as td:
            package = make_valid_v5()
            ref = {
                "url": "https://example.org/reference",
                "label": "Reference",
                "hook": "A useful optional explanation.",
            }
            activity(package, "lesson")["references"] = [ref]
            package = refresh_v5(package)
            w = Workspace(Path(td), package)
            admission = Path(td) / "role-a.json"
            write_json(admission, fake_pass_admission(ref["url"]))
            w.write_review()
            evidence = w.gate(role_a=[admission])
            self.assertEqual("PASS_AI_KIT_FACTORY_V5_R2", evidence["verdict"], evidence)
            self.assertEqual(
                {"url", "label", "hook"},
                set(activity(package, "lesson")["references"][0]),
            )

    def test_role_a_missing_or_mismatched_admission_holds(self):
        with tempfile.TemporaryDirectory() as td:
            package = make_valid_v5()
            url = "https://example.org/reference"
            activity(package, "lesson")["references"] = [{
                "url": url,
                "label": "Reference",
                "hook": "Optional.",
            }]
            package = refresh_v5(package)
            w = Workspace(Path(td), package)
            self.assertEqual(
                "HOLD_V5_FACTORY_ROLE_A_ADMISSION",
                w.gate()["verdict"],
            )
            wrong = Path(td) / "wrong.json"
            write_json(wrong, fake_pass_admission("https://example.org/other"))
            self.assertEqual(
                "HOLD_V5_FACTORY_ROLE_A_ADMISSION",
                w.gate(role_a=[wrong])["verdict"],
            )

    def test_role_b_source_set_exact_bytes_authorization_and_claim_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            w = Workspace(Path(td))
            evidence = w.gate()
            self.assertEqual(v5_factory.ROLE_B_PASS, evidence["roleBSources"]["verdict"])
            self.assertEqual(
                evidence["context"]["sourceSetDigest"],
                evidence["roleBSources"]["sourceSetDigest"],
            )
            write_json(w.role_b, role_b_manifest(w.source, allowed=False))
            self.assertEqual(
                "HOLD_V5_FACTORY_ROLE_B_SOURCE_GOVERNANCE",
                w.gate()["verdict"],
            )

    def test_web_role_b_requires_matching_safe_admission_and_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            w = Workspace(Path(td))
            body = b"Exact admitted Web source bytes\n"
            w.source.write_bytes(body)
            url = "https://example.org/source"
            admission_record = fake_pass_admission(
                url,
                body,
                purpose="authoring-source",
            )
            admission = Path(td) / "role-b-web-admission.json"
            write_json(admission, admission_record)
            manifest = role_b_manifest(w.source)
            manifest["sources"][0]["origin"] = {
                "kind": "web",
                "submittedUrl": url,
                "finalUrl": url,
                "checkedAt": CHECKED_AT,
                "contentType": "text/html",
                "webAdmissionId": admission_record["admissionId"],
            }
            write_json(w.role_b, manifest)
            w.write_review()
            evidence = w.gate(role_b_web=[admission])
            self.assertEqual("PASS_AI_KIT_FACTORY_V5_R2", evidence["verdict"], evidence)

            drifted = copy.deepcopy(admission_record)
            drifted["content"] = {
                "bytes": 1,
                "sha256": factory.sha256_bytes(b"x"),
            }
            drifted["stableIdentifier"] = {
                "kind": "content-sha256",
                "value": drifted["content"]["sha256"],
            }
            core = {k: v for k, v in drifted.items() if k != "admissionId"}
            drifted["admissionId"] = web.digest(core)
            bad = Path(td) / "role-b-web-bad.json"
            write_json(bad, drifted)
            manifest["sources"][0]["origin"]["webAdmissionId"] = drifted["admissionId"]
            write_json(w.role_b, manifest)
            self.assertEqual(
                "HOLD_V5_FACTORY_ROLE_B_SOURCE_GOVERNANCE",
                w.gate(role_b_web=[bad])["verdict"],
            )

    def test_role_b_missing_from_source_set_holds(self):
        with tempfile.TemporaryDirectory() as td:
            w = Workspace(Path(td))
            manifest = role_b_manifest(w.source)
            manifest["sources"][0]["sourceId"] = "unbound-source"
            write_json(w.role_b, manifest)
            self.assertEqual(
                "HOLD_V5_FACTORY_ROLE_B_SOURCE_GOVERNANCE",
                w.gate()["verdict"],
            )

    def test_one_byte_role_b_drift_rotates_source_and_context_and_stales_review(self):
        with tempfile.TemporaryDirectory() as td:
            w = Workspace(Path(td))
            old = w.context()
            old_review = copy.deepcopy(load_json(w.review))
            w.source.write_bytes(w.source.read_bytes() + b"X")
            w.write_role_b()
            new = w.context()
            self.assertNotEqual(old["sourceSetDigest"], new["sourceSetDigest"])
            self.assertNotEqual(old["contextDigest"], new["contextDigest"])
            write_json(w.review, old_review)
            evidence = w.gate()
            self.assertEqual("HOLD_V5_FACTORY_REVIEW_BINDING", evidence["verdict"], evidence)

    def test_exact_kit_byte_drift_stales_review_without_v5_to_v4_conversion(self):
        with tempfile.TemporaryDirectory() as td:
            w = Workspace(Path(td))
            old_review = copy.deepcopy(load_json(w.review))
            self.assertEqual("learnit.kit.v5", load_json(w.kit)["contract"])
            w.kit.write_bytes(w.kit.read_bytes() + b" \n")
            write_json(w.review, old_review)
            evidence = w.gate()
            self.assertEqual("HOLD_V5_FACTORY_REVIEW_BINDING", evidence["verdict"], evidence)
            self.assertEqual("learnit.kit.v5", load_json(w.kit)["contract"])

    def test_role_a_only_reference_change_keeps_source_set_but_stales_exact_kit_review(self):
        with tempfile.TemporaryDirectory() as td:
            package = make_valid_v5()
            activity(package, "lesson")["references"] = [{
                "url": "https://example.org/a",
                "label": "A",
                "hook": "Optional A",
            }]
            package = refresh_v5(package)
            w = Workspace(Path(td), package)
            old_context = w.context()
            old_review = copy.deepcopy(load_json(w.review))

            changed = copy.deepcopy(package)
            activity(changed, "lesson")["references"][0]["url"] = "https://example.org/b"
            changed = refresh_v5(changed)
            w.write_package(changed)
            b = Path(td) / "b.json"
            write_json(b, fake_pass_admission("https://example.org/b"))
            new_context = w.context()
            self.assertEqual(
                old_context["sourceSetDigest"],
                new_context["sourceSetDigest"],
            )
            self.assertNotEqual(old_context["kitSha256"], new_context["kitSha256"])
            self.assertNotEqual(old_context["contextDigest"], new_context["contextDigest"])
            write_json(w.review, old_review)
            evidence = w.gate(role_a=[b])
            self.assertEqual("HOLD_V5_FACTORY_REVIEW_BINDING", evidence["verdict"], evidence)

    def test_remote_media_still_fails_frozen_v5_authority(self):
        package = make_valid_v5()
        package["assets"][0]["format"] = "png"
        package["assets"][0]["data"] = "https://example.org/image.png"
        report = validate_v5(refresh_v5(package))
        self.assertFalse(report.ok)
        self.assertTrue(
            any("remote/active media" in error for error in report.errors),
            report.errors,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
