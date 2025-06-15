# Prowlarr GitOps Tracker Configuration - Step by Step

This plan breaks tracker configuration into small, testable steps. Each step has a verifiable state you can validate before proceeding.

## Prerequisites

Add these variables to your `.env` file in the repo root:

```bash
PROWLARR_API_KEY=7057f5abbbbb4499a54941f51992a68c
RUTRACKER_USER=<username>
RUTRACKER_PASS=<password>
```

## Step 1: Create Prowlarr Secrets

**Goal**: Create secrets from .env file using the same pattern as other apps
**Location**: Add to `playbooks/deploy-argocd-apps.yml`

Add this task to your `deploy-argocd-apps.yml`:

```yaml
- name: Verify and load Prowlarr credentials from .env
  block:
    - name: Load PROWLARR_API_KEY from .env
      set_fact:
        prowlarr_api_key: >-
          {{
            lookup('file', playbook_dir + '/../.env')
            | regex_findall('PROWLARR_API_KEY=([^\n]+)')
            | first
            | default('')
            | trim
          }}

    - name: Load RUTRACKER_USER from .env
      set_fact:
        rutracker_user: >-
          {{
            lookup('file', playbook_dir + '/../.env')
            | regex_findall('RUTRACKER_USER=([^\n]+)')
            | first
            | default('')
            | trim
          }}

    - name: Load RUTRACKER_PASS from .env
      set_fact:
        rutracker_pass: >-
          {{
            lookup('file', playbook_dir + '/../.env')
            | regex_findall('RUTRACKER_PASS=([^\n]+)')
            | first
            | default('')
            | trim
          }}

    - name: Validate Prowlarr credentials
      fail:
        msg: "{{ item.name }} is empty/missing in .env file"
      when: item.value | length == 0
      loop:
        - {name: "PROWLARR_API_KEY", value: "{{ prowlarr_api_key }}"}
        - {name: "RUTRACKER_USER", value: "{{ rutracker_user }}"}
        - {name: "RUTRACKER_PASS", value: "{{ rutracker_pass }}"}
  rescue:
    - name: Fail with helpful message
      fail:
        msg: "Error: .env file not found or Prowlarr credentials invalid"
  tags: prowlarr

- name: Create media namespace
  kubernetes.core.k8s:
    state: present
    kubeconfig: "{{ kubeconfig_path }}"
    definition:
      apiVersion: v1
      kind: Namespace
      metadata:
        name: media
  tags: prowlarr

- name: Create Prowlarr Secrets
  kubernetes.core.k8s:
    state: present
    namespace: media
    kubeconfig: "{{ kubeconfig_path }}"
    resource_definition:
      apiVersion: v1
      kind: Secret
      metadata:
        name: prowlarr-secrets
        namespace: media
      type: Opaque
      data:
        PROWLARR_API_KEY: "{{ prowlarr_api_key | b64encode }}"
        RUTRACKER_USER: "{{ rutracker_user | b64encode }}"
        RUTRACKER_PASS: "{{ rutracker_pass | b64encode }}"
  tags: prowlarr
```

**Verify Step 1**:

```bash
# Run only the prowlarr tasks
ansible-playbook playbooks/deploy-argocd-apps.yml --tags prowlarr

# Verify secret was created
kubectl get secret prowlarr-secrets -n media -o yaml
kubectl get secret prowlarr-secrets -n media -o jsonpath='{.data.PROWLARR_API_KEY}' | base64 -d
```

## Step 2: Create Bootstrap Script ConfigMap

**Goal**: Create the bootstrap script that will configure trackers
**Location**: `playbooks/yaml/argocd-apps/prowlarr/bootstrap-scripts-cm.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prowlarr-bootstrap-scripts
  namespace: media
data:
  bootstrap.sh: |
    #!/bin/sh
    set -eu

    P_URL="http://prowlarr.media.svc.cluster.local:9696"
    echo "Waiting for Prowlarr API…"
    until curl -sf "${P_URL}/api/v1/system/status"; do sleep 5; done

    list() { curl -sf "${P_URL}/api/v1/indexer?apikey=${PROWLARR_API_KEY}"; }

    for f in /payloads/*.json; do
      [ -f "$f" ] || continue  # skip if no files
      name=$(jq -r '.name' "$f")
      if list | grep -q "\"name\":\"$name\""; then
        echo "✔︎  $name already present – skipping"
        continue
      fi
      tmp=$(mktemp)
      jq \
        --arg user "$RUTRACKER_USER" \
        --arg pass "$RUTRACKER_PASS" \
        '(.fields[] | select(.name=="username")).value = $user |
         (.fields[] | select(.name=="password")).value = $pass' "$f" > "$tmp"

      echo "➕  Adding $name"
      curl -sf -X POST -H "Content-Type: application/json" \
        -d @"$tmp" "${P_URL}/api/v1/indexer?apikey=${PROWLARR_API_KEY}"
      rm "$tmp"
    done
```

**Verify Step 2**:

```bash
kubectl apply -f playbooks/yaml/argocd-apps/prowlarr/bootstrap-scripts-cm.yaml
kubectl get configmap prowlarr-bootstrap-scripts -n media
kubectl get configmap prowlarr-bootstrap-scripts -n media -o jsonpath='{.data.bootstrap\.sh}' | head -5
```

