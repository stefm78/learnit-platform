# Stage D restart checkpoint

## Purpose

This file is the canonical restart point for resuming the Learn-it architecture program after the RC719 human gate.

## Current product baseline

- Promoted standalone baseline: **RC718**
- Source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`
- Validated artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`
- Human gate: **RC719 — PASS_WITH_RESERVATIONS**
- Human evidence: `docs/evidence/rc718/human-validation-attestation.json`
- Reservations are non-blocking but must be itemized before any corrective implementation.

## Important sequencing rule

Stage D cannot be entered directly from this checkpoint.

The following gates must first be completed and accepted:

1. **Stage B — ARC-WP-010 design**
   - map every current storage access;
   - define one minimal storage boundary;
   - preserve storage technology, keys, data shapes, identifiers, UI and behavior;
   - define black-box equivalence tests and rollback.
2. **Stage C — first reversible seam implementation**
   - implement only the accepted boundary;
   - no IndexedDB, identity migration, sync, backend or functional UX change;
   - permanent Player CI must pass;
   - governor review must accept the seam.

Only then may Stage D begin.

## Stage D objective

Run the first controlled multi-AI implementation pilot on a bounded, reversible task with disjoint responsibilities:

- Developer agent: implementation within exact allowed paths.
- Adversarial QA agent: tests and failure scenarios, without editing implementation files.
- Integrator agent: diff, contract, provenance and rollback review.
- Governor: GO, GO_WITH_CONDITIONS, HOLD or NO_GO.

All agents must use:

- the exact accepted base commit;
- one canonical work package;
- machine-checkable `allowedPaths` and `forbiddenPaths`;
- bounded diff size;
- explicit test profile;
- the Remote Agent Worktree for implementation;
- the permanent Player CI for behavioral protection.

## Restart instruction

Use this exact instruction in a future chat:

> Reprends le dépôt privé `stefm78/learnit-platform` depuis `docs/handover/STAGE_D_RESTART_CHECKPOINT.md`. Vérifie l’état réel de `main`, les work packages et les gates. Ne saute pas ARC-WP-010 ni la première couture réversible. Si les étapes B et C sont acceptées, lance l’étape D avec un développeur, un QA contradictoire, un intégrateur et le gouverneur, sur des périmètres de fichiers disjoints. Sinon, termine d’abord les gates manquants. N’utilise aucun ancien handover comme source canonique si le dépôt le contredit.

## Resume gate

Before any action, the next session must verify:

- `main` is the only permanent branch when no PR is open;
- the current promoted baseline and artifact hash match governor state;
- RC719 reservations are either still deferred or explicitly itemized;
- `ARC-WP-010` exists and is accepted;
- the first reversible seam has a merged implementation and an accepted governor review;
- Player CI and repository governance are green on the exact base commit;
- no held domain has been entered.

## Still held

- player-wide refactor;
- global identifier migration;
- localStorage to IndexedDB migration;
- backend, accounts, cloud sync and remote catalog;
- commerce, institutions and marketplace.
