# Learn-it — RC718 legacy standalone Player

`apps/player/` contains the frozen source of the promoted RC718 standalone generation.

## Product status

- source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`;
- promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`;
- human gate: **RC719 — PASS_WITH_RESERVATIONS**;
- current role: historical access and explicitly bounded maintenance only.

RC716–RC718 added editable imported-plan naming while preserving package identity, course identifiers, learner progress, bilan and resume behavior.

## Reproducible commands

```bash
python dev/update_manifest.py
python build.py
python dev/run_all_checks.py --skip-build --include-browser --artifact dist/learnit.html
python dev/release_pipeline.py --output-dir release
```

Generated `dist/`, `build/` and `release/` outputs are not committed.

## Clean-break boundary

RC718 is not the runtime foundation of a transparent successor upgrade.

New-generation work must not:

- change RC718 storage semantics to prepare migration;
- read, clear or rewrite RC718 browser data;
- add a compatibility resolver, identity overlay or dual-key path;
- make RC718 packages silently valid under a successor contract;
- copy this complete Player without a justified bounded design.

The successor must use a new major contract, isolated localStorage and IndexedDB namespaces, canonical identities from creation and an empty active state. Its implementation remains blocked until `ARC-WP-022` is accepted.

## Maintenance rule

Any RC718 correction requires its own bounded work package, full Player CI, exact source-to-artifact provenance and an explicit decision on whether the legacy artifact is repromoted. Clean-generation changes must use separate files and release identity.
