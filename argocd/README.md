# Application management

The `soyspray` Application is the native Argo root. Its Kustomization lists each
child package explicitly. Each package contains an Application and AppProject.
Headlamp is the first adopted app. Other apps still use the existing Ansible path
until their individual migrations pass.

The root manages only Applications and AppProjects in `argocd`. Child projects
limit workload sources, namespaces, and resource kinds. Changes here require
operator review because access to Argo's namespace is an administrative boundary.

Bootstrap from a pushed topic branch after `make go`:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu playbooks/bootstrap-apps.yml \
  -e argocd_revision=YOUR_PUSHED_BRANCH
```

Run the same command with `-e argocd_revision=HEAD` after merge. Check the root and
each affected child with `kubectl -n argocd get applications`. Confirm the intended
revision, resource identities, and the app's user journey. Root health alone does
not prove child access or recovery.

Root pruning and cascading deletion are disabled. Child Applications and
AppProjects also carry `Prune=false,Delete=false`. Removing an entry from the list
does not retire its resources. Use an explicit Ansible retirement operation.
Protect every durable claim and its namespace before stateful adoption.

For rollback, revert the reviewed Application change and run the same bootstrap
path. Keep the child Application and its resources. Do not delete the root or a
child as a rollback step.

These controls use native [Argo deletion behavior](https://argo-cd.readthedocs.io/en/stable/user-guide/app_deletion/)
and [sync options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/).

## Preview one adopted application

The root can use a native inline Kustomize patch to select one child's Git branch.
Its checked-in Application stays on `HEAD`. Other children and upstream Helm
versions keep their declared revisions. This lets root self-healing remain on.
A chart-only child needs no source override; its chart configuration comes from
the selected root branch.

Commit and push the current checkout, run `make go`, then use:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu playbooks/bootstrap-apps.yml \
  -e argocd_revision=YOUR_PUSHED_BRANCH -e argocd_preview_application=headlamp
```

The selected Application must be declared in the native root. Its branch on GitHub
must match this clean checkout. Root definitions still come from the whole branch,
so keep unrelated child-definition changes out of a single-app preview. Ansible
waits for the root's complete source comparison and the selected child's sync and
health. Check resource identity, access, and the actual user journey separately.

After merge, run the bootstrap command with `argocd_revision=HEAD` and omit
`argocd_preview_application`. The operation replaces the root source parameters,
which removes the temporary patch. A source comparison prevents it from replacing
a concurrent operator's source change. Run the command again to check idempotency.
The preview never changes root pruning or deletion controls.
