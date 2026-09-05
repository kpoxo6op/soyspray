# Boys workloads

This native Kustomize package preserves the existing single-writer deployment,
claim, service, ingress, tunnel, and network boundaries. Run `make diff APP=boys`
and `make deploy APP=boys` from the repository root. Use the
[app guide](../README.md) for checks and recovery.


```text
boys.soyspray.vip
  -> Cloudflare Tunnel boys-public
  -> https://boys.boys.svc.cluster.local:443
  -> boys web pod on 8443
```

The dedicated connector can reach only NodeLocal DNS, the boys web pod, and
Cloudflare Tunnel endpoints. The web pod has no network egress. The private
Ingress remains available through LAN and Tailscale split DNS.

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

