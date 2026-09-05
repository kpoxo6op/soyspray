# Boys calendar

This package serves `https://boys.soyspray.vip`. The nine crew names are ready
in the sign-in list. A person claims an unused name with the crew PIN and then
chooses a personal PIN. Each name has a fixed color and line pattern. Equal
stacked lines show the availability overlap inside each date. The page shows
the name, crew PIN, and personal PIN as separate steps. The calendar lists each
boy as `unclaimed`, `no dates`, or with an available-day count.

The application stores names, selected dates, activity events, and salted
personal PIN hashes in SQLite on the `boys-data` Longhorn claim. It has no
email, analytics, or third-party browser script. The crew PIN can claim an
unused name but cannot replace a claimed PIN. The sign-in page directs a person
with a lost PIN to `t.me/borex69`. Cloudflare processes the public requests and
connection metadata to deliver the site.

The event log requires a signed-in session. It records new claims and changed
availability totals in newest-first order and refreshes every five seconds.
Existing claims appear as a `Before log` baseline, with their current
available-day count and no invented timestamp.

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
access or real account data. The full application tests remain in
`tests/test_boys_scheduler.py`.

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
