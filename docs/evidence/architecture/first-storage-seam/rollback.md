# Rollback proof — first reversible storage seam

## Trigger

Rollback is required if a post-merge regression is proven to originate from the storage-port extraction or if the accepted boundary invariants are later found false.

## Operation

Revert merge commit `1346e5772bd18432d96b2f88eb0d276fc7a04e94` through a reviewed pull request.

The revert must restore:

1. the complete synchronous storage adapter to `00_runtime_boot_and_content_library.js`;
2. removal of `04_local_storage_port.js`;
3. the previous source-manifest order and hashes;
4. the previous owner-map description;
5. removal of `contract_storage_boundary.py` from the source tree and mandatory registry;
6. removal of its `storage-resilience` evidence-map entry;
7. the previous runtime fingerprint and ignored-path list.

## Data impact

None.

- Storage keys are unchanged by the forward change and by the rollback.
- localStorage payloads are unchanged.
- IndexedDB database name, stores, identifiers and payloads are unchanged.
- No migration, backfill, remote compensation or learner-state conversion is required.

## Verification after rollback

- run `player-full`;
- require permanent Player CI, PR scope and repository governance;
- verify the restored runtime fingerprint;
- verify the promoted RC718 artifact identity or document any independent main drift;
- confirm existing learner library and progress remain readable.

## Recovery objective

The boundary can be removed with one revert while preserving learner data and product behavior. This satisfies the reversibility requirement of the first architectural seam.
