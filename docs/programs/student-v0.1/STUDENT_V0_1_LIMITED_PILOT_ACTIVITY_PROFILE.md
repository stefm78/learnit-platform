# Student V0.1 — Limited Pilot Activity Profile

## Status

This document defines the activity-family admission profile for the first limited Student V0.1 pilot. It is a pilot policy only; it does not change the published `learnit.kit.v4` schema, runtime support, or scoring semantics.

## Admitted families

The limited pilot admits:
- `lesson`
- `flashcard`
- `matching`
- `order`
- `classify`
- `qcm`
- `fill`

## Excluded from the first limited pilot

`constructed` is excluded from the first limited pilot.

`constructed` remains a supported `learnit.kit.v4` activity family outside this limited-pilot profile. The exclusion is not a schema deletion.

The limited pilot excludes free-text constructed responses because exact text matching is not a general mathematical semantic-equivalence mechanism. The existing `canonical-text-match-v1` behavior remains unchanged.

## Showcase consequence

For the Nombres complexes showcase, the single `constructed` activity is removed without replacement. The remaining 10 activities preserve their original order and the two existing objectives. The course duration therefore changes from 42 to 39 minutes.

The conjugate objective remains covered by:
- lesson;
- flashcard;
- matching practice;
- transfer QCM;
- validation QCM.

No new mathematical content is introduced by this policy.
