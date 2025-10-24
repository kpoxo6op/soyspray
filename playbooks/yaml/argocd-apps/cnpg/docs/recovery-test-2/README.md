# CNPG Database Recovery Test 2

Recovery Point: Base `20251024T074758` + WAL to `00000001000000000000000E` = Target `2025-10-24 20:53:45+00:00`

Applied recovery config to immich-db-cluster.yaml.

Deleted immich app

```bash
argocd app delete immich --yes
```

Verified immich-library PVC deleted as well.

Deleted DB cluster with `argocd app delete immich-db --yes`. Cluster and PVC removed.

Recreated the DB cluster with recovery config

```bash
argocd app delete immich-db --yes
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags immich-db
```

Check recovery: `kubectl get pods -n postgresql` then `kubectl logs -n postgresql immich-db-1-full-recovery-<hash>`

Recovery failed: `recovery ended before configured recovery target was reached`. Target time `20:53:45+00:00` was NZDT (local) not UTC. Fixed to `08:35:00+00:00` (UTC, before last txn at 08:35:56).

Pushed corrected time, deleted cluster, recreated with ansible playbook.

Recovery successful! Cluster healthy, both databases restored: `immich` (owner: immich) and `app` (owner: app).

Dropped legacy `app` database with `DROP DATABASE app;`. Reverted cluster to normal initdb bootstrap with backups enabled. Drill complete.
