# M3.1 Pedagogical Quality Engine — design freeze candidate

## 1. Mandate

M3.1 adds one reusable quality-control layer above the promoted M3.0 Authoring Foundation.

The product outcome is:

```text
candidate learnit.kit.v2
→ frozen canonical validation
→ deterministic pedagogical-quality analysis
→ actionable machine-readable report
→ human or AI correction
→ rerun
```

The same report is consumable by:

- a command-line process in an AI sandbox;
- CI;
- the Authoring Studio.

M3.1 does not ingest documents and does not add an LLM to the product. An external AI may use the versioned authoring skill to create or improve a candidate kit, but the quality engine itself is local, deterministic, read-only and network-free.

## 2. Evidence and authority

Current normative authorities remain unchanged:

- `contracts/learnit-kit-v2.schema.json`;
- `authoring/v2/validate_kit.py`;
- `authoring/v2/atlas/validate_atlas_content.py`;
- the promoted M3.0 Authoring Foundation;
- the two canonical Atlas proof kits.

Legacy authoring-pack V13.2 was reviewed as design evidence only:

- archive SHA-256: `339d5b32f2ac7d00b21300e8cba58f69a3c00afb8af520cdadbc97870a3c8116`;
- V13.2 skill SHA-256: `67fa114ce213c472953ad4da39e7756d7a8a059128c7ac8bd66440542a38c8f1`;
- V13.2 validator SHA-256: `25984b8f1707c2f3dac4d91446fa514db66eec1040d4779059876c6832d751ff`;
- V13.2 alignment script SHA-256: `d0a26d97b458c45a8dffcb469b613ddb55b20dd4be92b32af2b9a6597ab6d83f`.

That pack targets `learnit.import.v1.1` / RC687. It is not copied into Atlas and cannot widen `learnit.kit.v2`.

## 3. Architecture decision

### 3.1 One quality engine

M3.1 introduces one pure Python module:

`authoring/v2/atlas/pedagogical_quality.py`

It is both:

- an importable library;
- a CLI entry point.

It has no storage writes, network calls, clock dependency, random dependency or learner-state dependency.

For a given input kit and quality-engine version it returns exactly the same report bytes when canonical JSON serialization is requested.

### 3.2 Canonical validation remains upstream

The quality engine must not reimplement the JSON Schema, general v2 validator or Atlas editorial validator.

Processing order is fail-closed:

1. parse the candidate kit;
2. execute the frozen canonical validators;
3. if canonical validation fails, return `HOLD_CANONICAL_INVALID` and no positive pedagogical-quality verdict;
4. only on canonical PASS, evaluate M3.1 quality rules.

Canonical validity and pedagogical quality remain distinct concepts.

### 3.3 No second browser semantic engine

The Studio uses the Python quality engine through the existing Python authoring core.

GitHub Pages continues to execute Python in-browser through the existing Pyodide boundary. The Pages adapter copies the exact M3.1 Python module into the browser authority bundle; JavaScript renders reports but does not decide pedagogical validity.

## 4. Report contract

The machine-readable report schema is:

`learnit.atlas.pedagogical_quality_report.v1`

Minimum shape:

```json
{
  "schema": "learnit.atlas.pedagogical_quality_report.v1",
  "profile": "atlas.pedagogy.v1",
  "canonicalValid": true,
  "verdict": "PASS_ATLAS_PEDAGOGICAL_PROFILE_V1",
  "qualityBand": "EXCELLENT_BY_PROFILE",
  "counts": {
    "blocking": 0,
    "warning": 0,
    "advice": 0
  },
  "diagnostics": [],
  "courses": [],
  "objectives": []
}
```

Every diagnostic contains:

- stable `code`;
- `severity`: `blocking`, `warning` or `advice`;
- JSON `path`;
- affected package/course/objective/activity references when available;
- `cause`;
- `impact`;
- `fix`;
- optional deterministic `evidence`.

Diagnostic ordering is deterministic: severity, path, code.

## 5. Verdict and quality-band semantics

### 5.1 Export validity

Only canonical/integrity blocking diagnostics disable M3 export.

M3.1 warnings and advice do not silently redefine the `learnit.kit.v2` contract.

### 5.2 Profile verdict

- `HOLD_CANONICAL_INVALID`: canonical validators reject the kit.
- `PASS_ATLAS_PEDAGOGICAL_PROFILE_V1`: canonical validators pass and no M3.1 profile blocker exists.

M3.1 initially introduces no new profile blocker beyond canonical validity. This prevents a quality heuristic from becoming an implicit contract revision.

### 5.3 Quality band

The non-numeric quality band is:

- `BLOCKED`: canonical invalid;
- `COMPLETE`: profile pass with one or more warnings;
- `STRONG`: profile pass, zero warnings, one or more advice items;
- `EXCELLENT_BY_PROFILE`: profile pass, zero warnings, zero advice.

`EXCELLENT_BY_PROFILE` means only that the static kit satisfies the deterministic Atlas authoring profile. It is not evidence of learner mastery, retention, teaching effectiveness or certification.

No scalar 0–100 score is a release authority in M3.1.

## 6. Atlas pedagogical-quality rules v1

