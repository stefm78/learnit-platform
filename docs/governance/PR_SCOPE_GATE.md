# Pull-request scope gate

The stable check is:

```text
PR scope / gate
```

Every pull request targeting `main` must name exactly one work package in its body, for example:

```text
QA-WP-010
```

The gate loads the matching canonical file from `work-packages/` at the exact pull-request head and validates the complete `base...head` diff.

## Enforced controls

- exactly one canonical work-package identifier;
- canonical work-package file exists and contains the same identifier;
- non-empty, non-global `allowedPaths`;
- every added, modified, deleted and renamed path is inside `allowedPaths`;
- every path is outside `forbiddenPaths`;
- rename origins are checked as well as destinations;
- binary files, archives, executables, symbolic links and submodules are rejected;
- `.agent-runtime/`, `.agent-result/`, `.import/` and generated player output directories are rejected;
- ordinary pull requests continue to reject `.agent-jobs/` transport paths;
- player runtime changes cannot be mixed with workflow, governance, architecture, contract or platform changes;
- platform changes cannot be mixed with another sensitive domain.

The workflow uses read-only repository permissions and does not mutate the pull request.

## Strict Remote Agent transport exception

A Remote Agent pull request necessarily starts through `.agent-jobs/<JOB-ID>/READY`. The gate therefore recognizes one narrow transport form instead of rejecting the mechanism unconditionally.

The exception is accepted only when:

- exactly one job directory exists;
- it contains exactly `READY`, `change.patch` and `job.json`;
- `job.json` uses schema version 1, binds an `agent/**` branch, and names the pull-request base SHA exactly;
- `patchFile` references the patch in the same job directory;
- job `allowedPaths` are unique exact files, never globs;
- every job-allowed path is authorized by the canonical work package;
- the initial patch applies cleanly, contains text changes only, and every patch path satisfies both scopes;
- after the tested-result commit, every non-transport changed path remains inside the exact job paths and canonical work-package scope.

The report distinguishes `remote-agent-envelope` from `remote-agent-tested-result` and exposes the intended patch paths as the effective scoped files. The transport files are never treated as implementation scope.

This is not a branch exemption. A missing file, additional transport file, wrong base, scope escape, globbed path, archive, binary change or forbidden result path fails closed.

## Relationship with the Remote Agent Worktree

The Remote Agent Worktree validates and applies the job, runs the fixed test profile, packages the exact result, commits only validated result paths and attests the tested commit. The PR scope gate independently binds both the envelope and the final result to the canonical work package. Neither control substitutes for the other.

## Ruleset configuration

The target `main` ruleset remains:

- pull request required;
- direct pushes forbidden;
- `Repository governance` required;
- `PR scope / gate` required;
- `Player CI / gate` required for player changes;
- `Remote agent worktree / tested result` required for `agent/**` changes;
- bypass restricted and auditable.

The configured ruleset is not technically enforced on the current private personal-account repository; the documented exception remains active until the repository topology or plan changes.

## Failure recovery

A failed scope check must be fixed by one of these actions:

1. remove changes outside the intended work package;
2. split the pull request into separate work packages;
3. correct an invalid Remote Agent envelope or tested result;
4. govern and review a legitimate scope change in the canonical work-package file.

Do not broaden `allowedPaths` merely to silence the gate.
