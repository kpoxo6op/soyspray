# Certificate configuration

This app manages the existing Let's Encrypt issuers, wildcard certificates, and
TLS Secret reflector. Kubespray owns the cert-manager controller, webhook,
cainjector, CRDs, and namespace. Keep those foundation resources in Kubespray.

```sh
make status APP=cert-manager-config FORMAT=json
make check APP=cert-manager-config
make diff APP=cert-manager-config
make deploy APP=cert-manager-config REVISION=YOUR_PUSHED_BRANCH
kubectl get clusterissuer
kubectl -n cert-manager get certificate
```

The native root owns this Application and its restricted AppProject. Issuer and
Certificate names, specifications, key references, and reflection rules stay the
same. Prune/delete protection retains these resources when the app is parked.
Application deletion does not cascade. Deliberate retirement needs a separate
Ansible operation. Keep DNS-01 challenge access and existing client hostnames.

During adoption, manifests remain at the existing source path. Run `adopt.yml`
with the standard inventory and privilege options from AGENTS.md, first with
`--check`, then without it. It accepts only the known idle Application and removes
only Argo's cascading finalizers with a resource-version guard. Push first and
run `make go` before the operation. Then use the standard deployment command.
After merge, deploy HEAD and verify the exact Argo revision and health.

The remaining Ansible role keeps Cloudflare-token and shared public Bitnami OCI
repository bootstrap during migration. It no longer submits this Application.
Keep those inputs and registrations until their native bootstrap replacement is
verified. Existing Cloudflare, ACME, and TLS keys must remain unchanged during
adoption. Do not rotate keys or force certificate renewal as a migration test.

Verify both issuers and certificates are Ready, their revisions and expiry dates
are unchanged, reflector and foundation pods keep their identities, and retained
HTTPS hosts still validate. Certificate identity recovery and a dedicated app
smoke command remain unknown until maintained checks cover them. Keep encrypted
recovery inputs outside the cluster. Ingress migration is a separate change.
