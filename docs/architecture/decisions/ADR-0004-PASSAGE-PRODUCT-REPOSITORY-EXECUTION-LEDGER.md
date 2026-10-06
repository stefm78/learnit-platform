# ADR-0004 — PASSAGE product repository / execution ledger boundary

- Status: Accepted
- Date: 2026-10-06
- Authority: issue #480 / constituted LearnIT job `PASSAGE_RECONCILIATION_R1`
- Reviewed baseline: `21d25c36aec6c04fdfe8126c95e71cbf80771a1b`

## Context

LearnIT uses two durable surfaces with different responsibilities. GitHub contains the executable platform and its durable architecture; OneDrive contains course execution, orchestration and evidence. These surfaces must bind to each other without becoming competing product or execution authorities.

The accountable owner selected **PASSAGE** as the codename for the next major evolution intended to close the real vertical slice:

`source → Factory → exact kit → qualification → import → runtime → learner`

## Decision

1. **GitHub is the authority for the executable platform**: code, contracts, validators, runtime, Factory implementation, durable architecture, tests and product identities.
2. **OneDrive is the authority for execution and evidence**: course sources, orchestration, jobs, state logs, reviews, results and attestations.
3. OneDrive evidence about product behavior must bind the exact Git identities required by that evidence. OneDrive does not silently redefine the product.
4. **PASSAGE** is the codename for the evolution that closes the real vertical slice `source → Factory → exact kit → qualification → import → runtime → learner`.
5. PASSAGE uses the operating principle `need/blocker → smallest correct change → smallest sufficient proof → PASS / STOP / USE`.
6. PASSAGE does not make R35 or any other working design retroactively authoritative over existing lanes. Each lane remains governed by its own exact durable authorities.
7. A PASSAGE decision is reopened only when a material finding or proof invalidates one of its premises.

## Consequences

- `governance/governor-state.json` remains GitHub's machine-readable current repository frame.
- OneDrive state logs remain execution authorities for their applicable program, course, kit and pilot state.
- README files and human entry points explain and point to authorities; they do not duplicate dynamic state.
- This ADR records the boundary and codename only. It does **not** start PASSAGE implementation, promote any draft branch, or change product/runtime/Factory semantics.
