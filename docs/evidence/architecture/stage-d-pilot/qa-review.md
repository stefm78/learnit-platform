# Contradictory QA review — Stage D role-scope pilot

## Verdict

**PASS** on exact tested result `5e379eea7ae3b495be2203355425e6549b8fcec5`.

## Independence

QA owned only `apps/player/tests/contract_role_scope.py`. It did not edit the developer tool, integration metadata or governor records.

## Adversarial coverage

The contract passed 20 of 20 checks covering:

- valid assignment across all four mandatory roles;
- identical patterns owned by two roles;
- overlap between a glob and an exact path;
- unowned changed paths;
- duplicate patterns within one role;
- missing, empty, wrong-type and unexpected role scopes;
- empty, absolute, Windows-drive, parent-traversal and malformed repository paths;
- deterministic canonical output under reordered inputs;
- CLI success and explicit output creation;
- non-zero exit for invalid ownership;
- malformed-input exit behavior;
- absence of implicit output.

## Exact result gates

- Remote Agent `player-fast`: PASS.
- Mandatory checks: 36/36.
- Evidence bindings: 35/35.
- Permanent Player CI: PASS.
- Permanent browser suites: 24/24.
- PR scope: PASS.
- Repository governance: PASS.
- Branch hygiene: PASS.

## Negative-scope review

The implementation changes exactly four authorized paths. It does not modify Player runtime, source manifest, release configuration, workflow, product artifact, accepted storage seam or a held platform domain.

## Decision

The Stage D pilot meets the contradictory-QA gate without waiver or exception.
