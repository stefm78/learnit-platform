# /AUDIT /SOLVE /BUILD — JOB 03
## Student V0.1 — Authoring / AI Kit Factory / pedagogical quality

You are an independent Wave 1 implementation worker.

Do not inspect or depend on JOB 01/JOB 02 branches. Your authority is the frozen shared main architecture/contract only.

Repository: `stefm78/learnit-platform`
Authority issue: `#385`
Work package: `ATLAS-WP-029`
Pre-created branch: `student-v01/wave1-authoring-factory`

## 0. Reconstruct exact authority

Before editing:

1. fresh-read current control-plane/kernel authority required by the installed bootstrap;
2. fresh-read repository `main`;
3. verify main contains merged ARC-WP-025, `learnit.kit.v4`, the Wave 1 launch package and interface freeze;
4. verify your branch started from the exact same common Wave 1 launch base and contains no product change from another role;
5. bind that exact commit into `ATLAS-WP-029.baseline.requiredCommonWave1Base`.

Read as normative:
- `contracts/learnit-kit-v4.schema.json`
- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
- `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`
- `docs/programs/student-v0.1/WAVE1_HANDOFF.md`
- `docs/atlas/M3_1_PEDAGOGICAL_QUALITY_ENGINE_DESIGN.md`
- `docs/atlas/M3_2_AI_KIT_FACTORY_DESIGN.md`
- `work-packages/ATLAS-WP-029.json`

Read historical RC718 authoring skill/capabilities only as evidence for matching/order/flashcard/media patterns. Do not migrate its package/storage identity model.

## 1. Mission

Create an explicit v4 authoring path able to produce, validate and quality-check rich Student V0.1 kits without silently redefining the existing V2 authoring path.

You own:
- v4 canonical semantic validation on top of the frozen JSON Schema;
- V4 AI authoring skill/guidance;
- M3.1 pedagogical-quality compatibility for v4;
- AI Kit Factory gate compatibility for v4;
- authoring/factory tests.

You do **not** own learner runtime, UI, contracts, workflows, source-manifest fan-in or Student showcase content.

## 2. Preserve the existing authoring baseline

Do not edit:
- `authoring/v2/validate_kit.py`;
- `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V2.md`.

Create an explicit V4 path instead. Reuse stable helpers by import only where doing so does not alter V2 semantics.

Existing V2 kits and Factory evidence must remain valid.

## 3. V4 canonical semantic validator

Schema validation is necessary but not sufficient. Add deterministic semantic checks for at least:

### common identity/integrity
- UUID/reference consistency;
- revision/digest rules consistent with successor architecture;
- objective references exist;
- media references resolve to package assets;
- no unused/unsafe media where existing policy requires rejection/warning.

### lesson
- no assessment role/scoring secret;
- substantive learner-facing body;
- optional key points/context are source-supported, not filler.

### flashcard
- front/back/explanation present;
- non-scored only;
- cannot satisfy validation or diagnostic evidence.

### matching
- unique left/right IDs;
- complete one-to-one solution;
- every left and right item participates exactly once;
- no unknown IDs;
- enough items to constitute a meaningful association task.

### order
- unique item IDs;
- `correctOrder` contains every item exactly once;
- authored initial `items[]` ID order must **not** equal `correctOrder`;
- reject trivial one-item ordering.

### classify
- unique bucket/item IDs;
- at least two buckets;
- every item has exactly one expected bucket;
- no unknown bucket/item IDs;
- assignments cover all items exactly once;
- multi-label is rejected in Student V0.1.

### constructed
Preserve v3 bounded accepted-response requirements and canonical-text-match assumptions.

### media
- embedded/local only;
- SVG/PNG/JPEG/WebP only;
- alt + pedagogical role required;
- unsafe/active SVG rejected fail-closed;
- no remote source/URL interpretation.

## 4. Pedagogical quality

Extend M3.1 carefully so richer interaction is rewarded only when pedagogically justified.

