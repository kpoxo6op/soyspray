"""Disposable browser fixture with an operator-only invite handoff file."""

import json
import os
import tempfile
from pathlib import Path

from fixture import synthetic
from memes.server import server

with tempfile.TemporaryDirectory(prefix="memes-browser-") as data:
    synthetic(data)
    http = server(data, ("127.0.0.1", 18185), "http://127.0.0.1:18185", secure=False)
    directory = Path("test-results")
    directory.mkdir(exist_ok=True)
    path = directory / "invite"
    descriptor = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as file:
        file.write(
            json.dumps(
                {
                    project: "/t/" + http.store.invite("browser fixture " + project)
                    for project in ("phone", "desktop")
                }
            )
        )
    try:
        http.serve_forever()
    finally:
        path.unlink(missing_ok=True)
