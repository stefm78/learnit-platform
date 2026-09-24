# learnit.kit.v5 — Contract Delta (R2 Handoff 1)

Status: candidate contract for `ATLAS-WP-055`. This document does not authorize runtime/UI, authoring Factory/source governance, V8, showcase port, fan-in, merge or promotion.

## Authority and base

- Human R2 decision: issue #431 comment `5817817692` — `GO_PRE_PILOT_V5`.
- Exact base: `student-v01/fanin-b@18b925436777943b19c4b031c24659ad60dee133`.
- V4 remains byte- and meaning-immutable.
- No automatic V4 -> V5 rewrite exists.

## Exact successor

V5 uses the explicit root discriminator:

```json
{"contract":"learnit.kit.v5"}
```

All V4 package/course/activity identity fields, activity families, scoring fields, assets and media semantics are carried forward unchanged unless listed below.

## Activity-level hints

Every V5 activity family may optionally contain:

```json
"hints": ["Indice général", "Indice procédural", "Indice plus orientant"]
```

Structural rules:

- optional;
- authored order is canonical;
- 0..3 entries;
- each entry is a non-whitespace string;
- maximum 1200 characters per hint;
- no hint ID, per-hint revision, metadata object or hint-specific media.

The 1200-character bound matches the existing V4 prompt bound and prevents unbounded learner-facing content. Semantic answer-leak review is deliberately deferred to R2 Handoff 2 / semantic review.

## Activity-level references

Every V5 activity family may optionally contain:

```json
"references": [
  {
    "url": "https://example.org/resource",
    "label": "Nom court",
    "hook": "Pourquoi cette ressource aide cette activité."
  }
]
```

Structural rules:

- optional;
- maximum 3 references per activity;
- each object is closed and requires exactly `url`, `label`, `hook`;
- URL maximum 2048 characters;
- label maximum 180 characters, matching the existing V4 title bound;
- hook maximum 800 characters, matching the existing V4 key-point bound;
- label and hook must contain non-whitespace learner-facing text.

The maximum of 3 references is an implementation-level first-slice bound for optional enrichment, not a new architectural principle.

Static URL safety is deterministic and offline:

- HTTPS only;
- host required;
- credentials/userinfo forbidden;
- whitespace/control characters and backslashes forbidden;
- malformed ports rejected;
- `http:`, `javascript:`, `file:`, `blob:`, protocol-relative and malformed URLs rejected.

No link fetching, redirect resolution, health check, HTTP status, content type, checked-at timestamp or provenance/source-role field belongs to this handoff.

## Media/assets

V5 reuses the V4 package `assets[]` and activity `media[]` definitions without semantic change.

- no remote image URL;
- embedded local media only;
- existing SVG fail-closed rules remain active;
- references are never interpreted as media.

## Closed-schema behavior and V4 separation

V4 activity families already use Draft 2020-12 `unevaluatedProperties: false`; therefore V4 rejects `hints` and `references` without any V4 mutation.

V5 adds the two properties only to the shared V5 common activity definitions, so every activity family receives the same capability while family closure remains active. Unknown activity fields remain rejected.

The V5 validator rejects a V4 contract, and the unchanged V4 validator rejects a V5 contract. No implicit conversion path is introduced.

## Canonical identity and digests

The existing canonical digest algorithm hashes the full canonical activity object except its own revision digest field. Therefore V5 `hints[]` and `references[]` are digest-bearing authored content without changing the digest algorithm.

Consequences proven by tests:

- changing any hint changes the activity -> course -> package digest chain;
- reordering hints changes identity because reveal order is authored semantics;
- changing reference URL, label or hook changes the digest chain;
- unchanged revalidation is deterministic;
- V4 digest behavior remains unchanged.

## Explicitly deferred

- hint semantic answer-leak enforcement;
- source qualification/provenance and source-set governance;
- Factory/Authoring Skill changes;
- runtime/Atlas projection or persistence;
- UI/V8 surfaces;
- 10C showcase port;
- semantic review;
- WP-054 fan-in.
