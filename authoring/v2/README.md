# Learn-it v2 authoring foundation

This directory is the bounded `KIT-WP-001` authoring surface for the frozen `learnit.kit.v2` contract.

- Exact execution base: `d0186d7c0d65d44287c59534855ea90ffa3f8d06`
- Writable files: the five paths assigned to the authoring agent only
- Activity families: `qcm` and `fill` only
- Golden kits: representative foundation fixtures, not complete curricula
- Player acceptance: not claimed; integration is deferred to `INT-WP-001`

## Requirements

- Python 3.11 or later
- `jsonschema` 4.18 or later for Draft 2020-12 structural validation
- The frozen schema at `contracts/learnit-kit-v2.schema.json`

No build, runtime converter, RC718 compatibility layer, learner-state migration or generated release artifact is produced here.

## Persistent identity workflow

Canonical IDs are lowercase UUID version 4 values allocated once and persisted in the authored JSON. They are never derived from titles, text, positions, filenames, paths or digests.

`generate_ids.py` has two modes:

```bash
python authoring/v2/generate_ids.py path/to/draft.json
python authoring/v2/generate_ids.py --write path/to/draft.json
```

The default mode is read-only. `--write` is the explicit authorization to allocate new UUIDs.

Existing valid UUIDs are preserved byte-for-byte. Existing invalid values are rejected rather than replaced. Missing definition IDs can be allocated. Temporary explicit aliases of the form `@id:objective-algebra` can be used in both definitions and references; one random UUID v4 is allocated for each alias and persisted everywhere it is referenced. Aliases are authoring conveniences, not canonical derivation rules.

A missing reference cannot be inferred from ordering or text. It must use an explicit alias or an already persisted UUID.

## Revision and digest rules

Lineage identifies the evolving conceptual object. Revision identity identifies one immutable authored payload.

- A title-only authored change keeps the corresponding lineage ID.
- Because authored titles are part of the revision payload, that change requires a new revision ID and digest.
- A semantic change to a prompt, answer, choice, slot/token mapping, explanation or other immutable content requires a new revision ID and digest.
- A local Player display-label edit is outside the authored package and changes neither canonical lineage nor revision identity.
- Existing revision IDs are never regenerated from content.

Canonical JSON follows `FOUNDATION_V1.md`:

1. UTF-8;
2. NFC-normalized strings and object keys;
3. object keys sorted lexicographically by Unicode code point;
4. authored array order retained;
5. no insignificant whitespace;
6. values limited to objects, arrays, strings, integers, booleans and null;
7. the digest field of the object being digested omitted;
8. SHA-256 rendered as `sha256:<64 lowercase hex>`.

Digests are evaluated inside out: activities, then courses including declared activity digests, then package including declared course digests.

For a new revision, leave its digest absent or set it to `sha256:` followed by 64 zeros, allocate a new revision UUID, then run the explicit digest-writing mode:

```bash
python authoring/v2/validate_kit.py \
  --schema contracts/learnit-kit-v2.schema.json \
  --foundation-profile \
  --write-digests \
  path/to/draft.json
```

`--write-digests` only fills missing or all-zero digests. It refuses to rewrite a non-zero mismatch, because doing so could silently preserve a stale revision ID after a semantic change. After digest generation, run validation again without `--write-digests`.

## Validation

```bash
python authoring/v2/validate_kit.py \
  --schema contracts/learnit-kit-v2.schema.json \
  --foundation-profile \
  authoring/v2/golden/nombres_complexes.json \
  authoring/v2/golden/signaux_electriques.json
```

The validator performs:

- strict UTF-8 JSON parsing with duplicate-key rejection;
- Draft 2020-12 validation against the frozen schema;
- global definition-ID uniqueness within each package;
- objective-reference integrity;
- QCM choice uniqueness and `correctChoiceId` integrity;
- fill slot/token uniqueness, one answer per slot, complete slot coverage and `maxUses` enforcement;
- validation-role/phase consistency;
- foundation-profile minima for objectives and activity roles;
- canonical JSON and inside-out SHA-256 calculation;
- declared/calculated digest equality;
- cross-file detection of one revision ID associated with different content or digest.

Use `--show-canonical` to emit the full canonical JSON for cross-language comparison, or `--format json` for machine-readable reporting. Validation never modifies a kit unless `--write-digests` is explicitly supplied, and even then only the constrained new-digest operation is allowed.

## Golden kit summaries

### Nombres complexes

One 35-minute representative course with two objectives and six activities:

- three QCM and three fill activities;
- form cartésienne and real/imaginary parts;
- product and quotient calculations;
- module and argument;
- point/affix interpretation;
- one transfer activity and one explicit validation activity.

