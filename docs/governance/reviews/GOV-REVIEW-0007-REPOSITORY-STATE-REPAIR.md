# GOV-REVIEW-0007 — Repository state repair before architecture restart

## Decision

**GO_WITH_CONDITIONS**

The repository may resume with Stage B design only after the exact repair pull-request head passes `Repository governance` and `PR scope / gate` and is merged. Stage C and Stage D remain blocked.

## Exact base reviewed

- Repository: `stefm78/learnit-platform`
- Base commit: `06c6b25d11adcf24f06bb44d3eb092b0ba995cbe`
- Promoted product source: `decd9b77bc77a6de9dc28497d0f3affeb972e964`
- Promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`
- Human gate: `RC719 — PASS_WITH_RESERVATIONS`

## Evidence

1. `tools/validate_repository.py` accepts only the canonical work-package statuses listed in its `ALLOWED_STATUSES` set. `GOV-WP-013` used `accepted-with-conditions`, which is not in that executable vocabulary.
2. The same validator accepts generic phase statuses including `blocked`, and promoted-baseline status `promoted`. The governor state instead used unvalidated values `paused-before-architecture-stage-b` and `promoted-with-reservations`.
3. The validator requires each active exception to contain `id`, `rule`, `reason`, `owner`, `expiryOrRemovalGate` and `rollback`. `EXC-GOV-001` used a different, non-executable field set.
4. The latest promotion-record changes were present on `main`, but no pull-request-triggered workflow run was attached to the resulting head commit. This is consistent with the already-declared risk that the private personal-account ruleset is configured but not enforced.
5. No evidence shows that `ARC-WP-010` exists or that a first reversible seam has been implemented and governor-accepted.

## Claim, assumption and absence of evidence

- **Claim:** the current promotion identity remains valid. It is supported by unchanged source and artifact hashes in the checkpoint, governor state and GOV-REVIEW-0006.
- **Claim:** repository governance on the pre-repair head is not machine-proven. It is supported by the executable-schema mismatch above and absence of pull-request workflow runs on that head.
- **Assumption:** no unlisted permanent branch exists. PR #39 previously recorded independent verification of a main-only state, and no pull request is currently open, but the connector did not return a live complete branch inventory in this session.
- **Absence of evidence:** Stage B and Stage C acceptance records do not exist. This absence blocks Stage D.

## Repair accepted

- Normalize `GOV-WP-013.status` to `accepted`; its `result.decision` continues to preserve `GO_WITH_CONDITIONS`.
- Normalize `currentPhase.status` to `blocked` and `promotedBaseline.status` to `promoted`; the detailed reservation and sequencing semantics remain in dedicated fields and descriptions.
- Express `EXC-GOV-001` using the executable exception schema without weakening or hiding the exception.
- Record `GOV-WP-014` as the bounded repair authority.
- Keep `ARC-WP-010` as the next mandatory gate.

## Adversarial review

The repair must fail or be held if it:

- changes any `apps/player/**`, `.github/**`, `tools/**`, `docs/architecture/**`, `contracts/**` or `platform/**` path;
- changes the RC718 promoted source commit or artifact SHA;
- claims Stage B, Stage C or Stage D completion;
- removes the unenforced-ruleset exception;
- invents RC719 reservation details;
- broadens a work-package scope only to obtain a green check.

## Residual risks and conditions

- `RISK-GOV-002` and `EXC-GOV-001` remain active until GitHub technically enforces the main ruleset.
- RC719 reservations remain unitemized and may not be used as corrective requirements until the owner states them explicitly.
- The next permissible architecture action is design-only `ARC-WP-010` source cartography and seam specification.
- The first seam implementation remains held until ARC-WP-010 is separately accepted.

## Governor conclusion

After both repository gates pass on the exact repair head, merge is **GO_WITH_CONDITIONS**. Then prepare ARC-WP-010. Do not start the reversible seam or Stage D from this work package.
