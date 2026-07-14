# Integration review — Stage D role-scope pilot

## Verdict

**PASS** for exact tested result `5e379eea7ae3b495be2203355425e6549b8fcec5`, integrated by merge commit `ae6b82d90b72f0287462c7d34708d0330d5ce35b`.

## Provenance chain

- Exact base: `d65189b7ef59ccb74ba02c6c6ac96a212895a1e9`.
- Remote Agent trigger: `c0101bde910c8f3a47ce7f981a4e939a55176589`.
- Exact tested result: `5e379eea7ae3b495be2203355425e6549b8fcec5`.
- Remote Agent run: `29356520176`.
- Result envelope digest: `sha256:c4c6123c58caf8c070f47fe7c19970cabfa12b41bbd846caf517bd0b7361fb13`.
- Result patch SHA-256: `cf93ecf7ca553712e957a397fd3b94a392f34e7782a1e58554e7c3447ec15af5`.
- Permanent Player CI: `29356634330`.
- Integration PR: #72.
- Merge commit preserves the exact tested result as a parent.

## Product and artifact identity

The built artifact remains:

- 829075 bytes;
- SHA-256 `9e9db99065b678267818eb478849d7bd02c2e34e42f2f8e0628e01a3c22ef861`;
- product identity RC718.

The pilot therefore changes repository quality tooling only. It does not create or promote a product RC.

## Registration integrity

- `tests/contract_role_scope.py` is registered once in the mandatory registry.
- It is mapped once to the existing `source-and-build` evidence surface.
- No existing registry or evidence-map entry is removed, moved or modified.
- The Player working-file count is exactly 150, at the declared ceiling.

## Role integration

Every implementation path has exactly one owner:

- developer: one tool file;
- contradictory QA: one test file;
- integrator: two metadata files;
- governor: no implementation file.

## Rollback

One reviewed revert removes the two new files and restores the two metadata files. No learner data, artifact, storage, identifier, external system or migration is involved.

## Decision

The pilot is provenance-bound, deterministic, reversible and suitable for final governor acceptance.
