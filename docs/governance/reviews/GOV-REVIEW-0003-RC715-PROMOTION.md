# Governor review — ARC-WP-000 RC715 promotion

Date: 2026-07-14  
Repository: `stefm78/learnit-platform`  
Promoted source commit: `6c826977e16985d50b45d1b5e53501b4d7b993a2`  
Artifact SHA-256: `6d4546efbf9a1216e18fa90ee260e7d79841171c48f533d6b107266e281aa7c0`  
Work package: `ARC-WP-000`

## Decision

**GO**

RC715 is promoted as the forensic standalone baseline. This decision closes the standalone promotion gate; it does not authorize the held platform capabilities.

## Evidence

- RC715 source is present in GitHub under `apps/player/`;
- the source archive SHA-256 is `c6854bee987cfea2c2e7673fa0611d58e2f1db15fdb0c19e202806afee140eb4`;
- 145 regular source files were safely extracted and committed;
- GitHub Actions rebuilt the candidate from the imported source;
- the rebuilt artifact matches SHA-256 `6d4546efbf9a1216e18fa90ee260e7d79841171c48f533d6b107266e281aa7c0`;
- mandatory non-browser checks passed;
- repository governance validation passed;
- the accountable owner, `stefm78`, attested PASS for the complete requested human promotion gate on 2026-07-14;
- the exact human attestation is recorded in `docs/evidence/rc715/human-validation-attestation.json`.

## Evidence classification

### Directly reconstructed evidence

- source and package hashes;
- safe extraction controls;
- source inventory;
- clean GitHub Actions build;
- artifact identity;
- mandatory non-browser checks;
- repository governance checks.

### Accountable-owner attestation

- human validation result: PASS;
- scope: persistence, rename, desktop, Android, keyboard, assistive-technology, and the complete requested RC715 human gate.

### Absence of evidence

- raw screen recordings, screenshots, device logs, and per-case human-test forms are not committed;
- complete permanent browser-matrix execution is not yet enforced on every future sensitive pull request.

The owner attestation is accepted as sufficient human gate evidence for this promotion. Its documentary limitation remains visible as a low residual risk.

## Invariants

- no application source or behavior is changed by this promotion decision;
- the promoted baseline points to the exact source commit that reconstructs the tested artifact;
- GitHub remains the sole canonical development source;
- current and future changes remain traceable against the promoted baseline;
- architecture-target documents are not represented as already implemented.

## Conditions after promotion

1. Establish permanent player CI and representative black-box regression fixtures under `QA-WP-010`.
2. Do not begin the first architectural seam until `QA-WP-010` is accepted.
3. Keep player-wide refactoring, identifier migration, IndexedDB migration, backend, accounts, synchronization, catalog, commerce, institutions, and marketplace work on HOLD.
4. Continue standalone fixes only through bounded pull requests with tests and explicit provenance.
5. Retain RC715 as the rollback and behavioral-comparison reference.

## Open risks

- branch protection and required-review policy remain to be independently verified;
- machine-enforced work-package changed-file scope remains to be implemented;
- permanent complete browser CI remains to be established;
- detailed raw human evidence is absent, although owner PASS is durably recorded.

## Next mandatory gate

`QA-WP-010`

Permanent player CI and representative black-box regression fixtures must protect RC715 behavior before the first architectural seam is implemented.

## Rollback

Revoke the promotion in `governance/governor-state.json` and revert the promotion-governance pull request. The source commit and artifact hash remain immutable forensic references.
