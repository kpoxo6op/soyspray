# DeepSeek Harness Remote

This route makes DeepSeek Harness on laptop `mox` available at
<https://ai.soyspray.vip>. It is for private LAN and Tailscale access from the
phone. It does not run the harness in Kubernetes and does not add a public
tunnel.

## Ownership

- User systemd on `mox` runs the official `@deepseek-ai/dsh` Web profile and
  owns its sessions and credentials.
- Git and Argo CD own the private node relay, Service, and Ingress.
- cert-manager issues and renews the hostname certificate in this namespace.
- The laptop authentication proxy requires Basic Auth before the native
  DeepSeek Harness browser-token exchange.
- A non-root Nginx relay binds only to `node-0`'s private LAN address and reaches
  the stable Tailscale address of `mox`. Update `manifests/relay-config.yaml` if
  the laptop gets a new Tailscale identity.

## Check it

```sh
kubectl -n ai get application,deployment,service,ingress
curl --head https://ai.soyspray.vip/
```

The unauthenticated request must return `401`. Test an authenticated Harness session
from the phone with Tailscale enabled. Then disable Tailscale and mobile Wi-Fi;
the private hostname must not provide a Harness login path.

The route is unavailable when `mox` is asleep, offline, signed out, or when the
`deepseek-harness.service` or `deepseek-harness-auth-proxy.service` is stopped.
Kubernetes stores no Harness data and has no backup or restore role.

## Roll back

Do not delete the Argo CD Application first. Its deletion and pruning protections
intentionally retain resources. Restore the previous desired workload while the
Application and `apps/ai/manifests` path still exist, then verify
Argo has pruned the relay, Service, Ingress, and ConfigMap. Remove the Argo
registration only after the namespace contains no retained route resources.
