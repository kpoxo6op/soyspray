# Prowlarr GitOps Tracker Configuration

Below is a drop‑in, GitOps‑friendly pattern that will create (or update) the trackers you specify every time Prowlarr is deployed or re‑synced by Argo CD.
It keeps everything declarative in the same folder that already contains your Prowlarr manifests, and it lets you add new trackers just by committing another payload.json file.

## 1. Add one secret, two ConfigMaps, one Job, and extend kustomization.yaml

Location: `playbooks/yaml/argocd-apps/prowlarr/`

### (A) Secret – generated from your .env

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: prowlarr-secrets               # referenced later as envFrom
  namespace: media
type: Opaque
stringData:                            # PLAIN TEXT for clarity – never commit this!
  PROWLARR_API_KEY: 7057f5abbbbb4499a54941f51992a68c
  RUTRACKER_USER:   "<username>"
  RUTRACKER_PASS:   "<password>"
```

### (B) ConfigMap – tracker payloads (*.json)

Put each tracker in its own file to keep diffs clean

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prowlarr-payloads
  namespace: media
data:
  rutracker.json: |
    <<contents of rutracker_payload.json>>
  # add more entries here, e.g. '1337x.json', 'torrentgalaxy.json', ...
```

### (C) ConfigMap – bootstrap script

- Idempotent: skips a tracker if it already exists
- Injects $RUTRACKER_USER/$RUTRACKER_PASS into payload before POSTing

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
    done
```

### (D) Job – executed automatically after every Argo CD sync

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: prowlarr-bootstrap
  namespace: media
  annotations:
    argocd.argoproj.io/hook: PostSync           # run *after* Deployment is ready
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 900
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: runner
          image: alpine:3.20               # tiny; installs curl & jq on the fly
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

### Extend kustomization.yaml

```yaml
resources:
  - pvc-config.yaml
  - service.yaml
  - deployment.yaml
  - initial-config-configmap.yaml
  - bootstrap-job.yaml          # <─ reference (D) if you split files
  - tracker-payloads-cm.yaml    # <─ reference (B)
  - bootstrap-scripts-cm.yaml   # <─ reference (C)
  - prowlarr-secrets.yaml       # <─ reference (A)

# optional: if you prefer to generate the Secret from an un‑committed .env
secretGenerator:
  - name: prowlarr-secrets
    envs:
      - ../../../../secrets/prowlarr.env   # path outside your repo
generatorOptions:
  disableNameSuffixHash: true
```

## 2. How it works

1. Argo CD deploys Prowlarr (PVC, Service, Deployment as before).

2. When the Deployment is Ready, Argo CD starts the PostSync hook Job.

3. The Job:
   - waits for `GET /api/v1/system/status` to succeed,
   - loops over every `*.json` mounted from prowlarr‑payloads,
   - merges your secrets into the JSON,
   - POSTs to `POST /api/v1/indexer`,
   - skips anything that already exists (idempotent).

4. If you add or change a payload file, commit it and `argocd app sync prowlarr`; the Job is recreated and only the new/changed tracker is applied.

5. Secrets stay outside the repo: build the Secret with `kubectl create secret […] --from-env-file=.env -n media -o yaml > prowlarr-secrets.yaml` and do not commit that file, or generate it on‑the‑fly from Ansible.

## 3. Adding another tracker later

1. Drop a valid payload (exported from Prowlarr UI → Indexer ► ⋮ ► Export) into `playbooks/yaml/argocd-apps/prowlarr/payloads/`.

2. Commit & push.

3. `argocd app sync prowlarr` (or let auto‑sync do it).

That's it—the bootstrap Job runs again and adds the new tracker.

## 4. Using Ansible to keep secrets off‑repo (optional)

```yaml
# playbooks/add-prowlarr-secret.yml
- hosts: localhost
  tasks:
    - name: Load .env
      ansible.builtin.slurp:
        src: ../secrets/prowlarr.env     # .env kept in a private location
      register: envfile
    - name: Parse and create Secret
      kubernetes.core.k8s:
        namespace: media
        definition:
          apiVersion: v1
          kind: Secret
          metadata: {name: prowlarr-secrets}
          type: Opaque
          stringData: "{{ envfile.content | b64decode | community.general.parse_env }}"
```

Run this once (or in CI) before the first Argo CD sync, and again whenever you rotate passwords.

## Why this pattern?

- **Fully declarative GitOps** – every object (except the Secret, if you keep it out‑of‑repo) lives under source control.

- **No external secret manager required** – a plain Secret or an encrypted file handled by SOPS / Sealed‑Secrets will do.

- **Idempotent** – the script checks for an existing indexer before POSTing.

- **Extensible** – adding a tracker is a single‑file Git commit.

Deploy it once; from then on Prowlarr always comes up with the trackers you expect—no manual clicks, no drift.