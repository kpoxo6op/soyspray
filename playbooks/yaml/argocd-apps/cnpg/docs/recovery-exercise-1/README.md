# A/B Immich Postgres DR — Standard Exercise

Goal: repeatedly wipe the inactive letter, restore from S3 to a UTC target, flip
alias, and resume backups

Assumes Immich always uses:
postgresql://immich:immich@immich-db-active.postgresql.svc.cluster.local/immich

# Stable state

- Alias points to the current production letter:

  - A-production: `immich-db-active →
    immich-db-a-rw.postgresql.svc.cluster.local`

  - B-production: `immich-db-active →
    immich-db-b-rw.postgresql.svc.cluster.local`

- Exactly one letter is synced as production app (with backups). The other
  letter is absent.

- CNPG operator is synced and healthy.

# S3 layout (fixed)

- Bucket path: `s3://immich-offsite-archive-au2/immich/db/`

- `serverName`: `immich-db` (stable across A/B)

- Restore reads with secret `immich-offsite-restorer`. Backups write with
  `immich-offsite-writer`.

# One-time setup

1. Sync operator:

```

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags cnpg-operator

```

2. Sync alias + secret:

```

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags immich-db-active

```

# A → B exercise

1. Ensure A is current production and alias points to A:

```

kubectl -n postgresql get svc immich-db-active -o jsonpath='{.spec.externalName}{"\n"}'

```

2. Remove any existing B apps/resources:

```

argocd app delete immich-db-b --yes || true

argocd app delete immich-db-b-restore --yes || true

kubectl -n postgresql delete cluster immich-db-b --ignore-not-found

kubectl -n postgresql delete pvc -l cnpg.io/cluster=immich-db-b

```

3. Set **UTC** PITR target in:

```

edit: playbooks/yaml/argocd-apps/cnpg/immich-db-b-restore/overlays/target-time/patch.yaml

```

4. Recreate **B from S3** (backups disabled during recovery):

```

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags immich-db-b-restore

```

5. Watch recovery to `redo done`:

```

kubectl -n postgresql logs -l job-name=immich-db-b-1-full-recovery -c full-recovery --tail=100 -f

```

6. Validate database:

```

POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db-b -o name | head -n1 | sed 's#pod/##')

kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT version();"

kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT extname FROM pg_extension WHERE extname IN ('vectors','cube','earthdistance') ORDER BY 1;"

kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT COUNT(*) FROM assets;"

```

7. Flip alias to B and restart Immich:

- Edit
  `playbooks/yaml/argocd-apps/cnpg/immich-db-active/immich-db-active-service.yaml`:

  ```

  externalName: immich-db-b-rw.postgresql.svc.cluster.local

  ```

- Sync alias:

  ```

  ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags immich-db-active

  ```

- Restart Immich:

  ```

  kubectl -n immich rollout restart deployment/immich-server

  kubectl -n immich rollout status deployment/immich-server

  curl -k https://immich.soyspray.vip/api/server/ping

  ```

8. Promote B to production (enable backups):

```

argocd app delete immich-db-b-restore --yes

kubectl -n postgresql annotate cluster/immich-db-b argocd.argoproj.io/instance-

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags immich-db-b

```

9. Decommission A:

```

argocd app delete immich-db-a --yes || true

kubectl -n postgresql delete cluster immich-db-a --ignore-not-found

```

# B → A exercise

1. Ensure B is current production and alias points to B:

```

kubectl -n postgresql get svc immich-db-active -o jsonpath='{.spec.externalName}{"\n"}'

```

2. Remove any existing A apps/resources:

```

argocd app delete immich-db-a --yes || true

argocd app delete immich-db-a-restore --yes || true

kubectl -n postgresql delete cluster immich-db-a --ignore-not-found

kubectl -n postgresql delete pvc -l cnpg.io/cluster=immich-db-a

```

3. Set **UTC** PITR target in:

```

edit: playbooks/yaml/argocd-apps/cnpg/immich-db-a-restore/overlays/target-time/patch.yaml

```

4. Recreate **A from S3** (backups disabled during recovery):

```

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags immich-db-a-restore

```

5. Watch recovery to `redo done`:

```

kubectl -n postgresql logs -l job-name=immich-db-a-1-full-recovery -c full-recovery --tail=100 -f

```

6. Validate database:

```

POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db-a -o name | head -n1 | sed 's#pod/##')

kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT version();"

kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT extname FROM pg_extension WHERE extname IN ('vectors','cube','earthdistance') ORDER BY 1;"

kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT COUNT(*) FROM assets;"

```

7. Flip alias to A and restart Immich:

- Edit
  `playbooks/yaml/argocd-apps/cnpg/immich-db-active/immich-db-active-service.yaml`:

  ```

  externalName: immich-db-a-rw.postgresql.svc.cluster.local

  ```

- Sync alias:

  ```

  ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags immich-db-active

  ```

- Restart Immich:

  ```

  kubectl -n immich rollout restart deployment/immich-server

  kubectl -n immich rollout status deployment/immich-server

  curl -k https://immich.soyspray.vip/api/server/ping

  ```

8. Promote A to production (enable backups):

```

argocd app delete immich-db-a-restore --yes

kubectl -n postgresql annotate cluster/immich-db-a argocd.argoproj.io/instance-

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags immich-db-a

```

9. Decommission B:

```

argocd app delete immich-db-b --yes || true

kubectl -n postgresql delete cluster immich-db-b --ignore-not-found

```

# Rules that keep DR boring

- Edit only the **targetTime** patch before each exercise.

- Keep the **alias app** synced at all times.

- Keep exactly **one** production letter app synced with backups enabled.

- Delete the other letter **and its PVCs** to ensure clean state before every
  restore test.

- **Never sync a prod app** (`immich-db-a` or `immich-db-b`) when that letter
  doesn't exist yet.

- **Transfer ownership** by deleting restore app, then syncing prod app.

- Use **UTC** timestamps for `targetTime`. Set it ≤ last WAL transaction.

# Quick checks

```

kubectl -n postgresql get svc immich-db-active -o jsonpath='{.spec.externalName}{"\n"}'

kubectl -n postgresql get cluster

aws s3 ls s3://immich-offsite-archive-au2/immich/db/ --recursive | tail -n 5

```
