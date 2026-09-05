# Applications

Each migrated app keeps its Argo definitions, configuration, custom source,
useful checks, and operating guide in its own folder. The native root lists
adopted apps in [its Kustomization](../argocd/kustomization.yaml).

- [ExternalDNS](external-dns/README.md): maintain ingress DNS through the existing Cloudflare identity.
- [Boys](boys/README.md): shared calendar and accommodation links.
- [Headlamp](headlamp/README.md): browse the cluster through Authentik OIDC.
- [Autism traits](autism-traits/README.md): static assessment with scoring in the browser.

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
policies are not proof of a successful user journey or recovery. For mapped
claims, status reads native Longhorn backup age and private restore reports.
The `soyspray.vip/data-claims` annotation lists explicit `namespace/claim` names,
separated by commas when needed. No second app inventory is maintained.
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

## Check, compare, and deploy

Boys, autism traits, and ExternalDNS have app command files. Use the Application name:

```sh
make check APP=boys
make diff APP=boys
make smoke APP=boys
make deploy APP=boys REVISION=YOUR_PUSHED_BRANCH
make deploy APP=boys
make full-check
make restore-check APP=boys
```

`check APP=...` runs that app's maintained local checks. `make check` without
APP and `make full-check` run the full repository gate. Every deployment still
runs the full gate and Ansible preflight, even when APP is set. Push the branch
first. Deployment defaults to `REVISION=HEAD`; use the pushed branch for preview
and run the default again after merge.

`diff` uses the pinned upstream Argo CLI and the current Kubernetes context.
For Boys and autism traits, it sends YAML files from the local manifest folder for native
rendering and comparison. Argo applies the current Application's source options,
including runtime patches. It compares local workload changes, not edits to
Application metadata or bootstrap secrets. Argo omits Secret values. Read the
native manifests and Ansible check output for those separate changes.

ExternalDNS compares a clean, pushed commit with the live chart deployment. It
keeps explicit chart versions and resolves Git values to the exact commit. It
rejects Application setting changes that native revision overrides cannot render.
See [ExternalDNS](external-dns/README.md) for supported changes and limits.

The comparison does not sync or prune. A removed object in the diff is not proof
that Argo will delete it: check its `Prune=false` protection and the Application's
sync policy. An Application without a maintained operation file reports `unknown`
with its cause. The native app Makefiles are command entrypoints; they do not
replace the Application metadata inventory.

Boys also has a complete isolated `restore-check` operation. It reads encrypted
off-cluster inputs, verifies a completed backup through the restored app, and
cleans up its own temporary resources. See [Boys recovery](boys/README.md#run-an-isolated-restore).
Unsupported restore operations report `unknown` with their cause. Restore
reports do not replace the separate seven-day recovery-point measurements.

`smoke APP=boys` checks the deployed public phone and desktop journey and reports
authenticated coverage as unknown. See [Boys](boys/README.md#check-the-live-public-journey).
Other apps report an unsupported operation with its cause until their smoke
procedure is maintained.
