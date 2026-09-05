# Boys calendar

This package serves `https://boys.soyspray.vip`. The Russian interface has
three views: **Поездка**, **Даты**, and **Участники**. Sign in with a personal
PIN. To claim an unused name, select it, enter the crew PIN, and set a personal
PIN. The crew PIN cannot replace a claimed PIN.

Use **Поездка** to edit shared decisions, accommodation quotes, and the next
call. Any claimed member can mark a section agreed or reopen it. The board
shows that person's name and time. Editing an agreed value makes it a draft.
Agreement does not mean that every member voted for it.

Use **Даты** to compare proposed stays and answer yes, maybe, or no. A blank
answer stays unanswered. The separate availability calendar supports individual
days and inclusive ranges. Crew colours and patterns show overlap. The calendar
opens at the trip month. The history link keeps earlier claims and availability
events, including baseline records without invented timestamps.

Use **Участники** to edit your own attendance, travel dates, accompanying adult
and child counts, optional budget, and travel notes. Do not enter family names.
The board shows differences from the selected shared dates. Budgets use AUD per
person, excluding flights. Accommodation estimates need an explicit paying-person
count. A manual quote is dated information; the site does not fetch prices or
make bookings.

The call editor stores a UTC instant and IANA timezone. It displays Auckland
and Brisbane times and asks which occurrence to use when the clock repeats a
time. **Текст для Telegram** prepares saved information for manual copying.
Personal budgets and travel notes are excluded unless you select them. It does
not send messages or read chat.

Names, dates, events, salted PIN hashes, and trip data use SQLite on `boys-data`.
Trip content requires a signed-in session. The app has no email, analytics, or
third-party browser script. Cloudflare processes public requests and connection
metadata to deliver the site. A lost-PIN link opens `t.me/borex69`.

## Saving dates

Save keeps historical availability. It changes only your future selections.
The status line shows pending and failed saves. You can continue editing while
an earlier selection is saving; those newer edits still need another save.

If another window changes your dates, compare its saved dates with your draft.
Apply your additions and removals to the reviewed dates, then save again, or
discard your draft. Trip editors use the same conflict review. They keep input
when saving fails and preserve edits made during an outstanding save. Other
members refresh on focus and every 30 seconds. A
failed refresh is shown. Navigation warns when you have unsaved changes.

## Trip data interface

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

## Request path

```text
boys.soyspray.vip
  -> Cloudflare Tunnel boys-public
  -> https://boys.boys.svc.cluster.local:443
  -> boys web pod on 8443
```

The dedicated connector can reach only NodeLocal DNS, the boys web pod, and
Cloudflare Tunnel endpoints. The web pod has no network egress. The private
Ingress remains available through LAN and Tailscale split DNS.

## Runtime image

`Dockerfile` packages the Python server and static assets without runtime
installation. It uses the existing pinned Python base and runs as UID 1000.
The build context includes only the listed application files.

The Boys image workflow checks pull requests in an isolated container. A
successful main-branch build publishes an immutable GHCR digest and opens a
draft promotion PR. The PR changes the deployment image; add any configuration
that requires that source revision before deploying it. The server and static
assets run from the image. The existing PVC, database path, runtime Secret,
session key, and single-writer deployment stay in place. Source-only changes
do not change the running app.

The workflow does not merge or deploy. GitHub can require approval before
running checks on a workflow-created PR. Review and approve those checks, then
use the normal Ansible deployment path. Keep the prior digest for rollback.

`test-image.py` checks readiness, authentication, claim and personal-PIN login,
sessions, and static assets against a fresh isolated image. It has no cluster
access or real account data. The API checks are in
`tests/test_boys_scheduler.py`. The phone and desktop browser checks under
`tests/` use a disposable local database. Set `BOYS_TEST_BROWSER` to an installed
Chromium executable when needed. Browser tools are development dependencies
and are excluded from the runtime image.

## Deploy

Add these values to the ignored repository `.env` file:

```dotenv
BOYS_PIN=<crew-claim-pin>
BOYS_SESSION_KEY=<at-least-32-random-characters>
BOYS_CLOUDFLARED_TOKEN=<dedicated-tunnel-token>
```

Push the topic branch before deployment. Then run:

```bash
make boys BOYS_REVISION=<pushed-promotion-branch>
kubectl -n boys rollout status deployment/boys
kubectl -n boys rollout status deployment/boys-cloudflared
```

Configure the `boys-public` tunnel route with these values:

- Hostname: `boys.soyspray.vip`
- Service: `https://boys.boys.svc.cluster.local:443`
- Origin Server Name: `boys.soyspray.vip`
- No TLS Verify: disabled

The public DNS record must be one proxied CNAME to the dedicated tunnel. Do not
add a wildcard route, public router port, NodePort, or LoadBalancer.

Create one Response Header Transform Rule named `boys response privacy` with
this exact expression:

```text
(http.host eq "boys.soyspray.vip")
```

Remove the `NEL` and `Report-To` response headers. Keep the rule limited to
this hostname so browsers do not send Cloudflare Network Error Logging reports
for the calendar.

The crew list is in `app/server.py`. A name can be claimed once. The personal
PIN must contain 4 to 8 digits and must differ from the crew PIN.

## Check

Run the application and repository checks:

```bash
soyspray-venv/bin/python -m pytest -q tests/test_boys_scheduler.py
cd kubernetes/boys
npm ci
npx playwright install chromium
npm test
cd ../..
kubectl kustomize kubernetes/boys >/dev/null
make check
```

After deployment, check the private and public paths:

```bash
kubectl -n argocd get application boys
kubectl -n boys get deployment,pod,pvc,ingress
curl --fail --head https://boys.soyspray.vip/
```

The public response must not contain `NEL` or `Report-To`. Public DNS must
return Cloudflare addresses, not a LAN or Tailscale address. The local resolver
can still return the private Ingress address for the private path.

## Stop or remove

Use `make boys BOYS_ENABLED=false` to remove the workloads and runtime secrets.
The namespace and `boys-data` claim remain because they contain the event data.
The critical Longhorn backup group protects this claim every 30 minutes.
See the [recovery operations](../../playbooks/operations/recovery/README.md)
for backup and isolated restore commands. Data retirement requires a separate
Ansible operation.
