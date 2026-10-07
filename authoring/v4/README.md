# Learn-it V4 authoring

This directory is the explicit authoring path for the frozen `learnit.kit.v4` Student V0.1 contract.

It does not redefine V2 or V3. The canonical schema remains `contracts/learnit-kit-v4.schema.json`; this directory consumes that authority without editing it.

## Validate

```bash
python -B authoring/v4/validate_kit.py candidate-v4.json
python -B authoring/v4/validate_kit.py candidate-v4.json --format json
```

`--write-digests` fills only empty/zero revision digests using the same canonical JSON/SHA-256 primitives as the stable V2 authoring foundation. A non-zero mismatched digest is never overwritten silently.

The V4 semantic layer adds fail-closed checks that JSON Schema alone cannot express: global canonical ID/reference integrity, revision-digest integrity, objective/media resolution, non-scored lesson/flashcard boundaries, complete hidden solutions for matching/order/classify, order answer-leak prevention, single-label classify coverage, bounded constructed-response normalization, and embedded-media/SVG safety.

Unused package assets are reported as authoring warnings. Unsafe or remote media is rejected.

## Quality and Factory

After canonical PASS:

```bash
python -B authoring/v2/atlas/pedagogical_quality.py candidate-v4.json --json
```

The M3.1 engine dispatches explicitly on `contract`. Existing V2 behavior keeps the promoted `atlas.pedagogy.v1` profile; V4 uses `atlas.pedagogy.student-v0.1.v4`. V4 quality treats lesson/flashcard as exposure only, never validation evidence, and reports deterministic pathologies without imposing activity-family quotas.

The existing AI Kit Factory remains the source/brief/kit binding and independent semantic-review authority. Because it consumes the quality engine through its public `analyze_package()` seam, a canonical V4 candidate can enter the same deterministic Factory PASS/HOLD flow without a second manufacturing pipeline or any model/network integration.

See `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V4.md` for cognitive-operation guidance.
