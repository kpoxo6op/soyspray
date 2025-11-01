# Recovery Drill 3 — Blue/Green PITR with Stable DB Alias

Blue/green PITR for Immich with DNS alias. No deletes, same manifests for drills and real events.

## Previous Drill Summary

Test 2 recovered cluster from backup 20251024T074758 to target 08:35:00 UTC.
Encountered timezone conversion error (NZDT vs UTC). Successfully recovered 99 assets, verified extensions, manually restored media from S3, created missing folders. Cluster now runs on Timeline 2 with continuous archiving active.

---

## Design (works for drills and real disasters)

* **Recover as new**: Create a fresh CNPG cluster `immich-db-restore` with `bootstrap.recovery` from S3 + WAL to a **UTC** `targetTime`.
* **Switch traffic by alias**: Immich always talks to `immich-db-active.postgresql.svc.cluster.local:5432`. Cutover = flip the alias to point at the restored cluster.
* **Backups**: Keep backups **disabled** on `immich-db-restore` during drills. **Enable** them immediately after cutover in a real event.

```
Immich App  ─────────────▶  immich-db-active  ──►  immich-db-rw (normal)
                                      │
                                      └─────►  immich-db-restore-rw (after cutover)
```

---

## Stable State — Definition and Checklist

**Definition:**

* Alias points to **production**: `immich-db-active → immich-db-rw.postgresql.svc.cluster.local`.
* Production cluster **immich-db** is healthy with **backups enabled**.
* Restore cluster **immich-db-restore** is **absent** (deleted) or **OutOfSync** and **not** running.
* Immich responds at `/api/server/ping` and shows expected data.

**Verify stable state:**

```bash
# 1) Alias
kubectl -n postgresql get svc immich-db-active -o jsonpath='{.spec.externalName}{"\n"}'
# Expect: immich-db-rw.postgresql.svc.cluster.local

# 2) Production health
kubectl -n postgresql get cluster immich-db
kubectl -n postgresql get pods -l cnpg.io/cluster=immich-db

# 3) No restore cluster
kubectl -n postgresql get cluster immich-db-restore || true

# 4) Immich API
curl -k https://immich.soyspray.vip/api/server/ping
```

---

## Repo Layout, Names, and Process

**Keep a single overlay path** for the timestamp patch:
`playbooks/yaml/argocd-apps/cnpg/immich-db-restore/overlays/target-time/patch.yaml` → set `recoveryTarget.targetTime` (UTC).

**Branch and tag naming (per drill):**

* Branch: `drill3/restoreN` (e.g., `drill3/restore1`)
* Tags:
  * `restoreN-start` — overlay committed, restore app synced
  * `restoreN-cutover` — alias flipped to restore cluster
  * `restoreN-stable` — alias flipped back to production and restore cluster removed

**Commit message template:**

```
drill3(restoreN): PITR to <UTC timestamp>; WAL end <UTC>; alias <before>→<after>
```

**ArgoCD/Ansible invocation:**

* Operator: `--tags cnpg-operator`
* Restore app: `--tags immich-db-restore`
* Production DB + alias Service: `--tags immich-db`
* Immich app (when forcing reconnect): `--tags immich`

---

## One‑Time Setup (already in repo)

* **Alias Service**: `immich-db-active` (ExternalName → `immich-db-rw...`).
* **Immich DB_URL** uses the alias.
* **Restore app**: `immich-db-restore` with overlay `overlays/target-time`.
* **Applications**: `immich-db-application.yaml` and `immich-db-restore-application.yaml` present.

---

## WAL End‑Time Check (always in UTC)

Select a `targetTime` **≤** last WAL transaction time.

```bash
# Show last WAL objects
aws s3 ls s3://immich-offsite-archive-au2/immich/db/immich-db/wals/ --recursive | tail -n 5
# Inspect LastModified (UTC)
aws s3api head-object --bucket immich-offsite-archive-au2 \
  --key immich/db/immich-db/wals/<timeline>/<walfile> \
  --query 'LastModified' --output text
# Example targetTime: 2025-10-24 08:35:00+00:00
```

---

## Standard Drill Flow (applies to restore1, restore2, restore3)

> **Invariant:** Always operate in a dedicated branch `drill3/restoreN`.

### A. Prepare

1. Edit `immich-db-restore/overlays/target-time/patch.yaml` with the chosen **UTC** `targetTime`.
2. Commit with the template above and push.

