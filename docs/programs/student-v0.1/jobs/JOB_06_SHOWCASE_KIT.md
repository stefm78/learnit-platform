# /AUDIT /SOLVE /BUILD — JOB 06
## Student V0.1 — real 30–45 minute showcase kit

Repository: `stefm78/learnit-platform`  
Authority issue: `#405`  
Wave 2 control freeze: `#403`  
Work package: `ATLAS-WP-035`

Branch: `student-v01/wave2-showcase-kit`

Exact anchors:

- `WAVE2_COMMON_BASE = 281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- `QUALIFIED_PRODUCT_BASE = 8fa25844cf9ddf7c2429f730d818b3518c46de04`

Apply:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

---

## 0. Role

You are the learning-content author for one **real** Student V0.1 showcase journey.

This is not a feature-demo fixture.

The learner should be able to spend roughly 30–45 minutes learning a coherent bounded topic, with exposition, active retrieval/practice, feedback and meaningful evaluation.

You own only files under `showcase/student-v0.1/**`, your work package/prompt and qualification evidence.

No runtime, UI, schema, authoring-tool or workflow mutation is allowed.

---

## 1. Reconstruct authority

Before authoring:

1. fresh-read Human Control Plane HEAD;
2. fresh-read repository state and PR #402;
3. read issues #403, #405 and #401;
4. verify exact ancestry from `WAVE2_COMMON_BASE`;
5. read:
   - `contracts/learnit-kit-v4.schema.json`;
   - Student V0.1 architecture;
   - `authoring/v4/README.md`;
   - `authoring/v4/validate_kit.py`;
   - `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V4.md`;
   - `authoring/v2/atlas/pedagogical_quality.py`;
   - `authoring/factory/factory_gate.py` and README.

Content source authority for this job is the exact file at the common base:

`authoring/v2/atlas/nombres_complexes_atlas.json`

You may use other repository Nombres complexes artifacts only as corroborating evidence. Do not silently import facts that are absent from the chosen source basis.

Do not browse the web merely to enrich the mathematics. Source fidelity is the constraint.

---

## 2. Source sufficiency gate

Before creating the V4 kit, audit whether the chosen canonical source is sufficient for a coherent 30–45 minute rich journey.

The intended bounded domain is the source's own scope, especially conjugate/module/geometric interpretation as actually represented there.

Write:

`showcase/student-v0.1/nombres-complexes/SOURCE_BASIS.md`

Record:

- exact source path and Git blob/SHA;
- source title/version/provenance already present in that file;
- supported objectives/concepts/examples;
- explicit limits: what you will **not** teach because this source does not support it.

If the source cannot honestly support a useful rich V4 journey, stop:

`HOLD_STUDENT_V01_JOB06_SOURCE_INSUFFICIENT`

Do not fabricate content to avoid HOLD.

---

## 3. Learner brief

Create a machine-readable learner brief under the showcase directory.

Target:

- French;
- one course;
- 30–45 total estimated minutes;
- coherent introductory/reinforcement journey for the learner level implied by the source;
- bounded objectives derived from the source;
- no backend/network dependency;
- no claim of complete curriculum coverage.

The brief must define what the learner should understand/do by the end, not which UI widgets must be used.

---

## 4. Author the V4 candidate

Create:

`showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v4.json`

Follow V4 identity/digest rules exactly.

Do not assume V2 lineage identity may be reused across a major successor contract unless current authority explicitly permits it. When continuity is not normatively defined, allocate fresh stable V4 identities and keep provenance externally.

### Cognitive-operation rule

Choose activity families by learner operation, not variety.

There is no eight-family quota.

However, a qcm/fill-only rewrite is not a Student V0.1 showcase. The final journey must genuinely use the new V4 richness where the source supports it.

Examples of legitimate choices only when source-supported:

- `lesson`: explain conjugate/module/geometric relation;
- `flashcard`: active recall of a compact property;
- `matching`: associate expressions/representations that form two conceptual sets;
- `order`: reconstruct a genuinely ordered calculation/reasoning method;
- `classify`: categorize several examples by a meaningful property;
- `constructed`: produce a bounded result/explanation when exact canonical responses remain legitimate.

Do not force any of these if the task is fake.

At minimum, the journey must demonstrate genuinely distinct cognitive operations beyond recognition/token fill. If the source cannot support that without distortion, HOLD rather than stuffing the kit.

### Learning structure

The sequence should have an intelligible progression such as:

explain/discover → retrieve → guided practice → independent practice → feedback/remediation → validation/transfer → close/review

but do not invent phases unsupported by current contract.

Lesson/flashcard never count as mastery or validation evidence.

---

## 5. Media

Media is optional.

If used:

- it must clarify a source-supported mathematical representation;
- it must be embedded/local;
- require alt text + pedagogicalRole;
- safe SVG only if SVG is chosen;
- no decorative asset merely to demonstrate media support;
- no remote URI.

Create a provenance entry showing exactly which source statement/concept supports the visual.

---

## 6. Provenance map

Create:

`showcase/student-v0.1/nombres-complexes/PROVENANCE_MAP.json`

For every V4 activity and asset, bind it to one or more exact source activity/objective/content references from the chosen canonical V2 source.

The map lives outside the kit. Do not invent provenance fields in the V4 contract.

Every new statement/example must be justified by that map.

---

## 7. Validate and challenge the content

Run the canonical V4 validator.

Require PASS.

Run pedagogical quality.

Require at least `STRONG`. Prefer `EXCELLENT_BY_PROFILE` if achievable **without** source distortion.

Explicitly challenge:

- exposure-heavy objective with no practice;
- quiz-only treatment of new material;
- repeated same-operation interface rehearsal;
- fake classify;
- meaningless order;
- unbounded/low-operation constructed response;
- validation contaminated by lesson/flashcard;
- media with no pedagogical value;
- total duration outside 30–45 minutes.

Do not modify validators to obtain PASS.

Store relevant deterministic reports under the showcase directory.

---

## 8. Factory binding without fake independence

Generate the exact Factory review context using:

- source = exact canonical V2 Nombres complexes source file;
- learner brief = your final brief;
- kit = your final V4 candidate.

Store the context/request under the showcase directory.

Do **not** fabricate an independent semantic-review PASS from the same author context.

Allowed semantic-review status for this job:

- `PASS_INDEPENDENTLY_BOUND` only if you can prove a genuinely separate reviewer context and exact source/brief/kit hash binding;
- otherwise `PENDING_INDEPENDENT_REVIEW_AT_G3_OR_LATER`.

The second state does not by itself fail JOB06. It is an explicit reservation for G3/JOB08/JOB09.

---

## 9. Final audit

Prove:

- duration = 30–45 min;
- canonical V4 = PASS;
- source traceability complete;
- no unsupported mathematical facts;
- activity families chosen by cognitive operation;
- at least meaningful V4 richness beyond qcm/fill;
- lesson/flashcard non-scored;
- media safe if present;
- quality >= STRONG;
- Factory context exact;
- no product/tool mutation;
- no sibling Wave 2 dependency.

Create:

`qualification/STUDENT_V01_JOB06_SHOWCASE_RESULT.md`

Return exactly:

```text
STUDENT_V01_JOB06_RESULT
WAVE2_COMMON_BASE: 281dc7470d51682c5e6d79d3fff54c46cfbced3b
QUALIFIED_PRODUCT_BASE: 8fa25844cf9ddf7c2429f730d818b3518c46de04
RESULT_SHA: <exact result sha>
ISSUE: 405
PR: <pr number>
SOURCE_SUFFICIENCY: PASS|FAIL
SOURCE_TRACEABILITY: PASS|FAIL
DURATION_30_45: PASS|FAIL
V4_CANONICAL: PASS|FAIL
COGNITIVE_FIT: PASS|FAIL
V4_RICHNESS: PASS|FAIL
NON_SCORED_BOUNDARY: PASS|FAIL
MEDIA_SAFETY: PASS|NOT_USED|FAIL
PEDAGOGICAL_QUALITY: EXCELLENT_BY_PROFILE|STRONG|WEAK|FAIL
FACTORY_CONTEXT: PASS|FAIL
SEMANTIC_REVIEW: PASS_INDEPENDENTLY_BOUND|PENDING_INDEPENDENT_REVIEW_AT_G3_OR_LATER|FAIL
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed verdicts:

- `PASS_STUDENT_V01_JOB06_SHOWCASE_READY_FOR_FANIN_B`
- `HOLD_STUDENT_V01_JOB06_SOURCE_INSUFFICIENT`
- `HOLD_STUDENT_V01_JOB06_CONTENT_NEEDS_REWORK`
- `FAIL_STUDENT_V01_JOB06_SCOPE_VIOLATION`
