"""Run browser checks against disposable local data."""

import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from server import BoysApp, make_server  # noqa: E402

with tempfile.TemporaryDirectory(prefix="boys-browser-") as directory:
    seed = Path(directory) / "trip.json"
    arrival = date.today() + timedelta(days=60)
    seed.write_text(
        json.dumps(
            {
                "id": "browser-example",
                "document": {
                    "destination": {"name": "Тестовый берег"},
                    "dates": {
                        "options": [
                            {
                                "id": "short",
                                "label": "Три ночи",
                                "arrival": arrival.isoformat(),
                                "departure": (arrival + timedelta(days=3)).isoformat(),
                            },
                            {
                                "id": "long",
                                "label": "Четыре ночи",
                                "arrival": arrival.isoformat(),
                                "departure": (arrival + timedelta(days=4)).isoformat(),
                            },
                        ],
                        "selected": None,
                    },
                    "budget": {"min_cents": None, "max_cents": None},
                    "accommodation": {"candidates": [], "selected": None, "paying_people": None},
                    "call": {"at": None, "timezone": None, "url": ""},
                },
            }
        )
    )
    app = BoysApp(
        Path(directory) / "boys.sqlite3",
        "1357",
        b"local-browser-check-key-with-no-production-access",
        cookie_secure=False,
        trip_seed=seed,
    )
    make_server(("127.0.0.1", 18183), app).serve_forever()
