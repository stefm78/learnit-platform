# Student V0.1 — FAN-IN A Input Freeze

Status: **FROZEN INPUT AUTHORITY FOR JOB 04 AFTER GOV-WP-039 MERGE**

Shared Wave 1 base:

`27846dff52fde9b83434bca29bd8732ea42834bf`

## Accepted exact role heads

- JOB 01 / PR #387 / issue #383: `d937592fb4d1e6dba6fcd02e290290f1a98cff71`
- JOB 02 / PR #388 / issue #384: `6c91346d07c934cfb2917799084647b13e4fb931`
- JOB 03 / PR #389 / issue #385: `a90ba85857dded331e5e3952c2f181cbe2e6d689`

These SHAs are immutable integration inputs. Branch names are locators only. If any PR head differs at JOB 04 execution time, fail closed and return to the Control Room.

## Frozen changed-path sets

### JOB 01

- `apps/learnit-next/src/core/activity_semantics.js`
- `apps/learnit-next/src/core/contract.js`
- `apps/learnit-next/src/core/import.js`
- `apps/learnit-next/src/core/progress.js`
- `apps/learnit-next/src/core/session.js`
- `apps/learnit-next/src/integration/atlas/activity_projection.js`
- `apps/learnit-next/src/integration/atlas/import_adapter.js`
- `apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`
- `apps/learnit-next/tests/student_v01_learning_runtime.py`
- `work-packages/ATLAS-WP-027.json`

### JOB 02

- `apps/learnit-next/src/atlas.css`
- `apps/learnit-next/src/ui/activity_presenters.js`
- `apps/learnit-next/src/ui/media.js`
- `apps/learnit-next/tests/browser_student_v01_activity_presentation.py`
- `apps/learnit-next/tests/student_v01_activity_presentation.py`
- `work-packages/ATLAS-WP-028.json`

### JOB 03

- `authoring/factory/tests/test_student_v01_v4.py`
- `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V4.md`
- `authoring/v2/atlas/pedagogical_quality.py`
- `authoring/v2/atlas/tests/test_pedagogical_quality.py`
- `authoring/v4/README.md`
- `authoring/v4/tests/test_validate_v4.py`
- `authoring/v4/validate_kit.py`
- `work-packages/ATLAS-WP-029.json`

Pairwise intersections of these three role path sets are empty. JOB 04 must re-prove that fact from Git before integration.

## Accepted role qualification state

JOB 01 R1:
- contract admission PASS;
- v2 regression PASS;
- v3 constructed PASS;
- v4 evaluated types PASS;
- lesson/flashcard non-scored semantics PASS;
- secret boundary PASS;
- media admission PASS;
- scope PASS;
- durability PASS;
- verdict `PASS_STUDENT_V01_JOB01_R1_READY_FOR_FANIN_A`.

JOB 02:
- qcm/fill regression PASS;
- lesson/flashcard PASS;
- matching/order/classify/constructed PASS;
- media PASS;
- secret boundary PASS;
- accessibility smoke PASS;
- scope PASS;
- verdict `PASS_STUDENT_V01_JOB02_PRESENTATION_READY_FOR_FANIN_A`.

JOB 03 R1:
- regression classification `MISCLASSIFIED_INFRA_FAILURE`;
- v4 validator PASS;
- new activity semantics PASS;
- pedagogical quality PASS;
- Factory PASS;
- v2 regression PASS;
- media validation PASS;
- scope PASS;
- generic Learn-it Next CI reservation `OUT_OF_SCOPE_ROUTER_FAILURE`;
- verdict `PASS_STUDENT_V01_JOB03_R1_READY_FOR_FANIN_A`.

## Integration-owned paths

JOB 04 may add the minimum wiring required for the combined candidate only in:

- `.github/workflows/learnit-next-ci.yml`
- `apps/learnit-next/build.py`
- `apps/learnit-next/source_manifest.json`
- `apps/learnit-next/tests/student_v01_fanin_a.py`
- `qualification/STUDENT_V01_FANIN_A_RESULT.md`

No other integration repair path is implicitly authorized.

## No-silent-repair rule

JOB 04 is an integrator, not a fourth implementation stream. If combination reveals a semantic conflict, a frozen-interface defect, or a role defect that cannot be solved by integration-only wiring, JOB 04 must return HOLD with the owning role identified. It must not redesign or repair that role in place.
