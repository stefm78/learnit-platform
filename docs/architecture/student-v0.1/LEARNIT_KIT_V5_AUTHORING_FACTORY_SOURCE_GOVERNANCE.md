# Learn-it Kit V5 — Authoring, Factory and Source Governance (R2 Handoff 2)

Status: R2 pre-pilot candidate for ATLAS-WP-056 under GO_PRE_PILOT_V5.

## Boundary

This handoff adds an explicit V5 authoring/admission layer around the existing AI Kit Factory. It changes neither the frozen V5 contract/validator/tests nor V4, and it adds no learner runtime behavior.

The existing factory_gate.build_context remains the identity root. Exact kit bytes produce kitSha256; the canonical learner brief produces briefSha256; the sorted exact source inventory produces sourceSetDigest; those existing values produce contextDigest. The V5 adapter consumes these values and never computes a parallel identity.

## Role A learner references

Role A is optional learner-visible enrichment. The canonical learner object remains exactly {url,label,hook}; no provenance, status, hashes, timestamps, roles, redirects or authorization metadata enter the learner payload.

Every unique canonical Role A URL must have exactly one external PASS_V5_WEB_RESOURCE_ADMISSION_R1 record. Missing or extra/orphan evidence fails closed. A Role A change rotates exact kitSha256 and contextDigest, invalidating the previous review, but does not enter sourceSetDigest because Role A is not a source of canonical claims.

## Bounded Web admission and SSRF boundary

v5_web_admission.py admits one explicitly supplied HTTPS resource at authoring time. It forbids URL userinfo, follows at most five redirects, revalidates and re-resolves every hop, rejects loopback/private/link-local/multicast/unspecified/reserved destinations, and pins the TLS socket to an IP from the approved resolution set while preserving hostname SNI/Host. Connection/read time and response bytes are bounded. Authentication-required statuses, 404/410, executables and download-only resources HOLD.

There is no cookie flow, authentication prompt, recursive traversal, embedded-asset fetch, crawler, mirror, archive or permanent link monitor. Resolver and transport are injectable so qualification uses deterministic fixtures with no public Internet dependency.

## Role B authoring sources

Role B is every source whose content contributes material canonical claims. For V5, each existing Factory source binding must have explicit authorization, authorization basis, provenance, origin metadata, exact byte count/SHA-256 and at least one claim mapping. For Web origin, submitted/final HTTPS URLs and bounded Web-admission evidence are required before capture is used as a Factory source.

The V5 gate requires Role B IDs to equal the existing Factory source inventory and exact captures to match the bound source files. Because the existing sourceSetDigest hashes that inventory, changing one source byte rotates sourceSetDigest and contextDigest. Even after refreshing source evidence, the previous review target is stale.

Role B evidence remains authoring evidence and never enters learner references[].

## Hints and semantic review

The frozen V5 structure permits 0–3 ordered text hints. Zero is valid. authoring_policy.py blocks obvious direct canonical-answer leakage but explicitly does not claim semantic proof. SKILL_ATLAS_KIT_REVIEW_V2 requires a clean-context independent reviewer to explicitly pass hintProgression, hintAnswerLeak, roleAReferenceUsefulness and roleBClaimMapping in addition to the promoted six semantic dimensions.

A V5 semantic PASS therefore cannot be valid if the reviewer declares an answer leak. The deterministic policy also blocks obvious answer disclosure before semantic PASS can be considered.

## Explicit V5 Factory admission

v5_factory_gate.py requires the exact learnit.kit.v5 discriminator and calls the frozen V5 validator directly. It never rewrites the discriminator or strips V5 fields. After V5 canonical PASS, it reuses the unchanged common V4-family pedagogical diagnostics on the V5 object itself; this is diagnostic reuse, not V5-to-V4 conversion.

The V5 semantic review keeps the same target tuple: contextDigest, kitSha256, sourceSetDigest and briefSha256. Core six review dimensions are validated with the existing V1 semantics; the four V5 assertions are additional fail-closed checks.

## Preserved boundaries

No runtime/UI, Atlas hint reveal, learner-safe runtime projection, V8, 10C port/final showcase review, fan-in, merge, cherry-pick, promotion, ATLAS-WP-054 or student session is authorized here. Remote media remains forbidden by the unchanged V5/V4 media authority, and V2/V4 continue through their existing paths unchanged.
