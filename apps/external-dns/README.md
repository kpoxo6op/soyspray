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

Run from the repository root:

```sh
make check APP=external-dns
make diff APP=external-dns
make deploy APP=external-dns REVISION=YOUR_PUSHED_BRANCH
make status APP=external-dns FORMAT=json
```

Deployment runs the full local gate and standard Ansible bootstrap and root
reconciliation. After merge, run `make deploy APP=external-dns` to return to HEAD.
Verify Argo health, the chart and Git revisions, the original Deployment and RBAC
identities, the token hash, public DNS answers, and Cloudflare records. An ownership
cleanup must not change the rendered workload or DNS records. Smoke and restore operations return unknown with their cause while these
operations are added.

The diff command requires a clean, pushed branch. Native Argo renders the pinned
chart with Git values from that exact commit, without syncing or changing the
Application. Secrets are omitted. Chart version and values changes are supported.
Changes to source paths, Helm parameters, destination, project, or sync policy
return unknown because revision overrides cannot render those settings. Review
Application metadata and secret bootstrap changes separately.

## Restore the provider identity

Normal bootstrap preserves the existing token. Matching input makes no change;
a different supplied value stops before writing. A missing Secret is created
through the native API, which rejects a competing creation. Check mode validates
inputs and skips Secret creation.

Store `external_dns_cloudflare_api_token` in an Ansible Vault variables file
outside the checkout. Use the existing identity from the recovery archive. Keep
the Vault password outside the cluster. Pass the file with `-e @/private/file.yml`
and `--ask-vault-pass` to this command:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu apps/external-dns/bootstrap.yml \
  --ask-vault-pass -e @/private/external-dns.vault.yml
```

Do not put the token in Git, command arguments, or chart values. Reapply the existing TXT ownership settings
and verify DNS before accepting recovery.

Rollback uses the reviewed prior Application source and project. Keep the
Application and credentials; do not delete resources or restore the old removal
path as a rollback step.
