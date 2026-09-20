# /AUDIT /SOLVE /BUILD — JOB 06 R1
## Student V0.1 — targeted showcase semantic repair after G3 HOLD

Repository: `stefm78/learnit-platform`  
Authority issue: `#421`  
Original JOB06: `#405 / PR #408`  
G3 HOLD authority: `#419 / PR #420`  
Work package: `ATLAS-WP-042`

Branch:

`student-v01/wave2-showcase-kit-r1`

Exact anchors:

- `JOB06_R1_BASE = 28d6e2968fcbe79d7225b2c29efda22317af09c8`
- `JOB06_ORIGINAL_RESULT = 8e0e3c43968cf0cf442e0e47b73bc38fc19ae565`
- `G3_SEMANTIC_REVIEW_SHA = 461b3a39440568d0f55c6a9b3d83f979e875bd78`
- `G3_EVIDENCE_HEAD = 38892dc2bb65afd3b3c74b06cb6ff56bad8a5627`
- exact source commit: `281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- exact source blob: `7f83784e8719917496a694b2ad170d724190fd04`
- exact source SHA256: `sha256:3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`
- original candidate Git blob: `1436cee30927ffeaea0ea9a0f27ef9f7b72f15ae`
- original candidate SHA256: `sha256:694f6713c2399e680f4748b925c9b293a9c9236cf25c593ce2f900ba5cec918b`
- unchanged learner-brief SHA256: `sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge or cherry-pick anything.

---

## 0. Role

You are the JOB06 author-repair worker.

G3 independently reviewed the exact original showcase and returned a semantic HOLD only on validation independence.

Your task is to make the **smallest source-preserving author-side repair** that resolves the two accepted G3 findings.

You are **not** the independent reviewer.

You must not create or claim a replacement semantic-review PASS. A changed kit requires a later clean-context G3 review.

---

## 1. Fresh authority rebind

Before mutation:

1. fresh-read active Human Control Plane HEAD and bind exact UCP/UAO/governance authority;
2. fresh-read repository `main`;
3. read issue #421 and `work-packages/ATLAS-WP-042.json`;
4. fresh-read original JOB06 PR #408 and verify:
   - DRAFT/open/unmerged;
   - evidence head exactly `28d6e2968fcbe79d7225b2c29efda22317af09c8`;
5. fresh-read G3 PR #420 and verify:
   - DRAFT/open/unmerged;
   - semantic-review commit exactly `461b3a39440568d0f55c6a9b3d83f979e875bd78`;
   - evidence head exactly `38892dc2bb65afd3b3c74b06cb6ff56bad8a5627`;
6. verify this repair branch descends exactly from `JOB06_R1_BASE`;
7. re-read the exact G3 semantic review:
   `qualification/STUDENT_V01_G3_JOB06_SEMANTIC_REVIEW.json`
   from exact `G3_SEMANTIC_REVIEW_SHA`;
8. verify the exact original source and candidate blob identities before editing.

If any authority drifts, stop:

`HOLD_STUDENT_V01_JOB06_R1_AUTHORITY_DRIFT`

---

## 2. Accepted defects — do not debate them

Treat these G3 findings as accepted repair requirements.

### G3-SEM-001

Original validation:

`$.courses[0].activities[5]`

asks for:

`5 − 2i -> 5 + 2i`

but the exact same mapping is already learner-visible in earlier matching:

`$.courses[0].activities[2]`

### G3-SEM-002

Original validation:

`$.courses[0].activities[9]`

asks for:

`|−5 + 12i| = 13`

but the exact value is already learner-visible in earlier matching:

`$.courses[0].activities[8]`

The G3 review passed:

- source fidelity;
- answer correctness;
- ambiguity;
- objective coverage;
- learner fit.

Do not use this job to rewrite those dimensions gratuitously.

---

## 3. /solve — preferred minimal repair

Challenge this plan, but use it unless deterministic evidence proves it cannot satisfy the frozen V4/quality authorities.

### Conjugate matching

In original activity index 2, remove only the pair exposing the later validation answer:

