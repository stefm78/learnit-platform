# /AUDIT /SOLVE /BUILD — JOB 00
## Learn-it Student V0.1 — Activity Richness Architecture Freeze

You are the architecture owner for one bounded design-only gate.

Your output must make the next parallel implementation wave safe. Do not implement
learner/runtime/authoring product code in this job.

Repository:
`stefm78/learnit-platform`

Owner issue:
`#380`

Observed current main while this job was prepared:
`1e71271436fd4b7dd7d895cfec827833187630fe`

Re-read current `main` before acting. The observed SHA is not sovereign if it moved.

## 0. GOVERNANCE / EVIDENCE BOUNDARY

Reconstruct current repository authority before decisions.

Read at least:
- `GOVERNANCE.md`
- `governance/governor-state.json`
- `docs/roadmap/STANDALONE_TO_PLATFORM.md`
- `docs/architecture/clean-generation/FOUNDATION_V1.md`
- `docs/architecture/clean-generation/MULTI_AI_EXECUTION_V1.md`
- `docs/architecture/clean-generation/CONSTRUCTED_RESPONSE_CONTRACT_V3.md`
- `work-packages/ARC-WP-024.json`
- `work-packages/ATLAS-WP-025.json`
- `contracts/learnit-kit-v2.schema.json`
- `contracts/learnit-kit-v3.schema.json`
- current learner-safe `ActivityPresentation` seam in Learn-it Next.

Use historical RC718 only as evidence, never as successor authority:
- `apps/player/authoring/SKILL_CURRENT.md`
- `apps/player/contract/learnit-capabilities.json`
- `apps/player/contract/learnit-import.schema.json`
- stable historical flashcard/matching/order/media implementation/tests.

Known evidence to revalidate:
- RC718 had stable qcm, fill, matching, order, flashcard and bounded media.
- Successor v2 intentionally reduced the first slice to qcm/fill.
- v3 adds bounded `constructed`.
- PR #376 is an unmerged constructed-response product candidate. Treat it as
  reference evidence only; do not merge/cherry-pick it in this job.
- current architecture already separates:
  Learning semantics -> Session orchestration -> learner-safe ActivityPresentation
  -> UI interaction -> ActivityResponse -> Learning Evaluation.

## 1. MISSION

Define the smallest coherent successor architecture that is rich enough to support
a real 30–45 minute learner journey before the first student pilot.

Evaluate and, if justified, freeze this target grammar:

- `lesson`: first-class non-scored learning/exposition card; explanation, key
  points, optional contextual/historical note; may carry media; viewing is
  exposure/completion, never mastery.
- `flashcard`: active recall/reveal; no answer-key scoring in Student V0.1;
  excluded from validation/diagnostic evidence; may carry media.
- `matching`: associate items from two sets.
- `order`: reconstruct an ordered method, sequence or reasoning.
- `classify`: distribute items into buckets; first slice single-label only.
- existing `qcm`, `fill`, `constructed`.
- `media`: transverse capability, not an activity family.

Do not add a type merely for variety. Each admitted family must correspond to a
distinct cognitive interaction.

## 2. CONTRACT-VERSION DECISION

Explicitly compare:
A. silently expand `learnit.kit.v3`;
B. create explicit `learnit.kit.v4`;
C. keep v3 and add an out-of-band capability/plugin format.

Preserve existing v2 and v3 meanings. Do not make published contract meaning
depend on reader age.

Expected hypothesis to challenge:
`learnit.kit.v4` is the smallest safe successor.

## 3. OWNERSHIP BOUNDARY

Preserve and generalize only as much as evidence justifies:

Canonical kit semantics
→ Learning evaluation / non-evaluated completion semantics
→ Session orchestration
→ learner-safe ActivityPresentation
→ type-specific UI presenter
→ ActivityResponse
→ Learning evaluation

Rules:
- answer keys / correct mappings / correct order / bucket assignments /
  acceptedResponses never cross into learner-safe presentation;
- UI never owns correctness;
- session never owns raw DOM mechanics;
- presentation must be replaceable without changing the kit;
- do NOT build a dynamic plugin loader, registry marketplace, event bus or generic
  evaluator framework;
