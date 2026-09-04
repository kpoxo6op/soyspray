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
preseeded name has a fixed calendar color and line pattern in `app.js` and
`styles.css`. All calendar lines have the same weight.

The signed-in calendar shows each boy's claim state and available-day count.
The separate event log records new claims and changed availability totals.
Earlier claims appear once as `Before log` with their current day count. The
open log refreshes every five seconds. The app does not create events when a
person saves the same dates again.
