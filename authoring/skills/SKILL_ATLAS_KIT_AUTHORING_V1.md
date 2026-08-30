# Learn-it Atlas Kit Authoring Skill V1

## Purpose

Use this skill when an AI or human author must turn supplied learning material into a candidate Atlas kit for Learn-it.

The output contract is **only** `learnit.kit.v2`. The skill does not change the learner runtime, does not call a remote service, and does not publish a kit automatically.

The governing rule is:

> Source fidelity first. A quality metric never authorizes invented facts.

If the supplied material does not support a required pedagogical element, stop and report the gap instead of fabricating content.

## Authorities to read first

Before authoring, inspect the current repository versions of:

- `contracts/learnit-kit-v2.schema.json`
- `authoring/v2/validate_kit.py`
- `authoring/v2/atlas/validate_atlas_content.py`
- `authoring/v2/atlas/pedagogical_quality.py`
- `authoring/v2/atlas/nombres_complexes_atlas.json`
- `authoring/v2/atlas/signaux_electriques_atlas.json`

The schema and validators are authoritative. This skill is guidance around them, not a competing contract.

## Supported scope

Atlas V1 authoring uses only the activity families already present in the contract:

- `qcm`
- `fill`

Do not add a new activity type, source-provenance field, media field, runtime-AI field, account field, publication field, or any other property not authorized by the current schema.

## Source handling

1. Read the supplied documents completely enough to identify the concepts that must actually be learned.
2. Keep an **external working source map** in your own notes: source section/page → proposed objective/content.
3. Do not put that source map into the canonical kit unless a later contract explicitly provides a place for it.
4. Distinguish:
   - facts explicitly supported by the source;
   - pedagogical reformulations that preserve those facts;
   - unresolved ambiguities.
5. Never resolve an ambiguity by silently inventing domain content.

## Objective design

Create objectives that are observable and testable. Prefer one cognitive target per objective.

For each objective, the current Atlas profile requires exactly five activity classes in authored order:

1. **practice** — normally `application / practice`
2. **correction** — `consolidation / practice`, explicitly addressing a plausible error or misconception
3. **validation 1** — `validation / validation`
4. **validation 2** — `validation / validation`
5. **transfer** — `transfer / practice`

The two validation activities must test the same objective with distinct stimuli.

The transfer must reuse the underlying knowledge in a changed situation, not merely repeat a validation question with different numbers or labels.

Default calibration when the source supports it:

- first practice: `medium`
- correction: `medium`
- validations: `medium`
- transfer: `advanced`

The deterministic quality engine expects transfer difficulty to be greater than the first practice difficulty.

## Interaction variety

Use both `qcm` and `fill` when doing so tests the same objective naturally.

Do not force variety when it distorts the content. The quality engine may return an advisory rather than a blocker; source fidelity wins over an advisory.

For QCM:

- one unambiguously correct answer;
- distractors should represent plausible mistakes when the source supports them;
- avoid clues caused by wording length or grammar;
- explanations must explain why the correct operation or concept is correct.

For fill:

- preserve meaningful surrounding context;
- tokens must be unambiguous in the intended slots;
- `maxUses` must reflect actual required uses;
- answer mappings must be complete.

## Independence claims

Each objective has **exactly two** Atlas independence claims. Do not create a third claim for transfer.

The expected topology is:

1. first practice → first validation
2. first validation → second validation

Use a truthful `basisCode`:

- `new-instance` when the same representation is applied to a genuinely new instance;
- `new-context` when the second validation changes the context;
- `alternate-representation` only when the representation is genuinely different.

Do not label something `alternate-representation` merely to obtain a better quality band.

## Identity and derived fields

For a newly authored kit, create fresh UUIDv4 values wherever the current schema/golden kits require lineage, revision, objective, activity, choice, slot or token identities.

Treat these as canonical/derived fields, not prose to optimize manually:

- revision digests;
- stimulus digests;
- claim IDs;
- independence-claim stimulus digests.