- left item:
  - `itemId = 356f1c65-15dd-4abe-b3b0-39ae1c899356`
  - label `5 − 2i`
- right item:
  - `itemId = 8e33618e-5f8f-409d-8e8a-435a7c39ef8b`
  - label `5 + 2i`
- its matching solution entry.

Retain the two source-supported pairs:

- `2 + 3i -> 2 − 3i`
- `−1 − 4i -> −1 + 4i`

Do **not** alter the later validation activity at index 5.

### Module matching

In original activity index 8, remove only the pair exposing the later validation answer:

- left item:
  - `itemId = 839fe45f-b8c9-40a3-9dd1-4de798ecb08f`
  - label `|−5 + 12i|`
- right item:
  - `itemId = b85b6ad3-6305-4518-a9cd-b987c2ce2751`
  - label `13`
- its matching solution entry.

Retain the two source-supported pairs:

- `|3 + 4i| -> 5`
- `distance to origin of affix 8 − 15i -> 17`

Do **not** alter the later validation activity at index 9.

### Why this is preferred

It:
- removes the exact answer leakage;
- preserves source-supported validation instances;
- invents no new mathematical example;
- retains valid matching semantics with two pairs;
- preserves course order, activity count and 42-minute declared budget;
- avoids changing unrelated learner content.

If this exact minimal plan passes canonical validation and quality, any broader semantic rewrite is forbidden as unnecessary.

---

## 4. Identity/revision hygiene

Preserve all lineage IDs.

For each modified matching activity:

- allocate a fresh `activityRevisionId`;
- recompute its `activityRevisionDigest`.

Keep every **unmodified** activity object semantically unchanged and keep its existing revision ID/digest.

Because the course content changed:

- allocate a fresh `courseRevisionId`;
- recompute `courseRevisionDigest`.

Because package content changed:

- allocate a fresh `packageRevisionId`;
- recompute `packageRevisionDigest`.

Use repository canonical digest tooling/logic only.

Do not hand-invent digests.

Record exact before/after identities.

---

## 5. Source and learner brief are immutable

The source remains exactly:

`authoring/v2/atlas/nombres_complexes_atlas.json@281dc7470d51682c5e6d79d3fff54c46cfbced3b`

The learner brief remains exactly the existing JOB06:

`showcase/student-v0.1/nombres-complexes/LEARNER_BRIEF.json`

Do not edit either.

Do not add a new source.

Do not invent a replacement practice/validation example.

Source fidelity outranks preserving an old quality band.

---

## 6. Update author-side evidence only where invalidated

The repaired candidate invalidates some author-side evidence.

Update only these allowed files as needed:

- `nombres_complexes_student_v01_v4.json`
- `AUTHOR_AUDIT.md`
- `PROVENANCE_MAP.json`
- `V4_VALIDATION_REPORT.json`
- `PEDAGOGICAL_QUALITY_REPORT.json`
- `FACTORY_CONTEXT.json`
- `FACTORY_REVIEW_REQUEST.md`

### Provenance

For each repaired matching activity:

- remove provenance references that no longer support learner-visible content;
- retain only exact source references genuinely used by the repaired activity.

Do not weaken source traceability.

### AUTHOR_AUDIT

Record:
- G3 finding IDs;
- exact removed pairs;
- exact unchanged validation activities;
- exact revision changes;
- unchanged source/brief;
- canonical/quality results;
- statement that independent semantic review remains pending.

Do not claim semantic PASS.

---

## 7. Canonical validation

Run canonical V4 validation on the exact repaired kit.

Require:

`V4_CANONICAL: PASS`

Independently recompute and verify:

- both modified activity digests;
- all untouched activity digests remain valid;
- course digest;
- package digest;
- ID uniqueness;
- matching coverage and one-to-one semantics;
- at least two items per matching side;
- no unknown references;
- lesson/flashcard non-scored boundary unchanged.

Store/update:

`showcase/student-v0.1/nombres-complexes/V4_VALIDATION_REPORT.json`

If the preferred repair cannot pass canonical validation without broader semantic changes, stop:

