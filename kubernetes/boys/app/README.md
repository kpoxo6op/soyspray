# Boys calendar application

This folder contains the small Python server and browser files for the boys
availability calendar. The server uses only the Python standard library. It
stores names and selected calendar dates in SQLite.

Run the local checks from the repository root:

```bash
make setup
soyspray-venv/bin/python -m pytest -q tests/test_boys_scheduler.py
```

The access flow shows one step at a time. A person selects a preseeded name. An
unclaimed name requires the crew PIN and then a new personal PIN. A claimed
name requires its personal PIN. The site does not accept other names. Each
preseeded name has a fixed calendar color in `app.js` and `styles.css`.
