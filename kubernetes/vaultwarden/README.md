# Vaultwarden trial

This package runs the private Vaultwarden trial at
`https://vault.soyspray.vip`. It currently holds the recoverable Hays Online
Timesheets login.

Boris and the local agent use one account during V1. Keep only the Hays item in
this account until the identity split is designed.

## Use the vault

Connect to the home LAN or Tailscale, then open
`https://vault.soyspray.vip`. Sign in with:

- Email: the `email` value in the `vaultwarden-agent-bootstrap` Secret
- Master password: the `master-password` value in the
  `vaultwarden-agent-bootstrap` Secret

Registration is closed. Use this account to view, add, edit, and autofill
items.

On Boris's Wayland laptop, show the email and copy the master password for one
paste:

```bash
kubectl -n vaultwarden get secret vaultwarden-agent-bootstrap \
  -o jsonpath='{.data.email}' | base64 --decode
printf '\n'
kubectl -n vaultwarden get secret vaultwarden-agent-bootstrap \
  -o jsonpath='{.data.master-password}' | base64 --decode | wl-copy --paste-once
```

The server also works with official Bitwarden browser, desktop, and mobile
clients. Before sign-in, select **Self-hosted** and set the server URL to
`https://vault.soyspray.vip`. Bitwarden documents the client steps in
[Connect individual clients](https://bitwarden.com/help/change-client-environment/).

## Change the master password

The desktop app opens the web vault for this account setting. This is expected.
The deployment temporarily pins the exact pre-release image built from upstream
fix commit `fa2566d`. Stable Vaultwarden 1.37.2 cannot accept the current web
vault password-change request.

1. Write the new password on paper. It must have at least 12 characters.
   V1 has no master-password reset. The paper copy is the recovery copy.
2. Open `https://vault.soyspray.vip` and sign in.
3. Select **Settings > Security > Master password**.
4. Enter the current password and the new password.
5. Leave **Also rotate my account's encryption key** clear.
6. Select **Change master password**. The web vault signs out.
7. Update the runtime Secret before using the local reader:

```bash
cd /home/boris/code/soyspray
make go
(
  set -euo pipefail
  VAULTWARDEN_PASSWORD_VARS="$(mktemp /dev/shm/vaultwarden-password.XXXXXX.json)"
  trap 'rm -f "$VAULTWARDEN_PASSWORD_VARS"' EXIT
  read -rsp 'New master password: ' VAULTWARDEN_NEW_PASSWORD
  printf '\n'
  printf '%s' "$VAULTWARDEN_NEW_PASSWORD" \
    | jq -Rs --arg revision "$(git branch --show-current)" \
      '{vaultwarden_agent_master_password_override: ., vaultwarden_target_revision: $revision}' \
    > "$VAULTWARDEN_PASSWORD_VARS"
  unset VAULTWARDEN_NEW_PASSWORD
  soyspray-venv/bin/ansible-playbook \
    -i kubespray/inventory/soycluster/hosts.yml \
    --become --become-user=root --user ubuntu \
    playbooks/deploy-argocd-apps.yml --tags vaultwarden \
    --extra-vars "@$VAULTWARDEN_PASSWORD_VARS"
)
```

8. Clear the old command-line client session, then test a silent read:

```bash
VAULTWARDEN_CLI_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/bw-hays-agent"
if ! BITWARDENCLI_APPDATA_DIR="$VAULTWARDEN_CLI_DIR" bw status --nointeraction \
  | jq -e '.status == "unauthenticated"' >/dev/null; then
  BITWARDENCLI_APPDATA_DIR="$VAULTWARDEN_CLI_DIR" \
    bw logout --quiet --nointeraction
fi
unset VAULTWARDEN_CLI_DIR
agent-secret read hays-online-timesheets >/dev/null
```

The installed desktop app remains the normal human client. See the
[Vaultwarden problem](https://github.com/dani-garcia/vaultwarden/issues/7622),
[merged fix](https://github.com/dani-garcia/vaultwarden/pull/7634), and
[Bitwarden password guide](https://bitwarden.com/help/master-password/).

## Let an agent read Hays

The local reader needs `bw`, `kubectl`, and cluster access:

```bash
agent-secret read hays-online-timesheets
```

The command prints the username and password as plaintext JSON. Do not redirect
the output to logs or paste it into GitHub or a shell command.

## Deploy and check

Push the branch before deployment, then run from the repository root:

```bash
make vaultwarden VAULTWARDEN_REVISION="$(git branch --show-current)"
kubectl -n argocd get application vaultwarden
curl -fsS https://vault.soyspray.vip/alive
```

After merge, reconcile the default revision:

```bash
make vaultwarden VAULTWARDEN_REVISION=HEAD
```

The Ansible lifecycle is in
[`roles/apps/vaultwarden`](../../roles/apps/vaultwarden/README.md). The Argo CD
resources are in the
[Vaultwarden Argo CD folder](../../playbooks/argocd/applications/security/vaultwarden/README.md).

## V1 limits

V1 has one replica and one retained Longhorn volume. It has no backup, MFA,
phone approval, or multi-node recovery. Issues
[#202](https://github.com/kpoxo6op/soyspray/issues/202) to
[#205](https://github.com/kpoxo6op/soyspray/issues/205) track that work.
