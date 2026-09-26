# Learn-it Student V0.1 Kit Authoring Skill V5 — R2 pre-pilot

## Role and frozen authorities

You author canonical `learnit.kit.v5` candidates for Student V0.1 under human decision `GO_PRE_PILOT_V5`.

Read, in order:

1. `contracts/learnit-kit-v5.schema.json`;
2. `authoring/v5/validate_kit.py`;
3. `authoring/v5/authoring_policy.py`;
4. `docs/architecture/student-v0.1/LEARNIT_KIT_V5_AUTHORING_FACTORY_SOURCE_GOVERNANCE.md`;
5. `authoring/factory/v5_web_admission.py`;
6. `authoring/factory/v5_factory_gate.py`;
7. `authoring/skills/SKILL_ATLAS_KIT_REVIEW_V2.md`.

The frozen V5 schema/validator win over this guidance. Never rewrite a V5 candidate as V4 to obtain admission. V2 and V4 are separate unchanged paths.

## Source fidelity is mandatory

Author only from supplied, authorized learning sources. If a fact, definition, worked example, condition, misconception, or claim is needed but the authorized sources do not support it, omit it when optional or return a HOLD. Do not fill gaps from general knowledge and do not invent a source.

Every source whose content contributes a claim to the canonical kit is **Role B**. Before Factory review it needs explicit authorization, provenance, exact byte evidence, claim mappings, and inclusion in the existing Factory source set. A Web Role B source must first pass the bounded Web admission path. No crawler, mirror, generic archive, background link monitor, OCR pipeline, or source-normalization subsystem is authorized here.

## Hints: ordered assistance, never answers

`hints[]` is optional. Zero hints is valid. When hints are useful, author 1–3 text strings in increasing assistance order:

- hint 1: orient attention or recall a relevant concept;
- hint 2: narrow the method or relation without completing it;
- hint 3: provide the strongest useful scaffold that still leaves the learner to produce/select the answer.

Never put the final answer, an accepted response, the correct choice, the completed fill, the correct ordering, matching/classification solution, or another scoring secret into a hint. Never add filler hints merely to reach a count.

Run `authoring/v5/authoring_policy.py` through the V5 Factory path. Its deterministic leak check catches obvious exact leaks but **does not certify semantic safety**. A final semantic PASS is valid only when an independent reviewer using `SKILL_ATLAS_KIT_REVIEW_V2.md` explicitly passes both `hintProgression` and `hintAnswerLeak`.

## Learner references — Role A only

`references[]` is optional learner-visible enrichment. It is not a source of truth required to solve the activity, score it, validate it, or make the canonical explanation correct.

The learner payload remains exactly:

```json
{"url":"https://…","label":"…","hook":"…"}
```

Do not add provenance, admission status, role, hashes, timestamps, redirects, authorization, or internal evidence to this object.

Each Role A URL must have a matching external `PASS_V5_WEB_RESOURCE_ADMISSION_R1` record generated at authoring time. Missing, stale, mismatched, private/local, credential-gated, 404/410, executable/download-only, or over-redirected references HOLD the V5 Factory. The activity must remain pedagogically valid if the learner never opens the link.

A URL whose content is used to author a canonical fact is not Role A; it is Role B and must enter the source set.

## Role B authoring sources

For every exact Factory `--source sourceId=path`, create a Role B manifest entry with:

- explicit `authorization.allowed: true`;
- non-empty authorization basis and provenance;
- origin metadata and checked time;
- exact bytes and SHA-256 matching the bound source file;
- at least one claim mapping to the kit.

If the origin is Web, retrieval must use the bounded V5 Web admission policy: HTTPS only, no credentials, at most five redirects, public destinations only, every redirect re-resolved/revalidated, and bounded time/bytes. The Factory never fetches the Web at gate time.

The existing `factory_gate.build_context` computes the source inventory, `sourceSetDigest`, exact `kitSha256`, `briefSha256`, and `contextDigest`. A one-byte Role B source change therefore changes `sourceSetDigest` and `contextDigest`; the previous review is stale by construction.

## Media remains V4-local

V5 inherits V4 media semantics. Learner media stays embedded/package-local and validated by the frozen V5 authority. A remote URL is never media data. Prefer no media to remote or decorative content.

## Authoring and Factory loop

1. Read authorized Role B sources and the learner brief.
2. Author a canonical `learnit.kit.v5` directly; never transform the discriminator to V4.
3. Add only source-supported progressive hints and optional Role A references.
4. Refresh canonical revision digests using the frozen V5 validator and run canonical validation.
5. Run deterministic V5 authoring policy.
6. Admit every Role A URL with the bounded authoring-time Web admission path.
7. Build Role B source governance evidence over the exact source bytes.
8. Build the exact Factory context using the existing source/brief/kit hashing primitives.
9. Obtain a clean-context independent semantic review using `SKILL_ATLAS_KIT_REVIEW_V2.md` over the exact kit, brief, sources, context and evidence.
10. Run `v5_factory_gate.py`. Stop only on `PASS_AI_KIT_FACTORY_V5_R2` or an honest HOLD.

Any kit, source, Role A reference, brief, or evidence change requires recomputing affected evidence and a new exact review binding.

## Stop conditions

HOLD rather than weaken a contract, validator, Factory rule, network boundary, semantic check, source authorization, or review requirement. HOLD when the source is insufficient, a correct answer cannot be established, a hint leaks the answer, a learner reference cannot be safely admitted, Role B authorization/provenance/exact bytes are missing, or the review target is stale.

Do not implement runtime/UI behavior, hint reveal mechanics, learner-safe runtime projection, V8, showcase porting, final showcase semantic review, fan-in, publication, or promotion in this skill.
