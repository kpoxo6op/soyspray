# Boys calendar application

This folder contains the small Python server and browser files for the boys
availability calendar. The server uses only the Python standard library. It
stores names and selected calendar dates in SQLite.

Run the local checks from the repository root:

```bash
make setup
soyspray-venv/bin/python -m pytest -q tests/test_boys_scheduler.py
```

The shared PIN is not an identity system. A person who knows the PIN can use
an existing name and change its dates. Use this site only for the trusted event
group. Rotate the PIN if it leaves that group.
