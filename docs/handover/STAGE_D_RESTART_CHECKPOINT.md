# Learn-it architecture restart checkpoint

## Canonical status

Repository state always takes precedence over this checkpoint. Verify current `main`, `governance/governor-state.json`, accepted work packages, open pull requests and exact evidence before acting. Historical handovers and architecture references are not canonical when they conflict with the repository.

Common clean-generation implementation base: `d0186d7c0d65d44287c59534855ea90ffa3f8d06`.

## Legacy product baseline

The successor program does not modify the promoted legacy product:

- Frozen standalone generation: **RC718**.
- Product source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`.
- Promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`.
- Human gate: **RC719 — PASS_WITH_RESERVATIONS**.
- Human evidence: `docs/evidence/rc718/human-validation-attestation.json`.
- RC718 remains independently usable and must not be read, migrated, reset or mutated by successor work.

## Accepted architecture history

- `ARC-WP-014`: first reversible storage seam accepted; exact result `a4bf1fb1726c5c82e1af2ae085327e358fe4e3f4`.
- `ARC-WP-019`: controlled Stage D multi-role pilot accepted; exact result `5e379eea7ae3b495be2203355425e6549b8fcec5`.
- `ARC-WP-020`: stable identity taxonomy accepted; legacy migration sequence later superseded.
- `ARC-WP-021`: trajectory C clean break accepted.
- `ARC-WP-022`: minimum clean-generation contract, storage, slice and 32-file plan accepted.
- `ARC-WP-023`: exact subordinate parallel execution scopes accepted.

## Clean-generation foundation

### Contract

- Discriminator: `learnit.kit.v2`.
- Normative schema: `contracts/learnit-kit-v2.schema.json`.
- Canonical IDs: persisted lowercase UUID version 4 values.
- Digests: SHA-256 over the bounded canonical JSON profile.
- Foundation activity families: QCM and fill only.
- QCM answers use choice IDs.
- Fill activities use slot/token IDs and token `maxUses`.
- RC718 `learnit.import.v1.1` packages fail closed.

### Storage

- Successor localStorage prefix: `learnit.next.v1.`.
- Successor IndexedDB database: `learnit_next_v1`.
- RC718 localStorage keys and `learnit_durable_library_v1` are protected.
- Integrated tests must prove RC718 storage unchanged after successor boot, import, session and reset.

### Product slice

```text
empty library
→ strict v2 import
→ library
→ one course session
→ QCM and fill
→ progress persistence
→ refresh/restart recovery
```

The slice does not claim RC718 parity, mastery, retention or pedagogical completeness.

### File budget

`docs/architecture/clean-generation/FILE_PLAN_V1.json` freezes exactly **32 working files**:

- one frozen contract schema;
- 14 runtime/UI files;
- five authoring files;
- seven fixture/test files;
- five integration files.

No path may be added, renamed or split without a new governor decision.

## Parallel work is now authorized

The following three work packages may start concurrently from exact base `d0186d7c0d65d44287c59534855ea90ffa3f8d06`:

### DEV-WP-031 — runtime and UI

Owns only the 14 runtime/UI paths under `apps/learnit-next/` listed in the work package.

It implements contract/semantic validation, canonical digests, fail-closed import, isolated IndexedDB storage, library, QCM/fill sessions, progress and minimal UI.

### KIT-WP-001 — authoring and golden kits

Owns only five paths under `authoring/v2/`.

It implements UUID/digest tooling and representative Nombres complexes and Signaux électriques foundation kits.

### QA-WP-011 — contradictory QA and fixtures

Owns only three fixtures and four tests.

It specifies valid, legacy and digest-conflict inputs and attacks contract semantics, RC718 storage isolation, browser vertical flow and deterministic build requirements.

The three allowed-path sets are disjoint. Each role uses its own branch, clone or worktree and cannot certify itself.

## Integration remains held

`INT-WP-001` owns only:

- `apps/learnit-next/build.py`;
- `apps/learnit-next/source_manifest.json`;
- `apps/learnit-next/dev/run_checks.py`;
- `apps/learnit-next/dev/release.py`;
- `.github/workflows/learnit-next-ci.yml`.

The integrator starts only after exact independently reviewed result commits exist for all three parallel roles. It must return defects to the owning role instead of silently editing role-owned files.

## Current risks

- Main protection is configured but not technically enforced on the current private personal-account repository.
- The 32-file budget may prove too narrow; expansion requires a separate decision.
- Python and JavaScript canonical digest implementations may diverge.
- Same-origin storage isolation requires strong negative tests.
- Branches authorized from the earlier immutable base must prove clean diffs against later `main`.
- The successor requires explicit clean-break communication before human testing.
- RC719 reservations remain unitemized and are not successor requirements by default.

## Still held

- Integration before independent acceptance of all three parallel outputs.
- Human successor testing before integrated automated gates and governor acceptance.
- Any successor file outside the 32-file plan.
- Any RC718 compatibility, migration or package interpretation.
- Media and activity families beyond QCM and fill in the foundation slice.
- Advanced bilan, mastery, retention, adaptive sequencing and content patches.
- Backend, accounts, synchronization, remote catalog, commerce, tenancy and marketplace.

## Next mandatory gate

The next gate is `INT-WP-001`, but it is condition-based rather than immediate.

Before integration, obtain independently reviewed exact result commits for:

1. `DEV-WP-031`;
2. `KIT-WP-001`;
3. `QA-WP-011`.

Then the integrator must prove:

- exact 32-file set;
- shared Python/JavaScript canonical bytes and digests;
- both golden kits valid;
- legacy import atomic rejection;
- RC718 storage immutability;
- browser vertical slice;
- deterministic clean build;
- tested artifact equals proposed artifact;
- no held domain or unplanned dependency.

A separate governor acceptance is required before human testing.

## Restart instruction

> Reprends le dépôt privé `stefm78/learnit-platform` depuis `docs/handover/STAGE_D_RESTART_CHECKPOINT.md`. Vérifie `main`, le gouverneur, les PR et les checks. RC718 reste figée. La trajectoire C et `learnit.kit.v2` sont canoniques. `DEV-WP-031`, `KIT-WP-001` et `QA-WP-011` sont autorisés en parallèle depuis `d0186d7c0d65d44287c59534855ea90ffa3f8d06` sur leurs chemins strictement disjoints. Ne modifie pas le schéma, ne crée aucun fichier hors plan, n’accède pas au stockage RC718 et n’entre dans aucun domaine held. `INT-WP-001` reste bloqué jusqu’aux trois résultats exacts revus indépendamment.

## Resume verification

Before any action, confirm:

1. current `main` and open pull requests;
2. governor state and next condition gate;
3. frozen RC718 source and artifact hash;
4. accepted v2 schema, foundation and exact file plan;
5. exact common implementation base;
6. active role branches, results and path ownership;
7. no overlap, contract mutation or unplanned file;
8. current risks, exception and protected RC718 storage list;
9. that integration or held-domain work has not started prematurely.
