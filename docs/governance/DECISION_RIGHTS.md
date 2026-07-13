# Decision rights

## Roles

| Role | Accountable for |
|---|---|
| Repository owner | product direction, business priorities, final strategic arbitration, exceptional override |
| Architecture & Repository Governor | architecture frame, phase gates, work-package admissibility, repository integrity, evidence discipline |
| Integrator | branch convergence, conflict resolution, final PR coherence, reproducible integration |
| Implementer | bounded implementation within the approved work package |
| Independent QA | adverse tests, regression proof, provenance challenge |
| Security reviewer | authorization, tenancy, secrets, privacy, abuse and recovery controls |
| Learning reviewer | evidence semantics, mastery claims, learning quality and ethical analytics |
| Product/UX reviewer | learner comprehension, interaction quality and human gates |

## Decision matrix

| Decision | Proposes | Governor | Owner | Independent review |
|---|---|---|---|---|
| Local reversible fix | Implementer | checks scope | informed | QA as risk requires |
| Work package approval | Architect/integrator | approves or blocks | informed; arbitrates dispute | QA or specialist by risk |
| Shared contract change | Architect | approval required | arbitrates strategic impact | consumers + QA |
| Data migration | Implementer/architect | approval required | informed | independent QA mandatory |
| Architecture exception | Requester | recommends with expiry | approval required for high/critical | specialist as applicable |
| Phase transition | Governor/architect | recommends | approval required | independent evidence review |
| Release-candidate promotion | Integrator | gate decision | approval for promoted baseline | QA + human gate |
| Backend topology | Architect | recommends | approval required | operations/security |
| Commerce or marketplace activation | Product/architect | HOLD/GO recommendation | approval required | security, legal/ops, QA |
| Emergency rollback | Integrator or governor | may require immediate rollback | notified immediately | post-incident review |

## Override policy

The repository owner may override a governor decision only through a recorded decision containing:

- decision being overridden;
- reason;
- accepted risk;
- duration;
- owner;
- rollback or expiry condition;
- required follow-up evidence.

An override cannot silently change the architecture constitution or erase evidence. Critical security, privacy, or data-integrity risk must remain visible until closed.

## Governor independence

The governor must not be the sole reviewer when it also authored the implementation, migration, workflow, or contract under review. In that case, an independent QA or specialist review is mandatory.

## Dispute resolution

1. Reconstruct the exact artifact and evidence.
2. Separate facts, claims, assumptions, and missing proof.
3. State the constitution rule or roadmap gate involved.
4. Attempt a reversible experiment or counterexample.
5. Governor issues a recommendation.
6. Repository owner arbitrates unresolved strategic or risk-acceptance disputes.
7. Record the outcome in an ADR, work package, exception, or governor review.
