<!--
playbooks/yaml/argocd-apps/cnpg/docs/init-bootstrap/README.md
Zero-edit day‑zero bootstrap using the initdb overlay and alias A.
-->

# First‑time Immich DB bootstrap (A side, no restore)

This procedure initializes Immich DB fresh on **A** using the `initdb` overlay, pushes an **initial full backup** automatically, and keeps the stable alias `immich-db-active` pointing to A.

## Prereqs

- ArgoCD + ApplicationSet controller are running.
- CNPG operator application is synced.
- AWS writer secret for backups and restorer secret exist in the `postgresql` namespace:
  - `immich-offsite-writer` with writer keys `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `BUCKET_NAME`, `MEDIA_PREFIX`
  - `immich-offsite-restorer` with restorer keys

## Step 1 — Sync operator and alias A

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags cnpg-operator

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags cnpg-immich-alias

argocd app sync immich-db-active-a

kubectl -n postgresql get svc immich-db-active -o jsonpath='{.spec.externalName}{"\n"}'
```
Expected: `immich-db-a-rw.postgresql.svc.cluster.local`


## Step 2 — Sync ApplicationSet for DBs

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags cnpg-immich-db
```

## Step 3 — Bootstrap A from scratch

```bash
argocd app sync immich-db-a-initdb
kubectl -n postgresql get cluster immich-db-a
kubectl -n postgresql get pods -l cnpg.io/cluster=immich-db-a -w
```

## Step 4 — Validate Postgres and extensions

```bash

POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db-a -o name | head -n1 | sed 's#pod/##')
kubectl -n postgresql exec "$POD" -- psql postgresql://immich:immich@localhost/immich -c "SELECT version();"
kubectl -n postgresql exec "$POD" -- psql postgresql://immich:immich@localhost/immich -c "SELECT extname FROM pg_extension WHERE extname IN ('vectors','cube','earthdistance') ORDER BY 1;"
kubectl -n postgresql exec "$POD" -- psql postgresql://immich:immich@localhost/immich -c "SHOW search_path;"
```

## Step 5 — Initial full backup (auto via hook)

```bash
kubectl -n postgresql get backups -w
```

Confirm objects under `s3://immich-offsite-archive-au2/immich/db/` for `serverName: immich-db`.

## Step 6 — Point Immich at the stable alias and restart

```
postgresql://immich:immich@immich-db-active.postgresql.svc.cluster.local/immich
```

```bash
kubectl -n immich rollout restart deployment/immich-server
kubectl -n immich rollout status  deployment/immich-server
```

**Done:** A is live, backups enabled, alias stable.

## Cleanup — Start Over

To clean up all resources created by this procedure and start fresh:

```bash
# Delete ApplicationSets
kubectl delete applicationset immich-db -n argocd
kubectl delete applicationset immich-db-alias -n argocd

# Delete CNPG operator
kubectl delete application cnpg-operator -n argocd

# Delete S3 backup files
aws s3 rm s3://immich-offsite-archive-au2 --recursive

# Optional: Delete CNPG CRDs
kubectl delete crd backups.postgresql.cnpg.io clusters.postgresql.cnpg.io scheduledbackups.postgresql.cnpg.io poolers.postgresql.cnpg.io databases.postgresql.cnpg.io subscriptions.postgresql.cnpg.io publications.postgresql.cnpg.io imagecatalogs.postgresql.cnpg.io clusterimagecatalogs.postgresql.cnpg.io failoverquorums.postgresql.cnpg.io
```
