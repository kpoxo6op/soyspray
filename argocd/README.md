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
