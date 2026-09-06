# Node configuration and unique voice-model recovery

This laptop service collects four explicit files from each existing node:
`/etc/fstab`, `/etc/hostname`, `/etc/hosts`, and `/etc/netplan/50-cloud-init.yaml`.
It also collects `gi-v7.tflite` and the rollback model `gi-v2.tflite` from
`~/pCloudDrive/docs/soyspray/home-assistant-voice`.

The service uses the restricted `node/` Restic repository and the existing
`node-backup.vault.yml` credentials. It verifies node names and model headers,
backs up the files, restores them into a private local workspace, and compares
all hashes and sizes. Restic retains 30 daily snapshots for this host and tag.
It does not collect broad configuration directories or reproducible voice models.

Install through the repository venv:

```sh
ansible-playbook apps/recovery-input-backup/install.yml -e recovery_inputs_run_now=true
```

The native user timer runs daily at 03:15 Auckland time and catches missed runs
when the laptop is available. It invokes no model. Check
`systemctl --user status soyspray-recovery-input-backup.timer` and the private
reports under `~/.local/state/soyspray/recovery-input-backup/`.
The installer must reference the delivered checkout after merge. This timer
is separate from critical monthly restores and operations evidence collection.

The files can help recover mounts, node networking, and unique model inputs.
Kubespray still owns the cluster foundation. Do not apply restored configuration
to a replacement node without checking its disks and network interfaces.
