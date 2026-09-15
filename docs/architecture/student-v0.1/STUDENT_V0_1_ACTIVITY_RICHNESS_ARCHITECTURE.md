# Student V0.1 — Activity Richness Architecture

Work package `ARC-WP-025` · owner issue `#380` · exact design baseline `1e71271436fd4b7dd7d895cfec827833187630fe` · candidate `learnit.kit.v4` · design only · human gate required.

Verdict: `PASS_STUDENT_V0_1_ARCHITECTURE_READY_FOR_HUMAN_GATE`

## 1. Reconstructed authority

Issue #380 reopens only the smallest architecture gate needed for a richer learner-facing successor. `governance/governor-state.json` still records the earlier post-M3.4 `STOP_AND_OBSERVE` posture; it is deliberately not edited. Product implementation therefore remains blocked until this architecture candidate is human-accepted and merged through governance.

The decision was rebuilt from current `GOVERNANCE.md`, governor state, `STANDALONE_TO_PLATFORM.md`, `FOUNDATION_V1.md`, `MULTI_AI_EXECUTION_V1.md`, `CONSTRUCTED_RESPONSE_CONTRACT_V3.md`, `ARC-WP-024`, `ATLAS-WP-025`, v2/v3 schemas and the current Learn-it Next `ActivityPresentation` seam. RC718 material is historical evidence only. PR #376 is unmerged product evidence only; no content from it is incorporated.

## 2. Contract version

| Option | Result |
| --- | --- |
| A — silently expand v3 | **Reject.** Changes a published discriminator's meaning by reader age. |
| B — explicit `learnit.kit.v4` | **Select.** Explicit opt-in; v2/v3 meanings stay fixed. |
| C — v3 + out-of-band plugin/capability | **Reject.** Splits canonical validation/digest authority and invites an unjustified runtime framework. |

No v2/v3 package is rewritten, migrated, reclassified or re-digested.

## 3. Frozen grammar

v4 admits exactly: `lesson`, `flashcard`, `qcm`, `fill`, `matching`, `order`, `classify`, `constructed`. `media` is transverse, not an activity.

Each added family has a distinct learner action: consume structured explanation; recall then reveal; associate relations; reconstruct sequence; apply category boundaries. No generic plugin protocol, evaluator registry, marketplace or event bus is authorized.

## 4. Ownership boundary

```text
canonical v4
-> Learning semantic authority
-> Session orchestration
-> learner-safe ActivityPresentation
-> closed type-specific UI presenter
-> ActivityResponse
-> Learning evaluation / non-evaluated completion
```

UI never owns correctness. Session never owns raw DOM mechanics. Presenter replacement must not alter kit semantics. The presenter boundary is a closed internal dispatch over the eight types, not dynamic extensibility.

The following secrets never cross into ActivityPresentation: qcm `correctChoiceId`, fill `answers`, matching `matches`, order `correctOrder`, classify `correctBucketId`, constructed `acceptedResponses`.

## 5. Frozen family contracts

| Type | Authored secret / special data | Learner-safe presentation | ActivityResponse | Semantics |
| --- | --- | --- | --- | --- |
| lesson | `title`, `body`, `keyPoints`, optional `contextualNote`; **no assessmentRole** | same learner content + safe media | `{completed:true}` | explicit continue records exposure/completion only; never correctness/mastery |
| flashcard | `front`, `back`; **no assessmentRole** | front/back + safe media; back initially hidden | `{revealed:true}` | complete after reveal; no scoring; no validation/diagnostic evidence |
| qcm | hidden `correctChoiceId` | prompt + choice IDs/labels + safe media | `{choiceId}` | existing exact choice-ID behavior |
| fill | hidden `answers` | segments/tokens + safe media | slotId→tokenId mapping | existing deterministic mapping behavior |
| matching | hidden `matches` | left/right item IDs+labels | `{matches:[{leftItemId,rightItemId}]}` | exact complete one-to-one mapping |
| order | hidden `correctOrder` | item IDs+labels | `{itemIds:[...]}` | exact complete sequence |
| classify | each item has hidden `correctBucketId` | item/bucket IDs+labels | `{assignments:[{itemId,bucketId}]}` | exact single-label mapping |
| constructed | hidden `acceptedResponses` | prompt + safe media | `{text}` | v3 `canonical-text-match-v1` unchanged |

### Lesson

`assessmentRole` and scoring-secret fields are schema-forbidden. Completion occurs only after presentation plus explicit learner continue. It is not evidence of validation, mastery, retention or transfer.

### Flashcard

`assessmentRole` is schema-forbidden; diagnostic/validation learning phases are also forbidden. `back` is reveal content, not a scoring key, so it may exist in learner-safe presentation but must initially be hidden. No correctness boolean is produced.