- a small internal typed presenter boundary is allowed if multiple genuinely
  different interactions now justify it.

## 4. FIRST-SLICE SEMANTICS TO FREEZE

Freeze authored shape, learner-safe presentation, response shape and
evaluation/completion semantics for every family.

Required minimum:
- lesson: non-scored, no assessmentRole, completion != mastery.
- flashcard: reveal, non-scored, no validation/diagnostic role.
- matching: stable item IDs, exact one-to-one hidden solution.
- order: stable item IDs, exact hidden correct order.
- classify: stable item/bucket IDs, exactly one expected bucket per item.
- constructed: preserve v3 canonical-text-match-v1 and secret acceptedResponses.
- qcm/fill: preserve existing behavior.

## 5. MEDIA BOUNDARY

Design a bounded first media slice:
- package-level assets;
- per-unit media references;
- svg/png/jpeg/webp;
- required alt text and pedagogical role;
- embedded/local deterministic assets only;
- no remote URL dependency.

Reuse proven RC718 SVG fail-closed principles where applicable. Do not copy
legacy identity or storage models.

## 6. PARALLEL PROGRAM DESIGN

Prepare safe execution after human acceptance.

WAVE 1 — max 3 parallel workers, same exact merged architecture base, disjoint
write scopes:
- JOB 01 — Learning/runtime semantics
- JOB 02 — Activity presentation/UI
- JOB 03 — Authoring/Factory/quality

FAN-IN A:
- JOB 04 — controlled integration of exact reviewed JOB 01–03 results;
- no silent repairs.

WAVE 2 — max 3 parallel workers on exact FAN-IN A head:
- JOB 05 — contradictory QA
- JOB 06 — real student showcase kit
- JOB 07 — student pilot packaging/UX

FAN-IN B:
- JOB 08 — exact candidate integration + qualification

HUMAN GATE:
- JOB 09 — human replay / student-readiness acceptance

Then only:
- first 5–6 real student sessions.

Knowledge-assisted authoring stays outside this critical path.

## 7. FILE OWNERSHIP

The architecture job may only change its declared architecture/program paths.
It must not modify runtime, authoring implementation, workflows, current v2/v3
schemas or governor state.

Wave 1 handoff must define disjoint ownership. Build/source-manifest/workflow
fan-in files remain integrator-owned.

If current topology makes perfect disjointness impossible, say so and choose the
smallest preparatory seam rather than pretending concurrency is safe.

## 8. OUTPUTS

Produce exactly:
1. `work-packages/ARC-WP-025.json`
2. `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
3. `contracts/learnit-kit-v4.schema.json`
4. `docs/programs/student-v0.1/PROGRAM_CHARTER.md`
5. `docs/programs/student-v0.1/COORDINATION.yaml`
6. `docs/programs/student-v0.1/WAVE1_HANDOFF.md`
7. `docs/programs/student-v0.1/jobs/JOB_00_ARCHITECTURE_FREEZE.md`

Create an architecture-only branch and DRAFT PR from exact current main.
Do not merge it.

## 9. REQUIRED ADVERSARIAL CHECKS

Prove at minimum:
- v2 schema unchanged;
- v3 schema unchanged;
- v4 rejects unknown activity types;
- lesson cannot carry scoring secrets;
- flashcard cannot carry validation/diagnostic assessment role;
- matching/order/classify learner-safe presentations expose no solutions;
- classify semantic validator must enforce one bucket per item;
- media contract has no remote source field;
- no product/app/authoring/workflow path changed;
- no backend/account/provider/runtime-AI capability introduced;
- Wave 1 writable scopes are disjoint.

## 10. FINAL VERDICT

Return exactly one:
`PASS_STUDENT_V0_1_ARCHITECTURE_READY_FOR_HUMAN_GATE`
`HOLD_STUDENT_V0_1_ARCHITECTURE_NEEDS_REWORK`
`FAIL_STUDENT_V0_1_ACTIVITY_RICHNESS_NOT_JUSTIFIED`

PASS means architecture/program package ready for human acceptance only. It does
not authorize merge, Wave 1, product promotion or student use.
