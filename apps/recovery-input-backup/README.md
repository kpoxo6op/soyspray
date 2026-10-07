# Private recovery-input backup

The existing daily laptop service uses the restricted `node/` Restic repository,
its existing Vault credentials, pinned Python runtime and 30 daily snapshot
retention. No bucket policy, credentials or production alerts are changed.

The short include set covers the whole `~/.config/soyspray/recovery/` directory
(including the Argo admin Vault, unlock file and preserved voice models), private
Kubespray credentials, the active kubeconfig and any referenced certificate/key
files, node SSH identities/configuration/known hosts, and AWS profile configuration
and a credentials file when present. SSH keys are resolved from `ssh -G` for all
three nodes. CLI caches, source checkouts and browser state are excluded.
The collector also fetches fstab, hostname, hosts and netplan from each node.
Unexpected nested symlinks or missing required inputs stop the backup.

Each run stages files in a private workspace, verifies collection checksums,
backs them up, restores that exact snapshot in isolation and compares every
file's checksum and size. Local inputs must still match their originals after
the restore. Active/stable/staged/restored GI model hashes must agree. Temporary
content is cleaned up; private reports record the snapshot and match counts.

Install from delivered main with the repository Ansible environment:

```sh
ansible-playbook apps/recovery-input-backup/install.yml -e recovery_inputs_run_now=true
systemctl --user status soyspray-recovery-input-backup.timer
```

`operations_checkout` can point to an immutable release in the existing private
runtime directory; use its existing pinned venv. The service must never reference
a disposable worktree. The persistent timer remains daily at 03:15 Auckland.
Private reports are under `~/.local/state/soyspray/recovery-input-backup/`.
No production scrape or scheduled application restore depends on the laptop.

## Root of trust

`~/.config/soyspray/recovery/node-backup.vault.yml` holds the Restic password and
restricted S3 AWS access key pair. `vault-password` unlocks that Vault. The AWS
operator profile uses renewable login; its expiring caches are not recovery
inputs. A backup cannot independently unlock its own contents. An independent
copy of the unlock material has not been established by this work.

One human step: store the recovery Vault password, Restic password, restricted
S3 access key pair and repository address together in a password-manager entry
accessible without this laptop or cluster. Do not rotate them or automate the
password-manager step. Recovery restores files to a private directory first;
check disks/interfaces before applying any node configuration.


## Verified recovery point

On 2026-10-07, the native service completed snapshot `f9de4179` and an isolated
restore: all 43 collected files matched checksums and sizes, including all 29
local private originals. Active/stable/staged/restored voice models matched,
scratch cleanup completed, and the timer stayed enabled and active. This proves
that input set at that recovery point; it does not prove a whole-cluster restore
or independently held unlock material.
