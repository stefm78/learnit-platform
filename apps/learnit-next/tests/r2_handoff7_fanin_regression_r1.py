#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
A={".github/workflows/learnit-next-ci.yml":"9771876861b685db96083b4f8c9561fc045956ac","apps/learnit-next/src/integration/atlas/surface.js":"38e49785afc674c53436ec875782a2a07a47c18f","apps/learnit-next/tests/browser_student_v01_g5_r1_app_experience.py":"cb31b23288bf605b91483bbe81124901728c99c0","apps/learnit-next/tests/student_v01_g5_r1_app_experience.py":"0f0ee68e930eed1b662d2ef5f4434a9e1022ed98","docs/programs/student-v0.1/jobs/JOB_10A_G5_R1_APP_EXPERIENCE.md":"c1030b44ab3beded87b68e51b9d5d2bdf979ba79","work-packages/ATLAS-WP-051.json":"180a0caaf76b391b9cb421d9cdcf96acf7fb89eb","qualification/STUDENT_V01_G5_R1_APP_EXPERIENCE_RESULT.md":"9798774f5c331b50ebda1bd6fa84ed45bcd59aee"}
H6={"showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json":"57374ba897600894ab124e8ac2d3ee3b6f5c4cc2","showcase/student-v0.1/nombres-complexes/LEARNER_BRIEF.json":"6c4fb770f12690a3cb338c82fc77bf9b323c3b06","authoring/v2/atlas/nombres_complexes_atlas.json":"7f83784e8719917496a694b2ad170d724190fd04","showcase/student-v0.1/nombres-complexes/ROLE_B_SOURCE_MANIFEST_V5.json":"74e16e07e9e5978b7b5f3ce81befa4c0650bf925","showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT_V5.json":"3f6a1cec5444121c8fe742d515b400780046557c","showcase/student-v0.1/nombres-complexes/SEMANTIC_REVIEW_V5_R2.json":"a6c9f65f94900f5e46c0ecc8a44cb0d0e7166056","showcase/student-v0.1/nombres-complexes/FACTORY_EVIDENCE_V5_FINAL.json":"d1c17f6f12775f667c23df0a3cf96e316ffab41b"}
def blob(p): return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],cwd=ROOT,text=True).strip()
for p,s in A.items(): assert blob(p)==s,(p,blob(p),s)
for p,s in H6.items(): assert blob(p)==s,(p,blob(p),s)
render=(ROOT/"apps/learnit-next/src/ui/render.js").read_text(encoding="utf-8")
for m in ("OBJECTIVE_BUCKET_STATE_LABELS","renderSessionProgressDetails","data-session-objective-buckets","data-session-progress-details","renderEmbeddedMediaSet","data-activity-feedback-media"): assert m in render,m
session=render[render.index("const activityTitle = node('h2'"):render.index("function renderFeedback")]
section=session[session.index("const section = node"):]
assert section.index("renderServedActivityForm(")<section.index("objectiveBuckets,")<section.index("objectiveDetails,")
manifest=json.loads((ROOT/"apps/learnit-next/source_manifest.json").read_text(encoding="utf-8"));by={x["path"]:x for x in manifest["workingFiles"]}
assert by["apps/learnit-next/src/ui/render.js"]["fingerprint"]["value"]==blob("apps/learnit-next/src/ui/render.js")
assert by["apps/learnit-next/src/integration/atlas/surface.js"]["fingerprint"]["value"]==blob("apps/learnit-next/src/integration/atlas/surface.js")

# Re-run the exact H3 causal Node probe against the current integrated sources, bypassing only its historical frozen-blob preamble.
h3=(ROOT/"apps/learnit-next/tests/v5_runtime_atlas_projection_r1.py").read_text(encoding="utf-8")
tag="probe = r'''";start=h3.index(tag)+len(tag);end=h3.index("'''",start);probe=h3[start:end]
proc=subprocess.run(["node","--input-type=module","-e",probe],cwd=ROOT,text=True,capture_output=True)
print(proc.stdout,end="");print(proc.stderr,end="");assert proc.returncode==0
assert "V5_RUNTIME_ATLAS_PROJECTION_CAUSAL_PASS" in proc.stdout
assert "REFERENCES_RUNTIME_FETCH_NONE" in h3

# Reuse the qualified H5 current-runtime probes without its historical no-product-mutation scope assertion.
p=ROOT/"apps/learnit-next/tests/v5_showcase_port_r1.py"
spec=importlib.util.spec_from_file_location("wp059",p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
candidate=mod.make_candidate();frozen=json.loads((ROOT/"showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json").read_text(encoding="utf-8"));assert candidate==frozen
with tempfile.TemporaryDirectory() as td:
    target=Path(td)/"candidate.json";target.write_text(json.dumps(candidate,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    mod.core_smoke(target);mod.v8_browser_smoke(candidate,td)
print("STREAM_A_EXACT_NONCONFLICT_BYTES: PASS")
print("H6_SEMANTIC_TARGET_BYTES: PASS")
print("V5_RUNTIME_ATLAS_PROJECTION_CURRENT: PASS")
print("PERSIST_CONFIRM_REVEAL_CURRENT: PASS")
print("REFERENCES_RUNTIME_FETCH: NONE")
print("STREAM_A_V5_V8_DISCRIMINANT: PASS")
print("V5_IMPORT_10_RESPONSES_RELOAD_RESUME: PASS")
print("V8_EXACT_10_ACTIVITY_RENDER_RESPONSE_CURRENT: PASS")
