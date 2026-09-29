#!/usr/bin/env python3
"""Static qualification oracle for JOB_28_G5_DELTA_UX_FINDINGS_CORRECTIVE_R1."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARENT = "b6a24a5b2d300d3e10fc8a413148071636653a06"

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def blob(rel: str, ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", f"{ref}:{rel}"], cwd=ROOT, text=True).strip()

render = read("apps/learnit-next/src/ui/render.js")
styles = read("apps/learnit-next/src/styles.css")
manifest = json.loads(read("apps/learnit-next/source_manifest.json"))

# G5-UX-001: terminal guidance is concise, truthful and presentation-only.
assert "detail = 'Un objectif reste à confirmer. Rien à faire pour le moment.';" in render
assert "Un objectif est acquis récemment et un autre reste à confirmer." not in render
assert "validation distincte doit encore le confirmer" not in render
assert "ni nouvelle activité de validation à proposer ni date de disponibilité" not in render
assert "node('strong', { text: 'Parcours d’activités terminé' })" in render

# G5-UX-002: direct accessible edit affordance + out-of-flow overlay.
for token in (
    "className: 'quiet course-rename-button'",
    "'aria-label': `Renommer le cours ${course.title}`",
    "className: 'course-rename-icon'",
    "'aria-hidden': 'true'",
    "className: 'course-rename-overlay'",
    "'data-course-rename-overlay': 'true'",
    "runtime.setCourseDisplayLabel(course.courseInstallId, requestedLabel)",
    "focusCourseRenameInstallId: course.courseInstallId",
):
    assert token in render, token
assert "text: '⋯'" not in render
assert "className: 'course-settings-menu'" not in render
assert "titleSlot.replaceChildren(form)" not in render
assert "window.prompt" not in render
assert "position: absolute;" in styles
assert ".course-rename-overlay" in styles
for token in ("width: 44px", "height: 44px", ".course-rename-button", ".course-rename-control"):
    assert token in styles, token
assert ".course-inline-rename" not in styles
assert ".course-settings-menu" not in styles

# Only presentation/provenance changes: protected semantic/content files stay byte-identical.
protected = [
    "apps/learnit-next/src/core/session.js",
    "apps/learnit-next/src/core/activity_semantics.js",
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/core/objective_progress.js",
    "apps/learnit-next/src/core/learning_recommendation.js",
    "apps/learnit-next/src/integration/atlas/session.js",
    "apps/learnit-next/src/ui/activity_presenters.js",
    "contracts/learnit-kit-v5.schema.json",
    "authoring/v5/validate_kit.py",
    "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json",
]
for rel in protected:
    assert blob(rel) == blob(rel, PARENT), rel

# Manifest rebind is limited to the two changed product sources plus self provenance.
working = {item["path"]: item for item in manifest["workingFiles"]}
for rel in ("apps/learnit-next/src/ui/render.js", "apps/learnit-next/src/styles.css"):
    assert working[rel]["owner"] == "ATLAS-WP-070", rel
    assert working[rel]["fingerprint"]["kind"] == "git-blob-sha1", rel
    assert working[rel]["fingerprint"]["value"] == blob(rel), rel
self_item = working["apps/learnit-next/source_manifest.json"]
assert self_item["owner"] == "ATLAS-WP-070"
assert self_item["fingerprint"]["kind"] == "canonical-self-sha256"

print("G5_UX_001_TERMINAL_GUIDANCE=PASS")
print("G5_UX_002_DIRECT_RENAME_OVERLAY=PASS")
print("PROTECTED_SEMANTICS_IDENTITY=PASS")
print("SOURCE_MANIFEST_REBIND=PASS")
