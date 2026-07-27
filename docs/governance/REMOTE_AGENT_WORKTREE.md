# Remote Agent Worktree

## Purpose

The Remote Agent Worktree gives an AI agent two bounded capabilities in a real Git checkout:

- `ANALYZE`: run one fixed, versioned, read-only analysis profile on an exact commit;
- `IMPLEMENT`: apply one scoped text patch, run one fixed validation profile, and commit only the exact tested result to the originating `agent/**` branch.

It is not an autonomous merge authority. It never writes directly to `main`.

## Common request envelope

Every request is staged under `.agent-jobs/<JOB-ID>/` and activated by writing `READY` last.

Common fields:

```json
{
  "schemaVersion": 1,
  "id": "LLV2-ANALYZE-001",
  "baseCommit": "<full-lowercase-40-character-sha>",
  "branch": "agent/llv2-analyze-001",
  "mode": "analyze"
}
```

The branch must start from the declared commit and contain only its job envelope before execution.

Unknown fields are rejected. In particular, a request cannot provide `command`, `commands`, `shell`, scripts, environment overrides, plugins or arbitrary paths.

## ANALYZE mode

An analysis request adds exactly one fixed profile:

```json
{
  "schemaVersion": 1,
  "id": "LLV2-ANALYZE-001",
  "baseCommit": "d0a68fb4f47545a795934dc90ecadc834304c61e",
  "branch": "agent/llv2-analyze-001",
  "mode": "analyze",
  "analysisProfile": "learnit-next-snapshot"
}
```

The validation job:

1. checks out the exact pull-request head without persisted credentials;
2. verifies the exact base commit and envelope-only branch;
3. runs repository governance validation and Remote Agent unit tests;
4. executes the selected fixed profile with `contents: read` only;
5. uploads the structured report and any tested HTML artifact;
6. creates no result commit and performs no push.

Supported analysis profiles:

- `learnit-next-snapshot`
- `learnit-next-fast`
- `learnit-next-full`
- `learnit-next-browser`
- `learnit-next-authoring`
- `learnit-next-contract`

`learnit-next-snapshot` reports the materialized runtime files, module import edges, test inventory, ownership groups, composition points and declared artifact identity.

## IMPLEMENT mode

Existing implementation requests remain compatible. `mode` may be omitted and defaults to `implement`.

```json
{
  "schemaVersion": 1,
  "id": "LLV2-DEV-001",
  "baseCommit": "<full-sha>",
  "branch": "agent/llv2-dev-001",
  "mode": "implement",
  "patchFile": ".agent-jobs/LLV2-DEV-001/change.patch",
  "allowedPaths": ["apps/learnit-next/src/core/**"],
  "forbiddenPaths": [],
  "testProfile": "learnit-next-fast",
  "commitMessage": "LLV2: implement bounded learning change"
}
```

The implementation sequence remains:

1. validate branch, base, patch, paths and budgets;
2. apply the patch without repository credentials;
3. validate repository governance;
4. run the fixed profile;
5. package the exact tested patch and manifest;
6. revalidate the envelope in a separate write-token job;
7. commit and push only to the originating `agent/**` branch;
8. attach `Remote agent worktree / tested result` to the exact result commit.

## Fixed profiles

Legacy profiles remain supported:

- `repository`
- `player-fast`
- `player-targeted`
- `player-full`

Learn-it Next profiles:

- `learnit-next-snapshot`: inventory only, no build;
- `learnit-next-fast`: deterministic build plus bounded contract, storage and P1 checks;
- `learnit-next-full`: deterministic build plus the complete unittest discovery suite;
- `learnit-next-browser`: deterministic build plus browser and P1 scenarios;
- `learnit-next-authoring`: validate both canonical golden kits with the foundation profile;
- `learnit-next-contract`: run the contract-v2 contradictory suite.

The profiles materialize the manifest-controlled Learn-it Next tree, including files preserved as Git blobs, before running commands. When a profile builds the application, the exact produced `apps/learnit-next/dist/learnit-next.html` is included in the evidence artifact.

## Permanent prohibitions

The fast implementation lane cannot modify:

- `.github/**`
- `.agent-jobs/**`
- `.agent-runtime/**` or `.agent-result/**`
- `governance/**`
- `docs/architecture/**`
- `work-packages/**`
- `tools/agent_worktree.py`
- Git metadata, binaries, symlinks or submodules

Workflow, governance, architecture, work-package, secret, release and policy changes use the normal governed branch and pull-request path.

## Security boundary

Patched or analyzed repository code executes only in the read-token validation job. `actions/checkout` does not persist credentials.

The write-token job does not execute repository tests. It only downloads and revalidates the previously tested result envelope, stages that exact result and pushes to the originating internal branch.

An `ANALYZE` job never reaches the write-token job.

## Limits

Hard implementation ceilings remain:

- 1,000,000 patch bytes;
- 80 changed files;
- 8,000 added plus deleted lines.

Each work package should set substantially smaller limits.

## Failure and recovery

A failed analysis leaves the branch unchanged and publishes diagnostics only.

A failed implementation leaves the pull request branch with its job envelope. Correct or replace the patch and update `READY` last to trigger a new attempt.

A successful analysis PR is evidence transport and should be closed unmerged after its report is consumed. A successful implementation PR exposes only the exact tested product change for normal review and an explicit human merge decision.
