# Activity Experience Lab V3 — Human feedback rework

This isolated Student V0.1 Lab is a human-review prototype. It consumes learner-safe `ActivityPresentation` data and emits only frozen `ActivityResponse` objects. It has no correctness, score, mastery, progress, session, persistence or evaluator authority.

Run locally:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/`.

Automated checks:

```bash
python test_lab.py
python browser_smoke.py
```

V3 implements the human mobile review feedback:

- Flashcard B repeats the question on the revealed side and can flip back.
- Matching B snaps source cards into persistent paired rows opposite target descriptions.
- Order B removes numbers and visible arrow controls; the whole card drags and surrounding cards reflow immediately. Keyboard lift/move/drop remains available.
- Classify B places moved cards physically inside category buckets; `À classer` shrinks and cards can move between buckets or back.
- QCM A aligns labels immediately after radio controls and wraps long text.
- Fill B adds draggable token chips into sentence slots while preserving canonical slot mapping.

All touch manipulation uses Pointer Events. No HTML5 drag-and-drop dependency or external network request is used.
