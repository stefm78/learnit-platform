#!/usr/bin/env python3
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "18b925436777943b19c4b031c24659ad60dee133"
PRESENTER_BLOB = "fe38702b97f2f243101bfd0ae894b43aaeb2fbaf"

def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()

def show(ref: str, path: str) -> str:
    return git("show", f"{ref}:{path}")

surface_path = "apps/learnit-next/src/integration/atlas/surface.js"
render_path = "apps/learnit-next/src/ui/render.js"

baseline_surface = show(BASE, surface_path)
baseline_render = show(BASE, render_path)
assert "Aucun parcours Atlas installé" in baseline_surface
start = baseline_render.index("function renderSessionSnapshot")
end = baseline_render.index("function renderFeedback", start)
baseline_session = baseline_render[start:end]
assert baseline_session.index("objectiveSurface,") < baseline_session.index("renderServedActivityForm(")
print("G4_FALSE_EMPTY_STATE_REPRO=PASS")
print("G4_PROGRESS_BEFORE_ACTIVITY_REPRO=PASS")

surface = (ROOT / surface_path).read_text(encoding="utf-8")
render = (ROOT / render_path).read_text(encoding="utf-8")
assert "Aucun parcours Atlas installé" not in surface
assert "surface.style.display = 'none'" in surface
assert "Planner incompatibility is not an empty learner library" in surface
assert "data-session-objective-buckets" in render
assert "data-session-progress-details" in render
assert "Voir ma progression" in render
for label in ("À découvrir", "En apprentissage", "À renforcer", "À confirmer", "Acquis récemment"):
    assert label in render, label
start = render.index("function renderSessionSnapshot")
end = render.index("function renderFeedback", start)
session = render[start:end]
assert session.index("renderServedActivityForm(") < session.index("objectiveBuckets,")
assert session.index("renderServedActivityForm(") < session.index("objectiveDetails,")
assert git("rev-parse", "HEAD:apps/learnit-next/src/ui/activity_presenters.js") == PRESENTER_BLOB

for path in (
    "apps/learnit-next/src/core",
    "apps/learnit-next/build.py",
    "apps/learnit-next/index.template.html",
    "apps/learnit-next/source_manifest.json",
    "contracts",
    "authoring",
    "showcase",
    "pilot",
    "qa",
):
    result = subprocess.run(["git", "diff", "--quiet", BASE, "HEAD", "--", path], cwd=ROOT)
    assert result.returncode == 0, path

print("FALSE_EMPTY_STATE_STATIC=PASS")
print("ACTIVITY_PRIMARY_STATIC=PASS")
print("COMPACT_OBJECTIVE_BUCKETS_STATIC=PASS")
print("PROGRESSIVE_DISCLOSURE_STATIC=PASS")
print("ACTIVITY_PRESENTERS_UNCHANGED=PASS")
print("CORE_SEMANTICS_UNCHANGED=PASS")
