# Boys calendar

This package serves `https://boys.soyspray.vip`. People enter a name and the
shared PIN. They select dates in one shared calendar. Colored stripes show each
person's availability and overlap inside each date.

The application stores only names and selected dates in SQLite on the
`boys-data` Longhorn claim. It has no account, email, analytics, or third-party
browser script. The shared PIN is suitable for a trusted event group. It does
not prove who entered a name. Cloudflare processes the public requests and
connection metadata to deliver the site.

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

## Deploy

Add these values to the ignored repository `.env` file:

```dotenv
BOYS_PIN=<shared-pin>
BOYS_SESSION_KEY=<at-least-32-random-characters>
BOYS_CLOUDFLARED_TOKEN=<dedicated-tunnel-token>
```

Push the topic branch before deployment. Then run:

```bash
make boys BOYS_REVISION=feat/boys-event-scheduler
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
This package does not configure an offsite backup. Delete the claim only when
the group no longer needs its saved dates.
