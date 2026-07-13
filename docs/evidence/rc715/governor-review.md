# Governor review — SRC-WP-001 RC715 import

Date: 2026-07-13  
Repository: `stefm78/learnit-platform`  
Base commit: `56713bbe08efa3783e9a6e84f971930f1621ce39`  
Imported source commit on the import branch: `965113f758d7eac710b097a5e190b5ce3dcb638f`  
Canonical main development-baseline commit: `6c826977e16985d50b45d1b5e53501b4d7b993a2`  
Work package: `SRC-WP-001`

## Decision

**GO_WITH_CONDITIONS**

RC715 is accepted as the active GitHub development baseline. It is not accepted as a human-promoted stable standalone release.

## Evidence

- outer package SHA-256 verified: `f5e1bd5b17a9e16a6e14962d6db18632abb954bf71a68935c9186e8b1c190033`;
- nested minimal-source archive SHA-256 verified: `c6854bee987cfea2c2e7673fa0611d58e2f1db15fdb0c19e202806afee140eb4`;
- 145 regular source files found and 145 source files committed;
- archive traversal, absolute paths, duplicate paths, and symbolic links rejected by the import gate;
- source rebuilt in GitHub Actions;
- rebuilt artifact SHA-256 verified: `6d4546efbf9a1216e18fa90ee260e7d79841171c48f533d6b107266e281aa7c0`;
- mandatory non-browser checks passed from imported source;
- repository governance validation passed;
- transfer ZIPs, encoded transfer fragments, generated build outputs, and one-shot import workflows are absent from the merged tree;
- the canonical `main` baseline is the squash-merge commit `6c826977e16985d50b45d1b5e53501b4d7b993a2`.

## Claims and absence of evidence

- RC715 remains automation-ready rather than human-promoted;
- complete browser, Android, keyboard, assistive-technology, persistence, and rename promotion evidence remains governed by `ARC-WP-000`;
- branch protection and mandatory independent review remain an open repository risk;
- machine-enforced changed-file scope remains an open governance risk.

## Conditions

1. GitHub becomes the canonical source for subsequent standalone RC work.
2. No separate local source may continue as the authoritative development line.
3. Player-wide refactoring, global identifier migration, IndexedDB migration, backend, accounts, synchronization, remote catalog, commerce, institutional tenancy, and marketplace work remain on HOLD.
4. RC715 must not be represented as `standalone-v1.0` or as a human-promoted baseline.
5. `ARC-WP-000` remains the next mandatory application gate.

## Rollback

Revert the squash-merge commit `6c826977e16985d50b45d1b5e53501b4d7b993a2`. No application data migration or remote system change is part of this work package.
