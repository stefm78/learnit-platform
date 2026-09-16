# Student V0.1 — JOB 04 R1 FAN-IN A qualification

## Authority and binding

- Authority issue: `#391`
- R1 continuation issue: `#394`
- Work package: `ATLAS-WP-030`
- Integration PR: `#393`
- Integration branch: `student-v01/fanin-a`
- `FANIN_A_BASE`: `21d25c36aec6c04fdfe8126c95e71cbf80771a1b`
- `START_SHA`: `f8fe068bf056006ac63e6ae01bd59793442c7172`
- `WAVE1_COMMON_BASE`: `27846dff52fde9b83434bca29bd8732ea42834bf`
- JOB01 / PR #387: `d937592fb4d1e6dba6fcd02e290290f1a98cff71`
- JOB02 / PR #388: `6c91346d07c934cfb2917799084647b13e4fb931`
- JOB03 / PR #389: `a90ba85857dded331e5e3952c2f181cbe2e6d689`
- Qualified integrated candidate (`RESULT_SHA`): `f4636e06279481b62ffd676ba70313c71283baeb`

The active Human Control Plane was revalidated before the final evidence mutation. `main` remained exactly `21d25c36aec6c04fdfe8126c95e71cbf80771a1b`; no rebase or moving-main substitution was performed.

## Exact child identity proof

| Child | PR | Live head | Unmerged | Merge-base with common base | Frozen changed-path set | Result |
| --- | ---: | --- | --- | --- | --- | --- |
| JOB01 | #387 | `d937592fb4d1e6dba6fcd02e290290f1a98cff71` | yes | `27846dff52fde9b83434bca29bd8732ea42834bf` | exact, 10 paths | PASS |
| JOB02 | #388 | `6c91346d07c934cfb2917799084647b13e4fb931` | yes | `27846dff52fde9b83434bca29bd8732ea42834bf` | exact, 6 paths | PASS |
| JOB03 | #389 | `a90ba85857dded331e5e3952c2f181cbe2e6d689` | yes | `27846dff52fde9b83434bca29bd8732ea42834bf` | exact, 8 paths | PASS |

Pairwise changed-path intersections are empty. The child deltas were applied in JOB01 → JOB02 → JOB03 order using the exact frozen Git blobs; no child PR was merged to `main`, no role file was repaired in FAN-IN A, and no application conflict occurred.

`PATH_INDEPENDENCE: PASS`

`CHILD_DELTA_IDENTITY: PASS`

## Exact candidate path set

Relative to `FANIN_A_BASE`, the qualified candidate `f4636e06279481b62ffd676ba70313c71283baeb` changes exactly these 28 paths:

1. `.github/workflows/learnit-next-ci.yml`
2. `apps/learnit-next/source_manifest.json`
3. `apps/learnit-next/src/atlas.css`
4. `apps/learnit-next/src/core/activity_semantics.js`
5. `apps/learnit-next/src/core/contract.js`
6. `apps/learnit-next/src/core/import.js`
7. `apps/learnit-next/src/core/progress.js`
8. `apps/learnit-next/src/core/session.js`
9. `apps/learnit-next/src/integration/atlas/activity_projection.js`
10. `apps/learnit-next/src/integration/atlas/import_adapter.js`
11. `apps/learnit-next/src/ui/activity_presenters.js`
12. `apps/learnit-next/src/ui/media.js`
13. `apps/learnit-next/tests/browser_student_v01_activity_presentation.py`
14. `apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`
15. `apps/learnit-next/tests/student_v01_activity_presentation.py`
16. `apps/learnit-next/tests/student_v01_fanin_a.py`
17. `apps/learnit-next/tests/student_v01_learning_runtime.py`
18. `authoring/factory/tests/test_student_v01_v4.py`
19. `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V4.md`
20. `authoring/v2/atlas/pedagogical_quality.py`
21. `authoring/v2/atlas/tests/test_pedagogical_quality.py`
22. `authoring/v4/README.md`
23. `authoring/v4/tests/test_validate_v4.py`
24. `authoring/v4/validate_kit.py`
25. `work-packages/ATLAS-WP-027.json`
26. `work-packages/ATLAS-WP-028.json`
27. `work-packages/ATLAS-WP-029.json`
28. `work-packages/ATLAS-WP-030.json`

