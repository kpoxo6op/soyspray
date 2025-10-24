# playbooks/yaml/argocd-apps/cnpg/docs/recovery-test-3/README.md

# Disaster‑grade, blue/green PITR for Immich with a stable DB alias. No deletes, same manifests for drills and real events. Includes one‑time setup, drill runbook, disaster runbook, cutover/rollback, validation, and troubleshooting. References your current ArgoCD/CNPG/Immich layout.

# Recovery Drill 3 — Blue/Green PITR with Stable DB Alias

## Previous Drill Summary

Test 2 recovered cluster from backup 20251024T074758 to target 08:35:00 UTC.
Encountered timezone conversion error (NZDT vs UTC). Successfully recovered 99 assets, verified extensions, manually restored media from S3, created missing folders. Cluster now runs on Timeline 2 with continuous archiving active.

---

## Design (works for drills and real disasters)

* **Recover as new**: Create a fresh CNPG cluster `immich-db-restore` with `bootstrap.recovery` from S3 + WAL to a UTC `targetTime`.
* **Switch traffic by alias**: Immich always talks to `immich-db-active.postgresql.svc.cluster.local:5432`. Cutover = flip the alias to point at the restored cluster.
* **Backups**: Keep backups **disabled** on `immich-db-restore` during drills. **Enable** them immediately after cutover in a real event.
  This aligns with your repo's ArgoCD app layout under `playbooks/yaml/argocd-apps/` and the existing CNPG/Immich structure.

```
Immich App  ─────────────▶  immich-db-active  ──►  immich-db-rw (normal)
                                      │
                                      └─────►  immich-db-restore-rw (after cutover)
```

---

## One‑Time Setup (do this on a branch and keep it)

> Branch workflow

```bash
git checkout -b drill3-blue-green
```

### 1) Add the **DB alias Service** (ExternalName)

Create `Service/immich-db-active` in namespace `postgresql`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: immich-db-active
  namespace: postgresql
spec:
  type: ExternalName
  externalName: immich-db-rw.postgresql.svc.cluster.local
```

Commit it under `playbooks/yaml/argocd-apps/cnpg/` so ArgoCD owns it. 

### 2) Point **Immich** at the alias (once)

Edit `playbooks/yaml/argocd-apps/immich/values.yaml`:

```yaml
env:
  DB_URL: postgresql://immich:immich@immich-db-active.postgresql.svc.cluster.local:5432/immich
```

Leave the rest of the chart as is. This replaces the direct `immich-db-rw…` host with the alias and removes future app edits during drills/cutovers. 

### 3) Add the **restore cluster** app: `immich-db-restore`

Create a new path (mirrors your existing CNPG app layout):
`playbooks/yaml/argocd-apps/cnpg/immich-db-restore/`

**Base cluster** (`cluster.yaml`):

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: immich-db-restore
  namespace: postgresql
spec:
  instances: 1
  imageName: ghcr.io/tensorchord/cloudnative-pgvecto.rs:16-v0.3.0
  storage:
    size: 20Gi
    storageClass: longhorn
  bootstrap:
    recovery:
      source: immich-db-backup
      recoveryTarget:
        targetTime: "YYYY-MM-DD HH:MM:SS+00:00"
  externalClusters:
    - name: immich-db-backup
      barmanObjectStore:
        destinationPath: s3://immich-offsite-archive-au2/immich/db/
        serverName: immich-db
        s3Credentials:
          accessKeyId:
            name: immich-offsite-restorer
            key: AWS_ACCESS_KEY_ID
          secretAccessKey:
            name: immich-offsite-restorer
            key: AWS_SECRET_ACCESS_KEY
          region:
            name: immich-offsite-restorer
            key: AWS_REGION
  postgresql:
    shared_preload_libraries:
      - vectors
  monitoring:
    enablePodMonitor: true
```

**Kustomization** (`kustomization.yaml`):

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: postgresql
resources:
  - cluster.yaml
```

This matches your current CNPG settings (PG16 + pgvecto.rs `vectors`, Longhorn, S3 restorer creds). 

### 4) Add a **timestamp overlay** (the only per‑drill change)

Create `overlays/target-time/patch.yaml`:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: immich-db-restore
  namespace: postgresql
spec:
  bootstrap:
    recovery:
      recoveryTarget:
        targetTime: "2025-10-24 08:35:00+00:00"
```

Overlay kustomization `overlays/target-time/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: postgresql
resources:
  - ../../cluster.yaml
patches:
  - path: patch.yaml
```

### 5) Add an **ArgoCD Application** for the restore cluster

`immich-db-restore-application.yaml` (namespace `argocd`):

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: immich-db-restore
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  destination:
    server: "https://kubernetes.default.svc"
    namespace: postgresql
  sources:
    - repoURL: "https://github.com/kpoxo6op/soyspray.git"
      targetRevision: "drill3-blue-green"
      path: playbooks/yaml/argocd-apps/cnpg/immich-db-restore/overlays/target-time
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

Commit and push. Your Ansible playbook `playbooks/deploy-argocd-apps.yml` already drives ArgoCD apps by tag, so keep using it. 

