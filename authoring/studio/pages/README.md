# M3.0 GitHub Pages packaging

This directory is a transport layer for the already validated M3.0 Authoring Foundation.

It does not implement Atlas semantics. `build_pages.py` copies the frozen M3.0 web UI and the exact Python authority files into a static site. `pages-bootstrap.js` intercepts only the existing `/api/*` calls and executes the unchanged Python `authoring/studio/core.py` plus the existing v2 and Atlas validators in Pyodide inside the browser.

The normal loopback application remains unchanged and remains the offline reference. The Pages variant is an additional convenient human-gate surface.

## Network boundary

The browser may issue GET requests only to the pinned Pyodide distribution:

`https://cdn.jsdelivr.net/pyodide/v0.29.4/full/`

Kit bytes, drafts, lineage IDs and exports are processed only in browser memory/localStorage. No authoring data is sent to GitHub, jsDelivr or another service by the application.

## Build

```bash
python authoring/studio/pages/build_pages.py --output /tmp/atlas-authoring-pages
```

The generated directory is static and can be served from any ordinary HTTP origin. The candidate workflow publishes it under `/authoring/` while preserving the existing Learn-it learner page at the site root byte-for-byte.

This candidate deployment is not M3.0 promotion. Exact-head independent QA and explicit human PASS are still required before merge.
