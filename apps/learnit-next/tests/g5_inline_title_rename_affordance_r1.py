#!/usr/bin/env python3
"""Static qualification oracle for JOB_29_G5_INLINE_COURSE_TITLE_RENAME_AFFORDANCE_R1."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARENT = "829b51caa638bbbb6c81ca9a0ee8f60ab5d59b30"

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def blob(rel: str, ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", f"{ref}:{rel}"], cwd=ROOT, text=True).strip()

render = read("apps/learnit-next/src/ui/render.js")
styles = read("apps/learnit-next/src/styles.css")
manifest = json.loads(read("apps/learnit-next/source_manifest.json"))

# The accepted JOB28 terminal guidance is frozen and INFORMATION_DENSITY is not reopened.
assert "detail = 'Un objectif reste à confirmer. Rien à faire pour le moment.';" in render

# One direct semantic edit button remains, now attached to the title region.
for token in (
    "className: 'quiet course-rename-button'",
    "'aria-label': `Renommer le cours ${course.title}`",
    "className: 'course-rename-icon'",
    "'aria-hidden': 'true'",
    "const renameControl = node('span', { className: 'course-rename-control' }, [renameButton]);",
    "titleSlot.append(renameControl);",
    "titleSlot.append(form);",
    "className: 'course-rename-overlay'",
    "'data-course-rename-overlay': 'true'",
    "runtime.setCourseDisplayLabel(course.courseInstallId, requestedLabel)",
    "focusCourseRenameInstallId: course.courseInstallId",
):
    assert token in render, token
assert "            renameControl," not in render
assert "text: '⋯'" not in render
assert "className: 'course-settings-menu'" not in render
assert "contenteditable" not in render.lower()
assert "titleSlot.replaceChildren(form)" not in render
assert "window.prompt" not in render

# Heading remains a heading containing only the displayed title; edit is a separate control.
assert "const titleHeading = node('h3', {\n          className: 'course-title-heading',\n          text: course.title," in render

# Visible footprint is compact/chromeless; effective touch envelope is transparent 44x44.
for token in (
    ".course-rename-button {",
    "width: 24px;",
    "min-width: 24px;",
    "height: 24px;",
    "min-height: 24px;",
    "border: 0;",
    "background: transparent;",
    ".course-rename-button::before {",
    "width: 44px;",
    "height: 44px;",
):
    assert token in styles, token
assert "border: 1px solid var(--border);\n  border-radius: 10px;\n  background: var(--surface);\n  color: var(--text);" not in styles[styles.index(".course-rename-button {"):styles.index(".course-rename-icon")]
assert ".course-rename-overlay" in styles
overlay_css = styles[styles.index(".course-rename-overlay {"):styles.index(".course-rename-label {")]
assert "position: absolute;" in overlay_css
assert "left: 0;" in overlay_css

# Protected semantic/content sources remain byte-identical to the exact JOB28 parent evidence head.
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

working = {item["path"]: item for item in manifest["workingFiles"]}
for rel in ("apps/learnit-next/src/ui/render.js", "apps/learnit-next/src/styles.css"):
    assert working[rel]["owner"] == "ATLAS-WP-071", rel
    assert working[rel]["fingerprint"]["kind"] == "git-blob-sha1", rel
    assert working[rel]["fingerprint"]["value"] == blob(rel), rel
self_item = working["apps/learnit-next/source_manifest.json"]
assert self_item["owner"] == "ATLAS-WP-071"
assert self_item["fingerprint"]["kind"] == "canonical-self-sha256"

print("INLINE_TITLE_EDIT_STATIC=PASS")
print("SEMANTIC_BUTTON_AND_ACCESSIBLE_NAME=PASS")
print("COMPACT_VISIBLE_CHROME=PASS")
print("TRANSPARENT_44PX_TOUCH_ENVELOPE=PASS")
print("OUT_OF_FLOW_OVERLAY=PASS")
print("TERMINAL_GUIDANCE_PRESERVED=PASS")
print("PROTECTED_SEMANTICS_IDENTITY=PASS")
print("SOURCE_MANIFEST_REBIND=PASS")
