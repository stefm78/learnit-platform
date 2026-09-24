# Activity Experience Lab V7 — Exact Drag Geometry

This isolated Student V0.1 Lab consumes learner-safe `ActivityPresentation` fixtures and emits only the frozen `ActivityResponse` grammar. It contains no correctness evaluator, answer key, score, mastery, progress/session authority, persistence, external network dependency, plugin registry or production import.

Run locally:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8000/`.

Checks:

```bash
python test_lab.py
python browser_smoke.py
python production_audit.py
python visual_audit.py
```

V7 adds one shared interaction invariant across manipulable activities:

> selecting an object never moves layout; it only marks the object and reveals valid destinations. Tapping a revealed destination commits the action. Dragging to the same destination remains a shortcut.

Shared state vocabulary:

- normal;
- selected;
- eligible destination;
- active destination;
- dragging;
- keyboard focus remains independent.

Specific V7 behavior:

- Flashcard B keeps one left/start reading axis.
- Matching B reveals eligible descriptions after source selection; a filled source target is replaced by the moved card with no redundant frame.
- Order B renders insertion targets in an absolute overlay, so selecting a row leaves every row at the exact same geometry. Drag remains strict-Y with ghost + placeholder.
- Classify B highlights only valid bucket-title destinations after card selection; no movement panel exists.
- Fill B highlights only valid empty slots after token selection, plus the bank when returning a placed token; filled slots keep no redundant target shell.
- randomizable pools shuffle once per attempt and remain stable during that attempt.

The independent production audit challenges layout invariance, overlay hit regions, destination validity, state distinctness, mutation safety, framing convergence, look-and-feel consistency and accessibility DOM sanity.

Physical Android review remains required before any human prototype decision.


## V7 exact Order-B drag geometry invariant

During an active Order-B drag, the dashed placeholder is the unique in-flow geometric representative of the source row. Its border-box width and height are copied from the source `getBoundingClientRect()` and must match within 1 CSS px. The original source row remains alive for pointer capture but is positioned out of normal Grid flow, so no extra Grid track or `gap` is introduced. List height therefore remains invariant while the placeholder moves between insertion points.

The audit covers short and multi-line labels, narrow mobile width, repeated reorder directions, pointer cancel, strict-Y ghost motion, zero residual inline styles, and the existing non-drag insertion overlay.
