# Learn-it architecture restart checkpoint

## Canonical status

This file is the concise restart point after acceptance of the controlled Stage D pilot and the design-only stable-identity gate.

Repository state always takes precedence over this checkpoint. On restart, verify current `main`, `governance/governor-state.json`, accepted work packages and exact evidence before acting. Historical handovers are not canonical when they conflict with the repository.

Identity-design baseline: `e9d3f1f36d34170111b6b583bc7d9219e68e03ab`.

## Product baseline

The architecture work below did not promote or modify the product baseline.

- Promoted standalone baseline: **RC718**.
- Product source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`.
- Promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`.
- Human gate: **RC719 — PASS_WITH_RESERVATIONS**.
- Human evidence: `docs/evidence/rc718/human-validation-attestation.json`.
- Reservations remain non-blocking but must be itemized in `docs/product/RC719_RESERVATIONS.md` before corrective implementation.

## Accepted architecture gates

### Stage B — design

`ARC-WP-010` is accepted.

The accepted design defines one minimal reversible storage boundary while preserving storage technology, keys, payloads, identifiers, callers, UI and behavior.

### Stage C — first reversible seam

`ARC-WP-014` is accepted.

- Exact execution base: `f272c81f172b7d3c46a708bc5277b8401b15db1a`.
- Exact tested result: `a4bf1fb1726c5c82e1af2ae085327e358fe4e3f4`.
- Implementation merge: `1346e5772bd18432d96b2f88eb0d276fc7a04e94`.
- Governor acceptance merge: `d08cd1e1e63a135c819175fc7538d52487abeb92`.
- Remote Agent run: `29354643840`.
- Validation: 35/35 mandatory checks, 24/24 browser suites and 58/58 evidence bindings.
- Tested artifact: 829075 bytes, SHA-256 `9e9db99065b678267818eb478849d7bd02c2e34e42f2f8e0628e01a3c22ef861`.
- Durable evidence: `docs/evidence/architecture/first-storage-seam/`.
- Governor review: `docs/governance/reviews/GOV-REVIEW-0013-FIRST-SEAM-ACCEPTANCE.md`.

The unchanged synchronous localStorage adapter is owned by runtime part 04. Direct IndexedDB opening remains owned by runtime part 05. Rollback requires one revert and no learner-data migration.

### Stage D — controlled multi-agent pilot

`ARC-WP-019` is accepted.

The pilot added a deterministic role-scope ownership report through disjoint responsibilities:

- Developer: `apps/player/dev/role_scope_report.py`.
- Contradictory QA: `apps/player/tests/contract_role_scope.py`.
- Integrator: mandatory registry, evidence map and durable evidence.
- Governor: work package, state and decisions only.

Exact evidence:

- Execution base: `d65189b7ef59ccb74ba02c6c6ac96a212895a1e9`.
- Remote Agent trigger: `c0101bde910c8f3a47ce7f981a4e939a55176589`.
- Exact tested result: `5e379eea7ae3b495be2203355425e6549b8fcec5`.
- Implementation merge: `ae6b82d90b72f0287462c7d34708d0330d5ce35b`.
- Governor acceptance merge: `eb296c14825d1a624c96806ee3eba073e6225b69`.
- Remote Agent run: `29356520176`.
- Permanent Player CI run: `29356634330`.
- Validation: 36/36 mandatory checks, 20/20 pilot contract checks, 24/24 permanent browser suites and 35/35 evidence bindings.
- Result-envelope digest: `sha256:c4c6123c58caf8c070f47fe7c19970cabfa12b41bbd846caf517bd0b7361fb13`.
- Product artifact remained unchanged: SHA-256 `9e9db99065b678267818eb478849d7bd02c2e34e42f2f8e0628e01a3c22ef861`.
- Durable evidence: `docs/evidence/architecture/stage-d-pilot/`.
- Governor review: `docs/governance/reviews/GOV-REVIEW-0020-STAGE-D-PILOT-ACCEPTANCE.md`.

The Stage D operating model is validated for future bounded work packages. This does not authorize broad parallel refactoring.

### Stable identity and migration design

`ARC-WP-020` is accepted with conditions as a **design-only** gate.

The accepted scheme is `learnit-identity-v1`. It separates:

1. canonical package, course, objective, activity, asset and revision lineage;
2. local plan and course installation identities;
3. current legacy compatibility keys such as `packageId`, `importPackageId`, `localCourseId`, activity `id`, normalized objective text and `contentVersion`.

