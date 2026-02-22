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
- job: `silly-job`
  - parameter: `environments` (default `sandpit`)
  - parameter: `commands` (choices: `plan`, `apply`; default `plan`)

The bootstrap script prints a generated API token once when the controller initializes.

Fetch it from logs:

```bash
kubectl -n jenkins logs jenkins-0 -c init \
  | rg "Created API token for cloudbees-cli" \
  | awk -F'-> ' '{print $2}' \
  | tail -n 1
```

If that returns nothing (controller already initialized), create a new token with the same user/password:

```bash
USER=cloudbees-cli
PASS=cli-password
COOKIE_JAR=$(mktemp)
CRUMB_JSON=$(curl -s -c "$COOKIE_JAR" -u "$USER:$PASS" https://jenkins.soyspray.vip/crumbIssuer/api/json)
CRUMB_FIELD=$(echo "$CRUMB_JSON" | jq -r '.crumbRequestField')
CRUMB_VALUE=$(echo "$CRUMB_JSON" | jq -r '.crumb')
TOKEN=$(curl -s -u "$USER:$PASS" \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "$CRUMB_FIELD: $CRUMB_VALUE" \
  --data-urlencode "newTokenName=manual-token-$(date +%s)" \
  "https://jenkins.soyspray.vip/user/$USER/descriptorByName/jenkins.security.ApiTokenProperty/generateNewToken" \
  | jq -r '.data.tokenValue')
echo "$TOKEN"
```

Set it locally:

```bash
export TOKEN='<token from log or generated command>'
```

### 1) Check job exists


```bash
curl -s -u "cloudbees-cli:$TOKEN" https://jenkins.soyspray.vip/job/silly-job/api/json | jq
```

### 2) Get CSRF crumb

```bash
COOKIE_JAR=$(mktemp)
CRUMB_JSON=$(curl -s -c "$COOKIE_JAR" -u "cloudbees-cli:$TOKEN" https://jenkins.soyspray.vip/crumbIssuer/api/json)
CRUMB_FIELD=$(printf '%s' "$CRUMB_JSON" | sed -n 's/.*"crumbRequestField":"\([^"]*\)".*/\1/p')
CRUMB_VALUE=$(printf '%s' "$CRUMB_JSON" | sed -n 's/.*"crumb":"\([^"]*\)".*/\1/p')
echo $CRUMB_VALUE
```

### 3) Trigger build with defaults

```bash
curl -s -b "$COOKIE_JAR" -u "cloudbees-cli:$TOKEN" \
  -H "$CRUMB_FIELD: $CRUMB_VALUE" \
  -d "environments=sandpit&commands=plan" \
  -X POST "https://jenkins.soyspray.vip/job/silly-job/buildWithParameters"
```

The response includes:

- `Location: https://jenkins.soyspray.vip/queue/item/<id>/`

To run apply for another environment:

```bash
curl -s -b "$COOKIE_JAR" -u "cloudbees-cli:$TOKEN" \
  -H "$CRUMB_FIELD: $CRUMB_VALUE" \
  -d "environments=prod&commands=apply" \
  -X POST "https://jenkins.soyspray.vip/job/silly-job/buildWithParameters"
```

If the job was created before this change and returns `silly-job is not parameterized`, delete/recreate it once from Jenkins UI (`job/silly-job/` > delete) or recreate it by forcing a new bootstrap init, then rerun steps 1-3.

### 4) Read queue / build output

```bash
curl -s -b "$COOKIE_JAR" -u "cloudbees-cli:$TOKEN" https://jenkins.soyspray.vip/job/silly-job/1/consoleText
```

Expected output for the bootstrap job:

```text
silly job executed from bootstrap
```

## Verification done from this host

- Jenkins UI is reachable at `https://jenkins.soyspray.vip/` (NGINX ingress, TLS secret `prod-cert-tls`).
- ArgoCD app is `Synced` + `Healthy`.
