# Boys runtime

Python standard library, SQLite, and plain JavaScript run from an immutable image.
Use [the app guide](../README.md) for normal use, deployment, and recovery.


The authenticated trip interface stores one shared document, one response per
member, and an append-only audit log in three new SQLite tables. It preserves
the existing tables. Before the first migration, the server uses SQLite's
backup API to create a private `boys.before-trip-<time>.sqlite3` beside the live
database. Startup stops if backup validation fails or the migration is partial.

Runtime input can supply `BOYS_TRIP_SEED_FILE`, the path to a mounted Secret
file with an `id` and `document`. Prepare that input through Ansible Vault.
Keep real destination, dates, and trip content outside Git and static assets.
Seeding creates a draft once. Restarting never resets later edits. Without
a seed, the interface explains that no trip is configured and keeps general
availability available.

Authenticated endpoints:

| Method and path | Purpose |
| --- | --- |
| `GET /api/trip` | Read the trip and responses; missing responses remain unanswered |
| `PUT /api/trip` | Update shared values with `expected_revision` and `document` |
| `PUT /api/trip/response` | Update only the signed-in member with both response and trip revisions |
| `POST /api/trip/decision` | Agree or reopen a section with its expected trip revision |
| `GET /api/trip/activity?before=<id>` | Read up to 100 audit entries, newest first |

Responses need `expected_revision`, `expected_trip_revision`, and `document`.
A missing response starts at revision zero. A stale revision returns 409. Dates
and decisions use the trip revision. The browser must retain the conflicting
draft. Any claimed member can agree or reopen a decision. Editing a section
returns it to draft. Agreement records the actor and time; it is not a vote
from every member.

Money uses integer AUD cents. Budgets are per person, excluding flights.
Unknown amounts and attendance use null. Date answers use `yes`, `maybe`, or
`no`; absent answers remain unanswered. Answers retain the date range that the
member reviewed. If those dates change, the read interface reports an
unanswered value with cause `dates_changed`, while the stored response and
history remain intact. Call times use a UTC instant and an IANA timezone.
Links are manual inputs; the server does not fetch them.

The image check exercises a prior image, the migration image, and the prior
image again against the same disposable database. It checks old PIN login,
sessions, dates, events, the pre-migration backup, and rollback compatibility.
Use a completed Longhorn backup before live migration as well.