Scientific checks were performed against the supplied EPF `MI2 - Nombres Complexes`, second edition, 17 February 2026: algebraic form, multiplication, conjugate quotient method, module, argument and complex-plane interpretation. Checked numerical results include `(2+i)(3−2i)=8−i`, `(3+i)/(2+i)=7/5−i/5`, `|3+4i|=5`, and `arg(−1+i√3)=2π/3` for the principal argument.

### Signaux électriques

One 35-minute representative course with two objectives and six activities:

- three QCM and three fill activities;
- voltage/current units and Ohm's law;
- amplitude, offset, period, frequency and angular frequency;
- peak-to-peak versus RMS distinction;
- one transfer activity and one explicit validation activity.

Scientific checks were performed against the supplied EPF `Des signaux pour communiquer`, version 11 January 2026, especially the sinusoidal-signal definitions and RMS derivation. Checked results include `T=20 ms → f=50 Hz → ω=100π rad·s⁻¹`, a 4 V amplitude giving 8 V peak-to-peak and approximately 2.83 V RMS, and `i(t)=0.2 cos(400πt) A` giving `f=200 Hz`, `T=5 ms` and 0.4 A peak-to-peak.

Neither kit asserts measured mastery, retention or long-term learning effectiveness.

## Recorded validation — 2026-07-15

Commands executed from the repository root:

```bash
python -m py_compile authoring/v2/generate_ids.py authoring/v2/validate_kit.py
python -m json.tool authoring/v2/golden/nombres_complexes.json >/dev/null
python -m json.tool authoring/v2/golden/signaux_electriques.json >/dev/null
python authoring/v2/generate_ids.py authoring/v2/golden/nombres_complexes.json
python authoring/v2/generate_ids.py authoring/v2/golden/signaux_electriques.json
python authoring/v2/validate_kit.py --schema contracts/learnit-kit-v2.schema.json \
  --foundation-profile authoring/v2/golden/nombres_complexes.json \
  authoring/v2/golden/signaux_electriques.json
```

Observed result:

```text
Python compilation: PASS
JSON parse: PASS 2/2
ID allocation check: PASS 2/2; missing=0; aliases=0; existing IDs changed=0
Nombres complexes: structure PASS; semantic PASS; IDs=52; objective refs=7; qcm=3; fill=3
Signaux électriques: structure PASS; semantic PASS; IDs=50; objective refs=7; qcm=3; fill=3
Repeated validator output comparison: PASS, byte-identical
OVERALL PASS
```

Canonical revision results:

| Kit | Package revision ID | Package canonical bytes | Package revision digest | Course revision digest |
|---|---|---:|---|---|
| Nombres complexes | `e1807670-39f9-4bcd-a696-b50035d42fa5` | 8550 | `sha256:adaa82363317d19a6faab9d0374cc40e6197020f30750fb3e4db579479175f60` | `sha256:786307f33a9988a3d3f597530e92bb299c1d0a8dd1c603601ea499b44d8f9dcd` |
| Signaux électriques | `ad0064db-2150-470f-b8a9-8e4a475a0f8f` | 8605 | `sha256:13f55500bd91227317b9477177d1b2e0d622d6806356fcb8fe002cdf9a0414c8` | `sha256:ba9f13ec4e7c5ed1f8ce6c1eaa4884cba2d04265f3c7deb96c28fddc7922fee1` |

Adversarial temporary-copy checks, none committed:

```text
duplicate canonical ID: EXPECTED FAIL
a missing QCM choice reference: EXPECTED FAIL
a duplicate fill answer: EXPECTED FAIL
a token maxUses violation: EXPECTED FAIL
a semantic change with stale digest: EXPECTED FAIL
legacy contract discriminator: EXPECTED FAIL
same revision ID with changed answer and regenerated digest across files: EXPECTED FAIL
non-zero digest mismatch passed to --write-digests: REFUSED
title-only edit passed through generate_ids.py: existing IDs preserved; digest validation still requires a new revision ID/digest
invalid existing ID passed through generate_ids.py: REFUSED
```

## Review still required

Before integration, independent reviewers must confirm:

- contract behavior and Python/JavaScript canonical-byte agreement;
- mathematics and distractor quality for Nombres complexes;
- physics, units and amplitude/RMS distinctions for Signaux électriques;
- learning-objective/activity/feedback alignment;
- exact five-path scope and result hashes.

The Player has not yet demonstrated import or execution of these kits. That claim can only be made after the reviewed runtime, QA and authoring outputs are integrated and tested on the exact integrated result.

## Rollback

Discard or revert the five `authoring/v2` files. No schema, RC718 source, Player data, build, workflow or release artifact is affected.
