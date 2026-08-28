# Vaultwarden trial

This package runs the private Vaultwarden trial at
`https://vault.soyspray.vip`. It currently holds the recoverable Hays Online
Timesheets login.

## Use the vault

Connect to the home LAN or Tailscale, then open
`https://vault.soyspray.vip`. Sign in with:

- Email: `hays-agent@vault.soyspray.vip`
- Master password: the `master-password` value in the
  `vaultwarden-agent-bootstrap` Secret

Registration is closed. Use this account to view, add, edit, and autofill
items.

On Boris's Wayland laptop, copy the master password for one paste:

```bash
kubectl -n vaultwarden get secret vaultwarden-agent-bootstrap \
  -o jsonpath='{.data.master-password}' | base64 --decode | wl-copy --paste-once
```

The server also works with official Bitwarden browser, desktop, and mobile
clients. Before sign-in, select **Self-hosted** and set the server URL to
`https://vault.soyspray.vip`. Bitwarden documents the client steps in
[Connect individual clients](https://bitwarden.com/help/change-client-environment/).

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