The current Atlas canonical profile already requires, per objective, the ordered execution classes:

```text
practice → correction → validation → validation → transfer
```

and exactly two independence claims per objective. The frozen Atlas claim topology used by both canonical proof kits is:

```text
first practice → first validation
first validation → second validation
```

M3.1 must not invent a third validation→transfer claim: the canonical Atlas authority requires exactly two claims. Transfer quality is assessed through the existing transfer activity plus deterministic non-claim diagnostics.

M3.1 adds diagnostics that are deterministic but not contract-defining.

### 6.1 Warning rules

`PQ_COURSE_DURATION_MISMATCH`

The course `estimatedMinutes` must equal the sum of its authored activity `estimatedMinutes`.

`PQ_OBJECTIVE_DUPLICATE_STIMULUS`

Two activities for the same objective must not have identical normalized Atlas stimulus digests.

`PQ_TRANSFER_NOT_HARDER`

The transfer activity should have a difficulty rank greater than the first practice activity. Rank is exactly:

`easy < medium < advanced < expert`.

`PQ_VALIDATION_CHAIN_WEAK`

The existing two-claim chain should match the frozen Atlas topology exactly:

1. first practice → first validation, with basis `new-instance` or `alternate-representation`;
2. first validation → second validation, with basis `new-context` or `alternate-representation`.

No direct transfer claim is expected or permitted by this quality rule. A missing or differently connected two-claim chain is a warning, not a reason to expand the canonical claim count.

### 6.2 Advice rules

`PQ_OBJECTIVE_SINGLE_ACTIVITY_TYPE`

All five objective activities use the same interaction type. At least two supported interaction types are preferred where the subject matter permits it.

`PQ_VALIDATIONS_SAME_ACTIVITY_TYPE`

Both independent validations use the same interaction type. A different type is preferred when it tests the objective without changing the objective itself.

`PQ_NO_ALTERNATE_REPRESENTATION`

Neither of the two existing validation-independence claims uses `alternate-representation`. This is advisory only because not every objective benefits from a representation change.

These rules deliberately avoid semantic judgments that deterministic static analysis cannot prove, such as whether a distractor is intellectually plausible, an explanation is scientifically correct, or a transfer situation is genuinely meaningful beyond the declared and hashed stimulus relation.

## 7. Legacy V13.2 mapping

Relevant legacy concepts are treated as follows.

| V13.2 concept | Atlas M3.1 decision |
| --- | --- |
| objective coverage | retained through canonical objective/activity references and profile reporting |
| at least two activities per objective | superseded by Atlas exact five-class objective profile |
| validation required | retained and strengthened by two independent validations |
| transfer recommended | retained and already canonical in Atlas |
| remediation activity/role | not copied; Atlas correction is the current bounded remediation mechanism |
| `common_errors[]` | not copied; absent from `learnit.kit.v2` |
| flashcard/matching/order | not copied; M3.1 keeps only current `qcm` and `fill` contract |
| media/assets | not copied; absent from current Atlas contract |
| question duplicate detection | retained as deterministic stimulus-identity warning |
| format variety | retained as advice only |
| source field / generation report | kept outside canonical kit; traceable source ingestion belongs to M3.2 |
| scalar pedagogical score | rejected as release authority |
| machine-readable diagnostics | retained and strengthened |

## 8. AI sandbox contract

CLI:

```text
python -B authoring/v2/atlas/pedagogical_quality.py KIT.json
python -B authoring/v2/atlas/pedagogical_quality.py KIT.json --json
python -B authoring/v2/atlas/pedagogical_quality.py KIT.json --require-excellent
```

Behavior:

- default: human-readable compact report plus exit code;
- `--json`: canonical machine-readable report on stdout;
- `--require-excellent`: exit non-zero unless `qualityBand == EXCELLENT_BY_PROFILE`.

Exit codes:

- `0`: requested gate passed;
- `2`: canonical invalid;
- `3`: canonical valid but `--require-excellent` not reached;
- `4`: input/read/encoding failure.

No command edits the kit.

### 8.1 AI self-iteration protocol

The repository authoring skill instructs an AI to:

1. generate or modify one candidate `learnit.kit.v2`;
2. run canonical validation;
3. run the quality engine with `--json --require-excellent`;
4. repair only diagnostics supported by the source material and Atlas rules;
5. rerun;
6. stop when `EXCELLENT_BY_PROFILE`, or stop and report an unresolved conflict rather than invent unsupported content.

The skill must explicitly forbid changing facts solely to satisfy a metric.

An iteration cap is guidance, not an engine behavior. The engine never loops by itself.

## 9. Studio integration

The existing `validate_draft()` response gains a distinct pedagogical-quality section after canonical PASS.

The UI shows three clearly separated states:

- canonical validity;
- pedagogical completeness/strength;
- export availability.

A quality warning never masquerades as a canonical error.

The author sees the diagnostic cause, impact and suggested correction at the relevant objective/activity.

M3.1 does not add structural creation, deletion or reorder capability. If a diagnostic requires a structural change unavailable in M3.0, the Studio may explain that limitation; it must not perform a hidden structural edit.