## Step 3: Create Initial Tracker Payload

**Goal**: Add your first tracker configuration (RuTracker example)
**Location**: `playbooks/yaml/argocd-apps/prowlarr/tracker-payloads-cm.yaml`

First, export a tracker from Prowlarr UI to get the JSON structure:

1. Go to Prowlarr → Settings → Indexers → Add Indexer → RuTracker
2. Configure it manually once
3. Click the ⋮ menu → Export
4. Save the JSON

Create the ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prowlarr-payloads
  namespace: media
data:
  rutracker.json: |
    {
      "enableRss": true,
      "enableAutomaticSearch": true,
      "enableInteractiveSearch": true,
      "supportsRss": true,
      "supportsSearch": true,
      "protocol": "torrent",
      "priority": 25,
      "downloadClientId": 0,
      "name": "RuTracker.org",
      "implementation": "RuTracker",
      "implementationName": "RuTracker",
      "infoLink": "https://github.com/Prowlarr/Prowlarr",
      "tags": [],
      "fields": [
        {
          "order": 0,
          "name": "username",
          "label": "Username",
          "value": "PLACEHOLDER_USER",
          "type": "textbox",
          "advanced": false
        },
        {
          "order": 1,
          "name": "password",
          "label": "Password",
          "value": "PLACEHOLDER_PASS",
          "type": "password",
          "advanced": false
        }
      ]
    }
```

**Verify Step 3**:

```bash
kubectl apply -f playbooks/yaml/argocd-apps/prowlarr/tracker-payloads-cm.yaml
kubectl get configmap prowlarr-payloads -n media
kubectl get configmap prowlarr-payloads -n media -o jsonpath='{.data.rutracker\.json}' | jq .name
```

## Step 4: Create Bootstrap Job

**Goal**: Create the job that will run after Prowlarr deployment
**Location**: `playbooks/yaml/argocd-apps/prowlarr/bootstrap-job.yaml`

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: prowlarr-bootstrap
  namespace: media
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 900
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: runner
          image: alpine:3.20
          command: ["/bin/sh", "-c"]
          args:
            - |
              apk add --no-cache curl jq >/dev/null
              chmod +x /scripts/bootstrap.sh
              /scripts/bootstrap.sh
          envFrom:
            - secretRef: {name: prowlarr-secrets}
          volumeMounts:
            - {name: payloads, mountPath: /payloads, readOnly: true}
            - {name: scripts,  mountPath: /scripts,  readOnly: true}
      volumes:
        - {name: payloads, configMap: {name: prowlarr-payloads}}
        - {name: scripts,  configMap: {name: prowlarr-bootstrap-scripts, defaultMode: 0755}}
```

**Verify Step 4**:

```bash
kubectl apply -f playbooks/yaml/argocd-apps/prowlarr/bootstrap-job.yaml
kubectl get job prowlarr-bootstrap -n media
# Job won't run until Prowlarr is deployed and the PostSync hook triggers
```

## Step 5: Update Kustomization

**Goal**: Include all new resources in your kustomization
**Location**: `playbooks/yaml/argocd-apps/prowlarr/kustomization.yaml`

Add these to your existing resources:

```yaml
resources:
  - pvc-config.yaml
  - service.yaml
  - deployment.yaml
  - initial-config-configmap.yaml
  - bootstrap-job.yaml
  - tracker-payloads-cm.yaml
  - bootstrap-scripts-cm.yaml
```

**Verify Step 5**:

```bash
cd playbooks/yaml/argocd-apps/prowlarr/
kubectl kustomize . | grep -E "kind:|name:"
```

## Step 6: Deploy and Test

**Goal**: Deploy everything and verify it works

```bash
# Deploy the secrets first
ansible-playbook playbooks/deploy-argocd-apps.yml --tags prowlarr

# Sync the Prowlarr application (this will trigger the PostSync job)
argocd app sync prowlarr

# Monitor the bootstrap job
kubectl get jobs -n media
kubectl logs -f job/prowlarr-bootstrap -n media

# Verify trackers were added
curl -H "X-Api-Key: YOUR_API_KEY" http://prowlarr.local/api/v1/indexer
```

## Adding More Trackers (Future)

To add another tracker:

1. Export JSON from Prowlarr UI
2. Add it to `tracker-payloads-cm.yaml`:

   ```yaml
   data:
     rutracker.json: |
       <<existing rutracker config>>
     1337x.json: |
       <<new tracker config>>
   ```

3. Apply the configmap: `kubectl apply -f tracker-payloads-cm.yaml`
4. Restart the job: `kubectl delete job prowlarr-bootstrap -n media`
5. Sync Prowlarr: `argocd app sync prowlarr`

## Troubleshooting

**Secret not found**: Check step 1 completed successfully
**Job fails**: Check logs with `kubectl logs job/prowlarr-bootstrap -n media`
**Tracker not added**: Verify JSON payload is valid and API key is correct
**Bootstrap script not executable**: ConfigMap defaultMode should be 0755
