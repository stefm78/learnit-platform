# Architecture & Repository Governor review

## Review identity

- Review ID:
- Date:
- Repository:
- Base commit:
- Head commit or candidate:
- Work package or RC:
- Operational governor:
- Independent reviewers:

## 1. Scope reconstruction

- Intended change:
- Actual changed files:
- Declared non-goals:
- Overlapping active work packages:
- Scope deviations:

## 2. Evidence classification

### Evidence directly verified

- 

### Claims not independently reproduced

- 

### Assumptions used

- 

### Absence of proof

- 

## 3. Architecture frame

- Current phase from `governance/governor-state.json`:
- Authorized work matched:
- Held or prohibited work touched:
- Data owner affected:
- Contracts affected:
- Migrations affected:
- Dependency-direction impact:
- Canonical source-of-truth impact:

## 4. Counterexamples and adverse review

- Failure scenarios replayed:
- Conflicting-device or concurrency scenarios:
- Migration and rollback scenarios:
- Security or privacy negative tests:
- Provenance attacks:
- Human UX or learning gate required:

## 5. Constitution and exception review

- Architecture-constitution violations:
- Existing exceptions used:
- New exception requested:
- Exception owner and expiry:
- Removal gate:

## 6. Release and repository integrity

- Exact source identified:
- Build environment identified:
- Tests bound to artifact:
- Tested artifact equals proposed artifact:
- Undeclared files rejected:
- Rollback proven:
- Branch and review controls verified:

## 7. Risks

| Risk | Severity | Evidence | Required mitigation | Closure gate |
|---|---|---|---|---|
| | | | | |

## 8. Decision

Choose one:

- `GO`
- `GO_WITH_CONDITIONS`
- `HOLD`
- `NO_GO`

### Rationale


### Mandatory actions before merge or promotion

1. 

### Follow-up actions after merge

1. 

### Next gate


## 9. Governance-state impact

- [ ] No change to the canonical governor state is required.
- [ ] `governance/governor-state.json` is updated in this change.
- [ ] A new or changed exception is recorded.
- [ ] An active risk is closed or modified with evidence.

## 10. Sign-off

- Operational governor:
- Accountable owner decision, when required:
- Independent QA/security/learning/UX sign-off:
