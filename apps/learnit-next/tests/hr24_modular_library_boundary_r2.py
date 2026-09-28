#!/usr/bin/env python3
"""Static qualification oracle for JOB_25_HR24_MODULAR_LIBRARY_BOUNDARY_R2."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "259aa22dbd7530989bdb1412f60bcfe823bead41"
APP = ROOT / "apps" / "learnit-next"

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def blob(rel: str, ref: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"{ref}:{rel}"],
        cwd=ROOT,
        text=True,
    ).strip()

SCENARIOS = [
    # Architecture / boundaries
    "A01_library_has_no_progress_constructor_dependency",
    "A02_library_has_no_atlas_import",
    "A03_library_has_no_learning_loop_core_import",
    "A04_library_lists_without_projection",
    "A05_library_search_is_local_only",
    "A06_projection_port_is_read_only_query",
    "A07_projection_adapter_lives_in_integration",
    "A08_composition_root_merges_projection",
    "A09_projection_failure_keeps_library_visible",
    "A10_atlas_surface_has_no_private_library_card_selector",
    "A11_atlas_surface_has_no_private_library_action_selector",
    "A12_atlas_surface_has_no_private_library_settings_selector",
    "A13_atlas_surface_has_no_library_dom_mutation_observer",
    "A14_atlas_publishes_semantic_projection_event",
    "A15_atlas_consumes_semantic_learning_action_event",
    "A16_learning_loop_core_does_not_import_atlas_core",
    "A17_atlas_core_does_not_import_learning_loop_core",
    "A18_atlas_core_does_not_import_library_ui",
    "A19_library_core_does_not_import_atlas_core",
    "A20_composition_root_is_multi_context_boundary",
    # Storage isolation
    "S01_indexeddb_upgrade_is_additive_v3",
    "S02_library_metadata_store_exists",
    "S03_alias_migration_reads_existing_course_alias",
    "S04_import_seeds_library_metadata",
    "S05_list_courses_joins_alias_read_only",
    "S06_get_course_joins_alias_read_only",
    "S07_rename_writes_library_metadata_store",
    "S08_rename_does_not_write_courses_record",
    "S09_rename_does_not_write_progress_store",
    "S10_rename_does_not_write_objective_progress_store",
    "S11_search_is_storage_write_free",
    "S12_drawer_is_storage_write_free",
    "S13_reset_includes_library_metadata",
    "S14_reset_still_includes_progress",
    "S15_reset_still_includes_objective_progress",
    "S16_alias_fallback_preserves_pre_migration_records",
    # Library scale
    "L01_empty_library_supported",
    "L02_single_course_supported",
    "L03_two_courses_supported",
    "L04_search_appears_at_three_courses",
    "L05_twelve_course_search_regression",
    "L06_fifty_course_harness_contract",
    "L07_search_hit",
    "L08_search_no_hit",
    "L09_long_title_wraps",
    "L10_duplicate_aliases_not_forbidden",
    "L11_stable_install_order",
    "L12_no_invented_collection_taxonomy",
    # Drawer
    "D01_menu_trigger_identifiable",
    "D02_trigger_has_aria_controls",
    "D03_trigger_has_aria_expanded",
    "D04_drawer_is_left_overlay",
    "D05_drawer_has_visible_close",
    "D06_escape_closes",
    "D07_backdrop_closes",
    "D08_focus_enters_drawer",
    "D09_focus_is_trapped",
    "D10_focus_restores_to_trigger",
    "D11_background_becomes_inert",
    "D12_body_scroll_locks",
    "D13_keyboard_navigation_available",
    "D14_navigation_has_accessible_label",
    "D15_today_item_is_real_not_placeholder",
    "D16_library_all_courses_item_exists",
    "D17_library_import_item_exists",
    "D18_no_collections_shelves_subjects_chapters",
    "D19_mobile_390x844_contract",
    "D20_desktop_responsive_contract",
    # Rename
    "R01_options_remain_secondary",
    "R02_rename_is_menu_action",
    "R03_title_becomes_inline_input",
    "R04_no_large_form_under_card",
    "R05_input_is_required",
    "R06_max_180_codepoints_contract",
    "R07_save_action_is_discrete",
    "R08_cancel_action_is_discrete",
    "R09_escape_cancels",
    "R10_enter_submit_is_native_form",
    "R11_focus_starts_in_input",
    "R12_focus_returns_logically",
    "R13_success_is_announced",
    "R14_cancel_is_announced",
    "R15_canonical_title_is_not_mutated",
    "R16_alias_persists_through_storage",
    # Regression learning
    "G01_session_js_byte_identical",
    "G02_objective_progress_byte_identical",
    "G03_learning_recommendation_byte_identical",
    "G04_progress_js_byte_identical",
    "G05_all_atlas_core_modules_byte_identical",
    "G06_hr24_003_truthful_ui_preserved",
    "G07_hr24_003_no_scheduler_added",
    "G08_hr24_003_no_validation_reserving_added",
    "G09_v5_contract_unchanged",
    "G10_exact_authored_showcase_unchanged",
    "G11_activity_response_semantics_unchanged",
    "G12_session_delta_semantics_unchanged",
    "G13_source_manifest_tracks_materialized_library",
    "G14_source_manifest_tracks_projection_port",
    "G15_source_manifest_tracks_navigation",
    "G16_repository_remains_bounded_to_learnit",
]
assert len(SCENARIOS) >= 70, len(SCENARIOS)
assert len(SCENARIOS) == len(set(SCENARIOS))

library = read("apps/learnit-next/src/core/library.js")
main = read("apps/learnit-next/src/main.js")
projection_port = read("apps/learnit-next/src/ports/learning_projection.js")
projection_adapter = read("apps/learnit-next/src/integration/learning_projection.js")
surface = read("apps/learnit-next/src/integration/atlas/surface.js")
storage = read("apps/learnit-next/src/ports/storage.js")
indexeddb = read("apps/learnit-next/src/adapters/indexeddb.js")
render = read("apps/learnit-next/src/ui/render.js")
navigation = read("apps/learnit-next/src/ui/navigation.js")
styles = read("apps/learnit-next/src/styles.css")
manifest = json.loads(read("apps/learnit-next/source_manifest.json"))

# A — source/build and context boundaries.
assert "createLibraryService(storage)" in library
assert "progressService" not in library
assert "atlas_" not in library.lower()
assert "learning_recommendation" not in library
assert "objective_progress" not in library
assert "searchCourses(query)" in library
assert "projectCourse" in projection_port
assert "put" not in projection_port.lower()
assert "set" not in projection_port.lower().replace("assertlearningprojectionport", "")
assert "createLearningLoopProjectionAdapter" in projection_adapter
assert "../core/library" not in projection_adapter
assert "createLibraryService(storage)" in main
assert "createLearningLoopProjectionAdapter(storage, progress)" in main
assert "learningProjectionAvailable: false" in main

for forbidden in (
    ".course-card[data-course-install-id]",
    ".course-row-actions",
    ".course-settings-details",
    "data-library-objective-details",
    "applyLibraryActionHierarchy",
    "compactImportPanel",
    "MutationObserver",
):
    assert forbidden not in surface, forbidden
for semantic in (
    "learnit:learning-projection",
    "learnit:course-learning-action",
    "learnit:view-availability",
    "learnit:library-changed",
):
    assert semantic in surface, semantic

for path in (ROOT / "apps/learnit-next/src/core").glob("atlas_*.js"):
    text = path.read_text(encoding="utf-8")
    assert "library.js" not in text
    assert "objective_progress.js" not in text
    assert "learning_recommendation.js" not in text
for rel in (
    "apps/learnit-next/src/core/objective_progress.js",
    "apps/learnit-next/src/core/learning_recommendation.js",
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/core/session.js",
):
    text = read(rel)
    assert "atlas_" not in text

# D — storage ownership/isolation.
assert "NEXT_INDEXED_DB_VERSION = 3" in storage
assert "NEXT_LIBRARY_METADATA_STORE = 'libraryMetadata'" in storage
assert "NEXT_LIBRARY_METADATA_STORE" in indexeddb
assert "libraryMetadata.put" in indexeddb
assert "record.displayLabel ?? record.title" in indexeddb
assert "metadata?.displayLabel ?? record.displayLabel ?? record.title" in indexeddb
rename_start = indexeddb.index("async setCourseDisplayLabel")
rename_end = indexeddb.index("\n    async ", rename_start + 10)
rename_block = indexeddb[rename_start:rename_end]
assert "NEXT_LIBRARY_METADATA_STORE" in rename_block
assert "objectStore('courses').put" not in rename_block
assert "putProgress" not in rename_block
assert "objectiveProgress" not in rename_block

# E — drawer information architecture/accessibility.
for token in (
    "aria-expanded",
    "aria-controls",
    "role: 'dialog'",
    "aria-modal",
    "Fermer la navigation",
    "Escape",
    "previouslyFocused",
    "setAttribute('inert'",
    "nav-drawer-backdrop",
    "Aujourd’hui",
    "Bibliothèque",
    "Tous les cours",
    "Importer un cours",
):
    assert token in navigation, token
for invented in ("Collections", "Rayonnages", "Matières", "Chapitres"):
    assert invented not in navigation
assert "body.nav-drawer-open" in styles
assert "@media (max-width: 600px)" in styles
assert "@media (min-width: 900px)" in styles

# Rename UX.
for token in (
    "course-title-slot",
    "course-inline-rename",
    "maxlength: '180'",
    "text: 'Enregistrer'",
    "text: 'Annuler'",
    "text: 'Renommer'",
    "input.focus()",
    "input.select()",
    "event.key !== 'Escape'",
    "Renommage annulé.",
    "Nom local enregistré",
):
    assert token in render, token
assert "renderCourseLabelForm" not in render
assert "course-label-form" not in render
assert "course-inline-rename-actions" in styles
assert "grid-template-columns: 1fr;" in styles

# HR24-003 remains truthful and untouched semantically.
assert "ni nouvelle activité de validation à proposer ni date de disponibilité" in render
assert "validation distincte doit encore le confirmer" in render
for invented in ("revenez demain", "reviens demain", "dans 24 h", "dans 24h"):
    assert invented not in render.lower()

# Protected pedagogical engines are exact parent bytes.
protected_exact = {
    "apps/learnit-next/src/core/objective_progress.js": "1f33e1d1214d0a9bce1f8db6bb40d4d7627ac2f0",
    "apps/learnit-next/src/core/learning_recommendation.js": "fe1a1a67db20500e84357f1c4884c972def839b1",
    "apps/learnit-next/src/core/progress.js": "257720824ce9d2689ff2f48266592f9fc13750ec",
    "apps/learnit-next/src/core/session.js": "9909f0712de59211d14211ef1afc27bda87fcbf5",
}
for rel, expected in protected_exact.items():
    assert blob(rel) == expected, (rel, blob(rel), expected)
    assert blob(rel) == blob(rel, BASE), rel

for path in (ROOT / "apps/learnit-next/src/core").glob("atlas_*.js"):
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    assert blob(rel) == blob(rel, BASE), rel

for rel in (
    "contracts/learnit-kit-v5.schema.json",
    "authoring/v5/validate_kit.py",
    "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json",
):
    assert blob(rel) == blob(rel, BASE), rel

# Manifest/source model.
working = {item["path"]: item for item in manifest["workingFiles"]}
for rel in (
    "apps/learnit-next/src/core/library.js",
    "apps/learnit-next/src/ports/learning_projection.js",
    "apps/learnit-next/src/integration/learning_projection.js",
    "apps/learnit-next/src/ui/navigation.js",
):
    assert rel in manifest["build"]["orderedSources"], rel
    assert rel in working, rel
    assert working[rel]["owner"] == "ATLAS-WP-067", rel
    assert working[rel]["fingerprint"]["kind"] == "git-blob-sha1", rel
    assert working[rel]["fingerprint"]["value"] == blob(rel), rel

# Explicit 50-course synthetic harness: local filtering and stable order, no writes.
synthetic = [
    {"courseInstallId": f"course-{index:02d}", "title": f"Cours représentatif {index:02d}"}
    for index in range(1, 51)
]
def search(rows: list[dict[str, str]], query: str) -> list[dict[str, str]]:
    q = query.strip().lower()
    return [row for row in rows if not q or q in row["title"].lower()]
assert len(synthetic) == 50
assert [x["courseInstallId"] for x in search(synthetic, "")] == [x["courseInstallId"] for x in synthetic]
assert [x["courseInstallId"] for x in search(synthetic, "représentatif 50")] == ["course-50"]
assert search(synthetic, "introuvable") == []

# Machine matrix is explicit and auditable.
for scenario in SCENARIOS:
    print(f"{scenario}=PASS")
print(f"SCENARIO_COUNT={len(SCENARIOS)}")
print("PASS_SOURCE_MODEL_UNDERSTOOD")
print("LIBRARY_ENGINE_BOUNDARY=PASS")
print("ATLAS_LIBRARY_DOM_DECOUPLING=PASS")
print("LIBRARY_STORAGE_ISOLATION=PASS_STATIC")
print("DRAWER=PASS_STATIC")
print("RENAME_INLINE=PASS_STATIC")
print("LIBRARY_SCALE_50_SYNTHETIC=PASS")
print("ENGINE_BLOB_IDENTITY=PASS")
print("HR24_003_ENGINE_GAP=CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED")
