# Student V0.1 — Activity Richness Architecture

## Decision

**Select `learnit.kit.v4` as the explicit activity-richness successor.**

`learnit.kit.v2` and `learnit.kit.v3` remain immutable in meaning. Student V0.1
does not silently widen either published contract.

The target learner grammar is:
`lesson`, `flashcard`, `matching`, `order`, `classify`, plus existing `qcm`,
`fill`, `constructed`; `media` is a transverse capability.

## Why

- v2 intentionally proved the clean-generation foundation with qcm/fill.
- v3 proves a bounded constructed-response seam.
- RC718 is useful evidence that flashcard/matching/order/media are viable, but is
  not a migration base.
- The current goal is now a real learning journey, not only a quiz loop.
- Multiple genuinely different interactions now justify a small typed presenter
  boundary, but still do not justify a plugin runtime.

## Cognitive purpose

| Family | Purpose | Scored in Student V0.1 |
|---|---|---:|
| lesson | explain/expose a notion, key points, context | no |
| flashcard | active recall followed by reveal | no |
| matching | associate two conceptual sets | yes |
| order | reconstruct method/sequence/reasoning | yes |
| classify | distribute items into categories | yes |
| qcm | discriminate among alternatives | yes |
| fill | reconstruct a bounded expression | yes |
| constructed | produce bounded free text | yes |

`lesson` and `flashcard` completion is exposure/completion only. It must never be
used as validation/mastery evidence.

## Ownership

Canonical kit
→ Learning semantics
→ Session orchestration
→ learner-safe ActivityPresentation
→ type-specific presenter
→ ActivityResponse
→ Learning evaluation

The learner-safe presentation never contains:
- QCM correctChoiceId;
- fill answers;
- constructed acceptedResponses;
- matching matches;
- order correctOrder;
- classify assignments.

UI owns interaction mechanics only.

## First-slice response shapes

- lesson -> `{acknowledged:true}`
- flashcard -> `{revealed:true}`
- qcm -> existing `{choiceId}`
- fill -> existing slot mapping
- constructed -> existing `{text}`
- matching -> `{associations:[{leftItemId,rightItemId}]}`
- order -> `{orderedItemIds:[...]}`
- classify -> `{assignments:[{itemId,bucketId}]}`

## Classify

First slice is single-label only. Every item has exactly one authored bucket.
Multi-label classification is explicitly deferred. JSON Schema constrains shape;
semantic validation must additionally enforce ID uniqueness, coverage and exactly
one assignment per item.

## Presenter boundary

Allowed internal seam:

`projectActivityPresentation(sourceActivity)`
`renderActivityPresentation(presentation)`
`readActivityResponse(container, presentation)`

Type-specific modules are allowed for ownership/testability. Dynamic plugin
registration, event buses, evaluator registries and remote loading are not.

## Media

v4 adds package-level embedded image assets and per-unit media references.

Allowed:
- SVG
- PNG
- JPEG
- WebP

No remote URL field in Student V0.1. Every asset requires alt text and a
pedagogical role. SVG handling must fail closed against scripts, foreignObject,
iframes, event handlers, external hrefs and active/external references.

Media is learner-visible content, never scoring authority.

## Constructed

v4 preserves the v3 bounded semantics: local deterministic
`canonical-text-match-v1`; `acceptedResponses` remain behind the learner-safe
boundary.

PR #376 is reference evidence only. It is not merged/cherry-picked by this
architecture job.

## Compatibility

- v2 = qcm/fill.
- v3 = qcm/fill/constructed.
- v4 = qcm/fill/constructed + lesson/flashcard/matching/order/classify + media.
- no automatic package rewrite/migration.
- future runtime admission is explicit and fail-closed by discriminator.

## Execution topology

JOB 00 architecture + contract freeze
→ WAVE 1: JOB 01 Learning/runtime || JOB 02 Presentation/UI || JOB 03 Authoring/Factory
→ JOB 04 controlled fan-in A
→ WAVE 2: JOB 05 contradictory QA || JOB 06 showcase kit || JOB 07 pilot UX/package
→ JOB 08 controlled fan-in B / exact candidate
→ JOB 09 human replay / student-readiness
→ 5–6 real student sessions

Knowledge-assisted authoring remains outside the Student V0.1 critical path.

## Wave 1 ownership

All three Wave 1 jobs branch from the same exact merged Job 00 architecture head.
The v4 schema and architecture docs are read-only shared authority.

- JOB 01: Learning/session/import semantics + own tests.
- JOB 02: learner-safe rendering, response collection, accessibility/media
  presentation + own tests.
- JOB 03: authoring validators, skill, Factory, quality, Studio preview + own tests.
- JOB 04 alone owns build/source-manifest/central workflow fan-in.

If a worker discovers a contract defect, it stops and returns to architecture
instead of silently editing v4.

## Explicit non-goals

No backend, accounts, cloud catalog, remote AI scoring, generic activity plugin
framework, event bus, new persistent execution model, Knowledge dependency or
RC718 migration layer.

## Gate

This package is ready only for a human architecture decision. It does not itself
authorize product implementation or student use.
