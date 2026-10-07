# Applications

Each app keeps its workload configuration, useful checks, and operating guide
near its source. The native root lists every application in
[its Kustomization](../argocd/kustomization.yaml). Application ownership records
are in [`argocd/catalog/`](../argocd/catalog/).

- [Cert-manager](cert-manager): certificate controllers, admission and CRDs.
- [Certificate configuration](cert-manager-config): issuers, wildcard certificates and TLS reflection.
- [Media helper](media-helper): internal channel catalog, playlist and guide.
- [Obsidian sync](obsidian-livesync): CouchDB note sync and recovery.
- [Vaultwarden](vaultwarden): private human vault and restricted reader.
- [Domain health](domain-health): domain checks and Prometheus metrics.
- [DeepSeek Harness Remote](ai): private phone access to the official laptop-hosted DeepSeek Harness.
- [ExternalDNS](external-dns): maintain ingress DNS through the existing Cloudflare identity.
- [Boys](boys): shared calendar and accommodation links.
- [Headlamp](headlamp): browse the cluster through Authentik OIDC.
- [Autism traits](autism-traits): static assessment with scoring in the browser.

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

Boys, autism traits, ExternalDNS, domain health, Vaultwarden, Obsidian sync,
Headlamp, and Media Helper have app command files. Use the Application name:

```sh
make check APP=boys
make diff APP=boys
make smoke APP=boys
make full-check
make restore-check APP=boys
```

`check APP=...` runs that app's maintained local checks. `make check` without
`APP`, `make full-check`, and `make go` run the full repository gate. Merge the
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

Boys, Vaultwarden, and Obsidian have maintained isolated `restore-check` operations.
They read encrypted off-cluster inputs, verify a completed backup through the
restored app, and clean up temporary resources. Each app README states its tested
coverage and remaining human-login, note, or attachment gaps.
Unsupported restore operations report `unknown` with their cause. A completed backup is separate from a successful isolated restore.

`smoke APP=boys` checks the deployed public phone and desktop journey and reports
authenticated coverage as unknown. See [Boys](boys#check-the-live-public-journey).
Other apps report an unsupported operation with its cause until their smoke
procedure is maintained.
