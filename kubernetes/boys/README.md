# Boys calendar

Open <https://boys.soyspray.vip> and sign in with your personal PIN. For an
unclaimed name, select it, enter the crew PIN, then set a personal PIN. The
crew PIN cannot reset a claimed name.

**Календарь** opens first. Mark the days when you are free, then select
**Сохранить даты**. Open **Выбрать диапазон** to mark several days together.
Crew colours and patterns show overlap. Select a day to see who is free.
The calendar opens at the active trip month. **История** shows earlier events.

**Ссылки** is a separate list of places to consider. Add only a title and URL.
Select **Изменить** to correct or remove one link. The app does not fetch prices,
copy chat messages, or make bookings.

The save indicator stays visible on phones. Failed saves keep your draft.
Edits made during a save still need another save. If another window changes
saved data, review the conflict before applying your draft. Refresh runs on
focus and every 30 seconds without replacing unsaved input. Leaving with
unsaved changes gives a warning.

The smaller interface preserves all saved trip fields and responses. Editing
a link changes only its title and URL. Existing quotes, dates, notes, budgets,
and other fields remain in the database, though the interface no longer
shows their forms. The compatibility API and audit log remain available.

Names, dates, events, salted PIN hashes, and private trip data use SQLite on
`boys-data`. The app uses no external browser scripts or analytics. Cloudflare
handles public requests. A lost-PIN link opens `t.me/borex69`.

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
