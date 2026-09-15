# JOB — E1B Integration Qualification

## Purpose
Execute `NEXT_PROMPT_E1B_INTEGRATION_QUALIFICATION.md` as the bounded closure job for E1B. This job publishes and qualifies the already-authored experimental corpus; it does not redesign the experiment or integrate it into product authority.

## Inputs
- repository: `stefm78/learnit-platform`
- product main observed baseline: `1e71271436fd4b7dd7d895cfec827833187630fe`
- upstream PR: `#378`
- upstream branch: `experiment/e1a-r1-coverage-preservation-mi2-complexes`
- upstream observed head: `a760ce1f8bb1098f122a66beb73ce5d8c6e257b5`
- E1B branch: `experiment/e1b-energy-climate-scale-reuse`
- work package: `EXP-WP-002`
- payload root: `experiments/knowledge-e1b-energy-climate/`
- external source SHA-256: `cc411ddb76a904a684a44ce85be15b67a9ef9f2bc75288697a4981a62a4b0c73`
- source bytes: `3042017`
- source pages: `163`

## Execution graph
`REBIND -> CAS -> LOCAL_FREEZE_AUDIT -> PUBLISH -> DRAFT_PR -> EXACT_HEAD_CI -> ADVERSARIAL_AUDIT -> HANDOFF`

## Gates
### G0 — Authority/CAS
PASS only if current control-plane selection is valid, current repository identities are reconstructed, PR #378 is DRAFT/unmerged, and E1B has no conflicting independent mutation.

### G1 — Frozen payload
PASS only if all local payload JSON parses, the 8 candidate hashes equal the freeze manifest, no PDF is present, and all paths are authorized by `EXP-WP-002`.

### G2 — Publication
PASS only if the branch update is a safe fast-forward from the CAS head and the resulting delta stays inside the work-package surface.

### G3 — PR
PASS only if exactly one DRAFT stacked PR exists from E1B branch to the upstream experimental branch and its body names exactly `EXP-WP-002` as governing package.

### G4 — Exact-head CI
PASS only if the final PR head passes the E1B workflow using current canonical validators/Atlas/M3.1 and isolated-delta checks.

### G5 — Final audit
PASS only if final CI head equals current PR head, no merge occurred, no authority surface changed, the source PDF remains external, and all epistemic reservations remain explicit.

## Repair policy
Mechanical failures may be repaired inside authorized E1B paths. Semantic candidate repair requires the exact source bytes and invalidates/rebuilds affected derived evidence. Product-authority changes require return to `/solve`. No gate may be weakened to obtain PASS.

## Reservations that must survive
- `SOURCE_PAGE_COUNT = 163`
- `200_300_PAGE_SCALE_NOT_DIRECTLY_TESTED`
- `UPSTREAM_R1_RESERVATION = INDEPENDENCE_DEGRADED`
- `SEMANTIC_REVIEW_INDEPENDENCE = DEGRADED`
- `KNOWLEDGE_PATH_IS_OPTIONAL`

## Success token
`PASS_E1B_INTEGRATION_QUALIFICATION_READY_FOR_SOLVE`

## Safe next action after PASS
`REENTER_SOLVE_FROM_MAIN_FOR_MINIMUM_INTEGRATION`

## Forbidden actions
No automatic merge, no product promotion, no direct main mutation, no PR #378 mutation, no source-PDF commit, no schema/validator/runtime/Factory Gate change, and no self-issued independent semantic certification.
