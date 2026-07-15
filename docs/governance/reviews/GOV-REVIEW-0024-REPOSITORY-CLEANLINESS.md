# GOV-REVIEW-0024 — Repository cleanliness and canonical entry points

## Decision

**GO_WITH_CONDITIONS** for `GOV-WP-018`.

This is a documentation and governance cleanup only. It changes no Player source, test, build, contract, artifact, learner data or runtime behavior.

## Baseline reviewed

- Repository: `stefm78/learnit-platform`
- Exact base commit: `617bfaea591deb022e6019e100654fda85fe4472`
- Legacy product: RC718
- Human gate: RC719 `PASS_WITH_RESERVATIONS`
- Current direction: `ARC-WP-021` clean break
- Next mandatory gate: `ARC-WP-022`

## Evidence

The canonical governor state and restart checkpoint were current, but several high-visibility entry points still described earlier repository phases:

- the root README named RC715 as current and QA-WP-010 as the next step;
- architecture entry points said Player source was outside the repository and ARC-WP-000 remained blocked;
- the roadmap presented the superseded in-place migration sequence as current;
- contribution and governance files retained pre-import restrictions;
- the Player README described RC718 as an unpromoted candidate.

Exact findings and dispositions are recorded in `docs/evidence/governance/repository-cleanliness-audit.json`.

The repository validator rejects generated archives and credential-like files. `.gitignore` excludes generated builds, archives, caches, local data, secrets and agent runtime outputs. No open pull request existed at audit start.

## Claims

- Updating canonical entry points reduces restart ambiguity and prevents agents from repeating completed gates.
- Preserving historical references with an explicit non-canonical banner is safer than deleting evidence.
- The clean-generation roadmap can expose parallel AI lanes without authorizing implementation before shared contracts and scopes are frozen.

## Assumptions

- Historical work packages and reviews remain useful evidence and should not be reorganized merely for visual tidiness.
- Remote branch inventory is not asserted because the available branch-search result did not provide a reliable complete listing.

## Absence of evidence

There is no evidence in this cleanup that:

- any RC718 product file requires modification;
- any historical evidence should be deleted;
- new-generation implementation is ready;
- every remote historical branch has been removed.

## Adversarial review

The cleanup must fail if it:

- changes Player source, tests, build, contracts or artifact;
- hides the RC718 preservation boundary;
- presents historical reference-v1 as implemented current architecture;
- authorizes implementation of ARC-WP-022;
- reintroduces compatibility, overlay, dual-read or migration language;
- opens backend, account, synchronization, catalog, commerce, tenancy or marketplace work.

## Conditions

1. All changed files remain inside the exact `GOV-WP-018` scope.
2. Repository governance and PR-scope checks pass on the exact head.
3. Governor state remains unchanged because the effective product direction and next gate do not change.
4. RC718 source and promoted artifact remain untouched.
5. Historical references remain present and explicitly subordinate to current repository authority.
6. `ARC-WP-022` remains design and authorization only until separately accepted.

## Outcome

The canonical repository entry points may be aligned and merged after green checks.

Next mandatory gate remains `ARC-WP-022`.
