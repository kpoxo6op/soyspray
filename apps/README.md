# Applications

Each migrated app keeps its Argo definitions, configuration, custom source,
useful checks, and operating guide in its own folder. The native root lists
adopted apps in [its Kustomization](../argocd/kustomization.yaml).

- [Headlamp](headlamp/README.md): browse the cluster through Authentik OIDC.

Read the current cluster inventory and an app's status:

```sh
make apps
make apps FORMAT=json
make status APP=boys FORMAT=json
make list-apps
make backup-status FORMAT=json
```

These commands use the current `kubectl` context. Inventory comes from Application
metadata, including apps that still use the legacy deployment path. There is no
second application registry. The `soyspray.vip/owner` label names the operator
group. The `access-url`, `access-method`, `backup`, and `backup-cause` annotations
under `soyspray.vip/` describe access and the declared backup policy.

Status separates the desired source, Argo's last comparison, and its successful
deployment history. It reports a running revision only when Argo confirms the
current sources are synced. It includes Argo's comparison time; the command does
not refresh Argo or probe the runtime. A previous successful sync does not prove
that a later partial deployment completed.

Missing fields appear as `unknown` with a cause. Access URLs and declared backup
policies are not proof of a successful user journey or recovery. Backup age and
restore evidence remain unknown until their observation sources are connected.
Use [backup status](../playbooks/operations/recovery/README.md#read-backup-status)
for native Longhorn and CNPG observations while per-app recovery mapping is added.
An API failure returns an unknown inventory and a nonzero exit code, not an empty
healthy result. `scripts/app_status.py --help` also describes saved JSON input for
offline checks. The old `COLS` list format is replaced by native `kubectl` output
in `make list-apps` and structured JSON in `make apps`.

Migration is incremental. The existing `kubernetes/` and
`playbooks/argocd/applications/` paths remain authoritative for apps that have not
yet been adopted. Follow [the root procedure](../argocd/README.md) and verify each
replacement before removing its old path.
