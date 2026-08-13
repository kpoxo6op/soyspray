# Public Status Page Runbook

## Purpose

This runbook describes how to operate, diagnose, extend, change, and retire the
public service status page.

The page must remain available when the home cluster, internet connection, or
Cloudflare Tunnel is unavailable. Better Stack hosts the page and checks the
public application from outside the home network.

## Current design

```text
visitor
  -> status.soyspray.vip
  -> DNS-only CNAME statuspage.betteruptime.com
  -> Better Stack status page

Better Stack monitor
  -> https://autism.soyspray.vip/
  -> dedicated autism Cloudflare Tunnel
  -> home cluster
```

The important addresses are:

| Purpose | Address |
| --- | --- |
| Normal public page | `https://status.soyspray.vip` |
| Provider-hosted fallback | `https://soyspray-status.betteruptime.com` |
| Initial monitored service | `https://autism.soyspray.vip/` |
| Public CNAME target | `statuspage.betteruptime.com` |

The initial monitor runs every 180 seconds. It requires the text
`Detailed autism questionnaire`. A successful HTTP status without this text is
still a monitor failure.

The status page uses `automatic_reports=true`. Its autism component uses
`mark_as_down_for=any_incident`. Better Stack can therefore show the service as
down when the monitor opens an incident.

The free Better Stack plan has one status page. During normal operation, the
provider-hosted address redirects to the custom address. The two addresses do
not serve separate copies at the same time.

## Source of truth

- [`../platform/public-status.json`](../platform/public-status.json) defines the
  page, DNS record, and monitored services.
- [`../scripts/configure_status_page.py`](../scripts/configure_status_page.py)
  reconciles Better Stack and Cloudflare.
- [`../tests/test_public_status.py`](../tests/test_public_status.py) checks
  extension, idempotency, free-plan compatibility, DNS-only mode, and fallback
  behavior.
- [`../Makefile`](../Makefile) supplies `status-page-check`, `status-page`, and
  `status-page-fallback`.
- [`../platform/README.md`](../platform/README.md) contains the short operator
  procedure.

The reconciler creates or updates declared items. It does not delete an
unlisted monitor, status-page resource, or DNS record. Removing a service from
JSON does not remove it from Better Stack.

## Safety boundaries

- Do not put either API token in Git, documentation, screenshots, or command
  output.
- Use a team-based Better Stack Uptime token with read and write access.
- Do not use a Better Stack Telemetry token.
- Restrict the Cloudflare token to DNS read and write access for
  `soyspray.vip`.
- Keep the Cloudflare CNAME in DNS-only mode.
- Do not add a router port forward, Kubernetes Ingress, Service, or tunnel route
  for `status.soyspray.vip`.
- Push the branch before a live reconciliation.
- Stop if the script finds more than one page, monitor, resource, zone, or DNS
  record for the expected identity.

The Better Stack account owner email is intentionally not stored in this
public repository. Use the secure account record or the existing signed-in
Better Stack session for account recovery.

## Obtain credentials without printing them

In Better Stack, go to **Settings -> API tokens -> Team-based tokens**. Use an
existing Uptime token, or create one with read and write access.

Read the token without adding it to shell history:

```sh
read -rsp 'Better Stack Uptime token: ' BETTER_STACK_API_TOKEN
echo
export BETTER_STACK_API_TOKEN
```

When the cluster is available, load the restricted Cloudflare token from the
existing ExternalDNS Secret without printing it:

```sh
CLOUDFLARE_API_TOKEN="$(
  kubectl -n external-dns get secret cloudflare-api-token \
    -o jsonpath='{.data.api-token}' | base64 --decode
)"
export CLOUDFLARE_API_TOKEN
```

Clear both variables after the operation:

```sh
unset BETTER_STACK_API_TOKEN CLOUDFLARE_API_TOKEN
```

## Validate and reconcile

First validate the desired state:

```sh
make status-page-check
```

Commit and push the branch before a live change. Then reconcile the external
resources:

```sh
make status-page
```