---

## Drill Runbook (repeatable)

### 0) Preconditions

* `cnpg-operator` is synced (chart app already present). 
* Secrets `immich-offsite-restorer` and `immich-offsite-writer` exist in `postgresql`:

```bash
kubectl -n postgresql get secret immich-offsite-restorer immich-offsite-writer
```

### 1) Set the target time (UTC, not local)

Edit the overlay `patch.yaml` to the desired `YYYY-MM-DD HH:MM:SS+00:00` that is ≤ the last WAL transaction time. Commit and push.

### 2) Deploy the restore cluster

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/deploy-argocd-apps.yml --tags cnpg-operator,immich-db-restore
```

### 3) Watch PITR to completion

```bash
kubectl -n postgresql get pods
# look for: immich-db-restore-1-full-recovery-xxxxx  1/1  Running

kubectl -n postgresql logs immich-db-restore-1-full-recovery-xxxxx -c full-recovery -f
# expect phases: Target backup found → restore base backup → "starting point-in-time recovery to ...+00"
# WAL replay lines → "redo done" → "last completed transaction was at ...+00"
```

### 4) Validate the restored database

```bash
POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db-restore -o name | head -n1 | sed 's#pod/##')

kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT version();"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT extname FROM pg_extension WHERE extname IN ('vectors','cube','earthdistance') ORDER BY 1;"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SHOW search_path;"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT current_database(), current_user;"
# Optional: sanity on app data
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT COUNT(*) AS assets FROM assets;"
```

These checks mirror your CNPG/Immich validation commands. 

### 5) Blue/Green **cutover** by flipping the alias

Edit the `immich-db-active` Service manifest so `externalName` points to the restore RW endpoint:

```yaml
spec:
  type: ExternalName
  externalName: immich-db-restore-rw.postgresql.svc.cluster.local
```

Commit, push, and sync the alias Service via ArgoCD. The Immich app already uses the alias in its `DB_URL`, so no app change is required. 

### 6) Post‑cutover actions

* **Drill**: leave backups disabled on `immich-db-restore`.
* **Real event**: enable backups on `immich-db-restore` so WAL archiving resumes on the new timeline:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: immich-db-restore
  namespace: postgresql
spec:
  backup:
    retentionPolicy: "60d"
    barmanObjectStore:
      destinationPath: s3://immich-offsite-archive-au2/immich/db/
      s3Credentials:
        accessKeyId:
          name: immich-offsite-writer
          key: AWS_ACCESS_KEY_ID
        secretAccessKey:
          name: immich-offsite-writer
          key: AWS_SECRET_ACCESS_KEY
        region:
          name: immich-offsite-writer
          key: AWS_REGION
```

Commit this patch in the same restore path to keep GitOps control. Your existing primary cluster uses the same backup shape. 

### 7) Media rehydration (if testing a real snapshot)

Use your `immich-offsite-backup` job/cron to sync media back to the `immich-library` PVC, then confirm Immich web UI. The job manifests live under `playbooks/yaml/argocd-apps/immich-offsite-backup/`. 

### 8) Rollback / Cleanup

* To roll back during a drill: edit alias back to `immich-db-rw.postgresql.svc.cluster.local`, commit, push, sync.
* Delete `immich-db-restore` when finished.

---

## Disaster Runbook (hardware gone, new node)

1. Rebuild Kubernetes with Kubespray using your existing inventory.
2. Deploy ArgoCD base and your apps with `playbooks/deploy-argocd-apps.yml`. 
3. Sync `cnpg-operator`.
4. Sync `immich-db-restore` with the desired UTC `targetTime` overlay and wait for PITR completion.
5. Flip alias `immich-db-active` to `immich-db-restore-rw`.
6. Enable backups on `immich-db-restore`.
7. Sync Immich (already configured to use the alias in `values.yaml`) and rehydrate media from offsite backup if required. 

Result: Identical steps to the drill, no destructive deletes, immediate cutover, full GitOps.

---

## Troubleshooting

* **Recovery ended before target reached**: `targetTime` exceeded last WAL. Pick a timestamp ≤ the "last completed transaction" reported in the recovery logs, and keep it in `+00:00` UTC format.
* **Immich cannot connect**: verify the alias `immich-db-active` points to the intended RW Service and that `values.yaml` uses the alias host. 
* **Extensions/search_path differ**: re‑run the validation queries above. Your CNPG specs already preload `vectors` and set the same runtime. 

---

## Success Criteria

* Restore pod shows "redo done" and the final "last completed transaction" log line.
* Validation queries return PG16 with `vectors`, `cube`, `earthdistance` installed; `search_path` is correct; expected row counts are present.
* Immich responds at `/api/server/ping` after alias cutover. 

---

## Commit Plan (quick checklist)

1. Add `Service/immich-db-active` (ExternalName → `immich-db-rw…`).
2. Update Immich `values.yaml` `DB_URL` to the alias.
3. Create `immich-db-restore` base + overlay with `targetTime`.
4. Add `immich-db-restore-application.yaml` targeting your branch.
5. Run the Drill Runbook above end‑to‑end. 