### B. Bootstrap the restore cluster

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/deploy-argocd-apps.yml --tags cnpg-operator,immich-db-restore
```

* Watch logs until `redo done` and `last completed transaction was at ...+00:00`.

```bash
kubectl -n postgresql get pods
kubectl -n postgresql logs deploy/immich-db-restore-1-full-recovery -c full-recovery --tail=100 -f
```

### C. Validate the restored database

```bash
POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db-restore -o name | head -n1 | sed 's#pod/##')
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT version();"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT extname FROM pg_extension WHERE extname IN ('vectors','cube','earthdistance') ORDER BY 1;"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SHOW search_path;"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT COUNT(*) AS assets FROM assets;"
```

### D. Optional cutover (blue/green)

Flip alias to the restore cluster and restart Immich to drop old DB connections.

```bash
# Alias → restore rw
# Edit file: playbooks/yaml/argocd-apps/cnpg/immich-db/immich-db-active-service.yaml
# externalName: immich-db-restore-rw.postgresql.svc.cluster.local
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/deploy-argocd-apps.yml --tags immich-db

kubectl -n immich rollout restart deployment/immich-server
kubectl -n immich rollout status deployment/immich-server
curl -k https://immich.soyspray.vip/api/server/ping
```

### E. Post‑cutover (only for real incidents)

Enable backups on `immich-db-restore` to resume WAL archiving on the new timeline (commit a backup stanza patch and sync with `--tags immich-db-restore`).

---

## Returning to Stable After Each Drill (restore1, restore2, restore3)

> **Target:** Alias back to production, restore cluster removed, backups enabled on production.

**Step 1 — Flip alias back to production**

```bash
# Edit ExternalName back to production:
# externalName: immich-db-rw.postgresql.svc.cluster.local
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/deploy-argocd-apps.yml --tags immich-db
```

**Step 2 — Restart Immich to ensure fresh connections**

```bash
kubectl -n immich rollout restart deployment/immich-server
kubectl -n immich rollout status deployment/immich-server
```

**Step 3 — Remove the restore cluster**

```bash
# Either delete the ArgoCD app or set it OutOfSync (preferred: delete resources to free storage)
argocd app delete immich-db-restore --yes
kubectl -n postgresql get cluster
```

**Step 4 — Verify stable state**

```bash
kubectl -n postgresql get svc immich-db-active -o jsonpath='{.spec.externalName}{"\n"}'
kubectl -n postgresql get cluster immich-db
curl -k https://immich.soyspray.vip/api/server/ping
```

**Step 5 — Tag the repo**

```bash
git tag restoreN-stable
git push origin restoreN-stable
```

Repeat the same sequence after **restore1**, **restore2**, and **restore3**. Keep each drill in its own branch (`drill3/restore1`, `drill3/restore2`, `drill3/restore3`) and finish with `restoreN-stable`.

---

## Disaster Runbook (hardware gone, new node)

1. Rebuild Kubernetes with Kubespray and install ArgoCD.
2. Sync `cnpg-operator`.
3. Commit a **UTC** `targetTime` to `immich-db-restore/overlays/target-time/patch.yaml` and sync `immich-db-restore`.
4. Flip alias to `immich-db-restore-rw` and restart Immich.
5. Commit a backup stanza to `immich-db-restore` and sync to resume WAL archiving.
6. Rehydrate media to the `immich-library` PVC and validate UI.

---

## Troubleshooting

* **"recovery ended before configured recovery target was reached"** — Set `targetTime` **≤** the last WAL transaction and keep the timestamp in **UTC** (`+00:00`).
* **Immich still on old DB** — Confirm alias ExternalName, then restart `immich-server`.
* **Extensions/search_path mismatch** — Re‑run the validation queries and compare against production expectations.

---

## Quick Command Index

```bash
# Set UTC target time (edit file), then:
ansible-playbook ... --tags cnpg-operator,immich-db-restore

# Flip alias to restore
ansible-playbook ... --tags immich-db
kubectl -n immich rollout restart deployment/immich-server

# Flip alias back to production
ansible-playbook ... --tags immich-db
kubectl -n immich rollout restart deployment/immich-server

# Delete restore cluster
argocd app delete immich-db-restore --yes
```

---

## Success Criteria

* Restore logs show `redo done` and final `last completed transaction was at ...+00:00`.
* `vectors`, `cube`, `earthdistance` installed; `search_path` correct; expected row counts present.
* Immich returns `{"res":"pong"}` after each alias flip and restart.
