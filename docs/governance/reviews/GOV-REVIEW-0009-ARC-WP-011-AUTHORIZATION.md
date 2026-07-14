# GOV-REVIEW-0009 — First reversible seam implementation authorization

## Decision

**GO_WITH_CONDITIONS**

The first seam implementation is authorized only within the exact mechanical design and disjoint write scopes accepted previously. This is authorization to prepare and review an implementation pull request; it is not implementation acceptance and it does not open the later controlled multi-agent stage.

## Exact baseline

- Repository base: `06c5aee917b67bb996f703097e9a7300c0e43fff`
- Promoted product source: `decd9b77bc77a6de9dc28497d0f3affeb972e964`
- Promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`
- Accepted design: `docs/architecture/seams/ARC-WP-010_LOCAL_STORAGE_PORT.md`

## Authorized implementation

The developer may only:

1. remove the current inline synchronous `storage` adapter block from runtime part `00`;
2. add that unchanged block as runtime part `04_local_storage_port.js`;
3. insert `04` between `00` and `05` in the source manifest and regenerate its source fingerprints through the existing build;
4. update the owner map for `00`, `04` and `05`.

The adversarial QA author may only add the focused storage-boundary contract test. QA may inspect but not edit implementation files.

The integrator may only record evidence after reading the exact result. The governor may only update governance artifacts after independent evidence exists.

## Required execution controls

- exact base commit;
- internal `agent/**` branch;
- Remote Agent Worktree;
- `player-full` validation profile;
- no arbitrary shell command;
- no direct push to `main`;
- no autonomous merge;
- exact tested-result commit status;
- permanent Player CI and PR-scope checks;
- complete diff and rollback review.

## Contradictory review criteria

QA must actively seek and report:

- changed adapter error semantics;
- lost or renamed keys;
- duplicate primitive owners;
- moved IndexedDB ownership;
- manifest-order mistakes;
- test-only behavior that differs from production behavior;
- stale generated fingerprints;
- hidden edits outside the accepted four implementation paths;
- false equivalence claims based only on static checks.

The integrator must reject the result if the developer and QA scopes overlap, if the exact tested commit cannot be identified, or if a simple revert no longer restores the prior boundary.

## Governor boundaries

Implementation remains **HOLD** if any of the following occurs:

- scope expansion beyond the accepted extraction;
- modification of release configuration, product contract, UI or unrelated runtime code;
- any storage key, data-shape, identifier or technology change;
- missing full Player CI or Remote Agent result evidence;
- unresolved adversarial QA finding;
- evidence attached to a different commit than the proposed result.

## Conclusion

The separate implementation work package is authorized. Its result must return for independent QA, integration and governor acceptance. The later controlled multi-agent stage remains blocked.
