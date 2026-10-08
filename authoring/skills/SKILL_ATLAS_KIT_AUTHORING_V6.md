# Atlas Kit Authoring V6 — PASSAGE release path

Status: candidate skill for `learnit.kit.v6` release hardening.

Author only against the exact V6 contract and validator identities bound by the current governed work package. `constructed` remains schema-readable for historical compatibility but is disabled for new V6 production/release admission with exact reason `ACTIVITY_TYPE_DISABLED:constructed`. `productive` is an admitted family and must carry explicit deterministic scoring semantics.

Role B sources are the authoring source of truth. Every Role B source must be explicitly authorized, have exact bytes and SHA-256, provenance, and claim identifiers included in the source-set binding. A web source may be used only after bounded authoring-time admission; the Factory gate performs no web fetch. Role A learner references are optional, supplemental, and may never become a hidden source of truth.

V6 media is embedded in the kit. Preserve meaningful media and required `alt` text. Do not add remote media, image search, OCR, renderer services, or decorative-media requirements. When an objective materially requires interpreting a visual representation, author enough exact embedded media for an independent reviewer to judge `visualAdequacy=pass`; otherwise the review must hold.

Before Factory submission, bind the exact kit bytes, learner brief, authorized source inventory and source-set digest. Any later kit/brief/source change invalidates the semantic review target and requires a new independent review.