Important distinctions:
- `lesson` / `flashcard` = learning exposure/activation, not validation evidence;
- matching/order/classify may be practice or assessment depending on `assessmentRole` and learning phase;
- constructed can provide higher-order evidence only when the prompt actually requires construction/reasoning;
- media is not quality by itself; it must have a pedagogical role;
- variety is not a quota.

Do not create a rule such as “every kit must contain every activity type”.

A strong course may still use only the types suited to its objectives.

The quality engine should be able to flag pathologies such as:
- quiz-only course with no meaningful exposition for a genuinely new topic;
- lesson-heavy course with no practice/validation;
- repetitive same-operation activities;
- fake classification that is just a disguised QCM;
- order activity whose answer is already displayed in the initial order;
- decorative media with no pedagogical role.

Keep diagnostics deterministic and machine-readable.

## 5. V4 authoring skill

Create `SKILL_ATLAS_KIT_AUTHORING_V4.md` as an explicit successor skill.

It must teach an AI author to choose interaction by cognitive operation, for example:

```text
introduce/explain a notion     -> lesson
active recall                  -> flashcard
associate concepts             -> matching
reconstruct a method/sequence  -> order
sort examples into categories  -> classify
discriminate alternatives      -> qcm
reconstruct bounded expression -> fill
produce own bounded response   -> constructed
```

Also state when **not** to use each type.

Preserve the M3.2 principle: read supplied sources directly; do not invent a generic document-normalization/Source-to-Draft platform. Knowledge-assisted authoring remains optional and outside this job.

## 6. Factory integration

Extend the deterministic Factory path only as much as needed to consume a canonical v4 candidate and its pedagogical-quality report.

Preserve:
- source identity/freeze;
- canonical validation before quality;
- semantic/source-fidelity review;
- PASS/HOLD semantics;
- no provider/network dependency;
- no automatic publication.

Do not make richer activity variety a substitute for semantic review.

Do not weaken current v2 Factory evidence or release-set rules.

## 7. Write boundary

Change only paths authorized by `ATLAS-WP-029.json`.

No edits to:
- `contracts/**`;
- `apps/**`;
- `.github/**`;
- existing V2 authoring validator or V2 authoring skill.

JOB 04 owns integration-only files.

## 8. Qualification

At minimum create deterministic tests proving:
- representative valid v4 kit passes;
- every new activity family has at least one adversarial invalid fixture/check;
- order answer exposure is rejected;
- classify missing/duplicate/multi-label assignment is rejected;
- matching incomplete/duplicate mappings are rejected;
- lesson/flashcard cannot count as validation evidence;
- unsafe media is rejected;
- pedagogical quality can distinguish exposition/practice/validation without activity-type quota;
- Factory gate accepts a correctly qualified v4 candidate and still HOLDS on failed semantic review;
- existing v2 authoring/factory tests remain green.

Do not change runtime/UI to satisfy authoring tests.

## 9. PR / handoff

Use the pre-created branch and its existing draft PR if present. Do not merge.

Return exactly one verdict:

`PASS_STUDENT_V01_JOB03_AUTHORING_FACTORY_READY_FOR_FANIN_A`

`HOLD_STUDENT_V01_JOB03_AUTHORING_FACTORY_NEEDS_REWORK`

`FAIL_STUDENT_V01_JOB03_AUTHORING_SEMANTICS_UNSAFE`

Final block:

```text
STUDENT_V01_JOB03_RESULT
BASE_SHA: <exact common Wave1 base>
RESULT_SHA: <exact head>
ISSUE: 385
PR: <number>
V4_VALIDATOR: <PASS|FAIL>
NEW_ACTIVITY_SEMANTICS: <PASS|FAIL>
PEDAGOGICAL_QUALITY: <PASS|FAIL>
FACTORY: <PASS|FAIL>
V2_REGRESSION: <PASS|FAIL>
MEDIA_VALIDATION: <PASS|FAIL>
SCOPE: <PASS|FAIL>
FINAL_VERDICT: <exact token>
```
