# Deploy

## Preconditions

- The change is committed and pushed.
- `make go` passes.
- The Argo Application points at the branch being tested.
- The change has a written rollback path.

## Apply the Argo definitions

Activate the repository virtual environment and run the bank-lab tag through the
standard playbook:

```sh
source soyspray-venv/bin/activate
ansible-playbook \
  -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/deploy-argocd-apps.yml \
  --tags kong_bank_lab
```

The playbook changes Application definitions. Argo CD owns the workload sync.
Do not replace this step with `kubectl apply`.

## Verify

```sh
make status
make smoke
```

Check the customer app and Grafana in a browser. Confirm that the changed Argo
Application is `Synced` and `Healthy` before moving on.

Before merge, set any temporary branch `targetRevision` back to `HEAD`, push the
change, and run the checks again.
