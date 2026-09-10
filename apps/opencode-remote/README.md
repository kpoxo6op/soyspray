# OpenCode Remote

This route makes the OpenCode Web service on laptop `mox` available at
<https://opencode.soyspray.vip>. It is for private LAN and Tailscale access from
the phone. It does not run OpenCode in Kubernetes and does not add a public
tunnel.

## Ownership

- User systemd on `mox` runs OpenCode and owns its sessions and credentials.
- Git and Argo CD own the private node relay, Service, and Ingress.
- The namespace contains a declarative reflector mirror of the shared wildcard
  TLS secret. Reflector supplies and renews the certificate data.
- OpenCode Basic Auth remains required behind the ingress.
- A non-root Nginx relay binds only to `node-0`'s private LAN address and reaches
  the stable Tailscale address of `mox`. Update `manifests/relay-config.yaml` if
  the laptop gets a new Tailscale identity.

## Check it

```sh
kubectl -n opencode-remote get application,deployment,service,ingress
curl --head https://opencode.soyspray.vip/
```

The unauthenticated request must return `401`. Test an authenticated UI session
from the phone with Tailscale enabled. Then disable Tailscale and mobile Wi-Fi;
the private hostname must not provide an OpenCode login path.

The route is unavailable when `mox` is asleep, offline, signed out, or when the
`opencode-remote.service` user service is stopped. Kubernetes stores no OpenCode
data and has no backup or restore role.

## Roll back

Do not delete the Argo CD Application first. Its deletion and pruning protections
intentionally retain resources. Restore the previous desired workload while the
Application and `apps/opencode-remote/manifests` path still exist, then verify
Argo has pruned the relay, Service, Ingress, and ConfigMap. Remove the Argo
registration only after the namespace contains no retained route resources.
