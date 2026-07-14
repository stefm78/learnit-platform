# Permanent player CI

`Player CI` protects the standalone player without changing runtime behavior.

## Required gate

The stable pull-request check is:

```text
Player CI / gate
```

It succeeds only when all of the following pass on the same exact candidate commit:

1. browser-suite inventory validation;
2. clean player build;
3. mandatory contract and mutation checks;
4. source-manifest freshness and source-tree verification;
5. artifact identity recording;
6. CI-guard adversarial self-tests;
7. every browser suite in an independent matrix job;
8. artifact and source identity verification before and after each browser suite.

## Browser isolation

The browser matrix is generated from `dev/checks_registry.json`. The guard compares the registry with every `tests/browser_*.py` file. A missing, stale or duplicate suite fails the inventory job before browser execution.

`fail-fast` is disabled. A failed or timed-out suite does not prevent the remaining suites from producing their own statuses and evidence.

Each browser job:

- checks out the exact source candidate;
- downloads the HTML built once by the build job;
- verifies its SHA-256 and source bindings;
- installs Chromium;
- runs exactly one suite with a hard timeout;
- verifies that neither the artifact nor its source binding changed;
- uploads the suite report for 14 days.

## Local reproduction

From the repository root:

```bash
python -m pip install -r apps/player/requirements-test.txt
python -m playwright install chromium
python apps/player/dev/ci_guard.py inventory
make -C apps/player test-fast
python apps/player/dev/ci_guard.py record \
  --artifact apps/player/dist/learnit.html \
  --output apps/player/reports/ci_artifact.json
python apps/player/dev/ci_guard.py self-test
python apps/player/tests/browser_library_persistence_naming.py
python apps/player/dev/ci_guard.py verify \
  --artifact apps/player/dist/learnit.html \
  --manifest apps/player/reports/ci_artifact.json
```

The complete local browser registry remains available through:

```bash
make -C apps/player test
```

The permanent GitHub workflow deliberately executes browser suites separately instead of using the monolithic local runner.

## Evidence and retention

The build job uploads:

- `dist/learnit.html`;
- `reports/ci_artifact.json`;
- `reports/aggregate_report.json`.

Each browser job uploads its bounded report and the shared artifact manifest. Evidence is retained for 14 days. Generated HTML and reports remain outside source control.

## Security and provenance boundary

- workflow permissions are read-only;
- checkout credentials are not persisted;
- the artifact is built once and reused by all browser jobs;
- the exact artifact SHA, source commit, source manifest and checks registry are bound together;
- a changed source file after build, a changed artifact, or an omitted browser suite causes failure;
- this workflow does not publish a release or promote a baseline.
