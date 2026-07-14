# Branch hygiene

`main` is the only permanent development branch.

The `Branch hygiene` workflow removes branches only when deletion is supported by repository evidence:

- the branch is the same-repository head of a closed pull request; or
- the branch has no commits absent from `main` and is therefore fully merged.

The workflow always retains:

- `main`;
- any branch backing an open pull request;
- any unmerged branch with no closed-pull-request evidence;
- tags.

Unproven branches are reported as `unproven-orphan` rather than deleted.

## Security boundary

The cleanup job has `contents: write` only because GitHub branch deletion requires repository-content authority. It has `pull-requests: read` only to distinguish open, closed, and external pull-request heads. It has `issues: write` only to publish the initial or manually requested cleanup summary on governance issue #27.

To prevent privileged execution of pull-request code, the job always checks out the trusted `main` branch and executes `tools/cleanup_branches.py` from `main`. It never checks out or runs a pull-request head.

The workflow has no release, deployment, secret, tag, history-rewrite, or merge authority. Routine cleanup after PR closure does not create issue comments.

## Automatic operation

The workflow runs:

- whenever a pull request is closed;
- when the workflow or cleanup engine is added or changed on `main`;
- on explicit manual dispatch when an administrator needs another inventory pass.

Each run uploads `branch-hygiene-report.json` for 14 days. The report records every observed branch, its classification, the action taken, errors, and the `main` SHA before and after cleanup.

## Accepted initial cleanup

The accepted inventory run `29324362246` observed only three branches:

- `main`;
- `agent/smoke-remote-worktree`;
- `agent/smoke-remote-worktree-v2`.

The two smoke branches were deliberately retained as unproven orphans on the first pass. Their content was reviewed, closure-only PRs #37 and #38 were created and closed without merge, and the automatic policy then deleted both branches. Their refs were independently verified absent.

The normal repository state is therefore:

```text
main
+ branches for currently open pull requests only
+ explicitly retained unproven orphan branches, if any
```

Branch names are not durable evidence. Pull requests, commits, workflow results, work packages, and tags provide the durable record.
