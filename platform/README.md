# Shared platform resources

This folder contains cluster services shared by application tenants.

- [`kong/`](kong/) contains the optional API gateway platform used by the bank
  lab.
- [`public-status.json`](public-status.json) defines the external Better Stack
  status page, its DNS-only Cloudflare CNAME, and its monitored services.

Application-specific workloads stay under [`../apis/`](../apis/) and
[`../kubernetes/`](../kubernetes/) so platform ownership remains visible.

## Public status page

The page has two independent public addresses:

- `https://status.soyspray.vip`
- `https://soyspray-status.betteruptime.com`

The first address is a DNS-only CNAME. Better Stack hosts both addresses. The
home cluster and Cloudflare Tunnel do not serve the status page.

Add another object to `services` in `public-status.json` to monitor another
public page. Each object needs a name, URL, required keyword, and public
explanation.

Validate the configuration locally:

```sh
make status-page-check
```

After the branch is committed and pushed, export restricted API tokens and
reconcile the external resources:

```sh
export BETTER_STACK_API_TOKEN='<token with Uptime write access>'
export CLOUDFLARE_API_TOKEN='<token with DNS read and write access for soyspray.vip>'
make status-page
```

The command creates or updates each monitor, one shared status page, the page
resources, and the DNS-only CNAME. It does not delete unlisted monitors or DNS
records.