`HOLD_STUDENT_V01_JOB06_R1_MINIMAL_REPAIR_NOT_CANONICAL`

Do not improvise a larger repair silently.

---

## 8. Pedagogical quality

Run the frozen Student V0.1 V4 quality rules against the exact repaired kit.

Require at least:

`STRONG`

Prefer `EXCELLENT_BY_PROFILE` if it remains naturally true.

If removing the leaked pairs lowers the band but the kit remains canonical, source-faithful and at least STRONG, accept the honest band.

Do not invent content merely to recover `EXCELLENT_BY_PROFILE`.

Store/update:

`showcase/student-v0.1/nombres-complexes/PEDAGOGICAL_QUALITY_REPORT.json`

---

## 9. Explicit contamination audit

Before author-side PASS, scan the complete learner-visible sequence **before** each validation.

### Validation at activity 5

Require that no prior learner-visible content gives the exact mapping:

`5 − 2i -> 5 + 2i`

A generic conjugate rule or mention of `5 − 2i` without revealing its answer is allowed.

### Validation at activity 9

Require that no prior learner-visible content gives the exact result:

`|−5 + 12i| = 13`

A generic module formula is allowed.

Record this audit deterministically in `AUTHOR_AUDIT.md`.

Do not relabel a revealed answer as "practice" to bypass the defect.

---

## 10. Fresh Factory context

Because kit bytes changed, the old G3 semantic review and old Factory context are stale.

Generate a fresh Factory context from exact:

- repaired kit;
- unchanged learner brief;
- unchanged source.

Use canonical repository command/logic:

```bash
python -B authoring/factory/factory_gate.py context \
  --kit <repaired-kit> \
  --brief showcase/student-v0.1/nombres-complexes/LEARNER_BRIEF.json \
  --source nombres-complexes-atlas-v2=<exact-source> \
  > showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT.json
```

Require:

- new `kitSha256`;
- new `contextDigest`;
- same `briefSha256`;
- same `sourceSetDigest`;
- same exact source byte/hash binding.

Update:

`FACTORY_REVIEW_REQUEST.md`

with the new exact four-hash target.

It must explicitly state:

`SEMANTIC_REVIEW: PENDING_INDEPENDENT_G3_R1`

and require a clean reviewer context.

---

## 11. Do not run or fabricate the final semantic/Factory gate

This worker is the author/repair context.

Therefore:

- do not create `learnit.atlas.semantic_review.v1`;
- do not mark semantic review PASS;
- do not run a final `factory_gate.py gate` with a synthetic/self-authored review;
- do not reuse G3's old semantic review against new kit bytes.

The later G3 R1 reviewer owns independent semantic review and final Factory gate.

A changed kit necessarily invalidates the old semantic-review target binding.

---

## 12. Regression and invariance checks

Prove:

- source bytes unchanged;
- learner brief bytes unchanged;
- activity count unchanged;
- activity type/order unchanged;
- estimated course duration remains 42;
- objectives unchanged;
- validation activities at original indices 5 and 9 are semantically unchanged;
- unrelated activities are semantically unchanged;
- no assets introduced;
- no product/runtime/UI/pilot/QA/schema/authoring implementation changed.

Use exact structural diff tooling where practical, not only visual inspection.

---

## 13. Repository governance and scope

No central CI/workflow change is authorized.

Repository governance must PASS on the exact repair branch result.

Exact `JOB06_R1_BASE..RESULT_SHA` may change only:

- `work-packages/ATLAS-WP-042.json`
- `docs/programs/student-v0.1/jobs/JOB_06_R1_SHOWCASE_SEMANTIC_REPAIR.md`
- the seven allowed JOB06 showcase/evidence files listed above.

Then evidence-only qualification may add only:

- `qualification/STUDENT_V01_JOB06_R1_SHOWCASE_REPAIR_RESULT.md`

Any product, source, learner-brief, schema, authoring implementation, QA, pilot, workflow or governance mutation is scope FAIL.

---

## 14. RESULT_SHA and EVIDENCE_HEAD

