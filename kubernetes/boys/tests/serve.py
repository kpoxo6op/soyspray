"""Run browser checks against disposable local data."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from server import BoysApp, make_server  # noqa: E402

with tempfile.TemporaryDirectory(prefix="boys-browser-") as directory:
    app = BoysApp(
        Path(directory) / "boys.sqlite3",
        "1357",
        b"local-browser-check-key-with-no-production-access",
        cookie_secure=False,
    )
    make_server(("127.0.0.1", 18183), app).serve_forever()
