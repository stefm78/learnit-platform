#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/learnit-next"
FIXTURE = APP / "tests/fixtures/atlas_v3_constructed.json"
MANIFEST = APP / "source_manifest.json"


def canonical(value, *, omit_root_key: str | None = None, root: bool = True) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        import unicodedata
        return json.dumps(unicodedata.normalize("NFC", value), ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(canonical(item, omit_root_key=omit_root_key, root=False) for item in value) + "]"
    if isinstance(value, dict):
        import unicodedata
        normalized: dict[str, str] = {}
        for original in value:
            if root and original == omit_root_key:
                continue
            key = unicodedata.normalize("NFC", original)
            if key in normalized:
                raise ValueError("Object keys collide after NFC normalization")
            normalized[key] = original
        parts = []
        for key in sorted(normalized, key=lambda item: [ord(char) for char in item]):
            original = normalized[key]
            parts.append(
                json.dumps(key, ensure_ascii=False, separators=(",", ":"))
                + ":"
                + canonical(value[original], omit_root_key=omit_root_key, root=False)
            )
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"Unsupported canonical JSON value: {type(value)!r}")


def digest(value, field: str) -> str:
    payload = canonical(value, omit_root_key=field).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def materialize_sources(target: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in manifest["workingFiles"]:
        rel = item["path"]
        if not rel.startswith("apps/learnit-next/src/"):
            continue
        destination = target / rel.removeprefix("apps/learnit-next/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = ROOT / rel
        if source.exists():
            destination.write_bytes(source.read_bytes())
            continue
        fingerprint = item["fingerprint"]
        if fingerprint.get("kind") != "git-blob-sha1":
            raise AssertionError(f"Cannot materialize {rel}: {fingerprint}")
        blob = subprocess.check_output(
            ["git", "cat-file", "blob", fingerprint["value"]],
            cwd=ROOT,
        )
        destination.write_bytes(blob)


class ConstructedResponseQualification(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_has_real_canonical_digests(self) -> None:
        package = self.fixture
        self.assertEqual(package["contract"], "learnit.kit.v3")
        self.assertEqual(len(package["courses"]), 1)
        course = package["courses"][0]
        self.assertGreaterEqual(len(course["activities"]), 2)
        for activity in course["activities"]:
            self.assertEqual(activity["type"], "constructed")
            self.assertTrue(activity["acceptedResponses"])
            self.assertEqual(
                activity["activityRevisionDigest"],
                digest(activity, "activityRevisionDigest"),
            )
        self.assertEqual(course["courseRevisionDigest"], digest(course, "courseRevisionDigest"))
        self.assertEqual(package["packageRevisionDigest"], digest(package, "packageRevisionDigest"))

    def test_v3_runtime_learning_and_secret_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnit-v3-constructed-") as work:
            sandbox = Path(work) / "app"
            sandbox.mkdir(parents=True)
            materialize_sources(sandbox)
            (sandbox / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
            fixture_path = sandbox / "fixture.json"
            fixture_path.write_text(json.dumps(self.fixture, ensure_ascii=False), encoding="utf-8")
            script = sandbox / "qualify.mjs"
            script.write_text(textwrap.dedent(r'''
                import fs from 'node:fs';
                import { webcrypto } from 'node:crypto';
                globalThis.crypto ??= webcrypto;

                import { validatePackageV3Object } from './src/core/contract.js';
                import { evaluateAnswer } from './src/core/session.js';
                import { createAtlasCompatibleImportService } from './src/integration/atlas/import_adapter.js';
                import { projectAtlasActivityPresentation } from './src/integration/atlas/session.js';
                import { readAtlasActivityResponse, renderAtlasActivityMarkup } from './src/ui/render.js';

                const assert = (value, message) => {
                  if (!value) throw new Error(message);
                };
                const kit = JSON.parse(fs.readFileSync('./fixture.json', 'utf8'));
                const contract = await validatePackageV3Object(kit);
                assert(contract.ok, `V3 contract failed: ${JSON.stringify(contract.errors)}`);
                assert(contract.contractVersion === 'learnit.kit.v3', 'V3 contract identity missing');

                const activity = kit.courses[0].activities[0];
                const canonical = evaluateAnswer(activity, { text: '  e\u0301nergie\t  lumineuse\n' });
                assert(canonical.correct === true, 'NFC/Unicode-whitespace canonical match failed');
                assert(canonical.normalized.text === 'énergie lumineuse', 'constructed response was not canonically persisted');
                assert(evaluateAnswer(activity, { text: 'Énergie lumineuse' }).correct === false, 'comparison must remain case-sensitive');

                let blankRejected = false;
                try { evaluateAnswer(activity, { text: ' \t\n ' }); }
                catch (error) { blankRejected = error.code === 'constructed_text_required'; }
                assert(blankRejected, 'canonical blank response must fail before scoring');

                let longRejected = false;
                try { evaluateAnswer(activity, { text: 'x'.repeat(4001) }); }
                catch (error) { longRejected = error.code === 'constructed_text_too_long'; }
                assert(longRejected, '>4000 character response must fail before scoring');

                const presentation = projectAtlasActivityPresentation(activity);
                assert(JSON.stringify(Object.keys(presentation).sort()) === JSON.stringify(['prompt', 'type']), 'learner presentation contains extra fields');
                const projected = JSON.stringify(presentation);
                for (const forbidden of ['acceptedResponses', 'acceptedValues', 'evaluator', 'rubric', 'correctChoiceId', 'answers', 'scoringRuleId']) {
                  assert(!projected.includes(forbidden), `secret leaked in ActivityPresentation: ${forbidden}`);
                }

                const markup = renderAtlasActivityMarkup(presentation);
                assert(markup.includes('<textarea'), 'constructed textarea is missing');
                assert(markup.includes('maxlength="4000"'), 'textarea bound is missing');
                assert(!markup.includes('énergie lumineuse'), 'accepted response leaked into learner markup');

                const fakeContainer = {
                  querySelector(selector) {
                    if (selector === '[data-atlas-constructed-response="true"]') return { value: 'énergie lumineuse' };
                    return null;
                  },
                };
                const raw = readAtlasActivityResponse(fakeContainer, presentation);
                assert(raw.text === 'énergie lumineuse', 'UI raw response shape is not {text}');
                assert(evaluateAnswer(activity, raw).correct === true, 'UI response does not round-trip through Learning evaluation');

                const storage = {
                  committed: null,
                  async getRevisionDigestIndex() { return new Map(); },
                  async commitImport(plan) { this.committed = plan; },
                };
                const forbiddenBase = new Proxy({}, {
                  get(_target, name) {
                    return () => { throw new Error(`V3 incorrectly delegated to legacy base: ${String(name)}`); };
                  },
                });
                const service = createAtlasCompatibleImportService(storage, forbiddenBase);
                const validation = await service.validatePackage(kit);
                assert(validation.ok && validation.contractVersion === 'learnit.kit.v3', 'explicit V3 import validation failed');
                const preview = await service.previewImport(kit);
                assert(preview.contract === 'learnit.kit.v3' && preview.activityCount === 2, 'V3 preview failed');
                const imported = await service.importPackage(kit);
                assert(imported.contract === 'learnit.kit.v3', 'V3 import result lost contract identity');
                assert(storage.committed !== null, 'V3 import did not reuse existing installation persistence');

                console.log('ATLAS_WP_026_CONSTRUCTED_RUNTIME=PASS');
            '''), encoding="utf-8")
            result = subprocess.run(
                ["node", str(script)],
                cwd=sandbox,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("ATLAS_WP_026_CONSTRUCTED_RUNTIME=PASS", result.stdout)

    def test_changed_sources_keep_constructed_scoring_out_of_ui(self) -> None:
        integration = (APP / "src/integration/atlas/session.js").read_text(encoding="utf-8")
        ui = (APP / "src/ui/render.js").read_text(encoding="utf-8")
        self.assertIn("learnit.kit.v3.constructed.canonical-text-match-v1", integration)
        self.assertIn("evaluateAnswer(", integration)
        self.assertIn("data-atlas-constructed-response", ui)
        self.assertNotIn("acceptedResponses", ui)


if __name__ == "__main__":
    unittest.main()
