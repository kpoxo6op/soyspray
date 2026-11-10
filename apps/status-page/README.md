# Public status page

`make status-page-check` validates the existing status configuration. `make status-page` runs the full deployment check and configures the page through the maintained script. `make status-page-fallback` validates and applies its existing fallback mode.

`public-status.json` in this folder defines the external Better Stack status page, its DNS-only Cloudflare CNAME, and its monitored services. Unsupported operations report `unknown` with a cause.

The page has two public addresses:

- `https://status.soyspray.vip`
- `https://soyspray-status.betteruptime.com`

The first address is a DNS-only CNAME. Better Stack hosts the page. The home
cluster and Cloudflare Tunnel do not serve it.

During normal operation, Better Stack redirects the hosted address to the
custom address. To activate the hosted address as an independent fallback,
remove the custom domain through the tested operator command:

```sh
export BETTER_STACK_API_TOKEN='<token with Uptime write access>'
make status-page-fallback
```

Run `make status-page` to restore the custom address. The free Better Stack
plan includes one status page, so both addresses cannot serve separate copies
at the same time.

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

See [`../../soydocs/public-status-page.md`](../../soydocs/public-status-page.md) for
future diagnosis, extension, move maintenance, fallback, and rollback.

The OpenWrt split-DNS wildcard must not send the status hostname to the home
cluster. Keep this more-specific dnsmasq forwarding rule on the router:

```sh
uci -q del_list dhcp.@dnsmasq[0].server='/status.soyspray.vip/1.1.1.1'
uci add_list dhcp.@dnsmasq[0].server='/status.soyspray.vip/1.1.1.1'
uci commit dhcp
/etc/init.d/dnsmasq restart
```
