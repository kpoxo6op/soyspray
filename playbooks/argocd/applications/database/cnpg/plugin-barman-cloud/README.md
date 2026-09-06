# Barman Cloud plugin

This Kustomize source installs the official CloudNativePG Barman Cloud plugin
and declares the two future ObjectStores. The existing `cnpg-operator`
Application keeps its identity and Helm source. It also reads this Git source
from `cnpg-system` so the plugin and its CRD are owned by the existing native
CNPG Application.

The vendored [official v0.15.0 manifest](manifest.yaml) is unchanged. Its
controller image is pinned to the digest in `kustomization.yaml`. Its sidecar
image is pinned by the Kustomize Secret patch. The exact image identities are:

```text
ghcr.io/cloudnative-pg/plugin-barman-cloud@sha256:563c680fe7fda3466ca2b1f55a1397ed2ddc9e760360107dd7724f1959c1a536
ghcr.io/cloudnative-pg/plugin-barman-cloud-sidecar@sha256:06c78deca670525daa35fb1e5323159092785d11cf87b86217bdd5c679a41a84
```
The official installation requires CloudNativePG 1.26 or newer and installs
in the operator namespace, `cnpg-system`. The repository chart `0.26.0`
declares operator version `1.27.0`.

Procedure references:

- Installation: <https://cloudnative-pg.io/plugin-barman-cloud/docs/installation/>
- Built-in backup migration: <https://cloudnative-pg.io/plugin-barman-cloud/docs/migration/>
- Release manifest:
  <https://github.com/cloudnative-pg/plugin-barman-cloud/releases/download/v0.15.0/manifest.yaml>

The ObjectStores preserve the existing destinations and credential references:

| ObjectStore | Namespace | Destination | Secret | Retention |
| --- | --- | --- | --- | --- |
| `immich-offsite` | `postgresql` | `s3://immich-offsite-archive-au2/immich/db/` | `immich-offsite-writer` | `60d` |
| `authentik-offsite` | `authentik` | `s3://immich-offsite-archive-au2/authentik/postgresql/` | `authentik-offsite-writer` | `30d` |

Each Secret uses the existing `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
and `AWS_REGION` keys. `serverName` is intentionally omitted. The migration
guide requires the server identity to be selected later through the Cluster
plugin configuration. This change does not modify any Cluster,
ScheduledBackup, native `barmanObjectStore`, archive identity, or WAL setting.

Root owns the later archive handoff. First verify the plugin and ObjectStore
health. Then migrate each Cluster and ScheduledBackup through the supported
plugin procedure, preserving its existing archive identity and schedule.

Validate locally:

```sh
kubectl kustomize playbooks/argocd/applications/database/cnpg/plugin-barman-cloud
python3 playbooks/argocd/applications/database/cnpg/plugin-barman-cloud/tests/test_plugin.py
```

The ObjectStores and their CRD use `Prune=false,Delete=false`. Removing the
Application or a Git path must not cascade through the archive configuration.
The upstream manifest stays unchanged; Kustomize adds the CRD protection.

Deploy the pushed plugin branch with the standard inventory and privilege
options, after `make go`:

```sh
ansible-playbook playbooks/deploy-argocd-apps.yml --tags cnpg-operator \
  -e cnpg_operator_revision=codex/cnpg-barman-plugin
```

After merge, run the same command with `cnpg_operator_revision=HEAD`. Verify
both source revisions and plugin health. Database migrations are separate.
