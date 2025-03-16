# Full Step-by-Step Plan to Load Large Grafana Dashboards from Disk Instead of ConfigMaps

> **Goal**: Avoid Kubernetes size limits by having Grafana load dashboards directly from `.json` files on disk (instead of giant ConfigMaps).

## Step 1: Clean Up/Remove ConfigMap Generators for Large Dashboards

1. Open `kustomization.yaml`:

   ```yaml
   configMapGenerator:
     # ...
     # Comment out or remove the large dashboards that break the size limit.
     # For example:
     # - name: grafana-dashboard-node-exporter-full
     #   files:
     #     - dashboards/node-exporter-full-rfmoz.json
     #   ...
     # etc.
   ```

2. Validate:
   - Any large dashboards (e.g., `node-exporter-full-rfmoz.json`, `k8s-leospbru.json`) should **not** appear in `configMapGenerator`.
   - Keep or remove smaller dashboards if you wish. You could also remove **all** dashboards from ConfigMap to unify your approach in Step 3.

## Step 2: Decide How to Get `.json` Files Mounted into Grafana

Because we want Grafana to read `.json` files from local disk (instead of from a ConfigMap), we need some approach to place those files in the Grafana pod's filesystem. Common options:

- **Option A**: A sidecar like [git-sync](https://github.com/kubernetes/git-sync) that clones your `dashboards/` folder from Git into a shared volume.
- **Option B**: NFS or another persistent volume that contains the `dashboards/` folder.
- **Option C**: Manually copy them (not typical for GitOps).

Choose **one** approach. For demonstration, we'll outline a **git-sync** approach below.

## Step 3: Update `values.yaml` to Configure the Grafana Sidecar for File-based Dashboards

1. In `values.yaml`, under `grafana:`, update the sidecar configuration:

   ```yaml
   grafana:
     sidecar:
       dashboards:
         enabled: true
         label: grafana_dashboard
         provider:
           type: file
           disableDelete: false
         folder: /tmp/dashboards   # IMPORTANT: Use /tmp/dashboards, not /var/lib/grafana/dashboards
   ```

2. **IMPORTANT**: Do NOT add extra volumes or volume mounts. The Helm chart already creates a volume called `sc-dashboard-volume` that is mounted at `/tmp/dashboards`. We will use this existing volume in Step 4.

3. Validate:
   - The `provider.type` should be set to `file`
   - The `folder` should be set to `/tmp/dashboards` to match the Helm chart's configuration
   - No extra volumes or volume mounts should be added for dashboards as they would conflict with the existing volumes

## Step 4: (Optional) Add a git-sync Sidecar to Automate Cloning `.json` Files

> **Only needed** if you want the dashboards automatically pulled from your Git repo. If you prefer some other volume solution, skip this step.

In the same Helm values, define an extra sidecar container:

```yaml
grafana:
  extraContainers:
    - name: git-sync
      image: k8s.gcr.io/git-sync/git-sync:v4.0.3
      env:
        - name: GIT_SYNC_REPO
          value: "https://github.com/kpoxo6op/soyspray.git"
        - name: GIT_SYNC_BRANCH
          value: "v1.7.2"
        - name: GIT_SYNC_ROOT
          value: "/tmp/git"
        - name: GIT_SYNC_DEST
          value: "dashboards"    # subfolder name
        - name: GIT_SYNC_WAIT
          value: "60"            # sync interval in seconds
      volumeMounts:
        - name: sc-dashboard-volume   # IMPORTANT: Use the existing volume, not a new one
          mountPath: /tmp/git
```

**Explanation**:

- `git-sync` clones `https://github.com/kpoxo6op/soyspray.git` to `/tmp/git/dashboards`.
- We mount the existing `sc-dashboard-volume` (not a new volume) to make the JSON files visible to Grafana.
- The dashboard provider reads these files from `/tmp/dashboards` as configured in Step 3.

Validate:

- `kubectl -n monitoring get pods` and confirm your Grafana pod has two containers: `grafana` and `git-sync`.
- Check the logs: `kubectl logs <grafana-pod> -c git-sync` to ensure the repo is cloning successfully.
- `kubectl exec` into the Grafana container and run `ls /tmp/dashboards` to confirm the `.json` files are present.

## Step 5: Remove Old ConfigMaps (Optional)

If you prefer **not** to load **any** dashboards via ConfigMaps:

1. Delete or comment out **all** `configMapGenerator` entries in `kustomization.yaml`.
2. Validate your dashboards exist on disk at runtime (via the new sidecar approach).
3. Argo CD or `kubectl apply` should no longer attempt to create large ConfigMaps.

## Step 6: Argo CD Sync + Final Validation

1. Commit your changes in Git:
   - `values.yaml` modifications (Grafana sidecar configuration)
   - `kustomization.yaml` changes (removing large ConfigMaps)
2. In Argo CD, run:

   ```bash
   argocd app sync kube-prometheus-stack
   ```

3. After successful sync, check the Grafana UI:
   - Navigate to "Dashboards" → "Manage" and verify your large dashboards appear.
   - If you added `git-sync`, confirm that any future changes to `.json` files in Git are reflected in Grafana automatically.

## Done

At this point, your large dashboards will load from the filesystem (and bypass Kubernetes size limits), fulfilling your GitOps workflow without `kubectl` or ArgoCD complaining about giant JSON payloads.
