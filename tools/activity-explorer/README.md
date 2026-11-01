# Kit Activity Explorer (read-only; separate from learner product)

This is a static, publicly inspectable **navigation tool** for an operator-selected
LearnIT V6 JSON kit. It is not the learner application, Studio, Factory, or a
privileged authoring console. It never embeds a private kit or communicates with
OneDrive; opening a file is an explicit local browser action.

## Canonical renderer invariant

The explorer imports exactly the **existing LearnIT application modules**, with
no alternative renderer, fork, vendored source or edits to their implementation:

- `apps/learnit-next/src/integration/atlas/activity_projection.js` — project
  activity content and resolve `activity.media[].assetId` against `kit.assets`;
- `apps/learnit-next/src/ui/activity_presenters.js` — identical activity UI and
  response extraction;
- `apps/learnit-next/src/ui/media.js` — used transitively by the presenter for
  SVG/raster validation and optional image zoom;
- `apps/learnit-next/src/core/activity_semantics.js` — response evaluation;
- `apps/learnit-next/src/styles.css` — the same learner activity CSS.

Navigation/category/filters belong solely to this tool. **No learner runtime
module is changed.** The source code runs from the repo root via
`python -m http.server 8766 --bind 127.0.0.1`, then open
`http://127.0.0.1:8766/tools/activity-explorer/index.html`.

## GitHub Pages integration state

`stage_pages.py` creates a **local candidate**, preserving all 52 published
site routes byte-for-byte and adding precisely 8 new static resources (3 tool
files plus 5 unchanged canonical resources). It does not mutate or publish.
The current single Pages publisher is bound to its October 31 one-shot release;
a new governed release decision and a bounded change to that publisher are
required before `/tools/activity-explorer/` can become a live route.

GitHub Pages is public: no owner/Factory secrets or privileged editing may be
included. The operator chooses a local JSON file. Kit validation/approval and
publication remain exclusively in the Factory. The unchanged renderer's
existing limitations, including token reuse behavior, are inherited as-is.
