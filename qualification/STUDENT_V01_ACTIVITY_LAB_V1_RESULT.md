# Student V0.1 — Activity Experience Lab V6 — Destination Feedback / No Layout Shift — Phase A Result

Status: **READY FOR PHYSICAL ANDROID HUMAN REVIEW**

## Authority

- common base: `18b925436777943b19c4b031c24659ad60dee133`
- issue: `#434`
- draft PR: `#437`
- branch: `student-v01/g5-r1-activity-experience-lab`
- canonical JOB 10B blob: `9867580c41fa72eeb7cade20a20060906810ee4d`
- work-package blob: `a863c67a575cb84c80ec128f66fb81bd5c05064d`

Frozen authority revalidated:

- `WAVE1_INTERFACE_FREEZE.md`: `cf15b12e0d008484b8341a8a059fe0d91955f8b0`
- `STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`: `c900d96c3845276e23b77a43c970c7c3834655a5`
- production `activity_projection.js`: `607ecea8af6dc468ded05dbcc924693f90d576ff`
- production `activity_presenters.js`: `fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`

## Refined V6 execution prompt

The latest physical-device feedback was converted into a bounded V6 prompt before implementation.

- filename: `ACTIVITY_LAB_V6_DESTINATION_FEEDBACK_EXECUTION_PROMPT.md`
- SHA-256: `294c9b248dd759b0cb5ef8728bb8133807b7d4f24a994926530a246d4ffb1476`
- bytes: `12008`

The prompt establishes one transverse invariant:

> selecting a movable object must not alter activity geometry; selection only marks the object and reveals all and only valid destinations. Tapping a revealed destination commits the action. Dragging to the same destination remains a shortcut.

## Superseded result

The V5 result `fd30ac0f92b1fa4b9588e70a6fe60f10f593a9c0` is superseded for the next physical-device review.

No formal human prototype selection was inferred from the qualitative V5 feedback.

## Frozen V6 implementation

`LAB_RESULT_SHA`: `9a012886b15d72b752983123d78326ea5ac9709a`

V6 remains isolated to the Lab, its allowed architecture note, tests and qualification evidence. Production application source is unchanged.

### Implemented destination-feedback model

- shared visual states: normal, selected, eligible destination, active destination, dragging; keyboard focus remains independent;
- **Matching B**: source selection does not move geometry and highlights valid descriptions; matched source card replaces the dashed source-side target without stacked framing;
- **Order B**: selecting a row creates an absolute overlay of insertion targets and leaves all row rectangles and list height unchanged; visible intercalaires are thin while hit regions remain >=24px; center taps on adjacent cards remain usable; drag remains fixed-X / vertical-Y with a separate insertion placeholder;
- **Classify B**: selection alone never moves a card; only valid bucket-title destinations are highlighted; a placed card exposes source return plus other buckets, not its current bucket;
- **Fill B**: token selection alone never moves a token; empty slots are highlighted; a placed token additionally exposes the bank return destination; filled slots remain shell-free and non-destination by simple tap;
- **Flashcard B**: question, answer and explanation retain one left/start reading axis;
- randomizable option pools still shuffle once per attempt and remain stable within that attempt.

The V5 monolithic `lab_candidates.js` was removed from the V6 tree. V6 candidate renderers are split into explicit modules so the active implementation surface is unambiguous.

## Production audit and bounded repair

The separate adversarial production audit was executed after construction.

### Finding 1 — Order target size / interference

The first prompt draft contemplated ~44px insertion overlay targets. Audit reasoning showed that on the compact mobile list this would consume too much of adjacent-card space and risk intercepting normal card selection.

**Repair:** the prompt and implementation were tightened to a >=24px, approximately 28px overlay hit region with a 2px visible line. The production audit additionally proves that overlap with adjacent cards remains bounded and that the center of another card is still independently clickable.

### Finding 2 — stale version metadata

The visual audit found that the rendered page still carried stale V5 title/eyebrow metadata after the first V6 construction pass.

**Repair:** title, eyebrow and page heading were corrected to V6. All audits were rerun from clean state.

### Audit-harness corrections

Two assertions in the adversarial harness initially treated transient CSS transition/focus behavior as product defects. Those assertions were corrected; no functional invariant was relaxed.

Post-repair verdict: **PASS**.

## Exact Git identity audit

The complete V6 source set was reread from `LAB_RESULT_SHA` and matched the expected Git blob identities, including:

