# ExternalDNS

ExternalDNS keeps declared ingress hostnames in the existing Cloudflare zone.
It uses the upstream chart and the existing `cloudflare-api-token` Secret.
There is no human web interface or persistent volume.

Keep chart `1.14.0`, domain filter `soyspray.vip`, policy `upsert-only`, TXT owner
`k8s`, and prefix `external-dns-` during adoption. The ignored ingress rules and
TLS settings in `values.yaml` preserve how hostnames are selected. Do not rotate
the API token or change DNS ownership as part of a deployment cleanup.

The native root owns the Application and a dedicated AppProject. The existing
`default` project stays in place for other apps. Application and project guards
prevent pruning or cascading deletion. The chart keeps its existing resource
names and cluster read permissions.

## Deploy and verify

Run `make check APP=external-dns` for its native configuration and bootstrap
checks. `make status APP=external-dns FORMAT=json` reads Argo observations.
Unsupported app operations return unknown with a cause while their checks are
added. Push a topic branch and run the full `make go` gate. During the first adoption,
run `apps/external-dns/adopt.yml` with the standard Ansible inventory and privilege
flags below. Check mode verifies the known Application source and ownership.
Remove `--check` to remove only its Argo cascading finalizers, then use
`make deploy APP=external-dns REVISION=YOUR_PUSHED_BRANCH`. A concurrent
Application change causes the operation to fail before writing.

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu apps/external-dns/adopt.yml --check
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu apps/external-dns/bootstrap.yml
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu playbooks/bootstrap-apps.yml \
  -e argocd_revision=YOUR_PUSHED_BRANCH -e argocd_preview_application=external-dns
```

After merge, run the root bootstrap with `argocd_revision=HEAD` and omit the
preview application. Verify Argo health, the chart and Git revisions, the original
Deployment and RBAC identities, the token hash, public DNS answers, and Cloudflare
records. Adoption must not change the rendered workload or DNS records. Keep old
definitions until these checks pass, then remove their deployment registration.

## Restore the provider identity

Normal bootstrap preserves the existing token. Matching input makes no change;
a different supplied value stops before writing. A missing Secret is created
through the native API, which rejects a competing creation. Check mode validates
inputs and skips Secret creation.

Store `external_dns_cloudflare_api_token` in an Ansible Vault variables file
outside the checkout. Use the existing identity from the recovery archive. Keep
the Vault password outside the cluster. Pass the file with `-e @/private/file.yml`
and `--ask-vault-pass` to the bootstrap command. Do not put the token in Git,
command arguments, or chart values. Reapply the existing TXT ownership settings
and verify DNS before accepting recovery.

Rollback uses the reviewed prior Application source and project. Keep the
Application and credentials; do not delete resources or restore the old removal
path as a rollback step.
