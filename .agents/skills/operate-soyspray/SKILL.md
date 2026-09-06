---
name: operate-soyspray
description: Operate the Soyspray cluster through its standard commands and Ansible runbooks. Use for application status, branch deployment, backup checks, isolated recovery, and deliberate retirement.
---

Read [AGENTS.md](../../../AGENTS.md) and the app's short README before an operation.
Use Application metadata for inventory. A missing annotation, inaccessible API,
or absent restore report means unknown with its cause.

Use `make apps`, `make status APP=NAME FORMAT=json`, and
`make backup-status FORMAT=json` for observations. Use `make check APP=NAME`,
`make diff APP=NAME`, `make deploy APP=NAME`, `make smoke APP=NAME`, and
`make restore-check APP=NAME` where the app has a maintained operation. Check the
app README for limits; an unsupported command must not fall back to deployment.

Run cluster changes through committed, pushed Ansible. The three-node inventory
and standard privilege escalation are in AGENTS.md. Normal `make deploy APP=NAME`
runs shared checks, affected-app checks, and deployment preflight. Use `make go`
for shared changes and final verification. App Makefiles own their Ansible
recipes; use the root operator interface to run their checks first.
Keep Kubespray's foundation ownership, MetalLB, and
shared node access separate from app operations.

For a preview, use the [native root procedure](../../../argocd/README.md).
Keep committed child Git sources on HEAD. Its native inline patch selects the
pushed branch for one child. After merge, return the root to HEAD and verify the
child's exact comparison, health, resource identity, access, and user journey.
An Argo source revision alone does not prove which image is running.

Before stateful ownership changes, complete a recent backup and isolated restore.
Use the [recovery runbooks](../../../playbooks/operations/recovery/README.md).
Preserve claim, volume, database, namespace, image, and credential identities.
Keep SQLite WAL files with their databases; use the backup API for a consistent
copy. Count recovery-point age from the source snapshot or database dump start.
A schedule, successful upload, or healthy pod does not prove recoverability.

Keep root pruning and cascading deletion off. Protect durable resources against
both pruning and Application deletion. Parking retains data. Retirement uses a
specific Ansible operation with ownership checks and observable absence; never
reuse an old disable path that recreates resources or deletes shared access.
OpenClaw runs on the laptop. Keep its node-0 retirement verifier through the
migration window, and preserve shared credentials and Tailscale.

Use Ansible Vault and documented private inputs. Keep recovery keys outside the
cluster. Do not print secret values or use regex edits of plaintext credentials.
Report the checks actually completed and each remaining evidence gap.

Legacy live TV, voice, firmware, and status-page aliases forward to their app
Makefiles. Use the root aliases for deployment or firmware upload so the full
check and deployment preflight run. Their deployment ownership is unchanged.
For scheduled critical restores, use `playbooks/operations/recovery/install-restore-check-schedule.yml`. The native user timer runs the maintained commands and validates private reports. Read the recovery README before enabling it. Keep model polling out of scheduled backup and restore evidence collection.
