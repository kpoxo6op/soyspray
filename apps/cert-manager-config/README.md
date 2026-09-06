# Certificate configuration

This app manages the existing Let's Encrypt issuers, wildcard certificates, and
TLS Secret reflector. Kubespray owns the cert-manager controller, webhook,
cainjector, CRDs, and namespace. Keep those foundation resources in Kubespray.

```sh
make status APP=cert-manager-config FORMAT=json
make check APP=cert-manager-config
make smoke APP=cert-manager-config
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

Manifests and operating checks now live together in this app folder. Deployment
uses the native root after the shared checks, app check, and pushed-commit preflight. For a branch
preview, use the command above. After merge, run `make deploy APP=cert-manager-config`
and verify the exact HEAD comparison and health. The old source and one-time
adoption operation have been removed after identity verification.

Authentik waits for the reflected wildcard Secret in its own namespace. Its
role does not submit this Application, retarget it to an Authentik branch, or
apply the Certificate. Deploy certificate configuration before Authentik setup.

`bootstrap.yml` preserves the existing `cert-manager/cloudflare-api-token` Secret.
To restore a missing Secret, supply `cert_manager_cloudflare_api_token` in an
Ansible Vault variables file. Keep its password and encrypted input outside the
cluster and public Git. The foundation namespace must already exist. An empty
input or a token that differs from an existing Secret stops the operation.
The create-only request also refuses a competing Secret creation.

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu apps/cert-manager-config/bootstrap.yml \
  --vault-password-file ~/.config/soyspray/recovery/vault-password \
  -e @"$HOME/.config/soyspray/recovery/cert-manager-config.vault.yml" --check
```

After a pushed-commit `make go`, remove `--check` to restore the missing input.
The standard deployment runs this bootstrap before the native root. The general
Ansible deployment uses the same tasks for `--tags cert-manager`. Existing ACME
and TLS keys remain unchanged. Do not rotate keys or force renewal as a test.
Argo bootstrap owns the existing public Bitnami OCI repository registration.
The old role and duplicate repository definition were removed after the native
bootstrap passed live identity and repeat checks.

Verify both issuers and certificates are Ready, their revisions and expiry dates
are unchanged, reflector and foundation pods keep their identities, and retained
HTTPS hosts still validate. `make smoke APP=cert-manager-config` reads current issuer and certificate
readiness and validity dates. It validates trusted TLS with hostname checks for
Vaultwarden, Obsidian, and Headlamp. It reads no Secrets and uses no app credentials.
JSON output records each result and cause; exit codes are 0 for passed, 1 for
failed, and 2 for unknown. Missing API observations and network failures remain
unknown. This checks current TLS access; it does not prove renewal, identity
recovery, app login, or every reflected namespace. Keep encrypted recovery inputs
outside the cluster. Ingress migration is a separate change.
