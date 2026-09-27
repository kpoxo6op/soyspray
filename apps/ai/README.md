# DeepSeek Harness Remote

This route makes DeepSeek Harness on the laptop available at
<https://ai.soyspray.vip>. It is for private LAN and Tailscale access from the
phone. It does not run the harness in Kubernetes and does not add a public
tunnel.

## Ownership

- User systemd on the laptop runs the official `@deepseek-ai/dsh` Web profile and
  owns its sessions and credentials.
- Git and Argo CD own the private node relay, Service, and Ingress.
- cert-manager issues and renews the hostname certificate in this namespace.
- Authentik permits `cluster-admins` before the request reaches the relay.
- The laptop proxy accepts only the node-0 relay and performs the native
  DeepSeek Harness browser-token exchange.
- A non-root Nginx relay binds only to `node-0`'s private LAN address and reaches
  the laptop's Tailscale address. If that address changes, update
  `manifests/relay-config.yaml`, refresh the `checksum/relay-config` annotation
  in `manifests/relay-deployment.yaml`, and update `listenHost` in the laptop's
  `deepseek-harness/auth-proxy.mjs` before restarting the auth proxy. The
  checksum makes Argo replace Nginx after a config change.

## Check it

```sh
kubectl -n ai get application,deployment,service,ingress
curl --head https://ai.soyspray.vip/
systemctl --user enable --now deepseek-harness.service deepseek-harness-auth-proxy.service
```

The unauthenticated request must redirect to Authentik. Test an authenticated
Harness session from the phone with Tailscale enabled. Then disable Tailscale and mobile Wi-Fi;
the private hostname must not provide a Harness login path.

The route is unavailable when the laptop is asleep, offline, signed out, or when the
`deepseek-harness.service` or `deepseek-harness-auth-proxy.service` is stopped.
Kubernetes stores no Harness data and has no backup or restore role.

## Roll back

Do not delete the Argo CD Application first. Its deletion and pruning protections
intentionally retain resources. Restore the previous desired workload while the
Application and `apps/ai/manifests` path still exist, then verify
Argo has pruned the relay, Service, Ingress, and ConfigMap. Remove the Argo
registration only after the namespace contains no retained route resources.
