# Jenkins (`jenkins.soyspray.vip`) via ArgoCD + API

This app is deployed by ArgoCD from:

- `playbooks/argocd/applications/infrastructure/jenkins/jenkins-application.yaml`
- `playbooks/argocd/applications/infrastructure/jenkins/values.yaml`

The app exposes Jenkins at:

- `https://jenkins.soyspray.vip/`

## From the CLI (working flow)

Use a Jenkins user/token pair. In this cluster the bootstrap script creates:

- user: `cloudbees-cli`
- password: `cli-password`
- job: `silly-job` (echoes `silly job executed from bootstrap`)

Because the bootstrap script also prints a generated API token to pod init logs on startup, read the latest token from:

```bash
kubectl -n jenkins logs jenkins-0 -c init --tail=80
```

Example token format: `<TOKEN_FROM_INIT_LOGS>`

### 1) Check job exists

```bash
curl -sk -u "cloudbees-cli:<TOKEN>" \
  https://jenkins.soyspray.vip/job/silly-job/api/json
```

### 2) Get CSRF crumb

```bash
CRUMB_JSON=$(curl -sk -u "cloudbees-cli:<TOKEN>" \
  https://jenkins.soyspray.vip/crumbIssuer/api/json)
CRUMB_FIELD=$(printf '%s' "$CRUMB_JSON" | sed -n 's/.*"crumbRequestField":"\([^"]*\)".*/\1/p')
CRUMB_VALUE=$(printf '%s' "$CRUMB_JSON" | sed -n 's/.*"crumb":"\([^"]*\)".*/\1/p')
```

### 3) Trigger build

```bash
curl -sk -u "cloudbees-cli:<TOKEN>" \
  -H "$CRUMB_FIELD: $CRUMB_VALUE" \
  -X POST \
  "https://jenkins.soyspray.vip/job/silly-job/build"
```

The response includes:

- `Location: https://jenkins.soyspray.vip/queue/item/<id>/`

### 4) Read queue / build output

```bash
curl -sk -u "cloudbees-cli:<TOKEN>" \
  https://jenkins.soyspray.vip/job/silly-job/1/consoleText
```

Expected output for the bootstrap job:

```text
silly job executed from bootstrap
```

## Verification done from this host

- Jenkins UI is reachable at `https://jenkins.soyspray.vip/` (NGINX ingress, TLS secret `prod-cert-tls`).
- ArgoCD app is `Synced` + `Healthy`.
