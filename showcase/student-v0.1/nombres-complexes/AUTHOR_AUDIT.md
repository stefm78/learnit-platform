# Student V0.1 JOB06 — Author-side audit evidence

## Fresh authority rebind

- Constitutional UCP: `UCP-CONTROL-PLANE 1.1-R4 ACTIVE`; exact byte SHA-256 `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4` verified before project work.
- Fresh `CONTROL_PLANE_HEAD.json` Git blob: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`; deployment state `POST_APPLY_ACTIVE`.
- Active orchestrator: `UAO-KERNEL 2.6`, exact SHA-256 `dad404793b931bc4b7448d546dd6a54397fe32ea6a57213d3c42a3546441140e`.
- Selected command authorities were exact-hash verified before execution: UAA 1.2, UAS 2.4, UAB 1.3 and compatibility contract 1.0.
- Repository authority rebind: issues #401, #403 and #405 fresh-read; PR #402 fresh-read as open, draft and unmerged.
- JOB06 PR: #408, draft.
- Exact common base: `281dc7470d51682c5e6d79d3fff54c46cfbced3b`.
- Exact prepared JOB06 head before build: `88d8f8a0e5f4eaeede8eb6b2cb51156801b02f7e`.
- Branch ancestry was re-proved from the common base before mutation; the prepared branch was CAS-identical to `88d8f8a0e5f4eaeede8eb6b2cb51156801b02f7e`.
- First authored-content commit: `1542aaf3cc217b39c55e1f5599e8ea9d76e311ff`.
- GitHub Actions `Repository governance` run `35357599721` completed with conclusion `success` on that authored-content commit.

## Content and deterministic checks

- Source sufficiency: PASS
- Candidate course duration: 42 min
- Sum of activity durations: 42 min
- Activity families: `{"constructed": 1, "flashcard": 2, "lesson": 1, "matching": 2, "order": 1, "qcm": 4}`
- Evaluated operation families: `constructed, matching, order, qcm`
- Non-scored units: 3 (`lesson`/`flashcard` only), none carries `assessmentRole`, `diagnostic`, or `validation`.
- Media: NOT_USED
- Frozen V4 structural/semantic audit: PASS; 59 canonical IDs defined, 12 objective references checked, zero structural/semantic findings for the authored constructs.
- Canonical revision-digest checks: PASS for all 11 activities, the course and the package, using the frozen v2/V4 canonical JSON + SHA-256 algorithm.
- SHA-256 control self-test: `SHA256("abc") = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`.
- Exact source SHA-256 recheck: `sha256:3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`.
- Pedagogical profile: EXCELLENT_BY_PROFILE; zero warning/advice/blocking diagnostics under the frozen Student V0.1 V4 quality rules.
- Source traceability: every candidate activity is mapped in `PROVENANCE_MAP.json`; every mapping has at least one exact source reference; assets list is empty.
- Factory binding: PASS. Exact kit/brief/source-set/context hashes were independently recomputed from Git bytes and match `FACTORY_CONTEXT.json`.
- Independent semantic review: `PENDING_INDEPENDENT_REVIEW_AT_G3_OR_LATER`. No independent semantic PASS is claimed.

Adversarial challenge outcome: no exposure-only objective, no quiz-only treatment, no repeated single evaluated operation per objective, no classify task, the order task reconstructs the source-supported module calculation and is initially shuffled, the constructed response is bounded to an exact source-supported conjugate, lesson/flashcard are non-scored, no media exists, and total duration remains 42 minutes.

## Exact JOB06 build paths

Relative to prepared head `88d8f8a0e5f4eaeede8eb6b2cb51156801b02f7e`, the authored result changes exactly these nine paths:

1. `showcase/student-v0.1/nombres-complexes/SOURCE_BASIS.md`
2. `showcase/student-v0.1/nombres-complexes/LEARNER_BRIEF.json`
3. `showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v4.json`
4. `showcase/student-v0.1/nombres-complexes/PROVENANCE_MAP.json`
5. `showcase/student-v0.1/nombres-complexes/V4_VALIDATION_REPORT.json`
6. `showcase/student-v0.1/nombres-complexes/PEDAGOGICAL_QUALITY_REPORT.json`
7. `showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT.json`
8. `showcase/student-v0.1/nombres-complexes/FACTORY_REVIEW_REQUEST.md`
9. `showcase/student-v0.1/nombres-complexes/AUTHOR_AUDIT.md`

No runtime, UI, schema, authoring tool, workflow, pilot, QA, governance or sibling Wave 2 path is mutated.

## Rollback

For a build-only rollback, reset the JOB06 branch to prepared head `88d8f8a0e5f4eaeede8eb6b2cb51156801b02f7e`. For full WP-035 rollback, close PR #408 and delete `student-v01/wave2-showcase-kit`. No product code or sibling Wave 2 branch requires reversal.