Core decisions:

- canonical IDs are opaque, immutable and independent of titles, labels, ordering and local collision suffixes;
- `learnit.import.v1.1` fields retain their current meaning and are not silently promoted to canonical identity;
- canonical identity envelopes must be complete and digest-consistent or be rejected;
- legacy-only content remains usable but is not globally deduplicated by title, slug, order, file name or digest inference;
- two local installations of one canonical course remain separate progress namespaces;
- historical learner evidence is retained across revisions but counted toward current mastery only under explicit compatibility rules;
- migration is overlay-first, transactional and reversible, with legacy reads preserved through a compatibility window.

Canonical design and evidence:

- Work package: `work-packages/ARC-WP-020.json`.
- Decision: `docs/architecture/decisions/ADR-0001-STABLE-IDENTITY-MIGRATION.md`.
- Exact current-source inventory: `docs/evidence/architecture/stable-identity/current-identity-inventory.json`.
- Governor review: `docs/governance/reviews/GOV-REVIEW-0022-ARC-WP-020-STABLE-IDENTITY-DESIGN.md`.

No identifier, contract, runtime, stored data or product behavior has been changed. Identity implementation and learner-state migration remain blocked.

## Current constraints

- The Player working-file count is exactly **150**, equal to the enforced budget. The next implementation seam must modify existing files or remove/consolidate one before adding another.
- The `main-protection` ruleset is configured but not technically enforced on this private personal-account repository. Pull requests, CI, scope validation and governor review remain mandatory operational controls.
- Current RC718 identity is proven for local rename-safe progress, not for global lineage across devices or publishers.
- RC719 reservations are not yet itemized.
- The accepted first storage seam and RC718 product identity are frozen unless a dedicated work package says otherwise.

## Still held

- Writing canonical identity overlays.
- Rewriting learner-state, progress, bilan, session, retention, import-history or patch keys.
- Publishing or requiring a new import-contract version.
- Removing or reinterpreting legacy identity fields.
- Player-wide architecture refactoring.
- localStorage-to-IndexedDB migration.
- Backend, accounts and learner profiles.
- Cloud synchronization and remote catalog.
- Commerce, entitlements, institutional tenancy and publisher marketplace.

## Next mandatory gate

`ARC-WP-021` may authorize only an **additive read-only identity resolver and shadow diagnostic**.

It must:

- start from exact current `main`;
- classify complete canonical, legacy-only and invalid-partial identity;
- preserve every current legacy key and all existing behavior;
- perform no identity-overlay write and no learner-state migration;
- change no import decision, UI, product identity or storage ownership;
- modify exact existing Player files so the working-file count remains 150;
- use explicit disjoint developer, contradictory-QA, integrator and governor scopes;
- pass permanent Player CI and separate governor acceptance;
- provide one-revert rollback.

Contract publication, canonical identity writes and migration require later independent gates.

## Restart instruction

Use this instruction in a future session:

> Reprends le dépôt privé `stefm78/learnit-platform` depuis `docs/handover/STAGE_D_RESTART_CHECKPOINT.md`. Vérifie d’abord l’état réel de `main`, `governance/governor-state.json`, les work packages acceptés, les PR ouvertes et les checks. Considère Stage B, Stage C, le pilote Stage D et le design-only `ARC-WP-020` comme acquis seulement si le dépôt et les preuves exactes le confirment. La prochaine étape autorisée est `ARC-WP-021`, limitée à un résolveur d’identité en lecture seule et un diagnostic fantôme dans des fichiers Player existants. N’écris aucun overlay d’identité, ne migre aucune donnée ou clé historique, ne publie aucun nouveau contrat et n’entre dans aucun domaine backend ou synchronisation. Préserve RC718, la première couture, le budget de 150 fichiers Player et les périmètres de rôles disjoints. Le dépôt prévaut sur tout ancien handover.

## Resume verification

Before any new action, confirm:

1. current `main` and open pull requests;
2. governor state and next mandatory gate;
3. promoted RC718 artifact hash;
4. accepted Stage C and Stage D evidence roots;
5. accepted ARC-WP-020 ADR, inventory and governor review;
6. permanent Player CI, PR scope and repository governance status;
7. Player working-file count;
8. active risks and the unenforced-ruleset exception;
9. that no held identity, storage or platform domain has been entered.
