# Dream Team Iterative Challenge — reusable decision pattern

Status: **reference / inspiration**, not a normative product contract.

This note preserves the decision method used after the first real EPF learner-use
pilot. It is intended to be reusable whenever Learn-it faces a cross-domain design
decision where product value, learning value, architecture, runtime constraints,
accessibility and complexity must be traded off explicitly.

The method is deliberately stronger than a simple "ask several experts for an
opinion". It requires independent criteria, independent scoring, explicit friction,
composite scoring, consensus, Linus/Steve arbitration, re-scoring and iteration
until further improvement becomes marginal.

## Why this pattern exists

The first EPF V1 pilot showed that the dominant problem was not factory quality but
learner usability. The same product state could be interpreted very differently
depending on whether the reviewer focused on pedagogy, runtime integrity,
interaction design or architectural simplicity.

A reusable process is useful when:

- several disciplines can legitimately disagree;
- a local fix may hide a deeper system problem;
- average scores could mask a catastrophic weak dimension;
- implementation cost and added complexity matter;
- human evidence exists and should dominate speculative design;
- the team wants convergence before repository changes.

## Core roles

The exact team may change with context. For the EPF learner-UX challenge, the
reference composition was:

- **Linus** — architecture, simplicity, anti-complexity, long-term coherence.
- **Steve** — product value, UX clarity, learner desirability.
- **Learning Expert** — active recall, feedback, transfer, cognitive load.
- **UX / Interaction** — visual hierarchy, navigation, task focus.
- **Runtime Engineer** — state, session lifecycle, history, feasibility.
- **Accessibility** — focus, keyboard, screen reader, cognitive accessibility.
- **Adversarial Reviewer** — hidden assumptions, false consensus, second-order risk.

Linus and Steve are both normal participants and explicit final arbitrators when
material friction remains.

## Reusable pseudocode

```text
ALGORITHM DREAM_TEAM_ITERATIVE_CHALLENGE

INPUT:
    CONTEXT
    CURRENT_CANDIDATE
    HARD_CONSTRAINTS
    MAX_ROUNDS
    MIN_IMPROVEMENT
    MAX_ACCEPTABLE_FRICTION

1. ASSEMBLE_TEAM()

2. ROUND_0_INDEPENDENT_CRITERIA()
   FOR EACH member:
       member.analyse(CONTEXT, CURRENT_CANDIDATE)
       member.propose_criteria = [
           criterion,
           why_it_matters,
           measurement_method,
           importance 0..1,
           critical true|false
       ]
       member.challenge = strongest assumption / biggest risk
       member.initial_recommendations = [...]
   END

3. BUILD_COMMON_SCORECARD()
   CANONICAL_CRITERIA =
       merge_semantically_equivalent(all proposed criteria)

   Reject criteria that exist only for implementation convenience
   and have no material user/system value.

   Normalize weights:
       SUM(weights) = 1.0

4. INDEPENDENT_EVALUATION()
   FOR EACH member:
       FOR EACH relevant criterion:
           score = 0..100
           confidence = 0..1
           evidence = observation / proof / reasoning
       END

       recommendations = ranked concrete changes
       challenge = "What would make this candidate fail?"
       vetoes = hard-constraint or catastrophic-risk violations only
   END

   Rule:
       first evaluation is independent;
       no member sees other members' scores beforehand.

5. SCORE_EACH_CRITERION()
   CRITERION_SCORE =
       weighted_average(
           member.score,
           weight = confidence * domain_relevance
       )

   DISAGREEMENT =
       dispersion(member.score)

6. COMPOSITE_SCORE()
   BASE_SCORE =
       weighted_geometric_mean(
           CRITERION_SCORE,
           criterion.weights
       )

   FRICTION_PENALTY =
       high_disagreement
       + unresolved_contradictions
       + complexity_growth
       + low_confidence

   IF any HARD_CONSTRAINT violated:
       COMPOSITE_SCORE = HOLD
   ELSE:
       COMPOSITE_SCORE = BASE_SCORE - FRICTION_PENALTY

   Important:
       do not use a simple arithmetic mean;
       critical weak dimensions must not be hidden by strong unrelated ones.

7. BUILD_FRICTION_MATRIX()
   Detect:
       high score dispersion
       mutually incompatible recommendations
       vetoes

   Classify:
       PRODUCT_VALUE
       ARCHITECTURE
       LEARNING
       UX
       IMPLEMENTATION
       ACCESSIBILITY
       CROSS_DOMAIN

8. ATTEMPT_CONSENSUS()
   Synthesize recommendations that:
       maximize composite score
       preserve hard constraints
       prefer Pareto improvements
       minimize added complexity
       remove marginal-value changes
       preserve unresolved disagreements explicitly

   IF friction acceptable:
       accept preliminary consensus
   ELSE:
       go to arbitration

9. LINUS_STEVE_ARBITRATION()
   FOR EACH unresolved material friction:

       LINUS returns:
           architecture score
           complexity cost
           long-term risk
           recommendation
           rationale

       STEVE returns:
           user-value score
           clarity score
           learning/product impact
           recommendation
           rationale

       IF Linus and Steve agree:
           accept direction

       ELSE IF mainly architecture/system:
           give stronger decision weight to Linus

       ELSE IF mainly product/UX:
           give stronger decision weight to Steve

       ELSE:
           construct explicit alternatives
           rescore alternatives with full team
           choose highest composite score
           subject to hard constraints
   END

10. BUILD_NEXT_CANDIDATE()
    NEXT_CANDIDATE =
        CURRENT_CANDIDATE
        + accepted recommendations
        + arbitration decisions
        - rejected complexity
        - rejected low-value changes

    DO NOT IMPLEMENT YET.

11. FULL_RESCORING()
    FOR EACH member:
        evaluate NEXT_CANDIDATE again
        produce new score
        new confidence
        new challenge
        remaining risks
        new recommendations
    END

12. CONVERGENCE_CHALLENGE()
    Ask every member:
        What improved?
        What got worse?
        What remains unnecessarily complex?
        What user problem remains unresolved?
        What are we keeping only because we already invested in it?
        What can we remove with equal or better score?

    ANTI_COMPLEXITY_PASS:
        FOR EACH proposed change:
            simulate removing it
            IF score remains approximately equal OR improves:
                remove it
        END

13. ITERATE()
    IMPROVEMENT =
        NEW_COMPOSITE_SCORE - PREVIOUS_COMPOSITE_SCORE

    IF:
        hard constraints satisfied
        AND material friction resolved
        AND score sufficiently high
        AND improvement < MIN_IMPROVEMENT
            for two consecutive rounds
    THEN:
        CONVERGED = true

    ELSE IF:
        round < MAX_ROUNDS
        AND meaningful improvement remains
    THEN:
        CURRENT_CANDIDATE = NEXT_CANDIDATE
        round += 1
        go to INDEPENDENT_EVALUATION

    ELSE:
        stop with explicit unresolved trade-offs

14. RETURN()
    return:
        canonical criteria + weights
        all member scores
        criterion scores
        composite score by round
        friction matrix
        challenges
        recommendations
        Linus arbitrations
        Steve arbitrations
        rejected recommendations
        remaining risks
        complexity added
        complexity removed
        final candidate
        stop reason

15. ONLY_THEN_IMPLEMENT()
    IF consensus says IMPLEMENT:
        derive smallest coherent implementation scope
        split into streams only when parallelism creates real value
    ELSE:
        do not touch repository
```

