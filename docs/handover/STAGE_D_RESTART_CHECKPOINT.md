# Learn-it architecture restart checkpoint

## Canonical status

Repository state always takes precedence over this checkpoint. Verify current `main`, `governance/governor-state.json`, accepted work packages, open pull requests and exact evidence before acting. Historical handovers and architecture references are not canonical when they conflict with the repository.

Checkpoint design baseline: `135c7ee2729451e7e796749a38bf250f142c0ed4`.

## Legacy product baseline

The accepted successor design does not modify the promoted legacy product:

- Frozen standalone generation: **RC718**.
- Product source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`.
- Promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`.
- Human gate: **RC719 — PASS_WITH_RESERVATIONS**.
- Human evidence: `docs/evidence/rc718/human-validation-attestation.json`.
- RC718 remains independently usable and must not be read, migrated, reset or mutated by successor work.

## Accepted architecture history

### First reversible storage seam

`ARC-WP-014` is accepted.

- Exact tested result: `a4bf1fb1726c5c82e1af2ae085327e358fe4e3f4`.
- Implementation merge: `1346e5772bd18432d96b2f88eb0d276fc7a04e94`.
- Validation: 35/35 mandatory checks, 24/24 browser suites and 58/58 evidence bindings.
- Durable evidence: `docs/evidence/architecture/first-storage-seam/`.

### Controlled Stage D operating model

`ARC-WP-019` is accepted.

- Exact tested result: `5e379eea7ae3b495be2203355425e6549b8fcec5`.
- Implementation merge: `ae6b82d90b72f0287462c7d34708d0330d5ce35b`.
- Validation: 36/36 mandatory checks, 20/20 role-scope checks, 24/24 browser suites and 35/35 evidence bindings.
- Durable evidence: `docs/evidence/architecture/stage-d-pilot/`.

The disjoint developer, contradictory-QA, integrator and governor model remains mandatory.

### Stable identity taxonomy

`ARC-WP-020` remains accepted with conditions.

`learnit-identity-v1` separates canonical lineage/revision identity, local installation identity and legacy compatibility keys. The taxonomy and prohibition against title-derived canonical identity remain valid. Its legacy resolver and migration sequence is superseded.

### Clean-break decision

`ARC-WP-021` remains accepted with conditions.

Trajectory C is canonical. The successor does not provide:

- an RC718 compatibility resolver;
- identity overlay over RC718 data;
- dual read or dual write between legacy and successor keys;
- migration of RC718 library or learner state;
- transparent RC718 package upgrade.

Historical access is provided by RC718 itself.

## Accepted clean-generation foundation

`ARC-WP-022` is accepted with conditions as the minimum successor design.

### Contract

- Contract discriminator: `learnit.kit.v2`.
- Normative schema: `contracts/learnit-kit-v2.schema.json`.
- Canonical lineage and revision IDs: persisted lowercase UUID version 4 values.
- Revision digests: SHA-256 over the bounded canonical JSON profile.
- Foundation activity families: QCM and fill only.
- QCM answers use explicit choice IDs.
- Fill activities use explicit slot/token IDs and token `maxUses`.
- Legacy `learnit.import.v1.1` packages fail closed.

### Storage

- Successor localStorage prefix: `learnit.next.v1.`.
- Successor IndexedDB database: `learnit_next_v1`.
- RC718 localStorage keys and `learnit_durable_library_v1` are protected and untouched.
- The first integrated browser gate must prove byte-for-byte and record-for-record RC718 storage immutability after successor boot, import, session and reset.

### Product slice

The first successor slice proves:

```text
empty library
→ strict v2 import
→ library
→ one course session
→ QCM and fill
→ progress persistence
→ refresh/restart recovery
```

It does not claim RC718 feature parity or pedagogical completeness.

### Source budget

The successor root is `apps/learnit-next/`.

`docs/architecture/clean-generation/FILE_PLAN_V1.json` freezes exactly **32 working files** across contract, runtime, authoring, fixtures/tests and integration. No path may be added, renamed or split without a new governor decision.

The legacy RC718 Player remains at 150 files but is no longer the growth base for the successor.

## Multi-AI status

Three implementation streams are designed to run in parallel:

1. runtime and UI;
2. authoring and the two golden kits;
3. contradictory QA and fixtures.

They do **not** start merely because ARC-WP-022 exists. Parallel work becomes authorized only when `ARC-WP-023`:

- uses the exact ARC-WP-022 merge commit as the common base;
- creates separate subordinate work packages;
- reproduces the exact disjoint paths from `FILE_PLAN_V1.json`;
- confirms independent branches or worktrees;
- leaves build, manifest, workflow and release files exclusively to the later integrator.

The execution protocol is `docs/architecture/clean-generation/MULTI_AI_EXECUTION_V1.md`.

## Current constraints and risks

- The 32-file budget is intentionally narrow and may be changed only by a new decision.
- Python and JavaScript canonical JSON/digest implementations must agree on shared fixtures.
- Same-origin RC718/successor storage isolation depends on strict namespace ownership and negative tests.
- The `main-protection` ruleset is configured but not technically enforced on this private personal-account repository.
- The successor requires explicit rupture communication before human distribution.
- RC719 reservations remain unitemized and must not be silently copied into successor scope.

## Still held

- Successor implementation before `ARC-WP-023`.
- Any successor path outside the 32-file plan.
- Any RC718 compatibility, data migration or package interpretation.
- Media and activity families beyond QCM and fill in the foundation slice.
- Advanced bilan, mastery, retention, adaptive sequencing and content patches.
- Backend, accounts, cloud synchronization, remote catalog, commerce, tenancy and marketplace.

## Next mandatory gate

`ARC-WP-023` must create the exact subordinate implementation work packages from the ARC-WP-022 merge commit.

It must define:

- one runtime work package owning only the 14 runtime/UI paths;
- one authoring work package owning only the five authoring paths;
- one contradictory-QA/fixture work package owning only the seven fixture/test paths;
- one later integration work package owning only the five build/manifest/workflow/release paths;
- the same exact common base commit;
- exact tests, evidence and rollback for every role;
- controlled integration order and stop conditions.

After this gate is merged, the first three roles may work in parallel. The integrator remains sequential.

## Restart instruction

> Reprends le dépôt privé `stefm78/learnit-platform` depuis `docs/handover/STAGE_D_RESTART_CHECKPOINT.md`. Vérifie l’état réel de `main`, du gouverneur, des work packages, des PR et des checks. RC718 est la génération legacy figée. La trajectoire canonique est C. ARC-WP-022 a figé `learnit.kit.v2`, le stockage `learnit.next.v1.` / `learnit_next_v1`, le slice QCM+fill et le plan exact de 32 fichiers. N’implémente rien avant ARC-WP-023. ARC-WP-023 doit créer quatre work packages à base commune exacte : runtime, authoring, QA/fixtures et intégration. Les trois premiers peuvent ensuite partir en parallèle sur des scopes disjoints; l’intégrateur reste séquentiel. Aucun accès RC718, aucune compatibilité, aucun fichier non planifié et aucun domaine held.

## Resume verification

Before any action, confirm:

1. current `main` and open pull requests;
2. governor state and next mandatory gate;
3. frozen RC718 source and artifact hash;
4. accepted Stage C and Stage D evidence roots;
5. accepted identity taxonomy and clean-break decision;
6. accepted v2 schema, foundation and exact 32-file plan;
7. that no subordinate implementation has started before ARC-WP-023;
8. current risks, exceptions and protected RC718 storage list;
9. that no held domain or unplanned file has been entered.
