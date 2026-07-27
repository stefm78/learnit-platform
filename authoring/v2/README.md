# Learn-it v2 authoring foundation

This directory is the bounded `DEV-AUTHORING` surface for `PROG-WP-001`, Wave A. It uses the frozen `learnit.kit.v2` contract and does not modify `contracts/learnit-kit-v2.schema.json`.

## Scope

- activity families remain `qcm` and `fill`;
- only existing authoring fields are used to classify the learning loop:
  - `objectiveIds`;
  - `learningPhase`;
  - `assessmentRole`;
- the canonical kits are representative fixtures, not complete curricula;
- no runtime, learner-state, RC718 storage, import or accessibility code is changed here;
- no mastery, retention or certification claim is produced.

## Objective → training → validation rule

With `--foundation-profile`, each course must expose at least one representative objective with an ordered, distinct pair:

1. **Training activity**
   - references the objective through `objectiveIds`;
   - has `assessmentRole: "practice"`;
   - does not have `learningPhase: "validation"`.
2. **Validation activity**
   - references the same objective through `objectiveIds`;
   - has `learningPhase: "validation"`;
   - has `assessmentRole: "validation"`.
3. **Distinct and ordered**
   - the training and validation are different activities;
   - at least one training activity appears before the validation activity in the authored `activities` array.

The rule deliberately requires one representative objective rather than asserting that every objective is fully covered. The JSON report lists the coverage of every objective so an author can see which objectives have training only, validation only, or a complete ordered loop.

## Author diagnostics

Every blocking diagnostic identifies:

- a JSON path;
- the cause;
- the concerned value serialized after `value=`.

Example:

```text
$.courses[0].objectives[1].objectiveId: objective has no validation activity with learningPhase='validation' and assessmentRole='validation'; value={"objectiveId":"...","trainingActivityPaths":["$.courses[0].activities[2]"],"validationActivityPaths":[]}
```

The machine-readable report adds `objectiveLoops[]` for each file. Each record contains:

- `objectivePath` and `objectiveId`;
- `trainingActivities[]`;
- `validationActivities[]`;
- `orderedDistinctPairs[]`;
- `complete`.

## Structural and semantic validation

The validator also preserves the previous authoring checks:

- strict UTF-8 JSON parsing with duplicate-key rejection;
- Draft 2020-12 validation against the frozen schema;
- global canonical-ID uniqueness within each package;
- objective-reference integrity;
- QCM choice uniqueness and `correctChoiceId` integrity;
- fill slot/token uniqueness, complete slot coverage and `maxUses` enforcement;
- validation phase/role consistency;
- foundation minima for objectives, activities, QCM, fill, application/transfer and validation;
- canonical JSON and inside-out SHA-256 revision digests;
- cross-file rejection of one revision ID associated with different content or digest.

## Persistent identity and digest rules

Lineage IDs remain stable for the conceptual object. A semantic authored change requires a new revision ID and digest for the changed activity, then for its containing course and package.

Canonical JSON uses UTF-8, NFC normalization, lexicographically sorted object keys, authored array order, no insignificant whitespace and no floating-point values. The digest field of the object being digested is omitted. Digests are rendered as `sha256:<64 lowercase hex>`.

`--write-digests` only fills missing or all-zero digests. It refuses to rewrite a non-zero mismatch, because that could silently preserve a stale revision ID after a semantic change.

## Validation commands

From the repository root:

```bash
python -m py_compile \
  authoring/v2/validate_kit.py \
  apps/learnit-next/tests/dev_learning_loop_v2_authoring.py

python authoring/v2/validate_kit.py \
  --schema contracts/learnit-kit-v2.schema.json \
  --foundation-profile \
  --format json \
  authoring/v2/golden/nombres_complexes.json \
  authoring/v2/golden/signaux_electriques.json

python apps/learnit-next/tests/dev_learning_loop_v2_authoring.py -v
```

The fixed remote profile is `learnit-next-authoring`.

## Canonical kit changes for Wave A

### Nombres complexes

Representative objective:

> Relier une affixe à sa représentation géométrique, son module et un argument.

- training activities: module/point-image application and polar-form transfer;
- distinct validation: determine the affix and module of `M(−3,4)`;
- the validation now references only the representative geometric objective;
- package, course and changed validation activity use new revision IDs and recalculated digests.

### Signaux électriques

Representative objective:

> Caractériser un signal sinusoïdal par son amplitude, sa période, sa fréquence, sa pulsation et sa valeur efficace.

- training activities: period/frequency/pulsation application and amplitude/RMS transfer;
- distinct validation: characterize `i(t)=0,2 cos(400πt) A`;
- the validation now references only the representative signal-characterization objective;
- package, course and changed validation activity use new revision IDs and recalculated digests.

The mathematical and physical content remains consistent with the supplied EPF course sources: complex-plane coordinates and module for Nombres complexes, and amplitude, frequency, period, angular frequency and peak-to-peak value for Signaux électriques.

## Rollback

Revert only the five DEV-AUTHORING paths. The frozen schema, Learn-it Next source, import behavior, corrective review, accessibility and RC718 storage remain untouched.