## Scoring principles

### Non-compensatory composite

Use a weighted geometric mean rather than a simple arithmetic mean.

A candidate with excellent architecture but unusable learner interaction must not
receive a deceptively strong overall score.

Hard constraints remain non-compensable gates.

### Confidence and domain relevance

A member's contribution to a criterion is weighted by both:

- confidence in the evidence;
- relevance of that member's discipline to the criterion.

This prevents every opinion from receiving equal weight on every dimension.

### Friction is data

Disagreement is not averaged away. High dispersion creates explicit friction and
can reduce the composite score until resolved.

### Anti-complexity is mandatory

Every round includes a removal pass.

The team asks not only "what should we add?" but also:

> What can we remove and keep the same or a better outcome?

This is essential to avoid iterative expert review becoming iterative feature
accretion.

## EPF first-use application of the method

The initial product score was approximately **37 / 100 — HOLD**.

The strongest evidence came from the real first-use interview and screenshots:

- a learner could see an unrelated course while answering another course;
- full progress panels could separate a question from its answer controls;
- "Aujourd'hui" and the local library both exposed competing learning-entry paths;
- internal product/factory vocabulary leaked into the learner interface;
- explanation after an incorrect answer was useful;
- 5/15/30-minute controls were understood;
- library detail and local renaming had potential value.

The challenge converged after four scoring rounds at approximately **91 / 100**.
The score is a decision aid, not an empirical usability metric.

### Root cause selected by consensus

**Two competing learning paths for Atlas content.**

Reference architecture:

```text
TODAY
  choose course / 5-15-30 min / resume
        |
        v
ONE ATLAS SESSION ENGINE
        |
        v
focused activity
  objective
  step
  question
  answer controls
  hint / validate
        |
        v
feedback
        |
        v
next activity or summary

LIBRARY
  manage courses
  inspect progress/history
  local rename
  continue learning
        |
        +------> SAME ATLAS SESSION ENGINE
```

The library remains useful. The second pedagogical runtime does not.

### Explicitly deferred

The Dream Team did **not** approve adding a new teaching/discovery mode based on
the first pilot alone.

That question requires evidence from a target learner.

### Explicitly rejected as premature

- new backend;
- new storage model;
- new kit schema;
- dashboard redesign;
- onboarding wizard;
- third learning runtime;
- broad rewrite of the kits;
- new QA programme solely for this UX repair.

## Work-organization rule learned from this challenge

Do not automatically parallelize code touching the same conceptual learner flow.

For this case the recommended sequence is:

```text
STREAM 1 — bounded UX/runtime implementation
    one owner
    one Atlas learning journey
    preserve state/history

then

STREAM 2 — learner observation
    no code
    same interview regression
    ideally one fresh target EPF learner

then, only if learner usability is no longer blocking

resume V1 -> V2 continuity experiment
```

This sequential split is intentional: implementation and observation are
independent responsibilities, but parallel implementation streams would increase
the risk of recreating divergent learning paths.

## Reuse guidance

For future Dream Team challenges:

1. reuse the **process**, not necessarily the EPF criteria;
2. let the team construct criteria from the actual evidence;
3. preserve hard constraints explicitly;
4. score independently before consensus;
5. keep friction visible;
6. use Linus and Steve only for material unresolved trade-offs;
7. rescore after arbitration;
8. run the anti-complexity pass every round;
9. stop when improvement becomes marginal;
10. implement only after convergence.

