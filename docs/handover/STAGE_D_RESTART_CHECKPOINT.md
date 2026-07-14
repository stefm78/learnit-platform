# Learn-it architecture restart checkpoint

## Canonical status

This file is the concise restart point after acceptance of the first controlled Stage D pilot.

Repository state always takes precedence over this checkpoint. On restart, verify current `main`, `governance/governor-state.json`, accepted work packages and exact evidence before acting. Historical handovers are not canonical when they conflict with the repository.

Checkpoint base: `eb296c14825d1a624c96806ee3eba073e6225b69`.

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

## Current constraints

- The Player working-file count is exactly **150**, equal to the enforced budget. Do not add another Player file without removing or consolidating one, or accepting a dedicated budget change.
- The `main-protection` ruleset is configured but not technically enforced on this private personal-account repository. Pull requests, CI, scope validation and governor review remain mandatory operational controls.
- RC719 reservations are not yet itemized.
- The accepted first storage seam and RC718 product identity are frozen unless a dedicated work package says otherwise.

## Still held

- Stable global identifier implementation or migration.
- Player-wide architecture refactoring.
- localStorage-to-IndexedDB migration.
- Backend, accounts and learner profiles.
- Cloud synchronization and remote catalog.
- Commerce, entitlements, institutional tenancy and publisher marketplace.

## Next mandatory gate

`ARC-WP-020` must be **design-only**.

It must define stable global identifiers and migration strategy before implementation, including:

- inventory of current technical IDs and editable labels;
- persistence, progress and import/export payload dependencies;
- collision and compatibility rules;
- migration order and mixed-version handling;
- rollback and failure recovery;
- adversarial cases and evidence requirements;
- exact future role scopes.

It must not change Player runtime, stored data, product identity or a held platform domain.

## Restart instruction

Use this instruction in a future session:

> Reprends le dépôt privé `stefm78/learnit-platform` depuis `docs/handover/STAGE_D_RESTART_CHECKPOINT.md`. Vérifie d’abord l’état réel de `main`, `governance/governor-state.json`, les work packages acceptés, les PR ouvertes et les checks. Considère Stage B, Stage C et le pilote Stage D comme acquis seulement si le dépôt et les preuves exactes le confirment. La prochaine étape autorisée est le design-only `ARC-WP-020` sur les identifiants stables et la migration; n’implémente aucun changement d’identifiant, de stockage, de backend ou de synchronisation. Préserve RC718, la première couture, le budget de 150 fichiers Player et les périmètres de rôles disjoints. Le dépôt prévaut sur tout ancien handover.

## Resume verification

Before any new action, confirm:

1. current `main` and open pull requests;
2. governor state and next mandatory gate;
3. promoted RC718 artifact hash;
4. accepted Stage C and Stage D evidence roots;
5. permanent Player CI, PR scope and repository governance status;
6. Player working-file count;
7. active risks and the unenforced-ruleset exception;
8. that no held domain has been entered.