Use:

- `RESULT_SHA`: exact repaired author-side candidate + regenerated author-side evidence, before qualification narrative;
- `EVIDENCE_HEAD`: later commit adding only `qualification/STUDENT_V01_JOB06_R1_SHOWCASE_REPAIR_RESULT.md`.

The qualification must record:

- fresh HCP binding;
- exact authority anchors;
- accepted G3 findings;
- exact before/after removed pairs;
- revision-ID/digest changes;
- contamination audit;
- canonical validation result;
- quality result/band;
- repaired kit SHA256;
- new Factory context target hashes;
- statement that semantic review is pending;
- repository-governance run;
- exact changed paths;
- rollback.

---

## 15. PASS gate

Author-side repair PASS requires all:

- G3 findings bound exactly;
- G3-SEM-001 exact prior-answer exposure removed;
- G3-SEM-002 exact prior-answer exposure removed;
- both validation activities unchanged;
- both matching activities remain valid with >=2 pairs;
- no new source example invented;
- source unchanged;
- learner brief unchanged;
- activity order/count/duration/objectives unchanged;
- revision/digest hygiene PASS;
- provenance exact;
- V4 canonical PASS;
- pedagogical quality >= STRONG;
- full prior-to-validation contamination audit PASS;
- fresh Factory context PASS;
- review request rebound to new exact target;
- semantic review explicitly pending;
- Repository governance PASS;
- scope PASS.

PASS authorizes only a new independent G3 R1 review.

---

## 16. Final result block

Return exactly:

```text
STUDENT_V01_JOB06_R1_RESULT
JOB06_R1_BASE: 28d6e2968fcbe79d7225b2c29efda22317af09c8
JOB06_ORIGINAL_RESULT: 8e0e3c43968cf0cf442e0e47b73bc38fc19ae565
G3_SEMANTIC_REVIEW_SHA: 461b3a39440568d0f55c6a9b3d83f979e875bd78
RESULT_SHA: <exact repaired author-side result>
EVIDENCE_HEAD: <final evidence-only head>
ISSUE: 421
PR: <authoritative repair pr>
G3_SEM_001_REMOVED: PASS|FAIL
G3_SEM_002_REMOVED: PASS|FAIL
VALIDATION_ACTIVITIES_UNCHANGED: PASS|FAIL
MATCHING_MINIMUMS: PASS|FAIL
NO_NEW_SOURCE_CONTENT: PASS|FAIL
SOURCE_UNCHANGED: PASS|FAIL
LEARNER_BRIEF_UNCHANGED: PASS|FAIL
JOURNEY_STRUCTURE_UNCHANGED: PASS|FAIL
REVISION_DIGEST_HYGIENE: PASS|FAIL
SOURCE_TRACEABILITY: PASS|FAIL
V4_CANONICAL: PASS|FAIL
PEDAGOGICAL_QUALITY: EXCELLENT_BY_PROFILE|STRONG|COMPLETE|WEAK|FAIL
VALIDATION_CONTAMINATION_AUDIT: PASS|FAIL
REPAIRED_KIT_SHA256: <sha256>
FACTORY_CONTEXT_DIGEST: <sha256>
FACTORY_CONTEXT_REBOUND: PASS|FAIL
SEMANTIC_REVIEW: PENDING_INDEPENDENT_G3_R1
REPOSITORY_GOVERNANCE: PASS|FAIL
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed final verdicts:

- `PASS_STUDENT_V01_JOB06_R1_SHOWCASE_REPAIRED_FOR_G3_R1`
- `HOLD_STUDENT_V01_JOB06_R1_AUTHORITY_DRIFT`
- `HOLD_STUDENT_V01_JOB06_R1_MINIMAL_REPAIR_NOT_CANONICAL`
- `HOLD_STUDENT_V01_JOB06_R1_QUALITY_NEEDS_REWORK`
- `HOLD_STUDENT_V01_JOB06_R1_REPAIR_NEEDS_REWORK`
- `FAIL_STUDENT_V01_JOB06_R1_SCOPE_VIOLATION`
