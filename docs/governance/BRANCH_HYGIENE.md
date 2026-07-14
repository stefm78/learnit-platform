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

The cleanup job has `contents: write` only because GitHub branch deletion requires repository-content authority. To prevent privileged execution of pull-request code, the job always checks out the trusted `main` branch and executes `tools/cleanup_branches.py` from `main`. It never checks out or runs a pull-request head.

The workflow has no pull-request, issue, release, deployment, secret, or merge authority.

## Automatic operation

The workflow runs:

- whenever a pull request is closed;
- when the workflow or cleanup engine is first added or changed on `main`;
- on explicit manual dispatch when an administrator needs another inventory pass.

Each run uploads `branch-hygiene-report.json` for 14 days. The report records every observed branch, its classification, the action taken, errors, and the `main` SHA before and after cleanup.

## Expected repository state

After completed pull requests are cleaned, the normal repository state is:

```text
main
+ branches for currently open pull requests only
+ explicitly retained unproven orphan branches, if any
```

Branch names are not durable evidence. Pull requests, commits, workflow results, work packages, and tags provide the durable record.
