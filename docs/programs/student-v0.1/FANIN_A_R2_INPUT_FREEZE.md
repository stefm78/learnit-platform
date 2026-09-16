# Student V0.1 — FAN-IN A R2 Input Freeze

Status: **FROZEN EXECUTION AUTHORITY FOR JOB 04 R2**

## Exact anchors

- `FANIN_A_BASE`: `21d25c36aec6c04fdfe8126c95e71cbf80771a1b`
- `R2_START_CANDIDATE`: `f4636e06279481b62ffd676ba70313c71283baeb`
- `WAVE1_COMMON_BASE`: `27846dff52fde9b83434bca29bd8732ea42834bf`

Accepted role heads:

- JOB01 predecessor / PR #387: `d937592fb4d1e6dba6fcd02e290290f1a98cff71`
- JOB01 R2 / PR #396 / issue #395: `ef3080e32e873170c6fd2fbdc72e93c31389cebb`
- JOB02 / PR #388: `6c91346d07c934cfb2917799084647b13e4fb931`
- JOB03 / PR #389: `a90ba85857dded331e5e3952c2f181cbe2e6d689`

The prior executable FAN-IN candidate `f4636e...` already contains the exact accepted JOB01 predecessor, JOB02 and JOB03 deltas plus integration wiring. It failed only at the documented JOB03 -> JOB01 SVG admission boundary.

## Exact JOB01 R2 delta

The only role delta newly admitted into FAN-IN A R2 is:

`d937592fb4d1e6dba6fcd02e290290f1a98cff71..ef3080e32e873170c6fd2fbdc72e93c31389cebb`

Expected changed paths relative to the JOB01 predecessor:

- `apps/learnit-next/src/core/contract.js`
- `apps/learnit-next/tests/student_v01_learning_runtime.py`
- `work-packages/ATLAS-WP-031.json`

The integrator must freshly re-prove this exact path set and merge-base before applying it.

## Frozen unaffected roles

JOB02 and JOB03 remain byte-for-byte frozen at their accepted SHAs. JOB04 R2 must not modify their role-owned files.

## Prior failure to close

The prior integrated candidate accepted JOB03's representative inline SVG at authoring but JOB01 runtime rejected the standard root namespace:

`xmlns="http://www.w3.org/2000/svg"`

as if its `http:` substring were an active/external URI. JOB01 R2 independently qualified a narrow runtime fix that admits standard namespace metadata while preserving fail-closed malicious/external SVG rejection.

## No-silent-repair rule

JOB04 R2 may:

1. apply the exact frozen JOB01 R2 delta;
2. rebind only minimum integration-owned source-manifest / CI routing required by the new candidate branch/head;
3. add exact FAN-IN A R2 qualification evidence.

It may not repair or redesign JOB01, JOB02, JOB03, v4 architecture, schema, UI or authoring semantics. Any new semantic defect returns HOLD with the owning boundary identified.