### Matching

Stable left/right item IDs are required. Semantic validation must enforce unique IDs, equal non-zero cardinalities, complete coverage and a bijection: each left and right item appears exactly once in hidden `matches`; all references resolve. The learner response must also be a complete bijection before exact set comparison.

### Order

Stable item IDs are required. Semantic validation must make hidden `correctOrder` an exact permutation of all declared item IDs. The learner response must be a complete permutation before exact sequence comparison.

### Classify

Student V0.1 is single-label only. Every authored item structurally requires exactly one `correctBucketId`. Semantic validation must enforce unique item/bucket IDs and that every `correctBucketId` references a declared bucket. The learner response must contain exactly one assignment per item, with no unknown IDs, before exact mapping comparison.

### Constructed

Carry forward v3 unchanged: response `{text}`; blank-after-normalization fails closed; 4,000-character bound; `canonical-text-match-v1` = Unicode NFC, trim, collapse Unicode whitespace runs to one ASCII space, then case-sensitive exact equality against one normalized accepted response.

## 6. Media slice

v4 adds package-level `assets[]`. Every asset has stable `assetId`, `type:"image"`, format `svg|png|jpeg|webp`, embedded `data`, `encoding:"utf8"` for SVG or `"base64"` for raster, required non-empty `alt`, bounded `pedagogicalRole`, optional caption. Activities use bounded `media[]` refs.

There is deliberately no `src`, `url`, `source`, fetch or remote-dependency field. Semantic validation rejects unresolved asset refs and malformed encoding.

SVG implementation must reuse RC718's proven fail-closed principles: declarative allowlist; reject script, `foreignObject`, iframe, external image/use/href, event attributes, executable/remote style and external `url(...)`; no network retrieval; sanitize/validate before learner-safe presentation. RC718 identity/storage models are not reused.

## 7. Identity/digest

Clean-generation identity remains: stable UUIDv4 lineage/revision IDs independent of labels/order/content; authored array order preserved in canonical JSON; deterministic SHA-256 revision digests with the object's own digest omitted. v4 package digest covers `assets[]`, embedded data and media refs.

Semantic validation also rejects duplicate IDs, unresolved objective/media/solution refs, revision-ID/digest conflicts and incomplete matching/order/classify solutions.

## 8. Presenter seam

Multiple genuinely different controls now justify one small typed presenter boundary:

```text
ActivityPresentation type -> render controls -> read ActivityResponse
```

It must not load presenters dynamically, receive evaluator callbacks or canonical activities with secrets, become a second semantic validator, or define persistence/evidence policy.

The current topology is sufficiently separated for parallel implementation against the frozen interface. Wiring/build/source-manifest/workflow changes remain Fan-in A responsibilities.

## 9. Parallel program

After human acceptance **and merge**, all Wave 1 workers bind to the same exact architecture merge commit and frozen v4 schema:

- JOB 01 — Learning/runtime semantics.
- JOB 02 — Activity presentation/UI.
- JOB 03 — Authoring/Factory/quality.

Their writable scopes are frozen in `WAVE1_HANDOFF.md` and pairwise disjoint. JOB 04 integrates exact reviewed results and alone owns shared build/source-manifest/workflow wiring; no silent repairs.

Wave 2 starts from exact JOB 04 head: JOB 05 contradictory QA, JOB 06 real student showcase kit, JOB 07 pilot packaging/UX. JOB 08 performs exact Fan-in B + qualification. JOB 09 is human replay/readiness. Only a later explicit authority may permit 5–6 student sessions. Knowledge-assisted authoring stays outside the critical path.

## 10. Adversarial gate

PASS requires proof that:

- v2 and v3 schema blobs are unchanged from baseline;
- v4 is valid Draft 2020-12 JSON Schema and rejects unknown activity types;
- lesson rejects `assessmentRole` and known scoring secrets;
- flashcard rejects `assessmentRole`, validation and diagnostic use;
- matching/order/classify learner presentations contain no hidden solutions;
- classify has one authored expected bucket per item plus semantic response/reference completeness rules;
- media rejects remote source fields;
- candidate diff contains exactly the seven ARC-WP-025 outputs and no app/product/authoring/workflow/governor-state path;
- no backend/account/provider/runtime-AI/plugin/event-bus capability is introduced;
- Wave 1 writable scopes are pairwise disjoint.

`PASS_STUDENT_V0_1_ARCHITECTURE_READY_FOR_HUMAN_GATE` means **ready for accountable human architecture acceptance only**. It does not authorize merge, Wave 1, PR #376, product promotion or student use.
