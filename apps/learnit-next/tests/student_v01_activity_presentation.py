#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PRESENTERS = ROOT / "apps/learnit-next/src/ui/activity_presenters.js"
MEDIA = ROOT / "apps/learnit-next/src/ui/media.js"
ATLAS_CSS = ROOT / "apps/learnit-next/src/atlas.css"
RENDER = ROOT / "apps/learnit-next/src/ui/render.js"

presenters = PRESENTERS.read_text(encoding="utf-8")
media = MEDIA.read_text(encoding="utf-8")
css = ATLAS_CSS.read_text(encoding="utf-8")
render = RENDER.read_text(encoding="utf-8")

for source in (PRESENTERS, MEDIA):
    subprocess.run(["node", "--check", str(source)], cwd=ROOT, check=True)

# Static, finite presenter seam: no plugin registry/evaluator callback architecture.
assert "export function renderActivityPresentation" in presenters
assert "export function readActivityResponse" in presenters
assert "switch (presentation.type)" in presenters
for forbidden_architecture in ("registerPresenter", "pluginRegistry", "eventBus", "evaluatorCallback"):
    assert forbidden_architecture not in presenters

# The UI may be handed adversarial extra fields, but its implementation must never read scoring truth.
secret_fields = (
    "correctChoiceId",
    "answers",
    "acceptedResponses",
    "matches",
    "correctOrder",
    "assignments",
)
for field in secret_fields:
    dot_access = re.compile(rf"\bpresentation\s*\.\s*{re.escape(field)}\b")
    bracket_access = re.compile(rf"\bpresentation\s*\[\s*['\"]{re.escape(field)}['\"]\s*\]")
    assert not dot_access.search(presenters), f"secret field read through dot access: {field}"
    assert not bracket_access.search(presenters), f"secret field read through bracket access: {field}"

# All learner-visible content is constructed through textContent/attributes; no untrusted HTML sink.
assert ".innerHTML" not in presenters
assert ".innerHTML" not in media
assert "insertAdjacentHTML" not in presenters + media

# Response grammars are explicit and scoring-free.
for grammar in (
    "choiceId: selected.value",
    "acknowledged: true",
    "revealed: true",
    "associations:",
    "orderedItemIds",
    "assignments",
    "return { text }",
):
    assert grammar in presenters, grammar
assert "score(" not in presenters
assert "evaluate" not in presenters.lower()

# Matching/order/classify all have native keyboard/touch-safe controls independent of drag/drop.
assert "data-matching-left" in presenters and "data-matching-right" in presenters
assert 'data-order-move' in presenters
assert 'data-classify-select' in presenters
assert "dragstart" not in presenters.lower()
assert "draggable" not in presenters.lower()

# Flashcard reveal is explicit and no Student V0.1 self-grade surface exists.
assert "data-flashcard-reveal" in presenters
assert "flashcardRevealed" in presenters
assert "data-flashcard-grade" not in presenters

# Embedded media is local/data-only. SVG is parsed against finite tag/attribute allowlists.
for format_name in ("'svg'", "'png'", "'jpeg'", "'webp'"):
    assert format_name in media
assert "SVG_TAGS = new Set" in media and "SVG_ATTRS = new Set" in media
assert "DOMParser" in media and "XMLSerializer" in media
assert "data:image/" in media
assert "fetch(" not in media
assert "XMLHttpRequest" not in media
assert "new URL(" not in media

# UX floor: 44px controls, mobile stacking, bounded media and visible focus are declared.
assert "min-height:44px" in css
assert "focus-visible" in css
assert "activity-matching-pools{grid-template-columns:1fr}" in css
assert "max-width:100%" in css

# Existing Atlas qcm/fill production seam remains present; JOB 02 does not need integration ownership.
assert "export function renderAtlasActivityMarkup" in render
assert "export function readAtlasActivityResponse" in render
assert '[data-atlas-choice="true"]:checked' in render
assert "[data-atlas-slot]" in render

print("STUDENT_V01_ACTIVITY_PRESENTATION_STATIC_PASS")
print("SECRET_BOUNDARY_STATIC_PASS")
print("MEDIA_FAIL_CLOSED_STATIC_PASS")
print("ACCESSIBLE_NON_DRAG_CONTROLS_STATIC_PASS")
