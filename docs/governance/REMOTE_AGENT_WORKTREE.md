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
3. GitHub Actions checks the exact baseline and verifies that the branch contains only the job envelope.
4. The patch is rejected when it exceeds the declared scope, size or line budgets, touches a default forbidden area, contains a binary, symlink or submodule, or fails `git apply --check`.
5. Build and tests run in a job with `contents: read` and no persisted repository credential.
6. The exact tested result is packaged as a patch plus manifest.
7. A separate short job with `contents: write` revalidates the result, commits it only to the same `agent/**` branch, removes the temporary job envelope and appends `[agent-applied]` to the commit message.
8. A normal pull request, CI review and merge decision follow.

The workflow never pushes directly to `main`.

## Fixed validation profiles

- `repository`: repository governance validation only.
- `player-fast`: player build and mandatory non-browser checks through `make -C apps/player test-fast`.
- `player-targeted`: an explicit non-empty list of Python tests under `apps/player/tests/`; Chromium is installed.
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
- revalidates baseline, branch, digest, paths and limits using the protected runner script;
- stages the previously tested result;
- commits and pushes to the originating `agent/**` branch.

This limits the blast radius without pretending that CI execution of repository code is risk-free.

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

A failed validation or test leaves the branch with only its job envelope. Correct or replace the patch, remove the previous `READY` marker if necessary, and write `READY` last to start a new attempt.

A successful run removes the job envelope from the branch tree. The resulting commit and Actions evidence remain reviewable before any merge.
