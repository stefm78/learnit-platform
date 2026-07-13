# Architecture constitution

Status: challenged target reference. A rule becomes enforceable only when repository policy, code, or tests execute it.

## 1. Product foundation

1. The learner experience MUST remain usable offline for installed content.
2. Cloud capabilities MUST extend the local player, not replace it.
3. Commerce MUST remain subordinate to learning; the store is not the learner home screen.
4. An account MUST NOT become a mandatory wall before the learner obtains local value, unless a future institutional policy explicitly requires it.

## 2. Evolution strategy

1. The standalone version MUST be promoted and forensically baselined before transversal architectural refactoring.
2. Migration MUST proceed through small seams with behavioral equivalence and rollback.
3. The first backend MUST be a modular monolith.
4. A module MAY be extracted as a service only after a documented need for independent deployment, scaling, security boundary, or ownership.
5. Future directories and services MUST NOT be created merely to mirror a target diagram.

## 3. Domain boundaries

1. A datum MUST have one owning module.
2. Modules MUST communicate through declared interfaces, commands, queries, or events.
3. A module MUST NOT modify another module's tables or internal repository directly.
4. Cross-module transactions MUST have an explicit owner and failure model.
5. Shared code MUST remain minimal and domain-neutral.

## 4. Dependency direction

1. Domain code MUST NOT depend on UI frameworks, DOM APIs, IndexedDB, localStorage, HTTP, payment SDKs, or cloud-vendor SDKs.
2. UI code MUST NOT access persistence or remote APIs directly.
3. Adapters MAY depend on domain ports; domain code MUST NOT depend on adapters.
4. Cyclic module dependencies are prohibited.
5. Dependency exceptions require an ADR and an executable architecture test where practical.

## 5. Identity and versioning

1. Canonical identifiers MUST be opaque, stable, and independent of titles or display labels.
2. Published identifiers MUST NOT be reused for a different semantic entity.
3. Content lineage MUST distinguish package, package version, course, objective, activity, and activity revision.
4. A change in pedagogical meaning MUST create a new revision or compatibility decision.
5. Contract changes MUST be versioned; existing fields MUST NOT be silently reinterpreted.

## 6. Learning evidence

1. Raw learning facts, calculated interpretations, and recommendations MUST be stored and reasoned about separately.
2. Learning events intended for synchronization MUST be immutable and idempotent.
3. Projections and mastery states MUST be reconstructible from facts and an identified algorithm version.
4. A trace of activity MUST NOT be presented as proof of cognitive mastery without stated limitations.
5. Private and institution-assigned learning evidence MUST remain separable.

## 7. Local-first persistence and synchronization

1. Local persistence MUST support atomic write of a learning event and its outbound synchronization intent.
2. Synchronization MUST tolerate duplicate delivery, reordering, retries, network partition, device clock error, and stale clients.
3. Global mutable snapshots MUST NOT be used as the sole synchronization unit.
4. A server-received time MUST remain distinct from client-observed time.
5. No learning attempt may be lost or counted twice under tested failure scenarios.

## 8. Security and privacy

1. The system MUST separate account, learner profile, organization, device, and entitlement identities.
2. Tenant isolation MUST be tested negatively, not inferred from configuration.
3. Authors and publishers MUST NOT gain learner-data access merely because their content is installed.
4. Real learner data, credentials, or production exports MUST NOT enter source control.
5. Data export, correction, deletion, retention, and audit procedures MUST exist before a multi-user pilot.

## 9. Quality and provenance

1. The reviewed source MUST produce the tested artifact.
2. The tested artifact MUST be the published artifact.
3. A manifest MUST reject undeclared extra files as well as missing or modified files.
4. Build, test, contract, migration, and artifact identities MUST be recorded for releases.
5. Human gates remain mandatory for UX, accessibility, learning interpretation, and other behavior that automation does not prove.

## 10. Parallel AI engineering

1. Every implementation task MUST reference an exact base commit and canonical work package.
2. Allowed and forbidden paths MUST be machine-checkable.
3. Agents MUST work in isolated branches and working directories.
4. The implementation agent MUST NOT be the sole certifier.
5. Shared contracts MUST be frozen or explicitly coordinated before parallel implementation.
6. Integration MUST be owned by a designated integrator.
7. A task that exceeds its scope MUST stop and request a work-package amendment.

## 11. Source of truth

1. Each normative artifact MUST have one editable canonical representation.
2. Markdown views, indexes, GitHub issues, generated documentation, and API fragments SHOULD be derived from the canonical source.
3. Contradictory hand-maintained representations are prohibited.
4. Current implementation evidence takes precedence over aspirational documentation when determining what exists.

## 12. Decision discipline

1. Significant irreversible or cross-cutting choices require an ADR.
2. Claims, assumptions, evidence, and absence of evidence MUST be distinguished.
3. A green test proves only the behavior and environment it actually exercised.
4. Missing proof MUST NOT be converted into confidence by repetition.
