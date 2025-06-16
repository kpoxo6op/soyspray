# Prowlarr GitOps Tracker Configuration – Updated Step‑by‑Step Plan

This revision eliminates imperative `kubectl apply` calls.
Every state change is driven by **Git commit → ArgoCD diff → ArgoCD sync**.

## Prerequisites

Add these variables to `.env` in the repo root **once**:

```bash
PROWLARR_API_KEY=7057f5abbbbb4499a54941f51992a68c
RUTRACKER_USER=<username>
RUTRACKER_PASS=<password>
```

## Step 1 – Prowlarr Secrets (Ansible)

**Goal** Create/update the `prowlarr-secrets` Kubernetes Secret from `.env`.
**Playbook** `playbooks/deploy-argocd-apps.yml` (tag: `prowlarr`).
The task block is unchanged from the previous plan.

**Verify**

```bash
ansible-playbook playbooks/deploy-argocd-apps.yml --tags prowlarr
kubectl -n media get secret prowlarr-secrets
```

## Step 2 – Tracker Payload File

**Goal** Store RuTracker payload as a first‑class file in SCM.
**File** `playbooks/yaml/argocd-apps/prowlarr/rutracker_payload.json`
(already present – keep exactly as exported from the UI).

## Step 3 – ConfigMap Generator

**Goal** Let Kustomize turn payload files into a ConfigMap.
**File** `playbooks/yaml/argocd-apps/prowlarr/kustomization.yaml`
Add the section:

```yaml
configMapGenerator:
  - name: prowlarr-payloads
    namespace: media
    files:
      - rutracker.json=rutracker_payload.json
    options:
      disableNameSuffixHash: true
```

Remove the old hand‑written `tracker-payloads-cm.yaml`.

**Verify (GitOps style)**

```bash
git add playbooks/yaml/argocd-apps/prowlarr/{kustomization.yaml,rutracker_payload.json}
git commit -m "Generate prowlarr-payloads ConfigMap via kustomize"
git push
argocd app diff prowlarr        # shows the new ConfigMap
argocd app sync prowlarr
kubectl -n media get configmap prowlarr-payloads
```

## Step 4 – Bootstrap Script ConfigMap

**File** `playbooks/yaml/argocd-apps/prowlarr/bootstrap-scripts-cm.yaml`
(same content as previous plan).
Add the file path to `resources:` in `kustomization.yaml`.

**Verify**

```bash
git add playbooks/yaml/argocd-apps/prowlarr/bootstrap-scripts-cm.yaml
git commit -m "Add bootstrap script ConfigMap for Prowlarr"
git push && argocd app diff prowlarr && argocd app sync prowlarr
kubectl -n media get configmap prowlarr-bootstrap-scripts
```

## Step 5 – Bootstrap Job (PostSync Hook)

**File** `playbooks/yaml/argocd-apps/prowlarr/bootstrap-job.yaml`
(same spec; mounts `/payloads` from the generated ConfigMap).
Add the file path to `resources:` in `kustomization.yaml`.

**Verify**

```bash
git add playbooks/yaml/argocd-apps/prowlarr/bootstrap-job.yaml
git commit -m "PostSync job to import Prowlarr trackers"
git push && argocd app sync prowlarr
kubectl -n media logs -f job/prowlarr-bootstrap   # until ✔︎ messages appear
```

## Step 6 – Final Kustomize Inventory Check

Run a full render to confirm all objects are tracked:

```bash
kubectl kustomize playbooks/yaml/argocd-apps/prowlarr | grep -E "kind:|name:"
```

## Adding Another Tracker

1. Export JSON from Prowlarr UI.
2. Save it as `playbooks/yaml/argocd-apps/prowlarr/<tracker>.json`.
3. Append the filename under `files:` in the existing `configMapGenerator`.
4. `git commit && git push`, then `argocd app sync prowlarr`.
5. Monitor the PostSync job logs – the script will idempotently add only new trackers.

## Troubleshooting (GitOps centric)

* **Secret not found** – rerun Step 1 Ansible playbook.
* **Job fails** – `kubectl -n media logs job/prowlarr-bootstrap`.
* **Tracker not added** – validate JSON file structure and API key.
* **Script not executable** – ensure `defaultMode: 0755` on `scripts` volume or use `chmod +x` inside job.
