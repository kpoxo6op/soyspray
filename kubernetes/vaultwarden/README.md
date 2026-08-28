# Vaultwarden trial

This package runs the private Vaultwarden trial at
`https://vault.soyspray.vip`. It holds the recoverable Hays Online Timesheets
login.

V1 has two identities:

- Boris uses a private human account. Its email and master password do not
  enter Kubernetes.
- The local agent uses `automation@vault.soyspray.vip`. Kubernetes keeps this
  account's random master password in `vaultwarden-agent-login`.

Both accounts can read one shared item in the `Hays timesheets` collection.

## Use the vault

Connect to the home LAN or Tailscale, then open
`https://vault.soyspray.vip`. Sign in with your human email and the master
password that you keep on paper. Registration is closed during normal use.

The server also works with official Bitwarden browser, desktop, and mobile
clients. Before sign-in, select **Self-hosted** and set the server URL to
`https://vault.soyspray.vip`. Bitwarden documents the client steps in
[Connect individual clients](https://bitwarden.com/help/change-client-environment/).

## Change your human master password

1. Write the new password on paper. V1 cannot reset a forgotten master
   password.
2. Open the web vault and select **Settings > Security > Master password**.
3. Enter the old and new passwords.
4. Leave **Also rotate my account's encryption key** clear for this trial.
5. Select **Change master password** and sign in again on your devices.

No cluster change is required. The human password is independent from the
agent account. See the
[Bitwarden master-password guide](https://bitwarden.com/help/master-password/).

## Enrol the agent once

Use this only when the agent account must be created again.

1. Create the `Soyspray` organization and its `Hays timesheets` collection
   from the human account.
2. Through GitOps, temporarily set `INVITATIONS_ALLOWED=true`. Keep
   `SIGNUPS_ALLOWED=false`.
3. Invite `automation@vault.soyspray.vip` as a **User**. Give it only
   **View items** access to `Hays timesheets`. Allow password viewing. Do not
   give edit or collection-management access.
4. Register the invited account with the random password from
   `vaultwarden-agent-login`. Do not display or log that password.
5. Compare the member fingerprint in both sessions. Confirm the member from
   the human account.
6. Move `hays-online-timesheets` from the human vault to the shared collection.
7. Restore `INVITATIONS_ALLOWED=false` through GitOps.
8. Run the silent check:

```bash
agent-secret read hays-online-timesheets >/dev/null
```

Do not enable global sign-ups for enrollment. With no mail service, an open
invitation must be completed and confirmed in the same session.

## Let an agent read Hays

The local reader needs `bw`, `kubectl`, and cluster access:

```bash
agent-secret read hays-online-timesheets
```

The command prints the username and password as plaintext JSON. Do not redirect
the output to logs or paste it into GitHub or a shell command.

The helper uses the agent account's random master password internally. A local
process with the same cluster access can read that agent password. The human
master password is not in Kubernetes and is not available to the helper.

## Open the latest submitted Hays timesheet

Run the one-shot check from the repository root:

```bash
scripts/hays-open-submitted-timesheet
```

The command starts or reuses a dedicated Chrome profile at
`~/.local/state/hays-agent-chrome`. It signs in with the agent item, opens the
newest submitted-timesheet details page, and leaves that tab visible. It prints
only the page type and received date. It does not edit, submit, approve, or send
a timesheet.

The command needs `bw`, `kubectl`, Google Chrome, and cluster access. It does
not use the human Vaultwarden account, the human master password, or the normal
Chrome profile.

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
phone approval, scheduled Hays run, or multi-node recovery. Issues
[#202](https://github.com/kpoxo6op/soyspray/issues/202) to
[#205](https://github.com/kpoxo6op/soyspray/issues/205) and
[#207](https://github.com/kpoxo6op/soyspray/issues/207) track that work.