The result evidence commit adds only this authorized path: `qualification/STUDENT_V01_FANIN_A_RESULT.md`.

Integration-owned executable wiring used only:

- `.github/workflows/learnit-next-ci.yml`
- `apps/learnit-next/source_manifest.json`
- `apps/learnit-next/tests/student_v01_fanin_a.py`
- `qualification/STUDENT_V01_FANIN_A_RESULT.md`

`apps/learnit-next/build.py` was not modified.

`SCOPE: PASS`

## Integration wiring evidence

The deterministic source manifest was rebound to the exact integrated source blobs and expanded from 57 to 61 declared working files. Its canonical self fingerprint is `0ca4473d88ddf4218d6d9fc159df62d6c34a03ff51f4f02d73fc6994bf91849f`.

The exact Student V0.1 branch route was added to `.github/workflows/learnit-next-ci.yml` with 55 additions and zero deletions; historical routes were left unchanged.

## Qualification commands and results on `RESULT_SHA`

### Deterministic build

Command:

`python -B apps/learnit-next/build.py`

Result: PASS

- artifact: `apps/learnit-next/dist/learnit-next.html`
- bytes: `474462`
- SHA-256: `af0798fa94604068e15bc5261e8c96b43be7292c6c56e33c1bc30f46e06a966f`

### JOB01 runtime / contract qualification

Command:

`python -B apps/learnit-next/tests/student_v01_learning_runtime.py -v`

Result: PASS — `STUDENT_V01_LEARNING_RUNTIME_PASS 74/74`.

This unchanged role suite covers the frozen v2 regression, v3 constructed regression, v4 admission/runtime semantics, malformed/duplicate/omitted/extra/unknown matching/order/classify IDs, non-scored lesson/flashcard behavior, learner-safe projection, and media/runtime fail-closed checks.

`ROLE_TESTS: PASS`

`V2_REGRESSION: PASS`

`V3_REGRESSION: PASS`

### JOB02 presentation/UI qualification

Commands:

- `python -B apps/learnit-next/tests/student_v01_activity_presentation.py`
- `python -B apps/learnit-next/tests/browser_student_v01_activity_presentation.py`

Result: PASS.

Observed markers:

- `STUDENT_V01_ACTIVITY_PRESENTATION_STATIC_PASS`
- `SECRET_BOUNDARY_STATIC_PASS`
- `MEDIA_FAIL_CLOSED_STATIC_PASS`
- `ACCESSIBLE_NON_DRAG_CONTROLS_STATIC_PASS`
- `QCM_FILL_BROWSER_PASS`
- `LESSON_FLASHCARD_BROWSER_PASS`
- `MATCHING_ORDER_CLASSIFY_CONSTRUCTED_BROWSER_PASS`
- `MEDIA_SECRET_ACCESSIBILITY_BROWSER_PASS`
- `STUDENT_V01_ACTIVITY_PRESENTATION_BROWSER_PASS`

`NON_SCORED_LESSON_FLASHCARD: PASS`

`SECRET_BOUNDARY: PASS`

### JOB03 authoring / quality / Factory qualification

Commands:

- `python -B authoring/v4/tests/test_validate_v4.py -v`
- `python -B authoring/v2/atlas/tests/test_pedagogical_quality.py -v`
- `python -B authoring/factory/tests/test_student_v01_v4.py -v`

Results:

- v4 validator: 8/8 tests PASS
- pedagogical quality: 6/6 tests PASS
- Factory v4: 3/3 tests PASS

The representative v4 authoring fixture is accepted by the frozen JOB03 validator/quality layer.

## Cross-role end-to-end result

Command:

`python -B apps/learnit-next/tests/student_v01_fanin_a.py`

Result: FAIL at the first JOB03 → JOB01 admission boundary.

The deterministic JOB03 representative package contains the embedded SVG:

`<svg xmlns="http://www.w3.org/2000/svg" ...>`

