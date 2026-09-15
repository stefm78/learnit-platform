# Student V0.1 Program Charter

- Program: `STUDENT-V0.1`
- Architecture authority: `ARC-WP-025`
- Owner issue: `#380`
- Architecture source baseline: `1e71271436fd4b7dd7d895cfec827833187630fe`
- Architecture contract candidate: `learnit.kit.v4`
- Status: `ARCHITECTURE_GATE_PENDING_HUMAN`
- Knowledge-assisted authoring: outside critical path

## Mission

Deliver the smallest advanced learner-facing successor candidate that can sustain one credible 30–45 minute learning journey and then be evaluated with 5–6 real students.

The program is deliberately narrower than a platform program. It does not authorize backend, accounts, synchronization, cloud catalog, remote model scoring, provider orchestration, marketplace, generic plug-ins or a runtime event bus.

## Product hypothesis under test

A coherent journey needs more than question/answer repetition. Student V0.1 should combine:

- structured exposition (`lesson`);
- active recall (`flashcard`);
- recognition (`qcm`);
- reconstruction (`fill`);
- relation building (`matching`);
- sequence reasoning (`order`);
- category discrimination (`classify`);
- bounded production (`constructed`);
- local, pedagogically justified media across those units.

The objective is not maximum activity count. It is enough cognitive variation to make a real learner session credible while preserving one canonical semantic/evaluation boundary.

## Frozen architecture gate

The program cannot begin implementation until all are true:

1. `ARC-WP-025` is human-accepted.
2. Its DRAFT PR is merged through repository governance.
3. the exact resulting `main` merge commit is recorded as the Wave 1 base.
4. `contracts/learnit-kit-v4.schema.json` is frozen on that base.
5. current open branches/PRs are checked for writable-path overlap.

The architecture gate does not itself authorize Wave 1.

## Execution model

```text
ARC-WP-025 human acceptance
        |
        v
exact architecture merge commit
        |
        +----------------+----------------+
        |                |                |
      JOB 01           JOB 02           JOB 03
 Learning/runtime     Presentation/UI   Authoring/Factory/quality
        |                |                |
        +-------- exact reviewed results -+
                         |
                       JOB 04
                  FAN-IN A / no repair
                         |
        +----------------+----------------+
        |                |                |
      JOB 05           JOB 06           JOB 07
contradictory QA   real showcase kit   pilot packaging/UX
        |                |                |
        +-------- exact reviewed results -+
                         |
                       JOB 08
               FAN-IN B + qualification
                         |
                       JOB 09
          human replay / readiness gate
                         |
                  only if accepted
                         |
                 5–6 student sessions
```

Maximum parallelism is three workers. Every parallel worker starts from one exact common base and has a disjoint writable path set.

## Wave 1 exit criteria

JOB 01–03 are not considered complete merely because commits exist. Each must provide:

- exact base and result commit;
- changed-path list proving scope;
- machine tests relevant to its responsibility;
- claims separated from evidence;
- limitations and rollback;
- no generated artifact committed unless its work package explicitly makes that artifact authoritative.

JOB 04 accepts only exact reviewed results. It may wire shared integration files but may not silently repair worker-owned code.

Fan-in A must prove:

- v2/v3 behavior remains green;
- v4 admission is explicit and fail-closed;
- all eight presentation/response families cross the learner-safe boundary correctly;
- hidden solutions remain outside UI;
- local media is fail-closed;
- deterministic build/provenance is restored on the exact integrated head.

## Wave 2 exit criteria

JOB 05 performs contradictory QA against exact Fan-in A, including negative secret-boundary, schema, media and persistence/regression probes.

JOB 06 produces a real Student V0.1 showcase kit whose pedagogical sequence exercises the frozen grammar without manufacturing variety for its own sake.

JOB 07 prepares the bounded pilot-facing UX/package: clear launch, session expectations, local-only constraints, feedback collection and replay instructions. It does not create accounts or telemetry infrastructure.

JOB 08 integrates exact accepted Wave 2 results and runs the full qualification oracle on one exact candidate head.

## Human gate and student boundary

JOB 09 is a real human replay/readiness gate, not a formality. It must determine whether:

- the journey is understandable without developer explanation;
- lesson -> active practice -> feedback -> consolidation/transfer feels coherent;
- controls for matching/order/classify/constructed are usable;
- local media helps rather than distracts;
- non-scored lesson/flashcard completion is not misrepresented as learning success;
- no blocking defect or misleading learning claim remains.

Only a separate explicit acceptance after JOB 09 may authorize the first 5–6 student sessions.

## Stop conditions

Stop and return to the smallest affected gate if any occurs:

- v2 or v3 meaning changes;
- the v4 contract must change after Wave 1 starts;
- two parallel workers need the same writable file;
- a scoring secret reaches learner-safe presentation;
- lesson/flashcard begins contributing correctness/mastery evidence;
- media needs remote network dependencies;
- a generic runtime/plugin/evaluator framework is introduced to solve a local need;
- implementation requires backend/accounts/provider/runtime AI;
- Fan-in requires silent repair rather than returning a defect to its owner;
- current base identity becomes stale before mutation/integration.

## Success definition

Student V0.1 succeeds when one exact qualified local/static candidate is human-accepted for a small pilot and the subsequent 5–6 sessions produce actionable learner evidence.

It does not need to prove a platform architecture, long-term retention, generalized mastery, remote distribution or production-scale operations.
