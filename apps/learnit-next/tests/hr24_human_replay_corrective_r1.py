#!/usr/bin/env python3
"""Static and service-level qualification oracle for JOB_26_HR24_HUMAN_REPLAY_CORRECTIVE_R1."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARENT = "cb8ceb579dd65230f5300e9f58bd15cfa861578f"
PARENT_PRODUCT = "68a852f1b46564fd9f1cb21c0f848c44845e16d0"

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def blob(rel: str, ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", f"{ref}:{rel}"], cwd=ROOT, text=True).strip()

library = read("apps/learnit-next/src/core/library.js")
render = read("apps/learnit-next/src/ui/render.js")
navigation = read("apps/learnit-next/src/ui/navigation.js")
styles = read("apps/learnit-next/src/styles.css")
manifest = json.loads(read("apps/learnit-next/source_manifest.json"))

# One explicit deterministic Library search contract, reused by both active paths.
assert "export function normalizeLibrarySearchTerms(query)" in library
assert ".trim().toLocaleLowerCase('fr')" in library
assert ".split(/\\s+/u)" in library
assert "terms.every(term => haystack.includes(term))" in library
assert "return courses.filter(course => matchesLibrarySearch(query" in library
assert "import { matchesLibrarySearch } from '../core/library.js';" in render
assert "matchesLibrarySearch(query, entry.searchable)" in render
assert "entry.searchable.includes(query)" not in render
assert ".includes(normalized)" not in library
assert "...(externalProjection?.objectiveStates ?? course.objectives ?? []).map(item => item.label ?? '')" in render
assert "Boolean search" not in render
assert "advanced search" not in render.lower()

# Menu trigger: icon-only visual, independent accessible name, existing semantics retained.
assert "text: 'Menu'" not in navigation
assert "'aria-label': 'Ouvrir la navigation'" in navigation
assert navigation.count("className: 'nav-menu-bar'") == 3
assert "'aria-hidden': 'true'" in navigation
assert "'aria-expanded': 'false'" in navigation
assert "'aria-controls': drawerId" in navigation
assert "☰" not in navigation
for token in ("Escape", "previouslyFocused", "setAttribute('inert'", "nav-drawer-backdrop", "Fermer", "Aujourd’hui", "Bibliothèque", "Tous les cours", "Importer un cours"):
    assert token in navigation, token
for token in ("width: 44px", "height: 44px", ".nav-menu-icon", ".nav-menu-bar", "background: currentColor"):
    assert token in styles, token

# Actual service-level semantics, including Unicode whitespace and no write side effect.
node_test = r"""
import fs from 'node:fs';
const source = fs.readFileSync('apps/learnit-next/src/core/library.js','utf8');
const mod = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
let writes = 0;
const rows = [
  {courseInstallId:'a', packageInstallId:'p', courseLineageId:'l1', courseRevisionId:'r1', displayLabel:'Cours local', title:'Nombres fondamentaux', subtitle:'Complexes avancés', estimatedMinutes:1, activityCount:1},
  {courseInstallId:'b', packageInstallId:'p', courseLineageId:'l2', courseRevisionId:'r2', title:'Analyse réelle', subtitle:'Fonctions continues', estimatedMinutes:1, activityCount:1},
  {courseInstallId:'c', packageInstallId:'p', courseLineageId:'l3', courseRevisionId:'r3', title:'NOMBRES COMPLEXES', subtitle:'Pratique guidée', estimatedMinutes:1, activityCount:1},
];
const snapshot = JSON.stringify(rows);
const storage = {
  async listCourses(){ return structuredClone(rows); },
  async getCourse(id){ return rows.find(x=>x.courseInstallId===id); },
  async setCourseDisplayLabel(){ writes += 1; }
};
const service = mod.createLibraryService(storage);
const ids = async q => (await service.searchCourses(q)).map(x=>x.courseInstallId);
const same = (a,b) => JSON.stringify(a)===JSON.stringify(b);
if(!same(await ids('nombres complexes'), ['a','c'])) throw new Error('two-term AND');
if(!same(await ids('complexes nombres'), ['a','c'])) throw new Error('term order');
if(!same(await ids('  nombres   complexes  '), ['a','c'])) throw new Error('repeated whitespace');
if(!same(await ids('nombres\u00a0complexes'), ['a','c'])) throw new Error('unicode whitespace');
if(!same(await ids('local nombres avancés'), ['a'])) throw new Error('cross-field three-term');
if(!same(await ids('NOMBRES COMPLEXES'), ['a','c'])) throw new Error('French locale case');
if(!same(await ids('nombres absent'), [])) throw new Error('missing term');
if(!same(await ids(''), ['a','b','c'])) throw new Error('empty');
if(!same(await ids('   '), ['a','b','c'])) throw new Error('whitespace only');
if(writes !== 0) throw new Error('search wrote state');
if(JSON.stringify(rows)!==snapshot) throw new Error('search mutated records');
console.log('LIBRARY_MULTI_TERM_AND_SEARCH_SERVICE=PASS');
"""
subprocess.run(["node", "--input-type=module", "-e", node_test], cwd=ROOT, check=True)

# Protected semantics/content are byte-identical to JOB25 frozen product.
protected = [
    "apps/learnit-next/src/core/objective_progress.js",
    "apps/learnit-next/src/core/learning_recommendation.js",
    "apps/learnit-next/src/core/progress.js",
    "apps/learnit-next/src/core/session.js",
    "apps/learnit-next/src/core/activity_semantics.js",
    "apps/learnit-next/src/integration/atlas/session.js",
    "contracts/learnit-kit-v5.schema.json",
    "authoring/v5/validate_kit.py",
    "showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json",
]
for rel in protected:
    assert blob(rel) == blob(rel, PARENT_PRODUCT), rel
for path in (ROOT / "apps/learnit-next/src/core").glob("atlas_*.js"):
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    assert blob(rel) == blob(rel, PARENT_PRODUCT), rel

# Source manifest tracks only the four corrected source blobs under WP068 provenance.
working = {item["path"]: item for item in manifest["workingFiles"]}
corrected = [
    "apps/learnit-next/src/core/library.js",
    "apps/learnit-next/src/ui/render.js",
    "apps/learnit-next/src/ui/navigation.js",
    "apps/learnit-next/src/styles.css",
]
for rel in corrected:
    assert working[rel]["owner"] == "ATLAS-WP-068", rel
    assert working[rel]["fingerprint"]["kind"] == "git-blob-sha1", rel
    assert working[rel]["fingerprint"]["value"] == blob(rel), rel

print("MULTI_TERM_AND_SEARCH=PASS")
print("SEARCH_PATH_PARITY=PASS")
print("SEARCH_NO_STATE_MUTATION=PASS")
print("HAMBURGER_TRIGGER=PASS_STATIC")
print("HAMBURGER_ACCESSIBILITY=PASS_STATIC")
print("ENGINE_BLOB_IDENTITY=PASS")
print("HR24_003_ENGINE_GAP=CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED")
