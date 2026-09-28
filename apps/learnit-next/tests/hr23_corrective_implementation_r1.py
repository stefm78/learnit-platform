#!/usr/bin/env python3
"""Bounded static contract for JOB_24_HR23_CORRECTIVE_IMPLEMENTATION_R1."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps" / "learnit-next"
BASE = "3660668ffb6320650fb7c92b0cc9594a7e4f3d24"

render = (APP / "src/ui/render.js").read_text(encoding="utf-8")
css = (APP / "src/styles.css").read_text(encoding="utf-8")
objective = (APP / "src/ui/objective_progress.js").read_text(encoding="utf-8")
projection = (APP / "src/integration/atlas/activity_projection.js").read_text(encoding="utf-8")
presenters = (APP / "src/ui/activity_presenters.js").read_text(encoding="utf-8")
indexeddb = (APP / "src/adapters/indexeddb.js").read_text(encoding="utf-8")
manifest = json.loads((APP / "source_manifest.json").read_text(encoding="utf-8"))
schema = json.loads((ROOT / "contracts/learnit-kit-v5.schema.json").read_text(encoding="utf-8"))
kit = json.loads((ROOT / "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json").read_text(encoding="utf-8"))

def blob(path: str, ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", f"{ref}:{path}"], cwd=ROOT, text=True).strip()

# Semantic authorities are byte-identical to the exact JOB23 closeout.
protected = [
    "apps/learnit-next/src/core/session.js",
    "apps/learnit-next/src/core/activity_semantics.js",
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/core/objective_progress.js",
    "apps/learnit-next/src/core/learning_recommendation.js",
    "apps/learnit-next/src/main.js",
    "apps/learnit-next/src/integration/atlas/session.js",
    "apps/learnit-next/src/ui/media.js",
    "contracts/learnit-kit-v5.schema.json",
    "authoring/v5/validate_kit.py",
    "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json",
]
for path in protected:
    assert blob(path) == blob(path, BASE), path
assert blob("apps/learnit-next/src/core/session.js") == "9909f0712de59211d14211ef1afc27bda87fcbf5"

# A — deterministic reset clears all stores without delete/reopen and verifies emptiness before rendering.
reset_start = indexeddb.index("async resetNextData()")
reset_end = indexeddb.index("async storageReport()", reset_start)
reset_block = indexeddb[reset_start:reset_end]
assert "db.transaction(NEXT_STORES, 'readwrite')" in reset_block
assert "objectStore(storeName).clear()" in reset_block
assert "deleteDatabase(" not in reset_block
assert "remaining !== 0" in render
assert "await renderLibrary({ announcement: message })" in render

# B/H — scalable local retrieval, progressive disclosure, truthful static metadata, secondary management.
for token in (
    "library-search-input",
    "Rechercher dans vos cours",
    "course-objectives-details",
    "courseObjectiveSummary(course)",
    "Options du cours",
    "min estimées au total",
):
    assert token in render or token in css
assert "node('summary', { text: 'Gérer' })" not in render
assert "Priorité Learn-it" not in objective
assert "39 min restantes" not in render
course_schema = schema["$defs"]["course"]
assert not ({"chapters", "chapter", "phases", "groups", "objectiveGroups"} & set(course_schema["properties"]))
course = kit["courses"][0]
assert len(course["activities"]) == 10
assert sum(int(a["estimatedMinutes"]) for a in course["activities"]) == 39
assert course["estimatedMinutes"] == 39

# C — true objective toggle, subtle selection, keyboard/SR control relationship.
for token in ("clearDetail", "selectDetail", "aria-expanded", "aria-pressed", "data-objective-progress-r15-selected"):
    assert token in objective
assert "if (selectedReservoir === reservoir) clearDetail();" in objective
assert "transform: none" in css
assert "box-shadow: inset 0 -3px 0 #233f64" in css
assert "L’entraînement est à jour ; cet objectif doit encore être confirmé par une validation distincte." in objective

# D — the visually empty matching slot is itself a single-pointer/keyboard target.
assert "className:'activity-pair-slot'" in presenters
assert "role:'button',tabindex:'0'" in presenters
assert "Déposer ici pour " in presenters
assert "keyActivate(slot,activate)" in presenters
assert "target.addEventListener('click',activate)" in presenters

# E — mapping/classification relation is data, not punctuation.
post = projection[projection.index("export function projectPostAnswerFeedback"):projection.index("export function projectActivityPresentation")]
assert "comparisonRows" in post
assert "item: left.label" in post and "learner:" in post and "expected:" in post
for phrase in ("Élément :", "votre choix :", "réponse attendue :"):
    assert phrase not in post
assert "renderFeedbackComparison" in render
assert "node('table'" in render
for heading in ("Élément", "Votre réponse", "Attendu"):
    assert heading in render

# F — last correction and recap are separate render states using the exact returned sessionDelta.
assert "function renderSessionSummary(result)" in render
assert "text: 'Voir le bilan de la séance'" in render
assert "data-session-summary" in render
assert "context: 'terminal-summary'" in render
feedback_block = render[render.index("function renderFeedback(result)"):render.index("async function initialize()", render.index("function renderFeedback(result)"))]
assert "terminalObjectiveSurface" not in feedback_block
assert "renderSessionSummary(result)" in feedback_block

# G — truthful bounded capability gap; no invented time or false validation CTA.
assert "ni nouvelle activité de validation à proposer ni date de disponibilité" in render
assert "validation distincte doit encore le confirmer" in render
for invented in ("revenez demain", "reviens demain", "dans 24 h", "dans 24h"):
    assert invented not in render.lower()
assert "recommendation?.action === 'validate'" in render

# Manifest is rebound only to presentation/interaction/reset files owned by this WP.
owned = {item["path"]: item for item in manifest["workingFiles"] if item.get("owner") == "ATLAS-WP-066"}
expected_owned = {
    "apps/learnit-next/src/styles.css",
    "apps/learnit-next/src/adapters/indexeddb.js",
    "apps/learnit-next/src/ui/objective_progress.js",
    "apps/learnit-next/src/ui/render.js",
    "apps/learnit-next/src/integration/atlas/activity_projection.js",
    "apps/learnit-next/src/ui/activity_presenters.js",
    "apps/learnit-next/source_manifest.json",
}
assert expected_owned <= set(owned)
for path in expected_owned - {"apps/learnit-next/source_manifest.json"}:
    assert owned[path]["fingerprint"] == {"kind": "git-blob-sha1", "value": blob(path)}
assert manifest["artifact"]["finalized"] is False

print("HR23_A_RESET=PASS")
print("HR23_B_LIBRARY_SCALE=PASS")
print("HR23_C_OBJECTIVE_TOGGLE=PASS")
print("HR23_D_TAPPABLE_DESTINATION=PASS")
print("HR23_E_STRUCTURED_MAPPING_FEEDBACK=PASS")
print("HR23_F_SESSION_SUMMARY_SEPARATION=PASS")
print("HR23_G_AWAITING_VALIDATION_UI=PASS_WITH_ATLAS_CAPABILITY_GAP")
print("HR23_H_SECONDARY_MANAGEMENT=PASS")
print("SESSION_JS_UNCHANGED=PASS")
print("SCORING_AUTHORITY_UNCHANGED=PASS")
print("OBJECTIVE_STATE_SEMANTICS_UNCHANGED=PASS")
print("RECOMMENDATION_SEMANTICS_UNCHANGED=PASS")
print("V5_EXACT_SHOWCASE_10_ACTIVITIES_39_MINUTES=PASS")
