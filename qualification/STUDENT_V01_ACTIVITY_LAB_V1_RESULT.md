# Student V0.1 — Activity Experience Lab V7 — Exact Order-B Drag Geometry — Phase A Result

Status: **READY FOR PHYSICAL ANDROID HUMAN REVIEW**

## Authority

- common base: `18b925436777943b19c4b031c24659ad60dee133`
- issue: `#434`
- draft PR: `#437`
- branch: `student-v01/g5-r1-activity-experience-lab`

Frozen production / contract blobs remain unchanged:

- `WAVE1_INTERFACE_FREEZE.md`: `cf15b12e0d008484b8341a8a059fe0d91955f8b0`
- `STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`: `c900d96c3845276e23b77a43c970c7c3834655a5`
- production `activity_projection.js`: `607ecea8af6dc468ded05dbcc924693f90d576ff`
- production `activity_presenters.js`: `fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`

## Prompt

- filename: `ACTIVITY_LAB_V7_EXACT_DRAG_GEOMETRY_EXECUTION_PROMPT.md`
- SHA-256: `3c113ee42371301990ac6fe5ef205ff5488434510d39116fa0fc0f4ee26090e2`
- bytes: `11457`

The prompt makes the measured source border-box the sole authority for the Order-B placeholder geometry and requires the dragged source to leave Grid flow while preserving pointer capture.

## Frozen V7 result

`LAB_RESULT_SHA`: `13d44db96e3d526ddb7e3ae90bde488fd16af9a3`

This SHA supersedes the initial V7 implementation commit `a6c15c74e2a673306b096e1d5cc274be779943b0`.

### Product corrections

1. **Exact placeholder geometry**
   - placeholder width and height are copied from source `getBoundingClientRect()`;
   - explicit border-box sizing;
   - no fixed 54px minimum;
   - source row is moved to `position:absolute` during drag and therefore does not consume a Grid track or Grid gap;
   - placeholder is the sole in-flow geometric representative.

2. **Grid-gap correction**
   - removes the V6 pattern where a zero-height source row could coexist with the placeholder in Grid flow and create an extra gutter;
   - list height remains invariant while the placeholder moves.

3. **Visual-geometry correction after visual audit**
   - generic `active-destination` styling added an outer box-shadow to the placeholder, making the dashed target visually appear larger than its exact border box;
   - V7 adds a placeholder-specific `box-shadow:none!important` override.

4. **Cleanup**
   - drop restores normal-flow source styles;
   - pointer cancel removes ghost / placeholder and restores original source geometry/order;
   - no stale inline positioning remains.

### Preserved behavior

- non-drag Order-B selection / overlay intercalaires remain zero-reflow;
- drag remains vertical-order semantics;
- Matching B / Classify B / Fill B V6 destination-feedback behavior is unchanged;
- frozen ActivityResponse grammar remains unchanged.

## Audit

### Broad regression suite

- `STATIC_LAB_V7_TESTS: PASS`
- `STATIC_LAB_V7_GEOMETRY_INVARIANTS: PASS`
- `BROWSER_LAB_V7_DESTINATION_FEEDBACK_AUDIT: PASS`
- `PRODUCTION_AUDIT_V7: PASS`
- `VISUAL_AUDIT_CAPTURE_V7: PASS`

### Exact geometry suite

- short-label placeholder width/height == measured source within 1 CSS px: PASS
- placeholder initial x/y == source footprint within 1 CSS px: PASS
- source computed position is out-of-flow during active drag: PASS
- unique in-flow representative count preserved: PASS
- list height invariant during drag: PASS
- normal Grid row-gap accounting preserved: PASS
- placeholder moves before pointer-up: PASS
- multi-line source geometry: PASS
- 320px narrow-mobile geometry: PASS
- pointer cancel restoration: PASS
- residual inline style cleanup: PASS
- repeated first→last / last→first / middle→first / middle→last: PASS

`ORDER_B_V7_EXACT_GEOMETRY_AUDIT: PASS`

`ADVERSARIAL_PRODUCTION_GEOMETRY_AUDIT_V7: PASS`

### Audit findings

- The first adversarial repeated-drag harness used the exact midpoint of a target row for a before/after assertion. That coordinate is semantically ambiguous for an insertion algorithm whose threshold is the row midpoint. The harness was corrected to use unambiguous upper/lower edge targets; no functional invariant was weakened.
- Visual inspection found the generic active-destination box-shadow enlarged the *perceived* dashed target even though measured layout geometry was exact. The product CSS was corrected, then all relevant audits were rerun PASS.

### Standalone / package audit

- standalone Android HTML audit: `PORTABLE_ANDROID_V7_AUDIT: PASS`
- extracted ZIP static audit: PASS
- extracted ZIP broad mobile/browser audit: PASS
- extracted ZIP broad production audit: PASS
- deterministic ZIP rebuild: PASS

The causal automated browser evidence does not substitute for physical Android review.

## Repository governance

Repository governance on final LAB_RESULT_SHA:

- run `35995430750`
- conclusion: **PASS**

PR remains **DRAFT / OPEN / UNMERGED**.

## Human review package

Review ZIP:

- filename: `STUDENT_V01_ACTIVITY_LAB_V7_HUMAN_REVIEW.zip`
- SHA-256: `9067de6d9859da2f3f0481b3bc9cd9b1930c0122bca763a702e5c8f19fe3d781`
- bytes: `673935`

Standalone Android HTML:

- filename: `ACTIVITY_LAB_V7_EXACT_DRAG_GEOMETRY_ANDROID.html`
- SHA-256: `58648612e1b66ebd0bd1da8c10f98f541fbe10cb59669b8d40dd54f817c44875`
- bytes: `49912`

Human-selection template:

- filename: `ACTIVITY_LAB_V7_HUMAN_SELECTION.txt`
- SHA-256: `6d0708cdf3febd79c9be11bc36ae4fe018e3b047687ec8197015d7d58e5329a5`
- bytes: `597`
- bound to the exact review ZIP SHA-256 above.

## Gate

`HUMAN_PHYSICAL_ANDROID_REVIEW: REQUIRED`

No human selection is inferred. No merge, Phase-B integration or promotion is authorized.