`make status-page` runs the complete local and deployment preflight gate before
it calls the external APIs. A successful result prints both public addresses.

The operation is idempotent. A second run with unchanged JSON must not create a
duplicate page, monitor, component, or DNS record.

## Add or change a monitored page

Choose text that is stable and specific to the successful page. Confirm that
the public response contains it:

```sh
curl --fail --silent --show-error --location \
  https://example.soyspray.vip/ | rg -F 'Expected page text'
```

Add one object to `services` in `platform/public-status.json`:

```json
{
  "name": "Public service name",
  "url": "https://example.soyspray.vip/",
  "keyword": "Expected page text",
  "explanation": "External check of the public service."
}
```

Run these checks:

```sh
make status-page-check
soyspray-venv/bin/python -m pytest -q tests/test_public_status.py
make check
```

Commit and push the change. Then run `make status-page` with both tokens.

Confirm that Better Stack shows one new monitor and one new status-page
component. Confirm that the public page uses the expected name and explanation.

To change a service, edit the existing object and reconcile it. A URL change
creates a new monitor because the URL is the monitor identity. Remove the old
component and monitor manually only after you confirm the exact old URL.

To remove a service, first remove its status-page component in Better Stack.
Then remove its monitor. Finally, remove its JSON object. The reconciler does
not perform these destructive actions.

## Planned home move

An automatic incident can show that the service is down. It cannot know that a
home move caused the outage.

Before the equipment is unplugged, create scheduled maintenance in Better
Stack:

1. Open **Status pages -> Soyspray service status -> Maintenance**.
2. Create a maintenance event.
3. Use the title `Home server move`.
4. Use this description:

   ```text
   The Autism questionnaire is unavailable while the home server is moved and reconnected.
   ```

5. Select `Autism questionnaire` as the affected service.
6. Set the expected start and end times.
7. Save the maintenance event.

After reconnection, confirm the application and monitor are up. End or update
the maintenance event if its planned end time is no longer correct.

## Activate the hosted fallback

Use the fallback when the custom hostname cannot be trusted or reached:

```sh
export BETTER_STACK_API_TOKEN
make status-page-fallback
```

This command removes `custom_domain` from the Better Stack page. It does not
change Cloudflare DNS. The provider-hosted address must then return 200 without
redirecting to `status.soyspray.vip`:

```sh
curl --fail --head https://soyspray-status.betteruptime.com/
```

Restore normal operation with both API tokens:

```sh
make status-page
```

Then confirm that the provider-hosted address redirects to the custom address
and the custom address returns 200.

## Public DNS checks

The public CNAME must be exact:

```sh
dig @1.1.1.1 status.soyspray.vip CNAME +short
dig @1.1.1.1 status.soyspray.vip A +short
```

Expected CNAME:

```text
statuspage.betteruptime.com.
```

The A answer must be a public Better Stack address. It must not be
`192.168.20.20`, `100.96.77.28`, or another private address.

Confirm HTTPS and page content:

```sh
curl --fail --head https://status.soyspray.vip/
curl --fail --silent https://status.soyspray.vip/ | \
  rg -F 'Autism questionnaire'
```

If public DNS is correct but a new custom domain returns a certificate or 404
error, allow time for Better Stack to discover the CNAME and issue the
certificate. Recheck the Better Stack custom-domain setting before you change
DNS again.

## OpenWrt and Tailscale split DNS

OpenWrt sends most `*.soyspray.vip` names to the private cluster. The status
hostname is an exception because the cluster must not serve it.

Keep this specific dnsmasq forwarding rule:

```sh
uci -q del_list dhcp.@dnsmasq[0].server='/status.soyspray.vip/1.1.1.1'
uci add_list dhcp.@dnsmasq[0].server='/status.soyspray.vip/1.1.1.1'
uci commit dhcp
/etc/init.d/dnsmasq restart
```

Inspect and test the rule:

```sh
ssh openwrt "uci show dhcp.@dnsmasq[0] | grep status.soyspray.vip"
dig @192.168.20.1 status.soyspray.vip A +short
dig @100.96.77.28 status.soyspray.vip A +short
```

