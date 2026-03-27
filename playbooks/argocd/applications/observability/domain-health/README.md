# Domain Health Exporter

This app runs an in-cluster exporter that checks `soyspray.vip` health on a fixed
interval and exposes Prometheus metrics.

Current checks:

- RDAP expiry date for `soyspray.vip`
- Cloudflare zone exists
- Cloudflare zone status is `active`
- Cloudflare nameservers match the expected values
- Public DNS NS records match the expected values
- Healthchecks ping on successful / failed runs

Required `.env` variables before deploy:

- `CLOUDFLARE_API_TOKEN`
- `DOMAIN_HEALTHCHECKS_PING_URL`
- `SOYSPRAY_VIP_EXPECTED_NAMESERVERS`

`SOYSPRAY_VIP_EXPECTED_NAMESERVERS` should be a comma-separated list, for
example:

```dotenv
SOYSPRAY_VIP_EXPECTED_NAMESERVERS=ada.ns.cloudflare.com,bob.ns.cloudflare.com
```

The Cloudflare token only needs read access to the zone metadata.
