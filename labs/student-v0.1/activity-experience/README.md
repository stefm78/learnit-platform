# Activity Experience Lab V1

From this directory, start the standard-library static server:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8000/`. The Lab makes no external network request; localhost is used only to serve the static files.

This Phase-A Lab consumes only learner-safe `ActivityPresentation` fixtures and emits only `ActivityResponse` objects. It never evaluates correctness, scoring, mastery, progress or session state.

Run checks locally:

```bash
python test_lab.py
python browser_smoke.py
```
