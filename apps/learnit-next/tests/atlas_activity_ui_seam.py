#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
integration = (ROOT / "apps/learnit-next/src/integration/atlas/session.js").read_text(encoding="utf-8")
ui = (ROOT / "apps/learnit-next/src/ui/render.js").read_text(encoding="utf-8")
core = (ROOT / "apps/learnit-next/src/core/session.js").read_text(encoding="utf-8")

assert "from '../../ui/render.js'" in integration
assert "renderAtlasActivityMarkup(activity)" in integration
assert "readAtlasActivityResponse(wrapper, activity)" in integration
assert "function renderActivity(" not in integration
assert "function readResponse(" not in integration
assert "data-atlas-choice=\"true\"" not in integration
assert "[data-atlas-slot]" not in integration
assert "export function renderAtlasActivityMarkup" in ui
assert "export function readAtlasActivityResponse" in ui
assert "[data-atlas-choice=\"true\"]:checked" in ui
assert "[data-atlas-slot]" in ui
assert "querySelector" not in core
assert "document." not in core
print("ATLAS_ACTIVITY_UI_SEAM_PASS")
