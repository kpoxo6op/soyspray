# Application management

The `soyspray` Application is the single Argo CD root. Its Kustomization lists
all direct Applications, the two existing Immich ApplicationSets, and their
AppProjects. All Soyspray Git sources follow `main`.

## Normal change

1. Change a workload or its Application on a topic branch.
2. Run `make check APP=NAME` and `make go`.
3. Use `make diff APP=NAME` when that app has a maintained live comparison.
4. Merge the GitHub pull request.
5. Confirm the affected Argo Application is `Synced` and `Healthy`.

There is no branch deployment command and no Ansible Application submission
path. Merge to `main` is the deployment action. A custom image still needs its
separate immutable digest promotion pull request.

## Bootstrap and safety

`playbooks/bootstrap-apps.yml` installs or repairs the fixed root. It does not
select a branch. Use it only after the Argo foundation exists:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu playbooks/bootstrap-apps.yml
```

The bootstrap must grant a new root-project permission before the first root
sync that needs it. After that transition, the root also manages its own project.

Root pruning and cascading deletion are disabled. Catalog Applications carry
`Prune=false,Delete=false`. ApplicationSets preserve generated resources on
deletion. Removing a catalog entry does not retire its workloads or data. Use
an explicit Ansible retirement operation.

The catalog does not contain private values. Run
`playbooks/bootstrap-app-inputs.yml` only when a documented app needs a Secret,
private model, or other bootstrap input.

For rollback, revert the faulty commit through GitHub. Do not delete an
Application, namespace, claim, or volume as a rollback step. Root health does
not prove application access or recovery.
