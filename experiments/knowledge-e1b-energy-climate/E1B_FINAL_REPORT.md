# E1B final experimental report

## Result

`PASS_E1B_LONG_SOURCE_SCALE_REUSE_READY_FOR_INTEGRATION_SOLVE`

## Frozen source

- PDF pages: **163**.
- SHA-256: `cc411ddb76a904a684a44ce85be15b67a9ef9f2bc75288697a4981a62a4b0c73`.
- Source bytes remain read-only and are **not committed**.
- `200_300_PAGE_SCALE_NOT_DIRECTLY_TESTED`.

## A/B result

Eight frozen `learnit.kit.v2` candidates cover K1–K4 with matched Direct and Knowledge-assisted learner semantics. Deterministic canonical/Atlas/M3.1 qualification is required on the exact draft-PR head. Comparative semantic reviews remain non-independent and therefore correctly produce `HOLD_FACTORY_SEMANTIC_REVIEW`; this is an explicit reservation, not a semantic PASS claim.

## Architecture answer

The four-kit observation does not amortize Knowledge yet (Direct proxy 47 vs Knowledge proxy 65). Using the observed K1/K2 overlap profile, the projected medium-reuse break-even is around **13 overlapping derivatives**; high reuse can break even earlier, while low reuse remains cheaper on Direct through N=20. This justifies keeping Knowledge **optional**, targeted to repeated/evolving overlapping derivatives.

## Controls

K4 remains narrow to section 5.3.4 with 5.3.2/5.3.3 as support only. Change-impact fixtures localize Carnot changes to K1/K2 and Rth changes to K3 without global invalidation. The one-off Direct fast path remains intact.

## Reservations

- `UPSTREAM_R1_RESERVATION=INDEPENDENCE_DEGRADED`.
- `NON_INDEPENDENT_COMPARATIVE_REVIEW`.
- No merge, promotion, runtime/schema integration, or mandatory Knowledge route is authorized by this experiment.

## Handoff

After exact-head PR qualification, re-enter `/solve` from current `main` to decide the minimum integration, if any.
