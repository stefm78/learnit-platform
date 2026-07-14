# GOV-REVIEW-0004 — Remote Agent Worktree acceptance

## Decision

`GO_WITH_CONDITIONS`

## Scope reviewed

- `.github/workflows/remote-agent-worktree.yml`
- `tools/agent_worktree.py`
- `docs/governance/REMOTE_AGENT_WORKTREE.md`
- `templates/agent-job/job.example.json`
- `work-packages/DEV-WP-030.json`
- smoke evidence and GitHub Actions execution records

No player runtime source, storage model, identifiers, contracts, backend, synchronization or architecture HOLD boundary was changed by this work package.

## Evidence

### Repository-profile execution

- workflow run: `29317700613`
- exact trigger commit: `36e4cbaededd317232ab82c85e022fc14fd86d3f`
- exact result commit: `3109425d8620521ba3c14170acc82a44a8fe8d0e`
- result message contained `[agent-applied]`
- job envelope removed
- final diff restricted to one evidence file
- decision: PASS

### Exact-result status execution

- workflow run: `29318087482`
- exact trigger commit: `8d8af4509a213c8f1ace7b979489dace73969651`
- exact result commit: `670128b9a2d81bdec67c15fb2e1ca4bfd0a76b33`
- commit status: `Remote agent worktree / tested result = success`
- status target linked to the workflow run
- status-writing job checked out and executed no repository code
- decision: PASS

### Player-targeted execution

- workflow run: `29318562880`
- exact baseline: `55bc0078386728cb6ce467f2ce00823be1780cc3`
- exact trigger commit: `65da97ca4291faccbe9873e78bd4009cda019be4`
- exact result commit: `512191048927b21ba0fd82a14735968b96c4fa52`
- dependencies and Chromium installation: PASS
- deterministic RC718 build: PASS
- built artifact: 829005 bytes
- artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`
- browser persistence and naming regression: 18/18 PASS
- final result status on exact SHA: PASS
- final PR diff restricted to one evidence file

## Claims and boundaries

### Proven

- a same-repository `agent/**` pull request can transport one bounded text patch into a clean GitHub runner worktree;
- exact baseline, branch, paths, patch digest, file budget and line budget are machine checked;
- binaries, symbolic links, submodules and permanently forbidden paths are rejected;
- patched code is built and tested without repository write credentials;
- the exact tested result is revalidated before commit;
- the workflow writes only to the originating `agent/**` branch;
- temporary job files are removed from the result;
- the exact result SHA receives a durable success status;
- the real RC718 build and one representative browser suite execute successfully through this lane.

### Not proven or not authorized

- autonomous merge safety;
- every browser suite and the full permanent player matrix;
- branch protection or ruleset enforcement of the tested-result status;
- suitability for workflows, governance, architecture, migrations, secrets or held platform domains;
- protection against a malicious repository maintainer changing both workflow and validator in one governed change.

## Residual risks

1. Branch protection and mandatory review rules remain independently unverified.
2. The exact-result status is generated correctly but is not yet required by a repository ruleset.
3. The full player profile has not yet been exercised through this lane; the targeted RC718 browser suite and repository profiles have.
4. Conventional non-agent PRs still rely on review rather than the Remote Agent path-scope validator.

## Conditions

- no autonomous merge authority;
- an explicit human or governed AI review remains mandatory before merge;
- sensitive player changes use explicit targeted or full profiles until `QA-WP-010` is accepted;
- repository rulesets should eventually require `Remote agent worktree / tested result` for `agent/**` pull requests;
- workflow, governance, architecture, work-package, secret and held-platform changes remain outside the fast lane.

## Governor conclusion

The Remote Agent Worktree is accepted as the preferred development transport for bounded multi-file Learn-it changes under the stated conditions. It substantially reduces connector latency while preserving exact baseline, scope, test and provenance controls.
