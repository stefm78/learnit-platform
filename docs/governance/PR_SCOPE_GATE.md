# Pull-request scope gate

The stable check is:

```text
PR scope / gate
```

Every pull request targeting `main` must name exactly one work package in its body, for example:

```text
QA-WP-010
```

The gate loads `work-packages/QA-WP-010.json` from the exact pull-request head and validates the complete `base...head` diff.

## Enforced controls

- exactly one canonical work-package identifier;
- canonical work-package file exists and contains the same identifier;
- non-empty, non-global `allowedPaths`;
- every added, modified, deleted and renamed path is inside `allowedPaths`;
- every path is outside `forbiddenPaths`;
- rename origins are checked as well as destinations;
- binary files, archives, executables, symbolic links and submodules are rejected;
- `.agent-jobs/`, `.agent-runtime/`, `.agent-result/`, `.import/` and generated player output directories are rejected;
- player runtime changes cannot be mixed with workflow, governance, architecture, contract or platform changes;
- platform changes cannot be mixed with another sensitive domain.

The workflow uses read-only repository permissions and does not mutate the pull request.

## Relationship with the Remote Agent Worktree

The Remote Agent Worktree validates its job envelope before application and removes `.agent-jobs/` before producing the final result commit. The PR scope gate validates the final branch diff. Both controls are complementary.

## Ruleset configuration

Repository source can produce the checks but cannot, with the currently available connector, configure GitHub administrative rulesets. The target `main` ruleset remains:

- pull request required;
- direct pushes forbidden;
- `Repository governance` required;
- `PR scope / gate` required;
- `Player CI / gate` required for player changes;
- `Remote agent worktree / tested result` required for `agent/**` changes;
- bypass restricted and auditable.

Issue #27 tracks this administrative gate.

## Failure recovery

A failed scope check must be fixed by one of these actions:

1. remove changes that are outside the intended work package;
2. split the pull request into separate work packages;
3. govern and review a legitimate scope change in the canonical work-package file.

Do not broaden `allowedPaths` merely to silence the gate.
