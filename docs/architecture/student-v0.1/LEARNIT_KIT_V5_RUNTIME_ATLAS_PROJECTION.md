# Learn-it Kit V5 — Runtime / Atlas Projection R1

## Scope

This handoff admits `learnit.kit.v5` explicitly in the existing runtime without rewriting V4 and without changing activity-response or scoring semantics.

## Learner-safe projection

The initial V5 presentation is a positive projection. It never copies `hints`; references are copied only as `{url,label,hook}`; embedded activity media is resolved locally from imported package assets; media with `placement=feedback` is excluded from the initial projection. A separate `projectFeedbackMedia(..., {transitionAuthorized:true})` seam exposes only feedback media after an authorized feedback transition.

References are inert learner metadata. Projection performs no fetch and activity display, response capture and scoring do not require reference network availability.

## Atlas hint protocol

V5 qcm/fill reuses the existing Atlas `requestHelp('hint')` persistence path. The learner-visible rank is reconstructed from the existing durable `atlasMeta.assistanceUses` journal and the matching ResumeState `assistanceUseIds`; only records whose `assistanceKind` is `hint` count.

The protocol is:

1. verify the active plan and ResumeState are pinned to the exact installed package revision;
2. reconstruct the durable hint prefix;
3. stop without mutation when all canonical hints are consumed;
4. acquire an in-flight guard for the exact session/item;
5. request Atlas hint assistance;
6. require a committed confirmation;
7. reread durable state and require exactly one additional durable hint record;
8. reveal exactly that canonical next hint.

A persistence failure reveals nothing. A commit followed by a UI crash is recovered on resume because the prefix is reconstructed from durable Atlas evidence. Guided-step, solution and every non-hint assistance record remain assistance evidence but do not advance hint rank.

## Persistence boundary

No hint counter, table, IndexedDB store, Atlas schema version, sidecar or fallback revision is added. Existing Atlas storage and persistence schemas remain the authority.

## Frozen behavior

V4 schema/validator/tests, the V5 qualified schema/validator/tests, activity evaluation semantics, Atlas persistence ports/adapters and selected V7 presenters remain byte-identical to the qualified Handoff-2 parent.
