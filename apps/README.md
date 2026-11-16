# Applications

Each app keeps its workload configuration, useful checks, and operating guide
near its source. The native root lists every application in
[its Kustomization](../argocd/kustomization.yaml). Application ownership records
are in [`argocd/catalog/`](../argocd/catalog/).

Run `ls apps` to see every app folder, or `make list-apps` to list the Argo CD
Applications.

Read current health and sources through native Argo CD:

```sh
kubectl -n argocd get applications
kubectl -n argocd get application boys -o yaml
```

Use the Argo UI for workload comparisons and history, and Longhorn and CNPG
custom resources and UIs for backup state. Application annotations describe
ownership, access, and declared backup policy; they do not prove a successful
user journey or recovery. Native backup alerts remain in Prometheus.

## Check, compare, and merge

An app has command files when it has an `apps/<name>/Makefile`; run
`ls apps/*/Makefile` to see them. Use the Application name:

```sh
make check APP=boys
make diff APP=boys
make smoke APP=boys
make full-check
make restore-check APP=boys
```

`check APP=...` runs that app's maintained local checks. `make check` without
`APP` and `make full-check` run the full repository gate. Merge the
pull request to deploy. Argo follows `main`. App Makefiles share command
settings in `apps/common.mk`.

`diff` uses the pinned upstream Argo CLI and the current Kubernetes context.
For Boys and autism traits, it sends YAML files from the local manifest folder for native
rendering and comparison. Argo applies the current Application's source options,
including runtime patches. It compares local workload changes, not edits to
Application metadata or bootstrap secrets. Argo omits Secret values. Read the
native manifests and Ansible check output for those separate changes.

Media helper and certificate configuration compare a clean, pushed single Git source. ExternalDNS and Headlamp
compare a clean, pushed commit with the live chart deployment. It
keeps explicit chart versions and resolves Git values to the exact commit. It
rejects Application setting changes that native revision overrides cannot render.
See [ExternalDNS](external-dns) for supported changes and limits.

The comparison does not sync or prune. It uses the pushed commit only for the
comparison and does not change the live Application. A removed object in the
diff is not proof
that Argo will delete it: check its `Prune=false` protection and the Application's
sync policy. An Application without a maintained operation file reports `unknown`
with its cause. The native app Makefiles are command entrypoints; they do not
replace the Application metadata inventory.

An app that maintains an isolated `restore-check` defines it in
`apps/<name>/Makefile`. Each app README states its tested coverage and
remaining gaps.
Unsupported restore operations report `unknown` with their cause. A completed backup is separate from a successful isolated restore.

`smoke APP=boys` checks the deployed public phone and desktop journey and reports
authenticated coverage as unknown. See [Boys](boys#check-the-live-public-journey).
Read `apps/<name>/Makefile` to see whether an app maintains `smoke`.
