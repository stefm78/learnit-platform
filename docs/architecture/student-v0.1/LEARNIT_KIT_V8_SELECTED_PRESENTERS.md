# Learn-it Kit V8 — Selected Presenters R1

Status: **R2 Handoff 4 implementation boundary**

## Authority
- parent: `student-v01/r2-v5-runtime-atlas-projection-r1@1bd57ee49f39ebc993af6198d24ebd54cd0ddbab`
- V7 selection oracle: PR #437 / `577aa6cde9dfc58663a4935545e48bf8953c902b`
- selection blob: `947d0b20fbae356c47acd560fab584f9d4aa5199`
- selected variants: Flashcard B, Matching B, Order B, Classify B, QCM A, Fill B, Lesson A
- Handoff 3 result: `f1254562247a2ee54d5a5329b953fafc22eb8fd3`

## Boundary
This handoff ports only selected presenter behavior and consumes only V5 capabilities already qualified by Handoff 3. It does not create a second scoring, progress, persistence, assistance, media-fetch, or reference-fetch authority.

The frozen ActivityResponse grammars remain:
- lesson → `{acknowledged:true}`
- flashcard → `{revealed:true}`
- qcm → `{choiceId}`
- fill → canonical slot mapping
- matching → `{associations:[{leftItemId,rightItemId}]}`
- order → `{orderedItemIds:[...]}`
- classify → `{assignments:[{itemId,bucketId}]}`

## Selected V7 interaction contract
Matching B, Order B, Classify B and Fill B use one convergent interaction rule: selecting an object changes only state and reveals explicit destinations; activating a destination performs the same mutation as dragging to it. Pointer Events are progressive enhancement, never the only route.

Order B preserves the V7 geometry invariant: insertion targets are an absolute overlay for non-drag placement; on drag, the original row leaves Grid flow, one exact-size placeholder is the only in-flow representative, the ghost keeps fixed X and follows only Y, list height remains invariant, and cancel restores the original DOM/inline-style state.

Randomization is per presenter render/attempt only. It never changes canonical IDs and is not persisted or used for scoring, progression, or Atlas evidence. A deterministic test-only random source is exported solely for qualification.

## V5 hint integration
Presenters never receive unrevealed hints. Atlas session wiring exposes an Indice control only when the current V5 activity has authored hints and uses the exact Handoff-3 `requestNextAtlasV5Hint` + `reconstructAtlasHintPrefix` protocol. UI text is appended only after the Handoff-3 persist/confirm result or resume reconstruction. The presenter never persists assistance.

## V5 media lifecycle
Initial ActivityPresentation rendering accepts only projected `prompt` and `content` media. Handoff 3 already excludes feedback media from the initial projection. Feedback media are projected only after the answer transition with `transitionAuthorized:true` and rendered through the existing defensive embedded-media renderer. No remote fallback exists and media failure does not alter scoring.

## References
References are rendered below the primary task in a native `details` disclosure, closed by default, with “Pour aller plus loin” / “Références”. Rendering or opening the disclosure performs no fetch. Navigation occurs only when a learner activates an external link. Links use `target="_blank"`, `rel="noopener noreferrer"`, and visual + accessible external-link text.

## Compatibility
Core semantics, scoring, V4/V5 contracts, authoring, Atlas storage and evidence schemas remain frozen. PR #437 and PR #436 are oracles only; neither is cherry-picked. Stream 10A compatibility is validated later by an ephemeral detached composition and is never durable fan-in.
