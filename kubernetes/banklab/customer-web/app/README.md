# Customer demo application

This dependency-free Python and browser application shows the sample bank APIs
and their gateway policy results.

| File | Purpose |
| --- | --- |
| [`server.py`](server.py) | Small HTTP server and backend request proxy |
| [`traffic.py`](traffic.py) | Continuous synthetic gateway traffic |
| [`index.html`](index.html) | Page structure |
| [`app.js`](app.js) | Browser interactions and API result display |
| [`styles.css`](styles.css) | Responsive presentation |

The source files are mounted into containers through Kustomize ConfigMaps. The
tests in [`../../../../tests/`](../../../../tests/) exercise the server and
browser-facing behaviour.
