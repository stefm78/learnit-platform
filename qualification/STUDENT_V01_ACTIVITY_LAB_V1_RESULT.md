# Student V0.1 — Activity Experience Lab V5 — Interaction Convergence — Phase A Result

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

## Refined V5 execution prompt

The latest physical-device review was converted into a bounded V5 interaction-convergence prompt before implementation.

- filename: `ACTIVITY_LAB_V5_INTERACTION_CONVERGENCE_EXECUTION_PROMPT.md`
- SHA-256: `a073da9e2db212ff08c97647df5489e5e8b3643fabdb76de5c9cece990be0044`
- bytes: `10511`

The prompt requires one common manipulation grammar, explicit non-drag destinations, strict vertical Order-B semantics, no implicit mutation on selection clicks, deterministic per-attempt randomization, causal mobile-touch tests, a separate adversarial production audit and a bounded repair loop.

## Superseded result

The V4 result `91c217b4b9a1d5ba4b19c8e3b12e7da901ac6d25` is superseded for the next human review.

The prior automated V4 Order-B PASS is not treated as physical-device proof; physical Android feedback remains authoritative contradictory evidence for the usability of that exact build.

## Frozen V5 implementation

`LAB_RESULT_SHA`: `fd30ac0f92b1fa4b9588e70a6fe60f10f593a9c0`

V5 remains isolated to the Lab, its allowed architecture note and qualification/test material. Production source is unchanged.

### Implemented convergence

- **Flashcard B**: question, answer and explanation retain one left/start reading axis; the card remains reversible.
- **Matching B**: the stacked-frame defect is removed. An empty left target has one dashed affordance only; after placement the moved card replaces that affordance and the pair row itself has no outer frame. Selection is a subtle tinted/bordered state distinct from keyboard focus. Select-card -> tap-target and drag both work.
- **Order B**: rebuilt around strict vertical motion. A floating ghost has fixed X; a separate insertion placeholder moves through the list while the source row is not repeatedly reparented under the pointer. On drop the source is inserted at the placeholder. The non-drag path is card selection -> tappable intercalaires. No permanent ordinals or move-arrow buttons exist.
- **Classify B**: the intermediate movement panel is removed. Card tap selects only; direct bucket-title tap moves the selected card; tapping `À classer` returns it. Drag remains a direct shortcut.
- **Fill B**: the intermediate movement panel is removed. Token tap selects only; empty-slot tap places the selected token; a filled slot loses its dashed shell and destination semantics. Drag replacement returns the displaced token to the bank; the bank title is the explicit non-drag return destination.
- **Look & feel**: Matching / Order / Classify / Fill use one common card radius, neutral border, subtle selected state and drag elevation.
- **QCM A**: radio/text alignment and long-label wrapping retained.
- **Randomization**: QCM, Matching source/targets, Order, Classify source and Fill token pools shuffle once per attempt and remain stable within that attempt.

## Adversarial production audit and repair

The separate production audit intentionally challenged the authored browser tests and found one bounded regression during V5 construction:

**Finding:** Pointer Event setup could suppress the ordinary tap-selection path on a manipulable card, creating a false impression that the direct tap model was functional only in some scripted paths.

**Repair:** ordinary tap selection was restored; click suppression is now applied only after a real drag to absorb the synthetic post-drag click. The complete static, causal mobile-touch and production audits were rerun from clean state after the repair.

Post-repair verdict: **PASS**.

## Automated audit

Static audit:

- fixture schema / scoring-secret scan: PASS
- 12 required variants: PASS
- Pointer Events implementation: PASS
- HTML5 Drag-and-Drop dependency: ABSENT
- persistence / external network / evaluator authority: ABSENT
- stale movement-panel UI: ABSENT
- required V5 structural markers: PASS

Mobile Chromium audit at 390×844:

- Flashcard B reading-axis alignment: PASS
- same test seed => same randomized order: PASS
- different test seed => different representative order: PASS
- no reshuffle during an attempt: PASS
- Matching B selection state distinct from focus: PASS
- Matching B repeated selection produces zero association mutation: PASS
- Matching B select->target and causal drag: PASS
- Matching B filled target has no dashed shell / pair row has no outer border: PASS
- Order B ghost X locked while Y changes: PASS
- Order B placeholder moves before pointer-up: PASS
- Order B sibling reflow before pointer-up: PASS
- Order B final DOM reorder after drop: PASS
- Order B select->intercalaire non-drag reorder: PASS
- Classify B repeated card clicks produce zero movement: PASS
- Classify B direct bucket-title destination: PASS
- Classify B placed-card -> another bucket: PASS
- Classify B source-title return: PASS
- Fill B repeated token clicks produce zero movement: PASS
- Fill B direct empty-slot destination: PASS
- Fill B filled slot loses role/tabindex and dashed shell: PASS
- Fill B drag replacement returns displaced token to bank: PASS
- Fill B bank-title return: PASS
- frozen ActivityResponse grammars: PASS
- long-label stress at 390px: PASS
- reduced-motion behavior: PASS
- external requests: NONE
- browser errors: NONE

Adversarial production audit:

- ordinary tap path survives Pointer Event machinery: PASS
- selected state distinct from focus: PASS
- Matching nested framing removed: PASS
- Order non-drag intercalaires have >=40px hit height: PASS
- Classify destination remains available with existing bucket contents: PASS
- Fill occupied slot has no nested destination semantics: PASS
- common card radius across manipulable families: PASS
- nested actual buttons: NONE
- stale `Déplacer « ... » vers...` UI: NONE

Visual audit screenshots inspected:

- Matching B filled state: PASS
- Order B selected/intercalaires state: PASS
- Classify B mixed source/bucket state: PASS
- Fill B filled + empty slot state: PASS

## Package verification

Source tree:

- `STATIC_LAB_V5_TESTS: PASS`
- `BROWSER_LAB_V5_INTERACTION_AUDIT: PASS`
- `PRODUCTION_AUDIT_V5: PASS`

Extracted deterministic ZIP:

- source static audit: PASS
- source mobile/touch audit: PASS
- source production audit: PASS
- portable HTML entry byte-equal to external portable artifact: PASS

Standalone Android HTML:

- `PORTABLE_ANDROID_V5_AUDIT: PASS`
- external network requests: NONE
- browser errors: NONE

The automated browser evidence remains causal mobile/touch simulation. It does **not** substitute for physical Android human review.

## Repository audit

- exact common-base merge base: PASS
- V5 implementation Git objects reread by exact Git blob identity: PASS
- production `activity_projection.js` unchanged: PASS
- production `activity_presenters.js` unchanged: PASS
- frozen interface and richness architecture blobs unchanged: PASS
- implementation changed-path scope: PASS
- PR remains DRAFT / OPEN / UNMERGED: PASS
- Repository governance on LAB_RESULT_SHA: PASS, run `35984782842`

## Human review package

Current deterministic review archive:

- filename: `STUDENT_V01_ACTIVITY_LAB_V5_HUMAN_REVIEW.zip`
- SHA-256: `10e302ddd0d6d8bd64d195459ba27cbf2c3df9dc2da86d3ac1128da247ef7749`
- bytes: `371385`
- deterministic rebuild: PASS (byte-identical rebuild)

Portable Android entry:

- filename: `ACTIVITY_LAB_V5_INTERACTION_CONVERGENCE_ANDROID.html`
- archive entry: `00_OPEN_ME_ACTIVITY_LAB_V5.html`
- SHA-256: `5f65820c21feffef8eac8a2fe88854d486385efd6a0086f6e901c9dc6f60293f`
- bytes: `43659`
- self-contained CSS/data/JavaScript: PASS
- external stylesheet/script dependency: NONE

Human-selection template:

- filename: `ACTIVITY_LAB_V5_HUMAN_SELECTION.txt`
- SHA-256: `7fc546d597e3d5b332fb6df73dd3ceb72c399d72415b95372df166715bba1b45`
- bytes: `597`
- bound to exact current ZIP SHA-256: PASS

## Gate

`HUMAN_PHYSICAL_ANDROID_REVIEW: REQUIRED`

No human prototype selection is inferred. No Phase-B integration, merge or promotion is authorized.