- `index.html`: `93b08e1851fa599f09eb06af9c3aa5f12d05e9c1`
- `styles.css`: `146ea82e6fd6842be7b03ad9d5fb32bdf0ac9ef4`
- `lab_v6_helpers.js`: `2c6947853c7c701ae236eb55c1f46b270b1d0fb0`
- `lab_v6_flash.js`: `26a23f8a63bd6a268df8701fb751ba27019a422d`
- `lab_v6_matching.js`: `73f8b48c1113dcdb799189f18178889dc0eb7e63`
- `lab_v6_order.js`: `707ff3496ea600ec3322cc61055187ccc39548ac`
- `lab_v6_classify.js`: `5883929fc6d282980eeda9658cbea3ab05e5fb2a`
- `lab_v6_fill.js`: `734906cdb22cd571cfebab6ab11a872c0e1b2369`
- `test_lab.py`: `ce24732cfd1ffc4d1247fa43ce7c9fa4c3ef3d8a`
- `browser_smoke.py`: `73c3bbb726ce7c9d1de342d3764a9223dd90b425`
- `production_audit.py`: `c8d3fd9dc3f1fc77da40cafb8249c868dd046c6c`
- `visual_audit.py`: `5b30ffa08fccb956f8449cecd5886d5e9a54ce2c`

Stale `lab_candidates.js`: **ABSENT**.

## Automated audit

Source-tree audits:

- `STATIC_LAB_V6_TESTS: PASS`
- `BROWSER_LAB_V6_DESTINATION_FEEDBACK_AUDIT: PASS`
- `PRODUCTION_AUDIT_V6: PASS`
- `VISUAL_AUDIT_CAPTURE_V6: PASS`

Key causal / adversarial assertions:

- Order selection changes no row rectangle: PASS
- Order selection changes no list height: PASS
- Order insertion controls are absolute overlay children, not row-flow siblings: PASS
- Order visible insertion line <=4px; target hit region >=24px: PASS
- Order overlay/card-center interference bounded: PASS
- Order no-drag insertion changes order: PASS
- Order causal touch drag creates ghost + active placeholder and changes final order: PASS
- Matching selection geometry invariant: PASS
- Matching eligible-destination feedback: PASS
- Matching destination feedback clears after commit: PASS
- Matching filled-slot and outer-row redundant framing: ABSENT
- Classify selection geometry invariant: PASS
- Classify repeated selection creates no mutation: PASS
- Classify valid-destination feedback: PASS
- Fill selection geometry invariant: PASS
- Fill repeated selection creates no mutation: PASS
- Fill empty-slot destination feedback: PASS
- Fill filled-slot redundant shell: ABSENT
- common manip-card radius / state vocabulary: PASS
- nested actual buttons: NONE
- stale movement-panel UI: NONE
- external requests: NONE
- browser errors: NONE

Extracted deterministic ZIP audits:

- static audit: PASS
- browser/mobile audit: PASS
- adversarial production audit: PASS
- visual audit: PASS

Standalone Android HTML:

- `PORTABLE_ANDROID_V6_AUDIT: PASS`
- ZIP portable entry byte-equal to external portable artifact: PASS
- external requests: NONE
- browser errors: NONE

The browser evidence is causal mobile/touch simulation. It does **not** substitute for physical Android human review.

## Repository audit

- exact common-base merge base: PASS
- production `activity_projection.js` unchanged: PASS
- production `activity_presenters.js` unchanged: PASS
- frozen interface and richness architecture blobs unchanged: PASS
- implementation changed-path scope: PASS
- PR remains DRAFT / OPEN / UNMERGED: PASS
- Repository governance on LAB_RESULT_SHA: PASS, run `35991617659`

No production-source correction was required because the audited production source blobs remain exactly frozen.

## Human review package

Current deterministic review archive:

- filename: `STUDENT_V01_ACTIVITY_LAB_V6_HUMAN_REVIEW.zip`
- SHA-256: `667b30dc1fd634b81e286d5fb600388957a62b5dd82de1dd61a83618d0e9863b`
- bytes: `567929`
- deterministic rebuild: PASS

Portable Android entry:

- filename: `ACTIVITY_LAB_V6_DESTINATION_FEEDBACK_ANDROID.html`
- archive entry: `00_OPEN_ME_ACTIVITY_LAB_V6.html`
- SHA-256: `5f9e7f8bbb1c1a242606fc705fbfd6b82ea2ca87a5a21e15079e82c4a7fc990b`
- bytes: `49141`
- self-contained CSS/data/JavaScript: PASS

Human-selection template:

- filename: `ACTIVITY_LAB_V6_HUMAN_SELECTION.txt`
- SHA-256: `07d83fdb7bd85e61d27f81c22227bf105109c26e262438635dc0b76131147fd4`
- bytes: `597`
- bound to exact current ZIP SHA-256: PASS

## Gate

`HUMAN_PHYSICAL_ANDROID_REVIEW: REQUIRED`

No human prototype selection is inferred. No Phase-B integration, merge or promotion is authorized.
