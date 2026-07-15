# GOV-REVIEW-0025 — ARC-WP-022 clean-generation foundation

## Decision

**GO_WITH_CONDITIONS** for the architecture, contract and execution design in `ARC-WP-022`.

This decision freezes the minimum foundation and allows preparation of subordinate implementation work packages. It does not itself accept successor product code or a release candidate.

## Baseline reviewed

- Repository: `stefm78/learnit-platform`
- Exact baseline: `135c7ee2729451e7e796749a38bf250f142c0ed4`
- Legacy product: RC718
- Legacy artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`
- Clean-break decision: `ARC-WP-021`
- Proposed successor contract: `learnit.kit.v2`
- Proposed successor file budget: 32

## Scope reviewed

The pull request may change only:

- the ARC-WP-022 work package;
- one frozen v2 JSON Schema;
- three clean-generation design artifacts;
- this governor review;
- governor state;
- the canonical restart checkpoint.

No Player, authoring, fixture, test, workflow, build, artifact or learner-data implementation is allowed in this gate.

## Evidence

- Canonical repository entry points now identify RC718 as legacy and the clean-break successor as the active direction.
- RC718 current storage dependencies are inventoried, including localStorage state and library keys and the `learnit_durable_library_v1` IndexedDB database.
- The proposed successor namespaces, `learnit.next.v1.` and `learnit_next_v1`, are distinct from inventoried RC718 namespaces.
- The schema restricts the first slice to QCM and fill and uses explicit identity references rather than title, position or array-index identity.
- The file plan assigns exactly 32 future files with no shared writable path among three parallel implementers and one later integrator.
- The execution protocol freezes the contract before parallel start and defines stop conditions for overlap, drift, compatibility code and held-domain entry.

## Claims accepted

- A separate `apps/learnit-next` root is cleaner and safer than mutating or copying the 150-file RC718 Player as the initial successor baseline.
- QCM and fill are sufficient to prove a complete import-to-persistence learning loop without claiming feature or pedagogical completeness.
- Explicit QCM choice IDs prevent answer semantics from depending on array positions.
- Explicit fill slot/token IDs and `maxUses` eliminate missing-position and unintended single-use ambiguity.
- Three implementation agents can work safely in parallel after the contract and exact common base are frozen.
- A sequential independent integrator is required because build, manifest, workflow and release evidence are shared integration surfaces.

## Assumptions

- UUID version 4 generation is available in the authoring and browser environments used by the project.
- The existing Python and browser-test toolchain can support the successor without adding a package manager to the first slice.
- Representative six-activity versions of Nombres complexes and Signaux électriques are adequate foundation fixtures.
- The first successor human test can accept intentionally narrower functionality than RC718.

These assumptions must be tested by subordinate work packages and the integrated candidate.

## Absence of evidence

There is not yet executable proof that:

- the v2 schema and semantic rules accept the intended fixtures;
- Python and browser canonical-digest implementations agree byte for byte;
- IndexedDB transactions provide the planned atomic import behavior;
- successor reset and use leave RC718 storage byte-for-byte unchanged;
- the 32-file plan is sufficient to implement the vertical slice;
- the two foundation kits provide an acceptable human learning experience;
- the integrated clean build is deterministic.

These are implementation gates, not reasons to reject the bounded design.

## Contradictory challenge

The design was challenged against the following failure modes:

1. **A disguised RC718 fork.** Rejected by a separate root, 32-file ceiling and explicit prohibition on copying all RC718 implementation.
2. **Compatibility reintroduced as convenience.** Rejected by fail-closed legacy handling and explicit protected RC718 namespaces.
3. **Parallel-agent collisions.** Rejected by exact disjoint paths and an integrator-only shared surface.
4. **Identity overengineering.** Reduced to package, course, objective, activity, choice, slot and token identities required by the first slice.
5. **Index-based answer drift.** Removed through choice, slot and token identifiers.
6. **A large new platform hidden in the foundation.** Backend, accounts, sync, catalog, commerce, tenancy and marketplace remain held.
7. **Tests certifying a different artifact.** Deterministic build and exact tested-artifact identity remain mandatory.

## Conditions

1. The v2 schema is frozen at the ARC-WP-022 merge commit before parallel work starts.
2. `ARC-WP-023` creates subordinate work packages from that exact merge commit.
3. No subordinate package may add or rename a file outside `FILE_PLAN_V1.json`.
4. Runtime, authoring and QA/fixture agents use disjoint branches and write scopes.
5. The integrator does not repair role-owned code silently.
6. Successor code may not access, enumerate for mutation, clear or upgrade protected RC718 storage.
7. The first integrated candidate must pass the full 15-point acceptance matrix in `FOUNDATION_V1.md`.
8. A separate governor acceptance and human gate are required before distribution.

## Residual risks

- **Moderate — narrow contract:** The first slice does not support most RC718 activity families or media.
- **Moderate — dual-language digest implementation:** Python and JavaScript canonicalization can diverge without shared fixtures.
- **Moderate — browser storage isolation:** Same-origin applications can technically see common browser storage; prohibition and negative tests must enforce non-access.
- **Low — user expectation:** A new-generation artifact could be mistaken for an RC718 upgrade without explicit naming and release communication.
- **High governance risk:** GitHub main-protection remains configured but not technically enforced on the current private personal-account repository.

## Outcome

`ARC-WP-022` is accepted with conditions as the clean-generation foundation design.

The next mandatory gate is `ARC-WP-023`: create exact subordinate work packages from the ARC-WP-022 merge commit and verify that the three parallel implementation scopes and later integrator scope remain disjoint. Successor implementation remains on HOLD until that gate is merged.
