# Activity Experience Lab V4 — interaction stabilization

Run locally:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8000/`.

Checks:

```bash
python test_lab.py
python browser_smoke.py
```

V4 stabilizes the interaction model after physical Android review:
- Flashcard B uses one left-aligned reading axis on the verso.
- Order B uses a floating ghost plus a moving insertion gap; the whole card is draggable.
- Classify B card clicks only select. Movement requires drag or the explicit movement panel.
- Fill B token clicks only select. Movement requires drag or the explicit movement panel; occupied slots lose their dashed shell.
- QCM A keeps radio + text left aligned and wraps long labels.
- Randomized choices are seeded per in-memory activity attempt and remain stable during the attempt.

No correctness, score, mastery, progress, session authority, persistence or external network dependency is present.
