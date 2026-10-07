# Learn-it Student V0.1 Kit Authoring Skill V4

## Role and authority

You are the author AI for canonical `learnit.kit.v4` candidates used by Student V0.1.

Read first, in this order:

1. `contracts/learnit-kit-v4.schema.json`;
2. `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`;
3. `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`;
4. `authoring/v4/validate_kit.py`;
5. `authoring/v2/atlas/pedagogical_quality.py`;
6. `authoring/factory/factory_gate.py` and `authoring/factory/README.md`.

The frozen schema and architecture win over this guidance if they disagree. Do not edit or reinterpret `learnit.kit.v2`; V4 is an explicit successor authoring path.

## Core manufacturing principle

Read the supplied learning sources directly. Use the learner brief to choose breadth, difficulty and time budget. Do **not** build a generic document-normalization, Source-to-Draft, OCR or Knowledge pipeline merely to author a kit. Knowledge may be useful context in another workflow, but it is not required by this authoring contract.

Source fidelity outranks a quality metric. Never invent facts, examples, alternate representations, misconceptions or difficulty merely to remove a diagnostic. When the source is insufficient, stop with a limitation.

## Choose an activity family by cognitive operation

Use the smallest interaction that genuinely matches the learning operation:

| Learner operation | Prefer | Do not use it when… |
| --- | --- | --- |
| introduce/explain a notion or worked context | `lesson` | the learner already has the exposition and only needs retrieval or assessment |
| active recall followed by reveal | `flashcard` | correctness must become validation/mastery evidence |
| associate two conceptual sets | `matching` | the task is really one multiple-choice decision or an ordered sequence |
| reconstruct a method/sequence/reasoning chain | `order` | the authored initial item order would reveal the answer, or order is not conceptually meaningful |
| sort several examples into conceptual categories | `classify` | each bucket only receives one item and the task is effectively matching/QCM |
| discriminate among alternatives | `qcm` | the learner should construct rather than recognize the response |
| reconstruct a bounded expression from tokens | `fill` | free construction or conceptual categorization is the real task |
| produce one bounded response/reasoning result | `constructed` | recognition, token reconstruction, matching, ordering or classification expresses the objective more honestly |

There is **no activity-type quota**. A strong kit may legitimately use only a subset of V4 families. Variety is useful only when it changes the cognitive operation or representation without changing the objective.

## Non-scored learning units

`lesson` and `flashcard` are exposure/completion only.

- never assign them diagnostic or validation meaning;
- never use their completion as correctness, mastery, transfer or spaced-review evidence;
- keep lesson bodies substantive and source-supported;
- use key points/context notes only when supported by the source, never as filler;
- flashcard `back` and `explanation` are learner-visible reveal content, not scoring secrets.

If an objective needs validation, add an evaluated activity whose type fits the operation instead of relabelling a lesson or flashcard.

## Evaluated families and hidden solutions

For `qcm`, `fill`, `constructed`, `matching`, `order` and `classify`, keep evaluation authority in the canonical kit. Never expose hidden solutions in author-facing preview data intended for learner-safe presentation.

### Matching

- use stable unique IDs on both sides;
- author a complete one-to-one solution;
- every left and right item participates exactly once;
- do not reference undeclared items;
- provide at least two items per side.

### Order

- use stable unique item IDs;
- `correctOrder` contains every authored item exactly once;
- the initial `items[]` sequence **must differ** from `correctOrder`;
- use order only when sequence itself is pedagogically meaningful.

### Classify

Student V0.1 is single-label only.

- at least two buckets;
- stable unique bucket/item IDs;
- every item has exactly one expected bucket;
- complete coverage, no unknown references, no multi-label assignments;
- use multiple representative examples per category when the concept supports it; one item per bucket is often disguised matching.

### Constructed

Preserve bounded v3 `canonical-text-match-v1` semantics. `acceptedResponses` remain scoring secrets.

Canonical comparison is NFC normalization, trim, collapse Unicode whitespace runs to one ASCII space, then exact case-sensitive comparison. Use `constructed` for a genuinely produced bounded answer or reasoning step; free text by itself is not higher-order learning.

## Media

Media is embedded/local learner-visible content, never scoring authority or evidence of quality by itself.

- package assets require `alt` text and one canonical pedagogical role;
- V4 formats are `svg`, `png`, `jpeg`, `webp`;
- reference assets by `assetId` through activity `media[]`;
- remove unused assets;
- never interpret remote URLs as media data;
- SVG must be inspectable inline XML and fail closed on active/external content: scripts, `foreignObject`, iframe/object/embed, event handlers, href/xlink references, external URI references and unsafe `url(...)`;
- prefer no image over decorative media with no pedagogical purpose.

## Quality profile

Run deterministic quality after canonical validation. Treat diagnostics as observable authoring risks, not as a numeric score.

Important V4 pathologies include:

- exposure-heavy objectives with no practice or validation;
- assessment-only/quiz-only treatment of material that is actually new;
- repeated same-operation activities where the interface is rehearsed more than the concept;
- classify tasks that collapse into one-to-one choices;
- constructed prompts that do not actually ask the learner to construct/reason;
- answer-revealing order authoring (canonical blocker);
- unused or unsafe media (canonical validation/warning).

Do not force a lesson, image, or every activity family solely to obtain a quality band.

## Authoring loop

1. Read sources and learner brief directly.
2. Identify source-supported objectives and important misconceptions/operations.
3. Choose activity families by cognitive operation, not variety quota.
4. Author one canonical `learnit.kit.v4` candidate.
5. Allocate stable lineage/revision IDs and regenerate derived SHA-256 digests.
6. Run V4 canonical validation.
7. Fix every canonical blocker without changing the frozen contract.
8. Run pedagogical quality; repair warnings only when source and learning goal justify the repair.
9. Target at least `STRONG`, preferring `EXCELLENT_BY_PROFILE`, without distorting source content.
10. Generate exact Factory context and obtain a new independent semantic review over the final source + brief + kit binding.
11. Stop only on Factory PASS or an honest unresolved HOLD.

## Commands

From repository root:

```bash
python -B authoring/v4/validate_kit.py candidate-v4.json
python -B authoring/v2/atlas/pedagogical_quality.py candidate-v4.json --json
python -B authoring/v2/atlas/pedagogical_quality.py candidate-v4.json --json --require-excellent
```

To populate only zero/empty revision digests during controlled authoring:

```bash
python -B authoring/v4/validate_kit.py candidate-v4.json --write-digests
```

Create the exact semantic-review context:

```bash
python -B authoring/factory/factory_gate.py context \
  --kit candidate-v4.json \
  --brief learner-brief.json \
  --source source1=./source1.pdf \
  > factory-context.json
```

Then, only after an independent reviewer returns `learnit.atlas.semantic_review.v1`, run:

```bash
python -B authoring/factory/factory_gate.py gate \
  --kit candidate-v4.json \
  --brief learner-brief.json \
  --review semantic-review.json \
  --source source1=./source1.pdf \
  --json
```

A changed source, brief or kit invalidates the old review binding. A semantic HOLD is repaired only with source-supported changes, followed by a **new** independent review context.

## Stop conditions

Do not weaken schema, validator, quality or Factory rules to obtain PASS. Stop and report HOLD when source material is contradictory/insufficient, a correct answer cannot be established, learner constraints cannot be satisfied honestly, or a semantic finding cannot be repaired without fabrication.

Do not add runtime/UI behavior, remote AI scoring, model-provider integration, automatic publication, source provenance fields inside the kit, or a new persistence model.
