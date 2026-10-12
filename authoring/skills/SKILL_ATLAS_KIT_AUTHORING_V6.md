# Atlas Kit Authoring V6 — PASSAGE release path

Status: candidate skill for `learnit.kit.v6` release hardening.

Author only against the exact V6 contract and validator identities bound by the current governed work package. `constructed` and `productive` remain schema-readable for historical compatibility, but both are disabled for all new V6 Factory production and release admission. New authoring MUST NOT generate either family. The exact policy reasons are `ACTIVITY_TYPE_DISABLED:constructed` and `ACTIVITY_TYPE_DISABLED:productive`. Do not automatically convert or rewrite historical kits merely because either family is now production-disabled.

Role B sources are the authoring source of truth. Every Role B source must be explicitly authorized, have exact bytes and SHA-256, provenance, and claim identifiers included in the source-set binding. A web source may be used only after bounded authoring-time admission; the Factory gate performs no web fetch. Role A learner references are optional, supplemental, and may never become a hidden source of truth.

## Resolve learning intent before authoring

Before writing any activity, inspect the authorized Role B sources enough to identify a concise candidate objective scope. Expose to the human, in plain language, the proposed objectives/scope, recommended learning mode, prior-knowledge assumption, time budget, and any material recommendation to split or re-scope. Infer choices already explicit in the request; never make the human repeat known information. Ask only for materially missing or ambiguous choices, preferably in one compact interaction rather than a questionnaire.

The existing learner brief remains the sole durable pre-authoring context object. For new V6 production it MUST contain `learningIntent` with exactly `mode`, `priorKnowledge`, `objectiveScope`, `objectiveScopeConfirmed`, and `confirmationBasis`. Modes are `DISCOVERY`, `REVISION`, `EXAM`, `EXPLORATION`, `COMPLETE`; prior knowledge is `NOVICE`, `PARTIAL`, `STUDIED`, or `AUTO`. `objectiveScope` is the non-empty unique list of concise objectives actually exposed to and confirmed by the human. Set `objectiveScopeConfirmed=true` only after a valid confirmation basis applies.

Use `confirmationBasis=EXPLICIT_USER_DIRECTIVE` only when the original directive already unambiguously specifies the same material choices and explicitly requests immediate creation; this avoids a redundant extra turn. Otherwise require the human to confirm or correct the proposal and use `confirmationBasis=USER_CONFIRMED_PROPOSAL`. The interaction itself is not a new durable transcript artifact: its durable result is the learner brief already bound by `briefSha256`.

## Mode semantics

For `DISCOVERY`, assume the learner may be new: segment dense concepts into small coherent units, pretrain essential vocabulary or representations when needed, use source-supported worked or partially worked examples for procedural/calculation skills when pedagogically useful, move from guidance toward independence, keep independent validation genuinely independent, and avoid long front-loaded exposition across many unstabilized objectives.

For `REVISION`, start primarily from retrieval/application rather than replaying the whole course, remediate gaps concisely after they are exposed, revisit or interleave related objectives when the confirmed source/scope permits, and emphasize independent recall/application over exposition.

For `EXAM`, treat the kit as exam preparation or assessment practice, never certification. Do not reveal answers or give teaching hints before an assessed response. Prefer representative autonomous and multi-objective tasks when supported by the sources; explanatory feedback after an attempt is allowed. Never claim proctoring, certification, or prediction of an official grade.

For `EXPLORATION`, optimize for intelligibility, curiosity, useful phenomena/questions/connections, and learner choice where possible. Selective coverage is allowed only within the human-confirmed scope. Do not imply exhaustive mastery or exam readiness from exploration alone; low-stakes checks may sustain understanding but must not manufacture a mastery claim.

For `COMPLETE`, compose a coherent path from explanation/discovery through guided and independent practice to cumulative or exam-style validation. Do not compress an implausibly broad path into a monolith merely to fit the time budget. If the confirmed scope cannot reasonably support that full path within `timeBudgetMinutes`, return to the human with the smallest sensible split or re-scope before authoring.

These mode rules never weaken the active V6 activity policy: new `constructed` and `productive` remain disabled.

V6 media is embedded in the kit. Preserve meaningful media and required `alt` text. Do not add remote media, image search, OCR, renderer services, or decorative-media requirements. When an objective materially requires interpreting a visual representation, author enough exact embedded media for an independent reviewer to judge `visualAdequacy=pass`; otherwise the review must hold.

Before Factory submission, bind the exact kit bytes, learner brief, authorized source inventory and source-set digest. Any later kit/brief/source change—including a change to learning mode, prior knowledge, objective scope or time budget—invalidates the semantic review target and requires a new independent review.
