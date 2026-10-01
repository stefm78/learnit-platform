# LearnIT Kit V6 — Release-Grade Mastery Contract

V6 is an opt-in successor. It does not reinterpret or migrate learnit.kit.v2 through learnit.kit.v5.

## A/B mastery evidence

Every V6 activity with `assessmentRole=validation` targets exactly one objective and declares `validationSlot=A|B`.
One correct slot is not mastery. `mastery-evidence-complete` requires correct A and B evidence. A failed validation or failed remediation path invalidates stale evidence conservatively.

## Productive activity

`type=productive` is one coherent learner task containing ordered response parts. Public parts expose only prompt, label, response kind and optional unit prompt. The `scoring` object is authoritative scoring-secret data and never crosses ActivityPresentation.

Closed evaluator kinds are:

- `numeric-tolerance`: exact decimal input is converted to a rational and compared locally to an authored rational value with authored absolute tolerance and optional accepted units.
- `canonical-expression-set`: one expression part is compared after NFC, minus and whitespace normalization to a bounded authored set.
- `required-concepts`: one explanatory text part must contain at least one bounded literal alias from each authored concept group after deterministic text normalization.

Aggregation is exactly `all`. Unknown evaluators fail closed. No remote, LLM, probabilistic or plugin-registry evaluator is part of V6.

## Compatibility

Existing V2–V5 activity semantics, constructed canonical-text matching, package identities and learner-safe secret boundaries remain unchanged. Multi-objective activities remain consolidation/transfer evidence only for local mastery. Fresh-variant capacity, adaptive routing and delayed scheduling remain authoring constraints outside this engine delta.