Both queries must return the Better Stack CNAME and public address. If HTTPS
returns the Kubernetes Ingress fake certificate for `ingress.local`, the exact
router exception is missing or dnsmasq has stale state.

The private autism hostname must continue to use the normal split-DNS path:

```sh
dig @192.168.20.1 autism.soyspray.vip A +short
```

Do not replace the complete `soyspray.vip` wildcard while fixing the status
hostname.

## Diagnose a failure

### Status page is available and autism is down

Check the target directly:

```sh
curl --fail --head https://autism.soyspray.vip/
curl --fail --silent --location https://autism.soyspray.vip/ | \
  rg -F 'Detailed autism questionnaire'
```

If HTTP works but the keyword is absent, update the application or choose a
new stable keyword. Do not change the monitor to a status-only check unless a
partial or incorrect page is acceptable.

If the target is unavailable, diagnose the autism Cloudflare Tunnel and home
cluster. The external status page needs no cluster repair.

### Custom status hostname is unavailable

Check public DNS through `1.1.1.1`. Then check the OpenWrt and Tailscale answers.

During normal operation, the provider-hosted address redirects to the custom
address. Activate the fallback before you use the provider-hosted address to
separate a Better Stack failure from a custom-domain failure.

### Both status addresses are unavailable

Check the Better Stack service status and the Better Stack page settings. Also
confirm that the page is published. Do not change the autism tunnel or cluster
for a provider-side page failure.

### Reconciler returns HTTP 401

Use the team-based Uptime API token for the correct Better Stack team. Do not
use the Telemetry token. Copy the token again without whitespace or shell
clipboard conversion.

### Reconciler returns HTTP 403 for subscription settings

Do not add `subscribable` to `platform/public-status.json` on the free plan.
The current configuration intentionally omits this paid setting.

### Reconciler reports duplicates

Inspect the exact URL, page subdomain, resource, zone, or DNS name reported by
the error. Remove only a confirmed duplicate. Do not weaken the duplicate
guard or delete an unknown resource.

## Verification checklist

Run these checks after each live change:

```sh
make status-page-check
dig @1.1.1.1 status.soyspray.vip CNAME +short
dig @192.168.20.1 status.soyspray.vip A +short
dig @100.96.77.28 status.soyspray.vip A +short
curl --fail --head https://status.soyspray.vip/
curl --fail --head https://autism.soyspray.vip/
```

In Better Stack, confirm these items:

- The page is published.
- The custom domain is `status.soyspray.vip` during normal operation.
- Automatic reports are enabled.
- Every declared service has one monitor and one public component.
- The autism monitor type is `keyword`.
- The autism monitor status is `up` after a healthy check.
- No onboarding or test monitor is public.

Open the status page in a browser. Confirm that its service names, state,
history, maintenance page, and incident page render correctly.

## Rollback and retirement

For a temporary custom-domain problem, activate the hosted fallback. Do not
delete the status page.

To retire only the custom hostname:

1. Activate the hosted fallback.
2. Confirm that the provider-hosted address returns 200.
3. Remove only the `status.soyspray.vip` CNAME from Cloudflare.

To retire the complete service, confirm that no public status page is required.
Then remove the page component, monitor, page, and DNS record through their
respective APIs or consoles. These deletes are permanent and are not automated
by this repository.

## Verified baseline from 2026-08-13

The following state was verified when this runbook was created:

- `https://status.soyspray.vip/` returned 200 with a valid certificate.
- The page showed only `Autism questionnaire` and `100% uptime`.
- The Better Stack autism keyword monitor was `up`.
- The page and component were `operational`.
- Automatic reports were enabled.
- Public DNS returned the Better Stack CNAME and public address.
- OpenWrt LAN and Tailscale DNS returned the public Better Stack path.
- The provider-hosted fallback returned 200 while active.
- The custom domain was restored after the fallback test.
- The Better Stack onboarding `google.com` monitor and component were
  permanently removed.

This section is historical evidence. Do not assume it is the current state.
Run the verification checklist before you make a new operational claim.
