# Parcours V6 assistance — candidate domain contract, PR #514

> **CANDIDATE / NOT ADMITTED / HOLD until independent review.**
> This is a human-approved *functional decision*, not a self-certified domain event authority or release approval. No learner hint side-effect may be wired or activated on the strength of this document alone.

## Identity, decisions and normative bounds

- Existing Operations job: `LEARNIT_V6_THREE_MODULE_CONVERGENCE_AND_LEGACY_CLEANUP_R1`.
- Immutable `EXECUTE_ME.md` SHA-256: `5e00c873010c245cf8ec5361692a314d252c464b2bb9c4f59b1fd38f9d0b1a37`.
- Exact frozen main baseline: `ba97c68be0273437836230d66aed0e9d151f8a17`. Scope: draft PR #514 only. Charter v16.0 verified at proposal time.
- **Human decision (2026-11-05): Parcours is accountable for the V6 learner assistance domain.** Bibliothèque owns admitted kit/revision and provenance; Renderer is a pure view/intent adapter, never an independent authorization source.
- The user approved **0–3 hints**, authored order, active authorized V6 session, authorization and acknowledgement durably committed *before* reveal, deduplicated request IDs, crash replay, isolation per session/revision, unchanged scores/`maxUses`, full V2–V5 preservation.
- Local application-only trust boundary: student-controlled UI input is **not** a trusted authorization, including `parcoursAuthorized: true`. No claim of server-enforced anti-tamper security exists.

## Preconditions to activate one real V6 hint intent

1. Parcours, not Renderer or Explorer, must independently load the **active session snapshot** from canonical session storage, validate V6-only session UUID and currently served activity, and reject completed, stale, unknown, cross-course, or out-of-sequence intent. A client-supplied boolean, session ID, activity ID, or hints array is never proof of authorization.
2. Bibliothèque must supply the exact installed V6 course/kit for `courseInstallId`, its trusted package revision digest and activity revision digest, and the authored 0–3 hint strings. The input source is an admitted exact-revision V6 kit, not a free-form UI payload.
3. Validate exact identity binding to package install, package revision, course install, activity revision, active session UUID, and hint-array digest. A new course start rotates UUID; reload of the same active course preserves it. Version/revision drift causes fail-closed denial, never silent rebind of previous journal.
4. A fresh cryptographically random request UUID is generated once per **user intent**; retries reuse it. `AUTHORIZED(requestId,rank)` is appended through a durable, atomic IndexedDB compare-and-swap transaction; no hint text is written to the journal. Only after transaction completion may the same request be `ACKNOWLEDGED(requestId,rank)` in a second durable atomic commit.
5. `readAuthorizedView` may supply **only the acknowledged prefix** and only after rechecking the current trusted Parcours scope. `AUTHORIZED` without acknowledgement reveals nothing. Corrupt, absent-after-commit, competing, mismatched or unrecoverable journal => HOLD/deny, not a permissive reset.
6. Renderer receives a frozen authorized view and draws each hint as text, in source order, with keyboard focus/announcement and error/retry affordance. Renderer emits only a hint-request intent; it does not access the raw kit hints, issue acknowledgements, select assistance ranks, or persist state.
7. Explorer may expose authored hints only via its existing explicit `readOnlyHintPreview` path. This is not a learner authorization. No `learnit.kit.v5` journal or previous-response event may be imported as V6 authority.
8. Assistance state is independent of answer evaluation, progress, Atlas assistance classifications, scoring, response `maxUses`, and reward computation. Future semantic interaction with Atlas learning mastery needs a **separately approved and reviewed domain change**.
9. For any failure between authorization and acknowledgement, recover the persisted pending request ID and either finish its authorised ACK or keep all hints hidden. On offline errors, transaction abort, quota exhaustion or two-tab collision, never reveal or consume another rank silently. Other tabs resolve via canonical journal re-read, with one authorization per rank.
10. Fail closed on storage deletion/corruption. Do not reset or migrate real student IndexedDB; a new store/version or independent database scheme needs exact compatibility and migration testing before user-visible activation.

## Current implementation status (separate fact from approval)

- `src/core/v6_assistance.js`: isolated candidate `AUTHORIZED`/`ACKNOWLEDGED` CAS journal, source/hint digest binding, replay. Its `authorize(ctx)` callback is a **trust interface only**; the synthetic test callback accepts `ctx.parcoursAuthorized===true`, which is **not safe for real learner use**.
- `src/adapters/v6_assistance_indexeddb.js`: synthetic isolated IndexedDB CAS; no integrated migration or durable authority upgrade qualified.
- `src/core/session.js`: V6-only UUID seeded on new session and preserved after reload; does not authorize hints.
- `src/integration/atlas/activity_projection.js`: learner path defaults to hiding hints; read-only preview is separate.
- Existing CI on exact PR head `e7efce49047936ec872e69a3d3d39b13ea4be156`: Node 25/25 PASS, Chromium 12/12 PASS (9 journal smoke + 3 real learner session-UUID-only), two deterministic builds. **Not an end-to-end real learner hint test.**
- `ATLAS-WP-026` dedicated workflow rejects this unrelated branch by its own guard; do not amend it or use its failure to imply the journal failed.
- No legitimate old renderer, V5 adapter, source registry, scores, library content, or legacy code deleted. No actual learner hint button/runtime side effect wired.

## Required independent cross-owner approval (unmet)

The repository `docs/governance/DECISION_RIGHTS.md` requires Governor approval of a shared contract plus consumer and independent QA review; when an implementer authored it, that implementer/governor **cannot be the sole reviewer**.

Record reviewer **identity, independence from implementer, reviewed exact PR head, explicit PASS/HOLD/FAIL, evidence, objections and accepted revisions** before admission:

- **Bibliothèque / content consumer:** prove trustworthy source/revision binding, 0–3 hint contract and V6-only import.
- **Parcours domain/governor:** authorize active-session scope and actual event owner; disallow caller-controlled permissions. Decide expected cross-session, reopen/review, post-answer and completion semantics.
- **Renderer/UX:** verify authorised prefix only, a11y/focus/announcements, safe text and independent preview separation.
- **Independent QA/security:** challenge malicious UI context, tab races, stale sources, offline/crash, version upgrades and V5 isolation; reproduce on exact binary and inspect regressions. Reviewer cannot be the author alone.

**CURRENT VERDICT: HOLD_DOMAIN_AUTHORITY_INDEPENDENT_REVIEW.** The human functional decision is adopted as a design constraint; it is not a substitute for review and a trusted Parcours resolver. Do not mark this contract ACTIVE, merge PR, deploy Pages, or mutate kits, real learner data, Factory or catalogue.

## Exit criteria for subsequent governed implementation

- Exact independent PASS/admission (or HOLD with precise objection) recorded against this contract/head.
- Implement trusted Parcours scope derivation from active session and installed V6 kit, not `ctx.parcoursAuthorized`; create a closed authorized-domain event interface.
- On the **same PR #514** test an actual hint click/ACK/reveal/reload, 0 hints and 1–3 hints, two tabs, crash at each step, stale/competing source, score/`maxUses` noninterference, V5 regression, desktop/mobile accessibility, representative route coverage and two identical full builds.
- Record independent QA sign-off, three adversarial critique cycles, exact CI head and create-only durable evidence under separately admitted OneDrive paths. Never replace historical five immutable OUTPUTS.
- Before any merge/release, obtain a **separate explicit human GO**; neither this document nor a green CI grants promotion authority.
