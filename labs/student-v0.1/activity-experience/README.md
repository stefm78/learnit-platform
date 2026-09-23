# Activity Experience Lab V2 Touch

From this directory, start the standard-library static server:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8000/`. The Lab makes no external network request; localhost is used only to serve the static files.

The B variants are deliberately distinct from A:
- `flashcard-b`: physical recto/verso card;
- `matching-b`: draggable cards into large targets;
- `order-b`: tactile reorder list;
- `classify-b`: draggable cards into category zones.

Touch drag uses Pointer Events rather than HTML5 drag-and-drop. Every drag-enhanced prototype keeps a tap/keyboard fallback. The Lab consumes only learner-safe `ActivityPresentation` fixtures and emits only frozen `ActivityResponse` objects. It never evaluates correctness, scoring, mastery, progress or session state.

Run checks locally:

```bash
python test_lab.py
python browser_smoke.py
```
