# Activity Experience Lab V5 — Interaction Convergence

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

V5 converges manipulable activities on one interaction grammar:

- one neutral card border/radius;
- a subtle selected state distinct from keyboard focus;
- drag elevation without nested shells;
- a single dashed affordance only for empty targets;
- filled targets are visually replaced by the moved card/token;
- Pointer Events for drag; no HTML5 Drag and Drop.

Specific V5 behavior:

- Flashcard B keeps one left/start reading axis on the revealed face.
- Matching B removes stacked frames; matched rows become two single cards facing one another.
- Order B is vertical-only, uses a floating ghost plus independent insertion placeholder, and offers tap-to-select + tappable intercalaires as the non-drag path.
- Classify B removes the movement panel: select a card, then tap a persistent bucket-title destination; drag remains a shortcut.
- Fill B removes the movement panel: select a token, then tap an empty slot; a filled slot loses its shell. Drag replacement remains available and returns the displaced token to the bank.
- QCM A keeps left-aligned radio/text wrapping.
- randomizable option pools shuffle once per attempt and remain stable during that attempt.

`production_audit.py` adversarially challenges the authored tests and the final DOM interaction model. `visual_audit.py` captures the four key final states used for visual inspection.

Physical Android review remains required before any human prototype decision.
