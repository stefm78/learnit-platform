# GOV-REVIEW-0011 — First-seam fingerprint gate HOLD and bounded correction

## Decision

**GO_WITH_CONDITIONS for the correction; HOLD for Stage C and Stage D.**

The first implementation attempt is not accepted. Pull request 44 was closed unmerged after Remote Agent run `29329093616` passed envelope validation, patch application and repository validation but failed the fixed `player-full` profile. Packaging and tested-result attestation were skipped, so there is no result commit that can be reviewed or promoted.

## Evidence

1. `apps/player/tests/contract_source_tree.py` computes `runtime_fingerprint` by hashing every active source path name and its bytes. A source-only split therefore changes that fingerprint even when the concatenated runtime behavior is unchanged.
2. The same contract compares that computed value to `dev/release_config.json.runtime_fingerprint`.
3. The normalized JavaScript guard also hashes path names, but excludes paths listed in `baseline_equivalence.ignored_script_paths`.
4. Runtime part `00` is already in that ignored set because it contains accepted post-baseline behavior. The mechanically relocated unchanged adapter in new part `04` is not yet listed.
5. The failed branch did not change release configuration, as originally required. The guard therefore rejected stale path-sensitive metadata rather than proving a behavioral regression.

## Evidence versus inference

- **Evidence:** the fixed profile failed and no tested result exists.
- **Evidence:** the executable source-tree contract and release configuration are path-sensitive.
- **Inference:** these stale fingerprints caused the failure. The connector log was truncated before the individual check output, so this must be confirmed by a deterministic disposable diagnostic before the final patch is prepared.
- **Absence of evidence:** there is no proof that the normalized runtime semantic fingerprint would remain unchanged after adding part `04` to the existing ignored set. This absence is itself a gate.

## Accepted bounded correction

1. Run a disposable, unmerged Remote Agent diagnostic on exact accepted seam bytes.
2. The diagnostic may only emit:
   - the computed path-sensitive runtime fingerprint;
   - the normalized runtime fingerprint after treating new part `04` as the relocated continuation of already ignored part `00`;
   - exact base, trigger and source-path identities.
3. If the normalized value differs from the currently protected value, stop. Do not update it under this work package.
4. If it matches, the final integrator may change `release_config.json` only by:
   - adding `src/scripts/core/runtime_parts/04_local_storage_port.js` to `baseline_equivalence.ignored_script_paths`;
   - replacing `runtime_fingerprint` with the diagnostic value computed from the exact final bytes.
5. All other release metadata and every source-tree guard remain frozen.

## Role separation

- Developer: four implementation files only.
- Contradictory QA: focused contract and one mandatory registry entry only.
- Integrator: release fingerprint metadata and evidence only.
- Governor: work packages, state and reviews only.

No role may repair another role’s files while certifying them.

## Adversarial conditions

The result is HOLD if the diagnostic branch is merged, if the normalized fingerprint changes, if the fingerprint algorithm or guard is weakened, if product identity metadata changes, if the measured bytes differ from the final proposed bytes, or if any storage/UI/behavior contract changes.

## Conclusion

ARC-WP-013 is a correction to evidence binding, not an exception to tests. Stage C remains HOLD until a fresh exact result is independently tested and accepted. Stage D remains blocked.
