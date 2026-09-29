# STUDENT_V01_G5_DELTA_UX_FINDINGS_R1

JOB: \`JOB_28_G5_DELTA_UX_FINDINGS_CORRECTIVE_R1\`
WORK_PACKAGE: \`ATLAS-WP-070\`
EXECUTION_ISSUE: \`#471\`
G5_AUTHORITY_ISSUE: \`#427\`
PARENT_JOB27_HEAD: \`b6a24a5b2d300d3e10fc8a413148071636653a06\`
PARENT_REVIEWED_PRODUCT_SHA: \`8eceb94b8003adc539d34d2cfeeca62ff0c565a0\`
HUMAN_AUTHORIZATION_SOURCE: \`USER_EXPLICIT_G5_DELTA_UX_FINDINGS_CHAT_2026-09-29\`
NEW_CANDIDATE: \`PENDING_JOB28_RESULT_SHA\`

## G5-UX-001 — TERMINAL_GUIDANCE_TOO_VERBOSE

Human observation: on the completed-activities mobile state with an objective still \`À confirmer\`, the \`Parcours d’activités terminé\` block contains substantially more explanation than is useful for the learner.

Code root cause: \`renderCourseCompletionGuidance(...)\` hard-codes the long copy in the \`recommendation.action === 'validate'\` presentation branch.

Bounded solution: retain the heading and the underlying recommendation/objective state, but replace only the long learner-facing paragraph with \`Un objectif reste à confirmer. Rien à faire pour le moment.\`

Impacted G5 dimension: \`INFORMATION_DENSITY\`.

Human PASS is not claimed by this corrective evidence.

## G5-UX-002 — RENAME_MENU_AND_REFLOW

Human observation: a per-course \`⋯\` control opens a one-action \`Renommer\` menu, and selecting it replaces the course title in normal flow, moving neighboring controls.

Code root cause: the one-action \`course-settings-details/course-settings-menu\` path invokes \`beginRename()\`, which previously used \`titleSlot.replaceChildren(form)\`.

Bounded solution: replace the one-action menu with one direct accessible edit button, preserve \`runtime.setCourseDisplayLabel(...)\`, keep the authored canonical title immutable, and render the editor outside normal layout flow with a 44x44 minimum touch target and explicit focus restoration.

Impacted G5 dimensions: \`INTERACTION_GESTURE_QUALITY\`, \`MOBILE_TOUCH_USABILITY\`.

Human PASS is not claimed by this corrective evidence.

## Preserved / non-goals

- No scoring, ActivityResponse, objective-state, recommendation, sessionDelta, scheduler/date or authored-content semantics change.
- The implicit multi-term AND Library search and main three-bar navigation behavior remain accepted evidence to preserve, not human replay work to repeat.
- The exact V5 showcase kit remains byte-identical with expected SHA256 \`aeac0925e686d6055405382142ad14831c27f73992401a1748ec76b85665c62b\`.
- \`HR24_003_ENGINE_GAP\` remains \`CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED\` / known pilot limitation.
- No G5 PASS, GO_LIMITED_PILOT, merge, promotion or real student session is authorized.

The exact corrected candidate identity is intentionally recorded later in the JOB28 result evidence after machine qualification; this file does not fabricate that identity in advance.
