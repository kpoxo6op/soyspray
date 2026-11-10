# Repository tests

The test suite checks repository behavior and deployment rules without
requiring a live cluster.

Tests that cover repository rules or more than one app belong in `tests/`.
Tests for a single app belong in that app's `apps/<name>/tests` folder.

[`conftest.py`](conftest.py) provides shared paths and manifest helpers. Run the
focused suite with `make test`, or the complete local gate with `make check`.

Keep a test when it detects a concrete failure in behavior, data, access,
ownership, recovery, or publication that a broader check would miss. Prefer
real commands and user paths where practical. A rendered manifest can protect
a deployment contract, but its current image digest or wording is not itself
a test oracle. Avoid source-text mirrors, repeated coverage, and prose quotas.
Run affected checks after changes; use `make check` before delivery.