For a new candidate, initialize revision digest fields to the canonical zero digest before deriving them:

`sha256:0000000000000000000000000000000000000000000000000000000000000000`

Then use the repository authorities to rewrite claims and fill revision digests. A sandbox helper may use the existing Python functions, for example:

```python
import json
from pathlib import Path
from authoring.v2 import validate_kit as v2
from authoring.v2.atlas import validate_atlas_content as atlas

path = Path("candidate.json")
package = json.loads(path.read_text(encoding="utf-8"))
atlas.rewrite_claims(package)
errors = v2.fill_new_digests(package)
if errors:
    raise SystemExit("\n".join(errors))
path.write_text(
    json.dumps(package, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
```

This helper does not replace validation. Run the validators afterwards.

## Mandatory validation loop

Run these commands from the repository root:

```bash
python -B authoring/v2/validate_kit.py candidate.json
python -B authoring/v2/atlas/validate_atlas_content.py
python -B authoring/v2/atlas/pedagogical_quality.py candidate.json --json
python -B authoring/v2/atlas/pedagogical_quality.py candidate.json --json --require-excellent
```

The Atlas validator CLI without arguments validates the two repository proof kits. For an arbitrary candidate, also import and call `validate_package(candidate)` from `authoring/v2/atlas/validate_atlas_content.py`, or use the M3.1 quality engine, which invokes both canonical authorities on the supplied candidate before producing any positive profile verdict.

Interpret the quality result as follows:

- `BLOCKED`: canonical validation failed;
- `COMPLETE`: canonical PASS, but one or more deterministic warnings remain;
- `STRONG`: zero warnings, advisory improvements remain;
- `EXCELLENT_BY_PROFILE`: zero warnings and zero advisories.

`EXCELLENT_BY_PROFILE` describes a static kit against the deterministic authoring profile. It does **not** prove learner mastery, retention, teaching effectiveness, or certification.

## AI self-iteration protocol

When operating in a sandbox:

1. Author one candidate from the supplied source.
2. Derive canonical claims/digests.
3. Run canonical validation.
4. Run `pedagogical_quality.py --json --require-excellent`.
5. Read each diagnostic's `code`, `path`, `cause`, `impact`, and `fix`.
6. Correct only what is justified by the source and current Atlas rules.
7. Regenerate affected claims/digests.
8. Rerun the validators and quality engine.
9. Continue until:
   - `EXCELLENT_BY_PROFILE`; or
   - a remaining warning/advice cannot be resolved without unsupported invention or an unauthorized contract change.
10. In the second case, stop and report the unresolved diagnostic and why it must remain.

Never modify the validators, schema, golden kits, or quality engine to make a candidate pass.

## Delivery checklist

Before delivery:

- contract is `learnit.kit.v2`;
- only currently supported activity types are used;
- every objective follows the five-class Atlas profile;
- each objective has exactly two claims with the expected topology;
- canonical validation passes;
- revision/claim/stimulus digests are current;
- the quality report is attached or summarized;
- unresolved advisories are explicit;
- no unsupported fact was introduced to satisfy a metric.

## Provenance of this skill

This Atlas skill was re-authored from current Atlas authorities after reviewing the earlier Learn-it authoring-pack V13.2 as historical design evidence.

Evidence hashes:

- authoring pack archive SHA-256: `339d5b32f2ac7d00b21300e8cba58f69a3c00afb8af520cdadbc97870a3c8116`
- historical skill SHA-256: `67fa114ce213c472953ad4da39e7756d7a8a059128c7ac8bd66440542a38c8f1`
- historical validator SHA-256: `25984b8f1707c2f3dac4d91446fa514db66eec1040d4779059876c6832d751ff`
- historical alignment helper SHA-256: `d0a26d97b458c45a8dffcb469b613ddb55b20dd4be92b32af2b9a6597ab6d83f`

Those historical artifacts are evidence only. Current repository contracts and validators override them.