JOB03 authoring accepts that package, including the media asset. JOB01 runtime admission rejects the same unchanged package with:

`[{"code":"unsafe_svg","path":"$.assets[0].data","message":"SVG active/external URI is forbidden"}]`

The runtime `contract.js` media guard matches URI schemes across the raw SVG string, so the standard XML namespace declaration containing `http:` is classified as an active/external URI. The authoring validator's SVG policy treats the namespace declaration as metadata and separately rejects active/href/remote media references.

This is an observed semantic incompatibility between the frozen JOB03 authoring output and the frozen JOB01 runtime admission. It is not child SHA drift, a path conflict, source-manifest drift, or a CI-router failure. Under JOB04's no-silent-repair rule, FAN-IN A must not alter either frozen role implementation to resolve it.

Primary rework boundary: JOB01 runtime media admission (`apps/learnit-next/src/core/contract.js`), followed by requalification against the frozen JOB03 authoring fixture. No role repair is included in this FAN-IN candidate.

`V4_END_TO_END: FAIL`

`MEDIA: FAIL`

`AUTHORING_TO_LEARNER: FAIL`

## CI / governance / scope evidence

On exact candidate head `f4636e06279481b62ffd676ba70313c71283baeb`:

- Repository governance: PASS — workflow run `35064046111`
- PR scope: PASS — workflow run `35064046068`
- Learn-it Next exact routed integration CI: FAIL — workflow run `35064046073`
- CI failure is the cross-role SVG admission mismatch documented above; all preceding JOB04 build and role suites in that run passed.
- `main` remained exactly `21d25c36aec6c04fdfe8126c95e71cbf80771a1b` through final qualification.
- PR #387 remains open/unmerged at the exact JOB01 frozen SHA.
- PR #388 remains open/unmerged at the exact JOB02 frozen SHA.
- PR #389 remains open/unmerged at the exact JOB03 frozen SHA.

`REPOSITORY_GOVERNANCE: PASS`

`PR_SCOPE: PASS`

`INTEGRATION_CI: FAIL`

## Reservation and rollback

Reservation: do not launch Wave 2, merge PR #393, authorize student use, or promote Student V0.1 from this candidate. A role-owned correction must reconcile runtime inline-SVG namespace handling with the frozen authoring media semantics and then repeat FAN-IN qualification on a newly frozen accepted child head.

Rollback anchor for the bounded R1 continuation is `f8fe068bf056006ac63e6ae01bd59793442c7172`. The exact child PRs remain unmerged and therefore independently recoverable from their frozen SHAs.

## Machine-readable R1 result

```text
STUDENT_V01_JOB04_R1_FANIN_A_RESULT
FANIN_A_BASE: 21d25c36aec6c04fdfe8126c95e71cbf80771a1b
START_SHA: f8fe068bf056006ac63e6ae01bd59793442c7172
WAVE1_COMMON_BASE: 27846dff52fde9b83434bca29bd8732ea42834bf
JOB01_SHA: d937592fb4d1e6dba6fcd02e290290f1a98cff71
JOB02_SHA: 6c91346d07c934cfb2917799084647b13e4fb931
JOB03_SHA: a90ba85857dded331e5e3952c2f181cbe2e6d689
RESULT_SHA: f4636e06279481b62ffd676ba70313c71283baeb
ISSUE: 391
R1_ISSUE: 394
PR: 393
PATH_INDEPENDENCE: PASS
CHILD_DELTA_IDENTITY: PASS
ROLE_TESTS: PASS
V2_REGRESSION: PASS
V3_REGRESSION: PASS
V4_END_TO_END: FAIL
NON_SCORED_LESSON_FLASHCARD: PASS
SECRET_BOUNDARY: PASS
MEDIA: FAIL
AUTHORING_TO_LEARNER: FAIL
REPOSITORY_GOVERNANCE: PASS
PR_SCOPE: PASS
INTEGRATION_CI: FAIL
SCOPE: PASS
FINAL_VERDICT: HOLD_STUDENT_V01_FANIN_A_CONFLICT_REQUIRES_ROLE_REWORK
```
