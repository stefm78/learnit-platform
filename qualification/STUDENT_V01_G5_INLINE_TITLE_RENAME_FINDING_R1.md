# STUDENT_V01_G5_INLINE_TITLE_RENAME_FINDING_R1

JOB: `JOB_29_G5_INLINE_COURSE_TITLE_RENAME_AFFORDANCE_R1`
WORK_PACKAGE: `ATLAS-WP-071`
EXECUTION_ISSUE: `#473`
PARENT_PR: `#472`
PARENT_EVIDENCE_HEAD: `829b51caa638bbbb6c81ca9a0ee8f60ab5d59b30`
PARENT_REVIEWED_PRODUCT_SHA: `562af21e9b5fb1decd6a902dfdfa76873fa9c8bc`

## Finding

`G5-UX-003_INLINE_TITLE_EDIT_AFFORDANCE_VISUAL_WEIGHT`

JOB28 correctly removed the one-action ellipsis menu and made rename direct, accessible and out-of-flow. The remaining human finding is narrower: the visible 44x44 boxed pencil occupies disproportionate space as a separate course action.

## Required correction

- Keep the title as the dominant heading.
- Place one semantic pencil button immediately after the displayed title in the title region.
- Visible button footprint must be compact and chromeless, target <=32x32 CSS px.
- Preserve an approximately >=44x44 effective transparent pointer/touch target.
- Keep the rename overlay absolute/out-of-flow and anchored to a stable title-region ancestor.
- Preserve Escape cancel/focus restoration, Enter save through `runtime.setCourseDisplayLabel(...)`, local alias persistence and canonical-title immutability.
- No title-wide click target and no `contenteditable`.
- Preserve accepted JOB28 terminal guidance, search/hamburger behavior, R15, learner journey, runtime/presenter behavior and exact V5 showcase bytes.

`HR24_003 = CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED`

This is a micro-corrective UX finding only. No G5 or pilot decision is implied.
