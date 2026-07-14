# Remote Agent Worktree

## Purpose

This mechanism lets an AI development agent prepare a bounded multi-file change in a real, clean Git checkout without requiring Codex, Codespaces, or a developer workstation.

It is a transport and validation mechanism, not an autonomous merge authority.

## Operating sequence

1. Create an `agent/**` branch from one exact commit.
2. Stage one job under `.agent-jobs/<JOB-ID>/`:
   - `job.json` — baseline, branch, scope, limits, validation profile and commit message;
   - `change.patch` — one text-only Git patch;
   - `READY` — empty activation marker, always written last.
3. Open a pull request from the internal `agent/**` branch to `main`.
4. GitHub Actions checks the exact pull-request head and verifies that the branch contains only the job envelope.
5. The patch is rejected when it exceeds the declared scope, size or line budgets, touches a default forbidden area, contains a binary, symlink or submodule, or fails `git apply --check`.
6. Build and tests run in a job with `contents: read` and no persisted repository credential.
7. The exact tested result is packaged as a patch plus manifest.
8. A separate short job with `contents: write` revalidates the result, commits it only to the pull request's `agent/**` branch, removes the temporary job envelope and appends `[agent-applied]` to the commit message.
9. A final job that does not check out or execute repository code writes a success status on the exact result commit SHA.
10. The same pull request now exposes only the tested product change for normal review and merge decision.

The workflow rejects forks and never pushes directly to `main`.

## Fixed validation profiles

- `repository`: repository governance validation only.
- `player-fast`: player build and mandatory non-browser checks through `make -C apps/player test-fast`.
- `player-targeted`: rebuilds the player, then runs an explicit non-empty list of Python tests under `apps/player/tests/`; Chromium is installed.
- `player-full`: full player test command through `make -C apps/player test`; Chromium is installed.

A job cannot supply arbitrary shell commands.

## Permanent default prohibitions

Remote agent patches cannot modify:

- `.github/**`;
- `.agent-jobs/**`;
- `.agent-runtime/**` or `.agent-result/**`;
- `governance/**`;
- `docs/architecture/**`;
- `work-packages/**`;
- `tools/agent_worktree.py`;
- Git metadata, symlinks, submodules or binary files.

Changes to these areas require the governed connector/PR path rather than the fast development lane.

## Job constraints

Every job requires:

- a full immutable `baseCommit` SHA;
- an exact `agent/**` branch name;
- non-empty, non-global `allowedPaths`;
- explicit `forbiddenPaths`;
- one fixed validation profile;
- file, line and patch-size budgets;
- a one-line commit message.

The hard ceilings are:

- 1,000,000 patch bytes;
- 80 changed files;
- 8,000 added plus deleted lines.

Jobs should normally use substantially smaller limits.

## Security boundary

The build/test job has read-only repository permissions and `actions/checkout` does not persist credentials. Patched code may execute during tests but does not receive the write token.

The write-token job does not execute the patched test suite. It only:

- downloads the tested result envelope;
- revalidates baseline, pull-request branch, digest, paths and limits using the protected runner script;
- stages the previously tested result;
- commits and pushes to the originating internal `agent/**` branch.

The final status job receives only `statuses: write`. It does not check out the repository or execute patched code. It posts the `Remote agent worktree / tested result` status to the exact SHA emitted by the result-commit job.

The branch is rejected when the pull request head repository is not the current repository. This limits the blast radius without pretending that CI execution of repository code is risk-free.

## Usage policy

Use this lane for bounded product, UX, test and documentation changes whose work package explicitly permits the affected paths.

Do not use it for:

- workflow or governance changes;
- architecture constitution changes;
- secret handling;
- repository policy changes;
- global identifier or storage migrations;
- backend, synchronization, tenancy or commerce activation;
- direct release publication;
- direct merging.

## Failure and recovery

A failed validation or test leaves the pull request branch with only its job envelope. Correct or replace the patch, then update `READY` last to start a new pull-request synchronization attempt.

A successful run removes the job envelope from the branch tree. The pull request, exact-result commit status and Actions evidence remain reviewable before any merge.