## 10. Atlas authoring skill

M3.1 versions an Atlas-specific skill in the repository:

`authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V1.md`

It is a re-authored Atlas skill, not a renamed copy of V13.2.

It must:

- target only `learnit.kit.v2`;
- use only current qcm/fill activity families;
- follow the Atlas five-class objective profile;
- treat lineage IDs, revision IDs, digests and independence claims as canonical fields subject to validators;
- call the quality-engine CLI before delivery;
- require all canonical blockers fixed;
- prefer `EXCELLENT_BY_PROFILE` before delivery;
- preserve source fidelity and stop rather than invent unsupported teaching content;
- avoid source provenance fields not present in the contract;
- contain the V13.2 evidence hashes in a provenance note.

The skill is authoring/development guidance. It is not loaded by the learner runtime.

## 11. Implementation package freeze

After design acceptance, product implementation is `ATLAS-WP-012`.

Exact product writable paths:

- `work-packages/ATLAS-WP-012.json`
- `authoring/v2/atlas/pedagogical_quality.py`
- `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V1.md`
- `authoring/studio/core.py`
- `authoring/studio/web/index.html`
- `authoring/studio/web/studio.css`
- `authoring/studio/web/studio.js`
- `authoring/studio/pages/build_pages.py`
- `authoring/studio/pages/pages-bootstrap.js`
- `authoring/studio/tests/test_m3_1_pedagogical_quality.py`
- `.github/workflows/atlas-m3-1-pedagogical-quality-ci.yml`

Everything else is read-only, including:

- `contracts/**`;
- existing `authoring/v2/validate_kit.py`;
- existing `authoring/v2/atlas/validate_atlas_content.py`;
- canonical proof kits;
- learner runtime and source manifest;
- M3.0 QA files.

## 12. Independent QA freeze

Independent QA is `QA-WP-021`.

Exact QA writable paths:

- `work-packages/QA-WP-021.json`
- `authoring/studio/tests/qa_m3_1_pedagogical_quality.py`
- `.github/workflows/atlas-m3-1-pedagogical-quality-qa.yml`

QA may read the V13.2 evidence and the accepted design but must build its own contradictory cases.

QA never repairs product files.

Final QA binds one exact frozen ATLAS-WP-012 HEAD.

## 13. Required product evidence

Implementation CI must prove at minimum:

1. both canonical Atlas proof kits still pass unchanged canonical validators;
2. the engine returns deterministic report bytes for identical input;
3. canonical-invalid input never produces a positive profile verdict;
4. each warning/advice rule is independently triggered by a controlled mutation, including adversarial proof that no M3.1 rule requires a third independence claim;
5. diagnostic ordering and paths are deterministic;
6. `--require-excellent` exit codes match the report;
7. the quality engine never writes its input;
8. no network call is made;
9. the Studio consumes the Python report and does not reproduce rules in JavaScript;
10. Pages bundles the exact quality-engine Python source;
11. local Studio and Pages return equivalent reports for the exact same draft;
12. the Atlas authoring skill names the exact CLI and current contract only;
13. learner regressions and the exact promoted learner artifact remain unchanged.

## 14. Human gate

M3.1 requires a short author-facing desktop gate only after exact-head independent QA and a candidate Pages deployment.

Human flow:

1. open a canonical kit;
2. inspect an existing quality diagnostic or a controlled quality-warning candidate;
3. understand what is wrong without reading JSON;
4. make an allowed edit when possible;
5. observe the quality report update;
6. confirm the distinction between canonical error and quality recommendation is clear.

The CLI/AI-loop semantics do not require a separate human gate if QA proves exact behavior.

## 15. Non-goals

M3.1 explicitly excludes:

- PDF/text/Markdown ingestion as product functionality;
- source-provenance contract fields;
- LLM calls inside Studio or learner runtime;
- automatic kit publication;
- new activity families;
- schema revision;
- structural add/delete/reorder;
- media authoring;
- learner-state or recommendation changes;
- backend, accounts, synchronization;
- Gate3, Gate4 or M4+.

## 16. Rollback

M3.1 is additive except for bounded Studio/Pages wiring.

Rollback removes the quality module, Atlas authoring skill, M3.1 UI/report wiring and dedicated workflow, restoring the promoted M3.0 authoring behavior.

No learner data, learner runtime, canonical kit or schema migration is involved.

## 17. Claim-topology correction

A pre-implementation adversarial review found that the original frozen draft incorrectly expected a validation→transfer independence claim. That was incompatible with the canonical validator's exact two-claim count and with both canonical proof kits.

Correction authority: issue #262.

The correction preserves the canonical validator and proof kits unchanged. M3.1 evaluates only the existing two-claim topology and does not create a quality requirement that would force a contract/editorial-authority change.

## 18. Design verdict

If this design and ATLAS-WP-011 are accepted:

`PASS_M3_1_PEDAGOGICAL_QUALITY_ENGINE_DESIGN_TO_IMPLEMENTATION_GATE`

This authorizes the bounded ATLAS-WP-012 implementation only. It does not authorize promotion, M3.2, M3.3, Gate3, Gate4 or M4+.
