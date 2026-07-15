# Learn-it architecture restart checkpoint

## Canonical status

Repository state always takes precedence over this checkpoint. Verify current `main`, `governance/governor-state.json`, accepted work packages, open pull requests and exact evidence before acting. Historical handovers are not canonical when they conflict with the repository.

Checkpoint decision baseline: `0575385c5891e56506de6aaa0244297d766ea458`.

## Legacy product baseline

The current architecture decisions do not modify the promoted legacy product:

- Frozen standalone generation: **RC718**.
- Product source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`.
- Promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`.
- Human gate: **RC719 — PASS_WITH_RESERVATIONS**.
- Human evidence: `docs/evidence/rc718/human-validation-attestation.json`.
- RC718 remains available as the legacy generation and must not be mutated by new-generation work.

## Accepted architecture history

### First reversible storage seam

`ARC-WP-014` is accepted.

- Exact tested result: `a4bf1fb1726c5c82e1af2ae085327e358fe4e3f4`.
- Implementation merge: `1346e5772bd18432d96b2f88eb0d276fc7a04e94`.
- Validation: 35/35 mandatory checks, 24/24 browser suites and 58/58 evidence bindings.
- Durable evidence: `docs/evidence/architecture/first-storage-seam/`.

The unchanged synchronous localStorage adapter is owned by runtime part 04. Direct IndexedDB opening remains owned by runtime part 05.

### Controlled Stage D operating model

`ARC-WP-019` is accepted.

- Exact tested result: `5e379eea7ae3b495be2203355425e6549b8fcec5`.
- Implementation merge: `ae6b82d90b72f0287462c7d34708d0330d5ce35b`.
- Validation: 36/36 mandatory checks, 20/20 role-scope checks, 24/24 browser suites and 35/35 evidence bindings.
- Durable evidence: `docs/evidence/architecture/stage-d-pilot/`.

The disjoint developer, contradictory-QA, integrator and governor model remains mandatory for bounded implementation work.

### Stable identity taxonomy

`ARC-WP-020` is accepted with conditions.

`learnit-identity-v1` separates:

1. canonical lineage and immutable revision identity;
2. local installation identity;
3. legacy compatibility keys.

The taxonomy and its prohibition against title-derived canonical identity remain valid.

## Current trajectory — clean break

`ARC-WP-021` is accepted with conditions.

The accountable owner selected **trajectory C — clean-break generation**. The compatibility and migration sequence previously proposed after `ARC-WP-020` is superseded.

The following work is cancelled unless a future accountable-owner decision explicitly reopens it:

- RC718 compatibility resolver;
- identity overlay over RC718 data;
- dual read or dual write between legacy and canonical keys;
- transactional migration of RC718 learner state;
- mixed RC718/new-generation library operation;
- transparent upgrade of RC718 packages or browser state.

## New-generation rules

The next generation must start with:

- a new major content contract;
- canonical identity from creation;
- new localStorage keys and a distinct IndexedDB identity;
- an empty active library and learner state, except explicitly bundled new-generation content;
- regenerated or deliberately converted kits;
- explicit rejection of RC718 packages;
- no read, write, reset or deletion of RC718 browser storage;
- a distinct product and release identity;
- atomic source, contract, build, tests, artifact and hash evidence.

The identity taxonomy from `ARC-WP-020` is retained. Its resolver, overlay and migration path is not.

## Accepted concessions

The new generation does not automatically preserve:

- imported RC718 plans or courses;
- plan and course name customizations;
- active sessions or answers;
- progress and mastery state;
- bilans and review lists;
- retention schedules and history;
- import history, field evidence or content patches.

Historical access is provided by retaining RC718 itself, not by migrating its data.

## Current constraints

- The legacy Player working-file count is exactly **150**. The next foundation gate must explicitly retain, reduce or replace that budget.
- The `main-protection` ruleset is configured but not technically enforced on this private personal-account repository. Pull requests, CI, scope validation and governor review remain mandatory operational controls.
- New-generation implementation is not yet authorized.
- RC718 storage isolation must be proven negatively before any new-generation candidate is accepted.

## Still held

- Any new-generation Player implementation before the next foundation gate.
- Any RC718 compatibility or migration layer.
- Backend, accounts and learner profiles.
- Cloud synchronization and remote catalog.
- Commerce, entitlements, institutional tenancy and publisher marketplace.

## Next mandatory gate

`ARC-WP-022` must design and authorize the **minimum viable clean-generation foundation**.

It must define:

- the exact new major content contract;
- canonical identity fields and digest rules;
- isolated localStorage and IndexedDB namespaces;
- empty initial-state behavior;
- explicit legacy-package rejection;
- regeneration of the Nombres complexes and Signaux électriques golden kits;
- the exact Player file plan and source-budget decision;
- disjoint developer, contradictory-QA, integrator and governor scopes;
- automated storage-isolation, contract, product-flow, deterministic-build and artifact-identity gates;
- the first human release gate and rupture notice;
- a one-revert implementation boundary.

It must not introduce RC718 compatibility, learner-state migration or any held platform domain.

## Restart instruction

> Reprends le dépôt privé `stefm78/learnit-platform` depuis `docs/handover/STAGE_D_RESTART_CHECKPOINT.md`. Vérifie l’état réel de `main`, du gouverneur, des work packages, des PR et des checks. RC718 est la génération legacy figée. La trajectoire canonique est C : nouvelle génération sans compatibilité ni migration RC718. Conserve la taxonomie `learnit-identity-v1`, mais n’implémente aucun resolver legacy, overlay, dual-read ou migration. La prochaine gate est `ARC-WP-022`, design et autorisation du socle minimal clean-break : nouveau contrat majeur, stockage isolé, état vide, kits régénérés, plan de fichiers exact, QA contradictoire et preuves de release. Le dépôt prévaut sur tout ancien handover.

## Resume verification

Before any action, confirm:

1. current `main` and open pull requests;
2. governor state and next mandatory gate;
3. frozen RC718 source and artifact hash;
4. accepted Stage C and Stage D evidence roots;
5. accepted identity taxonomy and accepted clean-break decision;
6. that no compatibility or migration implementation has started;
7. Player file count and active risks;
8. that no held domain has been entered.
